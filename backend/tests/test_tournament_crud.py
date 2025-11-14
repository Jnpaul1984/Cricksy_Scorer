"""Unit tests for tournament CRUD operations"""
from __future__ import annotations

import datetime as dt
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.sql_app import models, schemas, tournament_crud

UTC = getattr(dt, "UTC", dt.UTC)


@pytest.fixture
def mock_session():
    """Mock database session"""
    session = AsyncMock()
    return session


@pytest.mark.asyncio
async def test_create_tournament(mock_session):
    """Test creating a tournament"""
    tournament_data = schemas.TournamentCreate(
        name="Test League",
        description="A test tournament",
        tournament_type="league",
    )

    with patch.object(mock_session, "add") as mock_add, patch.object(
        mock_session, "commit"
    ) as mock_commit, patch.object(mock_session, "refresh") as mock_refresh:
        result = await tournament_crud.create_tournament(mock_session, tournament_data)

        mock_add.assert_called_once()
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once()
        assert isinstance(result, models.Tournament)
        assert result.name == "Test League"
        assert result.tournament_type == "league"


@pytest.mark.asyncio
async def test_add_team_to_tournament(mock_session):
    """Test adding a team to a tournament"""
    tournament = models.Tournament(
        id="test-tournament-id",
        name="Test League",
        tournament_type="league",
        status="upcoming",
        created_at=dt.datetime.now(UTC),
        updated_at=dt.datetime.now(UTC),
    )

    team_data = schemas.TeamAdd(
        team_name="Test Team",
        team_data={"players": [{"id": "1", "name": "Player 1"}]},
    )

    # Mock the get_tournament call
    with patch.object(
        tournament_crud, "get_tournament", return_value=tournament
    ) as mock_get, patch.object(mock_session, "add") as mock_add, patch.object(
        mock_session, "commit"
    ) as mock_commit, patch.object(
        mock_session, "refresh"
    ) as mock_refresh:
        result = await tournament_crud.add_team_to_tournament(
            mock_session, "test-tournament-id", team_data
        )

        mock_get.assert_called_once_with(mock_session, "test-tournament-id")
        mock_add.assert_called_once()
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once()
        assert isinstance(result, models.TournamentTeam)
        assert result.team_name == "Test Team"


@pytest.mark.asyncio
async def test_update_team_stats_win(mock_session):
    """Test updating team stats after a win"""
    team = models.TournamentTeam(
        id=1,
        tournament_id="test-tournament-id",
        team_name="Test Team",
        team_data={},
        matches_played=0,
        matches_won=0,
        matches_lost=0,
        matches_drawn=0,
        points=0,
        net_run_rate=0.0,
    )

    # Mock the select query
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = team
    mock_session.execute = AsyncMock(return_value=mock_result)

    with patch.object(mock_session, "commit") as mock_commit, patch.object(
        mock_session, "refresh"
    ) as mock_refresh:
        result = await tournament_crud.update_team_stats(
            mock_session,
            "test-tournament-id",
            "Test Team",
            won=True,
            runs_scored=180,
            runs_conceded=150,
            overs_faced=20.0,
            overs_bowled=20.0,
        )

        mock_commit.assert_called_once()
        mock_refresh.assert_called_once()
        assert result.matches_played == 1
        assert result.matches_won == 1
        assert result.points == 2
        assert result.net_run_rate > 0  # Won with better run rate


@pytest.mark.asyncio
async def test_create_fixture(mock_session):
    """Test creating a fixture"""
    fixture_data = schemas.FixtureCreate(
        tournament_id="test-tournament-id",
        match_number=1,
        team_a_name="Team A",
        team_b_name="Team B",
        venue="Test Stadium",
        scheduled_date=dt.datetime.now(UTC),
    )

    with patch.object(mock_session, "add") as mock_add, patch.object(
        mock_session, "commit"
    ) as mock_commit, patch.object(mock_session, "refresh") as mock_refresh:
        result = await tournament_crud.create_fixture(mock_session, fixture_data)

        mock_add.assert_called_once()
        mock_commit.assert_called_once()
        mock_refresh.assert_called_once()
        assert isinstance(result, models.Fixture)
        assert result.team_a_name == "Team A"
        assert result.team_b_name == "Team B"


@pytest.mark.asyncio
async def test_get_points_table(mock_session):
    """Test getting points table"""
    teams = [
        models.TournamentTeam(
            id=1,
            tournament_id="test-tournament-id",
            team_name="Team A",
            team_data={},
            matches_played=2,
            matches_won=2,
            matches_lost=0,
            matches_drawn=0,
            points=4,
            net_run_rate=1.5,
        ),
        models.TournamentTeam(
            id=2,
            tournament_id="test-tournament-id",
            team_name="Team B",
            team_data={},
            matches_played=2,
            matches_won=1,
            matches_lost=1,
            matches_drawn=0,
            points=2,
            net_run_rate=0.5,
        ),
    ]

    with patch.object(
        tournament_crud, "get_tournament_teams", return_value=teams
    ) as mock_get:
        result = await tournament_crud.get_points_table(
            mock_session, "test-tournament-id"
        )

        mock_get.assert_called_once_with(mock_session, "test-tournament-id")
        assert len(result) == 2
        assert result[0].team_name == "Team A"
        assert result[0].points == 4
        assert result[1].team_name == "Team B"
        assert result[1].points == 2
