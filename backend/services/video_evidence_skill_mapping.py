from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Any

from backend.domain.player_development_skill_contract import PLAYER_DEVELOPMENT_SKILL_REGISTRY
from backend.sql_app.models import VideoAnalysisJob, VideoSession

MAX_EVIDENCE_MARKERS = 10
_COMPLETED_STATUSES = {"completed", "done"}


class VideoEvidenceSkillMappingError(ValueError):
    """Controlled validation error for video evidence -> skill input mapping."""


class VideoEvidenceSkillInputInsufficientDataError(VideoEvidenceSkillMappingError):
    """Raised when no valid timestamped evidence markers are available."""


@dataclass(frozen=True, slots=True)
class _EvidenceSource:
    name: str
    payload: dict[str, Any] | None


def build_coaching_video_evidence_skill_input(
    *,
    player_profile_id: str,
    coach_user_id: str,
    org_id: str | None,
    video_session: VideoSession,
    video_analysis_job: VideoAnalysisJob,
) -> dict[str, object]:
    _validate_context(
        player_profile_id=player_profile_id,
        coach_user_id=coach_user_id,
        video_session=video_session,
        video_analysis_job=video_analysis_job,
    )
    _validate_job_ready(video_session=video_session, video_analysis_job=video_analysis_job)

    markers = _extract_markers_prefer_deep(video_analysis_job)
    if not markers:
        raise VideoEvidenceSkillInputInsufficientDataError(
            "No valid timestamped video evidence markers were available."
        )

    analysis_mode = str(video_analysis_job.analysis_mode).strip()
    payload: dict[str, object] = {
        "player_profile_id": player_profile_id,
        "coach_user_id": coach_user_id,
        "org_id": org_id,
        "video_session_id": video_session.id,
        "video_analysis_job_id": video_analysis_job.id,
        "analysis_mode": analysis_mode,
        "evidence_markers": markers[:MAX_EVIDENCE_MARKERS],
    }
    _validate_output_contract(payload)
    return payload


def _validate_context(
    *,
    player_profile_id: str,
    coach_user_id: str,
    video_session: VideoSession,
    video_analysis_job: VideoAnalysisJob,
) -> None:
    if not player_profile_id.strip():
        raise VideoEvidenceSkillMappingError("Missing required context field: player_profile_id")
    if not coach_user_id.strip():
        raise VideoEvidenceSkillMappingError("Missing required context field: coach_user_id")
    if not video_session.id:
        raise VideoEvidenceSkillMappingError("Missing required context field: video_session.id")
    if not video_analysis_job.id:
        raise VideoEvidenceSkillMappingError("Missing required context field: video_analysis_job.id")


def _validate_job_ready(*, video_session: VideoSession, video_analysis_job: VideoAnalysisJob) -> None:
    status_value = str(getattr(video_analysis_job.status, "value", video_analysis_job.status)).strip()
    if status_value not in _COMPLETED_STATUSES:
        raise VideoEvidenceSkillMappingError(
            f"Video analysis job must be completed/done. Received status='{status_value}'."
        )
    if video_analysis_job.session_id != video_session.id:
        raise VideoEvidenceSkillMappingError("VideoAnalysisJob.session_id must match VideoSession.id.")
    analysis_mode = str(video_analysis_job.analysis_mode or "").strip()
    if not analysis_mode:
        raise VideoEvidenceSkillMappingError("Video analysis job is missing required analysis_mode.")


def _extract_markers_prefer_deep(video_analysis_job: VideoAnalysisJob) -> list[dict[str, object]]:
    sources = (
        _EvidenceSource("deep_results", _as_dict(video_analysis_job.deep_results)),
        _EvidenceSource("quick_results", _as_dict(video_analysis_job.quick_results)),
        _EvidenceSource("results", _as_dict(video_analysis_job.results)),
        _EvidenceSource("deep_findings", _as_dict(video_analysis_job.deep_findings)),
        _EvidenceSource("quick_findings", _as_dict(video_analysis_job.quick_findings)),
    )

    for source in sources:
        if source.payload is None:
            continue
        markers = _extract_markers_from_source(source.name, source.payload)
        if markers:
            return sorted(markers, key=_marker_sort_key)
    return []


def _extract_markers_from_source(source_name: str, payload: dict[str, Any]) -> list[dict[str, object]]:
    markers: list[dict[str, object]] = []
    raw_evidence = _extract_raw_evidence_payload(payload, source_name=source_name)
    if raw_evidence is not None:
        markers.extend(_extract_markers_from_raw_evidence(raw_evidence, source_name=source_name))
    markers.extend(_extract_markers_from_findings(payload, source_name=source_name))
    return markers


def _extract_raw_evidence_payload(
    payload: dict[str, Any], *, source_name: str
) -> dict[str, Any] | list[dict[str, Any]] | None:
    candidate_paths: tuple[tuple[str, ...], ...] = (
        ("evidence",),
        ("metrics", "evidence"),
        ("coach", "evidence"),
        ("coach", "metrics", "evidence"),
    )
    for path in candidate_paths:
        present, candidate = _get_nested(payload, path)
        if not present:
            continue
        if isinstance(candidate, dict):
            return candidate
        if isinstance(candidate, list) and all(isinstance(item, dict) for item in candidate):
            return candidate
        joined = ".".join(path)
        raise VideoEvidenceSkillMappingError(
            f"Malformed evidence structure at {source_name}.{joined}; expected dict or list[dict]."
        )
    return None


def _extract_markers_from_raw_evidence(
    evidence: dict[str, Any] | list[dict[str, Any]],
    *,
    source_name: str,
) -> list[dict[str, object]]:
    if isinstance(evidence, list):
        return _extract_markers_from_marker_list(evidence)

    markers: list[dict[str, object]] = []
    for metric_name, metric_payload in evidence.items():
        if not isinstance(metric_payload, dict):
            raise VideoEvidenceSkillMappingError(
                f"Malformed evidence metric '{metric_name}' in {source_name}; expected object."
            )
        threshold = _to_float(metric_payload.get("threshold"))
        finding_label = _to_label(metric_payload.get("finding_label")) or str(metric_name)
        markers.extend(
            _extract_metric_markers(
                metric_name=str(metric_name),
                finding_label=finding_label,
                threshold=threshold,
                metric_payload=metric_payload,
            )
        )
    return markers


def _extract_metric_markers(
    *,
    metric_name: str,
    finding_label: str,
    threshold: float | None,
    metric_payload: dict[str, Any],
) -> list[dict[str, object]]:
    markers: list[dict[str, object]] = []

    worst_frames = metric_payload.get("worst_frames")
    if worst_frames is not None:
        if not isinstance(worst_frames, list) or not all(isinstance(item, dict) for item in worst_frames):
            raise VideoEvidenceSkillMappingError("Malformed worst_frames evidence payload.")
        for frame in worst_frames:
            marker = _marker_from_item(
                metric_name=metric_name,
                finding_label=_to_label(frame.get("finding_label")) or finding_label,
                timestamp_value=frame.get("timestamp_s"),
                frame_num_value=frame.get("frame_num", frame.get("frame")),
                score_value=frame.get("score"),
                threshold_value=frame.get("threshold", threshold),
            )
            if marker is not None:
                markers.append(marker)

    bad_segments = metric_payload.get("bad_segments")
    if bad_segments is not None:
        if not isinstance(bad_segments, list) or not all(isinstance(item, dict) for item in bad_segments):
            raise VideoEvidenceSkillMappingError("Malformed bad_segments evidence payload.")
        for segment in bad_segments:
            marker = _marker_from_item(
                metric_name=metric_name,
                finding_label=_to_label(segment.get("finding_label")) or finding_label,
                timestamp_value=segment.get("start_timestamp_s", segment.get("timestamp_s")),
                frame_num_value=segment.get("start_frame", segment.get("frame_num")),
                score_value=segment.get("min_score", segment.get("score")),
                threshold_value=segment.get("threshold", threshold),
            )
            if marker is not None:
                markers.append(marker)

    for marker_list_key in ("frames", "frame_markers", "markers"):
        frame_markers = metric_payload.get(marker_list_key)
        if frame_markers is None:
            continue
        if not isinstance(frame_markers, list) or not all(
            isinstance(item, dict) for item in frame_markers
        ):
            raise VideoEvidenceSkillMappingError("Malformed frame-level evidence payload.")
        for frame_marker in frame_markers:
            marker = _marker_from_item(
                metric_name=metric_name,
                finding_label=_to_label(frame_marker.get("finding_label")) or finding_label,
                timestamp_value=frame_marker.get("timestamp_s"),
                frame_num_value=frame_marker.get("frame_num", frame_marker.get("frame")),
                score_value=frame_marker.get("score"),
                threshold_value=frame_marker.get("threshold", threshold),
            )
            if marker is not None:
                markers.append(marker)
    return markers


def _extract_markers_from_marker_list(markers_payload: list[dict[str, Any]]) -> list[dict[str, object]]:
    markers: list[dict[str, object]] = []
    for item in markers_payload:
        metric_name = _to_label(item.get("metric_name", item.get("metric", item.get("name"))))
        finding_label = _to_label(
            item.get("finding_label", item.get("label", item.get("title", metric_name)))
        )
        if not metric_name or not finding_label:
            continue
        marker = _marker_from_item(
            metric_name=metric_name,
            finding_label=finding_label,
            timestamp_value=item.get("timestamp_s", item.get("start_timestamp_s")),
            frame_num_value=item.get("frame_num", item.get("frame", item.get("start_frame"))),
            score_value=item.get("score", item.get("min_score")),
            threshold_value=item.get("threshold"),
        )
        if marker is not None:
            markers.append(marker)
    return markers


def _extract_markers_from_findings(
    payload: dict[str, Any], *, source_name: str
) -> list[dict[str, object]]:
    findings_payload = payload.get("findings", payload)
    findings_list: Any = findings_payload.get("findings") if isinstance(findings_payload, dict) else None
    if findings_list is None:
        return []
    if not isinstance(findings_list, list) or not all(isinstance(item, dict) for item in findings_list):
        raise VideoEvidenceSkillMappingError(
            f"Malformed findings structure in {source_name}; expected list[dict]."
        )

    markers: list[dict[str, object]] = []
    for finding in findings_list:
        finding_label = _to_label(finding.get("title", finding.get("code"))) or "finding"
        evidence_block = finding.get("evidence")
        threshold = (
            _to_float(evidence_block.get("threshold")) if isinstance(evidence_block, dict) else None
        )
        metric_name = _metric_name_from_finding(finding, finding_label)
        video_evidence = finding.get("video_evidence")
        if not isinstance(video_evidence, dict):
            continue
        markers.extend(
            _extract_metric_markers(
                metric_name=metric_name,
                finding_label=finding_label,
                threshold=threshold,
                metric_payload=video_evidence,
            )
        )
    return markers


def _metric_name_from_finding(finding: dict[str, Any], fallback: str) -> str:
    evidence = finding.get("evidence")
    if not isinstance(evidence, dict):
        return fallback
    for key, value in evidence.items():
        if key in {"threshold", "target_lag_seconds", "target"}:
            continue
        if isinstance(value, Real):
            return str(key)
    return fallback


def _marker_from_item(
    *,
    metric_name: str,
    finding_label: str,
    timestamp_value: Any,
    frame_num_value: Any,
    score_value: Any,
    threshold_value: Any,
) -> dict[str, object] | None:
    timestamp = _to_float(timestamp_value)
    if timestamp is None:
        return None
    frame_num = _to_int(frame_num_value)
    score = _to_float(score_value)
    threshold = _to_float(threshold_value)
    return {
        "metric_name": metric_name,
        "timestamp_s": timestamp,
        "frame_num": frame_num,
        "score": score,
        "threshold": threshold,
        "finding_label": finding_label,
    }


def _validate_output_contract(payload: dict[str, object]) -> None:
    contract = PLAYER_DEVELOPMENT_SKILL_REGISTRY["coaching_video_evidence_skill.v1"]
    required_inputs = set(contract["required_inputs"])  # type: ignore[arg-type]
    for field in (
        "player_profile_id",
        "coach_user_id",
        "org_id",
        "video_session_id",
        "video_analysis_job_id",
        "analysis_mode",
        "evidence_markers",
    ):
        if field not in required_inputs:
            raise VideoEvidenceSkillMappingError(f"Skill contract missing required input '{field}'.")
        if field not in payload:
            raise VideoEvidenceSkillMappingError(f"Mapped payload missing required input '{field}'.")


def _get_nested(payload: dict[str, Any], path: tuple[str, ...]) -> tuple[bool, Any]:
    current: Any = payload
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return False, None
        current = current[key]
    return True, current


def _as_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    return None


def _to_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, Real):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


def _to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _to_label(value: Any) -> str | None:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _marker_sort_key(marker: dict[str, object]) -> tuple[float, str, int, str]:
    timestamp = _to_float(marker.get("timestamp_s"))
    frame_num = _to_int(marker.get("frame_num"))
    return (
        timestamp if timestamp is not None else float("inf"),
        str(marker.get("metric_name", "")),
        frame_num if frame_num is not None else 10**9,
        str(marker.get("finding_label", "")),
    )
