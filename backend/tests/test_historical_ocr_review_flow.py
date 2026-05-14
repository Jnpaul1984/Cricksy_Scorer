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
