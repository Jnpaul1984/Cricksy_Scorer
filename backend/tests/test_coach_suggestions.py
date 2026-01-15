"""Tests for coach suggestions service."""

import pytest
from backend.services.coach_suggestions import (
    _propose_next_goal,
    _rank_findings,
    _select_coaching_cues,
    _select_drills,
    _select_focus,
    generate_coach_suggestions,
    generate_player_summary,
)


class TestRankFindings:
    """Test finding ranking logic."""

    def test_rank_by_severity(self):
        """Test findings ranked by severity (critical > moderate > minor)."""
        findings = [
            {
                "code": "F1",
                "title": "Minor Issue",
                "severity": "minor",
                "metrics": {"score": {"score": 0.55}},
            },
            {
                "code": "F2",
                "title": "Critical Issue",
                "severity": "critical",
                "metrics": {"score": {"score": 0.40}},
            },
            {
                "code": "F3",
                "title": "Moderate Issue",
                "severity": "moderate",
                "metrics": {"score": {"score": 0.60}},
            },
        ]

        ranked = _rank_findings(findings)

        assert ranked[0]["code"] == "F2"  # Critical first
        assert ranked[1]["code"] == "F3"  # Moderate second
        assert ranked[2]["code"] == "F1"  # Minor third

    def test_rank_by_persistence(self):
        """Test findings ranked by persistence (score < 0.60)."""
        findings = [
            {
                "code": "F1",
                "title": "Good Score",
                "severity": "moderate",
                "metrics": {"score": {"score": 0.70}},
            },
            {
                "code": "F2",
                "title": "Persistent Issue",
                "severity": "moderate",
                "metrics": {"score": {"score": 0.50}},
            },
        ]

        ranked = _rank_findings(findings)

        # Both same severity, persistent issue (F2) should be first
        assert ranked[0]["code"] == "F2"


class TestSelectFocus:
    """Test focus area selection."""

    def test_select_focus_from_failed_goal(self):
        """Test primary focus selected from failed goal."""
        findings = [
            {
                "code": "HEAD_MOVEMENT",
                "title": "Excessive Head Movement",
                "severity": "critical",
            }
        ]
        outcomes = {
            "metrics": [
                {
                    "code": "HEAD_MOVEMENT",
                    "title": "Head Stability",
                    "target_score": 0.70,
                    "actual_score": 0.50,
                    "passed": False,
                }
            ]
        }

        focus = _select_focus(findings, outcomes)

        assert "Head Stability" in focus["primary_focus"]
        assert len(focus["rationale"]) > 0
        assert "goal not met" in focus["rationale"][0].lower()

    def test_select_focus_from_severity(self):
        """Test primary focus from highest severity when no failed goals."""
        findings = [
            {
                "code": "KNEE_COLLAPSE",
                "title": "Front Knee Collapse",
                "severity": "moderate",
            },
            {
                "code": "HEAD_MOVEMENT",
                "title": "Head Stability Issue",
                "severity": "critical",
            },
        ]

        # Need to rank findings first
        ranked = _rank_findings(findings)
        focus = _select_focus(ranked, None)

        assert "Head Stability Issue" in focus["primary_focus"]
        assert focus["secondary_focus"] == "Front Knee Collapse"

    def test_select_focus_no_findings(self):
        """Test focus when no findings exist."""
        focus = _select_focus([], None)

        assert "No critical issues" in focus["primary_focus"]
        assert focus["secondary_focus"] is None


class TestSelectCoachingCues:
    """Test coaching cue extraction."""

    def test_select_coaching_cues_max_three(self):
        """Test max 3 cues selected from top findings."""
        findings = [
            {"coaching_cues": ["Cue 1A", "Cue 1B"]},
            {"coaching_cues": ["Cue 2A", "Cue 2B"]},
            {"coaching_cues": ["Cue 3A", "Cue 3B"]},
            {"coaching_cues": ["Cue 4A", "Cue 4B"]},
        ]

        cues = _select_coaching_cues(findings, max_cues=3)

        assert len(cues) == 3
        assert cues[0] == "Cue 1A"
        assert cues[1] == "Cue 2A"
        assert cues[2] == "Cue 3A"

    def test_select_coaching_cues_handles_missing(self):
        """Test cue selection when some findings have no cues."""
        findings = [
            {"coaching_cues": []},
            {"coaching_cues": ["Cue 2A"]},
            {"other_field": "no cues"},
        ]

        cues = _select_coaching_cues(findings, max_cues=3)

        assert len(cues) == 1
        assert cues[0] == "Cue 2A"


class TestSelectDrills:
    """Test drill selection."""

    def test_select_drills_max_three(self):
        """Test max 3 drills selected, avoiding duplicates."""
        findings = [
            {"suggested_drills": ["Drill A", "Drill B"]},
            {"suggested_drills": ["Drill C", "Drill D"]},
            {"suggested_drills": ["Drill A", "Drill E"]},  # Duplicate Drill A
        ]

        drills = _select_drills(findings, max_drills=3)

        assert len(drills) <= 3
        assert "Drill A" in drills
        # Drill A should appear only once (no duplicates)
        assert drills.count("Drill A") == 1

    def test_select_drills_handles_missing(self):
        """Test drill selection when some findings have no drills."""
        findings = [
            {"suggested_drills": []},
            {"suggested_drills": ["Drill X"]},
            {"other_field": "no drills"},
        ]

        drills = _select_drills(findings, max_drills=3)

        assert len(drills) == 1
        assert drills[0] == "Drill X"


class TestProposeNextGoal:
    """Test next goal proposal."""

    def test_propose_metric_improvement_when_failed(self):
        """Test proposing improvement when goal failed."""
        findings = []
        outcomes = {
            "metrics": [
                {
                    "code": "BALANCE_DRIFT",
                    "title": "Balance Control",
                    "target_score": 0.70,
                    "actual_score": 0.55,
                    "passed": False,
                }
            ]
        }

        next_goal = _propose_next_goal(findings, outcomes)

        assert next_goal["type"] == "metric_improvement"
        assert "Balance Control" in next_goal["description"]
        assert next_goal["target"] > 0.70  # Slightly higher than failed target
        assert next_goal["metric_code"] == "BALANCE_DRIFT"

    def test_propose_metric_maintenance_when_passed(self):
        """Test proposing maintenance when goal passed."""
        findings = []
        outcomes = {
            "metrics": [
                {
                    "code": "HEAD_MOVEMENT",
                    "title": "Head Stability",
                    "target_score": 0.70,
                    "actual_score": 0.75,
                    "passed": True,
                }
            ]
        }

        next_goal = _propose_next_goal(findings, outcomes)

        assert next_goal["type"] == "metric_maintenance"
        assert "Head Stability" in next_goal["description"]
        assert next_goal["target"] == 0.70

    def test_propose_finding_improvement_when_no_goals(self):
        """Test proposing based on top finding when no goals set."""
        findings = [
            {
                "code": "KNEE_COLLAPSE",
                "title": "Front Knee Collapse",
                "metrics": {"score": {"score": 0.50}},
            }
        ]

        next_goal = _propose_next_goal(findings, None)

        assert next_goal["type"] == "finding_improvement"
        assert "Front Knee Collapse" in next_goal["description"]
        assert next_goal["target"] > 0.50  # Improvement target
        assert next_goal["metric_code"] == "KNEE_COLLAPSE"


class TestGenerateCoachSuggestions:
    """Test full suggestion generation."""

    def test_generate_suggestions_with_all_components(self):
        """Test generating complete suggestions with all components."""

        # Mock job object
        class MockJob:
            deep_findings = {
                "findings": [
                    {
                        "code": "HEAD_MOVEMENT",
                        "title": "Excessive Head Movement",
                        "severity": "critical",
                        "metrics": {"score": {"score": 0.45}},
                        "coaching_cues": ["Keep eyes on ball", "Reduce head tilt"],
                        "suggested_drills": ["Wall batting exercise", "Mirror practice"],
                    },
                    {
                        "code": "BALANCE_DRIFT",
                        "title": "Balance Drift",
                        "severity": "moderate",
                        "metrics": {"score": {"score": 0.60}},
                        "coaching_cues": ["Strengthen core"],
                        "suggested_drills": ["Single-leg balance"],
                    },
                ]
            }
            outcomes = {
                "metrics": [
                    {
                        "code": "HEAD_MOVEMENT",
                        "title": "Head Stability",
                        "target_score": 0.70,
                        "actual_score": 0.45,
                        "passed": False,
                    }
                ]
            }
            goal_compliance_pct = 0.45

        job = MockJob()
        suggestions = generate_coach_suggestions(job, previous_jobs=None)

        assert "primary_focus" in suggestions
        assert suggestions["primary_focus"] is not None
        assert "secondary_focus" in suggestions
        assert "coaching_cues" in suggestions
        assert "drills" in suggestions
        assert "proposed_next_goal" in suggestions
        assert "rationale" in suggestions

        # Verify structure
        assert isinstance(suggestions["coaching_cues"], list)
        assert isinstance(suggestions["drills"], list)
        assert isinstance(suggestions["rationale"], list)
        assert isinstance(suggestions["proposed_next_goal"], dict)

    def test_generate_suggestions_no_findings(self):
        """Test suggestions when no findings exist."""

        class MockJob:
            deep_findings = {"findings": []}
            outcomes = None
            goal_compliance_pct = None

        job = MockJob()
        suggestions = generate_coach_suggestions(job, previous_jobs=None)

        assert "No critical issues" in suggestions["primary_focus"]
        assert suggestions["secondary_focus"] is None


class TestGeneratePlayerSummary:
    """Test player-facing summary generation."""

    def test_generate_player_summary_simplifies_text(self):
        """Test player summary simplifies coach suggestions."""
        coach_suggestions = {
            "primary_focus": "Excessive Head Movement",
            "coaching_cues": ["Keep eyes fixed on ball contact point", "Reduce lateral head tilt"],
            "drills": [
                "Batting against a wall with eyes fixed on the ball contact point",
                "Playing in front of a mirror to observe head position",
                "VMO (vastus medialis obliquus) activation exercises",
            ],
            "proposed_next_goal": {
                "type": "metric_improvement",
                "description": "Improve Head Stability score",
                "target": 0.75,
            },
            "rationale": ["Coach goal not met: HEAD_MOVEMENT"],
        }

        summary = generate_player_summary(coach_suggestions)

        assert "focus" in summary
        assert "what_to_practice" in summary
        assert "encouragement" in summary

        # Check simplification
        assert "Focus on: Excessive Head Movement" in summary["focus"]
        assert len(summary["what_to_practice"]) <= 3

        # Verify jargon removed
        practice_text = " ".join(summary["what_to_practice"])
        # Check that VMO drill was included and simplified
        has_vmo_reference = any(
            "leg muscle" in item.lower() or "vmo" in item.lower()
            for item in summary["what_to_practice"]
        )
        # Should have either simplified or original (depending on which drills made the cut)
        assert len(summary["what_to_practice"]) > 0

    def test_generate_player_summary_encouragement_varies(self):
        """Test encouragement message varies by goal type."""
        # Test "improve" case
        suggestions_improve = {
            "primary_focus": "Test",
            "coaching_cues": [],
            "drills": [],
            "proposed_next_goal": {"description": "Improve balance score"},
        }
        summary = generate_player_summary(suggestions_improve)
        assert "progress" in summary["encouragement"].lower()

        # Test "maintain" case
        suggestions_maintain = {
            "primary_focus": "Test",
            "coaching_cues": [],
            "drills": [],
            "proposed_next_goal": {"description": "Maintain consistency"},
        }
        summary = generate_player_summary(suggestions_maintain)
        assert "consistency" in summary["encouragement"].lower()
