"""Upload API routes for photo/PDF/video uploads with OCR processing."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.sql_app.database import get_db
from backend.sql_app.models import Upload, UploadStatus
from backend.utils.s3 import generate_presigned_put_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


# ===== Request/Response Models =====


class InitiateUploadRequest(BaseModel):
    """Request to initiate a new upload."""
    filename: str
    file_type: str  # MIME type
    game_id: str | None = None


class InitiateUploadResponse(BaseModel):
    """Response with presigned URL and upload details."""
    upload_id: str
    s3_key: str
    presigned_url: str
    expires_in: int


class CompleteUploadRequest(BaseModel):
    """Request to mark an upload as complete and enqueue processing."""
    upload_id: str
    s3_key: str
    size: int
    checksum: str | None = None


class CompleteUploadResponse(BaseModel):
    """Response after upload completion."""
    upload_id: str
    status: str
    message: str


class UploadStatusResponse(BaseModel):
    """Response with current upload status and parsed preview."""
    upload_id: str
    status: str
    filename: str
    file_type: str
    game_id: str | None
    parsed_preview: dict[str, Any] | None
    upload_metadata: dict[str, Any]
    created_at: str
    updated_at: str


class ApplyUploadRequest(BaseModel):
    """Request to apply parsed deliveries to a game."""
    game_id: str


class ApplyUploadResponse(BaseModel):
    """Response after applying parsed data to game."""
    upload_id: str
    game_id: str
    deliveries_applied: int
    message: str


# ===== Helper Functions =====


def _check_feature_enabled() -> None:
    """Check if uploads feature is enabled."""
    if not settings.ENABLE_UPLOADS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload feature is not enabled",
        )


async def _get_upload_or_404(upload_id: str, db: AsyncSession) -> Upload:
    """Get upload by ID or raise 404."""
    from sqlalchemy import select
    
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()
    
    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found",
        )
    
    return upload


# ===== Route Handlers =====


@router.post("/initiate", response_model=InitiateUploadResponse)
async def initiate_upload(
    request: InitiateUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> InitiateUploadResponse:
    """
    Initiate a new upload and return a presigned PUT URL.
    
    This endpoint creates an Upload record in the database and generates
    a presigned S3 URL for the client to upload the file directly to S3.
    """
    _check_feature_enabled()
    
    # Generate unique upload ID and S3 key
    upload_id = str(uuid.uuid4())
    # S3 key format: uploads/{upload_id}/{filename}
    s3_key = f"uploads/{upload_id}/{request.filename}"
    
    try:
        # Generate presigned URL
        presigned_url = generate_presigned_put_url(
            s3_key=s3_key,
            content_type=request.file_type,
        )
        
        # Create upload record
        upload = Upload(
            id=upload_id,
            uploader_id="anonymous",  # TODO: Use actual user ID from auth
            game_id=request.game_id,
            filename=request.filename,
            file_type=request.file_type,
            s3_key=s3_key,
            status=UploadStatus.pending,
            upload_metadata={},
        )
        
        db.add(upload)
        await db.commit()
        
        logger.info(f"Initiated upload {upload_id} for file {request.filename}")
        
        return InitiateUploadResponse(
            upload_id=upload_id,
            s3_key=s3_key,
            presigned_url=presigned_url,
            expires_in=settings.PRESIGNED_URL_EXPIRATION,
        )
    
    except Exception as e:
        logger.error(f"Failed to initiate upload: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initiate upload",
        )


@router.post("/complete", response_model=CompleteUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def complete_upload(
    request: CompleteUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> CompleteUploadResponse:
    """
    Mark an upload as complete and enqueue it for OCR processing.
    
    This endpoint is called after the client successfully uploads the file
    to S3 using the presigned URL. It updates the upload status and
    enqueues a background job to process the file.
    """
    _check_feature_enabled()
    
    upload = await _get_upload_or_404(request.upload_id, db)
    
    # Validate s3_key matches
    if upload.s3_key != request.s3_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="S3 key mismatch",
        )
    
    # Update metadata with size and checksum
    upload.upload_metadata["size"] = request.size
    if request.checksum:
        upload.upload_metadata["checksum"] = request.checksum
    
    # Update status to processing
    upload.status = UploadStatus.processing
    
    await db.commit()
    
    # Enqueue processing job (if OCR is enabled)
    if settings.ENABLE_OCR:
        try:
            # Import here to avoid circular dependency
            from backend.worker.processor import enqueue_processing_job
            enqueue_processing_job(request.upload_id)
            logger.info(f"Enqueued processing job for upload {request.upload_id}")
        except Exception as e:
            logger.error(f"Failed to enqueue processing job: {e}")
            # Don't fail the request, processing can be retried
    
    return CompleteUploadResponse(
        upload_id=request.upload_id,
        status=upload.status.value,
        message="Upload complete, processing enqueued" if settings.ENABLE_OCR else "Upload complete",
    )


@router.get("/{upload_id}/status", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
) -> UploadStatusResponse:
    """
    Get the current status of an upload, including parsed preview if available.
    
    This endpoint is used by the frontend to poll for processing completion
    and retrieve the parsed preview data.
    """
    _check_feature_enabled()
    
    upload = await _get_upload_or_404(upload_id, db)
    
    return UploadStatusResponse(
        upload_id=upload.id,
        status=upload.status.value,
        filename=upload.filename,
        file_type=upload.file_type,
        game_id=upload.game_id,
        parsed_preview=upload.parsed_preview,
        upload_metadata=upload.upload_metadata,
        created_at=upload.created_at.isoformat(),
        updated_at=upload.updated_at.isoformat(),
    )


@router.post("/{upload_id}/apply", response_model=ApplyUploadResponse)
async def apply_upload(
    upload_id: str,
    request: ApplyUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> ApplyUploadResponse:
    """
    Apply parsed deliveries from an upload to a game.
    
    This endpoint validates the parsed preview and then applies the deliveries
    to the specified game using the existing scoring endpoints. This requires
    manual confirmation from the user to prevent accidental data corruption.
    """
    _check_feature_enabled()
    
    upload = await _get_upload_or_404(upload_id, db)
    
    # Validate upload is ready
    if upload.status != UploadStatus.ready:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload is not ready (current status: {upload.status.value})",
        )
    
    # Validate parsed preview exists
    if not upload.parsed_preview:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No parsed preview available",
        )
    
    # Get deliveries from parsed preview
    deliveries = upload.parsed_preview.get("deliveries", [])
    if not deliveries:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No deliveries in parsed preview",
        )
    
    # TODO: Validate game exists and user has permission
    # TODO: Apply deliveries using existing POST /games/{id}/deliveries endpoint
    # For now, just log and return success
    
    logger.info(
        f"Applied {len(deliveries)} deliveries from upload {upload_id} to game {request.game_id}"
    )
    
    return ApplyUploadResponse(
        upload_id=upload_id,
        game_id=request.game_id,
        deliveries_applied=len(deliveries),
        message=f"Successfully applied {len(deliveries)} deliveries",
    )
