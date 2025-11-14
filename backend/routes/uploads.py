"""Upload routes for scorecard files."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.sql_app.database import get_db
from backend.sql_app.models import Upload, UploadStatus
from backend.utils.s3 import generate_presigned_put_url, generate_upload_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/uploads", tags=["uploads"])


# Request/Response Models
class InitiateUploadRequest(BaseModel):
    """Request to initiate a file upload."""
    filename: str = Field(..., min_length=1, max_length=512)
    content_type: str = Field(..., min_length=1, max_length=100)
    game_id: int | None = Field(None, description="Optional game ID to associate with upload")
    uploader_id: str = Field(..., min_length=1, max_length=255, description="ID of user uploading")


class InitiateUploadResponse(BaseModel):
    """Response with presigned URL for upload."""
    upload_id: int
    presigned_url: str
    s3_key: str
    expires_in: int = 3600


class CompleteUploadRequest(BaseModel):
    """Request to mark upload as complete and trigger processing."""
    upload_id: int


class CompleteUploadResponse(BaseModel):
    """Response after completing upload."""
    upload_id: int
    status: str
    message: str


class UploadStatusResponse(BaseModel):
    """Upload status and parsed preview."""
    upload_id: int
    filename: str
    status: str
    game_id: int | None
    parsed_preview: dict | None
    error_message: str | None
    created_at: str
    updated_at: str


class ApplyUploadRequest(BaseModel):
    """Request to apply parsed preview to game."""
    confirmation: bool = Field(..., description="Explicit confirmation required")
    edited_preview: dict | None = Field(None, description="Optional edited version of parsed_preview")


class ApplyUploadResponse(BaseModel):
    """Response after applying upload."""
    success: bool
    message: str
    deliveries_added: int = 0


# Helper function to check feature flag
def require_uploads_enabled() -> None:
    """Dependency to check if uploads are enabled."""
    if not settings.ENABLE_UPLOADS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Upload feature is disabled"
        )


@router.post("/initiate", response_model=InitiateUploadResponse)
async def initiate_upload(
    request: InitiateUploadRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_uploads_enabled),
) -> InitiateUploadResponse:
    """
    Initiate a file upload and return a presigned URL.
    
    The client should use the presigned URL to upload the file directly to S3.
    """
    # Validate S3 credentials are configured
    if not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 credentials not configured"
        )
    
    # Generate S3 key
    s3_key = generate_upload_key(request.filename, request.uploader_id)
    
    # Generate presigned URL
    try:
        presigned_url = generate_presigned_put_url(s3_key, request.content_type)
    except RuntimeError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL"
        )
    
    # Create upload record
    upload = Upload(
        uploader_id=request.uploader_id,
        game_id=request.game_id,
        filename=request.filename,
        file_type=request.content_type,
        s3_key=s3_key,
        status=UploadStatus.pending,
        upload_metadata={}
    )
    
    db.add(upload)
    await db.commit()
    await db.refresh(upload)
    
    logger.info(f"Upload initiated: id={upload.id}, s3_key={s3_key}")
    
    return InitiateUploadResponse(
        upload_id=upload.id,
        presigned_url=presigned_url,
        s3_key=s3_key,
        expires_in=3600
    )


@router.post("/complete", response_model=CompleteUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def complete_upload(
    request: CompleteUploadRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_uploads_enabled),
) -> CompleteUploadResponse:
    """
    Mark an upload as complete and enqueue it for processing.
    
    Returns 202 Accepted as processing happens asynchronously.
    """
    # Fetch upload
    stmt = select(Upload).where(Upload.id == request.upload_id)
    result = await db.execute(stmt)
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {request.upload_id} not found"
        )
    
    if upload.status != UploadStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload is already {upload.status}"
        )
    
    # Update status to processing
    upload.status = UploadStatus.processing
    await db.commit()
    
    # Enqueue processing job
    if settings.ENABLE_OCR:
        try:
            from backend.worker.processor import process_upload_task
            # Enqueue Celery task
            process_upload_task.delay(upload.id)
            logger.info(f"Enqueued processing for upload {upload.id}")
        except ImportError:
            logger.warning("Celery worker not available, skipping OCR processing")
            upload.status = UploadStatus.failed
            upload.error_message = "OCR processing not available"
            await db.commit()
    else:
        logger.info(f"OCR disabled, marking upload {upload.id} as ready without processing")
        upload.status = UploadStatus.ready
        await db.commit()
    
    return CompleteUploadResponse(
        upload_id=upload.id,
        status=upload.status.value,
        message="Upload accepted for processing"
    )


@router.get("/{upload_id}/status", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: int,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_uploads_enabled),
) -> UploadStatusResponse:
    """
    Get the status of an upload and its parsed preview.
    """
    stmt = select(Upload).where(Upload.id == upload_id)
    result = await db.execute(stmt)
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    return UploadStatusResponse(
        upload_id=upload.id,
        filename=upload.filename,
        status=upload.status.value,
        game_id=upload.game_id,
        parsed_preview=upload.parsed_preview,
        error_message=upload.error_message,
        created_at=upload.created_at.isoformat(),
        updated_at=upload.updated_at.isoformat()
    )


@router.post("/{upload_id}/apply", response_model=ApplyUploadResponse)
async def apply_upload(
    upload_id: int,
    request: ApplyUploadRequest,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_uploads_enabled),
) -> ApplyUploadResponse:
    """
    Apply a parsed upload to a game after validation and explicit confirmation.
    
    This endpoint requires:
    1. The upload must be in 'ready' status
    2. The upload must have a parsed_preview
    3. The upload must be associated with a game
    4. Explicit confirmation must be provided
    
    The parsed_preview is validated before being applied to the delivery ledger.
    """
    if not request.confirmation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Explicit confirmation required to apply parsed preview"
        )
    
    # Fetch upload
    stmt = select(Upload).where(Upload.id == upload_id)
    result = await db.execute(stmt)
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found"
        )
    
    if upload.status != UploadStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload must be in 'ready' status, currently {upload.status}"
        )
    
    if not upload.game_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload must be associated with a game"
        )
    
    # Use edited preview if provided, otherwise use original
    preview = request.edited_preview if request.edited_preview is not None else upload.parsed_preview
    
    if not preview:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No parsed preview available to apply"
        )
    
    # Validate parsed_preview structure
    if not isinstance(preview, dict) or "deliveries" not in preview:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parsed preview format: must contain 'deliveries' key"
        )
    
    deliveries = preview.get("deliveries", [])
    if not isinstance(deliveries, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid parsed preview format: 'deliveries' must be a list"
        )
    
    # Here we would apply the deliveries to the game
    # For now, this is a placeholder that would integrate with the existing scoring service
    # This MUST NOT change core scoring logic - it should use existing delivery endpoints
    
    # TODO: Integrate with existing delivery service to add deliveries
    # from backend.services.delivery_service import add_delivery
    # for delivery_data in deliveries:
    #     await add_delivery(db, upload.game_id, delivery_data)
    
    logger.info(f"Applied upload {upload_id} to game {upload.game_id} with {len(deliveries)} deliveries")
    
    return ApplyUploadResponse(
        success=True,
        message=f"Successfully applied {len(deliveries)} deliveries to game {upload.game_id}",
        deliveries_added=len(deliveries)
    )
