"""API routes for scorecard upload management."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from backend.config import settings
from backend.sql_app.database import get_db
from backend.sql_app.models import Upload
from backend.utils.s3 import generate_presigned_upload_url
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/uploads", tags=["uploads"])


# Pydantic models for request/response
class InitiateUploadRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(default="image/jpeg")


class InitiateUploadResponse(BaseModel):
    upload_id: str
    upload_url: str
    s3_key: str
    expires_in: int


class CompleteUploadRequest(BaseModel):
    upload_id: str


class UploadStatusResponse(BaseModel):
    upload_id: str
    status: str
    filename: str
    uploaded_at: datetime | None
    processed_at: datetime | None
    parsed_preview: dict[str, Any] | None
    error_message: str | None


class ApplyUploadRequest(BaseModel):
    upload_id: str
    confirm: bool = Field(..., description="User must explicitly confirm to apply")


class ApplyUploadResponse(BaseModel):
    upload_id: str
    status: str
    message: str


@router.post("/initiate", response_model=InitiateUploadResponse)
async def initiate_upload(
    request: InitiateUploadRequest, db: AsyncSession = Depends(get_db)
) -> InitiateUploadResponse:
    """
    Initiate a new upload by generating a presigned URL.

    This endpoint:
    1. Creates a new Upload record with status 'pending'
    2. Generates a presigned S3/MinIO upload URL
    3. Returns the URL and upload_id to the client

    The client should then PUT the file directly to the presigned URL.
    """
    if not settings.ENABLE_UPLOADS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload feature is disabled",
        )

    # Generate unique upload ID and S3 key
    upload_id = str(uuid.uuid4())
    s3_key = f"uploads/{upload_id}/{request.filename}"

    # Generate presigned URL
    upload_url = generate_presigned_upload_url(
        s3_key=s3_key,
        content_type=request.content_type,
        expiry=settings.S3_PRESIGNED_EXPIRY,
    )

    if not upload_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        )

    # Create upload record
    upload = Upload(
        upload_id=upload_id,
        filename=request.filename,
        s3_key=s3_key,
        status="pending",
        upload_url=upload_url,
    )

    db.add(upload)
    await db.commit()
    await db.refresh(upload)

    logger.info(f"Initiated upload {upload_id} for file {request.filename}")

    return InitiateUploadResponse(
        upload_id=upload_id,
        upload_url=upload_url,
        s3_key=s3_key,
        expires_in=settings.S3_PRESIGNED_EXPIRY,
    )


@router.post("/complete")
async def complete_upload(
    request: CompleteUploadRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, str]:
    """
    Mark an upload as completed after the client has uploaded to S3.

    This endpoint:
    1. Verifies the upload exists
    2. Updates status to 'uploaded'
    3. Triggers OCR processing (if enabled)
    """
    result = await db.execute(select(Upload).where(Upload.upload_id == request.upload_id))
    upload = result.scalar_one_or_none()

    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )

    if upload.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload is already {upload.status}",
        )

    # Mark as uploaded
    upload.status = "uploaded"
    upload.uploaded_at = datetime.now(UTC)
    upload.updated_at = datetime.now(UTC)

    await db.commit()

    # Trigger OCR processing if enabled
    if settings.ENABLE_OCR:
        try:
            from backend.worker.processor import process_upload_task

            # Queue the task
            process_upload_task.delay(request.upload_id)
            logger.info(f"Queued OCR processing for upload {request.upload_id}")
        except Exception as e:
            logger.warning(f"Failed to queue OCR processing: {e}")
            # Don't fail the request if queueing fails

    logger.info(f"Completed upload {request.upload_id}")

    return {"message": "Upload completed", "status": "uploaded"}


@router.get("/{upload_id}/status", response_model=UploadStatusResponse)
async def get_upload_status(upload_id: str, db: AsyncSession = Depends(get_db)) -> UploadStatusResponse:
    """
    Get the current status of an upload.

    Returns:
    - upload_id
    - status: pending, uploaded, processing, completed, failed, applied
    - filename
    - uploaded_at
    - processed_at
    - parsed_preview: OCR results (if completed)
    - error_message: Error details (if failed)
    """
    result = await db.execute(select(Upload).where(Upload.upload_id == upload_id))
    upload = result.scalar_one_or_none()

    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )

    return UploadStatusResponse(
        upload_id=upload.upload_id,
        status=upload.status,
        filename=upload.filename,
        uploaded_at=upload.uploaded_at,
        processed_at=upload.processed_at,
        parsed_preview=upload.parsed_preview,
        error_message=upload.error_message,
    )


@router.post("/{upload_id}/apply", response_model=ApplyUploadResponse)
async def apply_upload(
    upload_id: str, request: ApplyUploadRequest, db: AsyncSession = Depends(get_db)
) -> ApplyUploadResponse:
    """
    Apply the parsed scorecard data to the delivery ledger.

    This endpoint requires:
    1. Explicit user confirmation (confirm=true)
    2. Valid parsed_preview data
    3. Upload status must be 'completed'

    This endpoint validates the parsed_preview before applying and requires
    manual user confirmation to ensure human oversight of OCR results.
    """
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit confirmation required to apply upload",
        )

    result = await db.execute(select(Upload).where(Upload.upload_id == upload_id))
    upload = result.scalar_one_or_none()

    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload not found",
        )

    if upload.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload must be completed before applying (current status: {upload.status})",
        )

    if not upload.parsed_preview:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No parsed data available to apply",
        )

    # Validate parsed_preview structure
    if not isinstance(upload.parsed_preview, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parsed_preview format",
        )

    # TODO: Apply parsed data to delivery ledger
    # This is a placeholder - actual implementation would:
    # 1. Validate all required fields are present
    # 2. Create/update game deliveries
    # 3. Emit WebSocket events for live updates
    # 4. Handle transaction rollback on error

    upload.status = "applied"
    upload.applied_at = datetime.now(UTC)
    upload.updated_at = datetime.now(UTC)

    await db.commit()

    logger.info(f"Applied upload {upload_id} to delivery ledger")

    # Emit WebSocket notification (if live bus is available)
    try:
        from backend.services.live_bus import emit_to_game

        game_id = upload.parsed_preview.get("game_id")
        if game_id:
            await emit_to_game(
                game_id,
                "upload:applied",
                {"upload_id": upload_id, "filename": upload.filename},
            )
    except Exception as e:
        logger.warning(f"Failed to emit WebSocket notification: {e}")

    return ApplyUploadResponse(
        upload_id=upload_id,
        status="applied",
        message="Upload applied successfully",
    )
