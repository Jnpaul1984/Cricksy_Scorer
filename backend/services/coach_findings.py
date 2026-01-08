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
from typing import Any, cast

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

# Batting-specific drills
BATTING_DRILL_SUGGESTIONS = {
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

# Bowling-specific drills
BOWLING_DRILL_SUGGESTIONS = {
    "HEAD_MOVEMENT": [
        "Head stabilization drills focusing on target fixation",
        "Bowling at a single stump with head position awareness",
        "Neck strengthening exercises for delivery stride stability",
        "Mirror work to observe head control through release",
    ],
    "BALANCE_DRIFT": [
        "Single-leg balance drills on landing leg",
        "Core stability exercises for gather and delivery stride",
        "Rope drill walking to develop stable gather position",
        "Balance board work specific to bowling action",
    ],
    "KNEE_COLLAPSE": [
        "Front knee bracing drills with resistance bands",
        "Eccentric quadriceps loading exercises",
        "Landing leg stability work with medicine balls",
        "Plyometric exercises for knee control on impact",
    ],
    "ROTATION_TIMING": [
        "Hip-shoulder separation drills using rotation poles",
        "Counter-rotation exercises to enhance torque",
        "Medicine ball throws mimicking bowling action",
        "Flexibility work to maximize upper body coil",
    ],
    "ELBOW_DROP": [
        "High elbow position drills at release point",
        "Resistance band work for bowling arm path",
        "Wall drills maintaining elbow height through delivery",
        "Video analysis of release point consistency",
    ],
    "RELEASE_POINT": [
        "Rope drill with release point markers",
        "Mirror work at gather position",
        "Consistent stride length drills",
        "Target bowling with release point focus",
    ],
    "SWING_VARIATION": [
        "Wrist position drills for swing control",
        "Seam angle practice with video feedback",
        "Shiny/rough side awareness drills",
        "Grip variations for different swing types",
    ],
}

# Wicketkeeping-specific drills
WICKETKEEPING_DRILL_SUGGESTIONS = {
    "HEAD_MOVEMENT": [
        "Head tracking drills following ball from bowler to gloves",
        "Stationary catching with focus on head stillness",
        "Reaction ball exercises with head position awareness",
        "Mirror work to observe head control during takes",
    ],
    "BALANCE_DRIFT": [
        "Lateral movement drills maintaining low center of gravity",
        "Split-step timing exercises for balance preparation",
        "Single-leg stability work for diving movements",
        "Agility ladder work with emphasis on controlled stops",
    ],
    "KNEE_COLLAPSE": [
        "Squat endurance exercises for sustained low position",
        "Lateral lunge drills for leg strength and stability",
        "Knee tracking exercises during dive mechanics",
        "Core and leg integration work for stable crouch",
    ],
    "ROTATION_TIMING": [
        "Hip rotation drills for throws to stumps",
        "Medicine ball throws from crouched position",
        "Rotational power work for quick releases",
        "Footwork drills emphasizing hip drive on throws",
    ],
    "ELBOW_DROP": [
        "Catching drills focusing on soft hands technique",
        "Hand position exercises for optimal glove angle",
        "Resistance work for forearm and wrist strength",
        "High-repetition catching to develop natural hand positioning",
    ],
}

# Default/generic drills (used when no mode specified)
DRILL_SUGGESTIONS = BATTING_DRILL_SUGGESTIONS

# ============================================================================
# Allowed Finding Codes by Mode (Prevents Cross-Contamination)
# ============================================================================

ALLOWED_CODES_BY_MODE: dict[str, set[str]] = {
    "batting": {
        "HEAD_MOVEMENT",
        "BALANCE_DRIFT",
        "KNEE_COLLAPSE",
        "ROTATION_TIMING",
        "ELBOW_DROP",
        "INSUFFICIENT_POSE_VISIBILITY",
    },
    "bowling": {
        "HEAD_MOVEMENT",
        "BALANCE_DRIFT",
        "KNEE_COLLAPSE",
        "ROTATION_TIMING",
        "ELBOW_DROP",
        "INSUFFICIENT_POSE_VISIBILITY",
        # Bowling-specific codes
        "INSUFFICIENT_BALL_TRACKING",
        "INCONSISTENT_RELEASE_POINT",
        "SWING_ANALYSIS",
    },
    "wicketkeeping": {
        "HEAD_MOVEMENT",
        "BALANCE_DRIFT",
        "KNEE_COLLAPSE",
        "ROTATION_TIMING",
        "ELBOW_DROP",  # For catching hand position
        "INSUFFICIENT_POSE_VISIBILITY",
    },
    "fielding": {
        "HEAD_MOVEMENT",
        "BALANCE_DRIFT",
        "KNEE_COLLAPSE",
        "ROTATION_TIMING",
        "ELBOW_DROP",
        "INSUFFICIENT_POSE_VISIBILITY",
    },
}

# ============================================================================
# Mode-Aware Narratives (Why It Matters)
# ============================================================================

WHY_IT_MATTERS_BY_MODE: dict[str, dict[str, str]] = {
    "HEAD_MOVEMENT": {
        "batting": "A stable head position is crucial for visual tracking and bat control. "
        "Excessive head movement can cause timing issues and reduced shot accuracy.",
        "bowling": "Head stability during delivery is critical for consistent line and length. "
        "Head movement disrupts your sight of the target and reduces accuracy.",
        "wicketkeeping": "Keeping your head still while tracking the ball ensures clean takes. "
        "Head movement reduces reaction time and causes fumbles on lateral movements.",
        "fielding": "Head stability improves hand-eye coordination during catches and pickups. "
        "Excessive movement reduces tracking accuracy and increases errors.",
    },
    "KNEE_COLLAPSE": {
        "batting": "A braced front knee provides stability and transfers power from the lower body. "
        "Knee collapse reduces force generation and increases injury risk.",
        "bowling": "Front leg bracing at delivery is critical for transferring energy to the ball. "
        "Knee collapse dissipates power and puts excessive stress on the lower back.",
        "wicketkeeping": "Knee stability in your crouch maintains balance for lateral movements. "
        "Knee collapse slows your pushoff speed and limits range.",
        "fielding": "Knee bracing during pickups and throws provides a stable base. "
        "Collapse reduces throwing velocity and accuracy.",
    },
    "ROTATION_TIMING": {
        "batting": "Hip rotation should initiate before shoulder rotation to generate power through the "
        "kinetic chain. Poor timing reduces power and increases injury risk.",
        "bowling": "Hip-shoulder separation creates the 'whip' effect in fast bowling. "
        "Poor separation limits ball speed and increases shoulder injury risk.",
        "wicketkeeping": "Hip rotation powers your throws to the stumps. "
        "Poor timing reduces throwing velocity and accuracy from the crouched position.",
        "fielding": "Efficient hip-shoulder separation generates throwing power. "
        "Poor timing reduces throw distance and increases arm strain.",
    },
}

# Mode-aware high severity warnings (STOP training messages)
HIGH_SEVERITY_WARNINGS_BY_MODE: dict[str, dict[str, str]] = {
    "KNEE_COLLAPSE": {
        "batting": "Suspend intensive batting until technique improves",
        "bowling": "Suspend fast bowling until front leg mechanics are corrected",
        "wicketkeeping": "Limit extended keeping sessions until knee stability improves",
        "fielding": "Avoid explosive fielding drills until knee bracing is corrected",
    },
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
# Ball Tracking Findings (Bowling Mode)
# ============================================================================

BOWLING_BALL_TRACKING_FINDINGS = {
    "INSUFFICIENT_BALL_TRACKING": {
        "title": "Ball tracking insufficient for swing/length analysis",
        "why_it_matters": "Reliable ball tracking is essential for analyzing swing, seam position, and length. "
        "Low detection rates may be due to poor lighting, ball color contrast, or camera angle.",
        "cues": [
            "Improve video quality with better lighting",
            "Ensure ball color contrasts with background",
            "Use higher frame rate camera if available",
            "Adjust camera angle to track full ball flight",
        ],
        "drills": [
            "Re-record delivery with improved lighting setup",
            "Use contrasting background (dark sight-screen for red ball)",
            "Test camera positioning to capture full trajectory",
        ],
    },
    "INCONSISTENT_RELEASE_POINT": {
        "title": "Release point inconsistency detected",
        "why_it_matters": "Consistent release points are crucial for line and length control. "
        "Variation indicates mechanical issues in gather or delivery stride.",
        "low_severity": {
            "message": "Minor release point variation detected.",
            "cues": [
                "Focus on consistent gather position",
                "Mark your release point reference in practice",
                "Maintain consistent stride length",
            ],
        },
        "medium_severity": {
            "message": "Moderate release point inconsistency affecting control.",
            "cues": [
                "Release point is varying significantly",
                "Work on consistent run-up rhythm",
                "Practice with target markers at release point",
                "Video review of gather and release phases",
            ],
        },
        "high_severity": {
            "message": "High release point variation - major control issue.",
            "cues": [
                "Release point variance is severe",
                "Rebuild bowling action fundamentals",
                "Work with coach on gather mechanics",
                "Daily consistency drills with immediate feedback",
            ],
        },
    },
    "SWING_ANALYSIS": {
        "title": "Ball swing characteristics",
        "why_it_matters": "Understanding your natural swing helps plan field settings and "
        "develop variations. Swing is influenced by wrist position, seam angle, and release.",
        "analysis": {
            "straight": "Ball traveling straight - good for accuracy, consider developing swing variations",
            "inswing": "Natural inswing detected - use for attacking stumps and LBW opportunities",
            "outswing": "Natural outswing detected - excellent for taking outside edge",
            "swing": "Variable swing detected - work on consistent wrist position",
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


def _contextualize_finding(finding: dict[str, Any], analysis_context: str | None) -> dict[str, Any]:
    """
    Adjust finding wording based on analysis context (batting, bowling, etc.).

    Args:
        finding: The finding dict to contextualize
        analysis_context: One of "batting", "bowling", "wicketkeeping", "fielding", "mixed"

    Returns:
        Updated finding with context-aware messages
    """
    if not analysis_context or analysis_context == "mixed":
        return finding

    # Context-specific title adjustments
    title_adjustments = {
        "batting": {
            "HEAD_MOVEMENT": "Head movement during batting stroke",
            "BALANCE_DRIFT": "Balance drift in batting stance",
            "KNEE_COLLAPSE": "Front knee collapse during batting",
            "ROTATION_TIMING": "Hip-shoulder separation in batting swing",
            "ELBOW_DROP": "Elbow position in batting swing",
        },
        "bowling": {
            "HEAD_MOVEMENT": "Head movement during bowling delivery",
            "BALANCE_DRIFT": "Balance drift in bowling action",
            "KNEE_COLLAPSE": "Front knee collapse at delivery",
            "ROTATION_TIMING": "Hip-shoulder separation in bowling action",
            "ELBOW_DROP": "Elbow drop during bowling delivery",
        },
        "wicketkeeping": {
            "HEAD_MOVEMENT": "Head movement during keeping",
            "BALANCE_DRIFT": "Balance stability while keeping",
            "KNEE_COLLAPSE": "Knee stability in wicketkeeping stance",
            "ROTATION_TIMING": "Body rotation while taking the ball",
        },
        "fielding": {
            "HEAD_MOVEMENT": "Head movement during fielding",
            "BALANCE_DRIFT": "Balance during fielding movements",
            "KNEE_COLLAPSE": "Knee stability during fielding",
        },
    }

    code = finding.get("code")
    if code and analysis_context in title_adjustments:
        context_titles = title_adjustments[analysis_context]
        if code in context_titles:
            finding["title"] = context_titles[code]

    return finding


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


def _format_timestamp(seconds: float | None) -> str:
    """Format timestamp as MM:SS."""
    if seconds is None:
        return "N/A"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"


def _attach_evidence_markers(
    finding: dict,
    metric_key: str,
    evidence_data: dict | None,
) -> dict:
    """Attach worst_frames and bad_segments from evidence to finding.

    Args:
        finding: Finding dict to enhance
        metric_key: Key to lookup in evidence (e.g., "head_stability_score")
        evidence_data: Evidence dict from metrics_result["evidence"]

    Returns:
        Enhanced finding dict with video_evidence attached
    """
    if not evidence_data or metric_key not in evidence_data:
        return finding

    metric_evidence = evidence_data[metric_key]

    # Extract worst frames with timestamps
    worst_frames = metric_evidence.get("worst_frames", [])
    worst_frame_refs = []
    for wf in worst_frames[:3]:  # Top 3 worst
        frame_num = wf.get("frame_num")
        timestamp_s = wf.get("timestamp_s")
        score = wf.get("score")
        if timestamp_s is not None:
            worst_frame_refs.append(
                {
                    "frame": frame_num,
                    "timestamp": _format_timestamp(timestamp_s),
                    "score": round(score, 2) if score is not None else None,
                }
            )

    # Extract bad segments (time ranges)
    bad_segments = metric_evidence.get("bad_segments", [])
    segment_refs = []
    for seg in bad_segments[:3]:  # Top 3 segments
        start_ts = seg.get("start_timestamp_s")
        end_ts = seg.get("end_timestamp_s")
        min_score = seg.get("min_score")
        if start_ts is not None and end_ts is not None:
            segment_refs.append(
                {
                    "start": _format_timestamp(start_ts),
                    "end": _format_timestamp(end_ts),
                    "min_score": round(min_score, 2) if min_score is not None else None,
                }
            )

    # Attach to finding
    finding["video_evidence"] = {
        "worst_frames": worst_frame_refs,
        "bad_segments": segment_refs,
    }

    return finding


def _check_head_movement(
    metrics: dict,
    evidence: dict | None = None,
    drill_db: dict | None = None,
    analysis_mode: str = "batting",
) -> dict | None:
    """Check head stability metric with mode-aware narratives."""
    head_score = metrics.get("head_stability_score", {}).get("score")

    if head_score is None:
        return None

    if head_score < THRESHOLDS["head_stability_score"]:
        severity = _get_severity(head_score, THRESHOLDS["head_stability_score"])

        # Use mode-specific "why it matters" text
        why_it_matters = WHY_IT_MATTERS_BY_MODE.get("HEAD_MOVEMENT", {}).get(
            analysis_mode, FINDING_DEFINITIONS["HEAD_MOVEMENT"]["why_it_matters"]
        )

        finding = {
            "code": "HEAD_MOVEMENT",
            "title": FINDING_DEFINITIONS["HEAD_MOVEMENT"]["title"],
            "severity": severity,
            "evidence": {
                "head_stability_score": round(head_score, 3),
                "threshold": THRESHOLDS["head_stability_score"],
            },
            "why_it_matters": why_it_matters,
            "cues": FINDING_DEFINITIONS["HEAD_MOVEMENT"][f"{severity}_severity"]["cues"],
            "suggested_drills": (drill_db or BATTING_DRILL_SUGGESTIONS).get("HEAD_MOVEMENT", []),
        }

        return _attach_evidence_markers(finding, "head_stability_score", evidence)

    return None


def _check_balance_drift(
    metrics: dict,
    evidence: dict | None = None,
    drill_db: dict | None = None,
    analysis_mode: str = "batting",
) -> dict | None:
    """Check balance drift metric with mode-aware narratives."""
    balance_score = metrics.get("balance_drift_score", {}).get("score")

    if balance_score is None:
        return None

    if balance_score < THRESHOLDS["balance_drift_score"]:
        severity = _get_severity(balance_score, THRESHOLDS["balance_drift_score"])

        # Use mode-specific "why it matters" text
        why_it_matters = WHY_IT_MATTERS_BY_MODE.get("BALANCE_DRIFT", {}).get(
            analysis_mode, FINDING_DEFINITIONS["BALANCE_DRIFT"]["why_it_matters"]
        )

        finding = {
            "code": "BALANCE_DRIFT",
            "title": FINDING_DEFINITIONS["BALANCE_DRIFT"]["title"],
            "severity": severity,
            "evidence": {
                "balance_drift_score": round(balance_score, 3),
                "threshold": THRESHOLDS["balance_drift_score"],
            },
            "why_it_matters": why_it_matters,
            "cues": FINDING_DEFINITIONS["BALANCE_DRIFT"][f"{severity}_severity"]["cues"],
            "suggested_drills": (drill_db or BATTING_DRILL_SUGGESTIONS).get("BALANCE_DRIFT", []),
        }

        return _attach_evidence_markers(finding, "balance_drift_score", evidence)

    return None


def _check_knee_collapse(
    metrics: dict,
    evidence: dict | None = None,
    drill_db: dict | None = None,
    analysis_mode: str = "batting",
) -> dict | None:
    """Check knee brace metric with mode-aware narratives."""
    knee_score = metrics.get("front_knee_brace_score", {}).get("score")

    if knee_score is None:
        return None

    if knee_score < THRESHOLDS["front_knee_brace_score"]:
        severity = _get_severity(knee_score, THRESHOLDS["front_knee_brace_score"])

        # Use mode-specific "why it matters" text
        why_it_matters = WHY_IT_MATTERS_BY_MODE.get("KNEE_COLLAPSE", {}).get(
            analysis_mode, FINDING_DEFINITIONS["KNEE_COLLAPSE"]["why_it_matters"]
        )

        # Get base cues from FINDING_DEFINITIONS
        base_cues = FINDING_DEFINITIONS["KNEE_COLLAPSE"][f"{severity}_severity"]["cues"]

        # Replace mode-specific high severity warning if applicable
        cues = base_cues.copy() if isinstance(base_cues, list) else list(base_cues)
        if severity == "high":
            mode_warning = HIGH_SEVERITY_WARNINGS_BY_MODE.get("KNEE_COLLAPSE", {}).get(
                analysis_mode
            )
            if mode_warning:
                # Replace batting-specific warning with mode-specific one
                cues = [mode_warning if "Suspend intensive batting" in c else c for c in cues]

        finding = {
            "code": "KNEE_COLLAPSE",
            "title": FINDING_DEFINITIONS["KNEE_COLLAPSE"]["title"],
            "severity": severity,
            "evidence": {
                "front_knee_brace_score": round(knee_score, 3),
                "threshold": THRESHOLDS["front_knee_brace_score"],
            },
            "why_it_matters": why_it_matters,
            "cues": cues,
            "suggested_drills": (drill_db or BATTING_DRILL_SUGGESTIONS).get("KNEE_COLLAPSE", []),
        }

        return _attach_evidence_markers(finding, "front_knee_brace_score", evidence)

    return None


def _check_rotation_timing(
    metrics: dict,
    evidence: dict | None = None,
    drill_db: dict | None = None,
    analysis_mode: str = "batting",
) -> dict | None:
    """Check hip-shoulder separation timing metric with mode-aware narratives."""
    timing_value = metrics.get("hip_shoulder_separation_timing")

    # Handle both direct float and nested dict format
    lag = timing_value.get("score") if isinstance(timing_value, dict) else timing_value

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

    # Use mode-specific "why it matters" text
    why_it_matters = WHY_IT_MATTERS_BY_MODE.get("ROTATION_TIMING", {}).get(
        analysis_mode, FINDING_DEFINITIONS["ROTATION_TIMING"]["why_it_matters"]
    )

    finding = {
        "code": "ROTATION_TIMING",
        "title": FINDING_DEFINITIONS["ROTATION_TIMING"]["title"],
        "severity": severity,
        "evidence": {
            "hip_shoulder_separation_lag_seconds": round(lag, 3),
            "target_lag_seconds": target,
        },
        "why_it_matters": why_it_matters,
        "cues": FINDING_DEFINITIONS["ROTATION_TIMING"][f"{severity}_severity"]["cues"],
        "suggested_drills": (drill_db or BATTING_DRILL_SUGGESTIONS).get("ROTATION_TIMING", []),
    }

    return _attach_evidence_markers(finding, "hip_shoulder_separation_timing", evidence)


def _check_elbow_drop(
    metrics: dict,
    evidence: dict | None = None,
    drill_db: dict | None = None,
    analysis_mode: str = "batting",
) -> dict | None:
    """Check elbow drop metric with mode-aware narratives."""
    elbow_score = metrics.get("elbow_drop_score", {}).get("score")

    if elbow_score is None:
        return None

    if elbow_score < THRESHOLDS["elbow_drop_score"]:
        severity = _get_severity(elbow_score, THRESHOLDS["elbow_drop_score"])

        # Use mode-specific "why it matters" text
        why_it_matters = WHY_IT_MATTERS_BY_MODE.get("ELBOW_DROP", {}).get(
            analysis_mode, FINDING_DEFINITIONS["ELBOW_DROP"]["why_it_matters"]
        )

        finding = {
            "code": "ELBOW_DROP",
            "title": FINDING_DEFINITIONS["ELBOW_DROP"]["title"],
            "severity": severity,
            "evidence": {
                "elbow_drop_score": round(elbow_score, 3),
                "threshold": THRESHOLDS["elbow_drop_score"],
            },
            "why_it_matters": why_it_matters,
            "cues": FINDING_DEFINITIONS["ELBOW_DROP"][f"{severity}_severity"]["cues"],
            "suggested_drills": (drill_db or BATTING_DRILL_SUGGESTIONS).get("ELBOW_DROP", []),
        }

        return _attach_evidence_markers(finding, "elbow_drop_score", evidence)

    return None

    return None


def _generate_ball_tracking_findings(ball_tracking: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate findings from ball tracking data for bowling analysis."""
    findings: list[dict[str, Any]] = []

    trajectory: dict[str, Any] = ball_tracking.get("trajectory", {})
    metrics_data: dict[str, Any] = ball_tracking.get("metrics", {})

    detection_rate: float = float(trajectory.get("detection_rate", 0))

    # Gating: Low detection rate (<40%)
    if detection_rate < 40:
        finding_def_insufficient: dict[str, Any] = cast(
            dict[str, Any], BOWLING_BALL_TRACKING_FINDINGS["INSUFFICIENT_BALL_TRACKING"]
        )
        findings.append(
            {
                "code": "INSUFFICIENT_BALL_TRACKING",
                "title": finding_def_insufficient["title"],
                "severity": "medium",
                "evidence": {
                    "detection_rate": f"{detection_rate:.1f}%",
                    "threshold": "40%",
                },
                "why_it_matters": finding_def_insufficient["why_it_matters"],
                "cues": finding_def_insufficient["cues"],
                "suggested_drills": finding_def_insufficient["drills"],
            }
        )
        # Suppress swing/length claims if detection is poor
        return findings

    # Release consistency analysis
    release_consistency: float = float(metrics_data.get("release_consistency", 100))
    if release_consistency < 85:
        severity = (
            "low"
            if release_consistency >= 70
            else ("medium" if release_consistency >= 50 else "high")
        )
        finding_def: dict[str, Any] = cast(
            dict[str, Any], BOWLING_BALL_TRACKING_FINDINGS["INCONSISTENT_RELEASE_POINT"]
        )
        findings.append(
            {
                "code": "INCONSISTENT_RELEASE_POINT",
                "title": finding_def["title"],
                "severity": severity,
                "evidence": {
                    "release_consistency_score": round(release_consistency, 1),
                    "threshold": 85.0,
                },
                "why_it_matters": finding_def["why_it_matters"],
                "cues": finding_def[f"{severity}_severity"]["cues"],
                "suggested_drills": BOWLING_DRILL_SUGGESTIONS.get(
                    "RELEASE_POINT",
                    [
                        "Rope drill with release point markers",
                        "Mirror work at gather position",
                        "Consistent stride length drills",
                    ],
                ),
            }
        )

    # Swing analysis (informational, only if tracking is reliable)
    if detection_rate >= 60:
        trajectory_curve: str = str(metrics_data.get("trajectory_curve", "straight"))
        swing_deviation: float = float(metrics_data.get("swing_deviation", 0))

        swing_def: dict[str, Any] = cast(
            dict[str, Any], BOWLING_BALL_TRACKING_FINDINGS["SWING_ANALYSIS"]
        )
        swing_message: str = str(
            swing_def["analysis"].get(trajectory_curve, f"Trajectory: {trajectory_curve}")
        )

        findings.append(
            {
                "code": "SWING_ANALYSIS",
                "title": swing_def["title"],
                "severity": "low",  # Informational
                "evidence": {
                    "trajectory_curve": trajectory_curve,
                    "swing_deviation": round(swing_deviation, 1),
                    "ball_speed_estimate": round(metrics_data.get("ball_speed_estimate", 0), 1),
                },
                "why_it_matters": swing_def["why_it_matters"],
                "cues": [swing_message],
                "suggested_drills": BOWLING_DRILL_SUGGESTIONS.get(
                    "SWING_VARIATION",
                    [
                        "Wrist position drills for swing control",
                        "Seam angle practice with video feedback",
                        "Shiny/rough side awareness drills",
                    ],
                ),
            }
        )

    return findings


# ============================================================================
# Main API
# ============================================================================


def generate_findings(
    metrics: dict[str, Any], context: dict[str, Any] | None = None, analysis_mode: str | None = None
) -> dict[str, Any]:
    """
    Generate rule-based coaching findings from metrics.

    Routes to mode-specific generator based on analysis_mode parameter.

    Args:
        metrics: Dict with metric scores from compute_pose_metrics()
                 Expected keys: head_stability_score, balance_drift_score, etc.
                 Can also include "evidence" dict with worst_frames/bad_segments
        context: Optional context dict for future extensibility
                (e.g., player level, session type, analysis_context, camera_view)
        analysis_mode: REQUIRED analysis mode (batting, bowling, wicketkeeping, fielding)

    Returns:
        {
            "overall_level": "low|medium|high",
            "findings": [
                {
                    "code": "HEAD_MOVEMENT|BALANCE_DRIFT|...",
                    "title": str,
                    "severity": "low|medium|high",
                    "evidence": {...},
                    "video_evidence": {
                        "worst_frames": [...],
                        "bad_segments": [...]
                    },
                    "why_it_matters": str,
                    "cues": [str, ...],
                    "suggested_drills": [str, ...]
                },
                ...
            ],
            "context": {...},  # echo back context if provided
            "detection_rate": float  # pose detection rate for reliability gating
        }
    """
    # CRITICAL: Enforce analysis_mode is present (no silent batting fallback)
    VALID_MODES = {"batting", "bowling", "wicketkeeping", "fielding"}
    if not analysis_mode or analysis_mode not in VALID_MODES:
        raise ValueError(
            f"analysis_mode is required and must be one of {VALID_MODES}. Got: {analysis_mode}"
        )

    # Route to mode-specific generator
    if analysis_mode == "batting":
        result = generate_batting_findings(metrics, context, analysis_mode)
    elif analysis_mode == "bowling":
        result = generate_bowling_findings(metrics, context, analysis_mode)
    elif analysis_mode == "wicketkeeping":
        result = generate_wicketkeeping_findings(metrics, context, analysis_mode)
    elif analysis_mode == "fielding":
        result = generate_fielding_findings(metrics, context, analysis_mode)
    else:
        # Should never reach here due to validation above, but defensive
        raise ValueError(f"Unexpected analysis_mode: {analysis_mode}")

    # Filter findings to only allowed codes for this mode
    result["findings"] = _filter_findings_by_mode(result["findings"], analysis_mode)

    return result


def generate_batting_findings(
    metrics: dict[str, Any], context: dict[str, Any] | None = None, analysis_mode: str = "batting"
) -> dict[str, Any]:
    """Generate batting-specific findings from metrics."""
    return _generate_findings_internal(metrics, context, BATTING_DRILL_SUGGESTIONS, analysis_mode)


def generate_bowling_findings(
    metrics: dict[str, Any], context: dict[str, Any] | None = None, analysis_mode: str = "bowling"
) -> dict[str, Any]:
    """Generate bowling-specific findings from metrics with ball tracking integration."""
    # Generate base pose findings
    base_findings = _generate_findings_internal(
        metrics, context, BOWLING_DRILL_SUGGESTIONS, analysis_mode
    )

    # Add ball tracking findings if available
    ball_tracking = metrics.get("ball_tracking")
    if ball_tracking and not ball_tracking.get("error"):
        ball_findings = _generate_ball_tracking_findings(ball_tracking)
        base_findings["findings"].extend(ball_findings)

    return base_findings


def generate_wicketkeeping_findings(
    metrics: dict[str, Any],
    context: dict[str, Any] | None = None,
    analysis_mode: str = "wicketkeeping",
) -> dict[str, Any]:
    """Generate wicketkeeping-specific findings from metrics."""
    return _generate_findings_internal(
        metrics, context, WICKETKEEPING_DRILL_SUGGESTIONS, analysis_mode
    )


def generate_fielding_findings(
    metrics: dict[str, Any], context: dict[str, Any] | None = None, analysis_mode: str = "fielding"
) -> dict[str, Any]:
    """Generate fielding-specific findings from metrics."""
    # Fielding uses same base checks but with fielding-specific drill suggestions
    # Could be expanded with fielding-specific metrics in the future
    return _generate_findings_internal(metrics, context, BATTING_DRILL_SUGGESTIONS, analysis_mode)


def _filter_findings_by_mode(findings: list[dict[str, Any]], mode: str) -> list[dict[str, Any]]:
    """
    Filter findings to only include codes allowed for the given analysis mode.

    Prevents cross-contamination (e.g., bowling codes appearing in batting analysis).

    Args:
        findings: List of finding dicts with "code" keys
        mode: Analysis mode (batting, bowling, wicketkeeping, fielding)

    Returns:
        Filtered list containing only allowed codes for this mode
    """
    allowed = ALLOWED_CODES_BY_MODE.get(mode, ALLOWED_CODES_BY_MODE["batting"])

    filtered = []
    for finding in findings:
        code = finding.get("code")
        if code in allowed:
            filtered.append(finding)
        else:
            logger.warning(f"Filtered out finding code '{code}' not allowed for mode '{mode}'")

    return filtered


def _generate_findings_internal(
    metrics: dict[str, Any],
    context: dict[str, Any] | None,
    drill_db: dict[str, list[str]],
    analysis_mode: str,
) -> dict[str, Any]:
    """
    Internal findings generator with mode-specific drill database and narratives.

    Args:
        metrics: Pose metrics result
        context: Optional context dict
        drill_db: Mode-specific drill suggestions dictionary
        analysis_mode: Analysis mode (batting, bowling, wicketkeeping, fielding)

    Returns:
        Findings result dictionary with mode-aware narratives
    """
    # Extract metrics from nested structure if needed
    metric_scores = metrics.get("metrics", metrics)
    evidence_data = metrics.get("evidence")  # Extract evidence markers
    logger.info(f"Generating findings for {len(metric_scores)} metrics (mode={analysis_mode})")

    # Calculate detection rate for reliability gating
    summary = metrics.get("summary", {})
    total_frames = summary.get("total_frames", 1)
    frames_with_pose = summary.get("frames_with_pose", 0)
    detection_rate = (frames_with_pose / total_frames * 100) if total_frames > 0 else 0
    logger.info(f"Pose detection rate: {detection_rate:.1f}%")

    # Check all conditions (passing evidence, drill_db, and mode to each)
    findings = []

    head_finding = _check_head_movement(metric_scores, evidence_data, drill_db, analysis_mode)
    if head_finding:
        findings.append(head_finding)

    balance_finding = _check_balance_drift(metric_scores, evidence_data, drill_db, analysis_mode)
    if balance_finding:
        findings.append(balance_finding)

    knee_finding = _check_knee_collapse(metric_scores, evidence_data, drill_db, analysis_mode)
    if knee_finding:
        findings.append(knee_finding)

    rotation_finding = _check_rotation_timing(metric_scores, evidence_data, drill_db, analysis_mode)
    if rotation_finding:
        findings.append(rotation_finding)

    elbow_finding = _check_elbow_drop(metric_scores, evidence_data, drill_db, analysis_mode)
    if elbow_finding:
        findings.append(elbow_finding)

    # Check for insufficient pose visibility across metrics
    zero_frame_metrics = sum(
        1
        for metric in metric_scores.values()
        if isinstance(metric, dict) and metric.get("num_frames", 0) == 0
    )

    if zero_frame_metrics > 2:
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
        "detection_rate": round(detection_rate, 1),  # For reliability gating
    }

    if context:
        result["context"] = context

    return result
