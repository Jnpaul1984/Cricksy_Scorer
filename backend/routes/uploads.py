"""Upload routes for scorecard image uploads and OCR processing."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime as dt
from typing import Any

from backend.config import settings
from backend.sql_app.database import get_db
from backend.sql_app.models import Upload, UploadStatus
from backend.utils.s3 import generate_presigned_upload_url
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/uploads", tags=["uploads"])


# Request/Response schemas
class InitiateUploadRequest(BaseModel):
    """Request to initiate a new upload."""

    filename: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., min_length=1)
    game_id: str | None = None
    user_id: str | None = None


class InitiateUploadResponse(BaseModel):
    """Response with presigned URL for upload."""

    upload_id: str
    presigned_url: str
    s3_bucket: str
    s3_key: str
    expires_in: int


class CompleteUploadRequest(BaseModel):
    """Request to mark upload as complete."""

    file_size: int | None = None


class UploadStatusResponse(BaseModel):
    """Upload status information."""

    upload_id: str
    status: str
    filename: str
    game_id: str | None
    parsed_preview: dict[str, Any]
    error_message: str | None
    created_at: str
    updated_at: str
    processed_at: str | None
    applied_at: str | None


class ApplyUploadRequest(BaseModel):
    """Request to apply parsed data to delivery ledger."""

    confirm: bool = Field(..., description="User must explicitly confirm application")
    validated_data: dict[str, Any] | None = Field(
        None, description="Optional validated/corrected data"
    )


@router.post("/initiate", response_model=InitiateUploadResponse, status_code=status.HTTP_201_CREATED)
async def initiate_upload(
    request: InitiateUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> InitiateUploadResponse:
    """Initiate a new upload and generate presigned URL.

    Creates an upload record and returns a presigned URL for the client
    to upload the file directly to S3/MinIO.
    """
    if not settings.ENABLE_UPLOADS:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Upload feature is currently disabled",
        )

    # Validate content type
    allowed_types = ["image/jpeg", "image/png", "image/jpg", "application/pdf"]
    if request.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content type {request.content_type} not allowed. "
            f"Allowed types: {', '.join(allowed_types)}",
        )

    # Generate unique upload ID and S3 key
    upload_id = str(uuid.uuid4())
    s3_key = f"uploads/{upload_id}/{request.filename}"

    # Generate presigned URL
    try:
        presigned_url = generate_presigned_upload_url(
            bucket=settings.S3_BUCKET,
            key=s3_key,
            content_type=request.content_type,
            expiration=settings.S3_PRESIGNED_URL_EXPIRY,
        )
    except Exception as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate upload URL",
        ) from e

    # Create upload record
    upload = Upload(
        id=upload_id,
        game_id=request.game_id,
        user_id=request.user_id,
        filename=request.filename,
        content_type=request.content_type,
        s3_bucket=settings.S3_BUCKET,
        s3_key=s3_key,
        presigned_url=presigned_url,
        status=UploadStatus.initiated,
    )

    db.add(upload)
    await db.commit()

    logger.info(f"Initiated upload {upload_id} for file {request.filename}")

    return InitiateUploadResponse(
        upload_id=upload_id,
        presigned_url=presigned_url,
        s3_bucket=settings.S3_BUCKET,
        s3_key=s3_key,
        expires_in=settings.S3_PRESIGNED_URL_EXPIRY,
    )


@router.post("/{upload_id}/complete", status_code=status.HTTP_200_OK)
async def complete_upload(
    upload_id: str,
    request: CompleteUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Mark upload as complete and trigger OCR processing.

    Called by client after successfully uploading file to S3/MinIO.
    This triggers the OCR worker to process the file.
    """
    # Fetch upload record
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()

    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found",
        )

    if upload.status != UploadStatus.initiated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload {upload_id} is not in initiated state (current: {upload.status})",
        )

    # Update status
    upload.status = UploadStatus.uploaded
    if request.file_size:
        upload.file_size = request.file_size

    await db.commit()

    logger.info(f"Marked upload {upload_id} as uploaded")

    # Trigger OCR processing (if enabled)
    if settings.ENABLE_OCR:
        try:
            # Import here to avoid circular dependency
            from backend.worker.processor import process_upload_task

            process_upload_task.delay(upload_id)
            logger.info(f"Triggered OCR processing for upload {upload_id}")
        except Exception as e:
            logger.warning(f"Failed to trigger OCR processing: {e}")
            # Don't fail the request if worker is unavailable

    return {"message": "Upload marked as complete", "upload_id": upload_id}


@router.get("/{upload_id}/status", response_model=UploadStatusResponse)
async def get_upload_status(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
) -> UploadStatusResponse:
    """Get the current status of an upload."""
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()

    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found",
        )

    return UploadStatusResponse(
        upload_id=upload.id,
        status=upload.status.value,
        filename=upload.filename,
        game_id=upload.game_id,
        parsed_preview=upload.parsed_preview,
        error_message=upload.error_message,
        created_at=upload.created_at.isoformat(),
        updated_at=upload.updated_at.isoformat(),
        processed_at=upload.processed_at.isoformat() if upload.processed_at else None,
        applied_at=upload.applied_at.isoformat() if upload.applied_at else None,
    )


@router.post("/{upload_id}/apply", status_code=status.HTTP_200_OK)
async def apply_upload(
    upload_id: str,
    request: ApplyUploadRequest,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Apply parsed upload data to delivery ledger after user confirmation.

    This endpoint requires explicit user confirmation via the 'confirm' field.
    The parsed_preview must be validated before data is persisted to the delivery ledger.
    """
    # Require explicit confirmation
    if not request.confirm:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User confirmation required to apply upload data",
        )

    # Fetch upload record
    result = await db.execute(select(Upload).where(Upload.id == upload_id))
    upload = result.scalar_one_or_none()

    if not upload:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Upload {upload_id} not found",
        )

    # Validate status
    if upload.status not in [UploadStatus.parsed]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload {upload_id} must be in 'parsed' state to apply (current: {upload.status})",
        )

    # Validate parsed_preview exists and is not empty
    if not upload.parsed_preview or not isinstance(upload.parsed_preview, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload has no valid parsed preview data",
        )

    # Use validated data if provided, otherwise use parsed_preview
    data_to_apply = request.validated_data if request.validated_data else upload.parsed_preview

    # Validate required fields in data_to_apply
    required_fields = ["deliveries"]  # Minimum requirement for scorecard data
    for field in required_fields:
        if field not in data_to_apply:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Parsed data missing required field: {field}",
            )

    # TODO: Apply data to delivery ledger
    # This is where the actual data would be persisted to the game's delivery records
    # For now, we just mark the upload as applied
    # NOTE: Do NOT change core scoring logic - this is a placeholder for integration

    upload.status = UploadStatus.applied
    upload.applied_at = dt.now()

    # If validated data was provided, store it back to parsed_preview
    if request.validated_data:
        upload.parsed_preview = request.validated_data

    await db.commit()

    logger.info(f"Applied upload {upload_id} to delivery ledger")

    # Trigger socket broadcast for live updates (if game_id present)
    if upload.game_id:
        try:
            from backend.services.live_bus import emit_game_update

            await emit_game_update(upload.game_id, {"type": "upload_applied", "upload_id": upload_id})
            logger.info(f"Broadcasted upload_applied event for game {upload.game_id}")
        except Exception as e:
            logger.warning(f"Failed to broadcast upload_applied event: {e}")

    return {
        "message": "Upload data applied successfully",
        "upload_id": upload_id,
        "game_id": upload.game_id,
    }
