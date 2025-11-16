"""OCR-based scorecard parsing using Tesseract (prototype).

This is a prototype implementation. In production, you would:
- Use more sophisticated image preprocessing
- Implement better text parsing with NLP/regex patterns
- Add confidence scoring and validation
- Handle multiple scorecard formats
"""
from __future__ import annotations

import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger(__name__)


def parse_scorecard_image(upload_id: str) -> dict[str, Any]:
    """
    Parse scorecard image using OCR.

    This is a PROTOTYPE implementation that:
    1. Downloads image from S3/MinIO
    2. Runs Tesseract OCR to extract text
    3. Attempts basic parsing of the extracted text
    4. Returns structured data (very basic format)

    In production, this would:
    - Use advanced image preprocessing (deskew, denoise, etc.)
    - Apply NLP/ML models for entity extraction
    - Support multiple scorecard formats
    - Validate extracted data against cricket rules
    - Provide confidence scores

    Args:
        upload_id: UUID of the upload to process

    Returns:
        dict with parsed scorecard data

    Raises:
        RuntimeError: If OCR fails or dependencies missing
    """
    try:
        import pytesseract
        from PIL import Image
    except ImportError as e:
        raise RuntimeError(
            "OCR dependencies not available. Install with: "
            "pip install pytesseract pillow\n"
            "Also ensure Tesseract is installed on system."
        ) from e

    # Get upload details from database
    upload = _get_upload_from_db(upload_id)
    if not upload:
        raise ValueError(f"Upload {upload_id} not found")

    # Download image from S3/MinIO
    image_path = _download_image(upload["s3_bucket"], upload["s3_key"])

    try:
        # Load image
        image = Image.open(image_path)

        # Run OCR
        logger.info(f"Running OCR on {image_path}")
        text = pytesseract.image_to_string(image, lang="eng")

        logger.info(f"Extracted text ({len(text)} chars)")
        logger.debug(f"OCR text:\n{text[:500]}")

        # Parse the text (VERY BASIC - prototype level)
        parsed_data = _parse_scorecard_text(text)

        # Add metadata
        parsed_data["_metadata"] = {
            "upload_id": upload_id,
            "raw_text_preview": text[:500],
            "confidence": "low",  # Prototype has low confidence
            "parser_version": "0.1.0-prototype",
        }

        return parsed_data

    finally:
        # Clean up temp file
        if os.path.exists(image_path):
            os.unlink(image_path)


def _get_upload_from_db(upload_id: str) -> dict[str, Any] | None:
    """Get upload details from database."""
    import uuid

    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from backend.sql_app.models.upload import Upload

    # Get database URL
    db_url = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/cricksy_scorer")
    if "asyncpg" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    engine = create_engine(db_url)

    with Session(engine) as session:
        stmt = select(Upload).where(Upload.id == uuid.UUID(upload_id))
        result = session.execute(stmt)
        upload = result.scalar_one_or_none()

        if not upload:
            return None

        return {
            "id": str(upload.id),
            "filename": upload.filename,
            "s3_bucket": upload.s3_bucket,
            "s3_key": upload.s3_key,
        }


def _download_image(bucket: str, key: str) -> str:
    """
    Download image from S3/MinIO to temporary file.

    Args:
        bucket: S3 bucket name
        key: Object key

    Returns:
        Path to downloaded temporary file
    """
    try:
        from backend.utils.s3 import _get_s3_client
    except ImportError:
        # Fallback: create placeholder for testing
        logger.warning("S3 client not available, using placeholder")
        # Create a simple test image
        from PIL import Image

        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
        img = Image.new("RGB", (200, 100), color="white")
        img.save(temp_file.name)
        return temp_file.name

    s3_client = _get_s3_client()
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    logger.info(f"Downloading s3://{bucket}/{key} to {temp_file.name}")
    s3_client.download_file(bucket, key, temp_file.name)

    return temp_file.name


def _parse_scorecard_text(text: str) -> dict[str, Any]:
    """
    Parse OCR text into structured scorecard data.

    This is a PROTOTYPE implementation with very basic parsing.
    A production version would use:
    - Regular expressions for common patterns
    - NLP entity recognition
    - ML models trained on scorecard formats
    - Validation against cricket rules

    Args:
        text: Raw OCR text

    Returns:
        dict with parsed data (basic structure)
    """
    # For now, return a basic structure with placeholder data
    # A real implementation would parse team names, scores, players, etc.

    lines = [line.strip() for line in text.split("\n") if line.strip()]

    # Try to extract basic information (very naive)
    parsed = {
        "format": "unknown",
        "teams": [],
        "innings": [],
        "raw_lines": lines[:20],  # Include first 20 lines for manual review
        "parse_notes": [
            "PROTOTYPE: Manual verification required",
            "This is a basic OCR extraction",
            "Please review and edit all fields before applying",
        ],
    }

    # Try to detect team names (look for "vs" or "v")
    for line in lines[:10]:
        lower = line.lower()
        if " vs " in lower or " v " in lower:
            parts = [p.strip() for p in line.replace(" vs ", "|").replace(" v ", "|").split("|")]
            if len(parts) == 2:
                parsed["teams"] = [{"name": parts[0]}, {"name": parts[1]}]
                break

    # Try to detect scores (look for numbers with slashes like "250/8")
    import re

    score_pattern = r"(\d{1,3})/(\d{1,2})"
    for line in lines:
        match = re.search(score_pattern, line)
        if match:
            runs, wickets = match.groups()
            parsed["innings"].append(
                {
                    "runs": int(runs),
                    "wickets": int(wickets),
                    "confidence": "low",
                    "source_line": line,
                }
            )

    return parsed
