"""
Tests for Tactical Suggestion Engine

Tests coaching recommendations:
- Best bowler selection
- Weakness analysis
- Fielding recommendations
"""

import pytest
from backend.services.tactical_suggestion_engine import (
    TacticalSuggestionEngine,
    BowlerProfile,
    BatterProfile,
    ScoringZone,
    DeliveryType,
)


class TestBestBowlerSelection:
    """Test best bowler recommendation logic."""

    def test_recommends_effective_bowler(self):
        """Verify bowler with high effectiveness is recommended."""
        bowlers = [
            {
                "bowler_id": "b1",
                "bowler_name": "Bowler A",
                "total_deliveries": 100,
                "runs_conceded": 150,  # 1.5 economy
                "wickets_taken": 8,  # 1 per 12.5 balls
                "economy_rate": 1.5,
                "strike_rate_against": 50.0,
            },
            {
                "bowler_id": "b2",
                "bowler_name": "Bowler B",
                "total_deliveries": 80,
                "runs_conceded": 320,  # 4.0 economy
                "wickets_taken": 2,
                "economy_rate": 4.0,
                "strike_rate_against": 100.0,
            },
        ]

        batter = {
            "batter_id": "bat1",
            "batter_name": "Batter",
            "total_runs": 150,
            "total_deliveries": 100,
            "dismissals": 3,
            "batting_average": 50.0,
            "strike_rate": 150.0,
        }

        suggestion = TacticalSuggestionEngine.get_best_bowler(bowlers, batter)

        assert suggestion is not None
        assert suggestion.bowler_name == "Bowler A"  # More effective bowler
        assert suggestion.confidence > 0

    def test_skips_low_effectiveness_bowlers(self):
        """Verify bowler below effectiveness threshold is not recommended."""
        bowlers = [
            {
                "bowler_id": "b1",
                "bowler_name": "Weak Bowler",
                "total_deliveries": 50,
                "runs_conceded": 100,
                "wickets_taken": 0,
                "economy_rate": 12.0,
                "strike_rate_against": 200.0,
            },
        ]

        batter = {
            "batter_id": "bat1",
            "batter_name": "Batter",
            "total_runs": 200,
            "total_deliveries": 100,
            "dismissals": 2,
            "batting_average": 100.0,
            "strike_rate": 200.0,
        }

        suggestion = TacticalSuggestionEngine.get_best_bowler(bowlers, batter)

        assert suggestion is None  # Effectiveness too low

    def test_avoids_recently_used_bowlers(self):
        """Verify recently used bowlers are penalized."""
        bowlers = [
            {
                "bowler_id": "b1",
                "bowler_name": "Bowler A",
                "total_deliveries": 100,
                "runs_conceded": 180,  # 1.8 economy
                "wickets_taken": 8,
                "economy_rate": 1.8,
                "strike_rate_against": 40.0,
            },
            {
                "bowler_id": "b2",
                "bowler_name": "Bowler B",
                "total_deliveries": 100,
                "runs_conceded": 200,  # 2.0 economy
                "wickets_taken": 7,
                "economy_rate": 2.0,
                "strike_rate_against": 45.0,
            },
        ]

        batter = {
            "batter_id": "bat1",
            "batter_name": "Batter",
            "total_runs": 100,
            "total_deliveries": 100,
            "dismissals": 2,
            "batting_average": 50.0,
            "strike_rate": 100.0,
        }

        # With B1 as recent bowler
        suggestion = TacticalSuggestionEngine.get_best_bowler(bowlers, batter, ["b1"])

        # Should prefer B2 even if slightly weaker
        assert suggestion is not None
        assert suggestion.bowler_id == "b2"


class TestWeaknessAnalysis:
    """Test batter weakness detection."""

    def test_identifies_primary_weakness(self):
        """Verify primary weakness is correctly identified."""
        batter = {
            "batter_id": "bat1",
            "batter_name": "Test Batter",
            "total_runs": 100,
            "total_deliveries": 80,
            "dismissals": 2,
            "batting_average": 50.0,
            "strike_rate": 125.0,
            "pace_weakness": 70.0,  # Highest weakness
            "spin_weakness": 30.0,
            "yorker_weakness": 40.0,
            "dot_ball_weakness": 35.0,
        }

        analysis = TacticalSuggestionEngine.analyze_weakness(batter)

        assert analysis.primary_weakness == "DeliveryType.PACE"
        assert analysis.weakness_score == 70.0

    def test_recommends_delivery_for_weakness(self):
        """Verify delivery type recommendation matches weakness."""
        batter = {
            "batter_id": "bat1",
            "batter_name": "Test Batter",
            "total_runs": 100,
            "total_deliveries": 80,
            "dismissals": 2,
            "batting_average": 50.0,
            "strike_rate": 125.0,
            "pace_weakness": 10.0,
            "spin_weakness": 75.0,  # High weakness
            "yorker_weakness": 20.0,
            "dot_ball_weakness": 25.0,
        }

        analysis = TacticalSuggestionEngine.analyze_weakness(batter)

        assert analysis.primary_weakness == "DeliveryType.SPIN"
        assert analysis.confidence > 0.5

    def test_yorker_recommendations(self):
        """Verify yorker weakness recommendations."""
        batter = {
            "batter_id": "bat1",
            "batter_name": "Test Batter",
            "total_runs": 80,
            "total_deliveries": 100,
            "dismissals": 3,
            "batting_average": 26.67,
            "strike_rate": 80.0,
            "pace_weakness": 25.0,
            "spin_weakness": 35.0,
            "yorker_weakness": 85.0,  # High weakness
            "dot_ball_weakness": 30.0,
        }

        analysis = TacticalSuggestionEngine.analyze_weakness(batter)

        assert analysis.primary_weakness == "DeliveryType.YORKER"
        assert analysis.recommended_length == "yorker"
        assert analysis.recommended_line == "middle"

    def test_dot_ball_strategy(self):
        """Verify dot ball strategy recommendation."""
        batter = {
            "batter_id": "bat1",
            "batter_name": "Test Batter",
            "total_runs": 120,
            "total_deliveries": 100,
            "dismissals": 2,
            "batting_average": 60.0,
            "strike_rate": 120.0,
            "pace_weakness": 20.0,
            "spin_weakness": 15.0,
            "yorker_weakness": 25.0,
            "dot_ball_weakness": 65.0,  # Struggles with dots
        }

        analysis = TacticalSuggestionEngine.analyze_weakness(batter)

        assert analysis.primary_weakness == "dot_strategy"
        assert analysis.recommended_length == "good"


class TestFieldingRecommendations:
    """Test fielding position recommendations."""

    def test_prioritizes_high_scoring_zones(self):
        """Verify high-scoring zones get highest priority."""
        bowler = {
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        batter = {
            "batter_id": "bat1",
            "batter_name": "Batter",
        }

        scoring_zones = [
            {
                "line": "off",
                "length": "good",
                "runs_scored": 30,
                "dismissals": 1,
                "deliveries": 40,
            },
            {
                "line": "leg",
                "length": "full",
                "runs_scored": 10,
                "dismissals": 1,
                "deliveries": 30,
            },
            {
                "line": "middle",
                "length": "short",
                "runs_scored": 5,
                "dismissals": 0,
                "deliveries": 20,
            },
        ]

        setup = TacticalSuggestionEngine.recommend_fielding(
            bowler, batter, scoring_zones
        )

        # Primary zone should be off-good (highest scoring)
        assert "off" in setup.primary_zone
        assert setup.recommended_positions[0].priority == 1
        assert len(setup.recommended_positions) > 0

    def test_covers_multiple_scoring_zones(self):
        """Verify multiple fielding positions recommended."""
        bowler = {
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        batter = {
            "batter_id": "bat1",
            "batter_name": "Batter",
        }

        scoring_zones = [
            {
                "line": "off",
                "length": "full",
                "runs_scored": 20,
                "dismissals": 1,
                "deliveries": 30,
            },
            {
                "line": "leg",
                "length": "short",
                "runs_scored": 15,
                "dismissals": 1,
                "deliveries": 25,
            },
            {
                "line": "middle",
                "length": "good",
                "runs_scored": 10,
                "dismissals": 0,
                "deliveries": 20,
            },
        ]

        setup = TacticalSuggestionEngine.recommend_fielding(
            bowler, batter, scoring_zones
        )

        assert len(setup.recommended_positions) == 3


class TestScoringZoneAnalysis:
    """Test scoring zone metrics."""

    def test_calculates_run_rate(self):
        """Verify run rate calculation."""
        zone = ScoringZone(
            line="off",
            length="good",
            runs_scored=20,
            dismissals=1,
            deliveries=40,
        )

        assert zone.run_rate == 0.5  # 20 runs / 40 deliveries

    def test_calculates_dismissal_risk(self):
        """Verify dismissal risk calculation."""
        zone = ScoringZone(
            line="leg",
            length="full",
            runs_scored=25,
            dismissals=2,
            deliveries=50,
        )

        assert zone.dismissal_risk == 4.0  # (2/50) * 100


class TestBowlerProfile:
    """Test bowler profile effectiveness scoring."""

    def test_calculates_effectiveness_score(self):
        """Verify effectiveness score calculation."""
        bowler = BowlerProfile(
            bowler_id="b1",
            bowler_name="Test Bowler",
            total_deliveries=100,
            runs_conceded=200,  # 2.0 economy
            wickets_taken=8,  # 1 per 12.5 balls
            economy_rate=2.0,
            strike_rate_against=40.0,
        )

        score = bowler.effectiveness_score
        assert 0 <= score <= 100
        assert score > 30  # Good bowler should score above low baseline

    def test_high_economy_reduces_score(self):
        """Verify high economy rate reduces effectiveness."""
        bowler_good = BowlerProfile(
            bowler_id="b1",
            bowler_name="Good Bowler",
            total_deliveries=100,
            runs_conceded=30,
            wickets_taken=4,
            economy_rate=1.8,
            strike_rate_against=30.0,
        )

        bowler_bad = BowlerProfile(
            bowler_id="b2",
            bowler_name="Bad Bowler",
            total_deliveries=100,
            runs_conceded=80,
            wickets_taken=2,
            economy_rate=4.8,
            strike_rate_against=80.0,
        )

        assert bowler_good.effectiveness_score > bowler_bad.effectiveness_score


class TestBatterProfile:
    """Test batter profile metrics."""

    def test_calculates_current_form_score(self):
        """Verify recent form score calculation."""
        batter = BatterProfile(
            batter_id="bat1",
            batter_name="Test Batter",
            total_runs=200,
            total_deliveries=160,
            dismissals=4,
            batting_average=50.0,
            strike_rate=125.0,
            last_5_runs=[45, 30, 50, 40, 35],
        )

        form_score = batter.current_form_score
        assert 0 <= form_score <= 100
        assert form_score > 50  # Average is good (40 avg)

    def test_identifies_form_status(self):
        """Verify in-form detection."""
        good_form = BatterProfile(
            batter_id="bat1",
            batter_name="Good Form Batter",
            total_runs=200,
            total_deliveries=160,
            dismissals=3,
            batting_average=66.67,
            strike_rate=125.0,
            last_5_runs=[70, 60, 75, 55, 80],
        )

        bad_form = BatterProfile(
            batter_id="bat2",
            batter_name="Bad Form Batter",
            total_runs=100,
            total_deliveries=160,
            dismissals=5,
            batting_average=20.0,
            strike_rate=62.5,
            last_5_runs=[10, 5, 8, 3, 12],
        )

        assert good_form.is_in_form is True
        assert bad_form.is_in_form is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
