from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.historical_import_apply_service import apply_historical_batch
from backend.services.historical_import_service import create_import_batch
from backend.sql_app.models import (
    Game,
    HistoricalCompetitionRosterEntry,
    HistoricalCompetitionRosterStatus,
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
    roster_entries: list[object] | None = None,
    roster_snapshot: list[dict[str, object]] | None = None,
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
                "squad_roster_snapshot": roster_snapshot
                or [
                    {
                        "team_name": "Team A",
                        "named_squad": list(roster_entries or roster_names),
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


@pytest.mark.asyncio
async def test_phase10f_metadata_provenance_and_canonical_safe_fill(db_session: AsyncSession) -> None:
    db_session.add(Player(id=404, name="Metadata Player", role=None))
    await db_session.commit()

    game_id = await _make_batch(
        db_session,
        roster_names=["Metadata Player"],
        roster_entries=[
            {
                "name": "Metadata Player",
                "batting_style": "Right hand bat",
                "bowling_style": "Right arm fast",
                "role": "Bowler",
            }
        ],
    )

    row = (
        await db_session.execute(
            select(HistoricalSourcePlayerRegistry).where(
                HistoricalSourcePlayerRegistry.normalized_name == "metadata player"
            )
        )
    ).scalars().first()
    assert row is not None

    metadata_history = row.metadata_field_history
    assert isinstance(metadata_history, list)
    fields = {item["field_name"]: item for item in metadata_history if isinstance(item, dict)}
    assert fields["batting_style"]["value"] == "Right hand bat"
    assert fields["bowling_style"]["value"] == "Right arm fast"
    assert fields["player_role"]["value"] == "Bowler"
    assert fields["player_role"]["source_system"] == "historical_import_json"
    assert fields["player_role"]["source_schema"] == "cricsheet_json"
    assert fields["player_role"]["game_id"] == game_id
    assert fields["player_role"]["batch_id"]
    assert fields["player_role"]["confidence_status"] == "high"
    assert fields["player_role"]["first_seen"]
    assert fields["player_role"]["last_seen"]

    canonical = await db_session.get(Player, 404)
    assert canonical is not None
    assert canonical.role == "Bowler"

    foundation = row.career_profile_foundation
    assert foundation["matches_played"] == 1
    assert foundation["competitions"][0]["competition_name"] == "Caribbean Premier League"
    assert foundation["seasons"][0]["season"] == "2013"
    assert foundation["teams"][0]["team_name"] == "Team A"
    assert foundation["match_timeline"][0]["game_id"] == game_id
    assert foundation["match_timeline"][0]["match_date"] == "2013-07-30"


@pytest.mark.asyncio
async def test_phase10f_unknown_metadata_stays_unknown_and_not_fabricated(
    db_session: AsyncSession,
) -> None:
    await _make_batch(db_session, roster_names=["Unknown Metadata Player"])

    row = (
        await db_session.execute(
            select(HistoricalSourcePlayerRegistry).where(
                HistoricalSourcePlayerRegistry.normalized_name == "unknown metadata player"
            )
        )
    ).scalars().first()
    assert row is not None

    metadata_history = row.metadata_field_history
    fields = {item["field_name"]: item for item in metadata_history if isinstance(item, dict)}
    assert fields["batting_style"]["value"] is None
    assert fields["bowling_style"]["value"] is None
    assert fields["player_role"]["value"] is None
    assert fields["batting_style"]["source_status"] == "unknown"
    assert fields["player_role"]["confidence_status"] == "unknown"


@pytest.mark.asyncio
async def test_phase10f_conflict_detection_preserves_conflict_without_overwrite(
    db_session: AsyncSession,
) -> None:
    db_session.add(Player(id=505, name="Conflict Player", role="Batsman"))
    await db_session.commit()

    await _make_batch(
        db_session,
        roster_names=["Conflict Player"],
        roster_entries=[{"name": "Conflict Player", "role": "Bowler"}],
    )

    row = (
        await db_session.execute(
            select(HistoricalSourcePlayerRegistry).where(
                HistoricalSourcePlayerRegistry.normalized_name == "conflict player"
            )
        )
    ).scalars().first()
    assert row is not None
    assert row.review_required is True
    assert row.metadata_conflicts
    conflict = row.metadata_conflicts[0]
    assert conflict["field_name"] == "player_role"
    assert conflict["canonical_value"] == "Batsman"
    assert conflict["observed_value"] == "Bowler"
    assert conflict["review_state"] == "pending_review"

    canonical = await db_session.get(Player, 505)
    assert canonical is not None
    assert canonical.role == "Batsman"


@pytest.mark.asyncio
async def test_phase10f_career_profile_cross_match_consistency(db_session: AsyncSession) -> None:
    db_session.add(Player(id=606, name="Career Player", role=None))
    await db_session.commit()

    first_game_id = await _make_batch(
        db_session,
        roster_names=["Career Player"],
        competition_name="Caribbean Premier League",
        season="2013",
        roster_entries=[{"name": "Career Player", "role": "Bowler"}],
    )
    second_game_id = await _make_batch(
        db_session,
        roster_names=["Career Player"],
        competition_name="Caribbean Premier League",
        season="2014",
        roster_entries=[{"name": "Career Player", "role": "Bowler"}],
    )

    row = (
        await db_session.execute(
            select(HistoricalSourcePlayerRegistry).where(
                HistoricalSourcePlayerRegistry.normalized_name == "career player"
            )
        )
    ).scalars().first()
    assert row is not None
    foundation = row.career_profile_foundation
    assert foundation["matches_played"] == 2
    timeline_game_ids = {item["game_id"] for item in foundation["match_timeline"]}
    assert timeline_game_ids == {first_game_id, second_game_id}
    seasons = {item["season"] for item in foundation["seasons"]}
    assert seasons == {"2013", "2014"}


@pytest.mark.asyncio
async def test_phase10g_roster_tracks_named_playing_xi_and_substitute(db_session: AsyncSession) -> None:
    db_session.add(Player(id=701, name="Roster Captain", role="All-rounder"))
    await db_session.commit()

    game_id = await _make_batch(
        db_session,
        roster_names=["Roster Captain", "Bench Player", "Impact Sub", "Detached Player"],
        roster_snapshot=[
            {
                "team_name": "Team A",
                "named_squad": ["Roster Captain", "Bench Player"],
                "playing_xi": ["Roster Captain"],
                "substitutes": ["Impact Sub"],
                "unresolved_entries": [],
            }
        ],
    )

    rows = (
        await db_session.execute(
            select(HistoricalCompetitionRosterEntry).where(
                HistoricalCompetitionRosterEntry.game_id == game_id,
                HistoricalCompetitionRosterEntry.team_name == "Team A",
            )
        )
    ).scalars().all()

    status_by_name: dict[str, set[str]] = {}
    for row in rows:
        status_by_name.setdefault(row.source_player_name, set()).add(row.roster_status.value)
        assert row.provenance_references

    assert status_by_name["Roster Captain"] == {"named_squad", "playing_xi"}
    assert status_by_name["Bench Player"] == {"named_squad"}
    assert status_by_name["Impact Sub"] == {"substitute"}
    fallback_row = (
        await db_session.execute(
            select(HistoricalCompetitionRosterEntry).where(
                HistoricalCompetitionRosterEntry.game_id == game_id,
                HistoricalCompetitionRosterEntry.team_name.is_(None),
                HistoricalCompetitionRosterEntry.source_player_name == "Detached Player",
                HistoricalCompetitionRosterEntry.roster_status
                == HistoricalCompetitionRosterStatus.unavailable_unknown,
            )
        )
    ).scalars().first()
    assert fallback_row is not None


@pytest.mark.asyncio
async def test_phase10g_unresolved_roster_entry_preserves_source_identity(db_session: AsyncSession) -> None:
    await _make_batch(
        db_session,
        roster_names=["Unknown Trialist"],
        roster_snapshot=[
            {
                "team_name": "Team A",
                "named_squad": [],
                "playing_xi": [],
                "substitutes": [],
                "unresolved_entries": [{"name": "Unknown Trialist", "source_player_id": "src-u1"}],
            }
        ],
    )

    unresolved = (
        await db_session.execute(
            select(HistoricalCompetitionRosterEntry).where(
                HistoricalCompetitionRosterEntry.source_player_name == "Unknown Trialist",
                HistoricalCompetitionRosterEntry.roster_status
                == HistoricalCompetitionRosterStatus.unresolved,
            )
        )
    ).scalars().first()
    assert unresolved is not None
    assert unresolved.canonical_player_id is None
    assert unresolved.source_player_id == "src-u1"
    assert unresolved.provenance_references


@pytest.mark.asyncio
async def test_phase10g_player_movement_across_seasons_is_safe(db_session: AsyncSession) -> None:
    db_session.add(Player(id=702, name="Mover Player", role="Batsman"))
    await db_session.commit()

    await _make_batch(
        db_session,
        roster_names=["Mover Player"],
        competition_name="Caribbean Premier League",
        season="2013",
        roster_snapshot=[
            {
                "team_name": "Team A",
                "named_squad": ["Mover Player"],
                "playing_xi": ["Mover Player"],
                "substitutes": [],
                "unresolved_entries": [],
            }
        ],
    )
    await _make_batch(
        db_session,
        roster_names=["Mover Player"],
        competition_name="Caribbean Premier League",
        season="2014",
        roster_snapshot=[
            {
                "team_name": "Team B",
                "named_squad": ["Mover Player"],
                "playing_xi": ["Mover Player"],
                "substitutes": [],
                "unresolved_entries": [],
            }
        ],
    )

    rows = (
        await db_session.execute(
            select(HistoricalCompetitionRosterEntry).where(
                HistoricalCompetitionRosterEntry.canonical_player_id == 702,
                HistoricalCompetitionRosterEntry.roster_status
                == HistoricalCompetitionRosterStatus.named_squad,
                HistoricalCompetitionRosterEntry.team_name.is_not(None),
            )
        )
    ).scalars().all()
    assert len(rows) == 2
    assert {row.season for row in rows} == {"2013", "2014"}
    assert {row.team_name for row in rows} == {"Team A", "Team B"}
    assert all(row.review_required is False for row in rows)


@pytest.mark.asyncio
async def test_phase10g_same_match_cross_team_conflict_marked_review_required(
    db_session: AsyncSession,
) -> None:
    db_session.add(Player(id=703, name="Conflict Roster", role="All-rounder"))
    await db_session.commit()

    game_id = await _make_batch(
        db_session,
        roster_names=["Conflict Roster"],
        roster_snapshot=[
            {
                "team_name": "Team A",
                "named_squad": ["Conflict Roster"],
                "playing_xi": ["Conflict Roster"],
                "substitutes": [],
                "unresolved_entries": [],
            },
            {
                "team_name": "Team B",
                "named_squad": ["Conflict Roster"],
                "playing_xi": ["Conflict Roster"],
                "substitutes": [],
                "unresolved_entries": [],
            },
        ],
    )

    rows = (
        await db_session.execute(
            select(HistoricalCompetitionRosterEntry).where(
                HistoricalCompetitionRosterEntry.game_id == game_id,
                HistoricalCompetitionRosterEntry.canonical_player_id == 703,
                HistoricalCompetitionRosterEntry.roster_status
                == HistoricalCompetitionRosterStatus.named_squad,
                HistoricalCompetitionRosterEntry.team_name.is_not(None),
            )
        )
    ).scalars().all()

    assert len(rows) == 2
    assert {row.team_name for row in rows} == {"Team A", "Team B"}
    assert all(row.review_required is True for row in rows)
    assert all(row.conflict_references for row in rows)
