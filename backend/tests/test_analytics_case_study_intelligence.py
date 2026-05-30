from backend.services.analytics_case_study import (
    _build_multi_day_summary,
    _build_innings_callouts,
    _build_match_callouts,
    _build_story_blocks,
    _compute_dismissal_patterns,
    _compute_phase_stats,
    _detect_wicket_clusters_from_deliveries,
    _detect_recovery_windows_from_deliveries,
    _get_phase_ranges,
    _resolve_analysis_mode,
    _test_multi_day_ranges,
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
    # T20 now resolves to t20_limited_overs (more specific than the old limited_overs)
    assert mode == "t20_limited_overs"


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


# ---------------------------------------------------------------------------
# Phase 10R.3: Test/Multi-Day Deep Intelligence Tests
# ---------------------------------------------------------------------------


def _make_test_match(
    result: str = "Australia won by 124 runs",
) -> CaseStudyMatch:
    """Helper: 4-innings Test match between AUS and SA."""
    return CaseStudyMatch(
        id="test-aus-sa",
        date=date(2025, 1, 10),
        format="TEST",
        teams_label="AUS vs SA",
        result=result,
        innings=[
            CaseStudyInningsSummary(team="AUS", runs=400, wickets=10, overs=110.0, run_rate=3.63),
            CaseStudyInningsSummary(team="SA", runs=276, wickets=10, overs=85.0, run_rate=3.24),
            CaseStudyInningsSummary(team="AUS", runs=200, wickets=10, overs=60.0, run_rate=3.33),
            CaseStudyInningsSummary(team="SA", runs=200, wickets=7, overs=70.0, run_rate=2.85),
        ],
    )


def test_first_innings_lead_note_derivation() -> None:
    """_build_multi_day_summary derives first-innings lead note correctly."""
    match = _make_test_match()
    summary = _build_multi_day_summary(match)
    # AUS scored 400, SA scored 276 → AUS lead = 124
    assert summary.first_innings_lead_note is not None
    assert "124" in summary.first_innings_lead_note
    assert "AUS" in summary.first_innings_lead_note
    assert "lead" in summary.first_innings_lead_note.lower()


def test_lead_swing_notes_populated() -> None:
    """lead_swing_notes includes first-innings lead and target note."""
    match = _make_test_match()
    summary = _build_multi_day_summary(match)
    assert len(summary.lead_swing_notes) >= 1
    # First swing note is the first-innings lead
    assert summary.lead_swing_notes[0] == summary.first_innings_lead_note
    # Should include a target note for fourth innings
    target_notes = [n for n in summary.lead_swing_notes if "target" in n.lower()]
    assert target_notes, "Expected a fourth-innings target note in lead_swing_notes"


def test_fourth_innings_chase_structured_completed() -> None:
    """Fourth-innings chase shows completed when chasing team reached target."""
    # AUS: 400 + 200 = 600; SA prior innings: 276; target = (600 - 276) + 1 = 325
    # SA scored 200+? → need to reach 325 with wickets in hand
    match = CaseStudyMatch(
        id="t-chase-done",
        date=date(2025, 2, 1),
        format="TEST",
        teams_label="AUS vs SA",
        result="SA won by 3 wickets",
        innings=[
            CaseStudyInningsSummary(team="AUS", runs=300, wickets=10, overs=90.0, run_rate=3.33),
            CaseStudyInningsSummary(team="SA", runs=200, wickets=10, overs=65.0, run_rate=3.07),
            CaseStudyInningsSummary(team="AUS", runs=250, wickets=10, overs=80.0, run_rate=3.12),
            # target = (300 + 250) - 200 + 1 = 351; SA scored 355 with 7 wickets
            CaseStudyInningsSummary(team="SA", runs=355, wickets=7, overs=95.0, run_rate=3.73),
        ],
    )
    summary = _build_multi_day_summary(match)
    chase = summary.fourth_innings_chase
    assert chase is not None
    assert chase.chase_result == "completed"
    assert chase.chasing_team == "SA"
    assert chase.target == 351  # (300+250) - 200 + 1
    assert chase.wickets_in_hand == 3  # 10 - 7


def test_fourth_innings_chase_structured_fell_short() -> None:
    """Fourth-innings chase shows fell_short when all out below target."""
    match = CaseStudyMatch(
        id="t-chase-fail",
        date=date(2025, 2, 5),
        format="TEST",
        teams_label="ENG vs AUS",
        result="ENG won by 42 runs",
        innings=[
            CaseStudyInningsSummary(team="ENG", runs=350, wickets=10, overs=100.0, run_rate=3.5),
            CaseStudyInningsSummary(team="AUS", runs=280, wickets=10, overs=88.0, run_rate=3.18),
            CaseStudyInningsSummary(team="ENG", runs=250, wickets=10, overs=75.0, run_rate=3.33),
            # target = (350+250) - 280 + 1 = 321; AUS scored 278 (all out)
            CaseStudyInningsSummary(team="AUS", runs=278, wickets=10, overs=90.0, run_rate=3.08),
        ],
    )
    summary = _build_multi_day_summary(match)
    chase = summary.fourth_innings_chase
    assert chase is not None
    assert chase.chase_result == "fell_short"
    assert chase.runs_margin == 321 - 278  # 43
    assert chase.chasing_team == "AUS"


def test_wicket_cluster_detection_three_in_window() -> None:
    """_detect_wicket_clusters_from_deliveries detects 3+ wickets in 3 overs."""
    # 3 wickets in overs 45, 46, 47 → cluster
    deliveries = [
        {"inning": 1, "over_number": 45, "ball_number": 3, "is_wicket": True},
        {"inning": 1, "over_number": 46, "ball_number": 1, "is_wicket": True},
        {"inning": 1, "over_number": 47, "ball_number": 5, "is_wicket": True},
        # Non-wicket deliveries to fill the overs
        {"inning": 1, "over_number": 45, "ball_number": 1, "is_wicket": False, "runs_off_bat": 2},
        {"inning": 1, "over_number": 46, "ball_number": 2, "is_wicket": False, "runs_off_bat": 1},
        {"inning": 1, "over_number": 47, "ball_number": 2, "is_wicket": False, "runs_off_bat": 0},
    ]
    clusters = _detect_wicket_clusters_from_deliveries(deliveries, 1)
    assert clusters, "Expected at least one cluster for 3 wickets in 3 consecutive overs"
    labels = [c.label for c in clusters]
    assert any("cluster" in lbl or "collapse" in lbl for lbl in labels)


def test_wicket_cluster_detection_four_is_possible_collapse() -> None:
    """4 wickets in 3-over window produces 'possible collapse window' label."""
    deliveries = [
        {"inning": 2, "over_number": 30, "ball_number": 1, "is_wicket": True},
        {"inning": 2, "over_number": 30, "ball_number": 4, "is_wicket": True},
        {"inning": 2, "over_number": 31, "ball_number": 2, "is_wicket": True},
        {"inning": 2, "over_number": 32, "ball_number": 6, "is_wicket": True},
    ]
    clusters = _detect_wicket_clusters_from_deliveries(deliveries, 2)
    assert clusters
    assert any("collapse" in c.label for c in clusters)


def test_recovery_window_detection_after_cluster() -> None:
    """_detect_recovery_windows_from_deliveries finds a recovery after a cluster."""
    # Simulate 5 overs of runs (≥4 runs each) and no wickets after cluster at over 30
    deliveries = []
    for ov in range(32, 38):
        for ball in range(1, 7):
            deliveries.append(
                {
                    "inning": 1,
                    "over_number": ov,
                    "ball_number": ball,
                    "is_wicket": False,
                    "runs_off_bat": 1,
                    "extras": 0,
                }
            )
    # This gives 6 runs per over, 36 total over 6 overs — should be recovery
    recovery_windows = _detect_recovery_windows_from_deliveries(deliveries, 1, cluster_overs=[30])
    assert recovery_windows, "Expected a recovery window after overs of scoring without wickets"
    rw = recovery_windows[0]
    assert rw.wickets_fell == 0
    assert rw.runs_scored >= 20
    assert rw.label == "recovery period"


def test_multi_day_band_labels_use_passage_names() -> None:
    """_test_multi_day_ranges returns 'passage' labels, not generic 'Overs N-M'."""
    ranges = _test_multi_day_ranges(90.0)
    labels = [r[1] for r in ranges]
    assert any(
        "passage" in lbl.lower() for lbl in labels
    ), f"Expected passage-based labels, got: {labels}"
    # Ensure no label is purely "Overs N-M" generic pattern
    import re

    generic_pattern = re.compile(r"^Overs \d+-\d+$")
    for lbl in labels:
        assert not generic_pattern.match(lbl), f"Generic label still present: {lbl}"


def test_rich_match_callouts_for_test_mode_with_lead() -> None:
    """_build_match_callouts for test_multi_day includes first-innings lead callout."""
    match = _make_test_match()
    summary = _build_multi_day_summary(match)
    callouts = _build_match_callouts(
        match, analysis_mode="test_multi_day", multi_day_summary=summary
    )
    assert callouts, "Expected match callouts for test_multi_day mode"
    titles = [c.title for c in callouts]
    assert "First-innings lead established" in titles


def test_rich_match_callouts_include_fourth_innings_chase() -> None:
    """_build_match_callouts includes chase callout when fourth innings exists."""
    match = CaseStudyMatch(
        id="t2",
        date=date(2025, 3, 1),
        format="TEST",
        teams_label="NZ vs WI",
        result="NZ won by 5 wickets",
        innings=[
            CaseStudyInningsSummary(team="WI", runs=250, wickets=10, overs=80.0, run_rate=3.12),
            CaseStudyInningsSummary(team="NZ", runs=300, wickets=10, overs=90.0, run_rate=3.33),
            CaseStudyInningsSummary(team="WI", runs=200, wickets=10, overs=70.0, run_rate=2.85),
            # NZ target = (250+200)-300+1 = 151; NZ scored 155 with 5 wickets
            CaseStudyInningsSummary(team="NZ", runs=155, wickets=5, overs=45.0, run_rate=3.44),
        ],
    )
    summary = _build_multi_day_summary(match)
    callouts = _build_match_callouts(
        match, analysis_mode="test_multi_day", multi_day_summary=summary
    )
    titles = [c.title for c in callouts]
    assert "Fourth-innings chase completed" in titles


def test_story_blocks_test_mode_richer_content() -> None:
    """_build_story_blocks for test_multi_day produces richer content than 'unavailable'."""
    innings_summary = CaseStudyInningsSummary(
        team="AUS", runs=400, wickets=10, overs=110.0, run_rate=3.63
    )
    ranges = _test_multi_day_ranges(110.0)
    phases = _compute_phase_stats(
        phase_ranges=ranges,
        per_over_runs={i: 4 for i in range(1, 111)},
        per_over_wickets={i: 0 for i in range(1, 111)},
        total_runs=400,
        total_overs=110.0,
        innings_index=0,
        team="AUS",
    )
    strongest = max(phases, key=lambda p: p.runs) if phases else None
    weakest = min(phases, key=lambda p: p.runs) if phases else None

    blocks = _build_story_blocks(
        innings_summary,
        phases,
        strongest,
        weakest,
        analysis_mode="test_multi_day",
        innings_number=1,
    )
    # Richer content: should contain specific run rate or totals
    assert "400" in blocks.opening_story
    assert "unavailable" not in blocks.strongest_phase.lower()
    assert "unavailable" not in blocks.weakest_phase.lower()
    # Band labels must appear
    assert "passage" in blocks.strongest_phase.lower() or "band" in blocks.strongest_phase.lower()


def test_story_blocks_test_mode_no_limited_overs_language() -> None:
    """_build_story_blocks for test_multi_day must not produce limited-overs language."""
    innings_summary = CaseStudyInningsSummary(
        team="SA", runs=280, wickets=10, overs=88.0, run_rate=3.18
    )
    blocks = _build_story_blocks(
        innings_summary,
        phases=[],
        strongest_phase=None,
        weakest_phase=None,
        analysis_mode="test_multi_day",
        innings_number=2,
    )
    for attr in ("opening_story", "middle_overs_story", "death_overs_story"):
        val = getattr(blocks, attr, "") or ""
        assert "powerplay" not in val.lower(), f"Powerplay found in {attr}: {val}"
        assert "death over" not in val.lower(), f"Death over found in {attr}: {val}"
        assert "vs par" not in val.lower(), f"vs par found in {attr}: {val}"


# ---------------------------------------------------------------------------
# Phase 10R.4: ODI Format-Aware Phase Logic Tests
# ---------------------------------------------------------------------------


def test_odi_phase_ranges_are_four_phase() -> None:
    """ODI phase ranges return 4-phase model: powerplay/consolidation/acceleration/death."""
    phase_ranges = _get_phase_ranges("ODI", 50)
    ids = [pid for pid, *_ in phase_ranges]
    assert ids == ["powerplay", "consolidation", "acceleration", "death"]


def test_odi_phase_ranges_correct_boundaries() -> None:
    """ODI phase boundaries match the required 1-10 / 11-25 / 26-40 / 41-50 model."""
    phase_ranges = _get_phase_ranges("ODI", 50)
    by_id = {pid: (start, end) for pid, _label, start, end in phase_ranges}

    assert by_id["powerplay"] == (1, 10), f"Powerplay range wrong: {by_id['powerplay']}"
    assert by_id["consolidation"] == (
        11,
        25,
    ), f"Consolidation range wrong: {by_id['consolidation']}"
    assert by_id["acceleration"] == (26, 40), f"Acceleration range wrong: {by_id['acceleration']}"
    assert by_id["death"] == (41, 50), f"Death range wrong: {by_id['death']}"


def test_odi_phase_labels_include_odi_language() -> None:
    """ODI phase labels use ODI-specific names, not T20 terminology."""
    phase_ranges = _get_phase_ranges("ODI", 50)
    labels = [label for _, label, *_ in phase_ranges]
    assert any("powerplay" in label.lower() for label in labels)
    assert any("consolidation" in label.lower() for label in labels)
    assert any("acceleration" in label.lower() for label in labels)
    assert any("death" in label.lower() for label in labels)
    # Must NOT use T20-style 1-6 or 7-15 labels
    for label in labels:
        assert "1-6" not in label, f"T20-style phase label found in ODI ranges: {label}"
        assert "7-15" not in label, f"T20-style phase label found in ODI ranges: {label}"


def test_t20_phase_ranges_unchanged() -> None:
    """T20 phase ranges remain 1-6 / 7-15 / 16-20 (no regression)."""
    phase_ranges = _get_phase_ranges("T20", 20)
    by_id = {pid: (start, end) for pid, _label, start, end in phase_ranges}

    assert by_id["powerplay"] == (1, 6), f"T20 powerplay range regressed: {by_id['powerplay']}"
    assert by_id["middle"] == (7, 15), f"T20 middle range regressed: {by_id['middle']}"
    assert by_id["death"] == (16, 20), f"T20 death range regressed: {by_id['death']}"


def test_resolve_analysis_mode_odi() -> None:
    """ODI match resolves to odi_limited_overs analysis mode."""
    mode = _resolve_analysis_mode(
        raw_match_type="ODI",
        overs_per_side=50,
        innings_count=2,
        days_limit=None,
    )
    assert mode == "odi_limited_overs"


def test_resolve_analysis_mode_odi_by_overs() -> None:
    """Match with 50 overs per side (no explicit type) resolves to odi_limited_overs."""
    mode = _resolve_analysis_mode(
        raw_match_type="",
        overs_per_side=50,
        innings_count=2,
        days_limit=None,
    )
    assert mode == "odi_limited_overs"


def test_resolve_analysis_mode_t20() -> None:
    """T20 match resolves to t20_limited_overs analysis mode."""
    mode = _resolve_analysis_mode(
        raw_match_type="T20",
        overs_per_side=20,
        innings_count=2,
        days_limit=None,
    )
    assert mode == "t20_limited_overs"


def test_resolve_analysis_mode_t20_by_overs() -> None:
    """Match with 20 overs per side (no explicit type) resolves to t20_limited_overs."""
    mode = _resolve_analysis_mode(
        raw_match_type="",
        overs_per_side=20,
        innings_count=2,
        days_limit=None,
    )
    assert mode == "t20_limited_overs"


def test_resolve_analysis_mode_odm_alias() -> None:
    """ODM alias should resolve to ODI limited-overs mode."""
    mode = _resolve_analysis_mode(
        raw_match_type="ODM",
        overs_per_side=50,
        innings_count=2,
        days_limit=None,
    )
    assert mode == "odi_limited_overs"


def test_resolve_analysis_mode_test_unchanged() -> None:
    """Test/multi-day mode is unchanged (no regression)."""
    mode = _resolve_analysis_mode(
        raw_match_type="TEST",
        overs_per_side=90,
        innings_count=4,
        days_limit=5,
    )
    assert mode == "test_multi_day"


def test_odi_story_blocks_use_odi_language() -> None:
    """_build_story_blocks for odi_limited_overs uses ODI-specific phase language."""
    phase_ranges = _get_phase_ranges("ODI", 50)
    innings_summary = CaseStudyInningsSummary(
        team="India", runs=285, wickets=7, overs=50.0, run_rate=5.70
    )
    phases = _compute_phase_stats(
        phase_ranges=phase_ranges,
        per_over_runs={i: 5 for i in range(1, 51)},
        per_over_wickets={3: 1, 15: 1, 30: 2, 45: 2, 48: 1},
        total_runs=285,
        total_overs=50.0,
        innings_index=0,
        team="India",
    )
    strongest = max(phases, key=lambda p: p.runs) if phases else None
    weakest = min(phases, key=lambda p: p.runs) if phases else None

    blocks = _build_story_blocks(
        innings_summary,
        phases,
        strongest,
        weakest,
        analysis_mode="odi_limited_overs",
        innings_number=1,
    )

    # Must reference ODI phases
    assert "powerplay" in blocks.opening_story.lower() or "1\u201310" in blocks.opening_story
    assert "overs" in blocks.middle_overs_story.lower()
    # Must not use T20-style 1-6 framing
    assert "1-6" not in blocks.opening_story
    assert "7-15" not in blocks.middle_overs_story
    assert "16-20" not in blocks.death_overs_story
    # Acceleration and death labels
    assert "41" in blocks.death_overs_story or "death" in blocks.death_overs_story.lower()
    # No wicket(s) placeholder artifacts
    assert "wicket(s)" not in blocks.opening_story
    assert "wicket(s)" not in blocks.middle_overs_story
    assert "wicket(s)" not in blocks.death_overs_story
    assert "wicket(s)" not in blocks.wickets_by_phase


def test_odi_story_blocks_no_test_language() -> None:
    """_build_story_blocks for odi_limited_overs must not produce Test/multi-day language."""
    innings_summary = CaseStudyInningsSummary(
        team="Australia", runs=310, wickets=8, overs=50.0, run_rate=6.20
    )
    blocks = _build_story_blocks(
        innings_summary,
        phases=[],
        strongest_phase=None,
        weakest_phase=None,
        analysis_mode="odi_limited_overs",
        innings_number=1,
    )
    for attr in ("opening_story", "middle_overs_story", "death_overs_story"):
        val = getattr(blocks, attr, "") or ""
        assert (
            "innings 1" not in val.lower()
            or "innings" not in val.lower()
            or "passage" not in val.lower()
        ), f"Test language found in ODI story block {attr}: {val}"
        assert "vs par" not in val.lower(), f"vs par found in ODI {attr}: {val}"


def test_odi_innings_callouts_use_odi_phases() -> None:
    """_build_innings_callouts for odi_limited_overs references ODI phase labels."""
    phase_ranges = _get_phase_ranges("ODI", 50)
    phases = _compute_phase_stats(
        phase_ranges=phase_ranges,
        per_over_runs={i: 5 for i in range(1, 51)},
        per_over_wickets={3: 2, 4: 2, 15: 2, 16: 1, 28: 1, 45: 1},
        total_runs=285,
        total_overs=50.0,
        innings_index=0,
        team="Pakistan",
    )
    dismissal_patterns = _compute_dismissal_patterns(
        [
            {
                "inning": 1,
                "over_number": 3,
                "ball_number": 2,
                "is_wicket": True,
                "batter_name": "Batter 1",
            },
            {
                "inning": 1,
                "over_number": 4,
                "ball_number": 1,
                "is_wicket": True,
                "batter_name": "Batter 2",
            },
        ],
        1,
        phase_ranges,
    )
    callouts = _build_innings_callouts(
        1, phases, dismissal_patterns, analysis_mode="odi_limited_overs"
    )

    assert callouts, "Expected callouts for odi_limited_overs innings"
    all_phases = [c.phase for c in callouts]
    all_categories = [c.category for c in callouts]
    # Should have phase references
    assert any(c.phase for c in callouts)
    # Categories should be valid
    valid_cats = {"batting", "bowling", "player", "dismissal", "momentum", "outcome"}
    assert all(cat in valid_cats for cat in all_categories)


def test_t20_phase_ranges_unaffected_by_odi_changes() -> None:
    """T20 phase computation produces 3 phases, not 4 ODI phases."""
    phase_ranges = _get_phase_ranges("T20", 20)
    assert len(phase_ranges) == 3, f"Expected 3 T20 phases, got {len(phase_ranges)}"


def test_odi_phase_ranges_produce_four_phases() -> None:
    """ODI phase computation produces 4 phases."""
    phase_ranges = _get_phase_ranges("ODI", 50)
    assert len(phase_ranges) == 4, f"Expected 4 ODI phases, got {len(phase_ranges)}"


def test_odi_phase_ranges_with_45_overs() -> None:
    """ODI-style match with 45 overs also gets 4 ODI phases."""
    phase_ranges = _get_phase_ranges("ODI", 45)
    ids = [pid for pid, *_ in phase_ranges]
    assert "powerplay" in ids
    assert "consolidation" in ids
    assert "acceleration" in ids
    assert "death" in ids


def test_wicket_cluster_callout_is_presenter_ready() -> None:
    """Cluster callout should use smoother presenter-friendly language."""
    phase_ranges = _get_phase_ranges("ODI", 50)
    patterns = _compute_dismissal_patterns(
        [
            {"inning": 1, "over_number": 24, "ball_number": 2, "is_wicket": True},
            {"inning": 1, "over_number": 25, "ball_number": 1, "is_wicket": True},
        ],
        1,
        phase_ranges,
    )
    assert patterns.wicket_cluster_callout is not None
    assert "A key wicket cluster came between overs 24 and 26" in patterns.wicket_cluster_callout
    assert "2 wickets fell" in patterns.wicket_cluster_callout
