"""
Coach Report V2: Universal PDF template for all analysis types.

This module provides reusable rendering functions for a coach-friendly
report layout that works across bowling, batting, wicketkeeping, and fielding.
"""

from __future__ import annotations

import logging
from typing import Any

from backend.services.reports.findings_adapter import CommonFinding
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import PageBreak, Paragraph, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

# ============================================================================
# Typography and Layout Constants
# ============================================================================

# Colors
COLOR_PRIMARY = colors.HexColor("#2C3E50")  # Dark blue-gray for titles
COLOR_HEADING = colors.HexColor("#34495E")  # Medium blue-gray for headings
COLOR_SUBHEADING = colors.HexColor("#7F8C8D")  # Light gray for subheadings
COLOR_HIGH = colors.HexColor("#E74C3C")  # Red for high severity
COLOR_MEDIUM = colors.HexColor("#F39C12")  # Orange for medium severity
COLOR_LOW = colors.HexColor("#3498DB")  # Blue for low severity
COLOR_SUCCESS = colors.HexColor("#27AE60")  # Green for success/pass

# Font sizes
FONT_TITLE = 24
FONT_HEADING = 16
FONT_SUBHEADING = 14
FONT_BODY = 10
FONT_SMALL = 8

# Spacing
SPACE_SECTION = 0.3 * inch
SPACE_SUBSECTION = 0.15 * inch
SPACE_PARAGRAPH = 0.1 * inch


def get_styles() -> dict[str, ParagraphStyle]:
    """
    Get standardized paragraph styles for Coach Report V2.

    Returns:
        Dict of style name → ParagraphStyle
    """
    base_styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "CoachTitle",
            parent=base_styles["Title"],
            fontSize=FONT_TITLE,
            textColor=COLOR_PRIMARY,
            spaceAfter=12,
            alignment=1,  # Center
        ),
        "heading": ParagraphStyle(
            "CoachHeading",
            parent=base_styles["Heading1"],
            fontSize=FONT_HEADING,
            textColor=COLOR_HEADING,
            spaceAfter=10,
            spaceBefore=12,
        ),
        "subheading": ParagraphStyle(
            "CoachSubheading",
            parent=base_styles["Heading2"],
            fontSize=FONT_SUBHEADING,
            textColor=COLOR_SUBHEADING,
            spaceAfter=6,
            spaceBefore=8,
        ),
        "body": base_styles["BodyText"],
        "small": ParagraphStyle(
            "CoachSmall",
            parent=base_styles["BodyText"],
            fontSize=FONT_SMALL,
            textColor=COLOR_SUBHEADING,
        ),
    }


# ============================================================================
# Page 1: Coach Summary
# ============================================================================


def render_coach_summary(
    top_priorities: list[CommonFinding],
    secondary_focus: list[CommonFinding],
    this_week_actions: list[str],
    analysis_mode: str,
) -> list:
    """
    Render Page 1: Coach Summary.

    Layout:
    - Top Priority Fixes (2-3 items, ordered by severity)
    - Secondary Focus (1-2 items)
    - "This Week's Focus" action box (3 bullets)

    Args:
        top_priorities: Top 2-3 findings (high severity)
        secondary_focus: Secondary 1-2 findings
        this_week_actions: 3 action bullets for this week
        analysis_mode: Analysis mode (batting, bowling, etc.)

    Returns:
        List of reportlab flowables
    """
    elements = []
    styles = get_styles()

    # Page title
    mode_label = analysis_mode.capitalize() if analysis_mode else "Cricket"
    elements.append(Paragraph(f"{mode_label} Analysis: Coach Summary", styles["title"]))
    elements.append(Spacer(1, SPACE_SECTION))

    # Top Priority Fixes
    elements.append(Paragraph("🎯 Top Priority Fixes", styles["heading"]))
    if top_priorities:
        for idx, finding in enumerate(top_priorities, 1):
            elements.extend(_render_finding_summary(finding, idx, styles))
    else:
        elements.append(Paragraph("No critical issues detected.", styles["body"]))
    elements.append(Spacer(1, SPACE_SECTION))

    # Secondary Focus
    if secondary_focus:
        elements.append(Paragraph("📌 Secondary Focus", styles["heading"]))
        for idx, finding in enumerate(secondary_focus, 1):
            elements.extend(_render_finding_summary(finding, idx, styles, compact=True))
        elements.append(Spacer(1, SPACE_SECTION))

    # This Week's Focus
    elements.append(Paragraph("📅 This Week's Focus", styles["heading"]))
    action_bullets = "<br/>".join([f"• {action}" for action in this_week_actions])
    action_box_text = f'<para bgcolor="#ECF0F1" leftIndent="10" rightIndent="10" spaceBefore="6" spaceAfter="6">{action_bullets}</para>'
    elements.append(Paragraph(action_box_text, styles["body"]))
    elements.append(Spacer(1, SPACE_SECTION))

    # Page break after coach summary
    elements.append(PageBreak())

    return elements


def _render_finding_summary(
    finding: CommonFinding, index: int, styles: dict, compact: bool = False
) -> list:
    """
    Render a single finding in the coach summary.

    Args:
        finding: CommonFinding to render
        index: Finding number (1, 2, 3...)
        styles: Style dict
        compact: If True, use compact format for secondary items

    Returns:
        List of flowables
    """
    elements = []

    # Severity badge
    severity_color = {
        "high": COLOR_HIGH,
        "medium": COLOR_MEDIUM,
        "low": COLOR_LOW,
    }.get(finding["severity"], COLOR_SUBHEADING)

    severity_badge = f'<font color="{severity_color}">●</font>'
    title_text = (
        f"{index}. {severity_badge} <b>{finding['title']}</b> [{finding['severity'].upper()}]"
    )

    elements.append(Paragraph(title_text, styles["body"]))

    if not compact:
        # Full format: what's happening + why it matters
        elements.append(
            Paragraph(f"<i>What's happening:</i> {finding['what_happening']}", styles["small"])
        )
        elements.append(
            Paragraph(f"<i>Why it matters:</i> {finding['why_matters']}", styles["small"])
        )
    else:
        # Compact format: just what's happening
        elements.append(Paragraph(f"{finding['what_happening']}", styles["small"]))

    elements.append(Spacer(1, SPACE_PARAGRAPH))

    return elements


# ============================================================================
# Consolidated Findings Section
# ============================================================================


def render_consolidated_findings(findings: list[CommonFinding]) -> list:
    """
    Render consolidated findings section (no more Quick/Deep split).

    Layout per finding:
    - Title + Severity badge
    - What's happening (1-2 lines)
    - Why it matters (1-2 lines, coach language)
    - Drills (max 3 bullets)
    - Metrics (compact table: Score, Threshold, Pass/Fail)
    - Evidence references moved to appendix

    Args:
        findings: Consolidated list of CommonFindings

    Returns:
        List of reportlab flowables
    """
    elements = []
    styles = get_styles()

    elements.append(Paragraph("Detailed Analysis", styles["heading"]))
    elements.append(Spacer(1, SPACE_SUBSECTION))

    if not findings:
        elements.append(Paragraph("No findings to report.", styles["body"]))
        return elements

    for idx, finding in enumerate(findings, 1):
        elements.extend(_render_finding_detail(finding, idx, styles))
        elements.append(Spacer(1, SPACE_SECTION))

    return elements


def _render_finding_detail(finding: CommonFinding, index: int, styles: dict) -> list:
    """
    Render a detailed finding block.

    Args:
        finding: CommonFinding to render
        index: Finding number
        styles: Style dict

    Returns:
        List of flowables
    """
    elements = []

    # Title + Severity
    severity_color = {
        "high": COLOR_HIGH,
        "medium": COLOR_MEDIUM,
        "low": COLOR_LOW,
    }.get(finding["severity"], COLOR_SUBHEADING)

    severity_badge = f'<font color="{severity_color}">●</font>'
    title_text = (
        f"{index}. {severity_badge} <b>{finding['title']}</b> [{finding['severity'].upper()}]"
    )

    # Add phase label if present (Quick analysis note)
    if finding.get("phase") == "Quick":
        title_text += ' <font color="#95A5A6" size="8">(Initial scan)</font>'

    elements.append(Paragraph(title_text, styles["subheading"]))
    elements.append(Spacer(1, 0.05 * inch))

    # What's happening
    elements.append(
        Paragraph(f"<b>What's happening:</b> {finding['what_happening']}", styles["body"])
    )
    elements.append(Spacer(1, 0.05 * inch))

    # Why it matters
    elements.append(Paragraph(f"<b>Why it matters:</b> {finding['why_matters']}", styles["body"]))
    elements.append(Spacer(1, 0.1 * inch))

    # Drills
    drills = finding.get("drills", [])
    if drills:
        elements.append(Paragraph("<b>Suggested drills:</b>", styles["body"]))
        drill_text = "<br/>".join([f"  • {drill}" for drill in drills[:3]])
        elements.append(Paragraph(drill_text, styles["body"]))
        elements.append(Spacer(1, 0.1 * inch))

    # Metrics (compact table)
    metrics = finding.get("metrics", {})
    if metrics:
        elements.append(Paragraph("<b>Metrics:</b>", styles["small"]))
        metric_table = _build_metrics_table(metrics)
        if metric_table:
            elements.append(metric_table)
        elements.append(Spacer(1, 0.1 * inch))

    # Evidence note (reference to appendix)
    evidence = finding.get("evidence", {})
    if evidence:
        worst_frames = evidence.get("worst_frames", [])
        bad_segments = evidence.get("bad_segments", [])
        evidence_count = len(worst_frames) + len(bad_segments)
        if evidence_count > 0:
            evidence_note = f'<font color="#7F8C8D" size="8"><i>See Appendix for {evidence_count} video evidence markers</i></font>'
            elements.append(Paragraph(evidence_note, styles["small"]))

    return elements


def _build_metrics_table(metrics: dict[str, Any]) -> Table | None:
    """
    Build a compact metrics table.

    Format: Score | Threshold | Status

    Args:
        metrics: Metrics dict from finding

    Returns:
        Table or None if no valid metrics
    """
    rows = [["Metric", "Score", "Status"]]

    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            metric_name = key.replace("_", " ").title()
            score_str = f"{value:.2f}" if isinstance(value, float) else str(value)

            # Simple pass/fail based on value (< 0.5 = fail, >= 0.5 = pass for scores)
            status = ("✅ Pass" if value >= 0.5 else "❌ Fail") if 0 <= value <= 1 else f"{value}"

            rows.append([metric_name, score_str, status])

    if len(rows) == 1:  # Only header
        return None

    table = Table(rows, colWidths=[2.5 * inch, 1 * inch, 1 * inch])
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONT", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("TEXTCOLOR", (0, 0), (-1, 0), COLOR_HEADING),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECF0F1")),
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#BDC3C7")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )

    return table


# ============================================================================
# Appendix: Evidence & Confidence
# ============================================================================


def render_appendix_evidence(
    findings: list[CommonFinding], detection_rate: float, total_frames: int, frames_with_pose: int
) -> list:
    """
    Render appendix with video evidence and confidence metrics.

    Layout:
    - Detection rate and reliability
    - Per-finding video evidence (timestamps + worst frames)

    Args:
        findings: Consolidated findings
        detection_rate: Pose detection rate percentage
        total_frames: Total frames analyzed
        frames_with_pose: Frames with pose detected

    Returns:
        List of reportlab flowables
    """
    elements = []
    styles = get_styles()

    # Page break before appendix
    elements.append(PageBreak())

    # Appendix title
    elements.append(Paragraph("Appendix: Evidence & Confidence", styles["heading"]))
    elements.append(Spacer(1, SPACE_SUBSECTION))

    # Detection rate
    reliability_emoji = "✅" if detection_rate >= 60.0 else "⚠️"
    reliability_text = (
        "High confidence"
        if detection_rate >= 80.0
        else ("Moderate confidence" if detection_rate >= 60.0 else "Low confidence")
    )
    elements.append(
        Paragraph(
            f"<b>{reliability_emoji} Pose Detection Rate:</b> {detection_rate:.1f}% ({reliability_text})",
            styles["body"],
        )
    )
    elements.append(
        Paragraph(
            f"<b>Frames Analyzed:</b> {frames_with_pose:,} of {total_frames:,} total frames",
            styles["body"],
        )
    )
    elements.append(Spacer(1, SPACE_SECTION))

    # Per-finding evidence
    elements.append(Paragraph("Video Evidence by Finding:", styles["subheading"]))
    elements.append(Spacer(1, SPACE_SUBSECTION))

    for idx, finding in enumerate(findings, 1):
        evidence = finding.get("evidence", {})
        if not evidence:
            continue

        worst_frames = evidence.get("worst_frames", [])
        bad_segments = evidence.get("bad_segments", [])

        if not worst_frames and not bad_segments:
            continue

        # Finding title
        elements.append(Paragraph(f"<b>{idx}. {finding['title']}</b>", styles["body"]))

        # Time ranges
        if bad_segments:
            segment_texts = [
                f"{seg.get('start', 'N/A')}-{seg.get('end', 'N/A')}" for seg in bad_segments
            ]
            elements.append(
                Paragraph(f"  • Time Ranges: {', '.join(segment_texts)}", styles["small"])
            )

        # Worst instances
        if worst_frames:
            frame_texts = [
                f"frame {wf.get('frame', 'N/A')} ({wf.get('timestamp', 'N/A')})"
                for wf in worst_frames
            ]
            elements.append(
                Paragraph(f"  • Worst Instances: {', '.join(frame_texts)}", styles["small"])
            )

        elements.append(Spacer(1, SPACE_PARAGRAPH))

    return elements
