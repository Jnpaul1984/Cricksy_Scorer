"""
Tests for new backend endpoints: metrics, phase analysis, org stats, and tournament leaderboards.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from backend.sql_app import models


@pytest.fixture
async def test_game(async_client: AsyncClient):
    """Create a test game via API for testing."""
    # Create game via API (follows DEPLOY_BACKEND_PROTOCOL guidelines)
    create_response = await async_client.post(
        "/games",
        json={
            "match_type": "limited",
            "overs_limit": 20,
            "team_a_name": "Team A",
            "team_b_name": "Team B",
            "players_a": ["bat1", "bat2"],
            "players_b": ["bowl1", "bowl2"],
            "toss_winner_team": "Team A",
            "decision": "bat",
        },
    )
    assert create_response.status_code in (200, 201), f"Failed to create game: {create_response.text}"
    game_data = create_response.json()
    game_id = game_data.get("id") or game_data.get("gid") or game_data.get("game", {}).get("id")
    
    # Get full game details to extract player IDs
    game_response = await async_client.get(f"/games/{game_id}")
    assert game_response.status_code == 200
    game_details = game_response.json()
    
    # Extract actual player IDs from response
    striker_id = game_details["team_a"]["players"][0]["id"]
    non_striker_id = game_details["team_a"]["players"][1]["id"]
    bowler_id = game_details["team_b"]["players"][0]["id"]
    
    # Score a few deliveries via API
    for _ in range(6):  # Score 6 legal deliveries
        score_response = await async_client.post(
            f"/games/{game_id}/deliveries",
            json={
                "striker_id": striker_id,
                "non_striker_id": non_striker_id,
                "bowler_id": bowler_id,
                "runs_scored": 4,
                "runs_off_bat": 0,
                "extra": None,
                "is_wicket": False,
            },
        )
        assert score_response.status_code == 200, f"Failed to score: {score_response.text}"
    
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
