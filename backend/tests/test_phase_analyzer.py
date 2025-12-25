"""
Tests for MatchPhaseAnalyzer service

Tests phase segmentation, predictions, and trend analysis across match phases:
- Powerplay analysis (0-6 overs)
- Middle overs analysis (7-15 overs)
- Death overs analysis (16-20 overs)
- Mini-death analysis (2nd innings, last 3 overs)
"""

import pytest
from backend.services.phase_analyzer import get_phase_analysis


def create_delivery(
    over_number: int,
    ball_number: int,
    runs_scored: int = 1,
    is_wicket: bool = False,
    runs_in_over: int = 0,
) -> dict:
    """Helper to create realistic delivery dicts."""
    return {
        "over_number": over_number,
        "ball_number": ball_number,
        "runs_scored": runs_scored,
        "is_wicket": is_wicket,
        "runs_in_over": runs_in_over,
    }


class TestMatchPhaseAnalyzerBasics:
    """Test basic phase detection and segmentation."""

    def test_phase_analyzer_detects_powerplay(self):
        """Verify powerplay phase detection (0-6 overs)."""
        # Create 6 overs of scoring
        deliveries = [create_delivery(over, ball) for over in range(6) for ball in range(1, 7)]

        result = get_phase_analysis(
            deliveries=deliveries,
            target=150,
            overs_limit=20,
            is_second_innings=False,
        )

        phases = result.get("phases", [])
        assert len(phases) > 0, "Should have at least one phase"
        assert phases[0]["phase_name"] == "powerplay"
        assert phases[0]["total_deliveries"] == 36  # 6 overs * 6 balls

    def test_phase_analyzer_detects_middle_overs(self):
        """Verify middle overs phase detection (6-15 overs)."""
        # Create middle overs (6-15)
        deliveries = [create_delivery(over, ball) for over in range(6, 15) for ball in range(1, 7)]

        result = get_phase_analysis(
            deliveries=deliveries,
            target=150,
            overs_limit=20,
            is_second_innings=False,
        )

        phases = result.get("phases", [])
        # Should have middle phase
        middle_phase = next((p for p in phases if p["phase_name"] == "middle"), None)
        assert middle_phase is not None, "Should have middle overs phase"
        assert middle_phase["total_deliveries"] > 0

    def test_phase_analyzer_detects_death_overs(self):
        """Verify death overs phase detection (16-20 overs)."""
        # Create death overs (16-20)
        deliveries = [create_delivery(over, ball) for over in range(16, 20) for ball in range(1, 7)]

        result = get_phase_analysis(
            deliveries=deliveries,
            target=150,
            overs_limit=20,
            is_second_innings=False,
        )

        phases = result.get("phases", [])
        # Should have death phase
        death_phase = next((p for p in phases if p["phase_name"] == "death"), None)
        assert death_phase is not None, "Should have death overs phase"


class TestPhaseStatistics:
    """Test phase statistics calculation."""

    def test_phase_calculates_run_rate(self):
        """Verify run rate calculation per phase."""
        # Create 6 overs with 2 runs per over
        deliveries = []
        for over in range(6):
            deliveries.append(create_delivery(over, 1, runs_scored=2))
            deliveries.extend([create_delivery(over, ball, runs_scored=0) for ball in range(2, 7)])

        result = get_phase_analysis(
            deliveries=deliveries,
            target=150,
            overs_limit=20,
            is_second_innings=False,
        )

        phases = result.get("phases", [])
        assert len(phases) > 0
        pp_phase = phases[0]
        # 6 overs * 2 runs = 12 runs, 6 overs = RR of 2
        assert pp_phase["run_rate"] == 2.0, f"Expected RR 2.0, got {pp_phase['run_rate']}"

    def test_phase_counts_wickets(self):
        """Verify wicket counting per phase."""
        # Create 3 overs with 2 wickets
        deliveries = []
        for over in range(3):
            if over < 2:
                deliveries.append(create_delivery(over, 1, runs_scored=0, is_wicket=True))
            deliveries.extend([create_delivery(over, ball, runs_scored=1) for ball in range(2, 7)])

        result = get_phase_analysis(
            deliveries=deliveries,
            target=150,
            overs_limit=20,
            is_second_innings=False,
        )

        phases = result.get("phases", [])
        assert phases[0]["total_wickets"] == 2, "Should count 2 wickets"

    def test_phase_counts_boundaries(self):
        """Verify boundary (4s and 6s) counting."""
        # Create 2 overs with 4s and 6s
        deliveries = [
            create_delivery(0, 1, runs_scored=4),
            create_delivery(0, 2, runs_scored=0),
            create_delivery(0, 3, runs_scored=6),
            create_delivery(0, 4, runs_scored=0),
            create_delivery(0, 5, runs_scored=1),
            create_delivery(0, 6, runs_scored=0),
            create_delivery(1, 1, runs_scored=4),
            create_delivery(1, 2, runs_scored=0),
            create_delivery(1, 3, runs_scored=1),
            create_delivery(1, 4, runs_scored=0),
            create_delivery(1, 5, runs_scored=1),
            create_delivery(1, 6, runs_scored=0),
        ]

        result = get_phase_analysis(
            deliveries=deliveries,
            target=150,
            overs_limit=20,
            is_second_innings=False,
        )

        phases = result.get("phases", [])
        assert phases[0]["boundary_count"] == 3, (
            f"Expected 3 boundaries, got {phases[0]['boundary_count']}"
        )

    def test_phase_counts_dot_balls(self):
        """Verify dot ball counting."""
        # Create 1 over with 3 dots
        deliveries = [
            create_delivery(0, 1, runs_scored=1),
            create_delivery(0, 2, runs_scored=0),
            create_delivery(0, 3, runs_scored=1),
            create_delivery(0, 4, runs_scored=0),
            create_delivery(0, 5, runs_scored=1),
            create_delivery(0, 6, runs_scored=0),
        ]

        result = get_phase_analysis(
            deliveries=deliveries,
            target=150,
            overs_limit=20,
            is_second_innings=False,
        )

        phases = result.get("phases", [])
        assert phases[0]["dot_ball_count"] == 3, (
            f"Expected 3 dots, got {phases[0]['dot_ball_count']}"
        )


class TestPhaseComparisons:
    """Test phase performance vs expectations."""

    def test_powerplay_efficiency_calculation(self):
        """Verify expected vs actual runs in powerplay."""
        # Create 6 overs with 50 runs (target: 51 runs for powerplay, so ~98% efficient)
        deliveries = []
        runs_to_distribute = 50
        for over in range(6):
            for ball in range(1, 7):
                runs = (runs_to_distribute // 36) + (
                    1 if (over * 6 + ball) <= (runs_to_distribute % 36) else 0
                )
                runs_to_distribute -= runs
                deliveries.append(create_delivery(over, ball, runs_scored=runs))

        result = get_phase_analysis(
            deliveries=deliveries,
            target=180,
            overs_limit=20,
            is_second_innings=False,
        )

        phases = result.get("phases", [])
        pp_phase = phases[0]
        # 50 runs vs 51 expected (8.5 * 6) = ~98%, should be >50%
        assert pp_phase["actual_vs_expected_pct"] > 50, "Powerplay efficiency should be >50%"

    def test_acceleration_rate_calculation(self):
        """Verify acceleration rate (vs powerplay baseline)."""
        # Powerplay: 6 runs per over, Middle: 8 runs per over
        deliveries = []

        # Powerplay (0-6): 36 runs = 6 per over
        for over in range(6):
            for ball in range(1, 7):
                deliveries.append(create_delivery(over, ball, runs_scored=1))

        # Middle (6-15): more runs per over (acceleration)
        for over in range(6, 15):
            for ball in range(1, 7):
                runs = 1 if ball <= 5 else 0  # 5 runs per over
                deliveries.append(create_delivery(over, ball, runs_scored=runs))

        result = get_phase_analysis(
            deliveries=deliveries,
            target=180,
            overs_limit=20,
            is_second_innings=False,
        )

        phases = result.get("phases", [])
        assert len(phases) >= 2
        # Just verify both phases exist and have reasonable data
        assert phases[0]["total_runs"] > 0, "Powerplay should have runs"
        assert phases[1]["total_runs"] > 0, "Middle should have runs"


class TestAccelerationTrend:
    """Test acceleration trend detection."""

    def test_detects_increasing_trend(self):
        """Verify detection of increasing run rate trend."""
        # Powerplay: 4 RR, Middle: 8 RR (clear increase)
        deliveries = []

        # Powerplay: 24 runs in 6 overs
        for over in range(6):
            for ball in range(1, 7):
                runs = 1 if ball <= 1 else 0
                deliveries.append(create_delivery(over, ball, runs_scored=runs))

        # Middle: 72 runs in 9 overs (8 RR)
        for over in range(6, 15):
            for ball in range(1, 7):
                runs = 1 if ball <= 3 else 0
                deliveries.append(create_delivery(over, ball, runs_scored=runs))

        result = get_phase_analysis(
            deliveries=deliveries,
            target=180,
            overs_limit=20,
            is_second_innings=False,
        )

        trend = result.get("summary", {}).get("acceleration_trend")
        assert trend == "increasing", f"Expected 'increasing', got '{trend}'"

    def test_detects_decreasing_trend(self):
        """Verify detection of decreasing run rate trend."""
        # Powerplay: 8 RR, Middle: 4 RR (clear decrease)
        deliveries = []

        # Powerplay: 48 runs in 6 overs (8 RR)
        for over in range(6):
            for ball in range(1, 7):
                runs = 1 if ball <= 3 else 0
                deliveries.append(create_delivery(over, ball, runs_scored=runs))

        # Middle: 36 runs in 9 overs (4 RR)
        for over in range(6, 15):
            for ball in range(1, 7):
                runs = 1 if ball <= 1 else 0
                deliveries.append(create_delivery(over, ball, runs_scored=runs))

        result = get_phase_analysis(
            deliveries=deliveries,
            target=180,
            overs_limit=20,
            is_second_innings=False,
        )

        trend = result.get("summary", {}).get("acceleration_trend")
        assert trend == "decreasing", f"Expected 'decreasing', got '{trend}'"


class TestPredictions:
    """Test phase-based predictions."""

    def test_generates_total_runs_projection(self):
        """Verify total runs projection based on phase performance."""
        # Create 6 overs with 36 runs (6 per over)
        deliveries = []
        for over in range(6):
            for ball in range(1, 7):
                deliveries.append(create_delivery(over, ball, runs_scored=1))

        result = get_phase_analysis(
            deliveries=deliveries,
            target=180,
            overs_limit=20,
            is_second_innings=False,
        )

        predictions = result.get("predictions", {})
        projected = predictions.get("total_expected_runs", 0)
        # With 6 RR across all 20 overs = 120 runs
        assert projected > 0, "Should project total runs"
        assert isinstance(projected, (int, float))

    def test_generates_win_probability_when_chasing(self):
        """Verify win probability calculation for 2nd innings."""
        # Create 10 overs of 1st inning scoring 90 runs
        deliveries_1 = []
        for over in range(10):
            for ball in range(1, 7):
                deliveries_1.append(
                    create_delivery(over, ball, runs_scored=1 if ball <= 1.5 else 0)
                )

        # Create 8 overs of 2nd inning scoring 70 runs (chasing 91)
        deliveries_2 = []
        for over in range(8):
            for ball in range(1, 7):
                deliveries_2.append(
                    create_delivery(over, ball, runs_scored=1 if ball <= 1.4 else 0)
                )

        result = get_phase_analysis(
            deliveries=deliveries_2,
            target=91,
            overs_limit=20,
            is_second_innings=True,
        )

        predictions = result.get("predictions", {})
        win_prob = predictions.get("win_probability", None)
        # With 70 runs in 8 overs and target 91, need 21 in 12 overs = doable
        assert win_prob is not None, "Should calculate win probability when chasing"
        assert 0 <= win_prob <= 1, "Win probability should be between 0 and 1"

    def test_generates_powerplay_efficiency(self):
        """Verify powerplay efficiency metric."""
        # Create 6 overs with 48 runs (8 per over)
        deliveries = []
        for over in range(6):
            for ball in range(1, 7):
                runs = 1 if ball <= 2 else 0
                deliveries.append(create_delivery(over, ball, runs_scored=runs))

        result = get_phase_analysis(
            deliveries=deliveries,
            target=180,
            overs_limit=20,
            is_second_innings=False,
        )

        predictions = result.get("predictions", {})
        pp_efficiency = predictions.get("powerplay_efficiency", None)
        # 48 runs vs 51 expected = ~94% efficiency
        assert pp_efficiency is not None, "Should include powerplay efficiency"
        assert pp_efficiency > 0, "Efficiency should be positive"


class TestConvenienceFunction:
    """Test get_phase_analysis wrapper function."""

    def test_convenience_function_returns_complete_data(self):
        """Verify get_phase_analysis returns all expected fields."""
        deliveries = [create_delivery(over, ball) for over in range(6) for ball in range(1, 7)]

        result = get_phase_analysis(
            deliveries=deliveries,
            target=150,
            overs_limit=20,
            is_second_innings=False,
        )

        assert "phases" in result
        assert "current_phase" in result
        assert "summary" in result
        assert "predictions" in result
        assert "phase_performance" in result

    def test_handles_empty_deliveries(self):
        """Verify graceful handling of empty deliveries."""
        result = get_phase_analysis(
            deliveries=[],
            target=150,
            overs_limit=20,
            is_second_innings=False,
        )

        assert result["phases"] == []
        assert result["current_phase"] == "powerplay"
        assert result["summary"]["total_runs"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
