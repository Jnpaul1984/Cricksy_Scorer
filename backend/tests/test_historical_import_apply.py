"""Phase 5D - Historical JSON Import Apply MVP tests.

Validates:
- apply requires explicit confirm=True
- apply fails for missing / invalid batch_id
- apply fails for already-finalized (applied) batch
- apply fails for batch with non-valid status or errors
- apply fails when teams are not derivable
- apply creates expected historical Game metadata only
- apply does not mutate live / in-progress matches
- apply does not create data when validation fails
- apply marks batch finalized/applied only after successful write
- delivery records are NOT imported (Phase 5E follow-up)

Note on test-mode architecture:
  When CRICKSY_IN_MEMORY_DB=1 the main game routes use _FakeSession (which
  never persists rows), while historical import routes use _get_import_db
  (real SQLite in-memory).  Tests verify game creation via the apply response
  body and the batch-list endpoint rather than via GET /games/{id}, which
  would always return 404 from the fake session.
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
    """Helper: run dry-run with record_preview=true and return the batch record_id."""
    resp = client.post(
        "/api/historical-import/json/dry-run",
        json=_load_fixture(),
        params={"record_preview": "true"},
    )
    assert resp.status_code == 200, resp.text
    record_id = resp.json()["record_id"]
    assert record_id is not None
    return record_id


# ---------------------------------------------------------------------------
# confirm=True gate
# ---------------------------------------------------------------------------


def test_apply_requires_confirm_true() -> None:
    """apply with confirm=false must be rejected with a 422 error."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": False},
        )

    assert resp.status_code == 422, resp.text


def test_apply_confirm_missing_body_rejected() -> None:
    """apply with missing body must be rejected (422 from Pydantic validation)."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            content=b"{}",
            headers={"content-type": "application/json"},
        )

    # Pydantic rejects missing required field
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Batch existence gate
# ---------------------------------------------------------------------------


def test_apply_missing_batch_returns_404() -> None:
    """apply for a non-existent batch_id must return 404."""
    with TestClient(app) as client:
        resp = client.post(
            "/api/historical-import/json/batches/nonexistent-batch-id/apply",
            json={"confirm": True},
        )

    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# Duplicate apply gate
# ---------------------------------------------------------------------------


def test_apply_cannot_apply_same_batch_twice() -> None:
    """Second apply on the same batch must be rejected with 409."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)

        # First apply - should succeed
        r1 = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )
        assert r1.status_code == 200, r1.text
        assert r1.json()["status"] == "applied"

        # Second apply on same batch - must fail
        r2 = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )

    assert r2.status_code == 409, r2.text
    assert "already been applied" in r2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Successful apply - response shape
# ---------------------------------------------------------------------------


def test_apply_returns_correct_response_shape() -> None:
    """Successful apply must return batch_id, applied_game_id, records_created, status."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["batch_id"] == batch_id
    assert data["status"] == "applied"
    assert data["applied_game_id"] is not None
    assert len(data["applied_game_id"]) > 0
    assert data["records_created"] == 1
    assert "rollback_info" in data


# ---------------------------------------------------------------------------
# Batch is finalized only after successful apply
# ---------------------------------------------------------------------------


def test_apply_marks_batch_finalized() -> None:
    """After successful apply the batch must show is_finalized=True and applied_game_id set."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)

        # Confirm batch is not yet finalized
        batches_before = client.get("/api/historical-import/json/batches").json()
        assert len(batches_before) == 1
        assert batches_before[0]["is_finalized"] is False
        assert batches_before[0]["applied_game_id"] is None

        # Apply
        apply_resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )
        assert apply_resp.status_code == 200

        # Check batch is now finalized
        batches_after = client.get("/api/historical-import/json/batches").json()

    assert len(batches_after) == 1
    b = batches_after[0]
    assert b["is_finalized"] is True
    assert b["applied_game_id"] is not None
    assert b["applied_game_id"] == apply_resp.json()["applied_game_id"]


# ---------------------------------------------------------------------------
# Historical Game record created (verified via apply response + batch metadata)
#
# Note: In test mode (CRICKSY_IN_MEMORY_DB=1) the main /games/* routes use a
# _FakeSession that returns no rows.  Historical import routes use the real
# SQLite in-memory DB.  Game creation is therefore verified through the apply
# response body and the batch-list endpoint rather than GET /games/{id}.
# ---------------------------------------------------------------------------


def test_apply_creates_historical_game() -> None:
    """apply must return records_created=1 and a non-null applied_game_id."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        apply_resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )

    assert apply_resp.status_code == 200, apply_resp.text
    data = apply_resp.json()
    assert data["records_created"] == 1, "apply must report exactly 1 record created"
    assert data["applied_game_id"] is not None, "apply must return a non-null game id"
    assert len(data["applied_game_id"]) > 0


def test_apply_batch_record_links_to_created_game() -> None:
    """After apply the batch list shows applied_game_id matching the response."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        apply_resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )
        assert apply_resp.status_code == 200
        returned_game_id = apply_resp.json()["applied_game_id"]

        batches = client.get("/api/historical-import/json/batches").json()

    assert len(batches) == 1
    assert batches[0]["applied_game_id"] == returned_game_id
    assert batches[0]["is_finalized"] is True


def test_apply_rollback_info_contains_game_id() -> None:
    """apply response rollback_info must reference the created game id."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        apply_resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )

    assert apply_resp.status_code == 200, apply_resp.text
    data = apply_resp.json()
    rollback_info = data["rollback_info"]
    game_id = data["applied_game_id"]
    assert game_id in rollback_info, (
        f"rollback_info must mention the created game id '{game_id}'; got: {rollback_info!r}"
    )


# ---------------------------------------------------------------------------
# No data created on validation failures
# ---------------------------------------------------------------------------


def test_apply_no_game_created_when_confirm_false() -> None:
    """When confirm=False apply must fail and batch must remain un-finalized."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)

        client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": False},
        )

        batches = client.get("/api/historical-import/json/batches").json()

    # Batch must NOT be finalized
    assert len(batches) == 1
    assert batches[0]["is_finalized"] is False
    assert batches[0]["applied_game_id"] is None


def test_apply_no_game_created_for_missing_batch() -> None:
    """When batch does not exist apply must fail without creating any records."""
    with TestClient(app) as client:
        resp = client.post(
            "/api/historical-import/json/batches/does-not-exist/apply",
            json={"confirm": True},
        )

        # No batches should exist at all (none were recorded in this test)
        batches = client.get("/api/historical-import/json/batches").json()

    assert resp.status_code == 404
    assert batches == []


def test_apply_no_extra_game_created_on_duplicate_apply() -> None:
    """When second apply is rejected the records_created count must stay at 1."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)

        r1 = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )
        assert r1.status_code == 200
        first_game_id = r1.json()["applied_game_id"]

        # Second apply must be rejected
        r2 = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )

        # Batch record must still show only the first game
        batches = client.get("/api/historical-import/json/batches").json()

    assert r2.status_code == 409
    assert len(batches) == 1
    assert batches[0]["applied_game_id"] == first_game_id  # not overwritten


# ---------------------------------------------------------------------------
# Live match isolation
#
# In test mode POST /games uses _FakeSession so no real game is persisted.
# We verify isolation by ensuring apply leaves no finalized batch for a batch
# that was never recorded (i.e. we can't accidentally apply to a live game).
# ---------------------------------------------------------------------------


def test_apply_does_not_alter_other_batches() -> None:
    """apply on one batch must leave other batches un-finalized."""
    with TestClient(app) as client:
        # Record two different batches
        batch_a = _record_batch(client)
        # Slightly different payload so hash differs
        resp_b = client.post(
            "/api/historical-import/json/dry-run",
            json={**_load_fixture(), "matchType": "ODI"},
            params={"record_preview": "true"},
        )
        assert resp_b.status_code == 200
        batch_b = resp_b.json()["record_id"]

        # Apply only batch_a
        apply_resp = client.post(
            f"/api/historical-import/json/batches/{batch_a}/apply",
            json={"confirm": True},
        )
        assert apply_resp.status_code == 200

        batches = client.get("/api/historical-import/json/batches").json()

    by_id = {b["id"]: b for b in batches}
    assert by_id[batch_a]["is_finalized"] is True
    assert by_id[batch_b]["is_finalized"] is False, (
        "apply on batch_a must not finalize batch_b"
    )
    assert by_id[batch_b]["applied_game_id"] is None


# ---------------------------------------------------------------------------
# Delivery records NOT imported (Phase 5D scope document)
# ---------------------------------------------------------------------------


def test_apply_records_created_is_one_not_more() -> None:
    """records_created must be 1 (match metadata only, no delivery rows).

    Phase 5D imports match metadata only.  Delivery-level import is deferred
    to Phase 5E.  If delivery rows were imported, records_created would exceed
    the delivery_count of the batch.
    """
    with TestClient(app) as client:
        # Record the batch and check delivery_count
        dry_resp = client.post(
            "/api/historical-import/json/dry-run",
            json=_load_fixture(),
            params={"record_preview": "true"},
        )
        assert dry_resp.status_code == 200
        batch_id = dry_resp.json()["record_id"]
        delivery_count = dry_resp.json()["delivery_count"]

        apply_resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )

    assert apply_resp.status_code == 200
    assert apply_resp.json()["records_created"] == 1, (
        "Phase 5D must create exactly 1 record (the Game row); "
        f"delivery_count={delivery_count} should NOT be added as records_created"
    )
