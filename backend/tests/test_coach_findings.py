"""
Unit tests for rule-based coaching findings generator.

Tests verify:
1. Findings are generated correctly based on metric thresholds
2. Severity is classified appropriately
3. Evidence and context are included
4. Overall performance level is calculated correctly
"""

from __future__ import annotations

import pytest
from typing import Any

from backend.services.coach_findings import (
    DRILL_SUGGESTIONS,
    FINDING_DEFINITIONS,
    THRESHOLDS,
    _check_balance_drift,
    _check_elbow_drop,
    _check_head_movement,
    _check_knee_collapse,
    _check_rotation_timing,
    _get_overall_level,
    _get_severity,
    generate_findings,
)

# ============================================================================
# Test Utility Functions
# ============================================================================


class TestSeverityClassification:
    """Test severity calculation from scores."""

    def test_get_severity_high_score_low_severity(self) -> None:
        """High scores (above threshold) should yield low severity."""
        severity = _get_severity(0.85, threshold=0.60, is_higher_better=True)
        assert severity == "low"

    def test_get_severity_medium_score_medium_severity(self) -> None:
        """Medium scores (between threshold and threshold-0.15) yield medium severity."""
        severity = _get_severity(0.50, threshold=0.60, is_higher_better=True)
        assert severity == "medium"

    def test_get_severity_low_score_high_severity(self) -> None:
        """Low scores (far below threshold) should yield high severity."""
        severity = _get_severity(0.35, threshold=0.60, is_higher_better=True)
        assert severity == "high"

    def test_get_severity_at_threshold(self) -> None:
        """Scores at threshold should yield low severity."""
        severity = _get_severity(0.60, threshold=0.60, is_higher_better=True)
        assert severity == "low"


class TestOverallLevel:
    """Test overall performance level calculation."""

    def test_overall_level_no_findings(self) -> None:
        """No findings should yield high overall level."""
        level = _get_overall_level([])
        assert level == "high"

    def test_overall_level_all_low_severity(self) -> None:
        """All low severity findings should yield high overall level."""
        findings = [
            {"severity": "low"},
            {"severity": "low"},
            {"severity": "low"},
        ]
        level = _get_overall_level(findings)
        assert level == "high"

    def test_overall_level_all_medium_severity(self) -> None:
        """All medium severity findings should yield medium overall level."""
        findings = [
            {"severity": "medium"},
            {"severity": "medium"},
        ]
        level = _get_overall_level(findings)
        assert level == "medium"

    def test_overall_level_all_high_severity(self) -> None:
        """All high severity findings should yield low overall level."""
        findings = [
            {"severity": "high"},
            {"severity": "high"},
        ]
        level = _get_overall_level(findings)
        assert level == "low"

    def test_overall_level_mixed_severity(self) -> None:
        """Mixed severity findings should yield medium overall level."""
        findings = [
            {"severity": "low"},
            {"severity": "medium"},
            {"severity": "high"},
        ]
        level = _get_overall_level(findings)
        assert level == "medium"


# ============================================================================
# Test Individual Finding Checks
# ============================================================================


class TestHeadMovementFinding:
    """Test head movement finding generation."""

    def test_head_stable_no_finding(self) -> None:
        """High head stability should not generate finding."""
        metrics = {
            "head_stability_score": {"score": 0.85, "num_frames": 100},
        }

        finding = _check_head_movement(metrics)
        assert finding is None

    def test_head_unstable_low_severity(self) -> None:
        """Slightly low head stability should generate low severity finding."""
        metrics = {
            "head_stability_score": {"score": 0.55, "num_frames": 100},
        }

        finding = _check_head_movement(metrics)
        assert finding is not None
        assert finding["code"] == "HEAD_MOVEMENT"
        assert finding["severity"] == "low"
        assert "cues" in finding
        assert "suggested_drills" in finding

    def test_head_unstable_high_severity(self) -> None:
        """Very low head stability should generate high severity finding."""
        metrics = {
            "head_stability_score": {"score": 0.35, "num_frames": 100},
        }

        finding = _check_head_movement(metrics)
        assert finding is not None
        assert finding["severity"] == "high"

    def test_head_missing_data(self) -> None:
        """Missing head stability data should return None."""
        metrics: dict[str, Any] = {}

        finding = _check_head_movement(metrics)
        assert finding is None


class TestBalanceDriftFinding:
    """Test balance drift finding generation."""

    def test_balance_good_no_finding(self) -> None:
        """Good balance should not generate finding."""
        metrics = {
            "balance_drift_score": {"score": 0.75, "num_frames": 100},
        }

        finding = _check_balance_drift(metrics)
        assert finding is None

    def test_balance_poor_finding_generated(self) -> None:
        """Poor balance should generate finding."""
        metrics = {
            "balance_drift_score": {"score": 0.40, "num_frames": 100},
        }

        finding = _check_balance_drift(metrics)
        assert finding is not None
        assert finding["code"] == "BALANCE_DRIFT"
        assert "evidence" in finding
        assert "why_it_matters" in finding


class TestKneeCollapseFinding:
    """Test knee collapse finding generation."""

    def test_knee_braced_no_finding(self) -> None:
        """Good knee brace should not generate finding."""
        metrics = {
            "front_knee_brace_score": {"score": 0.80, "num_frames": 100},
        }

        finding = _check_knee_collapse(metrics)
        assert finding is None

    def test_knee_collapse_medium_severity(self) -> None:
        """Medium knee collapse should generate medium severity finding."""
        metrics = {
            "front_knee_brace_score": {"score": 0.42, "num_frames": 100},
        }

        finding = _check_knee_collapse(metrics)
        assert finding is not None
        assert finding["code"] == "KNEE_COLLAPSE"
        assert finding["severity"] == "medium"

    def test_knee_collapse_drills_present(self) -> None:
        """Finding should include suggested drills."""
        metrics = {
            "front_knee_brace_score": {"score": 0.30, "num_frames": 100},
        }

        finding = _check_knee_collapse(metrics)
        assert finding is not None
        assert len(finding["suggested_drills"]) > 0


class TestRotationTimingFinding:
    """Test hip-shoulder rotation timing finding."""

    def test_rotation_timing_good_no_finding(self) -> None:
        """Good rotation timing should not generate finding."""
        metrics = {
            "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},
        }

        finding = _check_rotation_timing(metrics)
        assert finding is None

    def test_rotation_timing_slightly_off_low_severity(self) -> None:
        """Slightly off timing should generate low severity finding."""
        metrics = {
            "hip_shoulder_separation_timing": {"score": 0.16, "num_frames": 100},  # 0.04s off
        }

        finding = _check_rotation_timing(metrics)
        assert finding is not None
        assert finding["code"] == "ROTATION_TIMING"
        assert finding["severity"] == "low"

    def test_rotation_timing_way_off_high_severity(self) -> None:
        """Way off timing should generate high severity finding."""
        metrics = {
            "hip_shoulder_separation_timing": {"score": 0.30, "num_frames": 100},  # 0.18s off
        }

        finding = _check_rotation_timing(metrics)
        assert finding is not None
        assert finding["severity"] == "high"

    def test_rotation_timing_negative_lag(self) -> None:
        """Negative lag (shoulder before hip) should trigger finding."""
        metrics = {
            "hip_shoulder_separation_timing": {"score": -0.05, "num_frames": 100},  # Shoulder first
        }

        finding = _check_rotation_timing(metrics)
        assert finding is not None


class TestElbowDropFinding:
    """Test elbow drop finding generation."""

    def test_elbow_drop_good_no_finding(self) -> None:
        """Good elbow drop should not generate finding."""
        metrics = {
            "elbow_drop_score": {"score": 0.75, "num_frames": 100},
        }

        finding = _check_elbow_drop(metrics)
        assert finding is None

    def test_elbow_high_finding_generated(self) -> None:
        """High elbows should generate finding."""
        metrics = {
            "elbow_drop_score": {"score": 0.35, "num_frames": 100},
        }

        finding = _check_elbow_drop(metrics)
        assert finding is not None
        assert finding["code"] == "ELBOW_DROP"


# ============================================================================
# Test Main API
# ============================================================================


class TestGenerateFindings:
    """Test main findings generation API."""

    def test_generate_findings_perfect_technique(self) -> None:
        """Perfect metrics should generate no findings."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.95, "num_frames": 100},
                "balance_drift_score": {"score": 0.90, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.92, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},
                "elbow_drop_score": {"score": 0.88, "num_frames": 100},
            }
        }

        result = generate_findings(metrics)

        assert result["overall_level"] == "high"
        assert len(result["findings"]) == 0

    def test_generate_findings_multiple_issues(self) -> None:
        """Multiple metric issues should generate multiple findings."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.45, "num_frames": 100},  # Issue
                "balance_drift_score": {"score": 0.40, "num_frames": 100},  # Issue
                "front_knee_brace_score": {"score": 0.35, "num_frames": 100},  # Issue
                "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},
                "elbow_drop_score": {"score": 0.88, "num_frames": 100},
            }
        }

        result = generate_findings(metrics)

        assert len(result["findings"]) == 3
        assert result["overall_level"] == "low"

    def test_generate_findings_structure(self) -> None:
        """Generated findings should have required structure."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.50, "num_frames": 100},
                "balance_drift_score": {"score": 0.90, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.90, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},
                "elbow_drop_score": {"score": 0.90, "num_frames": 100},
            }
        }

        result = generate_findings(metrics)

        assert "overall_level" in result
        assert "findings" in result
        assert result["overall_level"] in ["low", "medium", "high"]

        if result["findings"]:
            finding = result["findings"][0]
            assert "code" in finding
            assert "title" in finding
            assert "severity" in finding
            assert "evidence" in finding
            assert "why_it_matters" in finding
            assert "cues" in finding
            assert "suggested_drills" in finding

    def test_generate_findings_with_context(self) -> None:
        """Context should be echoed back in response."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.90, "num_frames": 100},
                "balance_drift_score": {"score": 0.90, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.90, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},
                "elbow_drop_score": {"score": 0.90, "num_frames": 100},
            }
        }
        context = {"player_id": 42, "session_type": "net_session"}

        result = generate_findings(metrics, context)

        assert "context" in result
        assert result["context"] == context

    def test_generate_findings_with_analysis_context_batting(self) -> None:
        """Analysis context should customize finding titles for batting."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.50, "num_frames": 100},  # Trigger finding
                "balance_drift_score": {"score": 0.90, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.90, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},
                "elbow_drop_score": {"score": 0.90, "num_frames": 100},
            }
        }
        context = {"analysis_context": "batting"}

        result = generate_findings(metrics, context)

        assert "findings" in result
        assert len(result["findings"]) > 0
        head_finding = next((f for f in result["findings"] if f["code"] == "HEAD_MOVEMENT"), None)
        assert head_finding is not None
        assert "batting" in head_finding["title"].lower()

    def test_generate_findings_with_analysis_context_bowling(self) -> None:
        """Analysis context should customize finding titles for bowling."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.50, "num_frames": 100},  # Trigger finding
                "balance_drift_score": {"score": 0.90, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.90, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},
                "elbow_drop_score": {"score": 0.90, "num_frames": 100},
            }
        }
        context = {"analysis_context": "bowling"}

        result = generate_findings(metrics, context)

        assert "findings" in result
        assert len(result["findings"]) > 0
        head_finding = next((f for f in result["findings"] if f["code"] == "HEAD_MOVEMENT"), None)
        assert head_finding is not None
        assert "bowling" in head_finding["title"].lower()

    def test_generate_findings_single_issue_low_severity(self) -> None:
        """Single low severity issue should yield medium overall level."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.55, "num_frames": 100},  # Low severity
                "balance_drift_score": {"score": 0.90, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.90, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},
                "elbow_drop_score": {"score": 0.90, "num_frames": 100},
            }
        }

        result = generate_findings(metrics)

        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "low"

    def test_generate_findings_single_issue_high_severity(self) -> None:
        """Single high severity issue should yield low overall level."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.30, "num_frames": 100},  # High severity
                "balance_drift_score": {"score": 0.90, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.90, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},
                "elbow_drop_score": {"score": 0.90, "num_frames": 100},
            }
        }

        result = generate_findings(metrics)

        assert len(result["findings"]) == 1
        assert result["findings"][0]["severity"] == "high"
        assert result["overall_level"] == "low"


# ============================================================================
# Integration Tests (Realistic Scenarios)
# ============================================================================


class TestFindingsIntegration:
    """Integration tests with realistic metric scenarios."""

    def test_findings_batting_stroke_good_technique(self) -> None:
        """Good technique scenario should produce minimal findings."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.82, "num_frames": 100},
                "balance_drift_score": {"score": 0.78, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.85, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.115, "num_frames": 100},
                "elbow_drop_score": {"score": 0.72, "num_frames": 100},
            }
        }

        result = generate_findings(metrics)

        assert result["overall_level"] == "high"
        assert len(result["findings"]) == 0

    def test_findings_batting_stroke_poor_technique(self) -> None:
        """Poor technique scenario should produce multiple findings."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.35, "num_frames": 100},
                "balance_drift_score": {"score": 0.40, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.30, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.28, "num_frames": 100},
                "elbow_drop_score": {"score": 0.25, "num_frames": 100},
            }
        }

        result = generate_findings(metrics)

        assert result["overall_level"] == "low"
        assert len(result["findings"]) == 5
        assert all(f["severity"] == "high" for f in result["findings"])

    def test_findings_mixed_technique(self) -> None:
        """Mixed technique (some good, some poor) should produce balanced findings."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.65, "num_frames": 100},  # Good
                "balance_drift_score": {"score": 0.45, "num_frames": 100},  # Poor
                "front_knee_brace_score": {"score": 0.48, "num_frames": 100},  # Poor
                "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},  # Good
                "elbow_drop_score": {"score": 0.80, "num_frames": 100},  # Good
            }
        }

        result = generate_findings(metrics)

        assert result["overall_level"] == "medium"
        assert len(result["findings"]) == 2

    def test_findings_all_evidence_included(self) -> None:
        """Evidence should include actual metric values."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.42, "num_frames": 100},
                "balance_drift_score": {"score": 0.90, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.90, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},
                "elbow_drop_score": {"score": 0.90, "num_frames": 100},
            }
        }

        result = generate_findings(metrics)

        finding = result["findings"][0]
        assert "evidence" in finding
        assert finding["evidence"]["head_stability_score"] == 0.42
        assert "threshold" in finding["evidence"]

    def test_findings_drills_available(self) -> None:
        """All findings should have suggested drills."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.50, "num_frames": 100},
                "balance_drift_score": {"score": 0.50, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.40, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.28, "num_frames": 100},
                "elbow_drop_score": {"score": 0.50, "num_frames": 100},
            }
        }

        result = generate_findings(metrics)

        for finding in result["findings"]:
            assert "suggested_drills" in finding
            assert isinstance(finding["suggested_drills"], list)
            assert len(finding["suggested_drills"]) > 0

    def test_findings_cues_relevant_to_severity(self) -> None:
        """Cues should match the severity level."""
        metrics = {
            "metrics": {
                "head_stability_score": {"score": 0.50, "num_frames": 100},  # Medium severity
                "balance_drift_score": {"score": 0.90, "num_frames": 100},
                "front_knee_brace_score": {"score": 0.90, "num_frames": 100},
                "hip_shoulder_separation_timing": {"score": 0.12, "num_frames": 100},
                "elbow_drop_score": {"score": 0.90, "num_frames": 100},
            }
        }

        result = generate_findings(metrics)

        finding = result["findings"][0]
        assert finding["severity"] == "medium"
        assert "cues" in finding
        assert len(finding["cues"]) > 0


# ============================================================================
# Constants Validation
# ============================================================================


class TestConstants:
    """Verify constants are properly defined."""

    def test_thresholds_defined(self) -> None:
        """All expected thresholds should be defined."""
        required_thresholds = [
            "head_stability_score",
            "balance_drift_score",
            "front_knee_brace_score",
            "hip_shoulder_separation_timing",
            "elbow_drop_score",
        ]

        for threshold in required_thresholds:
            assert threshold in THRESHOLDS

    def test_drill_suggestions_complete(self) -> None:
        """All finding codes should have drill suggestions."""
        required_codes = [
            "HEAD_MOVEMENT",
            "BALANCE_DRIFT",
            "KNEE_COLLAPSE",
            "ROTATION_TIMING",
            "ELBOW_DROP",
        ]

        for code in required_codes:
            assert code in DRILL_SUGGESTIONS
            assert isinstance(DRILL_SUGGESTIONS[code], list)
            assert len(DRILL_SUGGESTIONS[code]) > 0

    def test_finding_definitions_complete(self) -> None:
        """All finding definitions should be complete."""
        required_codes = [
            "HEAD_MOVEMENT",
            "BALANCE_DRIFT",
            "KNEE_COLLAPSE",
            "ROTATION_TIMING",
            "ELBOW_DROP",
        ]

        for code in required_codes:
            assert code in FINDING_DEFINITIONS
            definition = FINDING_DEFINITIONS[code]
            assert "title" in definition
            assert "why_it_matters" in definition
            assert "low_severity" in definition
            assert "medium_severity" in definition
            assert "high_severity" in definition


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
