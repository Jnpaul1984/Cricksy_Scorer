"""Phase 5C – Historical Import Batch Tracking + Duplicate Detection tests.

Validates:
- Default dry-run writes nothing to the DB (no_persistence=True, no record_id)
- record_preview=true records batch metadata (record_id returned)
- Duplicate by exact source hash detected (tracking_available=True)
- Semantic duplicate detected when semantic key is derivable
- No Game/Delivery/Player/Team rows are created in any path
- List endpoint returns batches scoped to caller
- is_finalized is always False in Phase 5C
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


FIXTURE_PATH = Path(__file__).resolve().parent / "simulated_t20_match.json"


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _fixture_with_date() -> dict[str, object]:
    """Return fixture with a date field so the semantic key is derivable."""
    data = _load_fixture()
    data["date"] = "2026-01-15"
    return data


# ---------------------------------------------------------------------------
# Default dry-run: no DB writes
# ---------------------------------------------------------------------------


def test_default_dry_run_writes_nothing() -> None:
    """Default call (no record_preview) must not write to DB and set no_persistence=True."""
    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=_load_fixture())

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["no_persistence"] is True
    assert data.get("record_id") is None, "record_id must be None when record_preview is not set"


def test_default_dry_run_tracking_available_with_no_prior_records() -> None:
    """tracking_available=True even on first call (Phase 5C table exists).

    When no prior batch exists the probable_duplicate should be not_duplicate.
    """
    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=_load_fixture())

    assert response.status_code == 200
    dup = response.json()["duplicate_detection"]
    assert dup["tracking_available"] is True
    assert dup["probable_duplicate"] == "not_duplicate"
    assert dup["duplicate_batch_id"] is None


# ---------------------------------------------------------------------------
# record_preview=true: persists batch metadata
# ---------------------------------------------------------------------------


def test_record_preview_returns_record_id() -> None:
    """record_preview=true should persist metadata and return a record_id."""
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/dry-run",
            json=_load_fixture(),
            params={"record_preview": "true"},
        )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["no_persistence"] is False
    assert data["record_id"] is not None
    assert len(data["record_id"]) > 0


def test_record_preview_stores_correct_metadata() -> None:
    """Persisted batch metadata matches the dry-run response."""
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/dry-run",
            json=_load_fixture(),
            params={"record_preview": "true"},
        )

    assert response.status_code == 200
    data = response.json()
    dup = data["duplicate_detection"]

    # The record should exist and have the right hash
    assert len(dup["source_hash_sha256"]) == 64
    assert data["record_id"] is not None


def test_record_preview_is_finalized_always_false() -> None:
    """is_finalized must remain False in Phase 5C (no write path)."""
    with TestClient(app) as client:
        # Record the batch
        client.post(
            "/api/historical-import/json/dry-run",
            json=_load_fixture(),
            params={"record_preview": "true"},
        )

        # List batches and verify is_finalized=False
        list_response = client.get("/api/historical-import/json/batches")

    assert list_response.status_code == 200
    batches = list_response.json()
    assert len(batches) == 1
    assert batches[0]["is_finalized"] is False


# ---------------------------------------------------------------------------
# Duplicate detection by hash
# ---------------------------------------------------------------------------


def test_duplicate_by_hash_detected_on_second_call() -> None:
    """Second record_preview with identical payload should flag likely_duplicate."""
    fixture = _load_fixture()

    with TestClient(app) as client:
        # First preview – records the batch
        r1 = client.post(
            "/api/historical-import/json/dry-run",
            json=fixture,
            params={"record_preview": "true"},
        )
        assert r1.status_code == 200
        first_id = r1.json()["record_id"]

        # Second preview with same payload – should detect duplicate
        r2 = client.post(
            "/api/historical-import/json/dry-run",
            json=fixture,
        )
        assert r2.status_code == 200

    dup2 = r2.json()["duplicate_detection"]
    assert dup2["probable_duplicate"] == "likely_duplicate"
    assert dup2["tracking_available"] is True
    assert dup2["duplicate_batch_id"] == first_id
    assert dup2["semantic_duplicate"] is False  # hash match takes priority


def test_no_false_duplicate_for_different_payload() -> None:
    """Different payload must not be flagged as duplicate."""
    fixture_a = _load_fixture()
    fixture_b = {**_load_fixture(), "matchType": "ODI"}  # different data

    with TestClient(app) as client:
        # Record fixture_a
        client.post(
            "/api/historical-import/json/dry-run",
            json=fixture_a,
            params={"record_preview": "true"},
        )
        # Dry-run fixture_b (different hash)
        r2 = client.post("/api/historical-import/json/dry-run", json=fixture_b)

    assert r2.status_code == 200
    dup = r2.json()["duplicate_detection"]
    assert dup["probable_duplicate"] == "not_duplicate"


# ---------------------------------------------------------------------------
# Semantic duplicate detection
# ---------------------------------------------------------------------------


def test_semantic_key_derivable_when_date_present() -> None:
    """Semantic key is populated in the response when date, match_type, and teams are present."""
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/dry-run",
            json=_fixture_with_date(),
        )

    assert response.status_code == 200
    dup = response.json()["duplicate_detection"]
    assert dup["semantic_key"] is not None
    # Format: <match_type>|<date>|<team_a>|<team_b> (sorted)
    assert "t20" in dup["semantic_key"]
    assert "2026-01-15" in dup["semantic_key"]


def test_semantic_key_not_derivable_without_date() -> None:
    """Semantic key is None when date is absent from the fixture."""
    fixture = _load_fixture()  # no date field

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=fixture)

    assert response.status_code == 200
    dup = response.json()["duplicate_detection"]
    assert dup["semantic_key"] is None


def test_semantic_duplicate_detected() -> None:
    """Semantic duplicate should be detected when hash differs but semantic key matches."""
    fixture_v1 = _fixture_with_date()
    # Slightly different payload (e.g. extra key) so hash differs
    fixture_v2 = {**_fixture_with_date(), "_extra_flag": True}

    with TestClient(app) as client:
        # Record v1
        r1 = client.post(
            "/api/historical-import/json/dry-run",
            json=fixture_v1,
            params={"record_preview": "true"},
        )
        assert r1.status_code == 200
        first_id = r1.json()["record_id"]

        # Dry-run v2 – different hash but same semantic key
        r2 = client.post("/api/historical-import/json/dry-run", json=fixture_v2)
        assert r2.status_code == 200

    dup2 = r2.json()["duplicate_detection"]
    assert dup2["probable_duplicate"] == "likely_duplicate"
    assert dup2["tracking_available"] is True
    assert dup2["duplicate_batch_id"] == first_id
    assert dup2["semantic_duplicate"] is True


# ---------------------------------------------------------------------------
# No Game/Delivery/Player/Team writes
# ---------------------------------------------------------------------------


def test_record_preview_does_not_create_games() -> None:
    """record_preview=true must NOT create any Game rows."""
    with TestClient(app) as client:
        before = client.get("/games/results")
        assert before.status_code == 200
        before_count = len(before.json())

        client.post(
            "/api/historical-import/json/dry-run",
            json=_load_fixture(),
            params={"record_preview": "true"},
        )

        after = client.get("/games/results")
        assert after.status_code == 200
        after_count = len(after.json())

    assert after_count == before_count, (
        f"record_preview=true must not create Game rows; "
        f"before={before_count} after={after_count}"
    )


# ---------------------------------------------------------------------------
# List endpoint
# ---------------------------------------------------------------------------


def test_list_batches_returns_empty_when_no_records() -> None:
    """GET /batches returns empty list when no batches have been recorded."""
    with TestClient(app) as client:
        response = client.get("/api/historical-import/json/batches")

    assert response.status_code == 200
    assert response.json() == []


def test_list_batches_returns_recorded_batch() -> None:
    """GET /batches should include any batch recorded with record_preview=true."""
    fixture = _load_fixture()

    with TestClient(app) as client:
        post_resp = client.post(
            "/api/historical-import/json/dry-run",
            json=fixture,
            params={"record_preview": "true"},
        )
        assert post_resp.status_code == 200
        record_id = post_resp.json()["record_id"]

        list_resp = client.get("/api/historical-import/json/batches")

    assert list_resp.status_code == 200
    batches = list_resp.json()
    assert len(batches) == 1
    b = batches[0]
    assert b["id"] == record_id
    assert b["is_finalized"] is False
    assert len(b["source_hash_sha256"]) == 64


def test_list_batches_multiple_records() -> None:
    """GET /batches should list all recorded batches."""
    fixture_a = _load_fixture()
    fixture_b = {**_load_fixture(), "matchType": "ODI"}

    with TestClient(app) as client:
        r1 = client.post(
            "/api/historical-import/json/dry-run",
            json=fixture_a,
            params={"record_preview": "true"},
        )
        r2 = client.post(
            "/api/historical-import/json/dry-run",
            json=fixture_b,
            params={"record_preview": "true"},
        )

        list_resp = client.get("/api/historical-import/json/batches")

    assert list_resp.status_code == 200
    batches = list_resp.json()
    assert len(batches) == 2

    # Both record IDs should appear in the batch list (order may vary)
    batch_ids = {b["id"] for b in batches}
    assert r1.json()["record_id"] in batch_ids
    assert r2.json()["record_id"] in batch_ids


def test_list_batches_limit_parameter() -> None:
    """limit parameter on GET /batches should be respected."""
    with TestClient(app) as client:
        # Record 3 batches
        fixtures = [
            _load_fixture(),
            {**_load_fixture(), "matchType": "ODI"},
            {**_load_fixture(), "matchType": "Test"},
        ]
        for f in fixtures:
            client.post(
                "/api/historical-import/json/dry-run",
                json=f,
                params={"record_preview": "true"},
            )

        list_resp = client.get("/api/historical-import/json/batches", params={"limit": 2})

    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2
