"""
Rule-Based Coaching Findings Generator

Converts pose metrics into human-readable coaching findings with:
- Issue detection based on MVP thresholds
- Severity classification
- Evidence and rationale
- Actionable coaching cues
- Suggested drills
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# Constants: MVP Thresholds
# ============================================================================

THRESHOLDS = {
    "head_stability_score": 0.60,
    "balance_drift_score": 0.55,
    "front_knee_brace_score": 0.50,
    "hip_shoulder_separation_timing": 0.12,  # Target lag, ±0.10 tolerance
    "hip_shoulder_separation_tolerance": 0.10,
    "elbow_drop_score": 0.55,
}

# ============================================================================
# Drill Database (Strings for MVP)
# ============================================================================

DRILL_SUGGESTIONS = {
    "HEAD_MOVEMENT": [
        "Batting against a wall with eyes fixed on the ball contact point",
        "Playing in front of a mirror to observe head position through shots",
        "Using neck stabilization exercises before net sessions",
        "Practice shadow batting with closed eyes to develop muscle memory",
    ],
    "BALANCE_DRIFT": [
        "Balance board exercises for proprioceptive development",
        "Single-leg stance drills to strengthen stabilizer muscles",
        "Practicing footwork drills with emphasis on weight distribution",
        "Playing off a line marked on the crease to track movement",
    ],
    "KNEE_COLLAPSE": [
        "Quadriceps strengthening exercises (lunges, leg press)",
        "Knee brace practice with weighted squats",
        "Band work focusing on VMO (vastus medialis obliquus) activation",
        "Balance drills on one leg to build knee stability",
    ],
    "ROTATION_TIMING": [
        "Hip mobility drills to increase rotation range",
        "Separation drills using medicine balls (hip vs shoulder rotation)",
        "Shadow batting focusing on hip rotation initiation",
        "Resistance band work to practice explosive hip rotation",
    ],
    "ELBOW_DROP": [
        "Arm drop exercises using suspension training",
        "Elbow angle drills in front of mirror for feedback",
        "Relaxation exercises to reduce upper body tension",
        "Throwing drills to develop natural arm drop pattern",
    ],
}

# ============================================================================
# Finding Definitions
# ============================================================================

FINDING_DEFINITIONS: dict[str, dict[str, Any]] = {
    "HEAD_MOVEMENT": {
        "title": "Head movement through contact",
        "why_it_matters": "A stable head position is crucial for visual tracking and bat control. "
        "Excessive head movement can cause timing issues and reduced accuracy.",
        "low_severity": {
            "message": "Minor head movement detected during swing.",
            "cues": [
                "Focus on keeping your nose over your toes at contact",
                "Watch the ball until it hits the bat",
                "Practice shadow batting with eyes fixed on a spot",
            ],
        },
        "medium_severity": {
            "message": "Significant head movement affecting shot consistency.",
            "cues": [
                "Head movement is reducing your ability to track the ball",
                "Implement head stabilization drills daily",
                "Develop neck strengthening routine",
                "Consider working with a biomechanics coach",
            ],
        },
        "high_severity": {
            "message": "Severe head movement is compromising batting technique.",
            "cues": [
                "Head is moving excessively - this is a fundamental issue",
                "Stop all match practice until technique improves",
                "Conduct daily, focused drill work with video analysis",
                "Work with coaching staff to identify root cause",
            ],
        },
    },
    "BALANCE_DRIFT": {
        "title": "Balance instability during motion",
        "why_it_matters": "Good balance keeps your weight centered over your feet, enabling powerful and "
        "controlled strokes. Poor balance leads to inconsistent shot placement.",
        "low_severity": {
            "message": "Minor balance drift observed.",
            "cues": [
                "Focus on weight distribution throughout your stance",
                "Maintain contact with the crease at all times",
                "Practice footwork patterns slowly",
            ],
        },
        "medium_severity": {
            "message": "Balance issues affecting stroke execution.",
            "cues": [
                "Your center of mass is shifting excessively",
                "Strengthen core stability with targeted exercises",
                "Practice drills with a marked crease line",
                "Reduce stride length temporarily to improve control",
            ],
        },
        "high_severity": {
            "message": "Poor balance is a critical limitation.",
            "cues": [
                "Balance loss is affecting all your shots",
                "Implement core and lower body strengthening program",
                "Work on footwork fundamentals in isolation",
                "Consider postural assessment and correction",
            ],
        },
    },
    "KNEE_COLLAPSE": {
        "title": "Knee collapse during stance",
        "why_it_matters": "A braced knee provides stability and transfers power from the lower body. "
        "Knee collapse reduces force generation and increases injury risk.",
        "low_severity": {
            "message": "Minor knee bending detected.",
            "cues": [
                "Focus on keeping knees braced throughout the shot",
                "Strengthen quadriceps with targeted exercises",
                "Maintain athletic knee position",
            ],
        },
        "medium_severity": {
            "message": "Significant knee collapse affecting power generation.",
            "cues": [
                "Your knees are collapsing - this reduces power and stability",
                "Begin daily quadriceps strengthening routine",
                "Practice maintaining knee brace through all shot types",
                "Work on lower body conditioning",
            ],
        },
        "high_severity": {
            "message": "Severe knee collapse - high injury risk.",
            "cues": [
                "Knee collapse is severe and poses injury risk",
                "Suspend intensive batting until technique improves",
                "Implement comprehensive knee stability program",
                "Get physiotherapy assessment before returning to training",
            ],
        },
    },
    "ROTATION_TIMING": {
        "title": "Hip-shoulder rotation timing",
        "why_it_matters": "Hip rotation should initiate before shoulder rotation to generate power through the "
        "kinetic chain. Poor timing reduces power and increases injury risk.",
        "low_severity": {
            "message": "Minor timing differences between hip and shoulder rotation.",
            "cues": [
                "Work on hip rotation initiation drills",
                "Practice separating hip and shoulder movement",
                "Focus on explosive hip drive",
            ],
        },
        "medium_severity": {
            "message": "Hip-shoulder separation timing is suboptimal.",
            "cues": [
                "Your hip and shoulder are rotating together instead of in sequence",
                "Practice medicine ball rotational drills",
                "Work on hip mobility to improve rotation range",
                "Film analysis to monitor separation progress",
            ],
        },
        "high_severity": {
            "message": "Poor hip-shoulder separation is limiting power generation.",
            "cues": [
                "Hip-shoulder separation is significantly poor",
                "This is limiting your power generation and swing speed",
                "Implement daily separation drills and mobility work",
                "Consider biomechanics analysis to identify restrictions",
            ],
        },
    },
    "ELBOW_DROP": {
        "title": "Elbow positioning at address",
        "why_it_matters": "Dropped elbows allow for a fuller swing and better bat control. High elbows restrict "
        "movement and create tension, leading to inconsistent shot execution.",
        "low_severity": {
            "message": "Elbows slightly high - minor positioning adjustment needed.",
            "cues": [
                "Work on relaxing your upper body",
                "Practice arm drop exercises",
                "Visualize natural elbow position during shadow batting",
            ],
        },
        "medium_severity": {
            "message": "High elbows are restricting your swing.",
            "cues": [
                "Your elbows are too high - this restricts movement",
                "Practice relaxation and arm drop drills",
                "Use mirrors to monitor elbow position",
                "Develop pre-shot routine to ensure proper setup",
            ],
        },
        "high_severity": {
            "message": "Severely high elbows are compromising technique.",
            "cues": [
                "Elbow position is severely high and restricting your swing",
                "This is a fundamental setup issue",
                "Work exclusively on elbow drop drills until corrected",
                "Address any underlying tension or flexibility issues",
            ],
        },
    },
}


# ============================================================================
# Utility Functions
# ============================================================================


def _get_severity(score: float, threshold: float, is_higher_better: bool = True) -> str:
    """
    Classify severity based on score vs threshold.

    Args:
        score: Actual metric value
        threshold: Target threshold
        is_higher_better: True if higher scores are better (default True)

    Returns:
        "low" | "medium" | "high"
    """
    if is_higher_better:
        # Higher is better (head_stability, balance_drift, etc.)
        diff = threshold - score
        if diff < 0.05:
            return "low"
        elif diff < 0.15:
            return "medium"
        else:
            return "high"
    else:
        # Lower is better (gap/difference metrics)
        diff = score - threshold
        if diff < 0.05:
            return "low"
        elif diff < 0.15:
            return "medium"
        else:
            return "high"


def _get_overall_level(findings: list[dict]) -> str:
    """
    Compute overall performance level from findings.

    Args:
        findings: List of finding dicts with severity

    Returns:
        "low" | "medium" | "high"
    """
    if not findings:
        return "high"

    severity_scores = {"low": 1, "medium": 2, "high": 3}
    avg_severity = sum(severity_scores.get(f["severity"], 1) for f in findings) / len(findings)

    if avg_severity < 1.5:
        return "high"
    elif avg_severity < 2.5:
        return "medium"
    else:
        return "low"


# ============================================================================
# Finding Generation
# ============================================================================


def _check_head_movement(metrics: dict) -> dict | None:
    """Check head stability metric."""
    head_score = metrics.get("head_stability_score", {}).get("score")

    if head_score is None:
        return None

    if head_score < THRESHOLDS["head_stability_score"]:
        severity = _get_severity(head_score, THRESHOLDS["head_stability_score"])

        return {
            "code": "HEAD_MOVEMENT",
            "title": FINDING_DEFINITIONS["HEAD_MOVEMENT"]["title"],
            "severity": severity,
            "evidence": {
                "head_stability_score": round(head_score, 3),
                "threshold": THRESHOLDS["head_stability_score"],
            },
            "why_it_matters": FINDING_DEFINITIONS["HEAD_MOVEMENT"]["why_it_matters"],
            "cues": FINDING_DEFINITIONS["HEAD_MOVEMENT"][f"{severity}_severity"]["cues"],
            "suggested_drills": DRILL_SUGGESTIONS.get("HEAD_MOVEMENT", []),
        }

    return None


def _check_balance_drift(metrics: dict) -> dict | None:
    """Check balance drift metric."""
    balance_score = metrics.get("balance_drift_score", {}).get("score")

    if balance_score is None:
        return None

    if balance_score < THRESHOLDS["balance_drift_score"]:
        severity = _get_severity(balance_score, THRESHOLDS["balance_drift_score"])

        return {
            "code": "BALANCE_DRIFT",
            "title": FINDING_DEFINITIONS["BALANCE_DRIFT"]["title"],
            "severity": severity,
            "evidence": {
                "balance_drift_score": round(balance_score, 3),
                "threshold": THRESHOLDS["balance_drift_score"],
            },
            "why_it_matters": FINDING_DEFINITIONS["BALANCE_DRIFT"]["why_it_matters"],
            "cues": FINDING_DEFINITIONS["BALANCE_DRIFT"][f"{severity}_severity"]["cues"],
            "suggested_drills": DRILL_SUGGESTIONS.get("BALANCE_DRIFT", []),
        }

    return None


def _check_knee_collapse(metrics: dict) -> dict | None:
    """Check knee brace metric."""
    knee_score = metrics.get("front_knee_brace_score", {}).get("score")

    if knee_score is None:
        return None

    if knee_score < THRESHOLDS["front_knee_brace_score"]:
        severity = _get_severity(knee_score, THRESHOLDS["front_knee_brace_score"])

        return {
            "code": "KNEE_COLLAPSE",
            "title": FINDING_DEFINITIONS["KNEE_COLLAPSE"]["title"],
            "severity": severity,
            "evidence": {
                "front_knee_brace_score": round(knee_score, 3),
                "threshold": THRESHOLDS["front_knee_brace_score"],
            },
            "why_it_matters": FINDING_DEFINITIONS["KNEE_COLLAPSE"]["why_it_matters"],
            "cues": FINDING_DEFINITIONS["KNEE_COLLAPSE"][f"{severity}_severity"]["cues"],
            "suggested_drills": DRILL_SUGGESTIONS.get("KNEE_COLLAPSE", []),
        }

    return None


def _check_rotation_timing(metrics: dict) -> dict | None:
    """Check hip-shoulder separation timing metric."""
    lag = metrics.get("hip_shoulder_separation_timing", {}).get("score")

    if lag is None:
        return None

    target = THRESHOLDS["hip_shoulder_separation_timing"]
    diff = abs(lag - target)

    # No finding if timing is perfect or very close
    if diff < 0.01:
        return None

    # Severity based on how far from target
    if diff < 0.05:
        severity = "low"
    elif diff < 0.15:
        severity = "medium"
    else:
        severity = "high"

    return {
        "code": "ROTATION_TIMING",
        "title": FINDING_DEFINITIONS["ROTATION_TIMING"]["title"],
        "severity": severity,
        "evidence": {
            "hip_shoulder_separation_lag_seconds": round(lag, 3),
            "target_lag_seconds": target,
        },
        "why_it_matters": FINDING_DEFINITIONS["ROTATION_TIMING"]["why_it_matters"],
        "cues": FINDING_DEFINITIONS["ROTATION_TIMING"][f"{severity}_severity"]["cues"],
        "suggested_drills": DRILL_SUGGESTIONS.get("ROTATION_TIMING", []),
    }


def _check_elbow_drop(metrics: dict) -> dict | None:
    """Check elbow drop metric."""
    elbow_score = metrics.get("elbow_drop_score", {}).get("score")

    if elbow_score is None:
        return None

    if elbow_score < THRESHOLDS["elbow_drop_score"]:
        severity = _get_severity(elbow_score, THRESHOLDS["elbow_drop_score"])

        return {
            "code": "ELBOW_DROP",
            "title": FINDING_DEFINITIONS["ELBOW_DROP"]["title"],
            "severity": severity,
            "evidence": {
                "elbow_drop_score": round(elbow_score, 3),
                "threshold": THRESHOLDS["elbow_drop_score"],
            },
            "why_it_matters": FINDING_DEFINITIONS["ELBOW_DROP"]["why_it_matters"],
            "cues": FINDING_DEFINITIONS["ELBOW_DROP"][f"{severity}_severity"]["cues"],
            "suggested_drills": DRILL_SUGGESTIONS.get("ELBOW_DROP", []),
        }

    return None


# ============================================================================
# Main API
# ============================================================================


def generate_findings(metrics: dict, context: dict | None = None) -> dict[str, Any]:
    """
    Generate rule-based coaching findings from metrics.

    Args:
        metrics: Dict with metric scores from compute_pose_metrics()
                 Expected keys: head_stability_score, balance_drift_score, etc.
        context: Optional context dict for future extensibility
                (e.g., player level, session type)

    Returns:
        {
            "overall_level": "low|medium|high",
            "findings": [
                {
                    "code": "HEAD_MOVEMENT|BALANCE_DRIFT|...",
                    "title": str,
                    "severity": "low|medium|high",
                    "evidence": {...},
                    "why_it_matters": str,
                    "cues": [str, ...],
                    "suggested_drills": [str, ...]
                },
                ...
            ],
            "context": {...}  # echo back context if provided
        }
    """
    # Extract metrics from nested structure if needed
    metric_scores = metrics.get("metrics", metrics)
    logger.info(f"Generating findings for {len(metric_scores)} metrics")

    # Check all conditions
    findings = []

    head_finding = _check_head_movement(metric_scores)
    if head_finding:
        findings.append(head_finding)

    balance_finding = _check_balance_drift(metric_scores)
    if balance_finding:
        findings.append(balance_finding)

    knee_finding = _check_knee_collapse(metric_scores)
    if knee_finding:
        findings.append(knee_finding)

    rotation_finding = _check_rotation_timing(metric_scores)
    if rotation_finding:
        findings.append(rotation_finding)

    elbow_finding = _check_elbow_drop(metric_scores)
    if elbow_finding:
        findings.append(elbow_finding)

    # Check for insufficient pose visibility across metrics
    zero_frame_metrics = sum(
        1
        for metric in metric_scores.values()
        if isinstance(metric, dict) and metric.get("num_frames", 0) == 0
    )

    if zero_frame_metrics > 2:
        # Calculate detection rate if available
        summary = metrics.get("summary", {})
        total_frames = summary.get("total_frames", 1)
        frames_with_pose = summary.get("frames_with_pose", 0)
        detection_rate = (frames_with_pose / total_frames * 100) if total_frames > 0 else 0

        # Set severity based on detection rate
        severity = "low" if detection_rate >= 50 else "medium"

        visibility_finding = {
            "code": "INSUFFICIENT_POSE_VISIBILITY",
            "title": "Insufficient Pose Visibility",
            "severity": severity,
            "evidence": {
                "zero_frame_metrics": zero_frame_metrics,
                "detection_rate": f"{detection_rate:.1f}%",
            },
            "why_it_matters": "Multiple metrics could not be computed due to insufficient pose detection. This limits the reliability of biomechanical analysis.",
            "cues": [
                "Improve video lighting and camera angle",
                "Ensure the athlete's full body is visible in the frame",
                "Reduce background clutter and improve contrast",
            ],
            "suggested_drills": [
                "Re-record the video with better lighting",
                "Adjust camera position for clearer pose visibility",
                "Test with different camera angles if available",
            ],
        }
        findings.append(visibility_finding)

    # Compute overall level
    overall_level = _get_overall_level(findings)

    logger.info(f"Generated {len(findings)} findings with overall level: {overall_level}")

    result: dict[str, Any] = {
        "overall_level": overall_level,
        "findings": findings,
    }

    if context:
        result["context"] = context

    return result
