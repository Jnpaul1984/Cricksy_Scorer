"""
Tests for new backend endpoints: metrics, phase analysis, org stats, and tournament leaderboards.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from backend.main import app
from backend.sql_app import models, crud
from backend.sql_app.schemas import GameCreate


@pytest.fixture
async def test_game(db_session: AsyncSession):
    """Create a test game with deliveries for testing."""
    game_id = str(uuid4())
    
    game = models.Game(
        id=game_id,
        match_type="limited",
        overs_limit=20,
        dls_enabled=False,
        toss_winner_team="Team A",
        decision="bat",
        team_a={"name": "Team A", "players": [{"id": "batter_1", "name": "Test Batter 1"}, {"id": "batter_2", "name": "Test Batter 2"}]},
        team_b={"name": "Team B", "players": [{"id": "bowler_1", "name": "Test Bowler 1"}]},
        batting_team_name="Team A",
        bowling_team_name="Team B",
        status=models.GameStatus.in_progress,
        current_inning=1,
        total_runs=125,
        total_wickets=3,
        overs_completed=18,
        balls_this_over=2,
        batting_scorecard={
            "batter_1": {
                "player_id": "batter_1",
                "player_name": "Test Batter 1",
                "runs": 45,
                "balls_faced": 32,
            },
            "batter_2": {
                "player_id": "batter_2",
                "player_name": "Test Batter 2",
                "runs": 38,
                "balls_faced": 28,
            },
        },
        bowling_scorecard={
            "bowler_1": {
                "player_id": "bowler_1",
                "player_name": "Test Bowler 1",
                "overs_bowled": 4,
                "runs_conceded": 32,
                "wickets_taken": 2,
                "economy": 8.0,
            },
        },
    )
    
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)
    
    # Add some deliveries
    deliveries = [
        # Powerplay (overs 1-6)
        models.Delivery(
            id=str(uuid4()),
            game_id=game_id,
            over_number=1,
            ball_number=1,
            bowler_id="bowler_1",
            striker_id="batter_1",
            non_striker_id="batter_2",
            runs_scored=2,
            runs_off_bat=2,
            is_wicket=False,
        ),
        models.Delivery(
            id=str(uuid4()),
            game_id=game_id,
            over_number=2,
            ball_number=1,
            bowler_id="bowler_1",
            striker_id="batter_1",
            non_striker_id="batter_2",
            runs_scored=4,
            runs_off_bat=4,
            is_wicket=False,
        ),
        # Middle overs (7-16)
        models.Delivery(
            id=str(uuid4()),
            game_id=game_id,
            over_number=10,
            ball_number=1,
            bowler_id="bowler_1",
            striker_id="batter_1",
            non_striker_id="batter_2",
            runs_scored=0,
            runs_off_bat=0,
            is_wicket=True,
        ),
        # Death overs (17-20)
        models.Delivery(
            id=str(uuid4()),
            game_id=game_id,
            over_number=18,
            ball_number=1,
            bowler_id="bowler_1",
            striker_id="batter_2",
            non_striker_id="batter_1",
            runs_scored=6,
            runs_off_bat=6,
            is_wicket=False,
        ),
    ]
    
    for delivery in deliveries:
        db_session.add(delivery)
    
    await db_session.commit()
    
    return game_id


class TestGameMetricsEndpoint:
    """Tests for GET /games/{gameId}/metrics"""
    
    @pytest.mark.asyncio
    async def test_get_game_metrics_success(self, async_client: AsyncClient, test_game: str):
        """Test successful retrieval of game metrics."""
        game_id = test_game
        
        response = await async_client.get(f"/games/{game_id}/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "game_id" in data
        assert "score" in data
        assert "wickets" in data
        assert "overs" in data
        assert "balls_remaining" in data
        assert "current_run_rate" in data
        assert "extras" in data
        assert isinstance(data["extras"], dict)
    
    @pytest.mark.asyncio
    async def test_get_game_metrics_not_found(self, async_client: AsyncClient):
        """Test metrics endpoint with non-existent game."""
        response = await async_client.get(f"/games/nonexistent/metrics")
        assert response.status_code == 404


class TestPhaseAnalysisEndpoint:
    """Tests for GET /games/{gameId}/phase-analysis"""
    
    @pytest.mark.asyncio
    async def test_get_phase_analysis_success(self, async_client: AsyncClient, test_game: str):
        """Test successful retrieval of phase analysis."""
        game_id = test_game
        
        response = await async_client.get(f"/games/{game_id}/phase-analysis")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify structure
        assert "game_id" in data
        assert "powerplay" in data
        assert "middle" in data
        assert "death" in data
        
        # Verify phase structure
        for phase_name in ["powerplay", "middle", "death"]:
            phase = data[phase_name]
            assert "total_runs" in phase
            assert "avg_per_over" in phase
            assert "fours" in phase
            assert "sixes" in phase
            assert "wickets" in phase
            assert "strike_rate" in phase
            assert "batting_order" in phase
            assert isinstance(phase["batting_order"], list)
    
    @pytest.mark.asyncio
    async def test_get_phase_analysis_not_found(self, async_client: AsyncClient):
        """Test phase analysis with non-existent game."""
        response = await async_client.get(f"/games/nonexistent/phase-analysis")
        assert response.status_code == 404


class TestOrganizationStatsEndpoint:
    """Tests for GET /organizations/{orgId}/stats"""
    
    @pytest.mark.asyncio
    async def test_get_org_stats_success(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test successful retrieval of organization stats."""
        org_id = str(uuid4())
        
        response = await async_client.get(f"/api/teams/organizations/{org_id}/stats")
        
        # Endpoint should return data even for non-existent org (empty stats)
        assert response.status_code == 200
        data = response.json()
        
        assert "total_teams" in data
        assert "total_matches" in data
        assert "season_win_rate" in data
        assert "avg_run_rate" in data
        assert "powerplay_net_runs" in data
        assert "middle_net_runs" in data
        assert "death_net_runs" in data
        assert "death_over_economy" in data


class TestOrganizationTeamsEndpoint:
    """Tests for GET /organizations/{orgId}/teams"""
    
    @pytest.mark.asyncio
    async def test_get_org_teams_success(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test successful retrieval of organization teams."""
        org_id = str(uuid4())
        
        response = await async_client.get(f"/api/teams/organizations/{org_id}/teams")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "teams" in data
        assert isinstance(data["teams"], list)
        
        if len(data["teams"]) > 0:
            team = data["teams"][0]
            assert "id" in team
            assert "name" in team
            assert "played" in team
            assert "won" in team
            assert "lost" in team
            assert "win_percent" in team
            assert "avg_score" in team
            assert "nrr" in team


class TestTournamentLeaderboardsEndpoint:
    """Tests for GET /tournaments/{tournamentId}/leaderboards"""
    
    @pytest.mark.asyncio
    async def test_get_tournament_leaderboards_success(self, async_client: AsyncClient, db_session: AsyncSession):
        """Test successful retrieval of tournament leaderboards."""
        tournament_id = str(uuid4())
        
        response = await async_client.get(
            f"/tournaments/{tournament_id}/leaderboards",
            params={"type": "all", "limit": 10}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "batting" in data
        assert "bowling" in data
        assert isinstance(data["batting"], list)
        assert isinstance(data["bowling"], list)
    
    @pytest.mark.asyncio
    async def test_get_batting_leaderboard_only(self, async_client: AsyncClient):
        """Test filtering by batting leaderboard only."""
        tournament_id = str(uuid4())
        
        response = await async_client.get(
            f"/tournaments/{tournament_id}/leaderboards",
            params={"type": "batting", "limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "batting" in data
        assert "bowling" in data
        assert len(data["batting"]) <= 5
        assert len(data["bowling"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_bowling_leaderboard_only(self, async_client: AsyncClient):
        """Test filtering by bowling leaderboard only."""
        tournament_id = str(uuid4())
        
        response = await async_client.get(
            f"/tournaments/{tournament_id}/leaderboards",
            params={"type": "bowling", "limit": 5}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "batting" in data
        assert "bowling" in data
        assert len(data["batting"]) == 0
        assert len(data["bowling"]) <= 5


# Sample curl commands for manual testing
"""
CURL COMMANDS FOR TESTING:

1. Get game metrics:
   curl -X GET "http://localhost:8000/games/{gameId}/metrics" \\
     -H "accept: application/json"

2. Get phase analysis:
   curl -X GET "http://localhost:8000/games/{gameId}/phase-analysis" \\
     -H "accept: application/json"

3. Get organization stats:
   curl -X GET "http://localhost:8000/api/teams/organizations/{orgId}/stats" \\
     -H "accept: application/json"

4. Get organization teams:
   curl -X GET "http://localhost:8000/api/teams/organizations/{orgId}/teams" \\
     -H "accept: application/json"

5. Get tournament leaderboards (all):
   curl -X GET "http://localhost:8000/tournaments/{tournamentId}/leaderboards?type=all&limit=10" \\
     -H "accept: application/json"

6. Get tournament batting leaderboard:
   curl -X GET "http://localhost:8000/tournaments/{tournamentId}/leaderboards?type=batting&limit=10" \\
     -H "accept: application/json"

7. Get tournament bowling leaderboard:
   curl -X GET "http://localhost:8000/tournaments/{tournamentId}/leaderboards?type=bowling&limit=10" \\
     -H "accept: application/json"
"""
