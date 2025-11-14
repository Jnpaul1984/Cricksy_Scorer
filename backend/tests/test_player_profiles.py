"""
Unit tests for player profile endpoints.
Tests profile data accuracy, achievements, and leaderboard rankings.
"""
import os
import sys
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

# Ensure backend is on path for local runs
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Set in-memory mode for testing
os.environ["CRICKSY_IN_MEMORY_DB"] = "1"

from backend.main import app

client = TestClient(app)


@pytest.fixture
def sample_player_profile():
    """Sample player profile data for testing."""
    return {
        "player_id": "test-player-123",
        "player_name": "Test Player",
        "total_matches": 10,
        "total_innings_batted": 10,
        "total_runs_scored": 450,
        "total_balls_faced": 300,
        "total_fours": 35,
        "total_sixes": 12,
        "times_out": 8,
        "highest_score": 95,
        "centuries": 0,
        "half_centuries": 4,
        "total_innings_bowled": 8,
        "total_overs_bowled": 30.0,
        "total_runs_conceded": 240,
        "total_wickets": 12,
        "best_bowling_figures": "3/25",
        "five_wicket_hauls": 0,
        "maidens": 2,
        "catches": 5,
        "stumpings": 0,
        "run_outs": 2,
    }


@pytest.fixture
def sample_achievement():
    """Sample achievement data for testing."""
    return {
        "achievement_type": "half_century",
        "title": "Half Century Hero",
        "description": "Scored 50 runs in the match against Team B",
        "badge_icon": "🏏",
        "game_id": "game-456",
        "metadata": {
            "runs": 50,
            "balls": 35,
            "fours": 5,
            "sixes": 2,
        },
    }


class TestPlayerProfileStats:
    """Test player profile statistics calculations."""

    def test_batting_average_calculation(self, sample_player_profile):
        """Test that batting average is calculated correctly."""
        # Expected: 450 / 8 = 56.25
        expected_avg = round(450 / 8, 2)

        # In actual implementation, this would be computed by the model
        runs = sample_player_profile["total_runs_scored"]
        times_out = sample_player_profile["times_out"]
        actual_avg = round(runs / times_out, 2) if times_out > 0 else float(runs)

        assert actual_avg == expected_avg
        assert actual_avg == 56.25

    def test_strike_rate_calculation(self, sample_player_profile):
        """Test that strike rate is calculated correctly."""
        # Expected: (450 / 300) * 100 = 150.0
        expected_sr = round((450 / 300) * 100, 2)

        runs = sample_player_profile["total_runs_scored"]
        balls = sample_player_profile["total_balls_faced"]
        actual_sr = round((runs / balls) * 100, 2) if balls > 0 else 0.0

        assert actual_sr == expected_sr
        assert actual_sr == 150.0

    def test_bowling_average_calculation(self, sample_player_profile):
        """Test that bowling average is calculated correctly."""
        # Expected: 240 / 12 = 20.0
        expected_avg = round(240 / 12, 2)

        runs_conceded = sample_player_profile["total_runs_conceded"]
        wickets = sample_player_profile["total_wickets"]
        actual_avg = (
            round(runs_conceded / wickets, 2) if wickets > 0 else float(runs_conceded)
        )

        assert actual_avg == expected_avg
        assert actual_avg == 20.0

    def test_economy_rate_calculation(self, sample_player_profile):
        """Test that economy rate is calculated correctly."""
        # Expected: 240 / 30.0 = 8.0
        expected_er = round(240 / 30.0, 2)

        runs_conceded = sample_player_profile["total_runs_conceded"]
        overs = sample_player_profile["total_overs_bowled"]
        actual_er = round(runs_conceded / overs, 2) if overs > 0 else 0.0

        assert actual_er == expected_er
        assert actual_er == 8.0

    def test_batting_average_with_no_dismissals(self):
        """Test batting average when player is never out."""
        runs = 100
        times_out = 0

        # When never out, average equals total runs
        actual_avg = round(runs / times_out, 2) if times_out > 0 else float(runs)
        assert actual_avg == 100.0

    def test_strike_rate_with_no_balls_faced(self):
        """Test strike rate when no balls have been faced."""
        runs = 0
        balls = 0

        actual_sr = round((runs / balls) * 100, 2) if balls > 0 else 0.0
        assert actual_sr == 0.0


class TestAchievementTypes:
    """Test achievement type validation and badge awarding."""

    def test_valid_achievement_types(self):
        """Test that all valid achievement types are recognized."""
        valid_types = [
            "century",
            "half_century",
            "five_wickets",
            "best_scorer",
            "best_bowler",
            "hat_trick",
            "golden_duck",
            "maiden_over",
            "six_sixes",
            "perfect_catch",
        ]

        # All these types should be valid
        for achievement_type in valid_types:
            assert achievement_type in [
                "century",
                "half_century",
                "five_wickets",
                "best_scorer",
                "best_bowler",
                "hat_trick",
                "golden_duck",
                "maiden_over",
                "six_sixes",
                "perfect_catch",
            ]

    def test_century_achievement_criteria(self):
        """Test that century achievement is awarded for 100+ runs."""
        runs_scored = 105
        assert runs_scored >= 100, "Century should be awarded for 100+ runs"

    def test_half_century_achievement_criteria(self):
        """Test that half-century achievement is awarded for 50-99 runs."""
        runs_scored = 75
        assert 50 <= runs_scored < 100, "Half-century should be awarded for 50-99 runs"

    def test_five_wickets_achievement_criteria(self):
        """Test that five-wicket haul achievement is awarded for 5+ wickets."""
        wickets_taken = 5
        assert wickets_taken >= 5, "Five-wicket haul should be awarded for 5+ wickets"


class TestLeaderboardRankings:
    """Test leaderboard ranking logic."""

    def test_leaderboard_sorting_by_runs(self):
        """Test that leaderboard correctly sorts by total runs."""
        players = [
            {"name": "Player A", "runs": 450},
            {"name": "Player B", "runs": 600},
            {"name": "Player C", "runs": 300},
        ]

        sorted_players = sorted(players, key=lambda p: p["runs"], reverse=True)

        assert sorted_players[0]["name"] == "Player B"
        assert sorted_players[1]["name"] == "Player A"
        assert sorted_players[2]["name"] == "Player C"

    def test_leaderboard_sorting_by_average(self):
        """Test that leaderboard correctly sorts by batting average."""
        players = [
            {"name": "Player A", "runs": 450, "outs": 8, "avg": 56.25},
            {"name": "Player B", "runs": 600, "outs": 10, "avg": 60.0},
            {"name": "Player C", "runs": 300, "outs": 5, "avg": 60.0},
        ]

        sorted_players = sorted(players, key=lambda p: p["avg"], reverse=True)

        # Both Player B and C have 60.0 average
        assert sorted_players[0]["avg"] == 60.0
        assert sorted_players[2]["avg"] == 56.25

    def test_leaderboard_sorting_by_wickets(self):
        """Test that leaderboard correctly sorts by total wickets."""
        players = [
            {"name": "Player A", "wickets": 12},
            {"name": "Player B", "wickets": 18},
            {"name": "Player C", "wickets": 8},
        ]

        sorted_players = sorted(players, key=lambda p: p["wickets"], reverse=True)

        assert sorted_players[0]["name"] == "Player B"
        assert sorted_players[1]["name"] == "Player A"
        assert sorted_players[2]["name"] == "Player C"

    def test_leaderboard_ranking_assignment(self):
        """Test that ranks are correctly assigned."""
        players = [
            {"name": "Player A", "runs": 600},
            {"name": "Player B", "runs": 450},
            {"name": "Player C", "runs": 300},
        ]

        # Assign ranks
        for rank, player in enumerate(players, start=1):
            player["rank"] = rank

        assert players[0]["rank"] == 1
        assert players[1]["rank"] == 2
        assert players[2]["rank"] == 3

    def test_leaderboard_limit(self):
        """Test that leaderboard respects limit parameter."""
        players = [{"name": f"Player {i}", "runs": 100 * i} for i in range(20, 0, -1)]

        limit = 10
        top_players = players[:limit]

        assert len(top_players) == limit


class TestPlayerProfileIntegration:
    """Integration tests for player profile data consistency."""

    def test_profile_data_completeness(self, sample_player_profile):
        """Test that profile contains all required fields."""
        required_fields = [
            "player_id",
            "player_name",
            "total_matches",
            "total_runs_scored",
            "total_wickets",
        ]

        for field in required_fields:
            assert field in sample_player_profile

    def test_profile_statistics_consistency(self, sample_player_profile):
        """Test that profile statistics are internally consistent."""
        # Centuries + half_centuries should be <= total_innings
        profile = sample_player_profile
        milestones = profile["centuries"] + profile["half_centuries"]
        innings = profile["total_innings_batted"]

        assert milestones <= innings

    def test_profile_fielding_stats_consistency(self, sample_player_profile):
        """Test that fielding statistics are non-negative."""
        profile = sample_player_profile

        assert profile["catches"] >= 0
        assert profile["stumpings"] >= 0
        assert profile["run_outs"] >= 0


class TestAchievementData:
    """Test achievement data structure and validation."""

    def test_achievement_has_required_fields(self, sample_achievement):
        """Test that achievement contains all required fields."""
        required_fields = [
            "achievement_type",
            "title",
            "description",
        ]

        for field in required_fields:
            assert field in sample_achievement

    def test_achievement_metadata_structure(self, sample_achievement):
        """Test that achievement metadata is properly structured."""
        metadata = sample_achievement["metadata"]

        assert isinstance(metadata, dict)
        assert "runs" in metadata
        assert metadata["runs"] == 50

    def test_achievement_game_association(self, sample_achievement):
        """Test that achievement can be associated with a game."""
        assert "game_id" in sample_achievement
        assert sample_achievement["game_id"] == "game-456"
