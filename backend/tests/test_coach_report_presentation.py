from __future__ import annotations

import pytest

from backend.services.coach_report_presentation import (
    METRIC_LABELS,
    build_longitudinal_presentation,
    build_player_presentation,
    confidence_band,
    metric_display_name,
    phase_display_name,
    progress_wording,
    proxy_wording,
    repetition_display_name,
    validity_wording,
)
from backend.services.coaching_action_registry import PRODUCTION_METRIC_ACTION_CONTRACTS


def _technical_report(
    *, repetitions: int = 2, metric_validity: str = "INSUFFICIENT_REPETITIONS"
) -> dict:
    return {
        "analysis_mode": "pace_bowling",
        "repetitions": [
            {
                "repetition_id": f"ba694e41-0000:rep:{index + 7}",
                "discipline": "pace_bowling",
                "action_type": "delivery",
                "start_ts": float(index),
                "start_frame": index * 10,
                "segmentation_confidence": 0.85,
                "validity_state": "VALID",
            }
            for index in range(repetitions)
        ],
        "phases": [
            {
                "phase_id": "ba694e41-0000:rep:7:release_proxy_window",
                "repetition_id": "ba694e41-0000:rep:7",
                "phase_name": "release_proxy_window",
                "confidence": 0.7,
                "validity_state": "LOW_CONFIDENCE",
                "requires_object_evidence": True,
            }
        ],
        "metrics": [
            {
                "metric_id": "pace_bowling_release_proxy_bowling_arm_angle_deg",
                "discipline": "pace_bowling",
                "phase": "release_proxy_window",
                "raw_value": None,
                "unit": "degrees",
                "confidence_score": 0.55,
                "validity_state": metric_validity,
                "classification_status": None,
            }
        ],
        "development_priorities": [],
        "strengths": [],
        "governed_actions": [],
        "consistency_observations": [],
        "representative_repetitions": {},
        "longitudinal_goal_evidence": [],
    }


def _report_with_supported_concern(repetitions: int) -> dict:
    report = _technical_report(repetitions=repetitions, metric_validity="VALID")
    report["metrics"][0].update(
        {
            "raw_value": 145.0,
            "classification_status": "NEEDS_ATTENTION",
        }
    )
    report["development_priorities"] = [
        {
            "metric_id": "pace_bowling_release_proxy_bowling_arm_angle_deg",
            "phase": "release_proxy_window",
            "valid_sample_count": 3,
            "confidence_score": 0.86,
            "supporting_repetition_ids": [item["repetition_id"] for item in report["repetitions"]],
            "observed_pattern": "This persisted V2 metric was classified as needs attention.",
            "limitations": [],
        }
    ]
    report["governed_actions"] = [
        {
            "action_id": "pace-release-follow-through",
            "linked_metric_id": "pace_bowling_release_proxy_bowling_arm_angle_deg",
            "technical_area": "Release and follow-through",
            "why_it_matters": "A repeatable release can improve control.",
            "coaching_objective": "Repeat the release shape.",
            "coaching_cue": "Reach tall through release.",
            "drills": ["Walk-through delivery"],
            "coach_observation": "A repeatable arm path.",
            "reassessment_criterion": "Compare the release estimate.",
            "requires_coach_approval": True,
            "review_status": "approved_for_coach_review",
        }
    ]
    return report


def test_every_production_metric_has_an_explicit_player_label() -> None:
    assert set(PRODUCTION_METRIC_ACTION_CONTRACTS) <= set(METRIC_LABELS)
    assert metric_display_name("batting_downswing_head_stability_score") == (
        "Head stability during downswing"
    )
    assert metric_display_name("batting_contact_proxy_front_knee_angle_deg") == (
        "Front knee position near contact"
    )
    assert metric_display_name("pace_bowling_release_proxy_bowling_arm_angle_deg") == (
        "Bowling-arm angle near release"
    )
    assert metric_display_name("unrelated_metric") == "Technique measurement"


@pytest.mark.parametrize(
    ("phase_id", "expected"),
    [
        ("contact_proxy_window", "Contact estimate"),
        ("release_proxy_window", "Release estimate"),
        ("front_foot_contact", "Front-foot contact"),
        ("follow_through", "Follow through"),
    ],
)
def test_phase_ids_have_plain_labels(phase_id: str, expected: str) -> None:
    assert phase_display_name(phase_id) == expected


@pytest.mark.parametrize(
    ("discipline", "action", "expected"),
    [
        ("batting", "shot", "Shot 4"),
        ("pace_bowling", "delivery", "Delivery 4"),
        ("spin_bowling", "delivery", "Delivery 4"),
        ("wicketkeeping", "stumping_action", "Stumping 4"),
        ("wicketkeeping", "standing_take", "Take 4"),
        ("fielding", "catch_collection", "Catch 4"),
        ("fielding", "throw_action", "Throw 4"),
    ],
)
def test_repetition_names_follow_discipline_and_action(
    discipline: str, action: str, expected: str
) -> None:
    assert repetition_display_name(discipline, action, 4) == expected


@pytest.mark.parametrize(
    ("score", "expected"),
    [
        (0.8, "High confidence"),
        (0.7999, "Medium confidence"),
        (0.6, "Medium confidence"),
        (0.5999, "Low confidence"),
        (None, "Confidence unavailable"),
    ],
)
def test_confidence_band_uses_canonical_boundaries(score: float | None, expected: str) -> None:
    assert confidence_band(score) == expected


def test_validity_and_proxy_states_use_player_language() -> None:
    assert validity_wording("VALID", "batting") is None
    assert validity_wording("INSUFFICIENT_VISIBILITY", "batting") == "Could not measure clearly"
    assert validity_wording("INSUFFICIENT_REPETITIONS", "pace_bowling") == ("Not enough deliveries")
    assert validity_wording("LOW_CONFIDENCE", "batting") == "Estimate only"
    assert proxy_wording("batting_contact_proxy_front_knee_angle_deg") == (
        "Approximate measurement"
    )
    assert proxy_wording("batting_setup_stance_width_ratio") is None
    assert proxy_wording("unrelated_proxy_named_metric") is None


def test_two_delivery_session_gets_one_contract_derived_insufficient_summary() -> None:
    presentation = build_player_presentation(_technical_report())

    assert [item["label"] for item in presentation["repetitions"]] == [
        "Delivery 1",
        "Delivery 2",
    ]
    assert presentation["insufficient_evidence"] == {
        "active": True,
        "title": "We detected 2 deliveries.",
        "summary": (
            "That is enough to review the movement phases, but not enough to make reliable "
            "technique judgments yet."
        ),
        "recommendation": "Record at least 3 comparable deliveries for a fuller analysis.",
        "minimum_repetitions": 3,
    }
    assert presentation["priorities"] == []
    assert presentation["governed_actions"] == []
    assert presentation["metrics"] == []


@pytest.mark.parametrize("repetition_count", [1, 2])
def test_subminimum_valid_concern_does_not_present_priority_or_action(
    repetition_count: int,
) -> None:
    presentation = build_player_presentation(_report_with_supported_concern(repetition_count))

    assert presentation["insufficient_evidence"]["active"] is True
    assert presentation["insufficient_evidence"]["minimum_repetitions"] == 3
    assert presentation["priorities"] == []
    assert presentation["governed_actions"] == []


def test_minimum_recurring_samples_allow_supported_priority_and_action() -> None:
    presentation = build_player_presentation(_report_with_supported_concern(3))

    assert presentation["insufficient_evidence"]["active"] is False
    assert [item["metric_id"] for item in presentation["priorities"]] == [
        "pace_bowling_release_proxy_bowling_arm_angle_deg"
    ]
    assert [item["linked_metric_id"] for item in presentation["governed_actions"]] == [
        "pace_bowling_release_proxy_bowling_arm_angle_deg"
    ]


def test_priority_uses_persisted_metric_specific_comparable_count() -> None:
    report = _report_with_supported_concern(43)
    report["development_priorities"][0]["valid_sample_count"] = 43

    presentation = build_player_presentation(report)

    assert presentation["priorities"][0]["repetition_count"] == 43


def test_priority_without_comparable_evidence_does_not_invent_zero() -> None:
    report = _report_with_supported_concern(3)
    priority = report["development_priorities"][0]
    priority.pop("valid_sample_count")
    priority["supporting_repetition_ids"] = []

    presentation = build_player_presentation(report)

    assert presentation["priorities"][0]["repetition_count"] is None


def test_supporting_repetition_ids_supply_a_metric_specific_count() -> None:
    report = _report_with_supported_concern(3)
    report["development_priorities"][0].pop("valid_sample_count")

    presentation = build_player_presentation(report)

    assert presentation["priorities"][0]["repetition_count"] == 3


def test_governed_actions_deduplicate_by_action_id_and_retain_metric_traceability() -> None:
    report = _report_with_supported_concern(3)
    duplicate = {
        **report["governed_actions"][0],
        "linked_metric_id": "pace_bowling_release_proxy_trunk_lean_deg",
    }
    report["governed_actions"].append(duplicate)

    presentation = build_player_presentation(report)

    assert len(presentation["governed_actions"]) == 1
    assert presentation["governed_actions"][0]["action_id"] == "pace-release-follow-through"
    assert presentation["governed_actions"][0]["linked_metric_ids"] == [
        "pace_bowling_release_proxy_bowling_arm_angle_deg",
        "pace_bowling_release_proxy_trunk_lean_deg",
    ]


def test_different_governed_action_ids_are_not_merged_when_wording_matches() -> None:
    report = _report_with_supported_concern(3)
    distinct = {
        **report["governed_actions"][0],
        "action_id": "pace-distinct-governed-action",
        "linked_metric_id": "pace_bowling_release_proxy_trunk_lean_deg",
    }
    report["governed_actions"].append(distinct)

    presentation = build_player_presentation(report)

    assert [item["action_id"] for item in presentation["governed_actions"]] == [
        "pace-release-follow-through",
        "pace-distinct-governed-action",
    ]


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("improved", "Improving"),
        ("unchanged", "Stable"),
        ("regressing", "Needs attention"),
        ("insufficient_data", "Not enough sessions yet"),
        ("non_comparable", "Cannot compare yet"),
    ],
)
def test_longitudinal_statuses_are_player_friendly(status: str, expected: str) -> None:
    assert progress_wording(status) == expected


def test_single_current_session_establishes_a_baseline() -> None:
    progress = build_player_presentation(_technical_report())["progress"]
    assert progress == {
        "state": "Baseline established",
        "summary": (
            "This is the player's first recorded assessment. Future comparable sessions will "
            "show what improved, stayed consistent, or needs more work."
        ),
        "items": [],
    }


def test_one_session_longitudinal_response_establishes_a_baseline() -> None:
    progress = build_longitudinal_presentation({"session_count": 1, "series": []})

    assert progress["state"] == "Baseline established"
    assert "first recorded assessment" in progress["summary"]


def test_valid_strong_metric_is_presented_as_a_current_session_positive() -> None:
    report = _technical_report(repetitions=3, metric_validity="VALID")
    report["metrics"][0].update({"raw_value": 145.0, "classification_status": "STRONG"})

    presentation = build_player_presentation(report)

    assert presentation["current_session_positives"] == [
        {
            "metric_id": "pace_bowling_release_proxy_bowling_arm_angle_deg",
            "title": "Bowling-arm angle near release",
            "observation": "This measurement looked good in this session.",
            "value": "145.0°",
            "phase": "Release estimate",
            "confidence": "Low confidence",
            "validity": None,
            "proxy": "Approximate measurement",
        }
    ]


def test_large_session_uses_concise_movement_summary_without_losing_evidence() -> None:
    report = _report_with_supported_concern(43)

    presentation = build_player_presentation(report)

    assert presentation["movement_summary"] == {
        "summary": "43 usable deliveries identified.",
        "phase_confidence_summary": (
            "1 phase observation across 1 movement phase: 1 medium confidence. "
            "Approximate movement phase evidence: 1 observation. Evidence note: Estimate only."
        ),
    }
    assert len(presentation["repetitions"]) == 43
    assert presentation["repetitions"][0]["repetition_id"] == "ba694e41-0000:rep:7"


def test_longitudinal_presentation_uses_plain_states_and_labels() -> None:
    progress = build_longitudinal_presentation(
        {
            "series": [
                {
                    "metric_id": "batting_downswing_head_stability_score",
                    "discipline": "batting",
                    "unit": "score",
                    "comparable_session_count": 2,
                    "baseline": {"raw_value": 0.61},
                    "latest": {"raw_value": 0.72},
                    "trend": {"state": "improving", "limitations": []},
                }
            ]
        }
    )

    assert progress == {
        "state": "Improving",
        "summary": "Comparable session evidence is moving in the intended direction.",
        "items": [
            {
                "metric_id": "batting_downswing_head_stability_score",
                "title": "Head stability during downswing",
                "discipline": "Batting",
                "state": "Improving",
                "baseline": "61%",
                "latest": "72%",
                "comparable_session_count": 2,
                "limitations": [],
            }
        ],
    }
