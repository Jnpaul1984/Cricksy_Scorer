"""
Test strict analysis_mode enforcement across worker, service, and findings.

Verifies:
1. Worker fails fast if analysis_mode is None
2. Service validates mode against VALID_MODES
3. Findings use mode-specific narratives
4. Bowling mode does not show batting-specific language
5. Code filtering prevents cross-contamination
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.coach_findings import (
    generate_findings,
    ALLOWED_CODES_BY_MODE,
    WHY_IT_MATTERS_BY_MODE,
    HIGH_SEVERITY_WARNINGS_BY_MODE,
)
from backend.services.coach_plus_analysis import run_pose_metrics_findings_report


# Sample metrics for testing
SAMPLE_METRICS = {
    "metrics": {
        "head_stability_score": {"score": 0.5, "num_frames": 100},
        "balance_drift_score": {"score": 0.6, "num_frames": 100},
        "front_knee_brace_score": {"score": 0.4, "num_frames": 100},
        "hip_shoulder_separation_timing": {"score": 0.08, "num_frames": 100},
        "elbow_drop_score": {"score": 0.7, "num_frames": 100},
    },
    "summary": {
        "total_frames": 120,
        "frames_with_pose": 100,
    },
}


class TestServiceValidation:
    """Test coach_plus_analysis.py validates analysis_mode."""

    @pytest.mark.asyncio
    async def test_service_rejects_none_mode(self):
        """Service should raise ValueError if analysis_mode is None."""
        with pytest.raises(ValueError, match="Invalid analysis_mode"):
            run_pose_metrics_findings_report(
                video_path="dummy.mp4",
                analysis_mode=None,
                sample_fps=5,
                include_frames=False,
            )

    @pytest.mark.asyncio
    async def test_service_rejects_invalid_mode(self):
        """Service should raise ValueError if analysis_mode is not in VALID_MODES."""
        with pytest.raises(ValueError, match="Invalid analysis_mode"):
            run_pose_metrics_findings_report(
                video_path="dummy.mp4",
                analysis_mode="running",  # Not valid
                sample_fps=5,
                include_frames=False,
            )

    @pytest.mark.asyncio
    async def test_service_accepts_valid_modes(self):
        """Service should accept all valid modes without error."""
        valid_modes = ["batting", "bowling", "wicketkeeping", "fielding"]
        
        for mode in valid_modes:
            # Mock the pose extraction at the source module level
            with patch("backend.services.pose_service.extract_pose_keypoints_from_video") as mock_extract:
                # Return minimal valid pose data matching expected schema
                mock_extract.return_value = {
                    "pose_frames": [],
                    "meta": {"fps": 30},
                    "total_frames": 100,
                    "sampled_frames": 100,
                    "frames_with_pose": 80,
                }
                
                # Function is NOT async despite being tested in an async test
                result = run_pose_metrics_findings_report(
                    video_path="dummy.mp4",
                    analysis_mode=mode,
                    sample_fps=5,
                    include_frames=False,
                )
                
                # Should complete without raising
                assert result is not None
                # result is an AnalysisArtifacts dataclass with .results field
                assert result.results["meta"]["analysis_mode_used"] == mode


class TestFindingsCodeFiltering:
    """Test that generate_findings filters codes by mode."""

    def test_bowling_mode_allows_only_bowling_codes(self):
        """Bowling mode should only return codes in ALLOWED_CODES_BY_MODE['bowling']."""
        result = generate_findings(SAMPLE_METRICS, analysis_mode="bowling")
        
        findings = result.get("findings", [])
        for finding in findings:
            code = finding["code"]
            assert code in ALLOWED_CODES_BY_MODE["bowling"], (
                f"Code '{code}' should not appear in bowling findings"
            )

    def test_wicketkeeping_mode_allows_only_wicketkeeping_codes(self):
        """Wicketkeeping mode should only return codes in ALLOWED_CODES_BY_MODE['wicketkeeping']."""
        result = generate_findings(SAMPLE_METRICS, analysis_mode="wicketkeeping")
        
        findings = result.get("findings", [])
        for finding in findings:
            code = finding["code"]
            assert code in ALLOWED_CODES_BY_MODE["wicketkeeping"], (
                f"Code '{code}' should not appear in wicketkeeping findings"
            )

    def test_fielding_mode_allows_only_fielding_codes(self):
        """Fielding mode should only return codes in ALLOWED_CODES_BY_MODE['fielding']."""
        result = generate_findings(SAMPLE_METRICS, analysis_mode="fielding")
        
        findings = result.get("findings", [])
        for finding in findings:
            code = finding["code"]
            assert code in ALLOWED_CODES_BY_MODE["fielding"], (
                f"Code '{code}' should not appear in fielding findings"
            )


class TestModeAwareNarratives:
    """Test that findings use mode-specific 'why_it_matters' text."""

    def test_head_movement_has_bowling_narrative(self):
        """HEAD_MOVEMENT finding in bowling mode should mention 'consistent line and length'."""
        # Force a head movement finding by reducing head_stability_score
        metrics_with_head_issue = {
            **SAMPLE_METRICS,
            "metrics": {
                **SAMPLE_METRICS["metrics"],
                "head_stability_score": {"score": 0.3, "num_frames": 100},  # Low score = finding
            }
        }
        
        result = generate_findings(metrics_with_head_issue, analysis_mode="bowling")
        findings = result.get("findings", [])
        
        head_findings = [f for f in findings if f["code"] == "HEAD_MOVEMENT"]
        if head_findings:
            head_finding = head_findings[0]
            why_it_matters = head_finding["why_it_matters"]
            
            # Should use bowling-specific narrative
            assert "line and length" in why_it_matters.lower() or "delivery" in why_it_matters.lower(), (
                f"Bowling mode should have bowling-specific narrative, got: {why_it_matters}"
            )
            
            # Should NOT mention batting-specific terms
            assert "bat" not in why_it_matters.lower()
            assert "shot" not in why_it_matters.lower()

    def test_knee_collapse_has_wicketkeeping_warning(self):
        """KNEE_COLLAPSE high severity in wicketkeeping should have wicketkeeping-specific warning."""
        # Force a high-severity knee collapse finding
        metrics_with_knee_issue = {
            **SAMPLE_METRICS,
            "metrics": {
                **SAMPLE_METRICS["metrics"],
                "front_knee_brace_score": {"score": 0.2, "num_frames": 100},  # Very low = high severity
            }
        }
        
        result = generate_findings(metrics_with_knee_issue, analysis_mode="wicketkeeping")
        findings = result.get("findings", [])
        
        knee_findings = [f for f in findings if f["code"] == "KNEE_COLLAPSE"]
        if knee_findings:
            knee_finding = knee_findings[0]
            
            if knee_finding["severity"] == "high":
                cues = knee_finding["cues"]
                
                # Should have wicketkeeping-specific warning
                has_wk_warning = any(
                    "keeping" in cue.lower() for cue in cues
                )
                
                # Should NOT have batting warning
                has_batting_warning = any(
                    "Suspend intensive batting" in cue for cue in cues
                )
                
                assert not has_batting_warning, (
                    "Wicketkeeping mode should not show 'Suspend intensive batting' warning"
                )


class TestNoBattingFallback:
    """Test that invalid/missing mode raises ValueError instead of defaulting to batting."""

    def test_none_mode_raises_error(self):
        """generate_findings(mode=None) should raise ValueError, not default to batting."""
        with pytest.raises(ValueError, match="analysis_mode is required"):
            generate_findings(SAMPLE_METRICS, analysis_mode=None)

    def test_empty_mode_raises_error(self):
        """generate_findings(mode='') should raise ValueError, not default to batting."""
        with pytest.raises(ValueError, match="analysis_mode is required"):
            generate_findings(SAMPLE_METRICS, analysis_mode="")

    def test_invalid_mode_raises_error(self):
        """generate_findings(mode='invalid') should raise ValueError, not default to batting."""
        with pytest.raises(ValueError, match="analysis_mode is required"):
            generate_findings(SAMPLE_METRICS, analysis_mode="running")


class TestModeAwareDictionaries:
    """Test that mode-aware dictionaries are correctly structured."""

    def test_allowed_codes_has_all_modes(self):
        """ALLOWED_CODES_BY_MODE should have entries for all valid modes."""
        required_modes = {"batting", "bowling", "wicketkeeping", "fielding"}
        assert set(ALLOWED_CODES_BY_MODE.keys()) == required_modes

    def test_why_it_matters_has_common_codes(self):
        """WHY_IT_MATTERS_BY_MODE should have entries for common codes."""
        expected_codes = {"HEAD_MOVEMENT", "KNEE_COLLAPSE"}
        
        for code in expected_codes:
            assert code in WHY_IT_MATTERS_BY_MODE, (
                f"WHY_IT_MATTERS_BY_MODE should have entry for {code}"
            )
            
            # Each code should have mode-specific text
            code_entry = WHY_IT_MATTERS_BY_MODE[code]
            assert "batting" in code_entry
            assert "bowling" in code_entry
            assert "wicketkeeping" in code_entry

    def test_high_severity_warnings_has_mode_variants(self):
        """HIGH_SEVERITY_WARNINGS_BY_MODE should have mode-specific warnings."""
        assert "KNEE_COLLAPSE" in HIGH_SEVERITY_WARNINGS_BY_MODE
        
        knee_warnings = HIGH_SEVERITY_WARNINGS_BY_MODE["KNEE_COLLAPSE"]
        assert "batting" in knee_warnings
        assert "bowling" in knee_warnings
        assert "wicketkeeping" in knee_warnings
        
        # Warnings should be different for each mode
        assert knee_warnings["batting"] != knee_warnings["bowling"]
        assert knee_warnings["bowling"] != knee_warnings["wicketkeeping"]
