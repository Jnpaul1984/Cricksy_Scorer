from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast

from backend.config import settings
from backend.services.batting_v2_metric_pack import attach_batting_v2_metric_pack
from backend.services.bowling_v2_metric_pack import attach_bowling_v2_metric_pack
from backend.services.coach_analysis_v2_compatibility import build_analysis_v2_contract
from backend.services.coach_findings import generate_findings
from backend.services.coach_report_service import generate_report_text
from backend.services.coach_strength_consistency import attach_strength_consistency_engine
from backend.services.fielding_v2_metric_pack import attach_fielding_v2_metric_pack
from backend.services.phase_recognition import attach_phase_recognition
from backend.services.pose_metrics import build_pose_metric_evidence, compute_pose_metrics
from backend.services.repetition_segmentation import attach_repetition_segmentation
from backend.services.wicketkeeping_v2_metric_pack import attach_wicketkeeping_v2_metric_pack

logger = logging.getLogger(__name__)


def extract_pose_keypoints_from_video(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from backend.services.pose_service import extract_pose_keypoints_from_video as _extract

    return cast(dict[str, Any], _extract(*args, **kwargs))


def extract_pose_landmarks(
    *,
    video_path: str,
    sample_fps: float,
    max_width: int = 640,
    max_seconds: float | None = None,
) -> list[dict[str, Any]]:
    """Extract raw pose landmarks from video (for GPU chunk processing).

    Returns only the pose landmark data without metrics/findings/report.
    Used by GPU workers to extract poses for individual chunks.

    Args:
        video_path: Path to video file
        sample_fps: Target sampling rate
        max_width: Max video width for processing
        max_seconds: Max duration to process

    Returns:
        List of pose frames with landmarks
    """
    pose_data = extract_pose_keypoints_from_video(
        video_path=video_path,
        sample_fps=sample_fps,
        max_width=max_width,
        max_seconds=max_seconds,
    )

    # Return frames with pose landmarks
    frames = (
        pose_data.get("frames")
        or pose_data.get("frames_data")
        or pose_data.get("pose_frames")
        or []
    )

    if not isinstance(frames, list):
        logger.warning(f"Unexpected frames format: {type(frames)}")
        return []

    return frames


@dataclass(frozen=True)
class AnalysisArtifacts:
    results: dict[str, Any]
    frames: list[dict[str, Any]] | None


def _normalize_pose_data(data: dict[str, Any]) -> dict[str, Any]:
    """Extract key summary fields from pose_service output supporting multiple schema versions."""
    total_frames = (
        data.get("total_frames")
        or data.get("pose_summary", {}).get("frame_count")
        or data.get("metrics", {}).get("frame_count")
    )
    if total_frames is None:
        raise ValueError("Could not find total_frames in pose data")

    sampled_frames = (
        data.get("sampled_frames")
        or data.get("pose_summary", {}).get("sampled_frame_count")
        or data.get("metrics", {}).get("sampled_frame_count")
    )
    if sampled_frames is None:
        raise ValueError("Could not find sampled_frames in pose data")

    frames_with_pose = data.get("frames_with_pose") or data.get("detected_frames")
    if frames_with_pose is None:
        raise ValueError("Could not find frames_with_pose/detected_frames in pose data")

    detection_rate_percent = (
        data.get("detection_rate_percent")
        or data.get("pose_summary", {}).get("detection_rate")
        or data.get("metrics", {}).get("detection_rate")
    )
    if detection_rate_percent is None:
        detection_rate_percent = (
            (frames_with_pose / sampled_frames * 100) if sampled_frames > 0 else 0
        )

    video_fps = data.get("video_fps") or data.get("fps") or 30.0
    model = data.get("model") or "MediaPipe Pose Landmarker Full"

    return {
        "total_frames": int(total_frames),
        "sampled_frames": int(sampled_frames),
        "frames_with_pose": int(frames_with_pose),
        "detection_rate_percent": float(detection_rate_percent),
        "video_fps": float(video_fps),
        "model": str(model),
    }


def run_pose_metrics_findings_report(
    *,
    video_path: str,
    sample_fps: float,
    include_frames: bool,
    max_width: int = 640,
    max_seconds: float | None = None,
    player_context: dict[str, Any] | None = None,
    analysis_mode: str | None = None,
    session_id: str | None = None,
    job_id: str | None = None,
) -> AnalysisArtifacts:
    """Shared analysis pipeline used by the background worker.

    Returns lightweight results dict plus optional frames payload.

    Args:
        analysis_mode: REQUIRED analysis mode (batting, bowling, wicketkeeping, fielding).
                      Determines which findings/drills are generated.
    """
    # Validate analysis_mode is present and valid
    VALID_MODES = {"batting", "bowling", "wicketkeeping", "fielding"}
    if not analysis_mode or analysis_mode not in VALID_MODES:
        raise ValueError(f"Invalid analysis_mode: {analysis_mode}. Must be one of {VALID_MODES}")

    pose_data = extract_pose_keypoints_from_video(
        video_path=video_path,
        sample_fps=sample_fps,
        max_width=max_width,
        max_seconds=max_seconds,
    )

    normalized = _normalize_pose_data(pose_data)

    pose_payload_for_metrics = {
        **pose_data,
        "total_frames": normalized["total_frames"],
        "sampled_frames": normalized["sampled_frames"],
        "frames_with_pose": normalized["frames_with_pose"],
        "detection_rate_percent": normalized["detection_rate_percent"],
        "video_fps": normalized["video_fps"],
        "model": normalized["model"],
        "summary": {
            "total_frames": normalized["total_frames"],
            "sampled_frames": normalized["sampled_frames"],
            "frames_with_pose": normalized["frames_with_pose"],
            "detection_rate_percent": normalized["detection_rate_percent"],
            "video_fps": normalized["video_fps"],
            "model": normalized["model"],
        },
    }

    metrics_result = compute_pose_metrics(pose_payload_for_metrics)

    try:
        evidence = build_pose_metric_evidence(pose_payload_for_metrics, metrics_result)
        metrics_result.setdefault("evidence", evidence)
    except Exception:
        logger.exception("Failed to compute evidence markers")

    metrics_result.setdefault("total_frames", normalized["total_frames"])
    metrics_result.setdefault("sampled_frames", normalized["sampled_frames"])
    metrics_result.setdefault("frames_with_pose", normalized["frames_with_pose"])
    metrics_result.setdefault("detection_rate_percent", normalized["detection_rate_percent"])
    metrics_result.setdefault("video_fps", normalized["video_fps"])
    metrics_result.setdefault("model", normalized["model"])

    # Pass analysis_mode to findings generation
    findings_result = generate_findings(metrics_result, analysis_mode=analysis_mode)
    report_result = cast(dict[str, Any], generate_report_text(findings_result, player_context))
    v2_contract = build_analysis_v2_contract(
        discipline=analysis_mode,
        sample_fps=float(sample_fps),
        source_video_fps=normalized["video_fps"],
        camera_view=(
            str(player_context.get("camera_view"))
            if isinstance(player_context, dict) and player_context.get("camera_view") is not None
            else None
        ),
        source_model=normalized["model"],
        metrics_payload=metrics_result,
    )

    frames_out: list[dict[str, Any]] | None = None
    if include_frames:
        frames_out = (
            pose_data.get("frames") or pose_data.get("frames_data") or pose_data.get("pose_frames")
        )
        if not isinstance(frames_out, list):
            frames_out = None

    results: dict[str, Any] = {
        "pose_summary": {
            "total_frames": normalized["total_frames"],
            "sampled_frames": normalized["sampled_frames"],
            "frames_with_pose": normalized["frames_with_pose"],
            "detection_rate_percent": normalized["detection_rate_percent"],
            "video_fps": normalized["video_fps"],
            "model": normalized["model"],
        },
        "metrics": metrics_result,
        "findings": findings_result,
        "report": report_result,
        "meta": {
            "sample_fps": float(sample_fps),
            "max_seconds": float(max_seconds) if max_seconds is not None else None,
            "analysis_mode": analysis_mode,
            "analysis_mode_used": analysis_mode,  # Explicit confirmation for frontend
            "session_discipline": (
                str(player_context.get("session_discipline"))
                if isinstance(player_context, dict)
                and player_context.get("session_discipline") is not None
                else None
            ),
        },
        "v2": v2_contract.model_dump(mode="json"),
    }

    frames_for_segmentation = (
        pose_data.get("frames")
        or pose_data.get("frames_data")
        or pose_data.get("pose_frames")
        or []
    )
    metric_refs = [
        str(metric_id)
        for metric_id, raw_metric in metrics_result.get("metrics", {}).items()
        if isinstance(raw_metric, dict)
    ]
    attach_repetition_segmentation(
        results_payload=results,
        discipline=analysis_mode,
        frames=frames_for_segmentation if isinstance(frames_for_segmentation, list) else [],
        session_id=session_id,
        job_id=job_id,
        sample_fps=float(sample_fps),
        source_video_fps=normalized["video_fps"],
        camera_view=(
            str(player_context.get("camera_view"))
            if isinstance(player_context, dict) and player_context.get("camera_view") is not None
            else None
        ),
        metric_refs=metric_refs,
        enabled=bool(settings.COACH_PLUS_REPETITION_SEGMENTATION_ENABLED),
    )
    attach_phase_recognition(
        results_payload=results,
        discipline=analysis_mode,
        sample_fps=float(sample_fps),
        source_video_fps=normalized["video_fps"],
        camera_view=(
            str(player_context.get("camera_view"))
            if isinstance(player_context, dict) and player_context.get("camera_view") is not None
            else None
        ),
        session_discipline=(
            str(player_context.get("session_discipline"))
            if isinstance(player_context, dict)
            and player_context.get("session_discipline") is not None
            else None
        ),
        enabled=bool(settings.COACH_PLUS_PHASE_RECOGNITION_ENABLED),
    )
    attach_batting_v2_metric_pack(
        results_payload=results,
        discipline=analysis_mode,
        frames=frames_for_segmentation if isinstance(frames_for_segmentation, list) else [],
        sample_fps=float(sample_fps),
        source_video_fps=normalized["video_fps"],
        camera_view=(
            str(player_context.get("camera_view"))
            if isinstance(player_context, dict) and player_context.get("camera_view") is not None
            else None
        ),
        source_model=normalized["model"],
    )
    attach_bowling_v2_metric_pack(
        results_payload=results,
        discipline=analysis_mode,
        session_discipline=(
            str(player_context.get("session_discipline"))
            if isinstance(player_context, dict)
            and player_context.get("session_discipline") is not None
            else None
        ),
        frames=frames_for_segmentation if isinstance(frames_for_segmentation, list) else [],
        sample_fps=float(sample_fps),
        source_video_fps=normalized["video_fps"],
        camera_view=(
            str(player_context.get("camera_view"))
            if isinstance(player_context, dict) and player_context.get("camera_view") is not None
            else None
        ),
        source_model=normalized["model"],
    )
    attach_wicketkeeping_v2_metric_pack(
        results_payload=results,
        discipline=analysis_mode,
        frames=frames_for_segmentation if isinstance(frames_for_segmentation, list) else [],
        sample_fps=float(sample_fps),
        source_video_fps=normalized["video_fps"],
        camera_view=(
            str(player_context.get("camera_view"))
            if isinstance(player_context, dict) and player_context.get("camera_view") is not None
            else None
        ),
        source_model=normalized["model"],
    )
    attach_fielding_v2_metric_pack(
        results_payload=results,
        discipline=analysis_mode,
        frames=frames_for_segmentation if isinstance(frames_for_segmentation, list) else [],
        sample_fps=float(sample_fps),
        source_video_fps=normalized["video_fps"],
        camera_view=(
            str(player_context.get("camera_view"))
            if isinstance(player_context, dict) and player_context.get("camera_view") is not None
            else None
        ),
        source_model=normalized["model"],
    )
    attach_strength_consistency_engine(results)

    return AnalysisArtifacts(results=results, frames=frames_out)
