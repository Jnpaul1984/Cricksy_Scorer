from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from statistics import mean, pstdev
from typing import Any

from backend.domain.coach_analysis_v2_contract import CoachingMetricResultV2
from backend.services.coach_analysis_v2_compatibility import compare_metric_results

LONGITUDINAL_PROGRESS_VERSION = "player_longitudinal_progress.v1"
_STABLE_THRESHOLDS_BY_UNIT = {
    "score": 0.05,
    "ratio": 0.05,
    "degrees": 5.0,
    "seconds": 0.02,
}
_TARGET_RANGE_METRICS: dict[str, tuple[float, float]] = {
    "batting_setup_stance_width_ratio": (0.9, 1.7),
    "batting_contact_proxy_front_knee_angle_deg": (130.0, 175.0),
    "pace_bowling_front_foot_contact_front_knee_angle_deg": (145.0, 178.0),
    "pace_bowling_release_proxy_trunk_lean_deg": (5.0, 35.0),
    "spin_bowling_pivot_shoulder_hip_separation_deg": (12.0, 40.0),
    "wicketkeeping_set_stance_width_ratio": (0.9, 1.7),
    "wicketkeeping_set_knee_flexion_angle_deg": (85.0, 125.0),
    "fielding_ready_stance_width_ratio": (0.85, 1.75),
    "fielding_ground_collection_body_drop_ratio": (0.15, 0.95),
    "fielding_ground_collection_knee_flexion_angle_deg": (75.0, 130.0),
    "fielding_throw_action_shoulder_hip_separation_deg": (12.0, 45.0),
}
_DIRECT_MEASUREMENT_SUFFIXES = (
    "_angle_deg",
    "_separation_deg",
    "_stance_width_ratio",
)
_DIRECT_MEASUREMENT_METRICS = {
    "fielding_ground_collection_body_drop_ratio",
}


@dataclass(frozen=True)
class _Observation:
    session: Any
    job: Any
    metric: CoachingMetricResultV2
    session_timestamp: datetime
    job_timestamp: datetime


def build_player_longitudinal_progress(
    sessions: list[Any],
    *,
    player_id: str,
    discipline_filter: str | None = None,
) -> dict[str, Any]:
    grouped: dict[tuple[str, str, str | None, str | None], list[_Observation]] = defaultdict(list)
    sessions_considered: list[dict[str, Any]] = []

    for session in sorted(
        sessions, key=lambda item: _timestamp_or_min(getattr(item, "created_at", None))
    ):
        primary_player_id = getattr(session, "primary_player_id", None)
        session_player_ids = [
            str(item)
            for item in (getattr(session, "player_ids", None) or [])
            if isinstance(item, str)
        ]
        if primary_player_id != player_id and player_id not in session_player_ids:
            continue

        job = _select_representative_job(getattr(session, "analysis_jobs", None) or [])
        session_summary = {
            "session_id": getattr(session, "id", None),
            "session_title": getattr(session, "title", None),
            "session_timestamp": _isoformat(getattr(session, "created_at", None)),
            "primary_player_id": primary_player_id,
            "discipline": getattr(session, "discipline", None),
            "job_id": getattr(job, "id", None),
            "job_timestamp": _isoformat(_job_timestamp(job)),
            "included": False,
            "reason": None,
        }

        if primary_player_id != player_id:
            session_summary["reason"] = (
                "Session includes the requested player but is not player-centered, so longitudinal attribution is unsafe."
            )
            sessions_considered.append(session_summary)
            continue

        metrics = _extract_metric_results(job)
        if not metrics:
            session_summary["reason"] = (
                "No V2 metric results were available for longitudinal analysis."
            )
            sessions_considered.append(session_summary)
            continue

        matched_metrics = 0
        for metric in metrics:
            metric_discipline = str(metric.discipline)
            if discipline_filter and metric_discipline != discipline_filter:
                continue
            grouped[(metric_discipline, metric.metric_id, metric.phase, metric.action_type)].append(
                _Observation(
                    session=session,
                    job=job,
                    metric=metric,
                    session_timestamp=_timestamp_or_min(getattr(session, "created_at", None)),
                    job_timestamp=_timestamp_or_min(_job_timestamp(job)),
                )
            )
            matched_metrics += 1

        session_summary["included"] = matched_metrics > 0
        session_summary["reason"] = (
            None
            if matched_metrics > 0
            else "No longitudinal metrics matched the requested discipline."
        )
        sessions_considered.append(session_summary)

    series = [
        _build_metric_series(
            observations=observations,
            player_id=player_id,
        )
        for _, observations in sorted(grouped.items(), key=lambda item: item[0])
    ]

    state_counts: dict[str, int] = defaultdict(int)
    for item in series:
        state_counts[str(item["trend"]["state"])] += 1

    return {
        "analysis_version": LONGITUDINAL_PROGRESS_VERSION,
        "generated_at": _isoformat(datetime.now(UTC)),
        "player_id": player_id,
        "discipline_filter": discipline_filter,
        "session_count": len(sessions_considered),
        "series_count": len(series),
        "summary": {
            "improving": state_counts.get("improving", 0),
            "regressing": state_counts.get("regressing", 0),
            "stable": state_counts.get("stable", 0),
            "mixed": state_counts.get("mixed", 0),
            "insufficient_data": state_counts.get("insufficient_data", 0),
            "non_comparable": state_counts.get("non_comparable", 0),
        },
        "sessions_considered": sessions_considered,
        "series": series,
    }


def _build_metric_series(*, observations: list[_Observation], player_id: str) -> dict[str, Any]:
    sorted_observations = sorted(
        observations,
        key=lambda item: (
            item.session_timestamp,
            item.job_timestamp,
            str(getattr(item.job, "id", "")),
        ),
    )
    semantics = _metric_semantics(sorted_observations[0].metric)
    numeric_candidates = [
        item for item in sorted_observations if _metric_numeric_value(item.metric) is not None
    ]
    comparable_component = _select_primary_comparable_component(
        numeric_candidates, player_id=player_id
    )
    comparable_ids = {id(item) for item in comparable_component}
    anchor = comparable_component[0] if comparable_component else None
    history = [
        _serialize_observation(
            observation=item,
            comparable=id(item) in comparable_ids,
            anchor=anchor,
            player_id=player_id,
            measurement_type=semantics.measurement_type,
        )
        for item in sorted_observations
    ]

    baseline = history_lookup = latest = best = None
    comparable_history = [item for item in history if item["comparable"]]
    if comparable_history:
        baseline = comparable_history[0]
        latest = comparable_history[-1]
        best = _select_best_observation(comparable_history, semantics)
        history_lookup = {item["job_id"]: item for item in history if item.get("job_id")}
    trend = _build_trend(comparable_history, semantics)
    if history_lookup and best is not None:
        best = history_lookup.get(best["job_id"], best)

    return {
        "discipline": str(sorted_observations[0].metric.discipline),
        "metric_id": sorted_observations[0].metric.metric_id,
        "metric_label": _metric_label(sorted_observations[0].metric.metric_id),
        "phase": sorted_observations[0].metric.phase,
        "action_type": sorted_observations[0].metric.action_type,
        "unit": sorted_observations[0].metric.unit,
        "measurement_type": semantics.measurement_type,
        "best_direction": semantics.best_direction,
        "target_range": (
            {"min": semantics.target_range[0], "max": semantics.target_range[1]}
            if semantics.target_range
            else None
        ),
        "metric_versions_seen": sorted(
            {
                str(item.metric.metric_version)
                for item in sorted_observations
                if item.metric.metric_version
            }
        ),
        "comparable_session_count": len(comparable_history),
        "history_count": len(history),
        "baseline": baseline,
        "latest": latest,
        "best": best,
        "best_available": best is not None,
        "trend": trend,
        "across_session_consistency": _build_across_session_consistency(comparable_history),
        "history": history,
    }


def _serialize_observation(
    *,
    observation: _Observation,
    comparable: bool,
    anchor: _Observation | None,
    player_id: str,
    measurement_type: str,
) -> dict[str, Any]:
    metric = observation.metric
    aggregate_stats = metric.aggregate_stats if isinstance(metric.aggregate_stats, dict) else {}
    consistency = metric.consistency if isinstance(metric.consistency, dict) else None
    comparability_reasons: list[str] = []
    comparability_state = "COMPARABLE" if comparable else "NON_COMPARABLE"
    if not comparable:
        if anchor is None:
            comparability_reasons.append(
                "No technically comparable baseline observation was available for this metric."
            )
        else:
            comparability_reasons.extend(
                compare_metric_results(
                    anchor.metric,
                    metric,
                    player_id_left=player_id,
                    player_id_right=player_id,
                ).reasons
            )
        if not comparability_reasons and _metric_numeric_value(metric) is None:
            comparability_reasons.append("Metric value is unavailable or non-numeric.")

    capture_profile = metric.capture_profile
    return {
        "session_id": getattr(observation.session, "id", None),
        "session_title": getattr(observation.session, "title", None),
        "session_timestamp": _isoformat(observation.session_timestamp),
        "job_id": getattr(observation.job, "id", None),
        "job_timestamp": _isoformat(observation.job_timestamp),
        "coaching_focus": getattr(observation.session, "coaching_focus", None),
        "metric_version": metric.metric_version,
        "discipline": str(metric.discipline),
        "phase": metric.phase,
        "action_type": metric.action_type,
        "raw_value": _metric_raw_value(metric),
        "normalized_score": _as_float(metric.normalized_score),
        "unit": metric.unit,
        "measurement_type": measurement_type,
        "validity_state": metric.validity_state.value,
        "confidence_score": _as_float(metric.confidence_score),
        "camera_view": getattr(capture_profile, "camera_view", None),
        "sample_fps": _as_float(getattr(capture_profile, "sample_fps", None)),
        "effective_analysis_fps": _as_float(
            getattr(capture_profile, "effective_analysis_fps", None)
        ),
        "source_video_fps": _as_float(getattr(capture_profile, "source_video_fps", None)),
        "source_model": getattr(capture_profile, "source_model", None),
        "capture_profile_version": getattr(capture_profile, "capture_profile_version", None),
        "repetition_count": _safe_int(
            aggregate_stats.get("repetition_count") or aggregate_stats.get("count")
        ),
        "valid_sample_count": _safe_int(
            aggregate_stats.get("valid_repetition_count") or aggregate_stats.get("count")
        ),
        "within_session_consistency": consistency,
        "evidence_refs": [item.model_dump(mode="json") for item in metric.evidence_refs],
        "timestamp_refs": [item.model_dump(mode="json") for item in metric.timestamp_refs],
        "frame_refs": [item.model_dump(mode="json") for item in metric.frame_refs],
        "limitations": list(metric.limitations),
        "comparable": comparable,
        "comparability_state": comparability_state,
        "comparability_reasons": comparability_reasons,
    }


def _build_trend(
    comparable_history: list[dict[str, Any]],
    semantics: "_MetricSemantics",
) -> dict[str, Any]:
    if not comparable_history:
        return {
            "state": "non_comparable",
            "method": None,
            "comparable_session_count": 0,
            "time_span_days": 0,
            "change_amount": None,
            "change_unit": None,
            "percent_change": None,
            "confidence_score": None,
            "limitations": ["No technically comparable observations were available."],
        }

    if len(comparable_history) == 1:
        return {
            "state": "insufficient_data",
            "method": "baseline_latest_delta",
            "comparable_session_count": 1,
            "time_span_days": 0,
            "change_amount": None,
            "change_unit": comparable_history[0].get("unit"),
            "percent_change": None,
            "confidence_score": comparable_history[0].get("confidence_score"),
            "limitations": [
                "At least two comparable sessions are required for longitudinal trend."
            ],
        }

    baseline = comparable_history[0]
    latest = comparable_history[-1]
    step_directions = [
        _compare_observation_values(left, right, semantics)
        for left, right in pairwise(comparable_history)
    ]
    improving_steps = sum(1 for step in step_directions if step["direction"] > 0)
    regressing_steps = sum(1 for step in step_directions if step["direction"] < 0)
    stable_steps = sum(1 for step in step_directions if step["direction"] == 0)

    if improving_steps and not regressing_steps:
        state = "improving"
    elif regressing_steps and not improving_steps:
        state = "regressing"
    elif stable_steps == len(step_directions):
        state = "stable"
    else:
        state = "mixed"

    first_dt = _parse_iso(baseline.get("session_timestamp"))
    last_dt = _parse_iso(latest.get("session_timestamp"))
    baseline_raw = _as_float(baseline.get("raw_value"))
    latest_raw = _as_float(latest.get("raw_value"))
    change_amount = (
        round(latest_raw - baseline_raw, 4)
        if baseline_raw is not None and latest_raw is not None
        else None
    )
    percent_change = None
    if (
        semantics.best_direction in {"higher", "lower"}
        and baseline_raw is not None
        and baseline_raw != 0.0
        and latest_raw is not None
    ):
        percent_change = round(((latest_raw - baseline_raw) / abs(baseline_raw)) * 100.0, 2)
    elif semantics.best_direction == "target_range":
        baseline_distance = _target_distance(baseline_raw, semantics)
        latest_distance = _target_distance(latest_raw, semantics)
        if (
            baseline_distance is not None
            and baseline_distance != 0.0
            and latest_distance is not None
        ):
            percent_change = round(
                ((baseline_distance - latest_distance) / baseline_distance) * 100.0,
                2,
            )

    confidence_values = [
        _as_float(item.get("confidence_score"))
        for item in comparable_history
        if item.get("confidence_score") is not None
    ]
    numeric_confidence_values = [item for item in confidence_values if item is not None]
    confidence_score = (
        round(mean(numeric_confidence_values) * min(1.0, len(comparable_history) / 4), 4)
        if numeric_confidence_values
        else None
    )
    method = (
        "baseline_latest_delta" if len(comparable_history) == 2 else "directional_step_consensus"
    )
    limitations = []
    if len(comparable_history) == 2:
        limitations.append(
            "Trend uses recent-versus-baseline change only because only two comparable sessions were available."
        )
    if any(item.get("validity_state") == "LOW_CONFIDENCE" for item in comparable_history):
        limitations.append(
            "Low-confidence observations were retained for visibility but may weaken trend certainty."
        )

    return {
        "state": state,
        "method": method,
        "comparable_session_count": len(comparable_history),
        "time_span_days": max((last_dt - first_dt).days, 0),
        "change_amount": change_amount,
        "change_unit": latest.get("unit"),
        "percent_change": percent_change,
        "confidence_score": confidence_score,
        "limitations": limitations,
    }


def _build_across_session_consistency(comparable_history: list[dict[str, Any]]) -> dict[str, Any]:
    if len(comparable_history) < 2:
        return {
            "classification": "insufficient_data",
            "method": None,
            "value": None,
            "comparable_session_count": len(comparable_history),
            "limitations": [
                "At least two comparable sessions are required for across-session stability."
            ],
        }

    values = [_as_float(item.get("raw_value")) for item in comparable_history]
    numeric_values = [item for item in values if item is not None]
    if len(numeric_values) < 2:
        return {
            "classification": "non_comparable",
            "method": None,
            "value": None,
            "comparable_session_count": len(numeric_values),
            "limitations": ["Across-session stability requires numeric comparable values."],
        }

    spread = pstdev(numeric_values) if len(numeric_values) > 1 else 0.0
    mean_value = mean(numeric_values)
    if abs(mean_value) > 1e-9:
        method = "coefficient_of_variation"
        value = round(spread / abs(mean_value), 4)
        classification = "stable" if value <= 0.1 else "variable"
    else:
        method = "population_standard_deviation"
        value = round(spread, 4)
        classification = "stable" if value <= 0.05 else "variable"

    return {
        "classification": classification,
        "method": method,
        "value": value,
        "comparable_session_count": len(values),
        "limitations": [
            "Across-session stability is reported separately from within-session repeatability."
        ],
    }


def _select_best_observation(
    comparable_history: list[dict[str, Any]], semantics: "_MetricSemantics"
) -> dict[str, Any] | None:
    if semantics.best_direction == "unavailable":
        return None

    scored: list[tuple[float, float, str, dict[str, Any]]] = []
    for item in comparable_history:
        raw_value = _as_float(item.get("raw_value"))
        if raw_value is None:
            continue
        rank = _best_rank(raw_value, semantics)
        confidence = _as_float(item.get("confidence_score")) or 0.0
        timestamp = str(item.get("session_timestamp") or "")
        scored.append((rank, -confidence, timestamp, item))

    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], item[1], item[2]))
    return scored[0][3]


def _select_primary_comparable_component(
    observations: list[_Observation], *, player_id: str
) -> list[_Observation]:
    if not observations:
        return []

    adjacency: dict[int, set[int]] = {index: set() for index in range(len(observations))}
    for left_index, left in enumerate(observations):
        for right_index in range(left_index + 1, len(observations)):
            right = observations[right_index]
            eligibility = compare_metric_results(
                left.metric,
                right.metric,
                player_id_left=player_id,
                player_id_right=player_id,
            )
            if eligibility.comparable:
                adjacency[left_index].add(right_index)
                adjacency[right_index].add(left_index)

    visited: set[int] = set()
    components: list[list[_Observation]] = []
    for index in range(len(observations)):
        if index in visited:
            continue
        stack = [index]
        component_indexes: list[int] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component_indexes.append(current)
            stack.extend(adjacency[current] - visited)
        components.append(
            sorted(
                [observations[item] for item in component_indexes],
                key=lambda item: (
                    item.session_timestamp,
                    item.job_timestamp,
                    str(getattr(item.job, "id", "")),
                ),
            )
        )

    components.sort(
        key=lambda items: (
            -len(items),
            _timestamp_or_min(items[0].session_timestamp),
            _timestamp_or_min(items[0].job_timestamp),
        )
    )
    return components[0]


def _select_representative_job(jobs: list[Any]) -> Any | None:
    if not jobs:
        return None

    ranked = sorted(
        jobs,
        key=lambda job: (
            _job_metric_count(job) > 0,
            _job_has_results(job),
            _timestamp_or_min(_job_timestamp(job)),
            str(getattr(job, "id", "")),
        ),
    )
    return ranked[-1]


def _job_metric_count(job: Any | None) -> int:
    return len(_extract_metric_results(job))


def _job_has_results(job: Any | None) -> bool:
    if job is None:
        return False
    return any(
        getattr(job, field_name, None)
        for field_name in ("deep_results", "quick_results", "results")
    )


def _extract_metric_results(job: Any | None) -> list[CoachingMetricResultV2]:
    if job is None:
        return []
    payloads = [
        getattr(job, "deep_results", None),
        getattr(job, "quick_results", None),
        getattr(job, "results", None),
    ]
    for payload in payloads:
        candidate = payload
        if isinstance(candidate, dict) and isinstance(candidate.get("deep"), dict):
            candidate = candidate["deep"]
        elif isinstance(candidate, dict) and isinstance(candidate.get("quick"), dict):
            candidate = candidate["quick"]
        metric_results = (
            candidate.get("v2", {}).get("metric_results") if isinstance(candidate, dict) else None
        )
        if not isinstance(metric_results, list):
            continue
        parsed: list[CoachingMetricResultV2] = []
        for item in metric_results:
            if not isinstance(item, dict):
                continue
            try:
                parsed.append(CoachingMetricResultV2.model_validate(item))
            except Exception:
                continue
        if parsed:
            return parsed
    return []


@dataclass(frozen=True)
class _MetricSemantics:
    measurement_type: str
    best_direction: str
    target_range: tuple[float, float] | None = None


def _metric_semantics(metric: CoachingMetricResultV2) -> _MetricSemantics:
    metric_id = metric.metric_id
    if metric_id in _TARGET_RANGE_METRICS:
        return _MetricSemantics(
            measurement_type=_measurement_type(metric_id),
            best_direction="target_range",
            target_range=_TARGET_RANGE_METRICS[metric_id],
        )
    if metric_id.endswith("_score"):
        return _MetricSemantics(
            measurement_type=_measurement_type(metric_id),
            best_direction="higher",
        )
    if any(
        token in metric_id
        for token in (
            "drift_ratio",
            "offset_ratio",
            "displacement_ratio",
            "compactness_ratio",
            "depth_delta_ratio",
            "arm_angle_deg",
        )
    ):
        return _MetricSemantics(
            measurement_type=_measurement_type(metric_id),
            best_direction="lower",
        )
    return _MetricSemantics(
        measurement_type=_measurement_type(metric_id),
        best_direction="unavailable",
    )


def _measurement_type(metric_id: str) -> str:
    if metric_id in _DIRECT_MEASUREMENT_METRICS or metric_id.endswith(_DIRECT_MEASUREMENT_SUFFIXES):
        return "pose_measurement"
    return "pose_proxy"


def _compare_observation_values(
    left: dict[str, Any], right: dict[str, Any], semantics: _MetricSemantics
) -> dict[str, Any]:
    left_value = _as_float(left.get("raw_value"))
    right_value = _as_float(right.get("raw_value"))
    if left_value is None or right_value is None:
        return {"direction": 0, "magnitude": None}

    threshold = _STABLE_THRESHOLDS_BY_UNIT.get(str(right.get("unit") or ""), 0.05)
    if semantics.best_direction == "higher":
        delta = right_value - left_value
    elif semantics.best_direction == "lower":
        delta = left_value - right_value
    elif semantics.best_direction == "target_range":
        delta = (_target_distance(left_value, semantics) or 0.0) - (
            _target_distance(right_value, semantics) or 0.0
        )
    else:
        return {"direction": 0, "magnitude": None}

    if abs(delta) <= threshold:
        return {"direction": 0, "magnitude": round(delta, 4)}
    return {"direction": 1 if delta > 0 else -1, "magnitude": round(delta, 4)}


def _best_rank(raw_value: float, semantics: _MetricSemantics) -> float:
    if semantics.best_direction == "higher":
        return -raw_value
    if semantics.best_direction == "lower":
        return raw_value
    if semantics.best_direction == "target_range":
        return _target_distance(raw_value, semantics) or math.inf
    return math.inf


def _target_distance(raw_value: float | None, semantics: _MetricSemantics) -> float | None:
    if raw_value is None or semantics.target_range is None:
        return None
    target_min, target_max = semantics.target_range
    midpoint = (target_min + target_max) / 2
    return round(abs(raw_value - midpoint), 4)


def _metric_numeric_value(metric: CoachingMetricResultV2) -> float | None:
    return (
        _metric_raw_value(metric)
        if _metric_raw_value(metric) is not None
        else _as_float(metric.normalized_score)
    )


def _metric_raw_value(metric: CoachingMetricResultV2) -> float | None:
    return _as_float(metric.raw_value)


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed


def _job_timestamp(job: Any | None) -> datetime | None:
    if job is None:
        return None
    return getattr(job, "completed_at", None) or getattr(job, "created_at", None)


def _metric_label(metric_id: str) -> str:
    return metric_id.replace("_", " ").strip().title()


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _parse_iso(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        return datetime.fromisoformat(value)
    return datetime.min.replace(tzinfo=UTC)


def _timestamp_or_min(value: datetime | None) -> datetime:
    return value if isinstance(value, datetime) else datetime.min.replace(tzinfo=UTC)
