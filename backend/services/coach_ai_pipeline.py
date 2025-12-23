"""
Coach Pro Plus AI Pipeline - Pose Analysis & Rule-Based Findings

Orchestrates pose extraction and rule-based analysis.
Extensible for future ML metrics and LLM integration (not implemented in MVP).
"""

from __future__ import annotations

import logging
from typing import Any

from backend.services.pose_service import extract_pose_keypoints_from_video

logger = logging.getLogger(__name__)


def analyze_video_pose(
    video_path: str,
    sample_fps: int = 10,
    max_width: int = 640,
) -> dict[str, Any]:
    """
    Analyze video for pose and generate rule-based findings.

    Args:
        video_path: Path to video file
        sample_fps: Sampling rate
        max_width: Max frame width for downscaling

    Returns:
        Analysis result with pose data and findings:
        {
            "success": true,
            "pose_data": {...},
            "findings": {
                "frames_analyzed": 100,
                "detection_rate": 85.5,
                "key_joints": [...],
                ...
            },
            "error": null
        }
    """
    try:
        logger.info(f"Starting pose analysis for: {video_path}")

        # Extract pose keypoints
        pose_data = extract_pose_keypoints_from_video(
            video_path=video_path,
            sample_fps=sample_fps,
            max_width=max_width,
        )

        # Generate rule-based findings
        findings = _generate_findings(pose_data)

        return {
            "success": True,
            "pose_data": pose_data,
            "findings": findings,
            "error": None,
        }

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return {
            "success": False,
            "pose_data": None,
            "findings": None,
            "error": str(e),
        }
    except ValueError as e:
        logger.error(f"Video read error: {e}")
        return {
            "success": False,
            "pose_data": None,
            "findings": None,
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Unexpected error during pose analysis: {e}", exc_info=True)
        return {
            "success": False,
            "pose_data": None,
            "findings": None,
            "error": f"Unexpected error: {e!s}",
        }


def _generate_findings(pose_data: dict[str, Any]) -> dict[str, Any]:
    """
    Generate rule-based findings from pose data.

    Current MVP rules:
    - Detection rate (% frames with pose)
    - Key joints present (shoulders, elbows, wrists, hips, knees, ankles)
    - Upper body posture insights

    Future: ML metrics, batting stance analysis, swing patterns, etc.
    """
    frames = pose_data.get("frames", [])
    detected_frames = [f for f in frames if f.get("pose_detected", False)]
    detection_rate = pose_data.get("detection_rate_percent", 0.0)

    findings: dict[str, Any] = {
        "frames_analyzed": len(frames),
        "frames_detected": len(detected_frames),
        "detection_rate": detection_rate,
        "key_joints_tracked": _analyze_key_joints(detected_frames),
        "posture_insights": _analyze_posture(detected_frames),
    }

    return findings


def _analyze_key_joints(detected_frames: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze which key joints are consistently tracked."""
    if not detected_frames:
        return {
            "shoulders": 0.0,
            "elbows": 0.0,
            "wrists": 0.0,
            "hips": 0.0,
            "knees": 0.0,
            "ankles": 0.0,
        }

    joints = {
        "shoulders": ["left_shoulder", "right_shoulder"],
        "elbows": ["left_elbow", "right_elbow"],
        "wrists": ["left_wrist", "right_wrist"],
        "hips": ["left_hip", "right_hip"],
        "knees": ["left_knee", "right_knee"],
        "ankles": ["left_ankle", "right_ankle"],
    }

    result = {}
    for joint_name, keypoint_names in joints.items():
        count = 0
        for frame in detected_frames:
            keypoints = frame.get("keypoints", {})
            # Check if both joints in pair are detected with good confidence
            if all(
                kp in keypoints and keypoints[kp][2] > 0.5 for kp in keypoint_names
            ):
                count += 1

        result[joint_name] = (count / len(detected_frames) * 100) if detected_frames else 0.0

    return result


def _analyze_posture(detected_frames: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze posture characteristics (MVP rule-based)."""
    if not detected_frames:
        return {
            "avg_shoulder_height_consistency": 0.0,
            "notes": "No frames with pose detected",
        }

    shoulder_heights = []
    for frame in detected_frames:
        keypoints = frame.get("keypoints", {})
        left_shoulder = keypoints.get("left_shoulder")
        right_shoulder = keypoints.get("right_shoulder")

        if left_shoulder and right_shoulder:
            # Y is normalized [0, 1], lower values = higher in image
            left_h = left_shoulder[1]
            right_h = right_shoulder[1]
            avg_h = (left_h + right_h) / 2.0
            shoulder_heights.append(avg_h)

    if shoulder_heights:
        # Calculate variance (lower = more consistent)
        mean_h = sum(shoulder_heights) / len(shoulder_heights)
        variance = sum((h - mean_h) ** 2 for h in shoulder_heights) / len(shoulder_heights)
        consistency = max(0, 100 - (variance * 100))  # 0-100 scale
    else:
        consistency = 0.0

    return {
        "avg_shoulder_height_consistency": round(consistency, 2),
        "notes": "Rule-based MVP: More metrics (swing angle, bat speed, etc.) coming soon",
    }
