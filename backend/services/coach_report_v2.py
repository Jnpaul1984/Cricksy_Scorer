from __future__ import annotations

import math
from typing import Any

from backend.services.coaching_action_registry import (
    ACTION_REGISTRY_VERSION,
    governed_actions_for,
)

REPORT_V2_VERSION = "coaching_analysis_report.v2"
_MEASURABLE_STATES = {"VALID", "LOW_CONFIDENCE"}
_V2_METRIC_PREFIXES = (
    "batting_",
    "pace_bowling_",
    "spin_bowling_",
    "wicketkeeping_",
    "fielding_",
)


def has_persisted_v2_evidence(results: dict[str, Any] | None) -> bool:
    if not isinstance(results, dict):
        return False
    v2 = results.get("v2")
    if not isinstance(v2, dict):
        return False
    return any(
        isinstance(v2.get(key), list) and bool(v2[key])
        for key in ("metric_results", "repetitions", "phases")
    )


def build_coaching_analysis_report_v2(
    *,
    results: dict[str, Any],
    analysis_mode: str | None,
    coach_goals: dict[str, Any] | None = None,
    outcomes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Interpret persisted V2 artifacts without recalculating video measurements."""
    v2_payload = results.get("v2")
    v2: dict[str, Any] = v2_payload if isinstance(v2_payload, dict) else {}
    repetitions = _sanitize_repetitions(v2.get("repetitions"))
    phases = _sanitize_phases(v2.get("phases"))
    metrics = _sanitize_metrics(v2.get("metric_results"))
    session_analysis = _session_analysis(results)
    concerns = _sanitize_signals(session_analysis.get("recurring_concerns"), metrics)
    strengths = _sanitize_signals(session_analysis.get("strengths"), metrics)
    consistency = _sanitize_consistency(session_analysis.get("consistency_observations"), metrics)
    priorities = _build_priorities(concerns, metrics)

    return {
        "report_version": REPORT_V2_VERSION,
        "source": "persisted_video_analysis_v2",
        "analysis_mode": analysis_mode,
        "capture_profile": _safe_mapping(v2.get("capture_profile")),
        "validity_state": _safe_text(v2.get("validity_state")) or "UNAVAILABLE",
        "repetitions": repetitions,
        "phases": phases,
        "metrics": metrics,
        "development_priorities": priorities,
        "strengths": strengths,
        "recurring_concerns": concerns,
        "consistency_observations": consistency,
        "representative_repetitions": {
            "best": _sanitize_selection(session_analysis.get("best_repetition")),
            "needs_work": _sanitize_selection(session_analysis.get("needs_work_repetition")),
        },
        "governed_actions": _build_governed_actions(priorities),
        "action_registry_version": ACTION_REGISTRY_VERSION,
        "coach_recorded_interventions": _sanitize_interventions(coach_goals),
        "longitudinal_goal_evidence": _sanitize_longitudinal(outcomes),
        "limitations": _collect_limitations(metrics, phases, repetitions, session_analysis),
        "governance": {
            "deterministic_evidence_selects_priority": True,
            "registry_selects_actions": True,
            "coach_approval_required_for_player_facing_actions": True,
            "automated_medical_or_conditioning_prescriptions": False,
        },
    }


def _sanitize_repetitions(payload: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict) or not _safe_text(item.get("repetition_id")):
            continue
        rows.append(
            {
                "repetition_id": _safe_text(item.get("repetition_id")),
                "discipline": _safe_text(item.get("discipline")),
                "action_type": _safe_text(item.get("action_type")),
                "start_ts": _finite_number(item.get("start_ts"), minimum=0),
                "end_ts": _finite_number(item.get("end_ts"), minimum=0),
                "start_frame": _safe_int(item.get("start_frame"), minimum=0),
                "end_frame": _safe_int(item.get("end_frame"), minimum=0),
                "segmentation_method": _safe_text(item.get("segmentation_method")),
                "segmentation_confidence": _finite_number(
                    item.get("segmentation_confidence"), minimum=0, maximum=1
                ),
                "validity_state": _safe_text(item.get("validity_state")) or "NOT_MEASURABLE",
                "insufficient_reason": _safe_text(item.get("insufficient_reason")),
            }
        )
    return rows


def _sanitize_phases(payload: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict) or not _safe_text(item.get("phase_id")):
            continue
        rows.append(
            {
                "phase_id": _safe_text(item.get("phase_id")),
                "repetition_id": _safe_text(item.get("repetition_id")),
                "phase_name": _safe_text(item.get("phase_name")),
                "start_ts": _finite_number(item.get("start_ts"), minimum=0),
                "end_ts": _finite_number(item.get("end_ts"), minimum=0),
                "confidence": _finite_number(item.get("confidence"), minimum=0, maximum=1),
                "validity_state": _safe_text(item.get("validity_state")) or "NOT_MEASURABLE",
                "requires_object_evidence": bool(item.get("requires_object_evidence")),
                "limitations": _safe_strings(item.get("limitations")),
            }
        )
    return rows


def _sanitize_metrics(payload: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict):
            continue
        metric_id = _safe_text(item.get("metric_id"))
        if not metric_id or not metric_id.startswith(_V2_METRIC_PREFIXES):
            continue
        validity = _safe_text(item.get("validity_state")) or "NOT_MEASURABLE"
        measurable = validity in _MEASURABLE_STATES
        raw_value = _finite_number(item.get("raw_value")) if measurable else None
        normalized = (
            _finite_number(item.get("normalized_score"), minimum=0, maximum=1)
            if measurable
            else None
        )
        confidence = _finite_number(item.get("confidence_score"), minimum=0, maximum=1)
        limitations = _safe_strings(item.get("limitations"))
        unavailable_reason = _safe_text(item.get("unavailable_reason"))
        if measurable and raw_value is None:
            unavailable_reason = unavailable_reason or (
                "The persisted raw value was unavailable or invalid and could not be used."
            )
            if unavailable_reason not in limitations:
                limitations.append(unavailable_reason)
        elif not measurable and not unavailable_reason:
            unavailable_reason = (
                "This metric is not reliably measurable from the persisted evidence."
            )
        rows.append(
            {
                "metric_id": metric_id,
                "metric_version": _safe_text(item.get("metric_version")),
                "discipline": _safe_text(item.get("discipline")),
                "action_type": _safe_text(item.get("action_type")),
                "repetition_id": _safe_text(item.get("repetition_id")),
                "phase": _safe_text(item.get("phase")),
                "raw_value": raw_value,
                "normalized_score": normalized,
                "unit": _safe_text(item.get("unit")),
                "classification_status": (
                    _safe_text(item.get("classification_status")) if measurable else None
                ),
                "confidence_score": confidence,
                "validity_state": validity,
                "proxy_state": "PROXY" if "proxy" in metric_id.lower() else "DIRECT_OR_UNSPECIFIED",
                "unavailable_reason": unavailable_reason,
                "limitations": limitations,
                "evidence_refs": _safe_dicts(item.get("evidence_refs")),
                "timestamp_refs": _safe_dicts(item.get("timestamp_refs")),
                "frame_refs": _safe_dicts(item.get("frame_refs")),
                "consistency": _safe_mapping(item.get("consistency")),
            }
        )
    return rows


def _session_analysis(results: dict[str, Any]) -> dict[str, Any]:
    for container_name in ("findings", "report"):
        container = results.get(container_name)
        if isinstance(container, dict) and isinstance(container.get("v2_session_analysis"), dict):
            return container["v2_session_analysis"]
    return {}


def _sanitize_signals(payload: Any, metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metric_ids = {
        item["metric_id"]
        for item in metrics
        if item["validity_state"] in _MEASURABLE_STATES and item["raw_value"] is not None
    }
    rows: list[dict[str, Any]] = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict) or item.get("metric_id") not in metric_ids:
            continue
        rows.append(
            {
                "metric_id": item["metric_id"],
                "discipline": _safe_text(item.get("discipline")),
                "phase": _safe_text(item.get("phase")),
                "severity": _safe_text(item.get("severity")),
                "confidence_score": _finite_number(
                    item.get("confidence_score"), minimum=0, maximum=1
                ),
                "valid_sample_count": _safe_int(item.get("valid_sample_count"), minimum=0),
                "summary": _safe_text(item.get("summary")) or "Persisted V2 pattern.",
                "supporting_repetition_ids": _safe_strings(item.get("supporting_repetition_ids")),
                "limitations": _safe_strings(item.get("limitations")),
            }
        )
    return rows


def _sanitize_consistency(payload: Any, metrics: list[dict[str, Any]]) -> list[dict[str, Any]]:
    metric_ids = {
        item["metric_id"]
        for item in metrics
        if item["validity_state"] in _MEASURABLE_STATES and item["raw_value"] is not None
    }
    rows: list[dict[str, Any]] = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict) or item.get("metric_id") not in metric_ids:
            continue
        rows.append(
            {
                "metric_id": _safe_text(item.get("metric_id")),
                "discipline": _safe_text(item.get("discipline")),
                "phase": _safe_text(item.get("phase")),
                "method": _safe_text(item.get("method")),
                "classification": _safe_text(item.get("classification")),
                "value": _finite_number(item.get("value"), minimum=0),
                "confidence_score": _finite_number(
                    item.get("confidence_score"), minimum=0, maximum=1
                ),
                "valid_sample_count": _safe_int(item.get("valid_sample_count"), minimum=0),
                "excluded_repetition_count": _safe_int(
                    item.get("excluded_repetition_count"), minimum=0
                ),
                "limitations": _safe_strings(item.get("limitations")),
            }
        )
    return rows


def _build_priorities(
    concerns: list[dict[str, Any]], metrics: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    by_id = {item["metric_id"]: item for item in metrics}
    candidates = list(concerns)
    known = {item["metric_id"] for item in candidates}
    for metric in metrics:
        if (
            metric["metric_id"] not in known
            and metric["validity_state"] == "VALID"
            and metric["classification_status"] == "NEEDS_ATTENTION"
            and metric["raw_value"] is not None
        ):
            candidates.append(
                {
                    "metric_id": metric["metric_id"],
                    "discipline": metric["discipline"],
                    "phase": metric["phase"],
                    "severity": "low",
                    "confidence_score": metric["confidence_score"],
                    "valid_sample_count": None,
                    "summary": "This persisted V2 metric was classified as needs attention.",
                    "supporting_repetition_ids": [],
                    "limitations": metric["limitations"],
                }
            )
    priorities: list[dict[str, Any]] = []
    for concern in candidates[:3]:
        metric = by_id.get(concern["metric_id"], {})
        priorities.append(
            {
                **concern,
                "observed_pattern": concern["summary"],
                "validity_state": metric.get("validity_state"),
                "proxy_state": metric.get("proxy_state"),
                "measured_value": metric.get("raw_value"),
                "unit": metric.get("unit"),
            }
        )
    return priorities


def _build_governed_actions(priorities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for priority in priorities:
        actions = governed_actions_for(
            metric_id=str(priority["metric_id"]),
            discipline=priority.get("discipline"),
            phase=priority.get("phase"),
        )
        for action in actions:
            rows.append(
                {
                    "linked_metric_id": priority["metric_id"],
                    "linked_repetition_ids": priority["supporting_repetition_ids"],
                    "observed_pattern": priority["observed_pattern"],
                    "evidence_validity": priority["validity_state"],
                    "evidence_confidence": priority["confidence_score"],
                    "evidence_limitations": priority["limitations"],
                    **action,
                }
            )
    return rows


def _sanitize_selection(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    return {
        "available": bool(payload.get("available")),
        "repetition_id": _safe_text(payload.get("repetition_id")),
        "rationale": _safe_text(payload.get("rationale") or payload.get("reason")),
        "confidence_score": _finite_number(payload.get("confidence_score"), minimum=0, maximum=1),
        "supporting_metrics": _safe_strings(payload.get("supporting_metrics")),
    }


def _sanitize_interventions(coach_goals: dict[str, Any] | None) -> list[dict[str, Any]]:
    payload = coach_goals.get("interventions") if isinstance(coach_goals, dict) else []
    rows: list[dict[str, Any]] = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "intervention_id": _safe_text(item.get("intervention_id")),
                "intervention_type": _safe_text(item.get("intervention_type")),
                "activity": _safe_text(item.get("activity")),
                "frequency": _safe_text(item.get("frequency")),
                "completion_state": _safe_text(item.get("completion_state")),
                "linked_goal_ids": _safe_strings(item.get("linked_goal_ids")),
                "governance_state": "coach_recorded",
                "player_facing_eligible": bool(item.get("visible_to_player", False)),
            }
        )
    return rows


def _sanitize_longitudinal(outcomes: dict[str, Any] | None) -> list[dict[str, Any]]:
    payload = outcomes.get("v2_target_evidence") if isinstance(outcomes, dict) else []
    rows: list[dict[str, Any]] = []
    for item in payload if isinstance(payload, list) else []:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "goal_id": _safe_text(item.get("goal_id")),
                "metric_id": _safe_text(item.get("metric_id")),
                "status": _safe_text(item.get("status")) or "insufficient_data",
                "confidence": _finite_number(item.get("confidence"), minimum=0, maximum=1),
                "baseline": _safe_observation(item.get("baseline")),
                "latest": _safe_observation(item.get("latest")),
                "limitations": _safe_strings(item.get("limitations")),
                "causation_claimed": False,
            }
        )
    return rows


def _safe_observation(payload: Any) -> dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    return {
        "job_id": _safe_text(payload.get("job_id")),
        "raw_value": _finite_number(payload.get("raw_value")),
        "unit": _safe_text(payload.get("unit")),
    }


def _collect_limitations(
    metrics: list[dict[str, Any]],
    phases: list[dict[str, Any]],
    repetitions: list[dict[str, Any]],
    session_analysis: dict[str, Any],
) -> list[str]:
    values: list[str] = []
    for metric in metrics:
        if metric["unavailable_reason"]:
            values.append(str(metric["unavailable_reason"]))
        values.extend(metric["limitations"])
    for phase in phases:
        values.extend(phase["limitations"])
    values.extend(
        str(item["insufficient_reason"]) for item in repetitions if item["insufficient_reason"]
    )
    for item in session_analysis.get("excluded_metrics", []):
        if isinstance(item, dict) and _safe_text(item.get("reason")):
            values.append(str(item["reason"]))
    return list(dict.fromkeys(values))


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_dicts(value: Any) -> list[dict[str, Any]]:
    return (
        [dict(item) for item in value if isinstance(item, dict)] if isinstance(value, list) else []
    )


def _safe_strings(value: Any) -> list[str]:
    return (
        [item for item in value if isinstance(item, str) and item.strip()]
        if isinstance(value, list)
        else []
    )


def _safe_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _finite_number(
    value: Any, *, minimum: float | None = None, maximum: float | None = None
) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    if minimum is not None and number < minimum:
        return None
    if maximum is not None and number > maximum:
        return None
    return number


def _safe_int(value: Any, *, minimum: int | None = None) -> int | None:
    number = _finite_number(value)
    if number is None or not number.is_integer():
        return None
    integer = int(number)
    return integer if minimum is None or integer >= minimum else None
