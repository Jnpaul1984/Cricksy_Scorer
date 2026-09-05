from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Any

_STABLE_THRESHOLDS_BY_UNIT = {
    "score": 0.05,
    "ratio": 0.05,
    "degrees": 5.0,
    "seconds": 0.02,
}


@dataclass(frozen=True)
class _GoalTarget:
    target_type: str
    target_value: float | None
    target_min: float | None
    target_max: float | None


def evaluate_v2_goals_against_longitudinal(
    *,
    v2_goals: list[dict[str, Any]],
    longitudinal_progress: dict[str, Any],
    latest_job_id: str | None,
) -> list[dict[str, Any]]:
    if not v2_goals:
        return []

    series = longitudinal_progress.get("series")
    if not isinstance(series, list):
        series = []

    evaluations: list[dict[str, Any]] = []
    for goal in v2_goals:
        evaluations.append(
            _evaluate_single_goal(
                goal=goal, longitudinal_series=series, latest_job_id=latest_job_id
            )
        )
    return evaluations


def _evaluate_single_goal(
    *,
    goal: dict[str, Any],
    longitudinal_series: list[dict[str, Any]],
    latest_job_id: str | None,
) -> dict[str, Any]:
    goal_id = str(goal.get("goal_id") or "")
    metric_id = goal.get("metric_id")
    technical_area = goal.get("technical_area")
    discipline = goal.get("discipline")
    phase = goal.get("phase")
    action_type = goal.get("action_type")
    target = _extract_target(goal)

    if not metric_id:
        return _unsupported(
            goal=goal,
            reason=(
                "Deterministic target evaluation requires a linked metric_id. "
                "Technical-area-only goals remain coach-managed."
            ),
        )

    matching = _match_series(
        longitudinal_series,
        discipline=str(discipline) if discipline else None,
        metric_id=str(metric_id),
        phase=str(phase) if phase else None,
        action_type=str(action_type) if action_type else None,
    )
    if matching is None:
        return _unsupported(
            goal=goal,
            reason="No matching longitudinal V2 metric series was found for this goal.",
        )

    history = matching.get("history")
    if not isinstance(history, list):
        history = []

    by_job_id = {str(item.get("job_id")): item for item in history if item.get("job_id")}
    latest_observation = by_job_id.get(str(latest_job_id)) if latest_job_id else None
    if latest_observation is not None and latest_observation.get("comparable") is False:
        return {
            "goal_id": goal_id,
            "metric_id": metric_id,
            "technical_area": technical_area,
            "discipline": discipline,
            "target": _serialize_target(target),
            "baseline": None,
            "latest": latest_observation,
            "change": None,
            "comparable_session_count": int(matching.get("comparable_session_count") or 0),
            "status": "non_comparable",
            "confidence": matching.get("trend", {}).get("confidence_score"),
            "limitations": [
                "The latest session result is not technically comparable to baseline evidence."
            ],
            "evidence": {
                "series_metric_id": matching.get("metric_id"),
                "series_phase": matching.get("phase"),
                "series_action_type": matching.get("action_type"),
            },
        }

    comparable_history = [item for item in history if item.get("comparable") is True]
    if not comparable_history:
        return {
            "goal_id": goal_id,
            "metric_id": metric_id,
            "technical_area": technical_area,
            "discipline": discipline,
            "target": _serialize_target(target),
            "baseline": None,
            "latest": None,
            "change": None,
            "comparable_session_count": 0,
            "status": "non_comparable",
            "confidence": None,
            "limitations": ["No technically comparable observations were available."],
            "evidence": {
                "series_metric_id": matching.get("metric_id"),
                "series_phase": matching.get("phase"),
                "series_action_type": matching.get("action_type"),
            },
        }

    baseline_job_id = goal.get("baseline_job_id")
    baseline = comparable_history[0]
    if baseline_job_id:
        baseline = next(
            (
                item
                for item in comparable_history
                if str(item.get("job_id")) == str(baseline_job_id)
            ),
            baseline,
        )

    baseline_index = comparable_history.index(baseline)
    comparable_from_baseline = comparable_history[baseline_index:]

    if len(comparable_from_baseline) < 2:
        return {
            "goal_id": goal_id,
            "metric_id": metric_id,
            "technical_area": technical_area,
            "discipline": discipline,
            "target": _serialize_target(target),
            "baseline": baseline,
            "latest": comparable_from_baseline[-1],
            "change": None,
            "comparable_session_count": len(comparable_from_baseline),
            "status": "insufficient_data",
            "confidence": _confidence_for([baseline]),
            "limitations": [
                "At least two comparable sessions (including baseline) are required for target evaluation."
            ],
            "evidence": {
                "series_metric_id": matching.get("metric_id"),
                "series_phase": matching.get("phase"),
                "series_action_type": matching.get("action_type"),
            },
        }

    latest = comparable_from_baseline[-1]
    evaluation = _evaluate_target(
        target=target,
        baseline=baseline,
        latest=latest,
        comparable_session_count=len(comparable_from_baseline),
        series=matching,
    )
    evaluation.update(
        {
            "goal_id": goal_id,
            "metric_id": metric_id,
            "technical_area": technical_area,
            "discipline": discipline,
            "target": _serialize_target(target),
            "baseline": baseline,
            "latest": latest,
            "comparable_session_count": len(comparable_from_baseline),
            "evidence": {
                "series_metric_id": matching.get("metric_id"),
                "series_phase": matching.get("phase"),
                "series_action_type": matching.get("action_type"),
            },
        }
    )
    return evaluation


def _match_series(
    series: list[dict[str, Any]],
    *,
    discipline: str | None,
    metric_id: str,
    phase: str | None,
    action_type: str | None,
) -> dict[str, Any] | None:
    exact = [
        item
        for item in series
        if str(item.get("metric_id")) == metric_id
        and (discipline is None or str(item.get("discipline")) == discipline)
        and (phase is None or str(item.get("phase")) == phase)
        and (action_type is None or str(item.get("action_type")) == action_type)
    ]
    if exact:
        return exact[0]

    relaxed = [
        item
        for item in series
        if str(item.get("metric_id")) == metric_id
        and (discipline is None or str(item.get("discipline")) == discipline)
    ]
    return relaxed[0] if relaxed else None


def _evaluate_target(
    *,
    target: _GoalTarget,
    baseline: dict[str, Any],
    latest: dict[str, Any],
    comparable_session_count: int,
    series: dict[str, Any],
) -> dict[str, Any]:
    baseline_raw = _as_float(baseline.get("raw_value"))
    latest_raw = _as_float(latest.get("raw_value"))

    if target.target_type == "min_normalized_score":
        baseline_raw = _as_float(baseline.get("normalized_score"))
        latest_raw = _as_float(latest.get("normalized_score"))

    if target.target_type == "improve_consistency":
        baseline_consistency = _extract_consistency_value(baseline)
        latest_consistency = _extract_consistency_value(latest)
        if baseline_consistency is None or latest_consistency is None:
            return {
                "status": "unsupported",
                "change": None,
                "confidence": _confidence_for([baseline, latest]),
                "limitations": [
                    "Consistency target evaluation requires comparable numeric within-session consistency values."
                ],
            }

        target_threshold = target.target_value if target.target_value is not None else 0.1
        if latest_consistency <= target_threshold:
            status = "achieved"
        elif latest_consistency < baseline_consistency:
            status = "improving_but_not_achieved"
        elif _is_unchanged(baseline_consistency, latest_consistency, "ratio"):
            status = "unchanged"
        else:
            status = "regressing"

        on_track = (
            status == "improving_but_not_achieved"
            and baseline_consistency > target_threshold
            and latest_consistency <= baseline_consistency * 0.6
        )
        return {
            "status": "on_track" if on_track else status,
            "change": {
                "absolute": round(latest_consistency - baseline_consistency, 4),
                "normalized": _progress_to_target_lower(
                    baseline_value=baseline_consistency,
                    latest_value=latest_consistency,
                    target_value=target_threshold,
                ),
                "unit": "ratio",
            },
            "confidence": _confidence_for([baseline, latest]),
            "limitations": _trend_limitations(series, comparable_session_count),
        }

    if baseline_raw is None or latest_raw is None:
        return {
            "status": "unsupported",
            "change": None,
            "confidence": _confidence_for([baseline, latest]),
            "limitations": [
                "Numeric baseline/latest values are required for deterministic evaluation."
            ],
        }

    if target.target_type == "increase_to_threshold":
        if target.target_value is None:
            return _invalid_target("increase_to_threshold requires target_value")
        return _evaluate_higher_target(
            baseline_value=baseline_raw,
            latest_value=latest_raw,
            target_value=target.target_value,
            unit=str(latest.get("unit") or "score"),
            series=series,
            comparable_session_count=comparable_session_count,
            confidence=_confidence_for([baseline, latest]),
        )

    if target.target_type == "decrease_to_threshold":
        if target.target_value is None:
            return _invalid_target("decrease_to_threshold requires target_value")
        return _evaluate_lower_target(
            baseline_value=baseline_raw,
            latest_value=latest_raw,
            target_value=target.target_value,
            unit=str(latest.get("unit") or "score"),
            series=series,
            comparable_session_count=comparable_session_count,
            confidence=_confidence_for([baseline, latest]),
        )

    if target.target_type == "stay_within_range":
        if target.target_min is None or target.target_max is None:
            return _invalid_target("stay_within_range requires target_min and target_max")
        return _evaluate_range_target(
            baseline_value=baseline_raw,
            latest_value=latest_raw,
            target_min=target.target_min,
            target_max=target.target_max,
            unit=str(latest.get("unit") or "score"),
            series=series,
            comparable_session_count=comparable_session_count,
            confidence=_confidence_for([baseline, latest]),
        )

    if target.target_type == "min_normalized_score":
        if target.target_value is None:
            return _invalid_target("min_normalized_score requires target_value")
        return _evaluate_higher_target(
            baseline_value=baseline_raw,
            latest_value=latest_raw,
            target_value=target.target_value,
            unit="score",
            series=series,
            comparable_session_count=comparable_session_count,
            confidence=_confidence_for([baseline, latest]),
        )

    return {
        "status": "unsupported",
        "change": None,
        "confidence": _confidence_for([baseline, latest]),
        "limitations": [
            f"Unsupported target type '{target.target_type}'. Deterministic evaluation was skipped."
        ],
    }


def _evaluate_higher_target(
    *,
    baseline_value: float,
    latest_value: float,
    target_value: float,
    unit: str,
    series: dict[str, Any],
    comparable_session_count: int,
    confidence: float | None,
) -> dict[str, Any]:
    if latest_value >= target_value:
        status = "achieved"
    elif latest_value > baseline_value:
        status = "improving_but_not_achieved"
    elif _is_unchanged(baseline_value, latest_value, unit):
        status = "unchanged"
    else:
        status = "regressing"

    on_track = (
        status == "improving_but_not_achieved"
        and _progress_to_target_higher(
            baseline_value=baseline_value,
            latest_value=latest_value,
            target_value=target_value,
        )
        >= 0.6
    )

    return {
        "status": "on_track" if on_track else status,
        "change": {
            "absolute": round(latest_value - baseline_value, 4),
            "normalized": _progress_to_target_higher(
                baseline_value=baseline_value,
                latest_value=latest_value,
                target_value=target_value,
            ),
            "unit": unit,
        },
        "confidence": confidence,
        "limitations": _trend_limitations(series, comparable_session_count),
    }


def _evaluate_lower_target(
    *,
    baseline_value: float,
    latest_value: float,
    target_value: float,
    unit: str,
    series: dict[str, Any],
    comparable_session_count: int,
    confidence: float | None,
) -> dict[str, Any]:
    if latest_value <= target_value:
        status = "achieved"
    elif latest_value < baseline_value:
        status = "improving_but_not_achieved"
    elif _is_unchanged(baseline_value, latest_value, unit):
        status = "unchanged"
    else:
        status = "regressing"

    on_track = (
        status == "improving_but_not_achieved"
        and _progress_to_target_lower(
            baseline_value=baseline_value,
            latest_value=latest_value,
            target_value=target_value,
        )
        >= 0.6
    )

    return {
        "status": "on_track" if on_track else status,
        "change": {
            "absolute": round(latest_value - baseline_value, 4),
            "normalized": _progress_to_target_lower(
                baseline_value=baseline_value,
                latest_value=latest_value,
                target_value=target_value,
            ),
            "unit": unit,
        },
        "confidence": confidence,
        "limitations": _trend_limitations(series, comparable_session_count),
    }


def _evaluate_range_target(
    *,
    baseline_value: float,
    latest_value: float,
    target_min: float,
    target_max: float,
    unit: str,
    series: dict[str, Any],
    comparable_session_count: int,
    confidence: float | None,
) -> dict[str, Any]:
    baseline_distance = _distance_to_range(baseline_value, target_min, target_max)
    latest_distance = _distance_to_range(latest_value, target_min, target_max)

    if latest_distance == 0.0:
        status = "achieved"
    elif latest_distance < baseline_distance:
        status = "improving_but_not_achieved"
    elif _is_unchanged(baseline_distance, latest_distance, unit):
        status = "unchanged"
    else:
        status = "regressing"

    on_track = (
        status == "improving_but_not_achieved"
        and baseline_distance > 0
        and (latest_distance <= baseline_distance * 0.4)
    )

    return {
        "status": "on_track" if on_track else status,
        "change": {
            "absolute": round(latest_value - baseline_value, 4),
            "normalized": _safe_round((baseline_distance - latest_distance) / baseline_distance, 4)
            if baseline_distance > 0
            else None,
            "unit": unit,
        },
        "confidence": confidence,
        "limitations": _trend_limitations(series, comparable_session_count),
    }


def _distance_to_range(value: float, target_min: float, target_max: float) -> float:
    if target_min <= value <= target_max:
        return 0.0
    if value < target_min:
        return round(target_min - value, 4)
    return round(value - target_max, 4)


def _extract_target(goal: dict[str, Any]) -> _GoalTarget:
    return _GoalTarget(
        target_type=str(goal.get("target_type") or ""),
        target_value=_as_float(goal.get("target_value")),
        target_min=_as_float(goal.get("target_min")),
        target_max=_as_float(goal.get("target_max")),
    )


def _serialize_target(target: _GoalTarget) -> dict[str, Any]:
    return {
        "target_type": target.target_type,
        "target_value": target.target_value,
        "target_min": target.target_min,
        "target_max": target.target_max,
    }


def _unsupported(*, goal: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "goal_id": str(goal.get("goal_id") or ""),
        "metric_id": goal.get("metric_id"),
        "technical_area": goal.get("technical_area"),
        "discipline": goal.get("discipline"),
        "target": _serialize_target(_extract_target(goal)),
        "baseline": None,
        "latest": None,
        "change": None,
        "comparable_session_count": 0,
        "status": "unsupported",
        "confidence": None,
        "limitations": [reason],
        "evidence": None,
    }


def _invalid_target(reason: str) -> dict[str, Any]:
    return {
        "status": "unsupported",
        "change": None,
        "confidence": None,
        "limitations": [reason],
    }


def _extract_consistency_value(observation: dict[str, Any]) -> float | None:
    consistency = observation.get("within_session_consistency")
    if not isinstance(consistency, dict):
        return None
    return _as_float(consistency.get("value"))


def _is_unchanged(left: float, right: float, unit: str) -> bool:
    threshold = _STABLE_THRESHOLDS_BY_UNIT.get(unit, 0.05)
    return abs(right - left) <= threshold


def _trend_limitations(series: dict[str, Any], comparable_session_count: int) -> list[str]:
    trend = series.get("trend") if isinstance(series, dict) else None
    limitations = trend.get("limitations") if isinstance(trend, dict) else None
    if isinstance(limitations, list):
        return [str(item) for item in limitations]
    if comparable_session_count <= 2:
        return [
            "Trend uses recent-versus-baseline change only because only two comparable sessions were available."
        ]
    return []


def _confidence_for(observations: list[dict[str, Any]]) -> float | None:
    values: list[float] = []
    for item in observations:
        value = _as_float(item.get("confidence_score"))
        if value is not None:
            values.append(value)
    return _safe_round(mean(values), 4) if values else None


def _progress_to_target_higher(
    *, baseline_value: float, latest_value: float, target_value: float
) -> float:
    denom = target_value - baseline_value
    if denom <= 0:
        return 1.0 if latest_value >= target_value else 0.0
    return max(0.0, min(1.0, (latest_value - baseline_value) / denom))


def _progress_to_target_lower(
    *, baseline_value: float, latest_value: float, target_value: float
) -> float:
    denom = baseline_value - target_value
    if denom <= 0:
        return 1.0 if latest_value <= target_value else 0.0
    return max(0.0, min(1.0, (baseline_value - latest_value) / denom))


def _safe_round(value: float | None, digits: int) -> float | None:
    return round(value, digits) if value is not None else None


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed
