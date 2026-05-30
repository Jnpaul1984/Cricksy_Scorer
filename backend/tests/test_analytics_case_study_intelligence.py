from backend.services.analytics_case_study import (
    _build_multi_day_summary,
    _build_innings_callouts,
    _compute_dismissal_patterns,
    _compute_phase_stats,
    _get_phase_ranges,
    _resolve_analysis_mode,
)
from backend.api.schemas.case_study import CaseStudyInningsSummary, CaseStudyMatch
from datetime import date


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


def test_resolve_analysis_mode_uses_test_multi_day_for_four_innings() -> None:
    mode = _resolve_analysis_mode(
        raw_match_type="TEST",
        overs_per_side=90,
        innings_count=4,
        days_limit=5,
    )
    assert mode == "test_multi_day"


def test_resolve_analysis_mode_preserves_limited_overs() -> None:
    mode = _resolve_analysis_mode(
        raw_match_type="T20",
        overs_per_side=20,
        innings_count=2,
        days_limit=None,
    )
    assert mode == "limited_overs"


def test_multi_day_summary_represents_four_innings() -> None:
    match = CaseStudyMatch(
        id="test-match",
        date=date(2025, 1, 1),
        format="TEST",
        teams_label="AUS vs SA",
        result="South Africa won by 3 wickets",
        innings=[
            CaseStudyInningsSummary(team="AUS", runs=320, wickets=10, overs=96.0, run_rate=3.33),
            CaseStudyInningsSummary(team="SA", runs=280, wickets=10, overs=88.0, run_rate=3.18),
            CaseStudyInningsSummary(team="AUS", runs=210, wickets=10, overs=70.0, run_rate=3.0),
            CaseStudyInningsSummary(team="SA", runs=251, wickets=7, overs=82.0, run_rate=3.06),
        ],
    )
    summary = _build_multi_day_summary(match)
    assert len(summary.innings) == 4
    assert summary.match_status == "won"
    assert summary.fourth_innings_chase_note is not None


def test_limited_overs_phase_labels_remain_for_t20() -> None:
    phase_ranges = _get_phase_ranges("T20", 20)
    labels = [label for _, label, *_ in phase_ranges]
    assert labels[0].startswith("Powerplay")
    assert "Middle Overs" in labels[1]
    assert "Death Overs" in labels[2]
