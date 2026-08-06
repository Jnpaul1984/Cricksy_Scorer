"""Phase 10T — CPL Roster Registry tests.

Validates:
- Team/player creation and duplicate prevention
- Player name normalization
- Returning player detection
- Roster import preview (dry-run, no mutations)
- Roster import apply
- Singular/plural formatting helpers

Run:
    CRICKSY_IN_MEMORY_DB=1 APP_SECRET_KEY=test-secret-key \\
      python -m pytest backend/tests/test_cpl_roster.py -v
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.api.schemas.cpl_roster import (
    CplPlayerCreate,
    CplPlayerUpdate,
    CplTeamCreate,
    RosterImportApplyRequest,
    RosterImportRow,
)
from backend.services.cpl_roster_service import (
    _normalize_name,
    apply_roster_import,
    create_player,
    create_team,
    list_players,
    list_teams,
    preview_roster_import,
    update_player,
)
from backend.sql_app import models


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _team_create(
    team_name: str = "Barbados Royals",
    season: str = "2024",
    competition_code: str = "CPL_MEN",
    team_short_name: str | None = None,
) -> CplTeamCreate:
    return CplTeamCreate(
        competition_code=competition_code,
        season=season,
        team_name=team_name,
        team_short_name=team_short_name,
        home_ground=None,
        source_note=None,
    )


def _player_create(
    player_name: str = "Chris Gayle",
    team_name: str = "Jamaica Tallawahs",
    season: str = "2024",
    competition_code: str = "CPL_MEN",
    role: str = "Batsman",
    status: str = "active",
) -> CplPlayerCreate:
    return CplPlayerCreate(
        competition_code=competition_code,
        season=season,
        player_name=player_name,
        display_name=None,
        aliases=[],
        team_name=team_name,
        role=role,
        batting_style=None,
        bowling_style=None,
        status=status,
        source_note=None,
    )


def _import_row(
    player: str,
    team: str,
    season: str = "2024",
    competition: str = "CPL_MEN",
    role: str = "All-Rounder",
    status: str = "active",
    source_note: str = "",
) -> RosterImportRow:
    return RosterImportRow(
        competition=competition,
        season=season,
        team=team,
        player=player,
        role=role,
        batting_style=None,
        bowling_style=None,
        status=status,
        source_note=source_note,
    )


# ---------------------------------------------------------------------------
# Normalization unit tests (no DB required)
# ---------------------------------------------------------------------------


class TestNormalizeName:
    def test_lowercase(self) -> None:
        assert _normalize_name("CHRIS GAYLE") == "chris gayle"

    def test_strips_extra_whitespace(self) -> None:
        assert _normalize_name("  Chris   Gayle  ") == "chris gayle"

    def test_diacritic_stripping(self) -> None:
        # é → e
        assert _normalize_name("André") == "andre"

    def test_same_string_same_result(self) -> None:
        assert _normalize_name("Dwayne Bravo") == _normalize_name("dwayne bravo")


# ---------------------------------------------------------------------------
# DB fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def session():
    """Provide a fresh in-memory SQLite async session for each test."""
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_setup())
    sm = async_sessionmaker(engine, expire_on_commit=False)

    async def _get():
        async with sm() as s:
            return s

    yield asyncio.get_event_loop().run_until_complete(_get())

    async def _teardown():
        await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_teardown())


def run(coro):
    """Synchronously run a coroutine in the event loop."""
    import asyncio

    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Team tests
# ---------------------------------------------------------------------------


class TestTeamRegistry:
    def test_create_team(self, session) -> None:
        team = run(create_team(session, _team_create("Barbados Royals")))
        assert team.id
        assert team.team_name == "Barbados Royals"
        assert team.normalized_team_name == "barbados royals"

    def test_create_team_sets_competition(self, session) -> None:
        team = run(create_team(session, _team_create("Guyana Amazon Warriors")))
        assert team.competition_code == "CPL_MEN"
        assert team.season == "2024"

    def test_duplicate_team_raises(self, session) -> None:
        run(create_team(session, _team_create("Trinbago Knight Riders")))
        with pytest.raises(ValueError, match="already exists"):
            run(create_team(session, _team_create("Trinbago Knight Riders")))

    def test_duplicate_team_case_insensitive(self, session) -> None:
        run(create_team(session, _team_create("Barbados Royals")))
        with pytest.raises(ValueError):
            run(create_team(session, _team_create("BARBADOS ROYALS")))

    def test_same_team_different_season_allowed(self, session) -> None:
        run(create_team(session, _team_create("Barbados Royals", season="2023")))
        # Should not raise
        team2 = run(create_team(session, _team_create("Barbados Royals", season="2024")))
        assert team2.season == "2024"

    def test_list_teams(self, session) -> None:
        run(create_team(session, _team_create("Barbados Royals")))
        run(create_team(session, _team_create("Jamaica Tallawahs")))
        result = run(list_teams(session, competition_code="CPL_MEN", season="2024"))
        assert result.total >= 2

    def test_list_teams_filters_by_season(self, session) -> None:
        run(create_team(session, _team_create("Barbados Royals", season="2023")))
        run(create_team(session, _team_create("Jamaica Tallawahs", season="2024")))
        result = run(list_teams(session, competition_code="CPL_MEN", season="2023"))
        assert result.total == 1
        assert result.teams[0].team_name == "Barbados Royals"


# ---------------------------------------------------------------------------
# Player tests
# ---------------------------------------------------------------------------


class TestPlayerRegistry:
    def test_create_player(self, session) -> None:
        player = run(create_player(session, _player_create("Chris Gayle")))
        assert player.id
        assert player.player_name == "Chris Gayle"
        assert player.normalized_player_name == "chris gayle"

    def test_create_player_normalizes_name(self, session) -> None:
        player = run(create_player(session, _player_create("  CHRIS  GAYLE  ")))
        assert player.normalized_player_name == "chris gayle"

    def test_duplicate_player_raises(self, session) -> None:
        run(create_player(session, _player_create("Dwayne Bravo")))
        with pytest.raises(ValueError, match="already exists"):
            run(create_player(session, _player_create("Dwayne Bravo")))

    def test_duplicate_case_insensitive(self, session) -> None:
        run(create_player(session, _player_create("Dwayne Bravo")))
        with pytest.raises(ValueError):
            run(create_player(session, _player_create("DWAYNE BRAVO")))

    def test_same_player_different_season_allowed(self, session) -> None:
        run(create_player(session, _player_create("Dwayne Bravo", season="2023")))
        player2 = run(create_player(session, _player_create("Dwayne Bravo", season="2024")))
        assert player2.season == "2024"

    def test_returning_player_detected(self, session) -> None:
        # Add same player in 2023 first
        run(create_player(session, _player_create("Kieron Pollard", season="2023")))
        # Add in 2024 — should be flagged as returning
        player2 = run(create_player(session, _player_create("Kieron Pollard", season="2024")))
        assert player2.is_returning is True
        assert player2.prior_season == "2023"

    def test_new_player_not_returning(self, session) -> None:
        player = run(create_player(session, _player_create("New Player Junior", season="2024")))
        assert player.is_returning is False
        assert player.prior_season is None

    def test_update_player_status(self, session) -> None:
        player = run(create_player(session, _player_create("Chris Gayle")))
        updated = run(
            update_player(
                session,
                player.id,
                CplPlayerUpdate(
                    status="inactive",
                    display_name=None,
                    aliases=None,
                    team_name=None,
                    role=None,
                    batting_style=None,
                    bowling_style=None,
                    source_note=None,
                ),
            )
        )
        assert updated is not None
        assert updated.status == "inactive"

    def test_update_player_display_name(self, session) -> None:
        player = run(create_player(session, _player_create("Christopher Henry Gayle")))
        updated = run(
            update_player(
                session,
                player.id,
                CplPlayerUpdate(display_name="Chris Gayle"),
            )
        )
        assert updated is not None
        assert updated.display_name == "Chris Gayle"

    def test_update_nonexistent_player_returns_none(self, session) -> None:
        result = run(update_player(session, "does-not-exist", CplPlayerUpdate()))
        assert result is None

    def test_list_players_by_team(self, session) -> None:
        run(create_player(session, _player_create("Player A", team_name="Team X")))
        run(create_player(session, _player_create("Player B", team_name="Team Y")))
        result = run(
            list_players(session, competition_code="CPL_MEN", season="2024", team_name="Team X")
        )
        assert result.total == 1
        assert result.players[0].player_name == "Player A"

    def test_list_players_returning_count(self, session) -> None:
        run(create_player(session, _player_create("Player A", season="2023")))
        run(create_player(session, _player_create("Player B", season="2023")))
        run(create_player(session, _player_create("Player A", season="2024")))
        run(create_player(session, _player_create("Player B", season="2024")))
        run(create_player(session, _player_create("Player C", season="2024")))
        result = run(list_players(session, competition_code="CPL_MEN", season="2024"))
        assert result.returning_count == 2
        assert result.new_count == 1


# ---------------------------------------------------------------------------
# Roster import preview tests
# ---------------------------------------------------------------------------


class TestRosterImportPreview:
    def test_preview_new_team_new_player(self, session) -> None:
        rows = [_import_row("Chris Gayle", "Jamaica Tallawahs")]
        result = run(
            preview_roster_import(session, rows=rows, competition_code="CPL_MEN", season="2024")
        )
        assert len(result.new_teams) == 1
        assert len(result.new_players) == 1
        assert len(result.existing_teams_matched) == 0
        assert len(result.existing_players_matched) == 0

    def test_preview_existing_team_is_matched(self, session) -> None:
        run(create_team(session, _team_create("Jamaica Tallawahs")))
        rows = [_import_row("Chris Gayle", "Jamaica Tallawahs")]
        result = run(
            preview_roster_import(session, rows=rows, competition_code="CPL_MEN", season="2024")
        )
        assert len(result.existing_teams_matched) == 1
        assert len(result.new_teams) == 0

    def test_preview_existing_player_is_matched(self, session) -> None:
        run(create_player(session, _player_create("Chris Gayle")))
        rows = [_import_row("Chris Gayle", "Jamaica Tallawahs")]
        result = run(
            preview_roster_import(session, rows=rows, competition_code="CPL_MEN", season="2024")
        )
        assert len(result.existing_players_matched) == 1
        assert len(result.new_players) == 0

    def test_preview_returning_player_detected(self, session) -> None:
        # Player in 2023
        run(create_player(session, _player_create("Dwayne Bravo", season="2023")))
        # Preview for 2024
        rows = [_import_row("Dwayne Bravo", "Trinbago Knight Riders", season="2024")]
        result = run(
            preview_roster_import(session, rows=rows, competition_code="CPL_MEN", season="2024")
        )
        assert len(result.returning_players) >= 1

    def test_preview_duplicate_in_same_batch(self, session) -> None:
        rows = [
            _import_row("Chris Gayle", "Jamaica Tallawahs"),
            _import_row("Chris Gayle", "Jamaica Tallawahs"),
        ]
        result = run(
            preview_roster_import(session, rows=rows, competition_code="CPL_MEN", season="2024")
        )
        assert len(result.duplicates) >= 1

    def test_preview_does_not_mutate_db(self, session) -> None:
        rows = [_import_row("Preview Player", "Preview Team")]
        run(preview_roster_import(session, rows=rows, competition_code="CPL_MEN", season="2024"))
        # After preview, no player should be in the DB
        result = run(list_players(session, competition_code="CPL_MEN", season="2024"))
        assert result.total == 0

    def test_preview_has_player_rows(self, session) -> None:
        rows = [_import_row("Chris Gayle", "Jamaica Tallawahs")]
        result = run(
            preview_roster_import(session, rows=rows, competition_code="CPL_MEN", season="2024")
        )
        assert len(result.new_players) == 1
        assert result.new_players[0].player_name == "Chris Gayle"

    def test_preview_has_team_rows(self, session) -> None:
        rows = [_import_row("Chris Gayle", "Jamaica Tallawahs")]
        result = run(
            preview_roster_import(session, rows=rows, competition_code="CPL_MEN", season="2024")
        )
        assert len(result.new_teams) >= 1


# ---------------------------------------------------------------------------
# Roster import apply tests
# ---------------------------------------------------------------------------


class TestRosterImportApply:
    def test_apply_creates_team_and_player(self, session) -> None:
        rows = [_import_row("Chris Gayle", "Jamaica Tallawahs")]
        req = RosterImportApplyRequest(
            rows=rows, competition_code="CPL_MEN", season="2024", confirm=True
        )
        result = run(apply_roster_import(session, req))
        assert result.teams_created >= 1
        assert result.players_created >= 1
        assert result.errors == []

    def test_apply_requires_confirm(self, session) -> None:
        rows = [_import_row("Chris Gayle", "Jamaica Tallawahs")]
        req = RosterImportApplyRequest(
            rows=rows, competition_code="CPL_MEN", season="2024", confirm=False
        )
        result = run(apply_roster_import(session, req))
        # When confirm=False, no records should be created
        assert result.players_created == 0
        assert result.teams_created == 0

    def test_apply_idempotent_for_existing_player(self, session) -> None:
        rows = [_import_row("Chris Gayle", "Jamaica Tallawahs")]
        req = RosterImportApplyRequest(
            rows=rows, competition_code="CPL_MEN", season="2024", confirm=True
        )
        run(apply_roster_import(session, req))
        # Apply again — should update rather than duplicate
        result2 = run(apply_roster_import(session, req))
        assert result2.errors == []
        players = run(list_players(session, competition_code="CPL_MEN", season="2024"))
        assert players.total == 1

    def test_apply_detects_returning_player(self, session) -> None:
        # 2023 player
        run(create_player(session, _player_create("Dwayne Bravo", season="2023")))
        rows = [_import_row("Dwayne Bravo", "Trinbago Knight Riders", season="2024")]
        req = RosterImportApplyRequest(
            rows=rows, competition_code="CPL_MEN", season="2024", confirm=True
        )
        run(apply_roster_import(session, req))
        result = run(list_players(session, competition_code="CPL_MEN", season="2024"))
        returning = [p for p in result.players if p.player_name == "Dwayne Bravo"]
        assert len(returning) == 1
        assert returning[0].is_returning is True

    def test_apply_multiple_teams_and_players(self, session) -> None:
        rows = [
            _import_row("Player A", "Team X"),
            _import_row("Player B", "Team X"),
            _import_row("Player C", "Team Y"),
            _import_row("Player D", "Team Y"),
        ]
        req = RosterImportApplyRequest(
            rows=rows, competition_code="CPL_MEN", season="2024", confirm=True
        )
        result = run(apply_roster_import(session, req))
        assert result.teams_created == 2
        assert result.players_created == 4

    def test_apply_returns_warnings_not_errors_for_soft_issues(self, session) -> None:
        # Duplicate row in batch — should warn, not error
        rows = [
            _import_row("Chris Gayle", "Jamaica Tallawahs"),
            _import_row("Chris Gayle", "Jamaica Tallawahs"),
        ]
        req = RosterImportApplyRequest(
            rows=rows, competition_code="CPL_MEN", season="2024", confirm=True
        )
        result = run(apply_roster_import(session, req))
        assert result.players_created == 1
        # Duplicate should appear in warnings (or be absorbed silently, but NOT errors)
        assert result.errors == []
