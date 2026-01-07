"""
Tests for Ball Tracking Integration in Analysis Pipeline

Tests ball tracking integration for bowling mode analysis.
"""

import pytest

from backend.services.coach_findings import generate_bowling_findings


@pytest.fixture
def mock_ball_tracking_low_detection():
    """Ball tracking with low detection rate (<40%)."""
    return {
        "trajectory": {
            "total_frames": 100,
            "detected_frames": 30,
            "detection_rate": 30.0,
            "avg_velocity": 150.0,
        },
        "metrics": {
            "trajectory_curve": "straight",
            "swing_deviation": 5.0,
            "release_consistency": 75.0,
        },
    }


@pytest.fixture
def mock_ball_tracking_good_detection():
    """Ball tracking with good detection rate (>60%)."""
    return {
        "trajectory": {
            "total_frames": 100,
            "detected_frames": 85,
            "detection_rate": 85.0,
            "avg_velocity": 250.0,
            "release_point": {"x": 100, "y": 50, "timestamp": 0.5},
            "bounce_point": {"x": 300, "y": 200, "timestamp": 1.2},
        },
        "metrics": {
            "trajectory_curve": "outswing",
            "swing_deviation": 45.0,
            "ball_speed_estimate": 280.0,
            "release_consistency": 92.0,
        },
    }


def test_bowling_findings_low_ball_detection_suppresses_swing_analysis(
    mock_ball_tracking_low_detection,
):
    """Test that low ball detection (<40%) suppresses swing claims."""
    metrics = {
        "metrics": {
            "head_stability_score": {"score": 0.85, "num_frames": 50},
        },
        "ball_tracking": mock_ball_tracking_low_detection,
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }

    result = generate_bowling_findings(metrics)

    findings = result["findings"]
    codes = [f["code"] for f in findings]

    # Should have insufficient ball tracking warning
    assert "INSUFFICIENT_BALL_TRACKING" in codes

    # Should NOT have swing analysis (suppressed due to low detection)
    assert "SWING_ANALYSIS" not in codes

    # Check warning message
    insufficient_finding = next(f for f in findings if f["code"] == "INSUFFICIENT_BALL_TRACKING")
    assert insufficient_finding["severity"] == "medium"
    assert "30.0%" in insufficient_finding["evidence"]["detection_rate"]


def test_bowling_findings_good_ball_detection_includes_swing_analysis(
    mock_ball_tracking_good_detection,
):
    """Test that good ball detection (>60%) includes swing analysis."""
    metrics = {
        "metrics": {
            "head_stability_score": {"score": 0.85, "num_frames": 50},
        },
        "ball_tracking": mock_ball_tracking_good_detection,
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }

    result = generate_bowling_findings(metrics)

    findings = result["findings"]
    codes = [f["code"] for f in findings]

    # Should have swing analysis
    assert "SWING_ANALYSIS" in codes

    # Should NOT have insufficient tracking warning
    assert "INSUFFICIENT_BALL_TRACKING" not in codes

    # Check swing analysis content
    swing_finding = next(f for f in findings if f["code"] == "SWING_ANALYSIS")
    assert swing_finding["evidence"]["trajectory_curve"] == "outswing"
    assert swing_finding["evidence"]["swing_deviation"] == 45.0


def test_bowling_findings_release_consistency_detection():
    """Test release consistency findings generation."""
    metrics = {
        "metrics": {},
        "ball_tracking": {
            "trajectory": {"detection_rate": 80.0},
            "metrics": {
                "release_consistency": 55.0,  # Medium severity (50-70)
                "trajectory_curve": "straight",
            },
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }

    result = generate_bowling_findings(metrics)

    findings = result["findings"]
    codes = [f["code"] for f in findings]

    # Should have release consistency finding
    assert "INCONSISTENT_RELEASE_POINT" in codes

    consistency_finding = next(f for f in findings if f["code"] == "INCONSISTENT_RELEASE_POINT")
    assert consistency_finding["severity"] == "medium"
    assert consistency_finding["evidence"]["release_consistency_score"] == 55.0


def test_bowling_findings_release_consistency_high_severity():
    """Test high severity release consistency (<50%)."""
    metrics = {
        "metrics": {},
        "ball_tracking": {
            "trajectory": {"detection_rate": 75.0},
            "metrics": {
                "release_consistency": 35.0,  # High severity (<50)
                "trajectory_curve": "straight",
            },
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }

    result = generate_bowling_findings(metrics)

    consistency_finding = next(
        f for f in result["findings"] if f["code"] == "INCONSISTENT_RELEASE_POINT"
    )
    assert consistency_finding["severity"] == "high"


def test_bowling_findings_release_consistency_low_severity():
    """Test low severity release consistency (70-85%)."""
    metrics = {
        "metrics": {},
        "ball_tracking": {
            "trajectory": {"detection_rate": 75.0},
            "metrics": {
                "release_consistency": 75.0,  # Low severity (70-85)
                "trajectory_curve": "straight",
            },
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }

    result = generate_bowling_findings(metrics)

    consistency_finding = next(
        f for f in result["findings"] if f["code"] == "INCONSISTENT_RELEASE_POINT"
    )
    assert consistency_finding["severity"] == "low"


def test_bowling_findings_without_ball_tracking():
    """Test that bowling findings work without ball tracking data."""
    metrics = {
        "metrics": {
            "head_stability_score": {"score": 0.85, "num_frames": 50},
            "balance_drift_score": {"score": 0.70, "num_frames": 50},
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }

    # Should not crash, just return pose-based findings
    result = generate_bowling_findings(metrics)

    assert "findings" in result
    assert "overall_level" in result
    # No ball tracking findings
    codes = [f["code"] for f in result["findings"]]
    assert "INSUFFICIENT_BALL_TRACKING" not in codes
    assert "SWING_ANALYSIS" not in codes


def test_bowling_findings_ball_tracking_error():
    """Test that ball tracking errors don't crash findings generation."""
    metrics = {
        "metrics": {
            "head_stability_score": {"score": 0.85, "num_frames": 50},
        },
        "ball_tracking": {
            "error": "OpenCV not available",
            "detection_rate": 0,
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }

    # Should not crash, should skip ball tracking findings
    result = generate_bowling_findings(metrics)

    codes = [f["code"] for f in result["findings"]]
    assert "INSUFFICIENT_BALL_TRACKING" not in codes
    assert "SWING_ANALYSIS" not in codes


def test_bowling_findings_swing_types():
    """Test different swing trajectory classifications."""
    for curve_type in ["straight", "inswing", "outswing", "swing"]:
        metrics = {
            "metrics": {},
            "ball_tracking": {
                "trajectory": {"detection_rate": 85.0},
                "metrics": {
                    "trajectory_curve": curve_type,
                    "swing_deviation": 45.0,
                    "ball_speed_estimate": 280.0,
                    "release_consistency": 92.0,
                },
            },
            "summary": {"total_frames": 100, "frames_with_pose": 90},
        }

        result = generate_bowling_findings(metrics)
        swing_finding = next(f for f in result["findings"] if f["code"] == "SWING_ANALYSIS")
        assert swing_finding["evidence"]["trajectory_curve"] == curve_type


def test_bowling_findings_ball_tracking_at_threshold():
    """Test ball tracking at exactly 40% threshold."""
    metrics = {
        "metrics": {},
        "ball_tracking": {
            "trajectory": {"detection_rate": 40.0},  # Exactly at threshold
            "metrics": {
                "trajectory_curve": "straight",
                "release_consistency": 90.0,
            },
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }

    result = generate_bowling_findings(metrics)
    codes = [f["code"] for f in result["findings"]]

    # At 40%, should still suppress (need >= 40 to pass, < 40 to suppress)
    # But 40.0 is NOT < 40, so should pass
    assert "INSUFFICIENT_BALL_TRACKING" not in codes


def test_bowling_findings_ball_tracking_just_below_threshold():
    """Test ball tracking just below 40% threshold."""
    metrics = {
        "metrics": {},
        "ball_tracking": {
            "trajectory": {"detection_rate": 39.9},  # Just below threshold
            "metrics": {
                "trajectory_curve": "straight",
                "release_consistency": 90.0,
            },
        },
        "summary": {"total_frames": 100, "frames_with_pose": 90},
    }

    result = generate_bowling_findings(metrics)
    codes = [f["code"] for f in result["findings"]]

    # Should trigger insufficient tracking
    assert "INSUFFICIENT_BALL_TRACKING" in codes
    assert "SWING_ANALYSIS" not in codes
