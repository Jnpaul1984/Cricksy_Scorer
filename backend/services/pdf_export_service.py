"""PDF export service for video analysis results - Coach Report V2."""

import io
import logging
from datetime import datetime
from typing import Any

from backend.services.reports.coach_report_template import (
    get_styles,
    render_appendix_evidence,
    render_coach_summary,
    render_consolidated_findings,
)
from backend.services.reports.findings_adapter import (
    consolidate_findings,
    extract_secondary_focus,
    extract_top_priorities,
    generate_this_week_actions,
)
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)


def generate_analysis_pdf(
    job_id: str,
    session_title: str,
    status: str,
    quick_findings: dict[str, Any] | None,
    deep_findings: dict[str, Any] | None,
    quick_results: dict[str, Any] | None,
    deep_results: dict[str, Any] | None,
    created_at: datetime,
    completed_at: datetime | None,
    analysis_mode: str | None = None,
) -> bytes:
    """
    Generate a Coach Report V2 PDF from video analysis results.

    Universal template for all analysis types (bowling, batting, wicketkeeping, fielding).

    Layout:
    - Page 1: Coach Summary (Top Priorities + This Week's Focus)
    - Page 2+: Consolidated Findings (no more Quick/Deep split)
    - Appendix: Evidence & Confidence

    Args:
        job_id: Analysis job ID
        session_title: Video session title
        status: Job status
        quick_findings: Quick analysis findings
        deep_findings: Deep analysis findings
        quick_results: Full quick analysis results
        deep_results: Full deep analysis results
        created_at: Job creation timestamp
        completed_at: Job completion timestamp
        analysis_mode: Analysis mode (batting, bowling, wicketkeeping, fielding)

    Returns:
        PDF bytes
    """
    logger.info(f"Generating Coach Report V2 PDF for job {job_id} (mode={analysis_mode})")

    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter, topMargin=0.75 * inch, bottomMargin=0.75 * inch
    )

    # Container for PDF elements
    elements = []

    # Get styles
    styles = get_styles()

    # Session metadata header (before coach summary)
    elements.extend(
        _render_metadata_header(
            session_title, job_id, status, created_at, completed_at, analysis_mode, styles
        )
    )

    # Consolidate Quick + Deep findings
    consolidated = consolidate_findings(quick_findings, deep_findings)

    if not consolidated:
        # No findings available - render simple message
        elements.append(Paragraph("No findings to report.", styles["body"]))
        elements.append(Spacer(1, 0.2 * inch))

        # Add basic metadata if available
        if quick_results or deep_results:
            results_data = deep_results or quick_results
            if results_data:  # Additional safety check for type checker
                summary_text = _extract_summary_from_results(results_data, "Analysis")
                elements.append(Paragraph(summary_text, styles["body"]))

    else:
        # Extract coach summary components
        top_priorities = extract_top_priorities(consolidated, max_count=3)
        secondary_focus = extract_secondary_focus(consolidated, top_priorities, max_count=2)
        this_week_actions = generate_this_week_actions(consolidated)

        # Page 1: Coach Summary
        elements.extend(
            render_coach_summary(
                top_priorities, secondary_focus, this_week_actions, analysis_mode or "cricket"
            )
        )

        # Page 2+: Consolidated Findings
        elements.extend(render_consolidated_findings(consolidated))

        # Appendix: Evidence & Confidence
        detection_rate = _extract_detection_rate(quick_findings, deep_findings)
        total_frames, frames_with_pose = _extract_frame_counts(quick_results, deep_results)

        elements.extend(
            render_appendix_evidence(consolidated, detection_rate, total_frames, frames_with_pose)
        )

    # Build PDF
    doc.build(elements)

    # Get PDF bytes
    pdf_bytes = buffer.getvalue()
    buffer.close()

    pdf_size_kb = len(pdf_bytes) / 1024
    logger.info(f"Generated Coach Report V2 PDF for job {job_id}: {pdf_size_kb:.2f} KB")

    return pdf_bytes


def _render_metadata_header(
    session_title: str,
    job_id: str,
    status: str,
    created_at: datetime,
    completed_at: datetime | None,
    analysis_mode: str | None,
    styles: dict,
) -> list:
    """
    Render session metadata header (appears above coach summary).

    Args:
        session_title: Video session title
        job_id: Job ID
        status: Job status
        created_at: Creation timestamp
        completed_at: Completion timestamp
        analysis_mode: Analysis mode
        styles: Style dict

    Returns:
        List of flowables
    """
    elements = []

    # Metadata table
    metadata_data = [
        ["Session:", session_title],
        ["Job ID:", job_id],
        ["Status:", status.upper()],
        ["Created:", created_at.strftime("%Y-%m-%d %H:%M:%S UTC")],
    ]
    if completed_at:
        metadata_data.append(["Completed:", completed_at.strftime("%Y-%m-%d %H:%M:%S UTC")])

    metadata_table = Table(metadata_data, colWidths=[1.5 * inch, 5 * inch])
    metadata_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONT", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#2C3E50")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    elements.append(metadata_table)
    elements.append(Spacer(1, 0.3 * inch))

    return elements


def _extract_detection_rate(
    quick_findings: dict[str, Any] | None, deep_findings: dict[str, Any] | None
) -> float:
    """
    Extract pose detection rate from findings.

    Args:
        quick_findings: Quick findings dict
        deep_findings: Deep findings dict

    Returns:
        Detection rate percentage (prefer deep, fallback to quick)
    """
    # Prefer deep findings
    if deep_findings and "detection_rate" in deep_findings:
        return float(deep_findings["detection_rate"])

    if quick_findings and "detection_rate" in quick_findings:
        return float(quick_findings["detection_rate"])

    return 0.0


def _extract_frame_counts(
    quick_results: dict[str, Any] | None, deep_results: dict[str, Any] | None
) -> tuple[int, int]:
    """
    Extract total frames and frames with pose from results.

    Args:
        quick_results: Quick results dict
        deep_results: Deep results dict

    Returns:
        Tuple of (total_frames, frames_with_pose)
    """
    results = deep_results or quick_results

    if not results:
        return 0, 0

    pose_summary = results.get("pose_summary") or results.get("pose", {})
    if isinstance(pose_summary, dict):
        total_frames = pose_summary.get("total_frames", 0)
        frames_with_pose = pose_summary.get("frames_with_pose", 0)
        return total_frames, frames_with_pose

    return 0, 0


# ============================================================================
# Legacy Helper Functions (kept for backward compatibility with tests)
# ============================================================================


def _format_findings(findings: dict[str, Any]) -> str:
    """Format findings dictionary as readable text.

    DEPRECATED: Legacy function kept for test compatibility.
    New code should use findings_adapter.consolidate_findings().

    Supports both legacy dict format and new finding object format.
    Finding objects have: code, title, severity, evidence, cues, suggested_drills.
    """
    lines = []

    # Check if findings is a list of finding objects
    findings_list = findings.get("findings", [])
    if isinstance(findings_list, list) and findings_list:
        for finding in findings_list:
            if not isinstance(finding, dict):
                continue

            # Format finding object
            title = finding.get("title", "Finding")
            severity = finding.get("severity", "unknown").upper()

            lines.append(f"<b>{title}</b> [{severity}]")

            # Evidence
            evidence = finding.get("evidence", {})
            if evidence and isinstance(evidence, dict):
                for key, val in evidence.items():
                    label = key.replace("_", " ").title()
                    lines.append(f"  • {label}: {val}")

            # Cues
            cues = finding.get("cues", [])
            if cues and isinstance(cues, list):
                lines.append("  <b>What to look for:</b>")
                for cue in cues:
                    lines.append(f"    - {cue}")

            # Drills
            drills = finding.get("suggested_drills", [])
            if drills and isinstance(drills, list):
                lines.append("  <b>Suggested drills:</b>")
                for drill in drills[:3]:  # Limit to first 3 for space
                    lines.append(f"    - {drill}")

            lines.append("<br/>")
    else:
        # Legacy format: key-value dict
        for key, value in findings.items():
            # Convert snake_case to Title Case
            label = key.replace("_", " ").title()

            if isinstance(value, dict):
                lines.append(f"<b>{label}:</b>")
                for sub_key, sub_value in value.items():
                    sub_label = sub_key.replace("_", " ").title()
                    lines.append(f"  • {sub_label}: {sub_value}")
            elif isinstance(value, list):
                lines.append(f"<b>{label}:</b>")
                for item in value:
                    if isinstance(item, str):
                        lines.append(f"  • {item}")
            else:
                lines.append(f"<b>{label}:</b> {value}")

    return "<br/>".join(lines) if lines else "No detailed findings available."


def _extract_summary_from_results(results: dict[str, Any], stage: str) -> str:
    """
    Extract a summary from raw results JSON.

    DEPRECATED: Legacy function kept for backward compatibility.
    """
    lines = [f"<b>{stage} analysis completed.</b><br/><br/>"]

    # Try to extract pose summary
    pose_summary = results.get("pose_summary") or results.get("pose", {})
    if pose_summary and isinstance(pose_summary, dict):
        detection_rate = pose_summary.get("detection_rate_percent", "N/A")
        total_frames = pose_summary.get("total_frames", "N/A")
        lines.append(
            f"<b>Pose Detection:</b> {detection_rate}% detection rate across {total_frames} frames"
        )

    # Try to extract evidence
    evidence = results.get("evidence", {})
    if evidence:
        lines.append("<br/><b>Key Findings:</b>")
        for metric, data in evidence.items():
            metric_label = metric.replace("_", " ").title()
            threshold = data.get("threshold", "N/A")
            lines.append(f"  • {metric_label}: Threshold = {threshold}")

    return (
        "<br/>".join(lines)
        if len(lines) > 1
        else f"{stage} analysis data available in full results JSON."
    )


def _format_proof_of_work(
    findings: dict[str, Any], results: dict[str, Any] | None, stage: str
) -> str:
    """
    Format proof of work section showing detection rate and video evidence.

    DEPRECATED: Legacy function kept for backward compatibility.
    New code should use render_appendix_evidence() from coach_report_template.

    Args:
        findings: Findings dictionary (output from coach_findings.generate_findings)
        results: Raw analysis results (optional, contains pose summary)
        stage: "Quick" or "Deep"

    Returns:
        HTML-formatted proof of work text
    """
    lines = []

    # Detection rate and reliability
    detection_rate = findings.get("detection_rate", 0.0)
    if detection_rate > 0:
        reliability_emoji = "✅" if detection_rate >= 60.0 else "⚠️"
        reliability_text = (
            "High confidence"
            if detection_rate >= 80.0
            else ("Moderate confidence" if detection_rate >= 60.0 else "Low confidence")
        )
        lines.append(
            f"<b>{reliability_emoji} Pose Detection Rate:</b> {detection_rate}% ({reliability_text})<br/>"
        )

    # Total frames analyzed
    if results:
        pose_summary = results.get("pose_summary") or results.get("pose", {})
        if isinstance(pose_summary, dict):
            total_frames = pose_summary.get("total_frames", 0)
            frames_with_pose = pose_summary.get("frames_with_pose", 0)
            if total_frames > 0:
                lines.append(
                    f"<b>Frames Analyzed:</b> {frames_with_pose:,} of {total_frames:,} total frames<br/><br/>"
                )

    # Per-finding video evidence
    finding_list = findings.get("findings", [])
    if finding_list:
        lines.append("<b>Video Evidence by Finding:</b><br/>")

        for idx, finding in enumerate(finding_list, 1):
            title = finding.get("title", "Unknown")
            severity = finding.get("severity", "low").upper()
            video_evidence = finding.get("video_evidence", {})

            if video_evidence:
                worst_frames = video_evidence.get("worst_frames", [])
                bad_segments = video_evidence.get("bad_segments", [])

                lines.append(f"<br/><b>{idx}. {title}</b> ({severity})<br/>")

                if bad_segments:
                    segment_texts = [f"{seg['start']}-{seg['end']}" for seg in bad_segments]
                    lines.append(f"  • Time Ranges: {', '.join(segment_texts)}<br/>")

                if worst_frames:
                    frame_texts = [
                        f"frame {wf['frame']} ({wf['timestamp']})" for wf in worst_frames
                    ]
                    lines.append(f"  • Worst Instances: {', '.join(frame_texts)}<br/>")

    if not lines:
        return ""

    return "".join(lines)
