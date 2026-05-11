"""Phase 5K — Historical Import Metadata Backfill / Repair tests.

Validates:
- repair requires explicit confirm=True
- repair fails for missing batch_id
- repair fails for unfinalized batches
- repair fails for non-completed (live) games
- repair fails for non-historical games
- repair returns already_complete when Phase 5J fields already present
- repair refused when dry_run_summary lacks Phase 5J metadata (reimport required)
- repair succeeds for a genuine legacy game (Phase 5J fields absent from game + present in batch)
- repair writes an audit log entry
- repair is idempotent (second call → already_complete)
- live/in-progress games are never mutated
- valid Phase 5J metadata is never overwritten
- scoring/delivery data is not mutated by the repair
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import app
from backend.services.historical_import_apply_service import apply_historical_batch
from backend.services.historical_import_backfill_service import (
    repair_legacy_historical_metadata,
)
from backend.services.historical_import_service import create_import_batch
from backend.sql_app.models import Game, GameStatus, HistoricalImportBatch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


async def _make_batch(
    db: AsyncSession,
    *,
    include_phase_5j_meta: bool = True,
    status: str = "valid",
    error_count: int = 0,
) -> HistoricalImportBatch:
    """Create a valid import batch.

    Args:
        include_phase_5j_meta: When True the dry_run_summary includes Phase 5J
            fields (event_name, season, match_number, source_dates) so the
            repair service can source values from it.  When False those fields
            are absent — simulating a very-old batch that cannot supply them.
    """
    metadata_preview: dict = {
        "match_type": "t20",
        "venue": "Test Ground",
        "date": "2024-05-01",
        "result": "Team A won by 10 runs.",
    }
    if include_phase_5j_meta:
        metadata_preview["event_name"] = "Test Cup 2024"
        metadata_preview["season"] = "2024"
        metadata_preview["match_number"] = 7
        metadata_preview["source_dates"] = ["2024-05-01"]

    return await create_import_batch(
        db,
        source_hash_sha256=_sha256(),
        source_format="cricksy_fixture",
        status=status,
        error_count=error_count,
        warning_count=0,
        innings_count=2,
        delivery_count=240,
        dry_run_summary={
            "metadata_preview": metadata_preview,
            "teams_preview": ["Team A", "Team B"],
            "innings_preview": [
                {"inning_no": 1, "team": "Team A", "deliveries": 120, "runs": 150, "wickets": 6},
                {"inning_no": 2, "team": "Team B", "deliveries": 120, "runs": 140, "wickets": 8},
            ],
        },
    )


async def _apply_and_strip_phase5j(
    db: AsyncSession,
    batch: HistoricalImportBatch,
) -> Game:
    """Apply the batch then strip Phase 5J fields from the game's historical_import
    metadata to simulate a legacy pre-Phase-5J import."""
    game, _, err = await apply_historical_batch(db, batch_id=batch.id, confirm=True)
    assert err is None, err
    assert game is not None

    # Strip Phase 5J fields to simulate a legacy game
    phases = dict(game.phases or {})
    hist = dict(phases.get("historical_import") or {})
    for field in ("event_name", "season", "match_number", "source_dates"):
        hist.pop(field, None)
    phases["historical_import"] = hist
    game.phases = phases
    await db.commit()
    await db.refresh(game)
    return game


# ---------------------------------------------------------------------------
# HTTP-level safety gate tests (TestClient)
# ---------------------------------------------------------------------------


def test_repair_requires_confirm_true() -> None:
    """repair-metadata with confirm=False must be rejected with 422."""
    with TestClient(app) as client:
        # Record a valid batch
        import json
        from pathlib import Path

        fixture = json.loads((Path(__file__).parent / "simulated_t20_match.json").read_text())
        dry_resp = client.post(
            "/api/historical-import/json/dry-run",
            json=fixture,
            params={"record_preview": "true"},
        )
        assert dry_resp.status_code == 200
        batch_id = dry_resp.json()["record_id"]

        # Apply to create a historical game
        apply_resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )
        assert apply_resp.status_code == 200

        # Repair with confirm=False must be rejected
        resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/repair-metadata",
            json={"confirm": False},
        )

    assert resp.status_code == 422, resp.text


def test_repair_missing_batch_returns_404() -> None:
    """repair-metadata for a non-existent batch_id must return 404."""
    with TestClient(app) as client:
        resp = client.post(
            "/api/historical-import/json/batches/no-such-batch/repair-metadata",
            json={"confirm": True},
        )

    assert resp.status_code == 404, resp.text


def test_repair_unfinalized_batch_returns_409() -> None:
    """repair-metadata on an unfinalized batch must be rejected."""
    with TestClient(app) as client:
        import json
        from pathlib import Path

        fixture = json.loads((Path(__file__).parent / "simulated_t20_match.json").read_text())
        dry_resp = client.post(
            "/api/historical-import/json/dry-run",
            json=fixture,
            params={"record_preview": "true"},
        )
        assert dry_resp.status_code == 200
        batch_id = dry_resp.json()["record_id"]

        # Attempt repair WITHOUT applying first (batch not finalized)
        resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/repair-metadata",
            json={"confirm": True},
        )

    assert resp.status_code == 409, resp.text
    assert "not been applied" in resp.json()["detail"].lower()


def test_repair_applied_batch_returns_already_complete() -> None:
    """repair-metadata on a Phase 5J-aware game must return already_complete (200).

    Post-Phase-5J imports include event_name/season/match_number/source_dates,
    so the repair service should not alter them.
    """
    with TestClient(app) as client:
        import json
        from pathlib import Path

        fixture = json.loads((Path(__file__).parent / "simulated_t20_match.json").read_text())
        dry_resp = client.post(
            "/api/historical-import/json/dry-run",
            json=fixture,
            params={"record_preview": "true"},
        )
        assert dry_resp.status_code == 200
        batch_id = dry_resp.json()["record_id"]

        apply_resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/apply",
            json={"confirm": True},
        )
        assert apply_resp.status_code == 200

        repair_resp = client.post(
            f"/api/historical-import/json/batches/{batch_id}/repair-metadata",
            json={"confirm": True},
        )

    # Returns 200 with already_complete — metadata was already set by Phase 5J
    assert repair_resp.status_code == 200, repair_resp.text
    data = repair_resp.json()
    assert data["status"] == "already_complete"
    assert data["fields_added"] == []


# ---------------------------------------------------------------------------
# Unit-level service tests using direct DB access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_repair_service_confirm_false_is_rejected(db_session: AsyncSession) -> None:
    """Service-level: confirm=False must return an error message."""
    batch = await _make_batch(db_session)
    result, _, error = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch.id,
        confirm=False,
    )
    assert result is None
    assert error is not None
    assert "confirm must be true" in error.lower()


@pytest.mark.asyncio
async def test_repair_service_unknown_batch(db_session: AsyncSession) -> None:
    """Service-level: non-existent batch_id must return an error."""
    result, _, error = await repair_legacy_historical_metadata(
        db_session,
        batch_id="no-such-batch",
        confirm=True,
    )
    assert result is None
    assert error is not None
    assert "not found" in error.lower()


@pytest.mark.asyncio
async def test_repair_service_unfinalized_batch(db_session: AsyncSession) -> None:
    """Service-level: unfinalized batch must be rejected."""
    batch = await _make_batch(db_session)
    result, _, error = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )
    assert result is None
    assert error is not None
    assert "not been applied" in error.lower()


@pytest.mark.asyncio
async def test_repair_service_live_game_refused(db_session: AsyncSession) -> None:
    """Service-level: live (non-completed) games must never be mutated."""
    batch = await _make_batch(db_session)
    # Create a live game and link it to the batch manually
    live_game = Game(
        id=str(uuid.uuid4()),
        team_a={"name": "Live A", "players": []},
        team_b={"name": "Live B", "players": []},
        match_type="t20",
        status=GameStatus.live,
        deliveries=[],
        phases={"historical_import": {"batch_id": batch.id}},
    )
    db_session.add(live_game)
    await db_session.flush()

    batch.is_finalized = True
    batch.applied_game_id = live_game.id
    db_session.add(batch)
    await db_session.commit()

    result, _, error = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )

    assert result is None
    assert error is not None
    assert "completed" in error.lower()

    # Verify the game was not modified
    await db_session.refresh(live_game)
    assert live_game.status == GameStatus.live


@pytest.mark.asyncio
async def test_repair_service_non_historical_game_refused(db_session: AsyncSession) -> None:
    """Service-level: games without historical_import phases key must be refused."""
    batch = await _make_batch(db_session)
    non_historical = Game(
        id=str(uuid.uuid4()),
        team_a={"name": "A", "players": []},
        team_b={"name": "B", "players": []},
        match_type="t20",
        status=GameStatus.completed,
        deliveries=[],
        phases={"some_other_key": {}},  # no historical_import key
    )
    db_session.add(non_historical)
    await db_session.flush()

    batch.is_finalized = True
    batch.applied_game_id = non_historical.id
    db_session.add(batch)
    await db_session.commit()

    result, _, error = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )

    assert result is None
    assert error is not None
    assert "not applicable" in error.lower() or "historical_import" in error.lower()


@pytest.mark.asyncio
async def test_repair_service_already_complete_not_overwritten(db_session: AsyncSession) -> None:
    """Service-level: games that already have Phase 5J metadata must not be overwritten."""
    batch = await _make_batch(db_session, include_phase_5j_meta=True)
    game, _, err = await apply_historical_batch(db_session, batch_id=batch.id, confirm=True)
    assert err is None and game is not None

    # Verify game has Phase 5J fields
    hist = game.phases["historical_import"]
    assert "event_name" in hist

    original_event_name = hist.get("event_name")

    result, warnings, error = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )

    assert error is None
    assert result is not None
    assert result["status"] == "already_complete"

    # Verify metadata was NOT changed
    await db_session.refresh(game)
    assert game.phases["historical_import"].get("event_name") == original_event_name


@pytest.mark.asyncio
async def test_repair_service_legacy_game_repaired(db_session: AsyncSession) -> None:
    """Service-level: a legacy game (missing Phase 5J fields) must be repaired from batch metadata."""
    batch = await _make_batch(db_session, include_phase_5j_meta=True)
    game = await _apply_and_strip_phase5j(db_session, batch)

    # Verify legacy state: Phase 5J fields are absent
    hist_before = game.phases["historical_import"]
    for field in ("event_name", "season", "match_number", "source_dates"):
        assert field not in hist_before, f"Field '{field}' should be absent before repair"

    result, warnings, error = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )

    assert error is None, error
    assert result is not None
    assert result["status"] == "repaired"
    assert result["game_id"] == game.id
    assert len(result["fields_added"]) > 0

    # Verify the game was updated with Phase 5J metadata
    await db_session.refresh(game)
    hist_after = game.phases["historical_import"]
    assert hist_after.get("event_name") == "Test Cup 2024"
    assert hist_after.get("season") == "2024"
    assert hist_after.get("match_number") == 7
    assert hist_after.get("source_dates") == ["2024-05-01"]


@pytest.mark.asyncio
async def test_repair_service_writes_audit_log(db_session: AsyncSession) -> None:
    """Successful repair must write a _repair_log entry in historical_import metadata."""
    batch = await _make_batch(db_session, include_phase_5j_meta=True)
    game = await _apply_and_strip_phase5j(db_session, batch)

    result, _, error = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )

    assert error is None
    assert result is not None
    assert result["status"] == "repaired"

    await db_session.refresh(game)
    hist = game.phases["historical_import"]
    assert "_repair_log" in hist
    repair_log = hist["_repair_log"]
    assert len(repair_log) == 1
    log_entry = repair_log[0]
    assert log_entry["phase"] == "5K"
    assert "repaired_at" in log_entry
    assert len(log_entry["fields_added"]) > 0
    assert log_entry["source"] == "dry_run_summary.metadata_preview"


@pytest.mark.asyncio
async def test_repair_service_is_idempotent(db_session: AsyncSession) -> None:
    """Second repair call on an already-repaired game must return already_complete."""
    batch = await _make_batch(db_session, include_phase_5j_meta=True)
    game = await _apply_and_strip_phase5j(db_session, batch)

    # First repair
    result1, _, err1 = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )
    assert err1 is None
    assert result1 is not None
    assert result1["status"] == "repaired"

    # Second repair — must report already_complete without modifying data
    result2, _, err2 = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )
    assert err2 is None
    assert result2 is not None
    assert result2["status"] == "already_complete"

    # Audit log must still have only one entry (not duplicated)
    await db_session.refresh(game)
    hist = game.phases["historical_import"]
    assert len(hist.get("_repair_log", [])) == 1


@pytest.mark.asyncio
async def test_repair_service_refused_when_batch_lacks_metadata(db_session: AsyncSession) -> None:
    """Service-level: repair must be refused when batch dry_run_summary has no Phase 5J fields.

    This proves that reimport is required when the source batch pre-dates Phase 5J
    and cannot supply the missing metadata.
    """
    batch = await _make_batch(db_session, include_phase_5j_meta=False)
    game = await _apply_and_strip_phase5j(db_session, batch)

    result, _, error = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )

    assert result is None
    assert error is not None
    assert "reimport" in error.lower() or "not possible" in error.lower()

    # Verify the game was NOT modified
    await db_session.refresh(game)
    hist = game.phases["historical_import"]
    assert "event_name" not in hist
    assert "_repair_log" not in hist


@pytest.mark.asyncio
async def test_repair_does_not_alter_other_games(db_session: AsyncSession) -> None:
    """repair-metadata on batch A must not alter the game created by batch B."""
    batch_a = await _make_batch(db_session, include_phase_5j_meta=True)
    batch_b = await _make_batch(db_session, include_phase_5j_meta=True)

    game_a = await _apply_and_strip_phase5j(db_session, batch_a)
    game_b, _, err_b = await apply_historical_batch(db_session, batch_id=batch_b.id, confirm=True)
    assert err_b is None and game_b is not None

    # Capture game_b event_name before repair
    event_b_before = game_b.phases["historical_import"].get("event_name")

    result, _, error = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch_a.id,
        confirm=True,
    )
    assert error is None
    assert result is not None
    assert result["status"] == "repaired"
    assert result["game_id"] == game_a.id

    # Verify game_b was not touched
    await db_session.refresh(game_b)
    assert game_b.phases["historical_import"].get("event_name") == event_b_before


@pytest.mark.asyncio
async def test_repair_does_not_alter_deliveries(db_session: AsyncSession) -> None:
    """repair-metadata must not modify Game.deliveries (scoring engine data)."""
    batch = await _make_batch(db_session, include_phase_5j_meta=True)
    game = await _apply_and_strip_phase5j(db_session, batch)

    original_deliveries = game.deliveries
    original_total_runs = game.total_runs
    original_status = game.status

    result, _, error = await repair_legacy_historical_metadata(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )
    assert error is None
    assert result is not None
    assert result["status"] == "repaired"

    await db_session.refresh(game)
    # Deliveries and scoring fields must be untouched
    assert game.deliveries == original_deliveries
    assert game.total_runs == original_total_runs
    assert game.status == original_status
