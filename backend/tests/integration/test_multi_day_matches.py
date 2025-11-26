"""
Integration tests for multi-day (Test) match functionality.

These tests verify that the backend correctly handles:
1. Creating multi-day matches with unlimited overs
2. Playing extended innings
3. Multiple innings transitions
4. Match state persistence
"""

import pytest

from .conftest import GameHelper


class TestMultiDayMatchCreation:
    """Tests for creating multi-day matches."""

    def test_create_test_match(self, game_helper: GameHelper):
        """
        Test creating a Test match (5-day, unlimited overs).
        """
        game_id, teams = game_helper.create_game(
            match_type="multi_day",
            days_limit=5,
            overs_limit=None,  # Unlimited overs
            overs_per_day=90,
        )

        # Get game object
        response = game_helper.client.get(f"/games/{game_id}")
        assert response.status_code == 200

        game_data = response.json()
        assert game_data["match_type"] == "multi_day"
        assert game_data["days_limit"] == 5
        assert game_data["overs_limit"] is None
        # Game starts in INNINGS_BREAK waiting for openers
        assert game_data["status"] == "INNINGS_BREAK"
        assert game_data["current_inning"] == 0

    def test_create_three_day_match(self, game_helper: GameHelper):
        """
        Test creating a 3-day match.
        """
        game_id, teams = game_helper.create_game(
            match_type="multi_day",
            days_limit=3,
            overs_limit=None,
            overs_per_day=80,
        )

        response = game_helper.client.get(f"/games/{game_id}")
        assert response.status_code == 200

        game_data = response.json()
        assert game_data["match_type"] == "multi_day"
        assert game_data["days_limit"] == 3

    def test_create_four_day_match(self, game_helper: GameHelper):
        """
        Test creating a 4-day match (common for first-class cricket).
        """
        game_id, teams = game_helper.create_game(
            match_type="multi_day",
            days_limit=4,
            overs_limit=None,
            overs_per_day=96,
        )

        response = game_helper.client.get(f"/games/{game_id}")
        assert response.status_code == 200

        game_data = response.json()
        assert game_data["match_type"] == "multi_day"
        assert game_data["days_limit"] == 4


class TestMultiDayMatchPlay:
    """Tests for playing multi-day matches."""

    def test_play_extended_innings(self, game_helper: GameHelper):
        """
        Test playing an extended innings (more than 50 overs).
        """
        game_id, teams = game_helper.create_game(
            match_type="multi_day",
            days_limit=5,
            overs_limit=None,
        )

        team_a_players = teams["team_a"]
        team_b_players = teams["team_b"]

        # Set openers
        game_helper.set_openers(team="A")

        striker = team_a_players[0]["id"]
        bowler1 = team_b_players[0]["id"]
        bowler2 = team_b_players[1]["id"]

        # Play 60 overs (360 balls) - more than a typical limited-overs match
        for i in range(360):
            bowler = bowler1 if (i // 6) % 2 == 0 else bowler2
            runs = 1 if i < 300 else 2  # Accelerate in last 10 overs
            response = game_helper.post_delivery(
                batsman_id=striker,
                bowler_id=bowler,
                runs_scored=runs,
            )
            assert response.status_code == 200

        # Verify score
        snapshot = game_helper.get_snapshot()
        assert snapshot["score"]["runs"] == 420  # 300 + 120
        assert snapshot["score"]["overs"] == 60


class TestMultiDayMatchState:
    """Tests for multi-day match state management."""

    def test_match_state_persistence(self, game_helper: GameHelper):
        """
        Test that match state is correctly maintained across deliveries.
        """
        game_id, teams = game_helper.create_game(
            match_type="multi_day",
            days_limit=5,
            overs_limit=None,
        )

        team_a_players = teams["team_a"]
        team_b_players = teams["team_b"]

        game_helper.set_openers(team="A")
        striker = team_a_players[0]["id"]
        bowler = team_b_players[0]["id"]

        # Play 1 over
        for i in range(6):
            response = game_helper.post_delivery(
                batsman_id=striker,
                bowler_id=bowler,
                runs_scored=1,
            )
            assert response.status_code == 200

        # Check state after 1 over
        response = game_helper.client.get(f"/games/{game_id}")
        game_data = response.json()

        assert game_data["total_runs"] == 6
        assert game_data["overs_completed"] == 1
        assert game_data["balls_this_over"] == 0
        assert game_data["current_inning"] == 1
        assert game_data["status"] == "IN_PROGRESS"

    def test_deliveries_list_populated(self, game_helper: GameHelper):
        """
        Test that deliveries list is correctly populated.
        """
        game_id, teams = game_helper.create_game(
            match_type="multi_day",
            days_limit=5,
            overs_limit=None,
        )

        team_a_players = teams["team_a"]
        team_b_players = teams["team_b"]

        game_helper.set_openers(team="A")
        striker = team_a_players[0]["id"]
        bowler = team_b_players[0]["id"]

        # Play 3 deliveries
        for i in range(3):
            response = game_helper.post_delivery(
                batsman_id=striker,
                bowler_id=bowler,
                runs_scored=i,  # 0, 1, 2
            )
            assert response.status_code == 200

        # Check deliveries list
        response = game_helper.client.get(f"/games/{game_id}")
        game_data = response.json()

        assert "deliveries" in game_data
        deliveries = game_data["deliveries"]
        assert len(deliveries) == 3

        # Verify delivery details
        assert deliveries[0]["runs_scored"] == 0
        assert deliveries[1]["runs_scored"] == 1
        assert deliveries[2]["runs_scored"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
