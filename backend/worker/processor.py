"""
Worker processor for handling upload processing jobs.

This module contains the main task for processing uploaded files:
- Download from S3
- Extract text via OCR (PaddleOCR or Tesseract)
- Parse scorecard data
- Update database with results
"""

from __future__ import annotations

import io
import logging
import tempfile
from pathlib import Path
from typing import Any

from backend.config import settings
from backend.sql_app.models import UploadStatus
from backend.utils.s3 import download_from_s3
from backend.worker.celery_app import celery_app
from backend.worker.parse_scorecard import parse_scorecard_text

logger = logging.getLogger(__name__)


def enqueue_processing_job(upload_id: str) -> str:
    """
    Enqueue a processing job for the given upload.
    
    Args:
        upload_id: ID of the upload to process
    
    Returns:
        Task ID
    """
    if not settings.ENABLE_OCR:
        logger.warning("OCR is disabled, skipping job enqueue")
        return ""
    
    task = process_upload_task.delay(upload_id)
    logger.info(f"Enqueued processing job {task.id} for upload {upload_id}")
    return task.id


@celery_app.task(name="backend.worker.processor.process_upload_task", bind=True)
def process_upload_task(self: Any, upload_id: str) -> dict[str, Any]:
    """
    Celery task to process an uploaded file.
    
    Steps:
    1. Download file from S3
    2. Run OCR to extract text
    3. Parse scorecard data
    4. Update database with parsed preview
    
    Args:
        upload_id: ID of the upload to process
    
    Returns:
        Dict with processing results
    """
    logger.info(f"Processing upload {upload_id}")
    
    try:
        # Import here to avoid import errors when Celery is not installed
        from sqlalchemy import create_engine, select, update
        from sqlalchemy.orm import Session
        
        from backend.sql_app.models import Upload
        
        # Create synchronous database session for worker
        # TODO: Get DATABASE_URL from settings/env
        engine = create_engine("sqlite:///./cricksy_scorer.db")
        session = Session(engine)
        
        # Get upload record
        upload = session.execute(
            select(Upload).where(Upload.id == upload_id)
        ).scalar_one_or_none()
        
        if not upload:
            logger.error(f"Upload {upload_id} not found")
            return {"success": False, "error": "Upload not found"}
        
        # Download file from S3
        logger.info(f"Downloading file from S3: {upload.s3_key}")
        file_content = download_from_s3(upload.s3_key)
        
        # Extract text based on file type
        ocr_text = ""
        file_type = upload.file_type.lower()
        
        if "pdf" in file_type:
            # Process PDF
            ocr_text = _process_pdf(file_content)
        elif "image" in file_type or file_type.startswith("image/"):
            # Process image
            ocr_text = _process_image(file_content)
        else:
            logger.warning(f"Unsupported file type: {file_type}")
            session.execute(
                update(Upload)
                .where(Upload.id == upload_id)
                .values(status=UploadStatus.failed, upload_metadata={"error": "Unsupported file type"})
            )
            session.commit()
            session.close()
            return {"success": False, "error": "Unsupported file type"}
        
        # Parse scorecard
        logger.info(f"Parsing scorecard from {len(ocr_text)} characters of text")
        parsed_data = parse_scorecard_text(ocr_text)
        
        # Update upload record with parsed preview
        session.execute(
            update(Upload)
            .where(Upload.id == upload_id)
            .values(
                status=UploadStatus.ready,
                parsed_preview=parsed_data,
            )
        )
        session.commit()
        session.close()
        
        logger.info(f"Successfully processed upload {upload_id}")
        return {
            "success": True,
            "upload_id": upload_id,
            "deliveries_count": len(parsed_data.get("deliveries", [])),
        }
    
    except Exception as e:
        logger.error(f"Error processing upload {upload_id}: {e}", exc_info=True)
        
        # Update status to failed
        try:
            from sqlalchemy import create_engine, update
            from sqlalchemy.orm import Session
            
            from backend.sql_app.models import Upload
            
            engine = create_engine("sqlite:///./cricksy_scorer.db")
            session = Session(engine)
            session.execute(
                update(Upload)
                .where(Upload.id == upload_id)
                .values(
                    status=UploadStatus.failed,
                    upload_metadata={"error": str(e)},
                )
            )
            session.commit()
            session.close()
        except Exception as db_error:
            logger.error(f"Failed to update upload status: {db_error}")
        
        return {"success": False, "error": str(e)}


def _process_pdf(pdf_content: bytes) -> str:
    """
    Process a PDF file and extract text via OCR.
    
    For PDFs, we:
    1. Convert pages to images using pdf2image
    2. Run OCR on each page image
    3. Combine text from all pages
    
    Args:
        pdf_content: PDF file content as bytes
    
    Returns:
        Extracted text
    """
    try:
        import pdf2image
        
        # Convert PDF to images
        with tempfile.TemporaryDirectory() as temp_dir:
            images = pdf2image.convert_from_bytes(pdf_content)
            
            all_text = []
            for i, image in enumerate(images):
                logger.info(f"Processing PDF page {i+1}/{len(images)}")
                page_text = _run_ocr_on_image(image)
                all_text.append(page_text)
            
            return "\n\n=== PAGE BREAK ===\n\n".join(all_text)
    
    except ImportError:
        logger.warning("pdf2image not installed, skipping PDF processing")
        return "ERROR: PDF processing not available"
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        return f"ERROR: {e}"


def _process_image(image_content: bytes) -> str:
    """
    Process an image file and extract text via OCR.
    
    Args:
        image_content: Image file content as bytes
    
    Returns:
        Extracted text
    """
    try:
        from PIL import Image
        
        image = Image.open(io.BytesIO(image_content))
        return _run_ocr_on_image(image)
    
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return f"ERROR: {e}"


def _run_ocr_on_image(image: Any) -> str:
    """
    Run OCR on an image using Tesseract.
    
    For production, consider using PaddleOCR for better accuracy.
    This prototype uses Tesseract for simplicity.
    
    Args:
        image: PIL Image object
    
    Returns:
        Extracted text
    """
    try:
        import pytesseract
        
        text = pytesseract.image_to_string(image)
        logger.info(f"Extracted {len(text)} characters via OCR")
        return text
    
    except ImportError:
        logger.warning("pytesseract not installed, using fallback")
        return "ERROR: OCR not available (pytesseract not installed)"
    except Exception as e:
        logger.error(f"OCR error: {e}")
        return f"ERROR: {e}"
