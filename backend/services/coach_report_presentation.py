from __future__ import annotations

from typing import Any

from backend.domain.coach_analysis_v2_contract import LOW_CONFIDENCE_THRESHOLD
from backend.services.coach_strength_consistency import MIN_RECURRING_SAMPLES

PLAYER_PRESENTATION_VERSION = "coaching_analysis_presentation.v1"
HIGH_CONFIDENCE_THRESHOLD = 0.8

METRIC_LABELS: dict[str, str] = {
    "batting_setup_stance_width_ratio": "Stance width at setup",
    "batting_setup_head_base_offset_ratio": "Head position over the base at setup",
    "batting_trigger_head_displacement_ratio": "Head movement during the trigger",
    "batting_downswing_head_stability_score": "Head stability during downswing",
    "batting_contact_proxy_front_knee_angle_deg": "Front knee position near contact",
    "batting_follow_through_balance_drift_ratio": "Balance through the follow through",
    "pace_bowling_approach_head_stability_score": "Head stability during the approach",
    "pace_bowling_gather_balance_drift_ratio": "Balance through the gather",
    "pace_bowling_front_foot_contact_front_knee_angle_deg": "Front knee position at front-foot contact",
    "pace_bowling_release_proxy_bowling_arm_angle_deg": "Bowling-arm angle near release",
    "pace_bowling_release_proxy_trunk_lean_deg": "Body lean near release",
    "pace_bowling_follow_through_balance_drift_ratio": "Balance through the follow through",
    "spin_bowling_approach_head_stability_score": "Head stability during the approach",
    "spin_bowling_coil_balance_drift_ratio": "Balance through the coil",
    "spin_bowling_pivot_shoulder_hip_separation_deg": "Shoulder and hip position during the pivot",
    "spin_bowling_delivery_stride_head_base_offset_ratio": "Head position through the delivery stride",
    "spin_bowling_release_proxy_bowling_arm_angle_deg": "Bowling-arm angle near release",
    "spin_bowling_follow_through_balance_drift_ratio": "Balance through the follow through",
    "wicketkeeping_set_stance_width_ratio": "Stance width in the set position",
    "wicketkeeping_set_knee_flexion_angle_deg": "Knee bend in the set position",
    "wicketkeeping_reaction_head_stability_score": "Head stability while reading the ball",
    "wicketkeeping_movement_lateral_displacement_ratio": "Lateral movement into the take",
    "wicketkeeping_collection_balance_drift_ratio": "Balance during collection",
    "wicketkeeping_recovery_head_base_offset_ratio": "Head position during recovery",
    "wicketkeeping_context_standing_set_depth_delta_ratio": "Set-position depth when standing up",
    "wicketkeeping_leg_side_movement_lateral_displacement_ratio": "Movement to the leg side",
    "wicketkeeping_stumping_action_wrist_compactness_ratio": "Hand position during the stumping action",
    "fielding_ready_stance_width_ratio": "Stance width in the ready position",
    "fielding_reaction_head_stability_score": "Head stability during reaction",
    "fielding_approach_balance_drift_ratio": "Balance during the approach",
    "fielding_ground_collection_body_drop_ratio": "Body position for ground-ball collection",
    "fielding_ground_collection_knee_flexion_angle_deg": "Knee bend during ground-ball collection",
    "fielding_ground_collection_head_base_offset_ratio": "Head position during ground-ball collection",
    "fielding_catch_collection_wrist_compactness_ratio": "Hand position during the catch",
    "fielding_transfer_balance_drift_ratio": "Balance during the transfer",
    "fielding_throw_action_shoulder_hip_separation_deg": "Shoulder and hip position during the throw",
    "fielding_recovery_balance_drift_ratio": "Balance after the fielding action",
    # Exact compatibility IDs retained by the Phase 10J.14 action registry.
    "batting_setup_head_alignment_ratio": "Head alignment at setup",
    "batting_contact_proxy_alignment_ratio": "Body alignment near contact",
    "pace_bowling_release_arm_angle_degrees": "Bowling-arm angle at release",
    "spin_bowling_pivot_alignment_ratio": "Body alignment during the pivot",
    "wicketkeeping_ready_base_width_ratio": "Stance width in the ready position",
    "fielding_collection_head_base_ratio": "Head position during collection",
    "fielding_transfer_balance_ratio": "Balance during the transfer",
}

PHASE_LABELS: dict[str, str] = {
    "setup": "Setup",
    "trigger": "Trigger",
    "backlift": "Backlift",
    "downswing": "Downswing",
    "contact": "Contact",
    "contact_proxy_window": "Contact estimate",
    "follow_through": "Follow through",
    "approach": "Approach",
    "gather": "Gather",
    "back_foot_contact": "Back-foot contact",
    "delivery_stride": "Delivery stride",
    "front_foot_contact": "Front-foot contact",
    "release": "Release",
    "release_proxy_window": "Release estimate",
    "coil": "Coil",
    "pivot": "Pivot",
    "set": "Set position",
    "reaction_read": "Read and react",
    "reaction": "Reaction",
    "movement": "Movement",
    "collection": "Collection",
    "recovery": "Recovery",
    "action": "Action",
    "ready": "Ready position",
    "transfer": "Transfer",
    "throw_action": "Throwing action",
}

VALIDITY_LABELS: dict[str, str | None] = {
    "VALID": None,
    "INSUFFICIENT_VISIBILITY": "Could not measure clearly",
    "INSUFFICIENT_REPETITIONS": "Not enough repetitions",
    "LOW_CONFIDENCE": "Estimate only",
    "MISSING_OBJECT_EVIDENCE": "Required ball or equipment detail was not visible",
    "MISSING_PHASE": "Movement phase could not be identified",
    "UNSUPPORTED_CAMERA_VIEW": "Camera angle not suitable for this measurement",
    "INSUFFICIENT_FRAME_RATE": "Video frame rate was too low for this measurement",
    "INVALID_RANGE": "Measurement could not be used reliably",
    "NOT_MEASURABLE": "Could not measure clearly",
    "UNAVAILABLE": "Evidence unavailable",
}

DISCIPLINE_LABELS = {
    "batting": "Batting",
    "pace_bowling": "Pace bowling",
    "spin_bowling": "Spin bowling",
    "bowling": "Bowling",
    "wicketkeeping": "Wicketkeeping",
    "fielding": "Fielding",
}

PROXY_METRIC_IDS = frozenset(
    {
        "batting_contact_proxy_front_knee_angle_deg",
        "pace_bowling_release_proxy_bowling_arm_angle_deg",
        "pace_bowling_release_proxy_trunk_lean_deg",
        "spin_bowling_release_proxy_bowling_arm_angle_deg",
        "batting_contact_proxy_alignment_ratio",
    }
)

ACTION_REPETITION_NOUNS = {
    "batting_shot": "Shot",
    "shot": "Shot",
    "bowling_delivery": "Delivery",
    "delivery": "Delivery",
    "wicketkeeping_action": "Keeping attempt",
    "wicketkeeping_take": "Take",
    "standing_take": "Take",
    "stumping_action": "Stumping",
    "fielding_action": "Fielding attempt",
    "fielding_catch": "Catch",
    "catch_collection": "Catch",
    "fielding_throw": "Throw",
    "throw_action": "Throw",
}


def metric_display_name(metric_id: str | None) -> str:
    if not metric_id:
        return "Technique measurement"
    return METRIC_LABELS.get(metric_id, "Technique measurement")


def phase_display_name(phase_id: str | None) -> str:
    if not phase_id:
        return "Movement phase"
    return PHASE_LABELS.get(phase_id, "Movement phase")


def confidence_band(score: Any) -> str:
    if not isinstance(score, int | float) or isinstance(score, bool):
        return "Confidence unavailable"
    if score >= HIGH_CONFIDENCE_THRESHOLD:
        return "High confidence"
    if score >= LOW_CONFIDENCE_THRESHOLD:
        return "Medium confidence"
    return "Low confidence"


def validity_wording(state: str | None, discipline: str | None = None) -> str | None:
    if state == "INSUFFICIENT_REPETITIONS":
        noun = _repetition_noun(discipline, plural=True).lower()
        return f"Not enough {noun}"
    return VALIDITY_LABELS.get(state or "UNAVAILABLE", "Could not measure reliably")


def proxy_wording(metric_id: str | None, phase: str | None = None) -> str | None:
    if metric_id in PROXY_METRIC_IDS or phase in {"contact_proxy_window", "release_proxy_window"}:
        return "Approximate measurement"
    return None


def repetition_display_name(discipline: str | None, action_type: str | None, index: int) -> str:
    noun = ACTION_REPETITION_NOUNS.get(
        (action_type or "").lower(), _repetition_noun(discipline, plural=False)
    )
    return f"{noun} {index}"


def consistency_wording(classification: str | None) -> str:
    return {
        "high": "Very repeatable",
        "moderate": "Mostly repeatable",
        "low": "Varied between repetitions",
        "insufficient_data": "Not enough repetitions to judge consistency",
    }.get(classification or "", "Consistency unavailable")


def progress_wording(status: str | None) -> str:
    return {
        "improved": "Improving",
        "improving": "Improving",
        "improving_but_not_achieved": "Improving",
        "achieved": "Improving",
        "unchanged": "Stable",
        "stable": "Stable",
        "regressing": "Needs attention",
        "mixed": "Needs attention",
        "insufficient_data": "Not enough sessions yet",
        "non_comparable": "Cannot compare yet",
    }.get(status or "", "Cannot compare yet")


def build_longitudinal_presentation(progress: dict[str, Any]) -> dict[str, Any]:
    """Translate persisted longitudinal results without changing their calculations."""
    series = progress.get("series", [])
    comparable = [item for item in series if item.get("comparable_session_count", 0) >= 2]
    if not series:
        return {
            "state": "Cannot compare yet",
            "summary": "No comparable session evidence is available.",
            "items": [],
        }
    if not comparable:
        return {
            "state": "Not enough sessions yet",
            "summary": "Complete another comparable session to start tracking progress.",
            "items": [],
        }

    items = [
        {
            "metric_id": item.get("metric_id"),
            "title": metric_display_name(item.get("metric_id")),
            "discipline": DISCIPLINE_LABELS.get(item.get("discipline"), "Cricket"),
            "state": progress_wording(item.get("trend", {}).get("state")),
            "baseline": _longitudinal_value(item.get("baseline"), item.get("unit")),
            "latest": _longitudinal_value(item.get("latest"), item.get("unit")),
            "comparable_session_count": item.get("comparable_session_count"),
            "limitations": item.get("trend", {}).get("limitations", []),
        }
        for item in comparable
    ]
    states = [item["state"] for item in items]
    if "Needs attention" in states:
        overall = "Needs attention"
    elif states and all(state == "Improving" for state in states):
        overall = "Improving"
    else:
        overall = "Stable"
    summary = {
        "Improving": "Comparable session evidence is moving in the intended direction.",
        "Needs attention": "Recent comparable evidence includes an area that needs attention.",
        "Stable": "Comparable session evidence is broadly stable.",
    }[overall]
    return {"state": overall, "summary": summary, "items": items}


def format_metric_value(value: Any, unit: str | None) -> str:
    if not isinstance(value, int | float) or isinstance(value, bool):
        return "Unavailable"
    if unit == "degrees":
        return f"{value:.1f}°"
    if unit == "score":
        return f"{value * 100:.0f}%"
    return f"{value:.3f}".rstrip("0").rstrip(".") + (f" {unit}" if unit else "")


def _longitudinal_value(observation: Any, unit: str | None) -> str:
    if not isinstance(observation, dict):
        return "Unavailable"
    return format_metric_value(observation.get("raw_value"), unit)


def build_player_presentation(report: dict[str, Any]) -> dict[str, Any]:
    repetitions = sorted(
        report.get("repetitions", []),
        key=lambda item: (
            item.get("start_ts") if item.get("start_ts") is not None else float("inf"),
            item.get("start_frame") if item.get("start_frame") is not None else float("inf"),
        ),
    )
    repetition_labels = {
        item.get("repetition_id"): repetition_display_name(
            item.get("discipline") or report.get("analysis_mode"), item.get("action_type"), index
        )
        for index, item in enumerate(repetitions, 1)
        if item.get("repetition_id")
    }
    usable_repetitions = [
        item for item in repetitions if item.get("validity_state") in {"VALID", "LOW_CONFIDENCE"}
    ]
    metrics = report.get("metrics", [])
    measurable_metrics = [item for item in metrics if item.get("raw_value") is not None]
    discipline = _discipline(report, repetitions, metrics)
    has_recurring_sample_minimum = len(usable_repetitions) >= MIN_RECURRING_SAMPLES
    priorities = (
        report.get("development_priorities", [])[:3] if has_recurring_sample_minimum else []
    )
    actions = report.get("governed_actions", []) if has_recurring_sample_minimum else []
    action_by_metric = {item.get("linked_metric_id"): item for item in actions}
    has_insufficient_metrics = any(
        item.get("validity_state") == "INSUFFICIENT_REPETITIONS" for item in metrics
    )
    insufficient = (
        not priorities
        and not actions
        and (has_insufficient_metrics or len(usable_repetitions) < MIN_RECURRING_SAMPLES)
    )

    return {
        "presentation_version": PLAYER_PRESENTATION_VERSION,
        "discipline": discipline,
        "discipline_label": DISCIPLINE_LABELS.get(discipline or "", "Cricket"),
        "usable_repetition_count": len(usable_repetitions),
        "repetition_count": len(repetitions),
        "analysis_quality": _analysis_quality(measurable_metrics, metrics),
        "session_summary": _session_summary(
            discipline, len(usable_repetitions), measurable_metrics, metrics
        ),
        "insufficient_evidence": _insufficient_evidence(
            discipline, len(usable_repetitions), bool(report.get("phases")), insufficient
        ),
        "repetitions": [
            {
                "repetition_id": item.get("repetition_id"),
                "label": repetition_labels.get(item.get("repetition_id"), "Repetition"),
                "confidence": confidence_band(item.get("segmentation_confidence")),
                "validity": validity_wording(item.get("validity_state"), discipline),
                "start_ts": item.get("start_ts"),
                "end_ts": item.get("end_ts"),
            }
            for item in repetitions
        ],
        "phases": [
            {
                "phase_id": item.get("phase_id"),
                "label": phase_display_name(item.get("phase_name")),
                "repetition_label": repetition_labels.get(item.get("repetition_id"), "Repetition"),
                "confidence": confidence_band(item.get("confidence")),
                "validity": validity_wording(item.get("validity_state"), discipline),
                "proxy": (
                    "Approximate movement phase" if item.get("requires_object_evidence") else None
                ),
            }
            for item in report.get("phases", [])
        ],
        "metrics": [
            _present_metric(item, discipline)
            for item in metrics
            if item.get("raw_value") is not None
        ],
        "strengths": [
            _present_signal(item, repetition_labels) for item in report.get("strengths", [])
        ],
        "priorities": [
            _present_priority(item, action_by_metric.get(item.get("metric_id")), repetition_labels)
            for item in priorities
        ],
        "governed_actions": _present_actions(actions),
        "consistency": [
            {
                "title": metric_display_name(item.get("metric_id")),
                "state": consistency_wording(item.get("classification")),
                "repetition_count": item.get("valid_sample_count"),
            }
            for item in report.get("consistency_observations", [])
        ],
        "representative_repetitions": _present_selections(
            report.get("representative_repetitions", {}), repetition_labels
        ),
        "progress": _present_progress(report.get("longitudinal_goal_evidence", [])),
    }


def _present_metric(item: dict[str, Any], discipline: str | None) -> dict[str, Any]:
    return {
        "metric_id": item.get("metric_id"),
        "label": metric_display_name(item.get("metric_id")),
        "phase": phase_display_name(item.get("phase")),
        "value": format_metric_value(item.get("raw_value"), item.get("unit")),
        "confidence": confidence_band(item.get("confidence_score")),
        "validity": validity_wording(item.get("validity_state"), discipline),
        "proxy": proxy_wording(item.get("metric_id"), item.get("phase")),
        "classification": (
            "Needs attention"
            if item.get("classification_status") == "NEEDS_ATTENTION"
            else "Doing well"
            if item.get("classification_status") == "STRONG"
            else None
        ),
    }


def _present_signal(
    item: dict[str, Any], repetition_labels: dict[str | None, str]
) -> dict[str, Any]:
    labels = [
        repetition_labels[rep_id]
        for rep_id in item.get("supporting_repetition_ids", [])
        if rep_id in repetition_labels
    ]
    return {
        "metric_id": item.get("metric_id"),
        "title": metric_display_name(item.get("metric_id")),
        "observation": item.get("summary") or "A repeatable pattern was measured.",
        "repetition_count": _comparable_repetition_count(item, labels),
        "repetition_labels": labels,
        "confidence": confidence_band(item.get("confidence_score")),
        "limitations": item.get("limitations", []),
    }


def _present_priority(
    item: dict[str, Any],
    action: dict[str, Any] | None,
    repetition_labels: dict[str | None, str],
) -> dict[str, Any]:
    presented = _present_signal(item, repetition_labels)
    presented.update(
        {
            "observation": (
                "This movement pattern needs attention in the comparable repetitions."
                if item.get("observed_pattern")
                == "This persisted V2 metric was classified as needs attention."
                else item.get("observed_pattern") or presented["observation"]
            ),
            "why_it_matters": (
                action.get("why_it_matters")
                if action
                else "Improving this can make the movement easier to repeat."
            ),
            "phase": phase_display_name(item.get("phase")),
            "proxy": proxy_wording(item.get("metric_id"), item.get("phase")),
        }
    )
    return presented


def _present_action(item: dict[str, Any]) -> dict[str, Any]:
    linked_metric_id = item.get("linked_metric_id")
    return {
        "action_id": item.get("action_id"),
        "linked_metric_id": linked_metric_id,
        "linked_metric_ids": [linked_metric_id] if linked_metric_id else [],
        "title": item.get("technical_area"),
        "observed_issue": metric_display_name(item.get("linked_metric_id")),
        "coaching_goal": item.get("coaching_objective"),
        "cue": item.get("coaching_cue"),
        "drills": item.get("drills", [])[:3],
        "coach_watches_for": item.get("coach_observation"),
        "reassess": item.get("reassessment_criterion"),
        "requires_coach_approval": item.get("requires_coach_approval"),
        "review_status": item.get("review_status"),
    }


def _present_actions(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    presented: list[dict[str, Any]] = []
    by_action_id: dict[str, dict[str, Any]] = {}
    for item in items:
        action = _present_action(item)
        action_id = item.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            presented.append(action)
            continue

        existing = by_action_id.get(action_id)
        if existing is None:
            by_action_id[action_id] = action
            presented.append(action)
            continue

        for metric_id in action["linked_metric_ids"]:
            if metric_id not in existing["linked_metric_ids"]:
                existing["linked_metric_ids"].append(metric_id)
    return presented


def _comparable_repetition_count(item: dict[str, Any], labels: list[str]) -> int | None:
    valid_sample_count = item.get("valid_sample_count")
    if (
        isinstance(valid_sample_count, int)
        and not isinstance(valid_sample_count, bool)
        and valid_sample_count > 0
    ):
        return valid_sample_count
    if labels:
        return len(set(labels))
    return None


def _present_selections(
    selections: dict[str, Any], repetition_labels: dict[str | None, str]
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key in ("best", "needs_work"):
        item = selections.get(key) if isinstance(selections, dict) else None
        result[key] = {
            "available": bool(item and item.get("available")),
            "label": repetition_labels.get(item.get("repetition_id")) if item else None,
            "rationale": item.get("rationale") if item else None,
            "confidence": confidence_band(item.get("confidence_score")) if item else None,
        }
    return result


def _present_progress(items: list[dict[str, Any]]) -> dict[str, Any]:
    if not items:
        return {
            "state": "Not enough sessions yet",
            "summary": "Complete another comparable session to start tracking progress.",
            "items": [],
        }
    states = [progress_wording(item.get("status")) for item in items]
    if "Cannot compare yet" in states:
        overall = "Cannot compare yet"
    elif "Not enough sessions yet" in states:
        overall = "Not enough sessions yet"
    elif "Needs attention" in states:
        overall = "Needs attention"
    elif all(state == "Improving" for state in states):
        overall = "Improving"
    else:
        overall = "Stable"
    summary = {
        "Cannot compare yet": "The available sessions are not comparable yet.",
        "Not enough sessions yet": "Complete another comparable session to start tracking progress.",
        "Needs attention": "Recent comparable evidence shows an area that needs attention.",
        "Improving": "Comparable session evidence is moving in the intended direction.",
        "Stable": "Comparable session evidence is broadly stable.",
    }[overall]
    return {
        "state": overall,
        "summary": summary,
        "items": [
            {
                "title": metric_display_name(item.get("metric_id")),
                "state": progress_wording(item.get("status")),
                "confidence": confidence_band(item.get("confidence")),
            }
            for item in items
        ],
    }


def _analysis_quality(measurable: list[dict[str, Any]], metrics: list[dict[str, Any]]) -> str:
    if not metrics or not measurable:
        return "There was not enough clear evidence for reliable technique judgments."
    if len(measurable) == len(metrics):
        return "The recording provided clear evidence for the available technique review."
    return "The recording supported a partial technique review; some measurements were unavailable."


def _session_summary(
    discipline: str | None,
    repetition_count: int,
    measurable: list[dict[str, Any]],
    metrics: list[dict[str, Any]],
) -> str:
    noun = _repetition_noun(discipline, plural=repetition_count != 1).lower()
    if not metrics or not measurable:
        return (
            f"We identified {repetition_count} usable {noun}, but could not confirm reliable "
            "technique measurements from this recording."
        )
    available_names = list(
        dict.fromkeys(metric_display_name(item.get("metric_id")) for item in measurable)
    )
    reviewed = ", ".join(name.lower() for name in available_names[:3])
    unavailable = len(metrics) - len(measurable)
    suffix = " Some measurements could not be made clearly." if unavailable else ""
    return (
        f"We identified {repetition_count} usable {noun}. The recording supported review of "
        f"{reviewed}.{suffix}"
    )


def _insufficient_evidence(
    discipline: str | None, repetition_count: int, has_phases: bool, active: bool
) -> dict[str, Any]:
    if not active:
        return {"active": False}
    noun = _repetition_noun(discipline, plural=repetition_count != 1).lower()
    phase_clause = (
        "That is enough to review the movement phases, but not enough to make reliable "
        "technique judgments yet."
        if has_phases
        else "That is not enough to make reliable technique judgments yet."
    )
    return {
        "active": True,
        "title": f"We detected {repetition_count} {noun}.",
        "summary": phase_clause,
        "recommendation": (
            f"Record at least {MIN_RECURRING_SAMPLES} comparable "
            f"{_repetition_noun(discipline, plural=True).lower()} for a fuller analysis."
        ),
        "minimum_repetitions": MIN_RECURRING_SAMPLES,
    }


def _discipline(
    report: dict[str, Any], repetitions: list[dict[str, Any]], metrics: list[dict[str, Any]]
) -> str | None:
    for item in (*repetitions, *metrics):
        if item.get("discipline"):
            return str(item["discipline"])
    mode = report.get("analysis_mode")
    return str(mode) if mode else None


def _repetition_noun(discipline: str | None, *, plural: bool) -> str:
    singular, plural_name = {
        "batting": ("Shot", "Shots"),
        "pace_bowling": ("Delivery", "Deliveries"),
        "spin_bowling": ("Delivery", "Deliveries"),
        "bowling": ("Delivery", "Deliveries"),
        "wicketkeeping": ("Keeping attempt", "Keeping attempts"),
        "fielding": ("Fielding attempt", "Fielding attempts"),
    }.get(discipline or "", ("Repetition", "Repetitions"))
    return plural_name if plural else singular
