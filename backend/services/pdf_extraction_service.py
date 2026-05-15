"""Phase 7C — optional PDF text extraction service.

Extracts embedded text from digitally-generated PDFs using pdfplumber.
Output is non-authoritative — feeds OCR review candidate metadata only.

Image OCR is NOT performed. Scanned PDFs return a graceful fallback state.

Allowed flow:
    PDF upload
    → optional PDF text extraction (this module)
    → OCR/review candidate text + metadata (non-authoritative)
    → human review/correction
    → structured JSON candidate
    → existing historical JSON dry-run validation
    → explicit apply through existing governed path only

Forbidden flow:
    PDF text extraction → official match data directly
"""

from __future__ import annotations

import io
import logging

logger = logging.getLogger(__name__)

# pdfplumber is an optional dependency; fail gracefully if not installed.
try:
    import pdfplumber  # type: ignore[import-untyped]

    _PDFPLUMBER_AVAILABLE = True
except ImportError:
    _PDFPLUMBER_AVAILABLE = False


class PdfExtractionResult:
    """Result of a PDF text extraction attempt.

    This is non-authoritative metadata for OCR review candidates only.
    It must never be used to create or mutate official match truth.
    """

    __slots__ = ("confidence", "extracted_text", "method", "uncertainty_flags", "warnings")

    def __init__(
        self,
        *,
        extracted_text: str | None,
        confidence: float,
        uncertainty_flags: list[str],
        warnings: list[str],
        method: str,
    ) -> None:
        self.extracted_text = extracted_text
        self.confidence = confidence
        self.uncertainty_flags = list(uncertainty_flags)
        self.warnings = list(warnings)
        self.method = method


def extract_text_from_pdf(payload: bytes) -> PdfExtractionResult:
    """Attempt to extract embedded text from a digitally generated PDF.

    This performs text-layer extraction only — no image OCR is performed.
    If the PDF is a scanned image (no embedded text layer), extraction
    returns an empty result with the ``scanned_pdf_no_text`` uncertainty flag.

    Returns a :class:`PdfExtractionResult` regardless of whether extraction
    succeeds or fails. Never raises — all errors are caught and reported
    as fallback state so the caller can always create an OCR review candidate.

    Args:
        payload: Raw PDF bytes.

    Returns:
        A :class:`PdfExtractionResult` with extracted text (or ``None``) and
        metadata describing the extraction outcome.
    """
    if not _PDFPLUMBER_AVAILABLE:
        return PdfExtractionResult(
            extracted_text=None,
            confidence=0.0,
            uncertainty_flags=["pdf_extraction_unavailable"],
            warnings=["pdfplumber is not installed; PDF text extraction is unavailable."],
            method="pdf_text_extract",
        )

    try:
        extracted_pages: list[str] = []
        with pdfplumber.open(io.BytesIO(payload)) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    extracted_pages.append(page_text.strip())
    except Exception as exc:
        logger.warning("PDF text extraction failed: %s", exc)
        return PdfExtractionResult(
            extracted_text=None,
            confidence=0.0,
            uncertainty_flags=["extraction_failed"],
            warnings=[f"PDF text extraction failed: {exc!s}"],
            method="pdf_text_extract",
        )

    if not extracted_pages:
        return PdfExtractionResult(
            extracted_text=None,
            confidence=0.0,
            uncertainty_flags=["scanned_pdf_no_text"],
            warnings=[
                "PDF contains no extractable text layer. "
                "This is likely a scanned image PDF. "
                "Image OCR is not performed — please enter the scorecard JSON manually."
            ],
            method="pdf_text_extract",
        )

    full_text = "\n\n".join(extracted_pages)
    return PdfExtractionResult(
        extracted_text=full_text,
        confidence=1.0,
        uncertainty_flags=[],
        warnings=[],
        method="pdf_text_extract",
    )
