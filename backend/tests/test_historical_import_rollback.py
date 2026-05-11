"""Phase 5E - Historical import rollback safety tests."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import app
from backend.services.historical_import_apply_service import apply_historical_batch, rollback_historical_batch
from backend.services.historical_import_service import create_import_batch
from backend.sql_app.models import Delivery, Game, GameStatus, HistoricalImportBatch, Player, Team

FIXTURE_PATH = Path(__file__).resolve().parent / "simulated_t20_match.json"


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _generate_test_hash() -> str:
    """Return a 64-char pseudo SHA-256 string for test batch creation."""
    return uuid.uuid4().hex + uuid.uuid4().hex


def _record_batch(client: TestClient) -> str:
    response = client.post(
        "/api/historical-import/json/dry-run",
        json=_load_fixture(),
        params={"record_preview": "true"},
    )
    assert response.status_code == 200, response.text
    record_id = response.json()["record_id"]
    assert record_id is not None
    return record_id


def test_rollback_requires_confirm_true() -> None:
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        client.post(f"/api/historical-import/json/batches/{batch_id}/apply", json={"confirm": True})
        response = client.post(
            f"/api/historical-import/json/batches/{batch_id}/rollback",
            json={"confirm": False},
        )

    assert response.status_code == 422, response.text


def test_rollback_missing_batch_returns_404() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/batches/does-not-exist/rollback",
            json={"confirm": True},
        )

    assert response.status_code == 404, response.text


def test_rollback_rejects_non_finalized_batch() -> None:
    with TestClient(app) as client:
        batch_id = _record_batch(client)
        response = client.post(
            f"/api/historical-import/json/batches/{batch_id}/rollback",
            json={"confirm": True},
        )

    assert response.status_code == 409, response.text
    assert "not finalized" in response.json()["detail"].lower()


async def _create_valid_batch(
    db_session: AsyncSession,
    *,
    match_type: str = "t20",
) -> HistoricalImportBatch:
    return await create_import_batch(
        db_session,
        source_hash_sha256=_generate_test_hash(),
        source_format="cricksy_fixture",
        status="valid",
        error_count=0,
        warning_count=0,
        innings_count=2,
        delivery_count=240,
        dry_run_summary={
            "metadata_preview": {
                "match_type": match_type,
                "venue": "Test Venue",
                "date": "2025-01-01",
                "result": "Team A won by 10 runs",
            },
            "teams_preview": ["Team A", "Team B"],
            "innings_preview": [
                {"inning_no": 1, "team": "Team A", "deliveries": 120, "runs": 150, "wickets": 6},
                {"inning_no": 2, "team": "Team B", "deliveries": 120, "runs": 140, "wickets": 8},
            ],
        },
    )


@pytest.mark.asyncio
async def test_rollback_rejects_finalized_batch_without_applied_game_id(db_session: AsyncSession) -> None:
    batch = await _create_valid_batch(db_session)
    batch.is_finalized = True
    batch.applied_game_id = None
    db_session.add(batch)
    await db_session.commit()

    rolled_back_game_id, _, error = await rollback_historical_batch(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )

    assert rolled_back_game_id is None
    assert error is not None
    assert "no applied_game_id" in error


@pytest.mark.asyncio
async def test_rollback_deletes_only_applied_historical_game(db_session: AsyncSession) -> None:
    batch_a = await _create_valid_batch(db_session, match_type="t20")
    batch_b = await _create_valid_batch(db_session, match_type="odi")

    game_a, _, err_a = await apply_historical_batch(db_session, batch_id=batch_a.id, confirm=True)
    game_b, _, err_b = await apply_historical_batch(db_session, batch_id=batch_b.id, confirm=True)
    assert err_a is None and game_a is not None
    assert err_b is None and game_b is not None

    rolled_back_id, _, rollback_err = await rollback_historical_batch(
        db_session,
        batch_id=batch_a.id,
        confirm=True,
    )
    assert rollback_err is None
    assert rolled_back_id == game_a.id

    batch_a_after = (
        await db_session.execute(select(HistoricalImportBatch).where(HistoricalImportBatch.id == batch_a.id))
    ).scalars().first()
    batch_b_after = (
        await db_session.execute(select(HistoricalImportBatch).where(HistoricalImportBatch.id == batch_b.id))
    ).scalars().first()
    assert batch_a_after is not None
    assert batch_b_after is not None

    assert await db_session.get(Game, game_a.id) is None
    assert await db_session.get(Game, game_b.id) is not None
    assert batch_a_after.is_finalized is False
    assert batch_a_after.applied_game_id is None
    assert batch_b_after.is_finalized is True
    assert batch_b_after.applied_game_id == game_b.id


@pytest.mark.asyncio
async def test_rollback_does_not_delete_live_games(db_session: AsyncSession) -> None:
    batch = await _create_valid_batch(db_session)
    live_game = Game(
        id=str(uuid.uuid4()),
        team_a={"name": "Live A", "players": []},
        team_b={"name": "Live B", "players": []},
        match_type="t20",
        status=GameStatus.live,
        deliveries=[],
        phases={},
    )
    db_session.add(live_game)
    await db_session.flush()

    batch.is_finalized = True
    batch.applied_game_id = live_game.id
    db_session.add(batch)
    await db_session.commit()

    rolled_back_id, _, error = await rollback_historical_batch(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )

    batch_after = (
        await db_session.execute(select(HistoricalImportBatch).where(HistoricalImportBatch.id == batch.id))
    ).scalars().first()
    assert rolled_back_id is None
    assert error is not None
    assert "not completed" in error
    assert await db_session.get(Game, live_game.id) is not None
    assert batch_after is not None
    assert batch_after.is_finalized is True
    assert batch_after.applied_game_id == live_game.id


@pytest.mark.asyncio
async def test_apply_rollback_roundtrip_preserves_non_game_rows(db_session: AsyncSession) -> None:
    before_games = int((await db_session.execute(select(func.count()).select_from(Game))).scalar_one())
    before_deliveries = int(
        (await db_session.execute(select(func.count()).select_from(Delivery))).scalar_one()
    )
    before_players = int((await db_session.execute(select(func.count()).select_from(Player))).scalar_one())
    before_teams = int((await db_session.execute(select(func.count()).select_from(Team))).scalar_one())

    batch = await _create_valid_batch(db_session)
    game, _, apply_error = await apply_historical_batch(db_session, batch_id=batch.id, confirm=True)
    assert apply_error is None
    assert game is not None

    rolled_back_id, _, rollback_error = await rollback_historical_batch(
        db_session,
        batch_id=batch.id,
        confirm=True,
    )
    assert rollback_error is None
    assert rolled_back_id == game.id

    batch_after = (
        await db_session.execute(select(HistoricalImportBatch).where(HistoricalImportBatch.id == batch.id))
    ).scalars().first()
    after_games = int((await db_session.execute(select(func.count()).select_from(Game))).scalar_one())
    after_deliveries = int(
        (await db_session.execute(select(func.count()).select_from(Delivery))).scalar_one()
    )
    after_players = int((await db_session.execute(select(func.count()).select_from(Player))).scalar_one())
    after_teams = int((await db_session.execute(select(func.count()).select_from(Team))).scalar_one())

    assert batch_after is not None
    assert batch_after.is_finalized is False
    assert batch_after.applied_game_id is None
    assert before_games == after_games
    assert before_deliveries == after_deliveries
    assert before_players == after_players
    assert before_teams == after_teams
