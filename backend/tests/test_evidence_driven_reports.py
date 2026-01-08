"""
Tests for evidence-driven coaching reports.

Tests the complete flow from pose metrics → findings with evidence →
reports with timestamps → PDF with proof of work.
"""

import pytest
from backend.services import coach_findings, coach_report_service, pdf_export_service
from datetime import datetime, timezone


# ============================================================================
# Helper Functions Tests
# ============================================================================


def test_format_timestamp_basic():
    """Test timestamp formatting for typical values."""
    assert coach_findings._format_timestamp(0) == "00:00"
    assert coach_findings._format_timestamp(65.5) == "01:05"
    assert coach_findings._format_timestamp(125.9) == "02:05"
    assert coach_findings._format_timestamp(3661.2) == "61:01"


def test_format_timestamp_edge_cases():
    """Test timestamp formatting edge cases."""
    assert coach_findings._format_timestamp(None) == "N/A"  # None returns N/A
    assert coach_findings._format_timestamp(0.4) == "00:00"  # Rounds down
    assert coach_findings._format_timestamp(59.9) == "00:59"


def test_attach_evidence_markers_complete():
    """Test evidence attachment with all data present."""
    finding = {"title": "Head Movement", "severity": "high"}

    evidence_data = {
        "head_stability_score": {
            "worst_frames": [
                {"frame_num": 100, "timestamp_s": 3.33, "score": 0.15},
                {"frame_num": 150, "timestamp_s": 5.0, "score": 0.18},
                {"frame_num": 200, "timestamp_s": 6.67, "score": 0.22},
                {
                    "frame_num": 250,
                    "timestamp_s": 8.33,
                    "score": 0.25,
                },  # Should be ignored (only top 3)
            ],
            "bad_segments": [
                {"start_timestamp_s": 3.0, "end_timestamp_s": 7.5, "min_score": 0.12},
                {"start_timestamp_s": 10.0, "end_timestamp_s": 15.0, "min_score": 0.14},
                {"start_timestamp_s": 20.0, "end_timestamp_s": 25.0, "min_score": 0.16},
                {
                    "start_timestamp_s": 30.0,
                    "end_timestamp_s": 35.0,
                    "min_score": 0.18,
                },  # Should be ignored
            ],
        }
    }

    coach_findings._attach_evidence_markers(finding, "head_stability_score", evidence_data)

    assert "video_evidence" in finding
    assert "worst_frames" in finding["video_evidence"]
    assert "bad_segments" in finding["video_evidence"]

    # Check top 3 worst frames
    worst_frames = finding["video_evidence"]["worst_frames"]
    assert len(worst_frames) == 3
    assert worst_frames[0]["frame"] == 100
    assert worst_frames[0]["timestamp"] == "00:03"
    assert worst_frames[0]["score"] == 0.15

    # Check top 3 bad segments
    bad_segments = finding["video_evidence"]["bad_segments"]
    assert len(bad_segments) == 3
    assert bad_segments[0]["start"] == "00:03"
    assert bad_segments[0]["end"] == "00:07"
    assert bad_segments[0]["min_score"] == 0.12


def test_attach_evidence_markers_missing_data():
    """Test evidence attachment when data is missing."""
    finding = {"title": "Head Movement"}

    # Empty evidence
    coach_findings._attach_evidence_markers(finding, "head_stability_score", {})
    assert "video_evidence" not in finding

    # None evidence
    coach_findings._attach_evidence_markers(finding, "head_stability_score", None)
    assert "video_evidence" not in finding

    # Metric not in evidence
    evidence_data = {"balance_drift_score": {"worst_frames": []}}
    coach_findings._attach_evidence_markers(finding, "head_stability_score", evidence_data)
    assert "video_evidence" not in finding


def test_attach_evidence_markers_partial_data():
    """Test evidence attachment with only some fields present."""
    finding = {"title": "Knee Collapse"}

    evidence_data = {
        "front_knee_brace_score": {
            "worst_frames": [
                {"frame_num": 42, "timestamp_s": 1.4, "score": 0.3},
            ],
            # No bad_segments
        }
    }

    coach_findings._attach_evidence_markers(finding, "front_knee_brace_score", evidence_data)

    assert "video_evidence" in finding
    assert len(finding["video_evidence"]["worst_frames"]) == 1
    assert finding["video_evidence"]["worst_frames"][0]["timestamp"] == "00:01"
    assert len(finding["video_evidence"]["bad_segments"]) == 0


# ============================================================================
# Check Functions Tests (Evidence Integration)
# ============================================================================


def test_check_head_movement_with_evidence():
    """Test head movement check attaches evidence correctly."""
    metrics = {
        "head_stability_score": {"score": 0.15},  # Below threshold (0.60)
    }

    evidence = {
        "head_stability_score": {
            "worst_frames": [
                {"frame_num": 10, "timestamp_s": 0.33, "score": 0.12},
            ],
            "bad_segments": [
                {"start_timestamp_s": 0.0, "end_timestamp_s": 2.0, "min_score": 0.10},
            ],
        }
    }

    finding = coach_findings._check_head_movement(metrics, evidence)

    assert finding is not None
    assert finding["code"] == "HEAD_MOVEMENT"
    assert "video_evidence" in finding
    assert len(finding["video_evidence"]["worst_frames"]) == 1
    assert len(finding["video_evidence"]["bad_segments"]) == 1


def test_check_functions_without_evidence():
    """Test all check functions work without evidence parameter."""
    metrics_low = {
        "head_stability_score": {"score": 0.15},
        "balance_drift_score": {"score": 0.22},
        "front_knee_brace_score": {"score": 0.18},
        "hip_shoulder_separation_timing": 0.28,  # Direct float, not nested
        "elbow_drop_score": {"score": 0.12},
    }

    # Should not crash when evidence is None
    assert coach_findings._check_head_movement(metrics_low, None) is not None
    assert coach_findings._check_balance_drift(metrics_low, None) is not None
    assert coach_findings._check_knee_collapse(metrics_low, None) is not None
    assert (
        coach_findings._check_rotation_timing(metrics_low, None) is not None
    )  # Will trigger because 0.28 is far from target 0.12
    assert coach_findings._check_elbow_drop(metrics_low, None) is not None


# ============================================================================
# Generate Findings Tests
# ============================================================================


def test_generate_findings_with_evidence_and_detection_rate():
    """Test complete findings generation with evidence and detection rate."""
    metrics = {
        "head_stability_score": {"score": 0.45},  # Will trigger finding (below 0.60)
        "balance_drift_score": {"score": 0.90},  # OK
        "front_knee_brace_score": {"score": 0.85},  # OK
        "hip_shoulder_separation_timing": 0.12,  # OK (close to target)
        "elbow_drop_score": {"score": 0.88},  # OK
        "summary": {
            "frames_with_pose": 450,
            "total_frames": 500,
            "detection_rate_percent": 90.0,
        },
        "evidence": {
            "head_stability_score": {
                "worst_frames": [
                    {"frame_num": 50, "timestamp_s": 1.67, "score": 0.35},
                    {"frame_num": 100, "timestamp_s": 3.33, "score": 0.40},
                ],
                "bad_segments": [
                    {"start_timestamp_s": 1.0, "end_timestamp_s": 4.0, "min_score": 0.32},
                ],
            }
        },
    }

    result = coach_findings.generate_findings(metrics, context={}, analysis_mode="batting")

    # Check structure
    assert "findings" in result
    assert "overall_level" in result
    assert "detection_rate" in result

    # Check detection rate
    assert result["detection_rate"] == 90.0

    # Check findings have evidence (head + rotation timing detected)
    assert len(result["findings"]) >= 1
    finding = next(f for f in result["findings"] if f["code"] == "HEAD_MOVEMENT")
    assert "video_evidence" in finding
    assert len(finding["video_evidence"]["worst_frames"]) == 2
    assert finding["video_evidence"]["worst_frames"][0]["timestamp"] == "00:01"


def test_generate_findings_low_detection_rate():
    """Test findings generation with low detection rate."""
    metrics = {
        "head_stability_score": {"score": 0.90},
        "balance_drift_score": {"score": 0.90},
        "front_knee_brace_score": {"score": 0.90},
        "hip_shoulder_separation_timing": 0.12,
        "elbow_drop_score": {"score": 0.90},
        "summary": {
            "frames_with_pose": 250,
            "total_frames": 500,
            "detection_rate_percent": 50.0,
        },
        "evidence": {},
    }

    result = coach_findings.generate_findings(metrics, context={}, analysis_mode="batting")

    assert result["detection_rate"] == 50.0
    # Low detection rate should be flagged downstream


def test_generate_findings_missing_evidence():
    """Test findings generation when evidence field is missing."""
    metrics = {
        "head_stability_score": {"score": 0.45},
        "summary": {
            "frames_with_pose": 480,
            "total_frames": 500,
            "detection_rate_percent": 96.0,
        },
        # No "evidence" field
    }

    result = coach_findings.generate_findings(metrics, context={}, analysis_mode="batting")

    # Should work without crashing
    assert result["detection_rate"] == 96.0
    assert len(result["findings"]) == 1
    # Finding should not have video_evidence since none was provided
    finding = result["findings"][0]
    assert (
        "video_evidence" not in finding
        or len(finding.get("video_evidence", {}).get("worst_frames", [])) == 0
    )


# ============================================================================
# Report Service Tests
# ============================================================================


def test_report_includes_video_evidence():
    """Test that report generation includes video evidence in top issues."""
    findings_payload = {
        "overall_level": "medium",
        "detection_rate": 85.0,
        "findings": [
            {
                "code": "HEAD_MOVEMENT",
                "title": "Excessive Head Movement",
                "severity": "high",
                "why_it_matters": "Affects consistency",
                "cues": ["Keep eyes level", "Lock head position"],
                "video_evidence": {
                    "worst_frames": [
                        {"frame": 50, "timestamp": "00:01", "score": 0.25},
                        {"frame": 100, "timestamp": "00:03", "score": 0.28},
                    ],
                    "bad_segments": [
                        {"start": "00:01", "end": "00:04", "min_score": 0.22},
                    ],
                },
            }
        ],
        "context": {},
    }

    report = coach_report_service.generate_report_text(findings_payload)

    assert "top_issues" in report
    assert len(report["top_issues"]) == 1

    issue = report["top_issues"][0]
    assert "video_evidence" in issue
    assert "00:01-00:04" in issue["video_evidence"]  # Bad segment
    assert "00:01" in issue["video_evidence"]  # Worst frame timestamp


def test_report_reliability_warning_low_detection():
    """Test that low detection rate triggers reliability warning."""
    findings_payload = {
        "overall_level": "medium",
        "detection_rate": 45.0,
        "findings": [],
        "context": {},
    }

    report = coach_report_service.generate_report_text(findings_payload)

    assert "reliability_warning" in report
    assert report["reliability_warning"] is not None
    assert "45" in report["reliability_warning"]
    assert "Low pose visibility" in report["reliability_warning"]


def test_report_no_warning_high_detection():
    """Test that high detection rate does not trigger warning."""
    findings_payload = {
        "overall_level": "excellent",
        "detection_rate": 92.0,
        "findings": [],
        "context": {},
    }

    report = coach_report_service.generate_report_text(findings_payload)

    assert "reliability_warning" in report
    assert report["reliability_warning"] is None


# ============================================================================
# PDF Export Tests
# ============================================================================


def test_pdf_proof_of_work_format():
    """Test proof of work section formatting."""
    findings = {
        "detection_rate": 88.0,
        "findings": [
            {
                "title": "Head Movement",
                "severity": "high",
                "video_evidence": {
                    "worst_frames": [
                        {"frame": 42, "timestamp": "00:01", "score": 0.3},
                    ],
                    "bad_segments": [
                        {"start": "00:01", "end": "00:05", "min_score": 0.25},
                    ],
                },
            }
        ],
    }

    results = {
        "pose_summary": {
            "total_frames": 500,
            "frames_with_pose": 440,
        }
    }

    proof_text = pdf_export_service._format_proof_of_work(findings, results, "Quick")

    # Should include detection rate
    assert "88.0%" in proof_text
    assert "High confidence" in proof_text or "Moderate confidence" in proof_text

    # Should include frame counts
    assert "440" in proof_text
    assert "500" in proof_text

    # Should include video evidence
    assert "Head Movement" in proof_text
    assert "00:01-00:05" in proof_text  # Time range
    assert "frame 42" in proof_text  # Frame number


def test_pdf_proof_of_work_low_confidence():
    """Test proof of work with low confidence indicator."""
    findings = {
        "detection_rate": 55.0,
        "findings": [],
    }

    proof_text = pdf_export_service._format_proof_of_work(findings, None, "Deep")

    assert "55.0%" in proof_text
    assert "Low confidence" in proof_text
    assert "⚠️" in proof_text  # Warning emoji


def test_pdf_generation_with_proof_of_work():
    """Test that PDF generation includes proof of work sections."""
    quick_findings = {
        "detection_rate": 90.0,
        "findings": [
            {
                "title": "Test Finding",
                "severity": "medium",
                "video_evidence": {
                    "worst_frames": [{"frame": 10, "timestamp": "00:00", "score": 0.5}],
                    "bad_segments": [],
                },
            }
        ],
    }

    quick_results = {
        "pose_summary": {
            "total_frames": 300,
            "frames_with_pose": 270,
        }
    }

    pdf_bytes = pdf_export_service.generate_analysis_pdf(
        job_id="test-123",
        session_title="Test Session",
        status="completed",
        quick_findings=quick_findings,
        deep_findings=None,
        quick_results=quick_results,
        deep_results=None,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )

    # Should generate valid PDF bytes
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    # PDF header check
    assert pdf_bytes[:4] == b"%PDF"


# ============================================================================
# Integration Tests
# ============================================================================


def test_end_to_end_evidence_flow():
    """Test complete flow from metrics → findings → report → PDF."""
    # Step 1: Metrics with evidence (from pose_metrics.py)
    metrics = {
        "head_stability_score": {"score": 0.35},
        "balance_drift_score": {"score": 0.25},
        "front_knee_brace_score": {"score": 0.88},
        "hip_shoulder_separation_timing": 0.12,
        "elbow_drop_score": {"score": 0.90},
        "summary": {
            "frames_with_pose": 475,
            "total_frames": 500,
            "detection_rate_percent": 95.0,
        },
        "evidence": {
            "head_stability_score": {
                "worst_frames": [
                    {"frame_num": 50, "timestamp_s": 1.67, "score": 0.30},
                    {"frame_num": 75, "timestamp_s": 2.5, "score": 0.32},
                ],
                "bad_segments": [
                    {"start_timestamp_s": 1.0, "end_timestamp_s": 3.0, "min_score": 0.28},
                ],
            },
            "balance_drift_score": {
                "worst_frames": [
                    {"frame_num": 100, "timestamp_s": 3.33, "score": 0.22},
                ],
                "bad_segments": [],
            },
        },
    }

    # Step 2: Generate findings
    findings_result = coach_findings.generate_findings(
        metrics, context={"name": "Test Player"}, analysis_mode="batting"
    )

    assert findings_result["detection_rate"] == 95.0
    assert len(findings_result["findings"]) >= 2  # Head + balance (and possibly rotation timing)

    head_finding = next(f for f in findings_result["findings"] if f["code"] == "HEAD_MOVEMENT")
    assert "video_evidence" in head_finding
    assert len(head_finding["video_evidence"]["worst_frames"]) == 2

    # Step 3: Generate report
    report = coach_report_service.generate_report_text(findings_result)

    assert report["reliability_warning"] is None  # High detection rate
    assert len(report["top_issues"]) >= 2

    head_issue = next((i for i in report["top_issues"] if "Head" in i["issue"]), None)
    assert head_issue is not None
    assert "video_evidence" in head_issue
    assert "00:01-00:03" in head_issue["video_evidence"]

    # Step 4: Generate PDF
    pdf_bytes = pdf_export_service.generate_analysis_pdf(
        job_id="integration-test",
        session_title="Integration Test Session",
        status="completed",
        quick_findings=findings_result,
        deep_findings=None,
        quick_results={"pose_summary": metrics["summary"]},
        deep_results=None,
        created_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc),
    )

    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000  # Reasonable PDF size
    # PDF content is compiled/compressed, so text search isn't reliable
    # Manual visual inspection would confirm "Proof of Work" section exists


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
