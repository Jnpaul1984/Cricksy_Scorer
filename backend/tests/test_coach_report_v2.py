from __future__ import annotations

import io
from datetime import UTC, datetime
from unittest.mock import patch

import pdfplumber
import pytest
from reportlab.platypus import Paragraph

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
                    "repetition_id": "rep-1",
                    "discipline": discipline,
                    "action_type": "test_action",
                    "start_ts": 0.5,
                    "end_ts": 1.1,
                    "start_frame": 15,
                    "end_frame": 33,
                    "segmentation_method": "persisted_test",
                    "segmentation_confidence": 0.91,
                    "validity_state": "VALID",
                }
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


@pytest.mark.parametrize(
    ("metric_id", "discipline", "phase", "expected_action"),
    [
        ("batting_setup_head_alignment_ratio", "batting", "setup", "batting-base-alignment"),
        (
            "pace_bowling_release_arm_angle_degrees",
            "pace_bowling",
            "release",
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


def test_non_measurable_and_non_finite_values_are_explicitly_unavailable() -> None:
    missing = _metric(
        "batting_contact_proxy_alignment_ratio",
        discipline="batting",
        phase="contact_proxy_window",
        raw_value=0.0,
        classification="STRONG",
        validity="MISSING_OBJECT_EVIDENCE",
        unavailable_reason="Ball and bat evidence was unavailable.",
    )
    unsafe = _metric(
        "batting_setup_head_alignment_ratio",
        discipline="batting",
        phase="setup",
        raw_value=float("nan"),
    )
    results = _results(missing)
    results["v2"]["metric_results"].append(unsafe)

    report = build_coaching_analysis_report_v2(results=results, analysis_mode="batting")
    missing_output, unsafe_output = report["metrics"]

    assert missing_output["raw_value"] is None
    assert missing_output["normalized_score"] is None
    assert missing_output["classification_status"] is None
    assert missing_output["proxy_state"] == "PROXY"
    assert missing_output["unavailable_reason"] == "Ball and bat evidence was unavailable."
    assert unsafe_output["raw_value"] is None
    assert "Unavailable" in _paragraph_text(report)


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
    results = _results(
        _metric(
            "pace_bowling_release_arm_angle_degrees",
            discipline="pace_bowling",
            phase="release",
        )
    )
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
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 1_000
    assert "Executive Coaching Summary" in text
    assert "Repetition & Phase Analysis" in text
    assert "rep-1" in text
    assert "release" in text
    assert "A recurring persisted V2 pattern was observed" in text
    assert "moderate" in text
    assert "pace-release-follow-through" in text
    assert "Appendix: Evidence & Limitations" in text
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
    assert "rep-1" in text
    assert "setup" in text
    assert "A recurring persisted V2 pattern was observed" in text
    assert "moderate" in text
    assert "Best: rep-1" in text
    assert "batting_contact_proxy_alignment_ratio" in text
    assert "MISSING_OBJECT_EVIDENCE / PROXY" in text
    assert "Unavailable:" in text
    assert "Ball and bat evidence was unavailable." in text
    assert "Stop all match practice" not in text
    assert "injury-risk" not in text
    assert "Pass" not in text
    assert "Fail" not in text


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
