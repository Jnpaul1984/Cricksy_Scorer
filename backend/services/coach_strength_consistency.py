from __future__ import annotations

import math
from collections import Counter
from statistics import mean, pstdev
from typing import Any

from backend.domain.coach_analysis_v2_contract import (
    CoachingMetricResultV2,
    EvidenceRef,
    FrameRef,
    RepetitionActionRecordV2,
    TimestampRef,
    ValidityState,
)
from backend.services.coach_analysis_v2_compatibility import has_measurable_validity_state

CONSISTENCY_ANALYSIS_VERSION = "strength_consistency.v1"
MIN_CONSISTENCY_SAMPLES = 2
MIN_RECURRING_SAMPLES = 3
RECURRING_SUPPORT_RATIO = 2 / 3


def build_metric_consistency(
    *,
    metric_id: str,
    unit: str,
    samples: list[Any],
    valid_range: tuple[float, float],
    classification_fn: Any,
    validity_state: ValidityState,
    confidence_score: float | None,
    candidate_repetition_count: int | None = None,
    unavailable_reason: str | None = None,
) -> dict[str, Any]:
    sample_payloads = [_sample_payload(sample, classification_fn) for sample in samples]
    values = [sample["value"] for sample in sample_payloads if isinstance(sample.get("value"), float)]
    valid_sample_count = len(values)
    total_candidates = max(candidate_repetition_count or valid_sample_count, valid_sample_count)
    excluded_repetition_count = max(0, total_candidates - valid_sample_count)
    excluded_reasons = []
    limitations: list[str] = []

    if excluded_repetition_count > 0:
        excluded_reasons.append(
            "Some repetitions were excluded because they were not measurable or not applicable for this metric."
        )

    if not has_measurable_validity_state(validity_state):
        limitations.append(
            unavailable_reason or "This metric was not safely measurable for repeatability analysis."
        )
        return {
            "analysis_version": CONSISTENCY_ANALYSIS_VERSION,
            "status": "UNAVAILABLE",
            "comparable": False,
            "method": None,
            "value": None,
            "classification": "insufficient_data",
            "confidence_score": confidence_score,
            "confidence_label": _confidence_label(confidence_score),
            "valid_sample_count": valid_sample_count,
            "minimum_required_samples": MIN_CONSISTENCY_SAMPLES,
            "excluded_repetition_count": excluded_repetition_count,
            "excluded_reasons": excluded_reasons,
            "samples": sample_payloads,
            "limitations": limitations,
        }

    if validity_state == ValidityState.LOW_CONFIDENCE:
        limitations.append(
            "Low-confidence measurements were kept for visibility but excluded from strength and recurring-concern claims."
        )

    if valid_sample_count < MIN_CONSISTENCY_SAMPLES:
        limitations.append(
            f"At least {MIN_CONSISTENCY_SAMPLES} valid repetitions are required for repeatability analysis."
        )
        return {
            "analysis_version": CONSISTENCY_ANALYSIS_VERSION,
            "status": "INSUFFICIENT_DATA",
            "comparable": False,
            "method": None,
            "value": None,
            "classification": "insufficient_data",
            "confidence_score": confidence_score,
            "confidence_label": _confidence_label(confidence_score),
            "valid_sample_count": valid_sample_count,
            "minimum_required_samples": MIN_CONSISTENCY_SAMPLES,
            "excluded_repetition_count": excluded_repetition_count,
            "excluded_reasons": excluded_reasons,
            "samples": sample_payloads,
            "limitations": limitations,
        }

    spread = pstdev(values) if len(values) > 1 else 0.0
    consistency_method, consistency_value, derived_limitations = _resolve_consistency_method(
        unit=unit,
        valid_range=valid_range,
        values=values,
        spread=spread,
    )
    limitations.extend(derived_limitations)

    class_counts = Counter(
        str(sample.get("classification_status"))
        for sample in sample_payloads
        if isinstance(sample.get("classification_status"), str)
    )
    agreement_rate = (
        round(max(class_counts.values()) / valid_sample_count, 4)
        if class_counts and valid_sample_count > 0
        else None
    )

    return {
        "analysis_version": CONSISTENCY_ANALYSIS_VERSION,
        "status": "ANALYZED",
        "comparable": True,
        "method": consistency_method,
        "value": consistency_value,
        "classification": _classify_consistency(consistency_method, consistency_value),
        "spread": round(spread, 4),
        "agreement_rate": agreement_rate,
        "confidence_score": confidence_score,
        "confidence_label": _confidence_label(confidence_score),
        "valid_sample_count": valid_sample_count,
        "minimum_required_samples": MIN_CONSISTENCY_SAMPLES,
        "excluded_repetition_count": excluded_repetition_count,
        "excluded_reasons": excluded_reasons,
        "samples": sample_payloads,
        "limitations": limitations,
    }


def attach_strength_consistency_engine(results_payload: dict[str, Any]) -> dict[str, Any]:
    v2_payload = results_payload.get("v2")
    if not isinstance(v2_payload, dict):
        return results_payload

    metric_results = _parse_metric_results(v2_payload.get("metric_results"))
    repetitions = _parse_repetitions(v2_payload.get("repetitions"))
    analysis = build_strength_consistency_analysis(
        metric_results=metric_results,
        repetitions=repetitions,
    )

    results_payload.setdefault("meta", {})
    if isinstance(results_payload.get("meta"), dict):
        results_payload["meta"]["strength_consistency_engine"] = {
            "analysis_version": CONSISTENCY_ANALYSIS_VERSION,
            "strengths_count": len(analysis["strengths"]),
            "recurring_concerns_count": len(analysis["recurring_concerns"]),
            "consistency_metrics_count": len(analysis["consistency_observations"]),
            "best_repetition_id": analysis["best_repetition"].get("repetition_id"),
            "needs_work_repetition_id": analysis["needs_work_repetition"].get("repetition_id"),
        }

    findings_payload = results_payload.get("findings")
    if isinstance(findings_payload, dict):
        findings_payload["v2_session_analysis"] = analysis

    report_payload = results_payload.get("report")
    if isinstance(report_payload, dict):
        report_payload["v2_session_analysis"] = analysis

    return results_payload


def build_strength_consistency_analysis(
    *,
    metric_results: list[CoachingMetricResultV2],
    repetitions: list[RepetitionActionRecordV2],
) -> dict[str, Any]:
    applicable_metrics = [
        metric
        for metric in metric_results
        if isinstance(metric.consistency, dict) and metric.metric_id.count("_") >= 2
    ]
    repetition_lookup = {item.repetition_id: item for item in repetitions}
    strengths: list[dict[str, Any]] = []
    recurring_concerns: list[dict[str, Any]] = []
    consistency_observations: list[dict[str, Any]] = []
    excluded_metrics: list[dict[str, Any]] = []

    repetition_evidence: dict[str, dict[str, Any]] = {}

    for metric in applicable_metrics:
        consistency = metric.consistency or {}
        consistency_observations.append(
            {
                "metric_id": metric.metric_id,
                "discipline": str(metric.discipline),
                "phase": metric.phase,
                "method": consistency.get("method"),
                "value": consistency.get("value"),
                "classification": consistency.get("classification"),
                "confidence_score": consistency.get("confidence_score"),
                "confidence_label": consistency.get("confidence_label"),
                "valid_sample_count": consistency.get("valid_sample_count"),
                "excluded_repetition_count": consistency.get("excluded_repetition_count"),
                "excluded_reasons": consistency.get("excluded_reasons", []),
                "limitations": consistency.get("limitations", []),
            }
        )

        if metric.validity_state != ValidityState.VALID:
            excluded_metrics.append(
                {
                    "metric_id": metric.metric_id,
                    "discipline": str(metric.discipline),
                    "validity_state": metric.validity_state.value,
                    "reason": metric.unavailable_reason
                    or "Low-confidence or unsupported metric evidence was excluded from strength and concern detection.",
                }
            )
            continue

        samples = _extract_consistency_samples(consistency)
        if len(samples) < MIN_RECURRING_SAMPLES:
            continue

        strong_samples = [sample for sample in samples if sample.get("classification_status") == "STRONG"]
        weak_samples = [
            sample for sample in samples if sample.get("classification_status") == "NEEDS_ATTENTION"
        ]
        valid_sample_count = len(samples)
        strong_ratio = len(strong_samples) / valid_sample_count
        weak_ratio = len(weak_samples) / valid_sample_count

        if strong_samples or weak_samples:
            _accumulate_repetition_evidence(repetition_evidence, metric, samples, repetition_lookup)

        if strong_samples and not weak_samples and strong_ratio >= RECURRING_SUPPORT_RATIO:
            strengths.append(
                _build_session_signal(
                    signal_type="strength",
                    metric=metric,
                    supporting_samples=strong_samples,
                    valid_sample_count=valid_sample_count,
                    support_ratio=strong_ratio,
                )
            )
        if weak_samples and not strong_samples and weak_ratio >= RECURRING_SUPPORT_RATIO:
            recurring_concerns.append(
                _build_session_signal(
                    signal_type="concern",
                    metric=metric,
                    supporting_samples=weak_samples,
                    valid_sample_count=valid_sample_count,
                    support_ratio=weak_ratio,
                )
            )

    best_repetition = _select_repetition_signal(
        repetition_evidence=repetition_evidence,
        repetition_lookup=repetition_lookup,
        selection_type="best",
    )
    needs_work_repetition = _select_repetition_signal(
        repetition_evidence=repetition_evidence,
        repetition_lookup=repetition_lookup,
        selection_type="needs_work",
    )

    return {
        "analysis_version": CONSISTENCY_ANALYSIS_VERSION,
        "minimum_samples": {
            "consistency": MIN_CONSISTENCY_SAMPLES,
            "recurring_signal": MIN_RECURRING_SAMPLES,
        },
        "strengths": strengths,
        "recurring_concerns": recurring_concerns,
        "consistency_observations": consistency_observations,
        "best_repetition": best_repetition,
        "needs_work_repetition": needs_work_repetition,
        "excluded_metrics": excluded_metrics,
    }


def _sample_payload(sample: Any, classification_fn: Any) -> dict[str, Any]:
    value = _safe_float(getattr(sample, "value", None))
    classification_status = classification_fn(value) if value is not None else None
    evidence_refs = getattr(sample, "evidence_refs", None) or []
    return {
        "repetition_id": getattr(sample, "repetition_id", None),
        "phase_id": getattr(sample, "phase_id", None),
        "value": round(value, 4) if value is not None else None,
        "confidence_score": _safe_float(getattr(sample, "confidence", None)),
        "classification_status": classification_status,
        "start_ts": _safe_float(getattr(sample, "start_ts", None)),
        "end_ts": _safe_float(getattr(sample, "end_ts", None)),
        "start_frame": _safe_int(getattr(sample, "start_frame", None)),
        "end_frame": _safe_int(getattr(sample, "end_frame", None)),
        "evidence_refs": [
            ref.model_dump(mode="json") if isinstance(ref, EvidenceRef) else ref
            for ref in evidence_refs
            if isinstance(ref, (EvidenceRef, dict))
        ],
    }


def _resolve_consistency_method(
    *, unit: str, valid_range: tuple[float, float], values: list[float], spread: float
) -> tuple[str, float, list[str]]:
    limitations: list[str] = []
    mean_value = mean(values)
    if unit in {"degrees", "seconds"}:
        denominator = abs(mean_value)
        if denominator > 1e-6:
            cv = spread / denominator
            if math.isfinite(cv):
                return ("coefficient_of_variation", round(cv, 4), limitations)
        limitations.append(
            "Coefficient of variation was skipped because the average value was too close to zero."
        )

    valid_span = valid_range[1] - valid_range[0]
    normalized_spread = (spread / valid_span) if valid_span > 0 else spread
    return ("normalized_spread", round(normalized_spread, 4), limitations)


def _classify_consistency(method: str, value: float | None) -> str:
    if value is None:
        return "insufficient_data"
    if method == "coefficient_of_variation":
        if value <= 0.1:
            return "high"
        if value <= 0.2:
            return "moderate"
        return "low"
    if value <= 0.08:
        return "high"
    if value <= 0.16:
        return "moderate"
    return "low"


def _confidence_label(score: float | None) -> str:
    if score is None:
        return "unknown"
    if score >= 0.8:
        return "high"
    if score >= 0.6:
        return "medium"
    return "low"


def _parse_metric_results(payload: Any) -> list[CoachingMetricResultV2]:
    if not isinstance(payload, list):
        return []
    results: list[CoachingMetricResultV2] = []
    for item in payload:
        try:
            results.append(CoachingMetricResultV2.model_validate(item))
        except Exception:
            continue
    return results


def _parse_repetitions(payload: Any) -> list[RepetitionActionRecordV2]:
    if not isinstance(payload, list):
        return []
    repetitions: list[RepetitionActionRecordV2] = []
    for item in payload:
        try:
            repetitions.append(RepetitionActionRecordV2.model_validate(item))
        except Exception:
            continue
    return repetitions


def _extract_consistency_samples(consistency: dict[str, Any]) -> list[dict[str, Any]]:
    samples = consistency.get("samples")
    if not isinstance(samples, list):
        return []
    extracted: list[dict[str, Any]] = []
    for item in samples:
        if not isinstance(item, dict):
            continue
        repetition_id = item.get("repetition_id")
        if not isinstance(repetition_id, str) or not repetition_id:
            continue
        extracted.append(item)
    return extracted


def _build_session_signal(
    *,
    signal_type: str,
    metric: CoachingMetricResultV2,
    supporting_samples: list[dict[str, Any]],
    valid_sample_count: int,
    support_ratio: float,
) -> dict[str, Any]:
    metric_label = metric.metric_id.replace(str(metric.discipline) + "_", "").replace("_", " ")
    supporting_repetition_ids = [
        repetition_id
        for repetition_id in [sample.get("repetition_id") for sample in supporting_samples]
        if isinstance(repetition_id, str)
    ]
    return {
        "metric_id": metric.metric_id,
        "discipline": str(metric.discipline),
        "phase": metric.phase,
        "severity": _support_severity(support_ratio, len(supporting_samples), valid_sample_count),
        "confidence_score": metric.confidence_score,
        "confidence_label": _confidence_label(metric.confidence_score),
        "valid_sample_count": valid_sample_count,
        "supporting_sample_count": len(supporting_samples),
        "support_ratio": round(support_ratio, 4),
        "supporting_repetition_ids": supporting_repetition_ids,
        "summary": (
            f"Repeated strong {metric_label} evidence across {len(supporting_samples)} of {valid_sample_count} comparable repetitions."
            if signal_type == "strength"
            else f"Repeated needs-attention {metric_label} evidence across {len(supporting_samples)} of {valid_sample_count} comparable repetitions."
        ),
        "consistency_classification": (
            metric.consistency.get("classification") if isinstance(metric.consistency, dict) else None
        ),
        "evidence_refs": _supporting_evidence_refs(metric.evidence_refs, supporting_repetition_ids),
        "timestamp_refs": _supporting_timestamp_refs(supporting_samples),
        "frame_refs": _supporting_frame_refs(supporting_samples),
        "limitations": list(metric.limitations),
    }


def _support_severity(support_ratio: float, supporting_count: int, valid_sample_count: int) -> str:
    if supporting_count == valid_sample_count and valid_sample_count >= MIN_RECURRING_SAMPLES:
        return "high"
    if support_ratio >= 0.75:
        return "medium"
    return "low"


def _accumulate_repetition_evidence(
    repetition_evidence: dict[str, dict[str, Any]],
    metric: CoachingMetricResultV2,
    samples: list[dict[str, Any]],
    repetition_lookup: dict[str, RepetitionActionRecordV2],
) -> None:
    for sample in samples:
        repetition_id = sample.get("repetition_id")
        if not isinstance(repetition_id, str):
            continue
        rep_bucket = repetition_evidence.setdefault(
            repetition_id,
            {
                "positive": [],
                "negative": [],
                "neutral": [],
                "confidence_scores": [],
            },
        )
        sample_entry = {
            "metric_id": metric.metric_id,
            "phase": metric.phase,
            "classification_status": sample.get("classification_status"),
            "confidence_score": sample.get("confidence_score"),
            "start_ts": sample.get("start_ts"),
            "end_ts": sample.get("end_ts"),
            "start_frame": sample.get("start_frame"),
            "end_frame": sample.get("end_frame"),
            "evidence_refs": sample.get("evidence_refs", []),
        }
        status = sample.get("classification_status")
        if status == "STRONG":
            rep_bucket["positive"].append(sample_entry)
        elif status == "NEEDS_ATTENTION":
            rep_bucket["negative"].append(sample_entry)
        else:
            rep_bucket["neutral"].append(sample_entry)

        confidence_score = _safe_float(sample.get("confidence_score"))
        if confidence_score is not None:
            rep_bucket["confidence_scores"].append(confidence_score)

        repetition = repetition_lookup.get(repetition_id)
        if repetition is not None and "repetition" not in rep_bucket:
            rep_bucket["repetition"] = repetition


def _select_repetition_signal(
    *,
    repetition_evidence: dict[str, dict[str, Any]],
    repetition_lookup: dict[str, RepetitionActionRecordV2],
    selection_type: str,
) -> dict[str, Any]:
    if not repetition_evidence:
        return {"available": False, "reason": "No comparable repetition evidence was available."}

    if selection_type == "best":
        candidates = [
            (repetition_id, payload)
            for repetition_id, payload in repetition_evidence.items()
            if len(payload.get("positive", [])) > 0
        ]
        if not candidates:
            return {
                "available": False,
                "reason": "No repetition had enough positive metric evidence for best-repetition selection.",
            }
        sorted_candidates = sorted(
            candidates,
            key=lambda item: (
                -len(item[1].get("positive", [])),
                len(item[1].get("negative", [])),
            ),
        )
        top_positive = len(sorted_candidates[0][1].get("positive", []))
        top_negative = len(sorted_candidates[0][1].get("negative", []))
        if sum(
            1
            for _, payload in sorted_candidates
            if len(payload.get("positive", [])) == top_positive
            and len(payload.get("negative", [])) == top_negative
        ) > 1:
            return {"available": False, "reason": "Best repetition evidence was tied across repetitions."}
        repetition_id, payload = sorted_candidates[0]
    else:
        candidates = [
            (repetition_id, payload)
            for repetition_id, payload in repetition_evidence.items()
            if len(payload.get("negative", [])) > 0
        ]
        if not candidates:
            return {
                "available": False,
                "reason": "No repetition had enough negative metric evidence for needs-work selection.",
            }
        sorted_candidates = sorted(
            candidates,
            key=lambda item: (
                -len(item[1].get("negative", [])),
                len(item[1].get("positive", [])),
            ),
        )
        top_negative = len(sorted_candidates[0][1].get("negative", []))
        top_positive = len(sorted_candidates[0][1].get("positive", []))
        if sum(
            1
            for _, payload in sorted_candidates
            if len(payload.get("negative", [])) == top_negative
            and len(payload.get("positive", [])) == top_positive
        ) > 1:
            return {
                "available": False,
                "reason": "Needs-work repetition evidence was tied across repetitions.",
            }
        repetition_id, payload = sorted_candidates[0]

    repetition = repetition_lookup.get(repetition_id) or payload.get("repetition")
    positive_metrics = payload.get("positive", [])
    negative_metrics = payload.get("negative", [])
    confidence_scores = payload.get("confidence_scores", [])
    average_confidence = (
        round(sum(confidence_scores) / len(confidence_scores), 3) if confidence_scores else None
    )
    selection_metrics = positive_metrics if selection_type == "best" else negative_metrics
    return {
        "available": True,
        "repetition_id": repetition_id,
        "action_type": getattr(repetition, "action_type", None),
        "start_ts": getattr(repetition, "start_ts", None),
        "end_ts": getattr(repetition, "end_ts", None),
        "start_frame": getattr(repetition, "start_frame", None),
        "end_frame": getattr(repetition, "end_frame", None),
        "confidence_score": average_confidence,
        "confidence_label": _confidence_label(average_confidence),
        "positive_metric_count": len(positive_metrics),
        "negative_metric_count": len(negative_metrics),
        "supporting_metrics": [item["metric_id"] for item in selection_metrics],
        "rationale": (
            f"Selected because this repetition had {len(positive_metrics)} strong metric signals and {len(negative_metrics)} needs-attention signals."
            if selection_type == "best"
            else f"Selected because this repetition had {len(negative_metrics)} needs-attention metric signals and only {len(positive_metrics)} strong signals."
        ),
        "evidence_refs": [
            {"ref_type": "repetition_window", "ref_id": repetition_id, "label": f"repetition:{repetition_id}"}
        ],
        "timestamp_refs": _supporting_timestamp_refs(selection_metrics),
        "frame_refs": _supporting_frame_refs(selection_metrics),
    }


def _supporting_evidence_refs(
    evidence_refs: list[EvidenceRef], supporting_repetition_ids: list[str]
) -> list[dict[str, Any]]:
    supported = []
    repetition_id_set = set(supporting_repetition_ids)
    for ref in evidence_refs:
        if ref.ref_type == "repetition_window" and ref.ref_id not in repetition_id_set:
            continue
        supported.append(ref.model_dump(mode="json"))
    return supported


def _supporting_timestamp_refs(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for sample in samples:
        start_ts = _safe_float(sample.get("start_ts"))
        end_ts = _safe_float(sample.get("end_ts"))
        refs.append(TimestampRef(start_ts=start_ts, end_ts=end_ts).model_dump(mode="json"))
    return refs


def _supporting_frame_refs(samples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for sample in samples:
        start_frame = _safe_int(sample.get("start_frame"))
        end_frame = _safe_int(sample.get("end_frame"))
        refs.append(FrameRef(start_frame=start_frame, end_frame=end_frame).model_dump(mode="json"))
    return refs


def _safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _safe_int(value: Any) -> int | None:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number
