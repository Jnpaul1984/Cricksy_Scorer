from backend.services.analytics_case_study import (
    _build_innings_callouts,
    _compute_dismissal_patterns,
    _compute_phase_stats,
    _get_phase_ranges,
)


def test_compute_dismissal_patterns_produces_timeline_and_fallback_flags() -> None:
    phase_ranges = _get_phase_ranges("T20", 20)
    deliveries = [
        {
            "inning": 1,
            "over_number": 8,
            "ball_number": 2,
            "is_wicket": True,
            "dismissal_type": "caught",
            "bowler_name": "A Bowler",
            "fielder_name": "A Fielder",
            "batter_name": "Batter 1",
        },
        {
            "inning": 1,
            "over_number": 9,
            "ball_number": 1,
            "is_wicket": True,
            "dismissal_type": "bowled",
            "bowler_name": "A Bowler",
            "batter_name": "Batter 2",
        },
    ]

    patterns = _compute_dismissal_patterns(deliveries, 1, phase_ranges)
    assert patterns.total_wickets == 2
    assert len(patterns.wicket_timeline) == 2
    assert patterns.dismissal_types[0]["type"] in {"caught", "bowled"}
    assert patterns.fallback_reason is None


def test_compute_dismissal_patterns_handles_missing_delivery_data() -> None:
    phase_ranges = _get_phase_ranges("T20", 20)
    patterns = _compute_dismissal_patterns([], 2, phase_ranges)
    assert patterns.total_wickets == 0
    assert patterns.fallback_reason == "No ball-by-ball data available."


def test_build_innings_callouts_contains_required_structure() -> None:
    phase_ranges = _get_phase_ranges("T20", 20)
    phases = _compute_phase_stats(
        phase_ranges=phase_ranges,
        per_over_runs={7: 3, 8: 4, 9: 2, 16: 15, 17: 14},
        per_over_wickets={7: 1, 8: 1, 9: 1, 17: 1},
        total_runs=140,
        total_overs=20.0,
        innings_index=0,
        team="Team A",
    )
    dismissal_patterns = _compute_dismissal_patterns(
        [
            {"inning": 1, "over_number": 16, "ball_number": 2, "is_wicket": True},
            {"inning": 1, "over_number": 17, "ball_number": 3, "is_wicket": True},
            {"inning": 1, "over_number": 18, "ball_number": 1, "is_wicket": True},
        ],
        1,
        phase_ranges,
    )
    callouts = _build_innings_callouts(1, phases, dismissal_patterns)

    assert callouts, "Expected deterministic callouts for innings analysis"
    first = callouts[0]
    assert first.phase
    assert first.category in {"batting", "bowling", "player", "dismissal", "momentum", "outcome"}
    assert isinstance(first.source_metrics, list)
    assert 0.0 <= first.confidence <= 1.0
    assert first.why_it_matters
