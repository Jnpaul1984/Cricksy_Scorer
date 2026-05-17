from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.historical_import_apply_service import apply_historical_batch
from backend.services.historical_import_service import create_import_batch
from backend.sql_app.models import (
    Game,
    HistoricalPlayerResolutionQueue,
    HistoricalPlayerResolutionState,
    HistoricalSourcePlayerRegistry,
    Player,
)


def _sha256() -> str:
    return uuid.uuid4().hex + uuid.uuid4().hex


async def _make_batch(
    db: AsyncSession,
    *,
    roster_names: list[str],
    competition_name: str = "Caribbean Premier League",
    season: str = "2013",
) -> str:
    source_hash = _sha256()
    batch = await create_import_batch(
        db,
        source_hash_sha256=source_hash,
        source_format="cricsheet_json",
        status="valid",
        error_count=0,
        warning_count=0,
        innings_count=2,
        delivery_count=12,
        dry_run_summary={
            "metadata_preview": {
                "match_type": "t20",
                "venue": "Kensington Oval",
                "date": "2013-07-30",
                "result": "Team A won",
                "event_name": competition_name,
                "season": season,
            },
            "teams_preview": ["Team A", "Team B"],
            "player_names_found": list(roster_names),
            "innings_preview": [
                {"inning_no": 1, "team": "Team A", "deliveries": 6, "runs": 10, "wickets": 1},
                {"inning_no": 2, "team": "Team B", "deliveries": 6, "runs": 8, "wickets": 2},
            ],
            "canonical_preview": {
                "competition_context": {
                    "competition_type": "franchise",
                    "competition_name": competition_name,
                    "season": season,
                },
                "source_provenance": {
                    "source_schema": "cricsheet_json",
                    "source_hash_sha256": source_hash,
                },
                "squad_roster_snapshot": [
                    {
                        "team_name": "Team A",
                        "named_squad": list(roster_names),
                        "playing_xi": list(roster_names),
                        "substitutes": [],
                        "unresolved_entries": [],
                    }
                ],
            },
        },
    )
    game, _, err = await apply_historical_batch(db, batch_id=batch.id, confirm=True)
    assert err is None, err
    assert game is not None
    return game.id


@pytest.mark.asyncio
async def test_identity_resolution_exact_match_and_no_blind_auto_create(
    db_session: AsyncSession,
) -> None:
    db_session.add(Player(id=101, name="Dwayne Smith", role="All-rounder"))
    await db_session.commit()

    game_id = await _make_batch(db_session, roster_names=["Dwayne Smith", "Mystery Batter"])

    rows = (
        await db_session.execute(
            select(HistoricalSourcePlayerRegistry).order_by(HistoricalSourcePlayerRegistry.source_player_name)
        )
    ).scalars()
    players = list(rows)
    assert len(players) == 2

    resolved = next(row for row in players if row.source_player_name == "Dwayne Smith")
    unresolved = next(row for row in players if row.source_player_name == "Mystery Batter")

    assert resolved.resolution_state == HistoricalPlayerResolutionState.auto_resolved
    assert resolved.canonical_player_id == 101
    assert resolved.mapping_method == "normalized_exact_match"
    assert unresolved.resolution_state == HistoricalPlayerResolutionState.unresolved
    assert game_id in unresolved.match_references
    game = (await db_session.execute(select(Game).where(Game.id == game_id))).scalars().first()
    assert game is not None
    hist_meta = (game.phases or {}).get("historical_import", {})
    player_registry_meta = hist_meta.get("player_identity_registry")
    assert isinstance(player_registry_meta, dict)
    assert player_registry_meta["unresolved_count"] >= 1

    queue_rows = (await db_session.execute(select(HistoricalPlayerResolutionQueue))).scalars().all()
    assert len(queue_rows) == 1
    assert queue_rows[0].source_player_id == unresolved.source_player_id
    assert queue_rows[0].queue_state == "pending"

    player_count = await db_session.scalar(select(func.count()).select_from(Player))
    assert player_count == 1, "historical import must not auto-create canonical players blindly"


@pytest.mark.asyncio
async def test_identity_resolution_alias_match(db_session: AsyncSession) -> None:
    db_session.add(Player(id=202, name="Dwayne R Smith", role="All-rounder"))
    await db_session.commit()

    await _make_batch(db_session, roster_names=["Dwayne R Smith"])
    await _make_batch(db_session, roster_names=["Dwayne R Smith", "Smith, DR"])

    alias_row = (
        await db_session.execute(
            select(HistoricalSourcePlayerRegistry).where(
                HistoricalSourcePlayerRegistry.source_player_name == "Smith, DR"
            )
        )
    ).scalars().first()
    assert alias_row is not None
    assert alias_row.resolution_state == HistoricalPlayerResolutionState.auto_resolved
    assert alias_row.canonical_player_id == 202
    assert alias_row.mapping_method == "alias_match"


@pytest.mark.asyncio
async def test_identity_resolution_duplicate_handling_cross_match_consistency(
    db_session: AsyncSession,
) -> None:
    db_session.add(Player(id=303, name="Consistent Player"))
    await db_session.commit()

    first_game_id = await _make_batch(db_session, roster_names=["Consistent Player"])
    second_game_id = await _make_batch(db_session, roster_names=["Consistent Player"])

    rows = (
        await db_session.execute(
            select(HistoricalSourcePlayerRegistry).where(
                HistoricalSourcePlayerRegistry.normalized_name == "consistent player"
            )
        )
    ).scalars().all()
    assert len(rows) == 1, "duplicate source players should not create duplicate registry rows"
    assert set(rows[0].match_references) == {first_game_id, second_game_id}


@pytest.mark.asyncio
async def test_identity_resolution_provenance_preserved_and_queue_created(
    db_session: AsyncSession,
) -> None:
    await _make_batch(db_session, roster_names=["Queue Candidate"])

    row = (
        await db_session.execute(select(HistoricalSourcePlayerRegistry))
    ).scalars().first()
    assert row is not None
    assert row.provenance_references
    provenance = row.provenance_references[0]
    assert provenance["batch_id"]
    assert provenance["game_id"]
    assert provenance["source_schema"] == "cricsheet_json"
    assert provenance["source_system"] == "historical_import_json"
    assert provenance["source_hash_sha256"]

    queue_row = (
        await db_session.execute(
            select(HistoricalPlayerResolutionQueue).where(
                HistoricalPlayerResolutionQueue.source_player_id == row.source_player_id
            )
        )
    ).scalars().first()
    assert queue_row is not None
    assert queue_row.reason == "unresolved"
