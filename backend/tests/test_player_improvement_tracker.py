"""
Tests for PlayerImprovementTracker service

Tests month-over-month improvement tracking:
- Monthly statistics aggregation
- Improvement metrics calculation
- Trend detection
- Consistency scoring
- Improvement summary generation
"""

import pytest
from backend.services.player_improvement_tracker import (
    PlayerImprovementTracker,
    MonthlyStats,
)


def create_match_data(
    runs_scored: int = 30,
    deliveries_faced: int = 40,
    is_dismissed: bool = False,
    boundaries_4: int = 2,
    boundaries_6: int = 1,
    role: str = "middle_order",
) -> dict:
    """Helper to create realistic match performance data."""
    return {
        "runs_scored": runs_scored,
        "deliveries_faced": deliveries_faced,
        "is_dismissed": is_dismissed,
        "boundaries_4": boundaries_4,
        "boundaries_6": boundaries_6,
        "role": role,
    }


class TestMonthlyStatsCalculation:
    """Test aggregation of monthly statistics."""

    def test_calculates_monthly_batting_average(self):
        """Verify batting average calculation."""
        # 4 matches: 25, 30, 35, 40 runs = avg 32.5
        matches = [
            create_match_data(runs_scored=25, deliveries_faced=30),
            create_match_data(runs_scored=30, deliveries_faced=35),
            create_match_data(runs_scored=35, deliveries_faced=40),
            create_match_data(runs_scored=40, deliveries_faced=45),
        ]

        stats = PlayerImprovementTracker.calculate_monthly_stats(matches, month="2024-12")

        assert stats is not None
        assert stats.batting_average == 32.5
        assert stats.total_runs == 130
        assert stats.innings_played == 4

    def test_calculates_monthly_strike_rate(self):
        """Verify strike rate calculation."""
        # 100 runs in 120 balls = 83.33 SR
        matches = [
            create_match_data(runs_scored=50, deliveries_faced=60),
            create_match_data(runs_scored=50, deliveries_faced=60),
        ]

        stats = PlayerImprovementTracker.calculate_monthly_stats(matches, month="2024-12")

        assert stats is not None
        assert stats.total_runs == 100
        assert stats.total_deliveries == 120
        assert abs(stats.strike_rate - 83.33) < 0.1

    def test_counts_dismissals(self):
        """Verify dismissal counting."""
        matches = [
            create_match_data(is_dismissed=True),
            create_match_data(is_dismissed=False),
            create_match_data(is_dismissed=True),
        ]

        stats = PlayerImprovementTracker.calculate_monthly_stats(matches)

        assert stats.dismissals == 2
        assert stats.innings_played == 3

    def test_counts_boundaries(self):
        """Verify boundary counting."""
        matches = [
            create_match_data(boundaries_4=2, boundaries_6=1),
            create_match_data(boundaries_4=3, boundaries_6=0),
            create_match_data(boundaries_4=1, boundaries_6=2),
        ]

        stats = PlayerImprovementTracker.calculate_monthly_stats(matches)

        assert stats.boundaries_4 == 6
        assert stats.boundaries_6 == 3

    def test_determines_primary_role(self):
        """Verify role detection."""
        matches = [
            create_match_data(role="opener"),
            create_match_data(role="opener"),
            create_match_data(role="middle_order"),
        ]

        stats = PlayerImprovementTracker.calculate_monthly_stats(matches)

        assert stats.role == "opener"  # Most common

    def test_handles_empty_matches(self):
        """Verify graceful handling of empty data."""
        result = PlayerImprovementTracker.calculate_monthly_stats([])

        assert result is None


class TestConsistencyScoring:
    """Test consistency score calculation."""

    def test_consistent_performer(self):
        """Verify high consistency for steady performances."""
        # Steady runs: 30, 32, 28, 30, 31 (low variance)
        matches = [
            create_match_data(runs_scored=30),
            create_match_data(runs_scored=32),
            create_match_data(runs_scored=28),
            create_match_data(runs_scored=30),
            create_match_data(runs_scored=31),
        ]

        stats = PlayerImprovementTracker.calculate_monthly_stats(matches)

        assert stats is not None
        assert stats.consistency_score > 70, "Steady performer should have high consistency"

    def test_inconsistent_performer(self):
        """Verify low consistency for erratic performances."""
        # Erratic runs: 5, 50, 10, 60, 8 (high variance)
        matches = [
            create_match_data(runs_scored=5),
            create_match_data(runs_scored=50),
            create_match_data(runs_scored=10),
            create_match_data(runs_scored=60),
            create_match_data(runs_scored=8),
        ]

        stats = PlayerImprovementTracker.calculate_monthly_stats(matches)

        assert stats is not None
        assert stats.consistency_score < 50, "Inconsistent performer should have low consistency"


class TestImprovementMetrics:
    """Test improvement metrics calculation."""

    def test_detects_improving_batting_average(self):
        """Verify detection of batting average improvement."""
        previous = MonthlyStats(
            month="2024-11",
            total_runs=100,
            total_deliveries=120,
            matches_played=4,
            innings_played=4,
            dismissals=1,
            boundaries_4=5,
            boundaries_6=1,
            batting_average=25.0,
            strike_rate=83.33,
            consistency_score=70.0,
            role="middle_order",
        )

        current = MonthlyStats(
            month="2024-12",
            total_runs=130,
            total_deliveries=120,
            matches_played=4,
            innings_played=4,
            dismissals=1,
            boundaries_4=6,
            boundaries_6=2,
            batting_average=32.5,
            strike_rate=108.33,
            consistency_score=72.0,
            role="middle_order",
        )

        metrics = PlayerImprovementTracker.calculate_improvement_metrics(previous, current)

        ba_metric = metrics["batting_average"]
        assert ba_metric.trend == "improving"
        assert ba_metric.percentage_change > 0

    def test_detects_declining_strike_rate(self):
        """Verify detection of strike rate decline."""
        previous = MonthlyStats(
            month="2024-11",
            total_runs=100,
            total_deliveries=100,
            matches_played=4,
            innings_played=4,
            dismissals=0,
            boundaries_4=5,
            boundaries_6=2,
            batting_average=25.0,
            strike_rate=100.0,
            consistency_score=70.0,
            role="middle_order",
        )

        current = MonthlyStats(
            month="2024-12",
            total_runs=90,
            total_deliveries=120,
            matches_played=4,
            innings_played=4,
            dismissals=1,
            boundaries_4=4,
            boundaries_6=1,
            batting_average=22.5,
            strike_rate=75.0,
            consistency_score=68.0,
            role="middle_order",
        )

        metrics = PlayerImprovementTracker.calculate_improvement_metrics(previous, current)

        sr_metric = metrics["strike_rate"]
        assert sr_metric.trend == "declining"
        assert sr_metric.percentage_change < 0

    def test_calculates_accurate_percentage_change(self):
        """Verify percentage change calculation accuracy."""
        previous = MonthlyStats(
            month="2024-11",
            total_runs=80,
            total_deliveries=100,
            matches_played=4,
            innings_played=4,
            dismissals=1,
            boundaries_4=4,
            boundaries_6=1,
            batting_average=20.0,
            strike_rate=80.0,
            consistency_score=60.0,
            role="opener",
        )

        current = MonthlyStats(
            month="2024-12",
            total_runs=100,
            total_deliveries=100,
            matches_played=4,
            innings_played=4,
            dismissals=1,
            boundaries_4=5,
            boundaries_6=2,
            batting_average=25.0,
            strike_rate=100.0,
            consistency_score=66.0,
            role="opener",
        )

        metrics = PlayerImprovementTracker.calculate_improvement_metrics(previous, current)

        # BA: 20 -> 25 = 25% improvement
        ba_metric = metrics["batting_average"]
        assert abs(ba_metric.percentage_change - 25.0) < 1.0

        # SR: 80 -> 100 = 25% improvement
        sr_metric = metrics["strike_rate"]
        assert abs(sr_metric.percentage_change - 25.0) < 1.0


class TestTrendDetection:
    """Test acceleration and decline trend detection."""

    def test_detects_improving_trend(self):
        """Verify detection of improving trend."""
        stats = [
            MonthlyStats(
                month="2024-10",
                total_runs=80,
                total_deliveries=100,
                matches_played=4,
                innings_played=4,
                dismissals=2,
                boundaries_4=3,
                boundaries_6=0,
                batting_average=20.0,
                strike_rate=80.0,
                consistency_score=65.0,
                role="middle_order",
            ),
            MonthlyStats(
                month="2024-11",
                total_runs=100,
                total_deliveries=110,
                matches_played=4,
                innings_played=4,
                dismissals=1,
                boundaries_4=5,
                boundaries_6=1,
                batting_average=25.0,
                strike_rate=90.91,
                consistency_score=72.0,
                role="middle_order",
            ),
            MonthlyStats(
                month="2024-12",
                total_runs=130,
                total_deliveries=120,
                matches_played=4,
                innings_played=4,
                dismissals=1,
                boundaries_4=7,
                boundaries_6=2,
                batting_average=32.5,
                strike_rate=108.33,
                consistency_score=75.0,
                role="middle_order",
            ),
        ]

        summary = PlayerImprovementTracker.get_improvement_summary(stats)

        # Verify summary structure
        assert summary["status"] == "success"
        assert "overall_trend" in summary
        assert summary["improvement_score"] > 0

    def test_generates_highlights(self):
        """Verify highlight generation."""
        previous = MonthlyStats(
            month="2024-11",
            total_runs=100,
            total_deliveries=120,
            matches_played=4,
            innings_played=4,
            dismissals=2,
            boundaries_4=5,
            boundaries_6=1,
            batting_average=25.0,
            strike_rate=83.33,
            consistency_score=70.0,
            role="middle_order",
        )

        current = MonthlyStats(
            month="2024-12",
            total_runs=130,
            total_deliveries=120,
            matches_played=4,
            innings_played=4,
            dismissals=1,
            boundaries_4=7,
            boundaries_6=2,
            batting_average=32.5,
            strike_rate=108.33,
            consistency_score=75.0,
            role="middle_order",
        )

        metrics = PlayerImprovementTracker.calculate_improvement_metrics(previous, current)
        highlights = PlayerImprovementTracker._generate_highlights([previous, current], metrics)

        assert len(highlights) > 0
        assert any("improving" in h.lower() or "📈" in h for h in highlights)


class TestImprovementSummary:
    """Test comprehensive improvement summary."""

    def test_generates_complete_summary(self):
        """Verify complete summary generation."""
        stats = [
            MonthlyStats(
                month="2024-10",
                total_runs=100,
                total_deliveries=120,
                matches_played=4,
                innings_played=4,
                dismissals=1,
                boundaries_4=5,
                boundaries_6=1,
                batting_average=25.0,
                strike_rate=83.33,
                consistency_score=70.0,
                role="middle_order",
            ),
            MonthlyStats(
                month="2024-11",
                total_runs=110,
                total_deliveries=120,
                matches_played=4,
                innings_played=4,
                dismissals=1,
                boundaries_4=6,
                boundaries_6=1,
                batting_average=27.5,
                strike_rate=91.67,
                consistency_score=72.0,
                role="middle_order",
            ),
            MonthlyStats(
                month="2024-12",
                total_runs=130,
                total_deliveries=120,
                matches_played=4,
                innings_played=4,
                dismissals=0,
                boundaries_4=7,
                boundaries_6=2,
                batting_average=32.5,
                strike_rate=108.33,
                consistency_score=75.0,
                role="middle_order",
            ),
        ]

        summary = PlayerImprovementTracker.get_improvement_summary(stats)

        assert summary["status"] == "success"
        assert "overall_trend" in summary
        assert "improvement_score" in summary
        assert "latest_stats" in summary
        assert "highlights" in summary
        assert len(summary["highlights"]) > 0

    def test_insufficient_data_handling(self):
        """Verify handling of insufficient data."""
        stats = [
            MonthlyStats(
                month="2024-12",
                total_runs=100,
                total_deliveries=120,
                matches_played=4,
                innings_played=4,
                dismissals=1,
                boundaries_4=5,
                boundaries_6=1,
                batting_average=25.0,
                strike_rate=83.33,
                consistency_score=70.0,
                role="middle_order",
            ),
        ]

        summary = PlayerImprovementTracker.get_improvement_summary(stats)

        assert summary["status"] == "insufficient_data"


class TestConvenienceFunction:
    """Test get_player_improvement_data wrapper."""

    def test_processes_dict_input(self):
        """Verify processing of dict input."""
        monthly_data = [
            {
                "month": "2024-11",
                "total_runs": 100,
                "total_deliveries": 120,
                "matches_played": 4,
                "innings_played": 4,
                "dismissals": 1,
                "boundaries_4": 5,
                "boundaries_6": 1,
                "batting_average": 25.0,
                "strike_rate": 83.33,
                "consistency_score": 70.0,
                "role": "middle_order",
            },
            {
                "month": "2024-12",
                "total_runs": 130,
                "total_deliveries": 120,
                "matches_played": 4,
                "innings_played": 4,
                "dismissals": 0,
                "boundaries_4": 7,
                "boundaries_6": 2,
                "batting_average": 32.5,
                "strike_rate": 108.33,
                "consistency_score": 75.0,
                "role": "middle_order",
            },
        ]

        from backend.services.player_improvement_tracker import (
            get_player_improvement_data,
        )

        result = get_player_improvement_data(monthly_data)

        assert result["status"] == "success"
        assert result["overall_trend"] in ["improving", "stable", "accelerating"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
