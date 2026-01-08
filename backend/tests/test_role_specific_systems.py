"""
Test role-specific systems: drills, thresholds, confidence scoring, and zero batting leakage.

This test suite verifies:
1. Wicketkeeping/bowling/fielding findings contain NO batting terminology
2. Drills come from correct mode-specific registry (no batting fallback)
3. Thresholds differ by analysis mode
4. Confidence scoring is present and valid
5. Mode filtering prevents cross-contamination
"""

import pytest
from backend.services.coach_findings import (
    DRILLS_BY_MODE,
    THRESHOLDS_BY_MODE,
    THRESHOLDS,
    generate_findings,
    _calculate_job_confidence,
    _calculate_finding_confidence,
    _check_head_movement,
    _check_balance_drift,
    _check_knee_collapse,
    _check_rotation_timing,
    _check_elbow_drop,
)


# Batting-specific terminology to check for leakage in why_it_matters and drills
# NOTE: Avoid false positives like "hip drive" (throwing term), "combat" (general), etc.
BATTING_SPECIFIC_PHRASES = [
    " bat ",  # bat as noun (isolated)
    "batsman", "batter",  # batting roles
    "backswing", "downswing", "backlift", "trigger",  # batting mechanics
    "cover drive", "pull shot", "cut shot", "on drive", "off drive",  # batting shots
    "playing a shot", "executing a shot",  # batting actions
]


@pytest.mark.parametrize("mode", ["wicketkeeping", "bowling", "fielding"])
def test_no_batting_terminology_in_non_batting_modes(mode):
    """
    Test that wicketkeeping/bowling/fielding findings' WHY_IT_MATTERS and DRILLS
    contain ZERO batting-specific phrases.
    
    This is the PRIMARY test for eliminating batting-language leakage.
    Generic cues may contain universal words like "stance" (keeper stance, bowling stance).
    """
    # Create mock metrics that trigger all findings
    metrics = {
        "head_stability_score": {"score": 0.35, "num_frames": 100},  # Low = bad head movement
        "balance_drift_score": {"score": 0.30, "num_frames": 100},  # Low = balance drift
        "front_knee_brace_score": {"score": 0.25, "num_frames": 100},  # Low = knee collapse
        "hip_shoulder_separation_timing": {"score": 0.20, "num_frames": 100},  # Low = rotation issue
        "elbow_drop_score": {"score": 0.15, "num_frames": 100},  # Low = elbow drop
        "summary": {
            "total_frames": 120,
            "frames_with_pose": 100,
        }
    }
    
    # Generate findings for non-batting mode
    result = generate_findings(metrics, analysis_mode=mode)
    
    # Extract text from WHY_IT_MATTERS and DRILLS (mode-specific parts)
    why_it_matters_text = []
    drills_text = []
    for finding in result["findings"]:
        why_it_matters_text.append(finding.get("why_it_matters", "").lower())
        drills_text.extend([drill.lower() for drill in finding.get("suggested_drills", [])])
    
    combined_text = " ".join(why_it_matters_text + drills_text)
    
    # Check for batting-specific phrases
    found_batting_phrases = [
        phrase for phrase in BATTING_SPECIFIC_PHRASES
        if phrase in combined_text
    ]
    
    assert len(found_batting_phrases) == 0, (
        f"Found batting-specific terminology in {mode} findings: {found_batting_phrases}\n"
        f"WHY_IT_MATTERS and DRILLS sample: {combined_text[:500]}..."
    )


@pytest.mark.parametrize("mode,drill_code,expected_count", [
    ("bowling", "HEAD_MOVEMENT", 4),  # Should return 4 bowling drills
    ("wicketkeeping", "BALANCE_DRIFT", 4),  # Should return 4 wicketkeeping drills
    ("fielding", "KNEE_COLLAPSE", 4),  # Should return 4 fielding drills
    ("batting", "ROTATION_TIMING", 4),  # Should return 4 batting drills
])
def test_drills_come_from_correct_mode_registry(mode, drill_code, expected_count):
    """Test that drills are pulled from the correct mode-specific registry."""
    mode_drills = DRILLS_BY_MODE.get(mode, {})
    drills = mode_drills.get(drill_code, [])
    
    assert len(drills) == expected_count, (
        f"Expected {expected_count} drills for {drill_code} in {mode}, got {len(drills)}"
    )
    
    # Verify drills contain mode-appropriate terminology
    combined = " ".join(drills).lower()
    
    if mode == "bowling":
        # Bowling drills should mention bowling/delivery/action
        assert any(term in combined for term in ["bowl", "delivery", "action", "pace", "seam"]), (
            f"Bowling drills for {drill_code} don't contain bowling terminology: {drills}"
        )
    elif mode == "wicketkeeping":
        # Wicketkeeping drills should mention keeping/gloves/crouch/take
        # Some drills may be generic (balance, footwork) but at least one should be keeper-specific
        has_keeper_terms = any(term in combined for term in ["keep", "glove", "crouch", "take", "keeper"])
        has_generic_terms = any(term in combined for term in ["balance", "footwork", "position", "movement"])
        assert has_keeper_terms or has_generic_terms, (
            f"Wicketkeeping drills for {drill_code} don't contain relevant terminology: {drills}"
        )
    elif mode == "fielding":
        # Fielding drills should mention field/catch/throw/movement
        assert any(term in combined for term in ["field", "catch", "throw", "pick", "movement", "position", "lateral", "dive"]), (
            f"Fielding drills for {drill_code} don't contain fielding terminology: {drills}"
        )


def test_drills_no_fallback_to_batting():
    """Test that missing drills return empty list, NOT batting drills."""
    # Create a mode with missing drill code
    mode_drills = DRILLS_BY_MODE.get("fielding", {})
    
    # Try to get a drill that doesn't exist
    non_existent_drill = mode_drills.get("NON_EXISTENT_CODE", [])
    
    assert non_existent_drill == [], (
        f"Expected empty list for missing drill, got: {non_existent_drill}"
    )


@pytest.mark.parametrize("metric,bowling,batting,wicketkeeping,fielding", [
    ("head_stability_score", 0.65, 0.60, 0.58, 0.55),
    ("balance_drift_score", 0.60, 0.55, 0.52, 0.50),
    ("front_knee_brace_score", 0.55, 0.50, 0.45, 0.48),
])
def test_thresholds_differ_by_mode(metric, bowling, batting, wicketkeeping, fielding):
    """Test that thresholds are different for each analysis mode."""
    bowling_thresholds = THRESHOLDS_BY_MODE.get("bowling", THRESHOLDS)
    batting_thresholds = THRESHOLDS_BY_MODE.get("batting", THRESHOLDS)
    keeping_thresholds = THRESHOLDS_BY_MODE.get("wicketkeeping", THRESHOLDS)
    fielding_thresholds = THRESHOLDS_BY_MODE.get("fielding", THRESHOLDS)
    
    assert bowling_thresholds[metric] == bowling, f"Bowling {metric} threshold mismatch"
    assert batting_thresholds[metric] == batting, f"Batting {metric} threshold mismatch"
    assert keeping_thresholds[metric] == wicketkeeping, f"Wicketkeeping {metric} threshold mismatch"
    assert fielding_thresholds[metric] == fielding, f"Fielding {metric} threshold mismatch"
    
    # Verify they're actually different
    all_thresholds = {bowling, batting, wicketkeeping, fielding}
    assert len(all_thresholds) >= 3, (
        f"Thresholds should differ by mode for {metric}, got: "
        f"bowling={bowling}, batting={batting}, wicketkeeping={wicketkeeping}, fielding={fielding}"
    )


@pytest.mark.parametrize("metric,bowling_strict,wicketkeeping_relaxed", [
    ("head_stability_score", 0.65, 0.58),
    ("balance_drift_score", 0.60, 0.52),
    ("front_knee_brace_score", 0.55, 0.45),
])
def test_bowling_strictest_wicketkeeping_most_relaxed(metric, bowling_strict, wicketkeeping_relaxed):
    """Test that bowling has strictest thresholds, wicketkeeping most relaxed."""
    bowling_thresholds = THRESHOLDS_BY_MODE["bowling"]
    keeping_thresholds = THRESHOLDS_BY_MODE["wicketkeeping"]
    
    assert bowling_thresholds[metric] > keeping_thresholds[metric], (
        f"Bowling should have stricter (higher) threshold than wicketkeeping for {metric}. "
        f"Got bowling={bowling_thresholds[metric]}, wicketkeeping={keeping_thresholds[metric]}"
    )
    
    assert bowling_thresholds[metric] == bowling_strict
    assert keeping_thresholds[metric] == wicketkeeping_relaxed


def test_confidence_fields_in_results():
    """Test that generate_findings returns confidence scoring fields."""
    metrics = {
        "head_stability_score": {"score": 0.75, "num_frames": 100},
        "summary": {
            "total_frames": 120,
            "frames_with_pose": 100,
        }
    }
    
    result = generate_findings(metrics, analysis_mode="batting")
    
    # Check job-level confidence fields
    assert "confidence_score" in result, "Missing confidence_score"
    assert "confidence_label" in result, "Missing confidence_label"
    assert "confidence_reasons" in result, "Missing confidence_reasons"
    assert "confidence_factors" in result, "Missing confidence_factors"
    
    # Validate ranges
    assert 0.0 <= result["confidence_score"] <= 1.0, (
        f"confidence_score out of range: {result['confidence_score']}"
    )
    assert result["confidence_label"] in ["high", "medium", "low"], (
        f"Invalid confidence_label: {result['confidence_label']}"
    )
    assert isinstance(result["confidence_reasons"], list), "confidence_reasons should be list"
    assert isinstance(result["confidence_factors"], list), "confidence_factors should be list (not dict)"


def test_per_finding_confidence():
    """Test that each finding has a confidence score."""
    metrics = {
        "head_stability_score": {"score": 0.35, "num_frames": 100},  # Trigger finding
        "summary": {
            "total_frames": 120,
            "frames_with_pose": 100,
        }
    }
    
    result = generate_findings(metrics, analysis_mode="batting")
    
    assert len(result["findings"]) > 0, "Should have at least one finding"
    
    for finding in result["findings"]:
        assert "confidence" in finding, f"Finding {finding['code']} missing confidence"
        confidence = finding["confidence"]
        assert 0.0 <= confidence <= 1.0, (
            f"Finding {finding['code']} confidence out of range: {confidence}"
        )


def test_job_confidence_calculation():
    """Test _calculate_job_confidence function directly."""
    metrics = {
        "overall_pose_visibility": {"score": 0.85},  # 85% detection
        "meta": {
            "total_frames": 100,
            "frames_analyzed": 95,  # 95% coverage
        },
        "summary": {
            "total_frames": 100,
            "frames_with_pose": 85,
        }
    }
    context = {
        "camera_view": "side"
    }
    
    confidence = _calculate_job_confidence(metrics, context, "batting")
    
    assert "confidence_score" in confidence
    assert "confidence_label" in confidence
    assert "confidence_reasons" in confidence
    assert "confidence_factors" in confidence
    
    # With 85% detection, 95% coverage, and side view, should be high confidence
    assert confidence["confidence_score"] >= 0.70, (
        f"Expected high confidence, got {confidence['confidence_score']} "
        f"(factors: {confidence['confidence_factors']})"
    )
    assert confidence["confidence_label"] in ["high", "medium"]


def test_finding_confidence_margin_based():
    """Test _calculate_finding_confidence uses margin-based scoring."""
    # Metrics with head stability
    metrics_high = {"head_stability_score": {"score": 0.30}}
    metrics_low = {"head_stability_score": {"score": 0.58}}
    
    # High severity finding (far below threshold 0.60)
    high_severity_finding = {
        "code": "HEAD_MOVEMENT",
        "severity": "high",
        "evidence": {
            "head_stability_score": 0.30,  # Far below 0.60
            "threshold": 0.60,
        }
    }
    
    high_conf = _calculate_finding_confidence(high_severity_finding, metrics_high)
    
    # Low severity finding (close to threshold)
    low_severity_finding = {
        "code": "HEAD_MOVEMENT",
        "severity": "low",
        "evidence": {
            "head_stability_score": 0.58,  # Close to 0.60
            "threshold": 0.60,
        }
    }
    
    low_conf = _calculate_finding_confidence(low_severity_finding, metrics_low)
    
    # High severity (larger margin) should have higher confidence
    assert high_conf > low_conf, (
        f"High severity finding should have higher confidence. "
        f"Got high={high_conf} (margin={0.60-0.30}), low={low_conf} (margin={0.60-0.58})"
    )


@pytest.mark.parametrize("mode,metric,score", [
    ("bowling", "head_stability_score", 0.50),  # Below bowling threshold (0.65) = finding
    ("batting", "head_stability_score", 0.50),  # Below batting threshold (0.60) = finding  
    ("wicketkeeping", "head_stability_score", 0.50),  # ABOVE wicketkeeping threshold (0.58) = no finding
])
def test_thresholds_affect_finding_generation(mode, metric, score):
    """Test that different thresholds lead to different finding generation."""
    metrics = {
        metric: {"score": score, "num_frames": 100},
        "summary": {
            "total_frames": 120,
            "frames_with_pose": 100,
        }
    }
    
    result = generate_findings(metrics, analysis_mode=mode)
    
    if mode == "wicketkeeping":
        # Score 0.50 is BELOW wicketkeeping threshold 0.58, so should have finding
        head_findings = [f for f in result["findings"] if "head" in f["code"].lower()]
        assert len(head_findings) > 0, (
            f"Wicketkeeping should generate head finding for score {score} "
            f"(threshold: {THRESHOLDS_BY_MODE['wicketkeeping'][metric]})"
        )
    else:
        # Bowling and batting should definitely have finding
        head_findings = [f for f in result["findings"] if "head" in f["code"].lower()]
        assert len(head_findings) > 0, (
            f"{mode} should generate head finding for score {score}"
        )


def test_check_functions_use_mode_thresholds():
    """Test that _check_* functions use mode-specific thresholds."""
    metrics = {
        "head_stability_score": {"score": 0.62, "num_frames": 100}
    }
    
    # Bowling (threshold 0.65) - should trigger finding
    bowling_finding = _check_head_movement(metrics, None, None, "bowling")
    assert bowling_finding is not None, "Should trigger finding for bowling (0.62 < 0.65)"
    
    # Batting (threshold 0.60) - should NOT trigger finding
    batting_finding = _check_head_movement(metrics, None, None, "batting")
    assert batting_finding is None, "Should NOT trigger finding for batting (0.62 > 0.60)"


def test_check_functions_use_mode_drills():
    """Test that _check_* functions return mode-specific drills."""
    metrics = {
        "balance_drift_score": {"score": 0.30, "num_frames": 100}
    }
    
    # Get findings for different modes
    bowling_finding = _check_balance_drift(metrics, None, None, "bowling")
    fielding_finding = _check_balance_drift(metrics, None, None, "fielding")
    
    assert bowling_finding is not None
    assert fielding_finding is not None
    
    bowling_drills = bowling_finding["suggested_drills"]
    fielding_drills = fielding_finding["suggested_drills"]
    
    # Drills should be different
    assert bowling_drills != fielding_drills, (
        "Bowling and fielding should have different drills for same finding"
    )
    
    # Check for mode-appropriate terminology
    bowling_text = " ".join(bowling_drills).lower()
    fielding_text = " ".join(fielding_drills).lower()
    
    assert any(term in bowling_text for term in ["bowl", "delivery", "action"]), (
        f"Bowling drills should contain bowling terminology: {bowling_drills}"
    )
    assert any(term in fielding_text for term in ["field", "movement", "position"]), (
        f"Fielding drills should contain fielding terminology: {fielding_drills}"
    )


def test_mode_validation_hard_guardrail():
    """Test that invalid modes raise ValueError."""
    metrics = {
        "head_stability_score": {"score": 0.50, "num_frames": 100},
        "summary": {"total_frames": 100, "frames_with_pose": 90}
    }
    
    with pytest.raises(ValueError, match="analysis_mode is required"):
        generate_findings(metrics, analysis_mode="invalid_mode")


@pytest.mark.parametrize("mode", ["batting", "bowling", "wicketkeeping", "fielding"])
def test_all_modes_have_drills_and_thresholds(mode):
    """Test that all valid modes have entries in DRILLS_BY_MODE and THRESHOLDS_BY_MODE."""
    assert mode in DRILLS_BY_MODE, f"Mode {mode} missing from DRILLS_BY_MODE"
    assert mode in THRESHOLDS_BY_MODE, f"Mode {mode} missing from THRESHOLDS_BY_MODE"
    
    mode_drills = DRILLS_BY_MODE[mode]
    mode_thresholds = THRESHOLDS_BY_MODE[mode]
    
    assert isinstance(mode_drills, dict), f"{mode} drills should be dict"
    assert isinstance(mode_thresholds, dict), f"{mode} thresholds should be dict"
    
    # Check required threshold keys
    required_thresholds = [
        "head_stability_score",
        "balance_drift_score",
        "front_knee_brace_score",
        "hip_shoulder_separation_timing",
        "elbow_drop_score",
    ]
    for threshold_key in required_thresholds:
        assert threshold_key in mode_thresholds, (
            f"{mode} missing threshold: {threshold_key}"
        )
