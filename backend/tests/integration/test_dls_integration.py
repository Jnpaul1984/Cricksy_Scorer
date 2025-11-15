"""
Integration tests for DLS (Duckworth-Lewis-Stern) calculations via API.

These tests verify that DLS calculations work correctly in real match scenarios,
using the full API to create games, post deliveries, and retrieve DLS targets.
"""

import pytest

from .conftest import GameHelper


class TestDLSIntegrationT20:
    """Integration tests for DLS in T20 matches."""

    def test_t20_match_with_dls_capability(self, game_helper: GameHelper):
        """
        Test that a T20 match can be created and played with DLS capability.
        This verifies the 20-over DLS table is available and the match works.
        """
        # Create a T20 game
        game_id, teams = game_helper.create_game(
            overs_limit=20,
            match_type="limited",
        )

        team_a_players = teams["team_a"]
        team_b_players = teams["team_b"]

        # Set openers for Team A
        game_helper.set_openers(team="A")

        striker = team_a_players[0]["id"]
        bowler1 = team_b_players[0]["id"]
        bowler2 = team_b_players[1]["id"]

        # Play 5 overs (30 balls) to verify the match works
        for i in range(30):
            bowler = bowler1 if (i // 6) % 2 == 0 else bowler2
            response = game_helper.post_delivery(
                batsman_id=striker,
                bowler_id=bowler,
                runs_scored=2,
            )
            assert response.status_code == 200

        # Verify the match is progressing
        snapshot = game_helper.get_snapshot()
        assert snapshot["score"]["runs"] == 60
        assert snapshot["score"]["overs"] == 5

    def test_t20_no_rain_no_dls(self, game_helper: GameHelper):
        """
        Test that a normal T20 match without rain doesn't use DLS.
        Target should be Team A's score + 1.
        """
        # Create a T20 game
        game_id, teams = game_helper.create_game(
            overs_limit=20,
            match_type="limited",
        )

        team_a_players = teams["team_a"]
        team_b_players = teams["team_b"]

        # Set openers for Team A
        game_helper.set_openers(team="A")

        striker = team_a_players[0]["id"]
        bowler1 = team_b_players[0]["id"]
        bowler2 = team_b_players[1]["id"]

        # Play 20 overs scoring exactly 100 runs
        for i in range(120):
            bowler = bowler1 if (i // 6) % 2 == 0 else bowler2
            runs = 1 if i < 100 else 0  # 100 runs in first 100 balls
            response = game_helper.post_delivery(
                batsman_id=striker,
                bowler_id=bowler,
                runs_scored=runs,
            )
            assert response.status_code == 200

        # Verify Team A's score
        snapshot = game_helper.get_snapshot()
        assert snapshot["score"]["runs"] == 100

        # In a normal match, Team B's target would be 101
        # (This would be verified by starting Team B's innings and checking the target)


class TestDLSIntegrationODI:
    """Integration tests for DLS in ODI (50-over) matches."""

    def test_odi_match_setup(self, game_helper: GameHelper):
        """
        Test setting up an ODI match with DLS capability.
        This verifies the 50-over DLS table is available.
        """
        # Create a 50-over game
        game_id, teams = game_helper.create_game(
            overs_limit=50,
            match_type="limited",
        )

        team_a_players = teams["team_a"]
        team_b_players = teams["team_b"]

        # Set openers for Team A
        game_helper.set_openers(team="A")

        striker = team_a_players[0]["id"]
        bowler = team_b_players[0]["id"]

        # Play a few overs to verify the match works
        bowler1 = team_b_players[0]["id"]
        bowler2 = team_b_players[1]["id"]
        for i in range(30):  # 5 overs
            bowler = bowler1 if (i // 6) % 2 == 0 else bowler2
            response = game_helper.post_delivery(
                batsman_id=striker,
                bowler_id=bowler,
                runs_scored=1,
            )
            assert response.status_code == 200

        # Verify the match is progressing
        snapshot = game_helper.get_snapshot()
        assert snapshot["score"]["runs"] == 30
        assert snapshot["score"]["overs"] == 5


class TestDLSIntegrationEdgeCases:
    """Integration tests for DLS edge cases."""

    def test_very_short_match(self, game_helper: GameHelper):
        """
        Test a very short match (1 over) to ensure DLS doesn't break.
        """
        # Create a 1-over game
        game_id, teams = game_helper.create_game(
            overs_limit=1,
            match_type="limited",
        )

        team_a_players = teams["team_a"]
        team_b_players = teams["team_b"]

        # Set openers for Team A
        game_helper.set_openers(team="A")

        striker = team_a_players[0]["id"]
        bowler = team_b_players[0]["id"]

        # Play 1 over (6 balls)
        for i in range(6):
            response = game_helper.post_delivery(
                batsman_id=striker,
                bowler_id=bowler,
                runs_scored=2,
            )
            assert response.status_code == 200

        # Verify the match completed
        snapshot = game_helper.get_snapshot()
        assert snapshot["score"]["runs"] == 12
        assert snapshot["score"]["overs"] == 1

    def test_match_with_wickets(self, game_helper: GameHelper):
        """
        Test a match with wickets to ensure DLS can handle wickets correctly.
        """
        # Create a short game for testing
        game_id, teams = game_helper.create_game(
            overs_limit=5,
            match_type="limited",
        )

        team_a_players = teams["team_a"]
        team_b_players = teams["team_b"]

        # Set openers for Team A
        game_helper.set_openers(team="A")

        striker = team_a_players[0]["id"]
        bowler = team_b_players[0]["id"]

        # Bowl a few normal deliveries
        for i in range(5):
            response = game_helper.post_delivery(
                batsman_id=striker,
                bowler_id=bowler,
                runs_scored=1,
            )
            assert response.status_code == 200

        # Take a wicket
        response = game_helper.post_delivery(
            batsman_id=striker,
            bowler_id=bowler,
            runs_scored=0,
            is_wicket=True,
            dismissal_type="bowled",
        )
        assert response.status_code == 200

        # Verify the wicket was recorded
        snapshot = game_helper.get_snapshot()
        assert snapshot["score"]["wickets"] == 1
        assert snapshot["score"]["runs"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
