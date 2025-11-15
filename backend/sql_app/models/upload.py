"""Upload model for scorecard image/document uploads."""
from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import DateTime, Enum as SAEnum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.sql_app.database import Base

UTC = getattr(dt, "UTC", dt.UTC)


class UploadStatus(str, enum.Enum):
    """Status of an upload through the processing pipeline."""

    pending = "pending"  # Initiated, awaiting file upload completion
    uploaded = "uploaded"  # File uploaded to S3/MinIO, awaiting processing
    processing = "processing"  # OCR worker is processing
    parsed = "parsed"  # OCR completed, awaiting manual review
    applied = "applied"  # User confirmed and data applied to ledger
    failed = "failed"  # Processing failed
    rejected = "rejected"  # User rejected the parsed result


class Upload(Base):
    """
    Represents an uploaded scorecard image/document.

    Workflow:
    1. Frontend calls /api/uploads/initiate -> pending, gets presigned URL
    2. Frontend uploads file to S3/MinIO
    3. Frontend calls /api/uploads/complete -> uploaded, triggers OCR worker
    4. Worker processes and updates to processing -> parsed (or failed)
    5. Frontend shows preview, user reviews
    6. User calls /api/uploads/apply -> applied, data persisted to game ledger
       OR user rejects -> rejected
    """

    __tablename__ = "uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # User/session info
    uploader_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploader_session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # File info
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    s3_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    s3_bucket: Mapped[str] = mapped_column(String(255), nullable=False)

    # Status and workflow
    status: Mapped[UploadStatus] = mapped_column(
        SAEnum(UploadStatus, native_enum=False),
        nullable=False,
        default=UploadStatus.pending,
        index=True,
    )

    # OCR/parsing results - JSONB for flexibility
    # Example: {"teams": [...], "innings": [...], "scores": {...}}
    parsed_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, default=dict)

    # Error tracking
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional: link to game if applied
    game_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # Timestamps
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    processed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    applied_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<Upload id={self.id} status={self.status} filename={self.filename}>"
