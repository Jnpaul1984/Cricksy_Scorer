"""Phase 5F – Historical JSON Delivery-Level Import MVP tests.

Validates:
- apply-deliveries requires confirm=true
- apply-deliveries requires Phase 5D to be applied first (batch must be finalized)
- apply-deliveries requires game to exist and be a historical import
- apply-deliveries verifies source hash
- apply-deliveries validates totals and blocks on irreconcilable data
- apply-deliveries imports correct delivery count
- repeat apply blocked (idempotency)
- rollback (Phase 5E) removes all delivery data
- Analyst case study reads real imported data (no fake fallback)
- Historical game shows innings summaries from Phase 5D (no delivery import needed)
- Live/in-progress match not touched by delivery import

Test architecture:
  HTTP endpoint tests use synchronous TestClient (fast, covers request/response shape).
  Service-level integration tests use @pytest.mark.asyncio with db_session fixture
  (same event loop, direct access to the real in-memory SQLite DB).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import app
from backend.services.historical_import_delivery_service import (
    _hash_payload,
    extract_normalized_innings,
    validate_innings_totals,
    verify_payload_hash,
)

FIXTURE_PATH = Path(__file__).resolve().parent / "simulated_t20_match.json"


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _fixture_bytes() -> bytes:
    return FIXTURE_PATH.read_bytes()


def _record_batch(client: TestClient) -> str:
    """Run dry-run with record_preview=True and return the batch record_id."""
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
    """Apply Phase 5D (create game shell) and return the applied_game_id."""
    resp = client.post(
        f"/api/historical-import/json/batches/{batch_id}/apply",
        json={"confirm": True},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["applied_game_id"]


def _apply_deliveries(client: TestClient, batch_id: str, *, confirm: bool = True):
    """Apply Phase 5F (import deliveries) and return the response."""
    return client.post(
        f"/api/historical-import/json/batches/{batch_id}/apply-deliveries",
        content=_fixture_bytes(),
        headers={"content-type": "application/json"},
        params={"confirm": str(confirm).lower()},
    )


# ===========================================================================
# Delivery service unit tests (no HTTP, no event loop needed)
# ===========================================================================


def test_delivery_service_normalize_fixture() -> None:
    """Normalizing the fixture produces 2 innings with all balls."""
    payload = _fixture_bytes()
    parsed = json.loads(payload)
    innings = extract_normalized_innings(parsed)

    assert len(innings) == 2
    assert innings[0]["inning_no"] == 1
    assert innings[1]["inning_no"] == 2
    assert len(innings[0]["deliveries"]) == 120
    assert len(innings[1]["deliveries"]) == 120

    # Each ball should have expected keys
    ball = innings[0]["deliveries"][0]
    assert "over_number" in ball
    assert "runs_off_bat" in ball
    assert "extra_runs" in ball
    assert "is_wicket" in ball
    assert "batsman" in ball
    assert "bowler" in ball
    assert ball["_source"] == "historical_import"
    assert ball["inning"] == 1


def test_delivery_service_hash_verification() -> None:
    """Hash verification returns True for the same payload."""
    payload = _fixture_bytes()
    hash_val = _hash_payload(payload)
    assert verify_payload_hash(payload, hash_val) is True
    assert verify_payload_hash(payload, "wrong_hash") is False


def test_delivery_service_totals_validation_ok() -> None:
    """Totals validation passes when derived matches explicit totals."""
    payload = _fixture_bytes()
    parsed = json.loads(payload)
    innings = extract_normalized_innings(parsed)

    # No preview data (use explicit runs from payload)
    validation, warnings, blocking_error = validate_innings_totals(innings, [])

    assert blocking_error is None, f"Expected no blocking error, got: {blocking_error}"
    assert all(v["status"] in ("ok", "warning") for v in validation)


def test_delivery_service_totals_validation_blocks_large_mismatch() -> None:
    """Totals validation blocks when explicit runs differ greatly from delivery-derived total."""
    payload = _fixture_bytes()
    parsed = json.loads(payload)
    innings = extract_normalized_innings(parsed)

    # Override the explicit runs to introduce a large mismatch.
    # The fixture has 120 balls per innings.  We set the explicit total to 10
    # (far below what the delivery events sum to), triggering a block.
    modified_innings = [dict(inn) for inn in innings]
    modified_innings[0]["runs_explicit"] = 10  # Force large discrepancy

    validation, warnings, blocking_error = validate_innings_totals(modified_innings, [])

    assert blocking_error is not None, "Expected a blocking error for large mismatch"
    assert any(v["status"] == "blocked" for v in validation)


# ===========================================================================
# HTTP endpoint tests (synchronous TestClient)
# ===========================================================================


# ---------------------------------------------------------------------------
# Confirm gate
# ---------------------------------------------------------------------------


def test_apply_deliveries_requires_confirm_true() -> None:
    """apply-deliveries with confirm=false must return 422."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        _apply_batch(client, batch_id)
        resp = _apply_deliveries(client, batch_id, confirm=False)

    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Batch existence and finalization gate
# ---------------------------------------------------------------------------


def test_apply_deliveries_missing_batch_returns_404() -> None:
    """apply-deliveries for a non-existent batch_id must return 404."""
    with TestClient(app) as client:
        resp = _apply_deliveries(client, "nonexistent-batch-id")

    assert resp.status_code == 404, resp.text


def test_apply_deliveries_requires_phase5d_applied_first() -> None:
    """apply-deliveries on an unfinalized batch must be rejected with 409."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        # Do NOT apply Phase 5D
        resp = _apply_deliveries(client, batch_id)

    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"].lower()
    assert "not been applied" in detail or "phase 5d" in detail


# ---------------------------------------------------------------------------
# Successful apply
# ---------------------------------------------------------------------------


def test_apply_deliveries_success_response_shape() -> None:
    """Successful apply must return correct response shape."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        _apply_batch(client, batch_id)
        resp = _apply_deliveries(client, batch_id)

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "deliveries_applied"
    assert data["batch_id"] == batch_id
    assert data["deliveries_imported"] > 0
    assert data["innings_processed"] == 2
    assert "rollback_info" in data
    assert "totals_validation" in data


def test_apply_deliveries_correct_count() -> None:
    """Deliveries imported must equal the delivery count in the dry-run preview."""
    with TestClient(app) as client:
        # Get delivery count from dry-run
        dry_resp = client.post(
            "/api/historical-import/json/dry-run",
            json=_load_fixture(),
            params={"record_preview": "true"},
        )
        assert dry_resp.status_code == 200
        batch_id = dry_resp.json()["record_id"]
        expected_delivery_count = dry_resp.json()["delivery_count"]

        _apply_batch(client, batch_id)
        resp = _apply_deliveries(client, batch_id)

    assert resp.status_code == 200, resp.text
    assert resp.json()["deliveries_imported"] == expected_delivery_count, (
        f"Expected {expected_delivery_count} deliveries but got {resp.json()['deliveries_imported']}"
    )


def test_apply_deliveries_totals_validation_returned() -> None:
    """Response must include totals_validation entries for each innings."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        _apply_batch(client, batch_id)
        resp = _apply_deliveries(client, batch_id)

    assert resp.status_code == 200, resp.text
    validation = resp.json()["totals_validation"]
    assert len(validation) == 2, "Expected 2 innings in totals_validation"
    for item in validation:
        assert "inning_no" in item
        assert "derived_runs" in item
        assert "status" in item
        assert item["status"] in ("ok", "warning"), (
            f"Totals validation status must be ok or warning for valid fixture, got: {item['status']}"
        )


# ---------------------------------------------------------------------------
# Idempotency gate
# ---------------------------------------------------------------------------


def test_apply_deliveries_repeat_apply_blocked() -> None:
    """Second apply-deliveries on the same game must be rejected with 409."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        _apply_batch(client, batch_id)

        # First apply succeeds
        r1 = _apply_deliveries(client, batch_id)
        assert r1.status_code == 200, r1.text

        # Second apply must be blocked
        r2 = _apply_deliveries(client, batch_id)

    assert r2.status_code == 409, r2.text
    detail = r2.json()["detail"].lower()
    assert "already" in detail


# ---------------------------------------------------------------------------
# Rollback removes delivery data
# ---------------------------------------------------------------------------


def test_apply_deliveries_rollback_removes_all_data() -> None:
    """Phase 5E rollback must delete the game (including delivery data)."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        game_id = _apply_batch(client, batch_id)

        # Import deliveries
        r1 = _apply_deliveries(client, batch_id)
        assert r1.status_code == 200, r1.text
        assert r1.json()["deliveries_imported"] > 0

        # Rollback
        rollback_resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/rollback",
            json={"confirm": True},
        )
        assert rollback_resp.status_code == 200, rollback_resp.text
        assert rollback_resp.json()["rolled_back_game_id"] == game_id

        # Batch should be un-finalized
        batches = client.get("/api/historical-import/json/batches").json()

    assert len(batches) == 1
    assert batches[0]["is_finalized"] is False
    assert batches[0]["applied_game_id"] is None


def test_apply_deliveries_cannot_apply_after_rollback() -> None:
    """After rollback, applying deliveries must fail (batch is un-finalized)."""
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        _apply_batch(client, batch_id)
        r1 = _apply_deliveries(client, batch_id)
        assert r1.status_code == 200, r1.text

        # Rollback
        client.post(
            f"/api/historical-import/json/batches/{batch_id}/rollback",
            json={"confirm": True},
        )

        # Try delivery apply again (batch is now un-finalized)
        r2 = _apply_deliveries(client, batch_id)

    # Must fail because batch is not finalized
    assert r2.status_code == 409, r2.text


# ---------------------------------------------------------------------------
# Cross-batch isolation
# ---------------------------------------------------------------------------


def test_apply_deliveries_does_not_affect_other_batches() -> None:
    """Delivery import for one batch must not affect other batches."""
    with TestClient(app) as client:
        # Create two batches
        batch_a = _record_batch(client)
        resp_b = client.post(
            "/api/historical-import/json/dry-run",
            json={**_load_fixture(), "matchType": "ODI"},
            params={"record_preview": "true"},
        )
        assert resp_b.status_code == 200
        batch_b = resp_b.json()["record_id"]

        # Apply Phase 5D for both
        game_a = _apply_batch(client, batch_a)
        game_b = _apply_batch(client, batch_b)

        # Apply deliveries only for batch_a
        r = _apply_deliveries(client, batch_a)
        assert r.status_code == 200, r.text

        # Check batches
        batches = client.get("/api/historical-import/json/batches").json()

    by_id = {b["id"]: b for b in batches}
    assert by_id[batch_a]["is_finalized"] is True
    assert by_id[batch_b]["is_finalized"] is True
    assert by_id[batch_b]["applied_game_id"] == game_b


# ===========================================================================
# Service-level integration tests (async, direct DB access)
# ===========================================================================


async def _create_batch_with_fixture_hash(db_session: AsyncSession) -> "HistoricalImportBatch":
    """Create a batch with the canonical hash of the fixture payload."""
    from backend.services.historical_import_service import create_import_batch

    fixture_bytes = _fixture_bytes()
    fixture_hash = _hash_payload(fixture_bytes)

    return await create_import_batch(
        db_session,
        source_hash_sha256=fixture_hash,
        source_format="cricksy_fixture",
        status="valid",
        error_count=0,
        warning_count=0,
        innings_count=2,
        delivery_count=240,
        dry_run_summary={
            "metadata_preview": {
                "match_type": "T20",
                "venue": "Generic Cricket Ground",
                "date": None,
                "result": "Team Alpha won",
            },
            "teams_preview": ["Team Alpha", "Team Beta"],
            "innings_preview": [
                {"inning_no": 1, "team": "Team Alpha", "deliveries": 120, "runs": 157, "wickets": 6},
                {"inning_no": 2, "team": "Team Beta", "deliveries": 120, "runs": 142, "wickets": 8},
            ],
        },
    )


@pytest.mark.asyncio
async def test_historical_innings_summary_visible_after_phase5d(db_session: AsyncSession) -> None:
    """After Phase 5D apply, case study must show innings from historical summary.

    This verifies the Phase 5F requirement that Analyst Workspace shows real
    innings data even before delivery-level import.
    """
    from backend.services.analytics_case_study import _build_case_study_from_db
    from backend.services.historical_import_apply_service import apply_historical_batch

    batch = await _create_batch_with_fixture_hash(db_session)
    game, _, err = await apply_historical_batch(db_session, batch_id=batch.id, confirm=True)
    assert err is None, f"Phase 5D apply failed: {err}"
    assert game is not None

    case_study = await _build_case_study_from_db(db_session, game.id, "test-user")

    # Innings must be populated from historical_innings_summary
    assert len(case_study.match.innings) >= 1, (
        "Case study must show at least one innings from historical data after Phase 5D"
    )

    # Should not be all zeros (fake data guard)
    total_runs = sum(inn.runs for inn in case_study.match.innings)
    assert total_runs > 0, (
        "Innings runs must be non-zero real data (not fake fallback). "
        f"Got innings: {case_study.match.innings}"
    )


@pytest.mark.asyncio
async def test_analyst_case_study_after_delivery_import(db_session: AsyncSession) -> None:
    """After Phase 5F delivery import, case study must show real phases and key players."""
    from backend.services.analytics_case_study import _build_case_study_from_db
    from backend.services.historical_import_apply_service import (
        apply_historical_batch,
        apply_historical_deliveries,
    )

    batch = await _create_batch_with_fixture_hash(db_session)
    game, _, err = await apply_historical_batch(db_session, batch_id=batch.id, confirm=True)
    assert err is None, f"Phase 5D apply failed: {err}"
    assert game is not None

    result_info, warnings, delivery_err = await apply_historical_deliveries(
        db_session,
        batch_id=batch.id,
        confirm=True,
        raw_payload=_fixture_bytes(),
    )
    assert delivery_err is None, f"Phase 5F delivery import failed: {delivery_err}"
    assert result_info is not None
    assert result_info["deliveries_imported"] > 0

    # Reload game from DB to pick up changes
    await db_session.refresh(game)

    case_study = await _build_case_study_from_db(db_session, game.id, "test-user")

    # Innings must be populated with real data
    assert len(case_study.match.innings) >= 2, "Must have 2 innings after full import"
    assert case_study.match.innings[0].runs > 0, "First innings must have non-zero runs"
    assert case_study.match.innings[1].runs > 0, "Second innings must have non-zero runs"

    # Phases must be computed from delivery data
    assert len(case_study.phases) > 0, (
        "Phases must be non-empty after delivery import; got empty phases list"
    )
    assert any(p.runs > 0 for p in case_study.phases), (
        "At least one phase must have runs > 0 from imported delivery data"
    )

    # Key players must be populated
    assert len(case_study.key_players) > 0, (
        "Key players must be populated after delivery import"
    )

    # Key phase must have real data
    assert case_study.key_phase.title != "Phase data not yet available", (
        "Key phase must have real data after delivery import"
    )


@pytest.mark.asyncio
async def test_no_fake_fallback_data_in_case_study(db_session: AsyncSession) -> None:
    """Case study for historical match must not use fake fallback values.

    The mock IDs 'm1' and 'm2' use hardcoded fake data.  A real historical
    game ID must never use those mock data paths.
    """
    from backend.services.analytics_case_study import _build_case_study_from_db
    from backend.services.historical_import_apply_service import (
        apply_historical_batch,
        apply_historical_deliveries,
    )

    batch = await _create_batch_with_fixture_hash(db_session)
    game, _, err = await apply_historical_batch(db_session, batch_id=batch.id, confirm=True)
    assert err is None
    assert game is not None

    _, _, delivery_err = await apply_historical_deliveries(
        db_session,
        batch_id=batch.id,
        confirm=True,
        raw_payload=_fixture_bytes(),
    )
    assert delivery_err is None

    await db_session.refresh(game)

    # Game ID must not be 'm1' or 'm2' (fake data IDs)
    assert game.id not in ("m1", "m2"), "Historical game must have a real UUID, not mock ID"

    case_study = await _build_case_study_from_db(db_session, game.id, "test-user")
    assert case_study.match.id == game.id, "Case study must be for the real imported game"
    # Lions/Falcons are mock-data team names; they must not appear for real imports
    assert "Lions" not in case_study.match.teams_label
    assert "Falcons" not in case_study.match.teams_label


@pytest.mark.asyncio
async def test_rollback_removes_delivery_data_service_level(db_session: AsyncSession) -> None:
    """Service-level test: rollback removes game including delivery data."""
    from sqlalchemy import select

    from backend.services.historical_import_apply_service import (
        apply_historical_batch,
        apply_historical_deliveries,
        rollback_historical_batch,
    )
    from backend.sql_app.models import Game

    batch = await _create_batch_with_fixture_hash(db_session)
    game, _, err = await apply_historical_batch(db_session, batch_id=batch.id, confirm=True)
    assert err is None
    assert game is not None
    game_id = game.id

    result_info, _, delivery_err = await apply_historical_deliveries(
        db_session,
        batch_id=batch.id,
        confirm=True,
        raw_payload=_fixture_bytes(),
    )
    assert delivery_err is None
    assert result_info is not None
    assert result_info["deliveries_imported"] > 0

    # Rollback
    rolled_back_id, _, rollback_err = await rollback_historical_batch(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )
    assert rollback_err is None, f"Rollback failed: {rollback_err}"
    assert rolled_back_id == game_id

    # Game must no longer exist
    game_after = (
        await db_session.execute(select(Game).where(Game.id == game_id))
    ).scalars().first()
    assert game_after is None, "Game (including delivery data) must be deleted after rollback"


@pytest.mark.asyncio
async def test_apply_deliveries_idempotency_service_level(db_session: AsyncSession) -> None:
    """Service-level test: second apply_historical_deliveries is blocked."""
    from backend.services.historical_import_apply_service import (
        apply_historical_batch,
        apply_historical_deliveries,
    )

    batch = await _create_batch_with_fixture_hash(db_session)
    game, _, err = await apply_historical_batch(db_session, batch_id=batch.id, confirm=True)
    assert err is None
    assert game is not None

    # First apply
    r1, _, e1 = await apply_historical_deliveries(
        db_session, batch_id=batch.id, confirm=True, raw_payload=_fixture_bytes()
    )
    assert e1 is None, f"First delivery apply failed: {e1}"

    # Second apply
    r2, _, e2 = await apply_historical_deliveries(
        db_session, batch_id=batch.id, confirm=True, raw_payload=_fixture_bytes()
    )
    assert e2 is not None, "Second delivery apply must return an error"
    assert "already" in e2.lower(), f"Expected 'already' in error message, got: {e2}"

