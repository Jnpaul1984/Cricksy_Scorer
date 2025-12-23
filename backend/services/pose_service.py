"""
Pose Extraction Service - Coach Pro Plus Video Analysis

Extracts pose keypoints from video using MediaPipe Tasks Vision API.
Uses mediapipe_init module for proper model loading with fail-fast error handling.

No fallbacks, no stubs - raises clear errors if MediaPipe is not properly initialized.
"""

from __future__ import annotations

import logging
import numpy as np
from pathlib import Path
from typing import Any

import cv2
import mediapipe as mp
from backend.mediapipe_init import (
    get_pose_landmarker,
    get_model_path,
    get_detection_method_name,
)

logger = logging.getLogger(__name__)


# MediaPipe Pose Landmarker outputs 33 keypoints
KEYPOINT_NAMES = [
    "nose",
    "left_eye_inner",
    "left_eye",
    "left_eye_outer",
    "right_eye_inner",
    "right_eye",
    "right_eye_outer",
    "left_ear",
    "right_ear",
    "mouth_left",
    "mouth_right",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_pinky",
    "right_pinky",
    "left_index",
    "right_index",
    "left_thumb",
    "right_thumb",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
]


def extract_pose_keypoints_from_video(
    video_path: str,
    sample_fps: float = 2.0,
    max_width: int = 640,
) -> dict[str, Any]:
    """Extract pose keypoints from a video file using MediaPipe Tasks Vision API.

    MediaPipe Pose Landmarker detects 33 keypoints per frame (nose, shoulders,
    elbows, wrists, hips, knees, ankles, and facial landmarks). Each keypoint
    has x, y, z coordinates and visibility score.

    Args:
        video_path: Path to video file (e.g., "/videos/coaching_angle.mp4")
        sample_fps: Target frames per second for sampling (default 2.0 = 1 frame every 0.5 sec)
        max_width: Maximum frame width for processing (default 640 for efficiency)

    Returns:
        dict with keys:
            - "pose_summary": {frame_count, sampled_frame_count, detection_rate}
            - "frames": [{"frame_num", "timestamp", "landmarks": [...], "detected": bool}]
            - "metrics": {mean_visibility, max_visibility, min_visibility}
            - "findings": [str] - list of pose quality findings
            - "report": str - human-readable summary

    Raises:
        FileNotFoundError: If video file doesn't exist
        ValueError: If video cannot be read or has no frames
        RuntimeError: If MediaPipe model is not initialized or available
    """
    if isinstance(video_path, str):
        video_path = Path(video_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    logger.info(f"Extracting pose from video: {video_path}")

    # Get MediaPipe detector - fails loudly if model is missing
    try:
        detector = get_pose_landmarker()
    except Exception as e:
        logger.error(f"Failed to get MediaPipe detector: {e}")
        raise RuntimeError(
            f"MediaPipe model not initialized. Model path: {get_model_path()}. "
            f"Error: {e}"
        ) from e

    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    if total_frames == 0 or fps == 0:
        cap.release()
        raise ValueError(f"Invalid video: {total_frames} frames, {fps} fps")

    logger.info(f"Video: {total_frames} frames @ {fps}fps, {width}x{height}")

    # Determine detection method based on running mode
    detection_method = get_detection_method_name()
    logger.info(f"Using MediaPipe detection method: {detection_method}")
    
    # Check for unsupported modes
    if detection_method == "detect_async":
        cap.release()
        raise RuntimeError(
            "LIVE_STREAM mode is not supported for offline video file processing. "
            "LIVE_STREAM requires a callback pipeline for real-time streaming. "
            "Set MEDIAPIPE_RUNNING_MODE to 'VIDEO' or 'IMAGE' for video file analysis."
        )

    # Calculate frame sampling
    frame_interval = max(1, int(fps / sample_fps))
    target_width = min(width, max_width)
    scale = target_width / width if width > 0 else 1.0
    target_height = int(height * scale)

    frames_data = []
    detected_count = 0
    visibility_scores = []

    frame_num = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # Sample frames at specified interval
            if frame_num % frame_interval == 0:
                timestamp = frame_num / fps

                # Resize for efficiency
                if scale < 1.0:
                    frame = cv2.resize(frame, (target_width, target_height))

                # Convert BGR to RGB for MediaPipe
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Ensure uint8 and contiguous
                if rgb_frame.dtype != np.uint8:
                    rgb_frame = rgb_frame.astype(np.uint8)
                rgb_frame = np.ascontiguousarray(rgb_frame)

                # Create MediaPipe Image
                try:
                    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                    timestamp_ms = int((frame_num / fps) * 1000)  # Monotonic timestamp
                    
                    # Call appropriate detection method based on running mode
                    if detection_method == "detect_for_video":
                        detection_result = detector.detect_for_video(mp_image, timestamp_ms)
                    elif detection_method == "detect":
                        detection_result = detector.detect(mp_image)
                    else:
                        # Should not reach here (checked earlier), but be defensive
                        raise RuntimeError(f"Unsupported detection method: {detection_method}")
                except Exception as e:
                    logger.warning(f"Detection failed for frame {frame_num}: {e}")
                    frames_data.append({
                        "frame_num": frame_num,
                        "timestamp": round(timestamp, 3),
                        "detected": False,
                        "landmarks": None,
                        "keypoints": None
                    })
                    frame_num += 1
                    continue

                frame_detected = False
                frame_landmarks = None
                frame_keypoints: dict | None = None

                # Extract landmarks from first detected pose
                if (detection_result and 
                    hasattr(detection_result, 'pose_landmarks') and
                    detection_result.pose_landmarks):
                    
                    landmarks_list = detection_result.pose_landmarks
                    if landmarks_list and len(landmarks_list) > 0:
                        frame_detected = True
                        landmarks = landmarks_list[0]  # First person
                        
                        frame_landmarks = []
                        frame_keypoints = {}  # Dictionary mapping keypoint names to landmarks
                        for i, landmark in enumerate(landmarks):
                            landmark_dict = {
                                "x": float(landmark.x),
                                "y": float(landmark.y),
                                "z": float(landmark.z),
                                "visibility": float(landmark.visibility)
                            }
                            frame_landmarks.append(landmark_dict)
                            
                            # Add to keypoints dictionary if we have a name for this index
                            if i < len(KEYPOINT_NAMES):
                                frame_keypoints[KEYPOINT_NAMES[i]] = landmark_dict
                            
                            visibility_scores.append(landmark.visibility)
                        
                        detected_count += 1

                # Normalize nulls to safe defaults
                if frame_keypoints is None:
                    frame_keypoints = {}

                frame_data = {
                    "frame_num": frame_num,
                    "timestamp": round(timestamp, 3),
                    "t": round(timestamp, 3),
                    "timestamp_ms": int(timestamp_ms),
                    "frame_index": frame_num,
                    "detected": bool(frame_detected),
                    "landmarks": frame_landmarks,
                    "keypoints": frame_keypoints,
                }
                frames_data.append(frame_data)

            frame_num += 1

    finally:
        cap.release()

    # Calculate metrics
    sampled_count = len(frames_data)
    detection_rate = (detected_count / sampled_count * 100) if sampled_count > 0 else 0

    metrics = {
        "frame_count": total_frames,
        "sampled_frame_count": sampled_count,
        "detection_rate": round(detection_rate, 1)
    }

    if visibility_scores:
        metrics.update({
            "mean_visibility": round(np.mean(visibility_scores), 3),
            "max_visibility": round(np.max(visibility_scores), 3),
            "min_visibility": round(np.min(visibility_scores), 3)
        })

    # Generate findings
    findings = []
    if detection_rate < 50:
        findings.append(
            f"Low detection rate ({detection_rate:.1f}%) - ensure good lighting "
            "and camera angle"
        )
    if visibility_scores and np.mean(visibility_scores) < 0.7:
        avg_vis = np.mean(visibility_scores)
        findings.append(
            f"Low confidence landmarks (avg visibility {avg_vis:.2f}) - "
            "may need closer camera angle"
        )
    if sampled_count < 10:
        findings.append(
            f"Very few frames sampled ({sampled_count}) - use higher sample_fps "
            "for more detail"
        )

    report = (
        f"Analyzed {total_frames} frames ({sampled_count} sampled) from "
        f"{video_path.name}. Detected pose in {detected_count} frames "
        f"({detection_rate:.1f}% detection rate)."
    )
    if findings:
        report += f" Notes: {'; '.join(findings)}"

    logger.info(
        f"Pose extraction complete: {sampled_count} frames, "
        f"{detection_rate:.1f}% detection rate"
    )

    return {
        # Primary response structure
        "pose_summary": metrics,
        "frames": frames_data,
        "frames_data": frames_data,  # Alias for backward compatibility
        "metrics": metrics,
        "findings": findings,
        "report": report,
        # Backwards-compatible alias keys for API clients
        "total_frames": total_frames,
        "fps": fps,
        "sampled_frames": sampled_count,
        "detected_frames": detected_count,
    }
