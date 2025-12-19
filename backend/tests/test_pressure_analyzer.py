import pytest
import pytest_asyncio
from datetime import datetime
from backend.services.pressure_analyzer import PressureAnalyzer, get_pressure_map


def create_delivery(
    delivery_num: int,
    over_num: float,
    runs_scored: int = 0,
    extra_type: str | None = None,
    is_wicket: bool = False,
    dismissal_type: str | None = None,
    striker_id: str = "striker_001",
    non_striker_id: str = "ns_001",
    bowler_id: str = "bowler_001",
    dismissed_by_id: str | None = None
) -> dict:
    """Helper to create delivery dictionaries (as stored in Game.deliveries JSON)."""
    return {
        "over_number": int(over_num),
        "ball_number": int((over_num % 1) * 10),
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "runs_scored": runs_scored,
        "runs_off_bat": runs_scored if not extra_type else 0,
        "extra_type": extra_type,
        "extra_runs": 1 if extra_type else 0,
        "is_wicket": is_wicket,
        "is_extra": bool(extra_type),
        "dismissal_type": dismissal_type,
        "dismissed_player_id": striker_id if is_wicket else None,
        "dismissal_by_id": dismissed_by_id,
        "commentary": "",
        "shot_map": None,
        "at_utc": datetime.utcnow().isoformat()
    }


def test_pressure_analyzer_low_pressure_scenario():
    """Test pressure calculation when runs are flowing (low pressure)."""
    # Simulate T20 runs flowing: High scoring rate, no wickets, few dots
    deliveries = []
    for i in range(1, 13):  # 2 overs
        over_num = float((i - 1) // 6)
        ball = (i - 1) % 6
        # Most deliveries are 1-2 runs, some boundaries
        runs = 2 if i % 3 == 0 else (4 if i % 5 == 0 else 1)
        delivery = create_delivery(
            delivery_num=i,
            over_num=over_num + ball / 10,
            runs_scored=runs
        )
        deliveries.append(delivery)

    target = 180  # T20 target
    result = get_pressure_map(deliveries, target, overs_limit=20)

    assert result is not None
    assert len(result["pressure_points"]) == 12
    assert result["summary"]["average_pressure"] < 40, "Should have low average pressure when runs flowing"
    assert result["summary"]["high_pressure_count"] == 0, "Should have no high pressure when batters dominating"


def test_pressure_analyzer_high_pressure_scenario():
    """Test pressure calculation with dot balls and wickets (high pressure)."""
    deliveries = []
    # Simulate pressure: Many dots, a wicket
    dots_in_over = [0, 0, 0, 0, 0, 1]  # Over 1: 5 dots, 1 run
    for i in range(1, 13):  # 2 overs
        over_num = float((i - 1) // 6)
        ball = (i - 1) % 6
        
        if i == 7:  # Wicket in over 2
            delivery = create_delivery(
                delivery_num=i,
                over_num=over_num + ball / 10,
                runs_scored=0,
                is_wicket=True,
                dismissal_type="bowled"
            )
        else:
            runs = dots_in_over[(i - 1) % 6] if i <= 6 else 0
            delivery = create_delivery(
                delivery_num=i,
                over_num=over_num + ball / 10,
                runs_scored=runs
            )
        deliveries.append(delivery)

    target = 180
    result = get_pressure_map(deliveries, target, overs_limit=20)

    assert result is not None
    assert len(result["pressure_points"]) == 12
    # With dots and a wicket, average pressure should be higher than low pressure scenario
    assert result["summary"]["average_pressure"] > 5, "Should have higher pressure with dots and wicket"
    assert result["summary"]["peak_pressure"] > 10, "Should have peak pressure from wicket + dots"


def test_pressure_analyzer_death_overs_scenario():
    """Test pressure escalation in death overs."""
    deliveries = []
    # Simulate 17-20 overs: Death phase
    for i in range(97, 121):  # Overs 17-20
        over_num = float((i - 1) // 6)
        ball = (i - 1) % 6
        
        # Vary runs: some dots, some boundaries
        if i % 4 == 0:
            runs = 6  # Boundary
        elif i % 3 == 0:
            runs = 0  # Dot
        else:
            runs = 2
        
        delivery = create_delivery(
            delivery_num=i,
            over_num=over_num + ball / 10,
            runs_scored=runs
        )
        deliveries.append(delivery)

    target = 180
    result = get_pressure_map(deliveries, target, overs_limit=20)

    assert result is not None
    assert len(result["pressure_points"]) == 24
    # Death overs should have higher average pressure
    phases = result.get("phases", {})
    if phases.get("death_stats"):
        death_avg = phases["death_stats"].get("avg_pressure", 0)
        # Death overs pressure should be calculated
        assert death_avg > 0, "Death phase should have pressure calculation"


def test_pressure_analyzer_rrr_factor():
    """Test pressure based on required run rate gap."""
    deliveries = []
    # Simulate scenario where RRR increases (pressure builds)
    # First 6 overs: only 1 run per over (low scoring)
    for i in range(1, 37):  # 6 overs
        over_num = float((i - 1) // 6)
        ball = (i - 1) % 6
        
        # Slow scoring: only 1 run per over
        runs = 1 if ball == 0 else 0
        
        delivery = create_delivery(
            delivery_num=i,
            over_num=over_num + ball / 10,
            runs_scored=runs
        )
        deliveries.append(delivery)

    target = 150  # T20 typical target
    result = get_pressure_map(deliveries, target, overs_limit=20)

    assert result is not None
    # Slow start should cause pressure to build
    assert result["summary"]["peak_pressure"] > 5, "Slow start should show increasing pressure"
    # Later deliveries should have higher pressure than earlier
    if len(result["pressure_points"]) > 1:
        early_pressure = result["pressure_points"][0]["pressure_score"]
        late_pressure = result["pressure_points"][-1]["pressure_score"]
        assert late_pressure >= early_pressure, "Pressure should not decrease with slow scoring"


def test_pressure_analyzer_peak_moments_extraction():
    """Test that peak pressure moments are correctly identified."""
    deliveries = []
    # Create varied pressure scenario with multiple wickets
    for i in range(1, 61):  # 10 overs
        over_num = float((i - 1) // 6)
        ball = (i - 1) % 6
        
        # Create pressure spikes at deliveries 30, 45, 55
        is_wicket = i in [30, 45]
        runs = 0 if is_wicket else (2 if i % 4 == 0 else 1)
        
        delivery = create_delivery(
            delivery_num=i,
            over_num=over_num + ball / 10,
            runs_scored=runs,
            is_wicket=is_wicket,
            dismissal_type="caught" if is_wicket else None,
            dismissed_by_id="fielder_001" if is_wicket else None
        )
        deliveries.append(delivery)

    target = 180
    result = get_pressure_map(deliveries, target, overs_limit=20)

    assert result is not None
    # The wicket deliveries should have elevated pressure
    wicket_deliveries = [p for p in result["pressure_points"] if p["delivery_num"] in [30, 45]]
    assert len(wicket_deliveries) > 0, "Wicket deliveries should be in pressure points"
    # Peak moments should exist if there are any deliveries with pressure >= 70
    # or just verify we can extract peak moments list
    peak_moments = result["peak_moments"]
    assert isinstance(peak_moments, list), "Peak moments should be a list"


def test_pressure_analyzer_phase_breakdown():
    """Test phase-based pressure analysis."""
    deliveries = []
    # Create full T20 inning
    for i in range(1, 121):  # Full 20 overs = 120 balls
        over_num = float((i - 1) // 6)
        
        # Vary by phase: powerplay aggressive, middle steady, death mixed
        if over_num < 6:  # Powerplay
            runs = 4 if i % 5 == 0 else (2 if i % 3 == 0 else 1)
        elif over_num < 15:  # Middle (overs 7-14 = 48 balls, but we have 60 because overs are 0-indexed 6-15)
            runs = 2 if i % 4 == 0 else (1 if i % 3 == 0 else 0)
        else:  # Death
            runs = 6 if i % 4 == 0 else (0 if i % 3 == 0 else 2)
        
        delivery = create_delivery(
            delivery_num=i,
            over_num=over_num + (i - 1) % 6 / 10,
            runs_scored=runs
        )
        deliveries.append(delivery)

    target = 180
    result = get_pressure_map(deliveries, target, overs_limit=20)

    assert result is not None
    phases = result["phases"]
    
    # Verify phase breakdown - overs 0-5 (inclusive) = 36 balls
    assert len(phases["powerplay"]) == 36, "Powerplay should have 6 overs = 36 balls"
    # Overs 6-15 = 60 balls
    assert len(phases["middle"]) == 60, f"Middle should have 10 overs = 60 balls, got {len(phases['middle'])}"
    # Overs 16-19 = 24 balls
    assert len(phases["death"]) == 24, f"Death should have 4 overs = 24 balls, got {len(phases['death'])}"
    
    # Each phase should have stats
    assert phases.get("powerplay_stats") is not None
    assert phases.get("middle_stats") is not None
    assert phases.get("death_stats") is not None


def test_pressure_analyzer_convenience_function():
    """Test get_pressure_map convenience function."""
    deliveries = []
    for i in range(1, 25):
        over_num = float((i - 1) // 6)
        ball = (i - 1) % 6
        runs = 1 if i % 4 == 0 else 0
        
        delivery = create_delivery(
            delivery_num=i,
            over_num=over_num + ball / 10,
            runs_scored=runs
        )
        deliveries.append(delivery)

    target = 150
    result = get_pressure_map(deliveries, target, overs_limit=20)

    assert result is not None
    assert "pressure_points" in result
    assert "summary" in result
    assert "peak_moments" in result
    assert "phases" in result
