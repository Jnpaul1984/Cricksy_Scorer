"""OCR processing worker for uploaded scorecard files.

This worker downloads files from S3, runs OCR using Tesseract, parses the results,
and updates the upload record with the parsed preview.
"""
from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

from celery import Task

from backend.config import settings
from backend.worker.celery_app import app

logger = logging.getLogger(__name__)


def _import_dependencies():
    """
    Lazy import of OCR dependencies to avoid requiring them in non-worker environments.
    
    Returns:
        Tuple of (pytesseract, Image, pdf2image modules) or (None, None, None) if not available
    """
    try:
        import pytesseract
        from PIL import Image
        
        try:
            from pdf2image import convert_from_path
        except ImportError:
            convert_from_path = None
            logger.warning("pdf2image not available, PDF processing will fail")
        
        return pytesseract, Image, convert_from_path
    except ImportError as e:
        logger.error(f"OCR dependencies not available: {e}")
        return None, None, None


class OCRProcessingTask(Task):
    """Custom Celery task with error handling."""
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        upload_id = args[0] if args else kwargs.get("upload_id")
        logger.error(f"OCR processing failed for upload {upload_id}: {exc}")
        
        # Update upload status to failed
        try:
            from backend.sql_app.database import SessionLocal
            from backend.sql_app.models import Upload, UploadStatus
            
            with SessionLocal() as db:
                upload = db.query(Upload).filter(Upload.id == upload_id).first()
                if upload:
                    upload.status = UploadStatus.failed
                    upload.error_message = f"OCR processing failed: {str(exc)}"
                    db.commit()
        except Exception as e:
            logger.error(f"Failed to update upload status: {e}")


@app.task(bind=True, base=OCRProcessingTask, name="backend.worker.processor.process_upload_task")
def process_upload_task(self, upload_id: int) -> dict[str, Any]:
    """
    Process an uploaded file: download, OCR, parse, and update database.
    
    Args:
        upload_id: ID of the upload to process
    
    Returns:
        Dictionary with processing results
    """
    logger.info(f"Starting OCR processing for upload {upload_id}")
    
    # Check if OCR is enabled
    if not settings.ENABLE_OCR:
        logger.warning(f"OCR is disabled, skipping processing for upload {upload_id}")
        return {"status": "skipped", "reason": "OCR disabled"}
    
    # Import dependencies
    pytesseract, Image, convert_from_path = _import_dependencies()
    if not pytesseract or not Image:
        error_msg = "OCR dependencies not available"
        logger.error(error_msg)
        _mark_upload_failed(upload_id, error_msg)
        return {"status": "error", "message": error_msg}
    
    # Import database and models
    try:
        from backend.sql_app.database import SessionLocal
        from backend.sql_app.models import Upload, UploadStatus
        from backend.utils.s3 import download_file_from_s3
        from backend.worker.parse_scorecard import parse_scorecard, validate_parsed_deliveries
    except ImportError as e:
        error_msg = f"Failed to import required modules: {e}"
        logger.error(error_msg)
        return {"status": "error", "message": error_msg}
    
    # Fetch upload record
    with SessionLocal() as db:
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        if not upload:
            logger.error(f"Upload {upload_id} not found")
            return {"status": "error", "message": "Upload not found"}
        
        s3_key = upload.s3_key
        file_type = upload.file_type
        filename = upload.filename
    
    # Create temporary file for download
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir) / filename
        
        try:
            # Download file from S3
            logger.info(f"Downloading {s3_key} from S3")
            download_file_from_s3(s3_key, str(temp_path))
            
            # Extract text based on file type
            ocr_text = ""
            if file_type.startswith("image/"):
                # Process image file
                logger.info(f"Running OCR on image {filename}")
                image = Image.open(temp_path)
                ocr_text = pytesseract.image_to_string(image)
            elif file_type == "application/pdf":
                if not convert_from_path:
                    error_msg = "PDF processing not available (pdf2image not installed)"
                    logger.error(error_msg)
                    _mark_upload_failed(upload_id, error_msg)
                    return {"status": "error", "message": error_msg}
                
                # Convert PDF to images and OCR each page
                logger.info(f"Converting PDF {filename} to images")
                images = convert_from_path(str(temp_path))
                
                ocr_texts = []
                for i, image in enumerate(images):
                    logger.info(f"Running OCR on page {i+1}/{len(images)}")
                    page_text = pytesseract.image_to_string(image)
                    ocr_texts.append(page_text)
                
                ocr_text = "\n\n--- PAGE BREAK ---\n\n".join(ocr_texts)
            else:
                error_msg = f"Unsupported file type: {file_type}"
                logger.error(error_msg)
                _mark_upload_failed(upload_id, error_msg)
                return {"status": "error", "message": error_msg}
            
            logger.info(f"OCR extracted {len(ocr_text)} characters")
            
            # Parse the OCR text
            logger.info("Parsing scorecard from OCR text")
            parsed_result = parse_scorecard(ocr_text)
            
            # Validate parsed deliveries
            deliveries = parsed_result.get("deliveries", [])
            is_valid, validation_errors = validate_parsed_deliveries(deliveries)
            
            if not is_valid:
                logger.warning(f"Validation errors: {validation_errors}")
                parsed_result["metadata"]["validation_errors"] = validation_errors
            
            # Add OCR text to metadata (truncate if too long)
            max_ocr_length = 10000
            if len(ocr_text) > max_ocr_length:
                parsed_result["metadata"]["ocr_text"] = ocr_text[:max_ocr_length] + "... (truncated)"
                parsed_result["metadata"]["ocr_text_full_length"] = len(ocr_text)
            else:
                parsed_result["metadata"]["ocr_text"] = ocr_text
            
            # Update upload record
            with SessionLocal() as db:
                upload = db.query(Upload).filter(Upload.id == upload_id).first()
                if upload:
                    upload.parsed_preview = parsed_result
                    upload.status = UploadStatus.ready
                    db.commit()
                    logger.info(f"Upload {upload_id} marked as ready with {len(deliveries)} deliveries")
            
            return {
                "status": "success",
                "upload_id": upload_id,
                "deliveries_found": len(deliveries),
                "confidence": parsed_result["metadata"].get("confidence", 0.0)
            }
            
        except Exception as e:
            error_msg = f"Error processing upload: {str(e)}"
            logger.error(error_msg, exc_info=True)
            _mark_upload_failed(upload_id, error_msg)
            raise


def _mark_upload_failed(upload_id: int, error_message: str) -> None:
    """Mark an upload as failed with an error message."""
    try:
        from backend.sql_app.database import SessionLocal
        from backend.sql_app.models import Upload, UploadStatus
        
        with SessionLocal() as db:
            upload = db.query(Upload).filter(Upload.id == upload_id).first()
            if upload:
                upload.status = UploadStatus.failed
                upload.error_message = error_message
                db.commit()
    except Exception as e:
        logger.error(f"Failed to mark upload as failed: {e}")
