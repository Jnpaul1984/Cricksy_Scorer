"""OCR processor for scorecard images.

This module handles downloading images from S3, running OCR (Tesseract),
and parsing the results into structured scorecard data.
"""

from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime as dt
from typing import Any

import pytesseract
from PIL import Image

from backend.config import settings
from backend.utils.s3 import generate_presigned_download_url, get_s3_client
from backend.worker.celery_app import app
from backend.worker.parse_scorecard import parse_scorecard, validate_parsed_data

logger = logging.getLogger(__name__)


def download_file_from_s3(bucket: str, key: str) -> str:
    """Download file from S3 to temporary local file.

    Args:
        bucket: S3 bucket name
        key: Object key in bucket

    Returns:
        Path to downloaded temporary file

    Raises:
        Exception: If download fails
    """
    s3_client = get_s3_client()

    # Create temporary file
    suffix = os.path.splitext(key)[1] or ".jpg"
    temp_fd, temp_path = tempfile.mkstemp(suffix=suffix)
    os.close(temp_fd)

    try:
        logger.info(f"Downloading {bucket}/{key} to {temp_path}")
        s3_client.download_file(bucket, key, temp_path)
        return temp_path
    except Exception as e:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except Exception:
            pass
        raise e


def run_ocr(image_path: str) -> str:
    """Run Tesseract OCR on image file.

    Args:
        image_path: Path to image file

    Returns:
        Extracted text from image

    Raises:
        Exception: If OCR fails
    """
    logger.info(f"Running OCR on {image_path}")

    try:
        # Open image with PIL
        image = Image.open(image_path)

        # Run Tesseract OCR
        # Configure for better scorecard recognition
        custom_config = r"--oem 3 --psm 6"  # OEM 3 = LSTM, PSM 6 = uniform block of text
        text = pytesseract.image_to_string(image, config=custom_config)

        logger.info(f"OCR extracted {len(text)} characters")
        return text

    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_upload_task(self, upload_id: str) -> dict[str, Any]:
    """Celery task to process an uploaded scorecard image.

    This task:
    1. Downloads the image from S3
    2. Runs OCR (Tesseract)
    3. Parses the OCR text into structured data
    4. Updates the upload record with results

    Args:
        upload_id: Upload ID to process

    Returns:
        Dictionary with processing results
    """
    logger.info(f"Processing upload {upload_id}")

    # Import here to avoid circular dependency and ensure DB session in worker context
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.asyncio import AsyncSession

    from backend.sql_app.database import DATABASE_URL
    from backend.sql_app.models import Upload, UploadStatus

    # Create async engine and session for worker
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session_maker = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    temp_file = None

    async def _process():
        nonlocal temp_file

        async with async_session_maker() as session:
            # Fetch upload record
            result = await session.execute(select(Upload).where(Upload.id == upload_id))
            upload = result.scalar_one_or_none()

            if not upload:
                logger.error(f"Upload {upload_id} not found")
                raise ValueError(f"Upload {upload_id} not found")

            if upload.status not in [UploadStatus.uploaded, UploadStatus.processing]:
                logger.warning(f"Upload {upload_id} is in state {upload.status}, skipping")
                return {"status": "skipped", "reason": f"Upload in {upload.status} state"}

            try:
                # Update status to processing
                upload.status = UploadStatus.processing
                await session.commit()

                # Download file from S3
                temp_file = download_file_from_s3(upload.s3_bucket, upload.s3_key)
                logger.info(f"Downloaded {upload.filename} to {temp_file}")

                # Run OCR
                ocr_text = run_ocr(temp_file)

                # Parse scorecard
                parsed_data = parse_scorecard(ocr_text)

                # Validate parsed data
                validation_errors = validate_parsed_data(parsed_data)
                if validation_errors:
                    logger.warning(f"Validation warnings for {upload_id}: {validation_errors}")
                    parsed_data["validation_errors"] = validation_errors

                # Update upload record with results
                upload.parsed_preview = parsed_data
                upload.status = UploadStatus.parsed
                upload.processed_at = dt.now()
                upload.error_message = None

                await session.commit()

                logger.info(f"Successfully processed upload {upload_id}")

                return {
                    "status": "success",
                    "upload_id": upload_id,
                    "confidence": parsed_data.get("confidence", 0.0),
                    "deliveries_count": len(parsed_data.get("deliveries", [])),
                }

            except Exception as e:
                logger.error(f"Error processing upload {upload_id}: {e}")

                # Update status to failed
                upload.status = UploadStatus.failed
                upload.error_message = str(e)
                upload.retry_count += 1

                await session.commit()

                # Retry if retries left
                if upload.retry_count < 3:
                    logger.info(f"Retrying upload {upload_id} (attempt {upload.retry_count})")
                    raise self.retry(exc=e)

                return {"status": "failed", "upload_id": upload_id, "error": str(e)}

            finally:
                # Clean up temp file
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.unlink(temp_file)
                        logger.debug(f"Cleaned up temp file {temp_file}")
                    except Exception as cleanup_err:
                        logger.warning(f"Failed to clean up temp file: {cleanup_err}")

    # Run async function
    import asyncio

    return asyncio.run(_process())
