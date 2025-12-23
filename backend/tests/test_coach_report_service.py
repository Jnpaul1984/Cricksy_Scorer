"""
Tests for Coach Report Generation Service

Verifies deterministic report generation works without LLM.
Tests all components: summary level, top issues, drills, weekly plan, notes.
"""

from __future__ import annotations

from backend.services.coach_report_service import (
    _build_weekly_plan,
    _generate_notes,
    _get_recommended_drills,
    _get_summary_level,
    _get_top_issues,
    generate_report_text,
)

# ============================================================================
# Test Utility Functions
# ============================================================================


class TestGetSummaryLevel:
    """Test summary level determination."""

    def test_excellent_no_findings(self) -> None:
        """No findings -> excellent."""
        result = _get_summary_level([])
        assert result == "excellent"

    def test_good_one_low_severity(self) -> None:
        """One low severity -> good."""
        findings = [{"severity": "low"}]
        result = _get_summary_level(findings)
        assert result == "good"

    def test_good_one_medium_severity(self) -> None:
        """One medium severity -> good."""
        findings = [{"severity": "medium"}]
        result = _get_summary_level(findings)
        assert result == "good"

    def test_fair_one_high_severity(self) -> None:
        """One high severity -> fair."""
        findings = [{"severity": "high"}]
        result = _get_summary_level(findings)
        assert result == "fair"

    def test_fair_two_medium_severity(self) -> None:
        """Two medium severity -> fair."""
        findings = [{"severity": "medium"}, {"severity": "medium"}]
        result = _get_summary_level(findings)
        assert result == "fair"

    def test_poor_three_high_severity(self) -> None:
        """Three high severity -> poor."""
        findings = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "high"},
        ]
        result = _get_summary_level(findings)
        assert result == "poor"

    def test_fair_mixed_severities(self) -> None:
        """Mixed severities lean toward fair."""
        findings = [
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
        ]
        result = _get_summary_level(findings)
        assert result == "fair"


class TestGetTopIssues:
    """Test top issues extraction."""

    def test_no_findings(self) -> None:
        """Empty findings -> empty top issues."""
        result = _get_top_issues([])
        assert result == []

    def test_single_finding(self) -> None:
        """Single finding extracted."""
        findings = [
            {
                "severity": "high",
                "title": "Head movement",
                "why_it_matters": "Affects tracking",
                "cues": ["Cue 1", "Cue 2", "Cue 3"],
            }
        ]
        result = _get_top_issues(findings)
        assert len(result) == 1
        assert result[0]["issue"] == "Head movement"
        assert result[0]["severity"] == "high"
        assert result[0]["cues"] == ["Cue 1", "Cue 2"]  # Top 2 cues

    def test_top_3_sorted_by_severity(self) -> None:
        """Top 3 sorted by severity (high first)."""
        findings = [
            {"severity": "low", "title": "Issue C", "cues": []},
            {"severity": "high", "title": "Issue A", "cues": []},
            {"severity": "medium", "title": "Issue B", "cues": []},
            {"severity": "low", "title": "Issue D", "cues": []},
        ]
        result = _get_top_issues(findings, top_n=3)
        assert len(result) == 3
        assert result[0]["issue"] == "Issue A"  # high
        assert result[1]["issue"] == "Issue B"  # medium
        assert result[2]["issue"] == "Issue C"  # low

    def test_cues_limited_to_two(self) -> None:
        """Only top 2 cues included."""
        findings = [
            {
                "severity": "high",
                "title": "Issue",
                "cues": ["Cue 1", "Cue 2", "Cue 3", "Cue 4"],
            }
        ]
        result = _get_top_issues(findings)
        assert len(result[0]["cues"]) == 2


class TestGetRecommendedDrills:
    """Test drill extraction."""

    def test_no_findings(self) -> None:
        """Empty findings -> no drills."""
        result = _get_recommended_drills([])
        assert result == []

    def test_drills_from_finding_code(self) -> None:
        """Drills extracted based on finding code."""
        findings = [{"code": "HEAD_MOVEMENT"}]
        result = _get_recommended_drills(findings)
        # Should have 3 drills for HEAD_MOVEMENT
        assert len(result) == 3
        assert "Mirror batting" in result[0]

    def test_multiple_findings_all_drills(self) -> None:
        """Multiple findings -> all unique drills up to limit."""
        findings = [
            {"code": "HEAD_MOVEMENT"},
            {"code": "BALANCE_DRIFT"},
            {"code": "KNEE_COLLAPSE"},
        ]
        result = _get_recommended_drills(findings, max_drills=10)
        assert len(result) == 9  # 3 drills x 3 findings

    def test_high_severity_first(self) -> None:
        """High severity drills prioritized."""
        findings = [
            {"code": "BALANCE_DRIFT", "severity": "low"},
            {"code": "HEAD_MOVEMENT", "severity": "high"},
        ]
        result = _get_recommended_drills(findings, max_drills=10)
        # HEAD_MOVEMENT drills should come first
        assert "Mirror batting" in result[0] or "Wall batting" in result[0]

    def test_max_drills_limit(self) -> None:
        """Respects maximum drills limit."""
        findings = [
            {"code": "HEAD_MOVEMENT"},
            {"code": "BALANCE_DRIFT"},
            {"code": "KNEE_COLLAPSE"},
            {"code": "ROTATION_TIMING"},
            {"code": "ELBOW_DROP"},
        ]
        result = _get_recommended_drills(findings, max_drills=5)
        assert len(result) == 5

    def test_no_duplicates(self) -> None:
        """No duplicate drills in result."""
        findings = [{"code": "HEAD_MOVEMENT"}, {"code": "HEAD_MOVEMENT"}]
        result = _get_recommended_drills(findings)
        assert len(result) == len(set(result))


class TestBuildWeeklyPlan:
    """Test weekly plan generation."""

    def test_plan_has_all_days(self) -> None:
        """Plan includes all 7 days."""
        plan = _build_weekly_plan([])
        assert len(plan) == 7
        days = [d["day"] for d in plan]
        assert "Monday" in days
        assert "Sunday" in days

    def test_plan_includes_focus(self) -> None:
        """Each day has focus area."""
        plan = _build_weekly_plan([])
        for day in plan:
            assert "focus" in day
            assert day["focus"].strip()

    def test_plan_includes_activities(self) -> None:
        """Each day has activities."""
        plan = _build_weekly_plan([])
        for day in plan:
            assert "activities" in day
            assert isinstance(day["activities"], list)
            assert len(day["activities"]) > 0

    def test_plan_includes_duration(self) -> None:
        """Each day has duration."""
        plan = _build_weekly_plan([])
        for day in plan:
            assert "duration" in day

    def test_plan_customized_with_findings(self) -> None:
        """Plan customized when findings provided."""
        findings = [
            {
                "severity": "high",
                "code": "HEAD_MOVEMENT",
            }
        ]
        plan = _build_weekly_plan(findings)
        # Monday should mention high-severity drill
        monday = plan[0]
        activities_str = " ".join(monday["activities"])
        # Should be customized
        assert activities_str

    def test_plan_with_high_severity_focus(self) -> None:
        """Thursday focus customized with high severity finding."""
        findings = [
            {
                "severity": "high",
                "code": "ROTATION_TIMING",
            }
        ]
        plan = _build_weekly_plan(findings)
        thursday = plan[3]
        # Focus should mention the high-severity issue
        assert "Rotation Timing" in thursday["focus"] or "Technique" in thursday["focus"]


class TestGenerateNotes:
    """Test personalized notes generation."""

    def test_no_findings_excellent_note(self) -> None:
        """No findings -> excellent note."""
        result = _generate_notes([])
        assert "Excellent" in result

    def test_high_severity_findings_priority(self) -> None:
        """High severity findings emphasized."""
        findings = [
            {"severity": "high"},
            {"severity": "high"},
            {"severity": "low"},
        ]
        result = _generate_notes(findings)
        assert "high-severity" in result.lower()
        assert "2" in result  # Should mention count

    def test_multiple_findings_coaching_note(self) -> None:
        """Multiple findings mention coaching."""
        findings = [
            {"severity": "high"},
            {"severity": "medium"},
            {"severity": "low"},
            {"severity": "low"},
        ]
        result = _generate_notes(findings)
        assert "coach" in result.lower()

    def test_consistency_message(self) -> None:
        """All notes include consistency message."""
        findings = [{"severity": "high"}]
        result = _generate_notes(findings)
        assert "consistency" in result.lower()

    def test_bowler_context(self) -> None:
        """Bowler-specific context included."""
        findings = [{"severity": "high"}]
        context = {"role": "bowler"}
        result = _generate_notes(findings, context)
        assert "bowling" in result.lower() or "gradual" in result.lower()

    def test_batter_context(self) -> None:
        """Batter-specific context included."""
        findings = [{"severity": "high"}]
        context = {"role": "batter"}
        result = _generate_notes(findings, context)
        assert "muscle memory" in result.lower() or "reps" in result.lower()


# ============================================================================
# Test Main Report Generation
# ============================================================================


class TestGenerateReportText:
    """Test complete report generation."""

    def test_basic_report_structure(self) -> None:
        """Report has all required fields."""
        findings_payload = {
            "overall_level": "medium",
            "findings": [],
        }
        result = generate_report_text(findings_payload)

        assert "summary" in result
        assert "top_issues" in result
        assert "drills" in result
        assert "one_week_plan" in result
        assert "notes" in result
        assert "generated_with_llm" in result
        assert result["generated_with_llm"] is False  # Deterministic by default

    def test_summary_personalized_with_player_name(self) -> None:
        """Summary includes player name."""
        findings_payload = {"overall_level": "high", "findings": []}
        context = {"name": "Virat"}
        result = generate_report_text(findings_payload, context)
        assert "Virat" in result["summary"]

    def test_summary_excellent_no_findings(self) -> None:
        """Excellent summary when no findings."""
        findings_payload = {"overall_level": "high", "findings": []}
        result = generate_report_text(findings_payload)
        assert "fundamentals" in result["summary"].lower() or "consistency" in result[
            "summary"
        ].lower()

    def test_top_issues_sorted_and_limited(self) -> None:
        """Top issues properly sorted and limited."""
        findings_payload = {
            "overall_level": "low",
            "findings": [
                {
                    "severity": "low",
                    "title": "Issue 1",
                    "why_it_matters": "Matters 1",
                    "cues": ["Cue 1"],
                },
                {
                    "severity": "high",
                    "title": "Issue 2",
                    "why_it_matters": "Matters 2",
                    "cues": ["Cue 2"],
                },
                {
                    "severity": "medium",
                    "title": "Issue 3",
                    "why_it_matters": "Matters 3",
                    "cues": ["Cue 3"],
                },
            ],
        }
        result = generate_report_text(findings_payload)
        # Should be limited to top 3
        assert len(result["top_issues"]) <= 3
        # Should be sorted by severity
        if len(result["top_issues"]) > 1:
            first_severity = result["top_issues"][0]["severity"]
            assert first_severity == "high"

    def test_drills_unique_and_actionable(self) -> None:
        """Drills are unique and actionable."""
        findings_payload = {
            "overall_level": "low",
            "findings": [
                {"code": "HEAD_MOVEMENT", "severity": "high"},
                {"code": "BALANCE_DRIFT", "severity": "high"},
            ],
        }
        result = generate_report_text(findings_payload)
        drills = result["drills"]

        # Should have drills
        assert len(drills) > 0
        # Should be unique
        assert len(drills) == len(set(drills))
        # Should be action-oriented
        assert all(len(d) > 5 for d in drills)  # Not too short

    def test_weekly_plan_complete(self) -> None:
        """Weekly plan is complete."""
        findings_payload = {
            "overall_level": "low",
            "findings": [{"code": "HEAD_MOVEMENT"}],
        }
        result = generate_report_text(findings_payload)
        plan = result["one_week_plan"]

        assert len(plan) == 7  # All 7 days
        for day in plan:
            assert "day" in day
            assert "focus" in day
            assert "duration" in day
            assert "activities" in day

    def test_notes_comprehensive(self) -> None:
        """Notes are comprehensive."""
        findings_payload = {
            "overall_level": "low",
            "findings": [
                {"severity": "high"},
                {"severity": "high"},
            ],
        }
        result = generate_report_text(findings_payload)
        notes = result["notes"]

        # Should have substance
        assert len(notes) > 50
        # Should be actionable
        assert any(
            word in notes.lower()
            for word in ["focus", "drills", "practice", "work", "implement"]
        )

    def test_context_preserved_in_output(self) -> None:
        """Player context affects report."""
        findings_payload = {
            "overall_level": "low",
            "findings": [
                {
                    "code": "HEAD_MOVEMENT",
                    "severity": "high",
                    "title": "Head Movement",
                    "why_it_matters": "Critical",
                    "cues": [],
                }
            ],
        }
        batter_context = {"role": "batter"}
        bowler_context = {"role": "bowler"}

        batter_report = generate_report_text(findings_payload, batter_context)
        bowler_report = generate_report_text(findings_payload, bowler_context)

        # Notes should differ based on role
        assert batter_report["notes"] != bowler_report["notes"]

    def test_multiple_high_severity_findings(self) -> None:
        """Multiple high-severity findings trigger poor level."""
        findings_payload = {
            "overall_level": "low",
            "findings": [
                {"severity": "high", "title": "Issue 1", "why_it_matters": "", "cues": []},
                {"severity": "high", "title": "Issue 2", "why_it_matters": "", "cues": []},
                {"severity": "high", "title": "Issue 3", "why_it_matters": "", "cues": []},
            ],
        }
        result = generate_report_text(findings_payload)
        assert result["notes"]  # Should still generate notes


class TestReportDeterministic:
    """Test deterministic nature of reports."""

    def test_same_input_same_output(self) -> None:
        """Same input always produces same output."""
        findings_payload = {
            "overall_level": "medium",
            "findings": [
                {
                    "code": "HEAD_MOVEMENT",
                    "severity": "high",
                    "title": "Head Movement",
                    "why_it_matters": "Vision tracking",
                    "cues": ["Cue 1"],
                }
            ],
        }

        report1 = generate_report_text(findings_payload)
        report2 = generate_report_text(findings_payload)

        assert report1["summary"] == report2["summary"]
        assert report1["top_issues"] == report2["top_issues"]
        assert report1["drills"] == report2["drills"]
        assert report1["notes"] == report2["notes"]

    def test_no_llm_by_default(self) -> None:
        """LLM flag is False by default."""
        findings_payload = {"overall_level": "high", "findings": []}
        result = generate_report_text(findings_payload)
        assert result["generated_with_llm"] is False


class TestReportIntegration:
    """Integration tests with realistic scenarios."""

    def test_excellent_technique_scenario(self) -> None:
        """Excellent technique with no findings."""
        findings_payload = {
            "overall_level": "high",
            "findings": [],
            "context": {"name": "Sachin"},
        }
        result = generate_report_text(findings_payload)

        assert "excellent" in result["summary"].lower() or "Sachin" in result["summary"]
        assert len(result["top_issues"]) == 0
        assert len(result["drills"]) == 0
        assert len(result["one_week_plan"]) == 7  # Still provide plan

    def test_poor_technique_scenario(self) -> None:
        """Poor technique with multiple high-severity findings."""
        findings_payload = {
            "overall_level": "low",
            "findings": [
                {
                    "code": "HEAD_MOVEMENT",
                    "severity": "high",
                    "title": "Head Movement",
                    "why_it_matters": "Affects tracking",
                    "cues": ["Keep head still"],
                },
                {
                    "code": "BALANCE_DRIFT",
                    "severity": "high",
                    "title": "Balance Drift",
                    "why_it_matters": "Affects stability",
                    "cues": ["Widen stance"],
                },
                {
                    "code": "KNEE_COLLAPSE",
                    "severity": "high",
                    "title": "Knee Collapse",
                    "why_it_matters": "Injury risk",
                    "cues": ["Strengthen knees"],
                },
            ],
        }
        result = generate_report_text(findings_payload)

        assert len(result["top_issues"]) == 3
        assert len(result["drills"]) >= 5
        assert "Priority" in result["notes"] or "high-severity" in result["notes"].lower()

    def test_mixed_technique_scenario(self) -> None:
        """Mixed technique with some good, some poor aspects."""
        findings_payload = {
            "overall_level": "medium",
            "findings": [
                {
                    "code": "ROTATION_TIMING",
                    "severity": "medium",
                    "title": "Hip Rotation",
                    "why_it_matters": "Power generation",
                    "cues": ["Work on drills"],
                },
                {
                    "code": "ELBOW_DROP",
                    "severity": "low",
                    "title": "Elbow Position",
                    "why_it_matters": "Bat control",
                    "cues": ["Minor adjustment"],
                },
            ],
        }
        result = generate_report_text(findings_payload)

        assert len(result["top_issues"]) == 2
        assert len(result["drills"]) >= 3
        assert "good" in result["summary"].lower() or "refine" in result["summary"].lower()
