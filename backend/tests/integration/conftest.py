"""
Integration Test Framework for Cricksy Scorer

Provides fixtures and utilities for integration testing including:
- Test client setup
- Game creation helpers
- Player management
- Delivery posting utilities
- Assertion helpers
"""

import pytest
from typing import Dict, List, Any, Optional
from fastapi.testclient import TestClient
from backend.main import _fastapi as app


@pytest.fixture
def api_client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_game(api_client):
    """Create a sample game with default settings."""
    response = api_client.post("/games", json={
        "team_a_name": "Team Alpha",
        "team_b_name": "Team Beta",
        "overs_limit": 20,
        "players_per_team": 11
    })
    assert response.status_code == 200
    return response.json()


class GameHelper:
    """Helper class for game operations in integration tests."""
    
    def __init__(self, client: TestClient):
        self.client = client
        self.game_id: Optional[str] = None
        self.game_data: Optional[Dict] = None
        self.team_a_players: List[Dict] = []
        self.team_b_players: List[Dict] = []
    
    def create_game(
        self,
        team_a_name: str = "Team Alpha",
        team_b_name: str = "Team Beta",
        overs_limit: Optional[int] = 20,
        players_per_team: int = 11,
        match_type: Optional[str] = None,
        days_limit: Optional[int] = None,
        overs_per_day: Optional[int] = None,
    ) -> tuple[str, Dict[str, Any]]:
        """Create a new game and store its data.
        
        Returns:
            Tuple of (game_id, teams_dict) where teams_dict contains team_a and team_b player lists
        """
        # Generate player names
        players_a = [f"Player A{i+1}" for i in range(players_per_team)]
        players_b = [f"Player B{i+1}" for i in range(players_per_team)]
        
        payload = {
            "team_a_name": team_a_name,
            "team_b_name": team_b_name,
            "players_a": players_a,
            "players_b": players_b,
            "overs_limit": overs_limit,
            "toss_winner_team": "A",
            "decision": "bat"
        }
        
        # Add multi-day match parameters if provided
        if match_type is not None:
            payload["match_type"] = match_type
        if days_limit is not None:
            payload["days_limit"] = days_limit
        if overs_per_day is not None:
            payload["overs_per_day"] = overs_per_day
        
        response = self.client.post("/games", json=payload)
        assert response.status_code == 200, f"Failed to create game: {response.text}"
        
        self.game_data = response.json()
        self.game_id = self.game_data["id"]
        self.team_a_players = self.game_data["team_a"]["players"]
        self.team_b_players = self.game_data["team_b"]["players"]
        
        # Return tuple of (game_id, teams_dict)
        teams = {
            "team_a": self.team_a_players,
            "team_b": self.team_b_players
        }
        return self.game_id, teams
    
    def set_openers(
        self,
        striker_id: Optional[str] = None,
        non_striker_id: Optional[str] = None,
        team: str = "A"
    ) -> Dict[str, Any]:
        """Set openers for a team."""
        assert self.game_id, "Game must be created first"
        
        # Use first two players if not specified
        if striker_id is None:
            striker_id = self.team_a_players[0]["id"] if team == "A" else self.team_b_players[0]["id"]
        if non_striker_id is None:
            non_striker_id = self.team_a_players[1]["id"] if team == "A" else self.team_b_players[1]["id"]
        
        response = self.client.post(f"/games/{self.game_id}/openers", json={
            "striker_id": striker_id,
            "non_striker_id": non_striker_id,
            "team": team
        })
        assert response.status_code == 200, f"Failed to set openers: {response.text}"
        return response.json()
    
    def post_delivery(
        self,
        batsman_id: str,
        bowler_id: str,
        runs_scored: int = 0,
        is_wicket: bool = False,
        dismissal_type: Optional[str] = None,
        extra_type: Optional[str] = None,
        runs_off_bat: Optional[int] = None,
        fielder_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Post a delivery to the game."""
        assert self.game_id, "Game must be created first"
        
        payload = {
            "bowler_id": bowler_id,
            "runs_scored": runs_scored
        }
        
        if is_wicket:
            payload["is_wicket"] = True
            payload["dismissal_type"] = dismissal_type or "bowled"
            if fielder_id:
                payload["fielder_id"] = fielder_id
        
        if extra_type:
            payload["extra"] = extra_type
        
        if runs_off_bat is not None:
            payload["runs_off_bat"] = runs_off_bat
        
        response = self.client.post(f"/games/{self.game_id}/deliveries", json=payload)
        return response
    
    def select_next_batsman(self, batter_id: str) -> Dict[str, Any]:
        """Select the next batsman after a wicket."""
        assert self.game_id, "Game must be created first"
        
        response = self.client.post(f"/games/{self.game_id}/next-batter", json={
            "batter_id": batter_id
        })
        assert response.status_code == 200, f"Failed to select batsman: {response.text}"
        return response.json()
    
    def start_next_innings(
        self,
        striker_id: str,
        non_striker_id: str,
        opening_bowler_id: str
    ) -> Dict[str, Any]:
        """Start the next innings."""
        assert self.game_id, "Game must be created first"
        
        response = self.client.post(f"/games/{self.game_id}/innings/start", json={
            "striker_id": striker_id,
            "non_striker_id": non_striker_id,
            "opening_bowler_id": opening_bowler_id
        })
        assert response.status_code == 200, f"Failed to start innings: {response.text}"
        return response.json()
    
    def finalize_game(self) -> Dict[str, Any]:
        """Finalize the game."""
        assert self.game_id, "Game must be created first"
        
        response = self.client.post(f"/games/{self.game_id}/finalize")
        assert response.status_code == 200, f"Failed to finalize game: {response.text}"
        return response.json()
    
    def get_snapshot(self) -> Dict[str, Any]:
        """Get the current game snapshot."""
        assert self.game_id, "Game must be created first"
        
        response = self.client.get(f"/games/{self.game_id}/snapshot")
        assert response.status_code == 200, f"Failed to get snapshot: {response.text}"
        return response.json()
    
    def get_deliveries(self) -> List[Dict[str, Any]]:
        """Get all deliveries for the game."""
        assert self.game_id, "Game must be created first"
        
        response = self.client.get(f"/games/{self.game_id}/deliveries")
        assert response.status_code == 200, f"Failed to get deliveries: {response.text}"
        return response.json()["deliveries"]
    
    def post_over(
        self,
        batsman_id: str,
        bowler_id: str,
        balls: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Post a complete over (6 legal deliveries)."""
        responses = []
        for ball in balls:
            response = self.post_delivery(
                batsman_id=ball.get("batsman_id", batsman_id),
                bowler_id=bowler_id,
                runs_scored=ball.get("runs", 0),
                is_wicket=ball.get("is_wicket", False),
                dismissal_type=ball.get("dismissal_type"),
                extra_type=ball.get("extra_type"),
                fielder_id=ball.get("fielder_id")
            )
            responses.append(response)
            
            # If wicket, select next batsman
            if ball.get("is_wicket") and ball.get("next_batsman_id"):
                self.select_next_batsman(ball["next_batsman_id"])
        
        return responses


@pytest.fixture
def game_helper(api_client):
    """Provide a GameHelper instance for tests."""
    return GameHelper(api_client)


class AssertionHelper:
    """Helper class for common assertions in integration tests."""
    
    @staticmethod
    def assert_wicket_count(deliveries: List[Dict], expected: int):
        """Assert the number of wickets in deliveries."""
        actual = sum(1 for d in deliveries if d.get("is_wicket"))
        assert actual == expected, f"Expected {expected} wickets, got {actual}"
    
    @staticmethod
    def assert_runs_scored(deliveries: List[Dict], expected: int):
        """Assert the total runs scored."""
        actual = sum(d.get("runs_scored", 0) for d in deliveries)
        assert actual == expected, f"Expected {expected} runs, got {actual}"
    
    @staticmethod
    def assert_pending_batsman(snapshot: Dict, expected: bool):
        """Assert the needs_new_batter flag (computed from is_out status)."""
        actual = snapshot.get("needs_new_batter", False)
        assert actual == expected, \
            f"Expected needs_new_batter={expected}, got {actual}"
    
    @staticmethod
    def assert_innings_summary(
        snapshot: Dict,
        runs: Optional[int] = None,
        wickets: Optional[int] = None,
        overs: Optional[int] = None
    ):
        """Assert first innings summary values."""
        summary = snapshot.get("first_inning_summary")
        assert summary is not None, "first_inning_summary not found in snapshot"
        
        if runs is not None:
            actual_runs = summary.get("runs")
            assert actual_runs == runs, \
                f"Expected {runs} runs in summary, got {actual_runs}"
        
        if wickets is not None:
            actual_wickets = summary.get("wickets")
            assert actual_wickets == wickets, \
                f"Expected {wickets} wickets in summary, got {actual_wickets}"
        
        if overs is not None:
            actual_overs = summary.get("overs")
            assert actual_overs == overs, \
                f"Expected {overs} overs in summary, got {actual_overs}"
    
    @staticmethod
    def assert_game_result(snapshot: Dict, expected_winner: Optional[str] = None):
        """Assert game result."""
        result = snapshot.get("result")
        assert result is not None, "Result not found in snapshot"
        
        if expected_winner:
            result_text = result.get("result_text", "")
            assert expected_winner in result_text, \
                f"Expected '{expected_winner}' in result, got: {result_text}"


@pytest.fixture
def assert_helper():
    """Provide an AssertionHelper instance for tests."""
    return AssertionHelper()


# Utility functions

def create_simple_over(runs_per_ball: List[int]) -> List[Dict[str, Any]]:
    """Create a simple over with specified runs per ball."""
    return [{"runs": r} for r in runs_per_ball]


def create_wicket_over(
    wicket_ball: int,
    runs_before: List[int],
    runs_after: List[int],
    dismissal_type: str = "bowled",
    next_batsman_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Create an over with a wicket at specified ball number."""
    balls = []
    
    # Balls before wicket
    for r in runs_before:
        balls.append({"runs": r})
    
    # Wicket ball
    balls.append({
        "runs": 0,
        "is_wicket": True,
        "dismissal_type": dismissal_type,
        "next_batsman_id": next_batsman_id
    })
    
    # Balls after wicket
    for r in runs_after:
        balls.append({"runs": r})
    
    return balls




