from __future__ import annotations

from types import SimpleNamespace

from backend.domain.coach_analysis_v2_contract import (
    CoachingMetricResultV2,
    RepetitionActionRecordV2,
    ValidityState,
)
from backend.services.coach_strength_consistency import (
    attach_strength_consistency_engine,
    build_metric_consistency,
    build_strength_consistency_analysis,
)


def _sample(repetition_id: str, value: float, confidence: float = 0.9) -> SimpleNamespace:
    return SimpleNamespace(
        repetition_id=repetition_id,
        phase_id=f"{repetition_id}:setup",
        value=value,
        confidence=confidence,
        start_ts=0.1,
        end_ts=0.2,
        start_frame=1,
        end_frame=2,
        evidence_refs=[],
    )


def _repetition(repetition_id: str) -> RepetitionActionRecordV2:
    return RepetitionActionRecordV2(
        repetition_id=repetition_id,
        session_id="session-1",
        job_id="job-1",
        discipline="batting",
        action_type="batting_shot",
        start_ts=0.1,
        end_ts=0.2,
        start_frame=1,
        end_frame=2,
        validity_state=ValidityState.VALID,
    )


def _metric(
    metric_id: str, classification: str, repetition_ids: list[str]
) -> CoachingMetricResultV2:
    consistency = {
        "status": "ANALYZED",
        "classification": "high",
        "method": "normalized_spread",
        "value": 0.04,
        "confidence_score": 0.88,
        "valid_sample_count": len(repetition_ids),
        "excluded_repetition_count": 0,
        "excluded_reasons": [],
        "limitations": [],
        "samples": [
            {
                "repetition_id": repetition_id,
                "classification_status": classification,
                "confidence_score": 0.88,
                "start_ts": 0.1,
                "end_ts": 0.2,
                "start_frame": 1,
                "end_frame": 2,
                "evidence_refs": [],
            }
            for repetition_id in repetition_ids
        ],
    }
    return CoachingMetricResultV2(
        metric_version="metric.v2",
        metric_id=metric_id,
        discipline=metric_id.split("_", 1)[0],
        raw_value=0.8,
        unit="ratio",
        confidence_score=0.88,
        validity_state=ValidityState.VALID,
        classification_status=classification,
        repetition_values=[0.8 for _ in repetition_ids],
        aggregate_stats={"count": len(repetition_ids), "repetition_count": len(repetition_ids)},
        consistency=consistency,
    )


def test_build_metric_consistency_classifies_stable_values_as_high_consistency() -> None:
    consistency = build_metric_consistency(
        metric_id="batting_setup_stance_width_ratio",
        unit="ratio",
        samples=[_sample("rep-1", 1.0), _sample("rep-2", 1.01), _sample("rep-3", 0.99)],
        valid_range=(0.8, 1.4),
        classification_fn=lambda value: "STRONG" if value and value >= 0.95 else "NEEDS_ATTENTION",
        validity_state=ValidityState.VALID,
        confidence_score=0.9,
        candidate_repetition_count=3,
    )

    assert consistency["status"] == "ANALYZED"
    assert consistency["method"] == "normalized_spread"
    assert consistency["classification"] == "high"
    assert consistency["valid_sample_count"] == 3
    assert consistency["excluded_repetition_count"] == 0


def test_build_metric_consistency_falls_back_when_cv_denominator_is_near_zero() -> None:
    consistency = build_metric_consistency(
        metric_id="pace_bowling_release_timing_seconds",
        unit="seconds",
        samples=[_sample("rep-1", -0.1), _sample("rep-2", 0.1), _sample("rep-3", 0.0)],
        valid_range=(-0.5, 0.5),
        classification_fn=lambda _value: "DEVELOPING",
        validity_state=ValidityState.VALID,
        confidence_score=0.82,
        candidate_repetition_count=3,
    )

    assert consistency["status"] == "ANALYZED"
    assert consistency["method"] == "normalized_spread"
    assert any(
        "Coefficient of variation was skipped" in item for item in consistency["limitations"]
    )


def test_build_metric_consistency_returns_insufficient_data_for_single_valid_sample() -> None:
    consistency = build_metric_consistency(
        metric_id="fielding_recovery_balance_ratio",
        unit="ratio",
        samples=[_sample("rep-1", 0.8)],
        valid_range=(0.0, 1.0),
        classification_fn=lambda _value: "STRONG",
        validity_state=ValidityState.VALID,
        confidence_score=0.84,
        candidate_repetition_count=3,
    )

    assert consistency["status"] == "INSUFFICIENT_DATA"
    assert consistency["excluded_repetition_count"] == 2


def test_build_strength_consistency_analysis_detects_recurring_signals_and_ranked_repetitions() -> (
    None
):
    repetitions = [_repetition("rep-1"), _repetition("rep-2"), _repetition("rep-3")]
    metric_results = [
        _metric("batting_setup_stance_width_ratio", "STRONG", ["rep-1", "rep-1", "rep-1"]),
        _metric("fielding_recovery_balance_ratio", "NEEDS_ATTENTION", ["rep-3", "rep-3", "rep-3"]),
    ]

    analysis = build_strength_consistency_analysis(
        metric_results=metric_results,
        repetitions=repetitions,
    )

    assert analysis["strengths"][0]["metric_id"] == "batting_setup_stance_width_ratio"
    assert analysis["recurring_concerns"][0]["metric_id"] == "fielding_recovery_balance_ratio"
    assert analysis["best_repetition"]["available"] is True
    assert analysis["best_repetition"]["repetition_id"] == "rep-1"
    assert analysis["needs_work_repetition"]["available"] is True
    assert analysis["needs_work_repetition"]["repetition_id"] == "rep-3"


def test_build_strength_consistency_analysis_requires_recurring_support_and_excludes_low_confidence() -> (
    None
):
    repetitions = [_repetition("rep-1"), _repetition("rep-2"), _repetition("rep-3")]
    recurring_candidate = _metric(
        "wicketkeeping_ready_base_width_ratio", "STRONG", ["rep-1", "rep-2"]
    )
    low_confidence_metric = _metric(
        "spin_bowling_release_alignment_ratio", "NEEDS_ATTENTION", ["rep-1", "rep-2", "rep-3"]
    )
    low_confidence_metric.validity_state = ValidityState.LOW_CONFIDENCE
    low_confidence_metric.unavailable_reason = "Confidence too low"

    analysis = build_strength_consistency_analysis(
        metric_results=[recurring_candidate, low_confidence_metric],
        repetitions=repetitions,
    )

    assert analysis["strengths"] == []
    assert analysis["recurring_concerns"] == []
    assert analysis["best_repetition"]["available"] is False
    assert analysis["needs_work_repetition"]["available"] is False
    assert analysis["excluded_metrics"][0]["metric_id"] == "spin_bowling_release_alignment_ratio"


def test_attach_strength_consistency_engine_updates_results_payload_additively() -> None:
    payload = {
        "v2": {
            "metric_results": [
                _metric(
                    "batting_setup_stance_width_ratio", "STRONG", ["rep-1", "rep-1", "rep-1"]
                ).model_dump(mode="json")
            ],
            "repetitions": [_repetition("rep-1").model_dump(mode="json")],
        },
        "findings": {},
        "report": {},
    }

    attach_strength_consistency_engine(payload)

    assert (
        payload["meta"]["strength_consistency_engine"]["analysis_version"]
        == "strength_consistency.v1"
    )
    assert "v2_session_analysis" in payload["findings"]
    assert "v2_session_analysis" in payload["report"]
