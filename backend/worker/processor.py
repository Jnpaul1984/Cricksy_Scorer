"""Task processor for orchestrating upload processing workflow."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime

from backend.worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="backend.worker.processor.process_scorecard_task", bind=True)
def process_scorecard_task(self, upload_id: str) -> dict[str, str]:
    """
    Process uploaded scorecard image with OCR.

    Workflow:
    1. Update status to 'processing'
    2. Download image from S3/MinIO
    3. Run OCR (Tesseract) to extract text
    4. Parse text into structured data
    5. Update status to 'parsed' with results (or 'failed' on error)

    Args:
        upload_id: UUID of the upload to process

    Returns:
        dict with status and message
    """
    from backend.config import settings

    if not settings.ENABLE_OCR:
        logger.warning("OCR is disabled, skipping processing")
        return {"status": "skipped", "message": "OCR disabled"}

    logger.info(f"Starting processing for upload {upload_id}")

    try:
        # Import here to avoid dependency issues when worker not needed
        from backend.worker.parse_scorecard import parse_scorecard_image

        # Update status to processing
        _update_upload_status(upload_id, "processing")

        # Process the scorecard
        parsed_data = parse_scorecard_image(upload_id)

        # Update status to parsed with data
        _update_upload_status(
            upload_id, "parsed", parsed_data=parsed_data, processed_at=datetime.utcnow()
        )

        logger.info(f"Successfully processed upload {upload_id}")
        return {"status": "parsed", "message": "Processing complete"}

    except Exception as e:
        logger.exception(f"Failed to process upload {upload_id}: {e}")

        # Update status to failed with error
        _update_upload_status(upload_id, "failed", error_message=str(e))

        return {"status": "failed", "message": str(e)}


def _update_upload_status(
    upload_id: str,
    status: str,
    parsed_data: dict | None = None,
    error_message: str | None = None,
    processed_at: datetime | None = None,
) -> None:
    """
    Update upload status in database.

    Uses synchronous SQLAlchemy connection since Celery workers
    don't run in async context.
    """
    # Import SQLAlchemy sync version
    from sqlalchemy import create_engine, update
    from sqlalchemy.orm import Session

    from backend.sql_app.models.upload import Upload

    # Get database URL from environment
    import os

    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/cricksy_scorer")
    # Convert asyncpg to psycopg2 for sync
    if "asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    engine = create_engine(db_url)

    with Session(engine) as session:
        stmt = update(Upload).where(Upload.id == uuid.UUID(upload_id)).values(status=status)

        if parsed_data is not None:
            stmt = stmt.values(parsed_data=parsed_data)
        if error_message is not None:
            stmt = stmt.values(error_message=error_message)
        if processed_at is not None:
            stmt = stmt.values(processed_at=processed_at)

        session.execute(stmt)
        session.commit()

    logger.info(f"Updated upload {upload_id} status to {status}")
