from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app
from backend.routes.historical_import import PHASE_7_MAX_DOCUMENT_BYTES

FIXTURE_PATH = Path(__file__).resolve().parent / "simulated_t20_match.json"


def _fixture_payload() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _pdf_bytes() -> bytes:
    return b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


def _pdf_with_text_bytes() -> bytes:
    """Build a minimal valid digital PDF that contains extractable text."""
    content_stream = b"BT /F1 12 Tf 72 720 Td (Test scorecard text) Tj ET\n"
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = (
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]"
        b" /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
    )
    obj4 = (
        b"4 0 obj\n<< /Length "
        + str(len(content_stream)).encode()
        + b" >>\nstream\n"
        + content_stream
        + b"endstream\nendobj\n"
    )
    obj5 = b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"

    header = b"%PDF-1.4\n"
    offset = len(header)
    offsets: dict[int, int] = {}
    body = header
    for n, obj in [(1, obj1), (2, obj2), (3, obj3), (4, obj4), (5, obj5)]:
        offsets[n] = offset
        body += obj
        offset += len(obj)

    xref_offset = offset
    xref = b"xref\n0 6\n" + b"0000000000 65535 f \n"
    for i in range(1, 6):
        xref += f"{offsets[i]:010d} 00000 n \n".encode()

    trailer = (
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF\n"
    )
    return body + xref + trailer


def _pdf_without_text_bytes() -> bytes:
    """Build a minimal valid PDF with proper structure but no embedded text (simulates scanned PDF)."""
    obj1 = b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
    obj2 = b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
    obj3 = b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"

    header = b"%PDF-1.4\n"
    offset = len(header)
    offsets: dict[int, int] = {}
    body = header
    for n, obj in [(1, obj1), (2, obj2), (3, obj3)]:
        offsets[n] = offset
        body += obj
        offset += len(obj)

    xref_offset = offset
    xref = b"xref\n0 4\n" + b"0000000000 65535 f \n"
    for i in range(1, 4):
        xref += f"{offsets[i]:010d} 00000 n \n".encode()

    trailer = (
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n"
        + str(xref_offset).encode()
        + b"\n%%EOF\n"
    )
    return body + xref + trailer


def _create_candidate(client: TestClient, candidate_json: dict[str, object]) -> dict[str, object]:
    response = client.post(
        "/api/historical-import/json/ocr-review/candidates",
        files={"file": ("scorecard.pdf", _pdf_bytes(), "application/pdf")},
        data={
            "candidate_json": json.dumps(candidate_json),
            "extraction_method": "manual_candidate_json",
            "extraction_confidence": "0.82",
            "uncertainty_flags": json.dumps(["team_name_low_confidence"]),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_ocr_review_candidate_accepts_valid_pdf_upload() -> None:
    with TestClient(app) as client:
        payload = _create_candidate(client, _fixture_payload())

    assert payload["status"] == "needs_review"
    assert payload["source_document"]["content_type"] == "application/pdf"
    assert "non-authoritative" in payload["extraction"]["non_authoritative_notice"].lower()


def test_ocr_review_candidate_rejects_unsupported_upload_type() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/ocr-review/candidates",
            files={"file": ("scorecard.txt", b"not-a-document", "text/plain")},
        )

    assert response.status_code == 415, response.text


def test_ocr_review_candidate_rejects_oversized_payload() -> None:
    oversized = b"0" * (PHASE_7_MAX_DOCUMENT_BYTES + 1)

    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/ocr-review/candidates",
            files={"file": ("scorecard.pdf", oversized, "application/pdf")},
        )

    assert response.status_code == 413, response.text


def test_ocr_review_candidate_rejects_malformed_uncertainty_flags() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/ocr-review/candidates",
            files={"file": ("scorecard.pdf", _pdf_bytes(), "application/pdf")},
            data={
                "candidate_json": json.dumps(_fixture_payload()),
                "uncertainty_flags": "{not-json",
            },
        )

    assert response.status_code == 422, response.text
    assert "uncertainty_flags" in response.json()["detail"]


def test_ocr_review_candidate_create_does_not_create_official_match_data() -> None:
    with TestClient(app) as client:
        before = client.get("/games/results")
        assert before.status_code == 200, before.text
        before_count = len(before.json())

        _create_candidate(client, _fixture_payload())

        after = client.get("/games/results")
        assert after.status_code == 200, after.text
        after_count = len(after.json())

    assert before_count == after_count


def test_ocr_review_correction_updates_reviewed_json() -> None:
    with TestClient(app) as client:
        created = _create_candidate(client, _fixture_payload())
        candidate_id = created["candidate_id"]
        reviewed_json = _fixture_payload()
        reviewed_json["matchType"] = "T20"
        response = client.patch(
            f"/api/historical-import/json/ocr-review/candidates/{candidate_id}/review",
            json={
                "reviewed_json": reviewed_json,
                "reviewer_notes": "Corrected OCR team labels.",
                "uncertainty_flags": ["batting_order_uncertain"],
            },
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "ready_for_dry_run"
    assert data["reviewed_json"]["matchType"] == "T20"
    assert "batting_order_uncertain" in data["extraction"]["uncertainty_flags"]


def test_ocr_review_dry_run_passes_and_creates_handoff_batch() -> None:
    with TestClient(app) as client:
        before_games = client.get("/games/results")
        assert before_games.status_code == 200, before_games.text
        before_count = len(before_games.json())

        created = _create_candidate(client, _fixture_payload())
        candidate_id = created["candidate_id"]
        review_resp = client.patch(
            f"/api/historical-import/json/ocr-review/candidates/{candidate_id}/review",
            json={"reviewed_json": _fixture_payload(), "uncertainty_flags": []},
        )
        assert review_resp.status_code == 200, review_resp.text

        dry_run_resp = client.post(
            f"/api/historical-import/json/ocr-review/candidates/{candidate_id}/dry-run",
            json={"record_preview": True},
        )

        after_games = client.get("/games/results")

    assert dry_run_resp.status_code == 200, dry_run_resp.text
    data = dry_run_resp.json()
    assert data["status"] == "dry_run_passed"
    assert data["dry_run_result"]["status"] == "valid"
    assert data["dry_run_batch_id"] is not None
    assert after_games.status_code == 200
    assert len(after_games.json()) == before_count


def test_ocr_review_dry_run_failed_returns_validation_errors() -> None:
    invalid_candidate = {
        "info": {"teams": ["A", "B"], "match_type": "T20"},
        "innings": [{"team": "A", "overs": "not-a-list"}],
    }
    with TestClient(app) as client:
        created = _create_candidate(client, invalid_candidate)
        candidate_id = created["candidate_id"]
        review_resp = client.patch(
            f"/api/historical-import/json/ocr-review/candidates/{candidate_id}/review",
            json={"reviewed_json": invalid_candidate, "uncertainty_flags": []},
        )
        assert review_resp.status_code == 200, review_resp.text

        dry_run_resp = client.post(
            f"/api/historical-import/json/ocr-review/candidates/{candidate_id}/dry-run",
            json={"record_preview": True},
        )

    assert dry_run_resp.status_code == 200, dry_run_resp.text
    payload = dry_run_resp.json()
    assert payload["status"] == "dry_run_failed"
    assert payload["dry_run_result"]["status"] != "valid"
    assert payload["dry_run_result"]["errors"]


def test_rejected_ocr_review_candidate_cannot_run_dry_run() -> None:
    with TestClient(app) as client:
        created = _create_candidate(client, _fixture_payload())
        candidate_id = created["candidate_id"]
        reject_resp = client.post(
            f"/api/historical-import/json/ocr-review/candidates/{candidate_id}/reject",
            json={"reason": "Document too blurry to verify scorecard totals."},
        )
        assert reject_resp.status_code == 200, reject_resp.text

        dry_run_resp = client.post(
            f"/api/historical-import/json/ocr-review/candidates/{candidate_id}/dry-run",
            json={"record_preview": True},
        )

    assert dry_run_resp.status_code == 409, dry_run_resp.text


# ---------------------------------------------------------------------------
# Phase 7C — PDF text extraction tests
# ---------------------------------------------------------------------------


def test_pdf_text_extraction_creates_candidate_with_extracted_text() -> None:
    """Valid digital PDF + extraction_method=pdf_text_extract populates ocr_text."""
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/ocr-review/candidates",
            files={"file": ("scorecard.pdf", _pdf_with_text_bytes(), "application/pdf")},
            data={"extraction_method": "pdf_text_extract"},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["extraction"]["method"] == "pdf_text_extract"
    assert data["extraction"]["confidence"] == 1.0
    assert data["extraction"]["ocr_text"] is not None
    assert "Test scorecard text" in data["extraction"]["ocr_text"]
    assert data["extraction"]["uncertainty_flags"] == []
    # Extraction produces non-empty ocr_text → status escalates to needs_review
    assert data["status"] == "needs_review"
    # Non-authoritative notice must be present
    assert "non-authoritative" in data["extraction"]["non_authoritative_notice"].lower()


def test_pdf_with_no_extractable_text_creates_candidate_with_fallback_state() -> None:
    """Valid PDF with no text layer → candidate created with scanned_pdf_no_text flag."""
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/ocr-review/candidates",
            files={"file": ("scorecard.pdf", _pdf_without_text_bytes(), "application/pdf")},
            data={"extraction_method": "pdf_text_extract"},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["extraction"]["method"] == "pdf_text_extract"
    assert data["extraction"]["confidence"] == 0.0
    assert data["extraction"]["ocr_text"] is None
    assert "scanned_pdf_no_text" in data["extraction"]["uncertainty_flags"]
    # No text extracted; candidate remains in uploaded state (no ocr_text or candidate_json)
    assert data["status"] == "uploaded"
    assert "non-authoritative" in data["extraction"]["non_authoritative_notice"].lower()


def test_corrupt_pdf_is_handled_safely_with_fallback_state() -> None:
    """Corrupt/invalid PDF bytes are handled gracefully; candidate is still created."""
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/ocr-review/candidates",
            files={"file": ("scorecard.pdf", b"not-a-valid-pdf", "application/pdf")},
            data={"extraction_method": "pdf_text_extract"},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["extraction"]["method"] == "pdf_text_extract"
    assert data["extraction"]["confidence"] == 0.0
    assert data["extraction"]["ocr_text"] is None
    # Either extraction_failed or scanned_pdf_no_text; both are valid fallback indicators
    assert data["extraction"]["uncertainty_flags"]
    assert data["status"] in ("uploaded", "needs_review")


def test_image_upload_does_not_invoke_pdf_text_extraction() -> None:
    """Non-PDF image upload with extraction_method=pdf_text_extract skips PDF extraction."""
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64  # minimal PNG-like header
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/ocr-review/candidates",
            files={"file": ("scorecard.png", png_bytes, "image/png")},
            data={"extraction_method": "pdf_text_extract"},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    # Image uploads must not trigger PDF extraction; extraction method is stored as-is
    # but no auto-populated ocr_text from pdfplumber
    assert data["extraction"]["method"] == "pdf_text_extract"
    assert data["extraction"]["ocr_text"] is None
    assert data["extraction"]["confidence"] is None


def test_pdf_text_extraction_does_not_create_official_match_data() -> None:
    """Uploading a text-extractable PDF must not create any official game rows."""
    with TestClient(app) as client:
        before = client.get("/games/results")
        assert before.status_code == 200, before.text
        before_count = len(before.json())

        client.post(
            "/api/historical-import/json/ocr-review/candidates",
            files={"file": ("scorecard.pdf", _pdf_with_text_bytes(), "application/pdf")},
            data={"extraction_method": "pdf_text_extract"},
        )

        after = client.get("/games/results")
        assert after.status_code == 200, after.text

    assert len(after.json()) == before_count


def test_candidate_with_extracted_text_still_requires_human_review() -> None:
    """Even after successful text extraction, candidate status must be needs_review (not applied)."""
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/ocr-review/candidates",
            files={"file": ("scorecard.pdf", _pdf_with_text_bytes(), "application/pdf")},
            data={"extraction_method": "pdf_text_extract"},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    # Must still be at a human-review stage, not applied
    assert data["status"] not in (
        "applied_via_structured_import_only",
        "dry_run_passed",
        "ready_for_dry_run",
    )
    assert data["reviewed_json"] is None


def test_existing_dry_run_handoff_unchanged_after_phase_7c() -> None:
    """Dry-run handoff path continues to work as before Phase 7C changes."""
    with TestClient(app) as client:
        created = _create_candidate(client, _fixture_payload())
        candidate_id = created["candidate_id"]

        review_resp = client.patch(
            f"/api/historical-import/json/ocr-review/candidates/{candidate_id}/review",
            json={"reviewed_json": _fixture_payload(), "uncertainty_flags": []},
        )
        assert review_resp.status_code == 200, review_resp.text

        dry_run_resp = client.post(
            f"/api/historical-import/json/ocr-review/candidates/{candidate_id}/dry-run",
            json={"record_preview": True},
        )

    assert dry_run_resp.status_code == 200, dry_run_resp.text
    result = dry_run_resp.json()
    assert result["status"] == "dry_run_passed"
    assert result["dry_run_batch_id"] is not None

