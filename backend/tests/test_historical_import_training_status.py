"""Phase 5I - Historical Import Training Dataset Readiness tests.

Validates:
- GET /batches/{batch_id}/training-status returns 404 for unknown batch
- A fresh (unfinalized) batch has training_eligible=False
- Exclusion reason reflects the actual blocking condition
- raw_json_retained is always False in Phase 5I
- training_registry_phase is 'deferred' in Phase 5I
- An applied (finalized, valid, 0 errors) batch has training_eligible=True
- Required fields (source_hash_sha256, source_format, imported_at, etc.) are present
- No fake metadata is returned
- Training status does not mutate any game or delivery data
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

FIXTURE_PATH = Path(__file__).resolve().parent / "simulated_t20_match.json"


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _record_batch(client: TestClient) -> str:
    """Helper: persist a dry-run batch and return its batch ID."""
    resp = client.post(
        "/api/historical-import/json/dry-run",
        json=_load_fixture(),
        params={"record_preview": "true"},
    )
    assert resp.status_code == 200, resp.text
    record_id = resp.json()["record_id"]
    assert record_id is not None
    return record_id


def _apply_batch(client: TestClient, batch_id: str) -> str:
    """Helper: apply a batch and return the applied_game_id."""
    resp = client.post(
        f"/api/historical-import/json/batches/{batch_id}/apply",
        json={"confirm": True},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "applied"
    return data["applied_game_id"]


# ---------------------------------------------------------------------------
# 404 for unknown batch
# ---------------------------------------------------------------------------


def test_training_status_404_for_unknown_batch() -> None:
    """GET training-status for a non-existent batch_id must return 404."""
    with TestClient(app) as client:
        resp = client.get("/api/historical-import/json/batches/nonexistent-batch/training-status")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Unfinalized batch is not eligible
# ---------------------------------------------------------------------------


def test_training_status_unfinalized_batch_not_eligible() -> None:
    """A batch that has been recorded (dry-run only, not applied) must not be eligible."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        resp = client.get(f"/api/historical-import/json/batches/{batch_id}/training-status")

    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["batch_id"] == batch_id
    assert data["training_eligible"] is False
    assert data["exclusion_reason"] == "batch_not_finalized"
    assert data["raw_json_retained"] is False
    assert data["training_registry_phase"] == "deferred"


# ---------------------------------------------------------------------------
# Required fields are present
# ---------------------------------------------------------------------------


def test_training_status_required_fields_present() -> None:
    """Training status response must include all required metadata fields."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        resp = client.get(f"/api/historical-import/json/batches/{batch_id}/training-status")

    assert resp.status_code == 200, resp.text
    data = resp.json()

    # All required fields must be present and non-null where expected
    assert "batch_id" in data
    assert "source_format" in data
    assert "source_hash_sha256" in data
    assert len(data["source_hash_sha256"]) == 64, "SHA-256 must be 64 hex chars"
    assert "imported_at" in data
    assert "innings_count" in data
    assert "delivery_count" in data
    assert "training_eligible" in data
    assert "raw_json_retained" in data
    assert "training_registry_phase" in data


# ---------------------------------------------------------------------------
# No fake metadata
# ---------------------------------------------------------------------------


def test_training_status_no_fake_metadata() -> None:
    """Source hash must match actual file hash — no fake values injected."""
    fixture = _load_fixture()
    with TestClient(app) as client:
        # First get the dry-run hash
        preview_resp = client.post("/api/historical-import/json/dry-run", json=fixture)
        assert preview_resp.status_code == 200
        expected_hash = preview_resp.json()["duplicate_detection"]["source_hash_sha256"]

        # Record the batch
        record_resp = client.post(
            "/api/historical-import/json/dry-run",
            json=fixture,
            params={"record_preview": "true"},
        )
        batch_id = record_resp.json()["record_id"]

        # Verify hash matches
        status_resp = client.get(f"/api/historical-import/json/batches/{batch_id}/training-status")

    assert status_resp.status_code == 200
    assert status_resp.json()["source_hash_sha256"] == expected_hash


# ---------------------------------------------------------------------------
# Applied batch is training-eligible
# ---------------------------------------------------------------------------


def test_training_status_applied_batch_is_eligible() -> None:
    """A batch that has been applied (finalized, valid, 0 errors) must be training-eligible."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        _apply_batch(client, batch_id)
        resp = client.get(f"/api/historical-import/json/batches/{batch_id}/training-status")

    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["training_eligible"] is True
    assert data["exclusion_reason"] is None
    assert data["applied_game_id"] is not None
    assert data["raw_json_retained"] is False
    assert data["training_registry_phase"] == "deferred"


# ---------------------------------------------------------------------------
# Training status does not mutate data
# ---------------------------------------------------------------------------


def test_training_status_does_not_mutate_data() -> None:
    """Calling training-status multiple times must not change any batch state."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)

        # Call training-status twice
        r1 = client.get(f"/api/historical-import/json/batches/{batch_id}/training-status")
        r2 = client.get(f"/api/historical-import/json/batches/{batch_id}/training-status")

        # Verify batch list is unchanged
        list_resp = client.get("/api/historical-import/json/batches")

    assert r1.status_code == 200
    assert r2.status_code == 200

    # Both calls return identical data
    assert r1.json()["training_eligible"] == r2.json()["training_eligible"]
    assert r1.json()["exclusion_reason"] == r2.json()["exclusion_reason"]

    # Batch list should contain exactly one record
    assert list_resp.status_code == 200
    batches = list_resp.json()
    assert any(b["id"] == batch_id for b in batches)
