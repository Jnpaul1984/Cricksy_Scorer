from __future__ import annotations

import io
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import patch

import pdfplumber
import pytest
from reportlab.platypus import Paragraph

from backend.routes.coach_pro_plus import _build_job_v2_coaching_report
from backend.services.coach_report_v2 import (
    build_coaching_analysis_report_v2,
    has_persisted_v2_evidence,
)
from backend.services.pdf_export_service import generate_analysis_pdf
from backend.services.reports.coach_report_template import (
    render_coaching_analysis_report_v2,
)


def _metric(
    metric_id: str,
    *,
    discipline: str,
    phase: str,
    raw_value: float | None = 0.72,
    classification: str | None = "NEEDS_ATTENTION",
    validity: str = "VALID",
    unavailable_reason: str | None = None,
) -> dict[str, object]:
    return {
        "metric_version": "metric.v2",
        "metric_id": metric_id,
        "discipline": discipline,
        "action_type": "test_action",
        "repetition_id": "rep-1",
        "phase": phase,
        "raw_value": raw_value,
        "normalized_score": 0.72,
        "unit": "ratio",
        "classification_status": classification,
        "confidence_score": 0.86,
        "validity_state": validity,
        "unavailable_reason": unavailable_reason,
        "limitations": [],
        "evidence_refs": [{"evidence_id": "evidence-1"}],
        "timestamp_refs": [{"start_ts": 0.5, "end_ts": 1.1}],
        "frame_refs": [{"start_frame": 15, "end_frame": 33}],
    }


def _results(metric: dict[str, object]) -> dict[str, object]:
    metric_id = str(metric["metric_id"])
    discipline = str(metric["discipline"])
    phase = str(metric["phase"])
    signal = {
        "metric_id": metric_id,
        "discipline": discipline,
        "phase": phase,
        "severity": "medium",
        "confidence_score": 0.84,
        "valid_sample_count": 3,
        "summary": "A recurring persisted V2 pattern was observed.",
        "supporting_repetition_ids": ["rep-1", "rep-2", "rep-3"],
        "limitations": ["Comparable camera placement is required."],
    }
    return {
        "v2": {
            "validity_state": "VALID",
            "capture_profile": {"camera_view": "side_on"},
            "repetitions": [
                {
                    "repetition_id": f"rep-{index}",
                    "discipline": discipline,
                    "action_type": "test_action",
                    "start_ts": index - 0.5,
                    "end_ts": index + 0.1,
                    "start_frame": index * 15,
                    "end_frame": index * 15 + 18,
                    "segmentation_method": "persisted_test",
                    "segmentation_confidence": 0.91,
                    "validity_state": "VALID",
                }
                for index in range(1, 4)
            ],
            "phases": [
                {
                    "phase_id": "rep-1:phase",
                    "repetition_id": "rep-1",
                    "phase_name": phase,
                    "start_ts": 0.6,
                    "end_ts": 1.0,
                    "confidence": 0.88,
                    "validity_state": "VALID",
                    "limitations": [],
                }
            ],
            "metric_results": [metric],
        },
        "findings": {
            "v2_session_analysis": {
                "strengths": [],
                "recurring_concerns": [signal],
                "consistency_observations": [
                    {
                        "metric_id": metric_id,
                        "discipline": discipline,
                        "phase": phase,
                        "method": "normalized_spread",
                        "classification": "moderate",
                        "value": 0.18,
                        "confidence_score": 0.83,
                        "valid_sample_count": 3,
                        "excluded_repetition_count": 0,
                        "limitations": [],
                    }
                ],
                "best_repetition": {
                    "available": True,
                    "repetition_id": "rep-1",
                    "reason": "Strongest evidence-supported repetition.",
                    "confidence_score": 0.85,
                },
                "needs_work_repetition": {
                    "available": True,
                    "repetition_id": "rep-3",
                    "reason": "Most evidence-supported development example.",
                    "confidence_score": 0.82,
                },
                "excluded_metrics": [],
            }
        },
    }


def _paragraph_text(report: dict[str, object]) -> str:
    flowables = render_coaching_analysis_report_v2(report)
    return "\n".join(item.getPlainText() for item in flowables if isinstance(item, Paragraph))


def _pdf_text(pdf_bytes: bytes) -> str:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as document:
        return "\n".join(page.extract_text() or "" for page in document.pages)


def _pdf_sections(pdf_bytes: bytes) -> tuple[str, str]:
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as document:
        pages = [page.extract_text() or "" for page in document.pages]
    appendix_index = next(index for index, text in enumerate(pages) if "Technical appendix" in text)
    return "\n".join(pages[:appendix_index]), "\n".join(pages[appendix_index:])


@pytest.mark.parametrize(
    ("metric_id", "discipline", "phase", "expected_action"),
    [
        (
            "batting_setup_head_base_offset_ratio",
            "batting",
            "setup",
            "batting-base-alignment",
        ),
        (
            "pace_bowling_release_proxy_bowling_arm_angle_deg",
            "pace_bowling",
            "release_proxy_window",
            "pace-release-follow-through",
        ),
    ],
)
def test_v2_report_uses_persisted_evidence_and_discipline_registry(
    metric_id: str, discipline: str, phase: str, expected_action: str
) -> None:
    report = build_coaching_analysis_report_v2(
        results=_results(_metric(metric_id, discipline=discipline, phase=phase)),
        analysis_mode=discipline,
    )
    assert report["source"] == "persisted_video_analysis_v2"
    assert report["repetitions"][0]["repetition_id"] == "rep-1"
    assert report["phases"][0]["phase_name"] == phase
    assert report["development_priorities"][0]["metric_id"] == metric_id
    assert report["consistency_observations"][0]["classification"] == "moderate"
    assert report["representative_repetitions"]["best"]["repetition_id"] == "rep-1"
    assert expected_action in {action["action_id"] for action in report["governed_actions"]}
    assert {action["discipline"] for action in report["governed_actions"]} == {discipline}


def test_non_measurable_values_are_explicitly_unavailable() -> None:
    missing = _metric(
        "batting_contact_proxy_alignment_ratio",
        discipline="batting",
        phase="contact_proxy_window",
        raw_value=0.0,
        classification="STRONG",
        validity="MISSING_OBJECT_EVIDENCE",
        unavailable_reason="Ball and bat evidence was unavailable.",
    )
    results = _results(missing)

    report = build_coaching_analysis_report_v2(results=results, analysis_mode="batting")
    missing_output = report["metrics"][0]

    assert missing_output["raw_value"] is None
    assert missing_output["normalized_score"] is None
    assert missing_output["classification_status"] is None
    assert missing_output["proxy_state"] == "PROXY"
    assert missing_output["unavailable_reason"] == "Ball and bat evidence was unavailable."
    assert "Unavailable" in _paragraph_text(report)


@pytest.mark.parametrize(
    "raw_value",
    [None, float("nan"), float("inf"), float("-inf")],
    ids=["null", "nan", "positive-infinity", "negative-infinity"],
)
def test_invalid_numeric_concern_cannot_create_priority_or_governed_action(
    raw_value: float | None,
) -> None:
    metric = _metric(
        "batting_setup_head_base_offset_ratio",
        discipline="batting",
        phase="setup",
        raw_value=raw_value,
        classification="NEEDS_ATTENTION",
        validity="VALID",
    )

    report = build_coaching_analysis_report_v2(
        results=_results(metric),
        analysis_mode="batting",
    )
    output = report["metrics"][0]

    assert output["raw_value"] is None
    assert output["validity_state"] == "VALID"
    assert output["classification_status"] == "NEEDS_ATTENTION"
    assert output["unavailable_reason"]
    assert output["unavailable_reason"] in output["limitations"]
    assert report["development_priorities"] == []
    assert report["governed_actions"] == []
    assert "Unavailable" in _paragraph_text(report)


def test_finite_valid_concern_still_creates_priority_and_governed_action() -> None:
    report = build_coaching_analysis_report_v2(
        results=_results(
            _metric(
                "batting_setup_head_base_offset_ratio",
                discipline="batting",
                phase="setup",
                raw_value=0.72,
            )
        ),
        analysis_mode="batting",
    )

    assert [item["metric_id"] for item in report["development_priorities"]] == [
        "batting_setup_head_base_offset_ratio"
    ]
    assert [item["action_id"] for item in report["governed_actions"]] == ["batting-base-alignment"]


def test_job_api_presentation_uses_the_same_v2_report_source_as_pdf() -> None:
    results = _results(
        _metric(
            "batting_downswing_head_stability_score",
            discipline="batting",
            phase="downswing",
        )
    )
    report = _build_job_v2_coaching_report(
        SimpleNamespace(
            deep_results=results,
            quick_results=None,
            coach_goals=None,
            outcomes=None,
        ),
        "batting",
    )

    assert report is not None
    assert report["player_presentation"]["priorities"][0]["title"] == (
        "Head stability during downswing"
    )
    assert report["player_presentation"]["governed_actions"]


def test_governed_actions_require_coach_approval_and_longitudinal_is_non_causal() -> None:
    results = _results(
        _metric(
            "fielding_transfer_balance_ratio",
            discipline="fielding",
            phase="transfer",
        )
    )
    report = build_coaching_analysis_report_v2(
        results=results,
        analysis_mode="fielding",
        coach_goals={
            "interventions": [
                {
                    "intervention_id": "int-1",
                    "activity": "Coach-entered transfer drill",
                    "completion_state": "planned",
                    "visible_to_player": False,
                }
            ]
        },
        outcomes={
            "v2_target_evidence": [
                {
                    "goal_id": "goal-1",
                    "metric_id": "fielding_transfer_balance_ratio",
                    "status": "improved",
                    "confidence": 0.8,
                    "baseline": {"job_id": "job-1", "raw_value": 0.61, "unit": "ratio"},
                    "latest": {"job_id": "job-2", "raw_value": 0.72, "unit": "ratio"},
                    "limitations": ["Observational comparison only."],
                }
            ]
        },
    )

    assert all(action["requires_coach_approval"] for action in report["governed_actions"])
    assert all(not action["player_facing_eligible"] for action in report["governed_actions"])
    assert report["coach_recorded_interventions"][0]["governance_state"] == "coach_recorded"
    assert report["longitudinal_goal_evidence"][0]["causation_claimed"] is False


def test_v2_pdf_bypasses_unsafe_legacy_findings_and_free_form_suggestions() -> None:
    metric = _metric(
        "pace_bowling_release_arm_angle_degrees",
        discipline="pace_bowling",
        phase="release",
    )
    metric["evidence_refs"] = [
        {"ref_type": "repetition_phase", "ref_id": "rep-1:release", "label": "Release"}
    ]
    metric["timestamp_refs"] = [{"start_ts": 28.12, "end_ts": 31.44}]
    metric["frame_refs"] = [{"start_frame": 842, "end_frame": 943}]
    results = _results(metric)
    with (
        patch(
            "backend.services.pdf_export_service.consolidate_findings",
            side_effect=AssertionError("legacy findings must not be read for V2 reports"),
        ),
        patch(
            "backend.services.pdf_export_service.render_coaching_suggestions",
            side_effect=AssertionError("free-form suggestions must not render for V2 reports"),
        ),
    ):
        pdf_bytes = generate_analysis_pdf(
            job_id="job-v2",
            session_title="V2 session",
            status="completed",
            quick_findings={"findings": [{"title": "Suspend intensive batting"}]},
            deep_findings={"findings": [{"title": "Injury risk"}]},
            quick_results=None,
            deep_results=results,
            created_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
            analysis_mode="pace_bowling",
            coach_suggestions={"weekly_plan": "Stop all match practice"},
        )

    text = _pdf_text(pdf_bytes)
    player_text, appendix_text = _pdf_sections(pdf_bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1_000
    assert "1. How did I do?" in player_text
    assert "3 usable deliveries identified" in player_text
    assert "Bowling-arm angle at release" in player_text
    assert "High confidence" in player_text
    assert "What should I do in training?" in player_text
    assert "Technical appendix" in appendix_text
    assert "rep-1" not in player_text
    assert "pace_bowling_release_arm_angle_degrees" not in player_text
    assert "pace-release-follow-through" not in player_text
    assert "job-v2" not in player_text
    assert "rep-1" not in appendix_text
    assert "pace_bowling_release_arm_angle_degrees" in appendix_text
    assert "pace-release-follow-through" in appendix_text
    assert "job-v2" in appendix_text
    assert "Full repetition IDs, phase IDs, timestamps, frame ranges" in appendix_text
    assert "00:28.12\u201300:31.44" not in appendix_text
    assert "Frames 842\u2013943" not in appendix_text
    assert "rep-1:release" not in appendix_text
    assert "00:28.12\u201300:31.44" not in player_text
    assert "Frames 842\u2013943" not in player_text
    assert "Suspend intensive batting" not in text
    assert "Injury risk" not in text
    assert "Stop all match practice" not in text
    assert "batting-swing-balance" not in text


def test_batting_pdf_preserves_proxy_and_unavailable_evidence_without_zero_fallback() -> None:
    results = _results(
        _metric(
            "batting_setup_head_alignment_ratio",
            discipline="batting",
            phase="setup",
        )
    )
    results["v2"]["metric_results"].append(
        _metric(
            "batting_contact_proxy_alignment_ratio",
            discipline="batting",
            phase="contact_proxy_window",
            raw_value=0.0,
            classification="STRONG",
            validity="MISSING_OBJECT_EVIDENCE",
            unavailable_reason="Ball and bat evidence was unavailable.",
        )
    )
    results["v2"]["repetitions"] = [
        {
            **results["v2"]["repetitions"][0],
            "repetition_id": f"ba694e41-0000-0000-0000-00000000000{index}:rep:{index}",
            "action_type": "shot",
            "start_ts": float(index),
        }
        for index in range(1, 5)
    ]
    results["v2"]["phases"] = [
        {
            **results["v2"]["phases"][0],
            "phase_id": f"batting-phase-{index}",
            "repetition_id": results["v2"]["repetitions"][index - 1]["repetition_id"],
        }
        for index in range(1, 5)
    ]
    technical_report = build_coaching_analysis_report_v2(
        results=results,
        analysis_mode="batting",
    )
    assert len(technical_report["repetitions"]) == 4
    assert technical_report["repetitions"][0]["repetition_id"].startswith("ba694e41-")
    assert technical_report["metrics"][0]["timestamp_refs"]
    assert technical_report["metrics"][0]["frame_refs"]

    pdf_bytes = generate_analysis_pdf(
        job_id="job-batting-v2",
        session_title="Batting V2 session",
        status="completed",
        quick_findings={
            "findings": [
                {
                    "title": "Stop all match practice until technique improves",
                    "why_it_matters": "Unsupported injury-risk claim",
                }
            ]
        },
        deep_findings=None,
        quick_results=results,
        deep_results=None,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        analysis_mode="batting",
    )

    text = _pdf_text(pdf_bytes)
    player_text, appendix_text = _pdf_sections(pdf_bytes)
    normalized_player_text = " ".join(player_text.split())
    assert "4 usable shots identified" in player_text
    for index in range(1, 5):
        assert f"Shot {index}" not in player_text
    assert "Head alignment at setup" in player_text
    assert "Some measurements could not be made clearly" in normalized_player_text
    assert "ba694e41-" not in player_text
    assert "batting_setup_head_alignment_ratio" not in player_text
    assert "batting_contact_proxy_alignment_ratio" not in player_text
    assert "MISSING_OBJECT_EVIDENCE" not in player_text
    assert "DIRECT_OR_UNSPECIFIED" not in player_text
    assert "batting_contact_proxy_alignment_ratio" in appendix_text
    assert "MISSING_OBJECT_EVIDENCE" in appendix_text
    assert "proxy state PROXY" in appendix_text
    assert "Ball and bat evidence was unavailable." in appendix_text
    assert "Stop all match practice" not in text
    assert "injury-risk" not in text
    assert "Pass" not in text
    assert "Fail" not in text


def test_pdf_omits_unavailable_comparable_count_without_fabricating_a_number() -> None:
    results = _results(
        _metric(
            "batting_setup_head_base_offset_ratio",
            discipline="batting",
            phase="setup",
        )
    )
    results["findings"]["v2_session_analysis"]["recurring_concerns"] = []

    pdf_bytes = generate_analysis_pdf(
        job_id="job-count-unavailable",
        session_title="Count unavailable",
        status="completed",
        quick_findings=None,
        deep_findings=None,
        quick_results=results,
        deep_results=None,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        analysis_mode="batting",
    )

    player_text, _ = _pdf_sections(pdf_bytes)
    assert "Head position over the base at setup" in player_text
    assert "Comparable repetition count unavailable" not in player_text
    assert "0 comparable repetitions" not in player_text


def test_bowling_pdf_summarizes_two_delivery_insufficient_evidence_once() -> None:
    metric = _metric(
        "pace_bowling_release_proxy_bowling_arm_angle_deg",
        discipline="pace_bowling",
        phase="release_proxy_window",
        raw_value=None,
        classification=None,
        validity="INSUFFICIENT_REPETITIONS",
        unavailable_reason="At least 3 comparable deliveries are required.",
    )
    results = _results(metric)
    metric["evidence_refs"] = []
    metric["timestamp_refs"] = []
    metric["frame_refs"] = []
    results["v2"]["repetitions"] = [
        {
            **results["v2"]["repetitions"][0],
            "repetition_id": f"delivery-uuid-{index}:rep:{index}",
            "action_type": "delivery",
            "start_ts": float(index),
        }
        for index in range(1, 3)
    ]
    results["v2"]["phases"] = [
        {
            **results["v2"]["phases"][0],
            "phase_id": f"delivery-uuid-{index}:release_proxy_window",
            "repetition_id": results["v2"]["repetitions"][index - 1]["repetition_id"],
            "phase_name": "release_proxy_window",
            "requires_object_evidence": True,
        }
        for index in range(1, 3)
    ]
    analysis = results["findings"]["v2_session_analysis"]
    analysis["recurring_concerns"] = []
    analysis["consistency_observations"] = []
    analysis["best_repetition"] = {"available": False}
    analysis["needs_work_repetition"] = {"available": False}

    pdf_bytes = generate_analysis_pdf(
        job_id="job-bowling-two",
        session_title="Two deliveries",
        status="completed",
        quick_findings={"findings": [{"title": "High hip-shoulder issue"}]},
        deep_findings=None,
        quick_results=results,
        deep_results=None,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        analysis_mode="pace_bowling",
    )

    player_text, appendix_text = _pdf_sections(pdf_bytes)
    normalized_player_text = " ".join(player_text.split())
    assert "2 usable deliveries identified" in player_text
    assert "Delivery 1" not in player_text
    assert "Delivery 2" not in player_text
    assert "Approximate movement phase evidence" in normalized_player_text
    assert player_text.count("We detected 2 deliveries.") == 1
    assert "Full repetition IDs, phase IDs, timestamps, frame ranges" in appendix_text
    assert "Record at least 3 comparable deliveries" in player_text
    assert "Not enough evidence was available to confirm a development priority" in player_text
    assert "No governed training action is available" in player_text
    assert "pace_bowling_release_proxy_bowling_arm_angle_deg" not in player_text
    assert "INSUFFICIENT_REPETITIONS" not in player_text
    assert "delivery-uuid-" not in player_text
    assert "High hip-shoulder issue" not in player_text
    assert "pace_bowling_release_proxy_bowling_arm_angle_deg" in appendix_text
    assert "INSUFFICIENT_REPETITIONS" in appendix_text
    assert "delivery-uuid-1" not in appendix_text


def test_legacy_jobs_keep_historical_report_path() -> None:
    assert has_persisted_v2_evidence({"pose_summary": {"total_frames": 12}}) is False
    pdf_bytes = generate_analysis_pdf(
        job_id="job-legacy",
        session_title="Historical session",
        status="completed",
        quick_findings=None,
        deep_findings=None,
        quick_results={"pose_summary": {"total_frames": 12, "frames_with_pose": 9}},
        deep_results=None,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )

    assert pdf_bytes.startswith(b"%PDF")
    assert "Job ID: job-legacy" in _pdf_text(pdf_bytes)
