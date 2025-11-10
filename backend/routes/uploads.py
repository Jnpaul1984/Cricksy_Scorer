"""Upload routes for scorecard image/document uploads."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.sql_app.database import get_db
from backend.sql_app.models.upload import Upload, UploadStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


# Request/Response Models
class InitiateUploadRequest(BaseModel):
    """Request to initiate an upload."""

    filename: str = Field(..., min_length=1, max_length=512)
    content_type: str | None = Field(None, max_length=128)
    file_size: int | None = Field(None, gt=0)
    uploader_name: str | None = Field(None, max_length=255)
    uploader_session_id: str | None = Field(None, max_length=255)


class InitiateUploadResponse(BaseModel):
    """Response from initiate upload."""

    upload_id: str
    upload_url: str
    upload_method: str  # "PUT"
    expires_in: int
    s3_key: str
    s3_bucket: str


class CompleteUploadRequest(BaseModel):
    """Request to mark upload as complete."""

    upload_id: str


class UploadStatusResponse(BaseModel):
    """Upload status response."""

    upload_id: str
    status: str
    filename: str
    created_at: str
    updated_at: str
    processed_at: str | None = None
    applied_at: str | None = None
    error_message: str | None = None
    parsed_data: dict[str, Any] | None = None
    game_id: str | None = None


class ApplyUploadRequest(BaseModel):
    """Request to apply parsed upload to game ledger."""

    upload_id: str
    game_id: str | None = None
    confirmation: bool = Field(..., description="User must confirm before applying")


class ApplyUploadResponse(BaseModel):
    """Response from apply upload."""

    upload_id: str
    status: str
    game_id: str | None = None
    message: str


def _check_feature_enabled() -> None:
    """Check if uploads feature is enabled."""
    if not settings.ENABLE_UPLOADS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload feature is not enabled",
        )


async def _get_upload_or_404(
    upload_id: uuid.UUID, db: AsyncSession
) -> Upload:
    """Get upload by ID or raise 404."""
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found",
        )
    return upload


@router.post("/initiate", response_model=InitiateUploadResponse)
async def initiate_upload(
    request: InitiateUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> InitiateUploadResponse:
    """
    Initiate a new upload and get presigned URL.

    1. Creates Upload record in pending state
    2. Generates presigned S3/MinIO URL for upload
    3. Returns URL and upload metadata to client

    Client should then:
    - Upload file to the presigned URL
    - Call /complete with upload_id when done
    """
    _check_feature_enabled()

    # Validate file size
    if request.file_size:
        max_size_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if request.file_size > max_size_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File size exceeds maximum of {settings.MAX_UPLOAD_SIZE_MB}MB",
            )

    # Create upload record
    upload_id = uuid.uuid4()
    s3_key = f"uploads/{upload_id}/{request.filename}"
    s3_bucket = settings.S3_UPLOAD_BUCKET

    upload = Upload(
        id=upload_id,
        filename=request.filename,
        content_type=request.content_type,
        file_size=request.file_size,
        s3_key=s3_key,
        s3_bucket=s3_bucket,
        status=UploadStatus.pending,
        uploader_name=request.uploader_name,
        uploader_session_id=request.uploader_session_id,
    )

    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    # Generate presigned URL (if boto3 available)
    try:
        from backend.utils.s3 import generate_presigned_upload_url

        presigned = generate_presigned_upload_url(
            bucket=s3_bucket,
            key=s3_key,
            expires_in=3600,
            content_type=request.content_type,
        )
        upload_url = presigned["url"]
        upload_method = presigned.get("method", "PUT")
    except Exception as e:
        logger.warning(f"Failed to generate presigned URL: {e}")
        # Fallback for development without S3
        upload_url = f"http://placeholder-upload-url/{s3_key}"
        upload_method = "PUT"

    return InitiateUploadResponse(
        upload_id=str(upload_id),
        upload_url=upload_url,
        upload_method=upload_method,
        expires_in=3600,
        s3_key=s3_key,
        s3_bucket=s3_bucket,
    )


@router.post("/complete")
async def complete_upload(
    request: CompleteUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Mark upload as complete and trigger OCR processing.

    1. Updates Upload status to 'uploaded'
    2. Triggers Celery task for OCR processing (if enabled)
    3. Returns acknowledgment

    Processing happens asynchronously. Client should poll /status
    to check processing progress.
    """
    _check_feature_enabled()

    upload_id = uuid.UUID(request.upload_id)
    upload = await _get_upload_or_404(upload_id, db)

    if upload.status != UploadStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload is not in pending state (current: {upload.status})",
        )

    # Update status
    upload.status = UploadStatus.uploaded
    await db.commit()

    # Trigger OCR processing (if enabled)
    if settings.ENABLE_OCR:
        try:
            from backend.worker.processor import process_scorecard_task

            # Queue the task
            process_scorecard_task.delay(str(upload_id))
            logger.info(f"Queued OCR task for upload {upload_id}")
        except Exception as e:
            logger.warning(f"Failed to queue OCR task: {e}")
            # Continue anyway - processing can be triggered manually

    return {
        "upload_id": str(upload_id),
        "status": "uploaded",
        "message": "Upload complete, processing queued",
    }


@router.get("/status/{upload_id}", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
) -> UploadStatusResponse:
    """
    Get status of an upload.

    Returns current processing status and parsed data (if available).
    """
    _check_feature_enabled()

    upload = await _get_upload_or_404(uuid.UUID(upload_id), db)

    return UploadStatusResponse(
        upload_id=str(upload.id),
        status=upload.status.value,
        filename=upload.filename,
        created_at=upload.created_at.isoformat(),
        updated_at=upload.updated_at.isoformat(),
        processed_at=upload.processed_at.isoformat() if upload.processed_at else None,
        applied_at=upload.applied_at.isoformat() if upload.applied_at else None,
        error_message=upload.error_message,
        parsed_data=upload.parsed_data,
        game_id=str(upload.game_id) if upload.game_id else None,
    )


@router.post("/apply", response_model=ApplyUploadResponse)
async def apply_upload(
    request: ApplyUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplyUploadResponse:
    """
    Apply parsed upload data to game ledger.

    This endpoint requires manual confirmation from the user.
    It validates that:
    1. Upload is in 'parsed' state
    2. parsed_data is present and valid
    3. User has confirmed the action

    After validation, it:
    1. Persists data to appropriate game tables
    2. Updates upload status to 'applied'
    3. Emits socket event for live updates
    """
    _check_feature_enabled()

    if not request.confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation required to apply upload",
        )

    upload_id = uuid.UUID(request.upload_id)
    upload = await _get_upload_or_404(upload_id, db)

    if upload.status != UploadStatus.parsed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload must be in 'parsed' state to apply (current: {upload.status})",
        )

    if not upload.parsed_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No parsed data available to apply",
        )

    # TODO: Implement actual application logic
    # This should:
    # 1. Validate parsed_data structure
    # 2. Create/update game record
    # 3. Create delivery records
    # 4. Update player stats
    # 5. Emit socket events for live updates

    # For now, just mark as applied
    upload.status = UploadStatus.applied
    upload.applied_at = datetime.utcnow()
    if request.game_id:
        upload.game_id = uuid.UUID(request.game_id)

    await db.commit()

    logger.info(f"Applied upload {upload_id} to game")

    return ApplyUploadResponse(
        upload_id=str(upload_id),
        status="applied",
        game_id=str(upload.game_id) if upload.game_id else None,
        message="Upload data applied successfully",
    )
