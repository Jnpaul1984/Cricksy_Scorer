"""
Coach Report V2: Universal PDF template for all analysis types.

This module provides reusable rendering functions for a coach-friendly
report layout that works across bowling, batting, wicketkeeping, and fielding.
"""

from __future__ import annotations

import logging
from html import escape
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
SPACE_ITEM = 0.15 * inch  # Space between items

# Table widths
TABLE_FULL_WIDTH = 7.5 * inch


def _safe_pdf_text(value: Any, default: str = "Unavailable") -> str:
    """Return escaped display text without converting missing evidence to zero."""
    if value is None or value == "":
        return default
    return escape(str(value))


def _format_v2_number(value: Any, unit: Any = None) -> str:
    if value is None or isinstance(value, bool):
        return "Unavailable"
    rendered = f"{value:.3f}".rstrip("0").rstrip(".") if isinstance(value, float) else str(value)
    suffix = f" {_safe_pdf_text(unit, '')}" if unit else ""
    return f"{rendered}{suffix}"


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
# Page 2: Goals vs Outcomes (Phase 2)
# ============================================================================


def render_goals_vs_outcomes(
    goals: dict[str, Any] | None,
    outcomes: dict[str, Any] | None,
) -> list:
    """
    Render Goals vs Outcomes page (Page 2 in Coach Report V2).

    Shows coach-defined targets alongside actual performance with pass/fail indicators.

    Args:
        goals: Coach goals dict {zones: [...], metrics: [...]}
        outcomes: Calculated outcomes dict {zones: [...], metrics: [...], overall_compliance_pct}

    Returns:
        List of reportlab flowables for this page
    """
    styles = get_styles()
    elements = []

    # Page title
    elements.append(Paragraph("Your Goals vs Outcomes", styles["title"]))
    elements.append(Spacer(1, SPACE_SECTION))

    if not goals:
        elements.append(
            Paragraph(
                "No goals were set for this analysis session.",
                styles["body"],
            )
        )
        return elements

    if not outcomes:
        elements.append(
            Paragraph(
                "<i>Outcomes not yet calculated. Goals defined below:</i>",
                styles["body"],
            )
        )
        elements.append(Spacer(1, SPACE_SUBSECTION))

    # Overall compliance summary
    if outcomes:
        overall_pct = outcomes.get("overall_compliance_pct", 0.0)
        compliance_color = COLOR_SUCCESS if overall_pct >= 70.0 else COLOR_HIGH

        elements.append(
            Paragraph(
                f"<b>Overall Goal Compliance:</b> <font color='{compliance_color.hexval()}'>{overall_pct:.1f}%</font>",
                styles["heading"],
            )
        )
        elements.append(Spacer(1, SPACE_SECTION))

    # Zone Goals Section
    zone_goals = goals.get("zones", [])
    zone_outcomes = outcomes.get("zones", []) if outcomes else []

    if zone_goals:
        elements.append(Paragraph("Target Zone Accuracy", styles["heading"]))
        elements.append(Spacer(1, SPACE_SUBSECTION))

        # Build zone table
        zone_table_data = [["Zone", "Target", "Actual", "Status", "Delta"]]

        # Create lookup for outcomes
        zone_outcomes_map = {zo["zone_id"]: zo for zo in zone_outcomes}

        for zg in zone_goals:
            zone_id = zg["zone_id"]
            zone_name = zg.get("zone_name", "Unknown Zone")
            target = f"{zg['target_accuracy'] * 100:.0f}%"

            zo = zone_outcomes_map.get(zone_id)
            if zo:
                actual = f"{zo['actual_accuracy'] * 100:.0f}%"
                passed = zo["pass"]
                delta = zo["delta"]
                status = "✅ Pass" if passed else "❌ Miss"
                delta_text = f"{delta * 100:+.0f}%"
            else:
                actual = "N/A"
                status = "⏳ Pending"
                delta_text = "—"

            zone_table_data.append([zone_name, target, actual, status, delta_text])

        zone_table = Table(
            zone_table_data, colWidths=[2.5 * inch, 1 * inch, 1 * inch, 1 * inch, 1 * inch]
        )
        zone_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADING),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), FONT_BODY),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, COLOR_SUBHEADING),
                    ("FONTSIZE", (0, 1), (-1, -1), FONT_SMALL),
                ]
            )
        )

        elements.append(zone_table)
        elements.append(Spacer(1, SPACE_SECTION))

    # Metric Goals Section
    metric_goals = goals.get("metrics", [])
    metric_outcomes = outcomes.get("metrics", []) if outcomes else []

    if metric_goals:
        elements.append(Paragraph("Performance Metric Targets", styles["heading"]))
        elements.append(Spacer(1, SPACE_SUBSECTION))

        # Build metric table
        metric_table_data = [["Metric", "Target", "Actual", "Status", "Delta"]]

        # Create lookup for outcomes
        metric_outcomes_map = {mo["code"]: mo for mo in metric_outcomes}

        for mg in metric_goals:
            code = mg["code"]
            title = mg.get("title", code.replace("_", " ").title())
            target = f"{mg['target_score']:.2f}"

            mo = metric_outcomes_map.get(code)
            if mo:
                actual = f"{mo['actual_score']:.2f}"
                passed = mo["pass"]
                delta = mo["delta"]
                status = "✅ Pass" if passed else "❌ Miss"
                delta_text = f"{delta:+.2f}"
            else:
                actual = "N/A"
                status = "⏳ Pending"
                delta_text = "—"

            metric_table_data.append([title, target, actual, status, delta_text])

        metric_table = Table(
            metric_table_data, colWidths=[2.5 * inch, 1 * inch, 1 * inch, 1 * inch, 1 * inch]
        )
        metric_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADING),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), FONT_BODY),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, COLOR_SUBHEADING),
                    ("FONTSIZE", (0, 1), (-1, -1), FONT_SMALL),
                ]
            )
        )

        elements.append(metric_table)
        elements.append(Spacer(1, SPACE_SECTION))

    v2_goal_evidence = outcomes.get("v2_target_evidence", []) if outcomes else []
    if v2_goal_evidence:
        elements.append(Paragraph("Deterministic V2 Goal Progress", styles["heading"]))
        elements.append(Spacer(1, SPACE_SUBSECTION))
        v2_table_data = [["Goal", "Baseline", "Latest", "Status", "Confidence"]]
        for item in v2_goal_evidence:
            metric_label = (
                item.get("metric_id") or item.get("technical_area") or item.get("goal_id")
            )
            baseline = item.get("baseline") or {}
            latest = item.get("latest") or {}
            baseline_value = baseline.get("raw_value")
            latest_value = latest.get("raw_value")
            unit = latest.get("unit") or baseline.get("unit") or ""
            confidence = item.get("confidence")
            v2_table_data.append(
                [
                    str(metric_label),
                    "N/A" if baseline_value is None else f"{baseline_value:.3f} {unit}".strip(),
                    "N/A" if latest_value is None else f"{latest_value:.3f} {unit}".strip(),
                    str(item.get("status", "unsupported")).replace("_", " ").title(),
                    "N/A" if confidence is None else f"{confidence * 100:.0f}%",
                ]
            )

        v2_table = Table(
            v2_table_data, colWidths=[2.3 * inch, 1.1 * inch, 1.1 * inch, 1.3 * inch, 1.0 * inch]
        )
        v2_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_HEADING),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), FONT_BODY),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                    ("GRID", (0, 0), (-1, -1), 1, COLOR_SUBHEADING),
                    ("FONTSIZE", (0, 1), (-1, -1), FONT_SMALL),
                ]
            )
        )
        elements.append(v2_table)
        elements.append(Spacer(1, SPACE_SECTION))

    interventions = goals.get("interventions", []) if goals else []
    if interventions:
        elements.append(Paragraph("Recorded Interventions", styles["heading"]))
        elements.append(Spacer(1, SPACE_SUBSECTION))
        for item in interventions[:8]:
            activity = (
                item.get("activity")
                or item.get("title")
                or item.get("intervention_type")
                or "Intervention"
            )
            completion = item.get("completion_state")
            frequency = item.get("frequency")
            line = f"• {activity}"
            if completion:
                line += f" ({completion})"
            if frequency:
                line += f" — {frequency}"
            elements.append(Paragraph(line, styles["body"]))
        elements.append(Spacer(1, SPACE_SECTION))

    # Add page break after goals page
    elements.append(PageBreak())

    return elements


# ============================================================================
# Page 3: Coaching Suggestions (Phase 3)
# ============================================================================


def render_coaching_suggestions(
    suggestions: dict[str, Any] | None,
    player_summary: dict[str, Any] | None = None,
) -> list:
    """
    Render Page 3: AI-generated coaching suggestions.

    CRITICAL RULES:
    - Suggestions are coach-facing (technical)
    - Player summary is optional and simplified
    - Do NOT repeat findings or metrics already shown
    - Focus on actionable next steps

    Args:
        suggestions: Coach suggestions dict with primary_focus, drills, etc.
        player_summary: Optional player-facing simplified summary

    Returns:
        List of ReportLab flowables
    """
    from reportlab.platypus.flowables import Flowable

    elements: list[Flowable] = []

    if not suggestions:
        # Skip page if no suggestions exist
        return elements

    # Get styles
    styles = get_styles()
    heading1_style = styles["heading"]
    heading2_style = styles["subheading"]
    body_style = styles["body"]

    # Page title
    elements.append(Paragraph("<b>Coaching Suggestions</b>", heading1_style))
    elements.append(Spacer(1, SPACE_SECTION))

    # Primary Focus
    primary_focus = suggestions.get("primary_focus", "No specific focus identified")
    elements.append(Paragraph("<b>Primary Focus:</b>", heading2_style))
    elements.append(Paragraph(primary_focus, body_style))
    elements.append(Spacer(1, SPACE_ITEM))

    # Secondary Focus (if exists)
    secondary_focus = suggestions.get("secondary_focus")
    if secondary_focus:
        elements.append(Paragraph("<b>Secondary Focus:</b>", heading2_style))
        elements.append(Paragraph(secondary_focus, body_style))
        elements.append(Spacer(1, SPACE_ITEM))

    # Coaching Cues
    coaching_cues = suggestions.get("coaching_cues", [])
    if coaching_cues:
        elements.append(Paragraph("<b>Key Coaching Cues:</b>", heading2_style))
        cues_data = [[f"{i + 1}. {cue}"] for i, cue in enumerate(coaching_cues)]
        cues_table = Table(cues_data, colWidths=[TABLE_FULL_WIDTH])
        cues_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(cues_table)
        elements.append(Spacer(1, SPACE_ITEM))

    # Drill Priorities
    drills = suggestions.get("drills", [])
    if drills:
        elements.append(Paragraph("<b>Recommended Drills:</b>", heading2_style))
        drills_data = [[f"{i + 1}. {drill}"] for i, drill in enumerate(drills)]
        drills_table = Table(drills_data, colWidths=[TABLE_FULL_WIDTH])
        drills_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(drills_table)
        elements.append(Spacer(1, SPACE_ITEM))

    # Proposed Next Goal
    proposed_goal = suggestions.get("proposed_next_goal", {})
    if proposed_goal:
        elements.append(Paragraph("<b>Proposed Next Session Goal:</b>", heading2_style))
        goal_desc = proposed_goal.get("description", "")
        goal_target = proposed_goal.get("target", 0.0)

        goal_text = f"{goal_desc}"
        if goal_target > 0:
            goal_text += f" (target: {goal_target:.0%})"

        elements.append(Paragraph(goal_text, body_style))
        elements.append(Spacer(1, SPACE_ITEM))

    # Rationale
    rationale = suggestions.get("rationale", [])
    if rationale:
        elements.append(Paragraph("<b>Rationale:</b>", heading2_style))
        for reason in rationale:
            elements.append(Paragraph(f"• {reason}", body_style))
        elements.append(Spacer(1, SPACE_ITEM))

    # Optional: Player Summary (simplified, separate section)
    if player_summary:
        elements.append(Spacer(1, SPACE_SECTION))
        elements.append(Paragraph("<b>Player-Facing Summary</b>", heading2_style))
        elements.append(Spacer(1, SPACE_ITEM))

        focus = player_summary.get("focus", "")
        if focus:
            elements.append(Paragraph(focus, body_style))
            elements.append(Spacer(1, SPACE_ITEM))

        what_to_practice = player_summary.get("what_to_practice", [])
        if what_to_practice:
            elements.append(Paragraph("<b>What to practice:</b>", body_style))
            for item in what_to_practice:
                elements.append(Paragraph(f"• {item}", body_style))
            elements.append(Spacer(1, SPACE_ITEM))

        encouragement = player_summary.get("encouragement", "")
        if encouragement:
            elements.append(Paragraph(f"<i>{encouragement}</i>", body_style))

    # Page break after suggestions
    elements.append(PageBreak())

    return elements


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


def render_coaching_analysis_report_v2(report: dict[str, Any]) -> list:
    """Render a report derived exclusively from persisted Phase 10J V2 evidence."""
    styles = get_styles()
    elements: list[Any] = []

    elements.append(Paragraph("1. Executive Coaching Summary", styles["heading"]))
    mode = _safe_pdf_text(report.get("analysis_mode"), "Cricket")
    repetitions = report.get("repetitions", [])
    phases = report.get("phases", [])
    metrics = report.get("metrics", [])
    measurable_count = sum(item.get("raw_value") is not None for item in metrics)
    elements.append(
        Paragraph(
            f"This {mode} report uses persisted V2 analysis only: "
            f"{len(repetitions)} repetitions, {len(phases)} phases, and "
            f"{measurable_count} of {len(metrics)} metrics with measurable values.",
            styles["body"],
        )
    )
    elements.append(
        Paragraph(
            "Metric classifications, confidence, validity, and proxy status are reported "
            "as persisted; this report does not infer thresholds or measurement direction.",
            styles["small"],
        )
    )

    priorities = report.get("development_priorities", [])
    if priorities:
        elements.append(Paragraph("Evidence-led priorities", styles["subheading"]))
        for priority in priorities:
            elements.append(
                Paragraph(
                    f"<b>{_safe_pdf_text(priority.get('metric_id'))}</b>: "
                    f"{_safe_pdf_text(priority.get('observed_pattern'))} "
                    f"(validity: {_safe_pdf_text(priority.get('validity_state'))}; "
                    f"confidence: {_format_v2_number(priority.get('confidence_score'))}; "
                    f"proxy: {_safe_pdf_text(priority.get('proxy_state'))})",
                    styles["body"],
                )
            )
    else:
        elements.append(
            Paragraph(
                "No development priority could be selected from valid persisted V2 evidence.",
                styles["body"],
            )
        )

    elements.append(PageBreak())
    elements.append(Paragraph("2. Repetition &amp; Phase Analysis", styles["heading"]))
    elements.extend(_render_v2_repetitions(repetitions, styles))
    elements.extend(_render_v2_phases(phases, styles))
    elements.extend(_render_v2_metrics(metrics, styles))

    elements.append(PageBreak())
    elements.append(Paragraph("3. Technical Development Areas", styles["heading"]))
    if priorities:
        for index, priority in enumerate(priorities, 1):
            rep_ids = ", ".join(priority.get("supporting_repetition_ids", [])) or "Unavailable"
            elements.append(
                Paragraph(
                    f"<b>{index}. {_safe_pdf_text(priority.get('metric_id'))}</b>",
                    styles["subheading"],
                )
            )
            details = [
                ("Observed pattern", priority.get("observed_pattern")),
                ("Phase", priority.get("phase")),
                ("Supporting repetitions", rep_ids),
                (
                    "Measured value",
                    _format_v2_number(priority.get("measured_value"), priority.get("unit")),
                ),
                ("Validity", priority.get("validity_state")),
                ("Confidence", _format_v2_number(priority.get("confidence_score"))),
                ("Proxy state", priority.get("proxy_state")),
            ]
            elements.extend(_render_v2_detail_lines(details, styles))
            elements.extend(_render_v2_limitations(priority.get("limitations", []), styles))
    else:
        elements.append(
            Paragraph("No evidence-supported development area is available.", styles["body"])
        )

    elements.append(Paragraph("4. Strengths &amp; Consistency", styles["heading"]))
    elements.extend(_render_v2_signal_group("Strengths", report.get("strengths", []), styles))
    elements.extend(
        _render_v2_signal_group("Recurring concerns", report.get("recurring_concerns", []), styles)
    )
    consistency = report.get("consistency_observations", [])
    elements.append(Paragraph("Consistency observations", styles["subheading"]))
    if consistency:
        for observation in consistency:
            elements.append(
                Paragraph(
                    f"<b>{_safe_pdf_text(observation.get('metric_id'))}</b>: "
                    f"{_safe_pdf_text(observation.get('classification'))}; "
                    f"{_safe_pdf_text(observation.get('method'))}="
                    f"{_format_v2_number(observation.get('value'))}; "
                    f"valid samples={_safe_pdf_text(observation.get('valid_sample_count'))}; "
                    f"confidence={_format_v2_number(observation.get('confidence_score'))}.",
                    styles["body"],
                )
            )
    else:
        elements.append(Paragraph("Unavailable from the persisted V2 evidence.", styles["body"]))
    elements.extend(_render_v2_representative_repetitions(report, styles))

    elements.append(PageBreak())
    elements.append(Paragraph("5. Coach-Approved Action Plan", styles["heading"]))
    elements.append(
        Paragraph(
            "The following registry actions are coach-facing candidates. They require coach approval "
            "before assignment or player-facing publication and are not medical or conditioning advice.",
            styles["body"],
        )
    )
    actions = report.get("governed_actions", [])
    if actions:
        for index, action in enumerate(actions, 1):
            elements.append(
                Paragraph(
                    f"<b>{index}. {_safe_pdf_text(action.get('technical_area'))}</b> "
                    f"({_safe_pdf_text(action.get('action_id'))})",
                    styles["subheading"],
                )
            )
            details = [
                ("Linked evidence", action.get("linked_metric_id")),
                ("Why it matters technically", action.get("why_it_matters")),
                ("Objective", action.get("coaching_objective")),
                ("Cue", action.get("coaching_cue")),
                ("Drills", "; ".join(action.get("drills", []))),
                ("Coach should observe", action.get("coach_observation")),
                ("Reassessment", action.get("reassessment_criterion")),
                ("Review status", action.get("review_status")),
            ]
            elements.extend(_render_v2_detail_lines(details, styles))
            elements.extend(_render_v2_limitations(action.get("evidence_limitations", []), styles))
    else:
        elements.append(
            Paragraph("No governed action matched the available valid V2 evidence.", styles["body"])
        )

    interventions = report.get("coach_recorded_interventions", [])
    if interventions:
        elements.append(Paragraph("Coach-recorded interventions", styles["subheading"]))
        for intervention in interventions:
            elements.append(
                Paragraph(
                    f"{_safe_pdf_text(intervention.get('activity'))} "
                    f"(state: {_safe_pdf_text(intervention.get('completion_state'))}; "
                    f"governance: coach recorded)",
                    styles["body"],
                )
            )

    longitudinal = report.get("longitudinal_goal_evidence", [])
    if longitudinal:
        elements.append(PageBreak())
        elements.append(Paragraph("6. Progress / Longitudinal Evidence", styles["heading"]))
        elements.append(
            Paragraph(
                "Comparisons describe persisted observations only. They do not attribute change to an intervention.",
                styles["small"],
            )
        )
        for item in longitudinal:
            baseline = item.get("baseline") or {}
            latest = item.get("latest") or {}
            elements.append(
                Paragraph(
                    f"<b>{_safe_pdf_text(item.get('metric_id'))}</b>: "
                    f"baseline {_format_v2_number(baseline.get('raw_value'), baseline.get('unit'))}; "
                    f"latest {_format_v2_number(latest.get('raw_value'), latest.get('unit'))}; "
                    f"status {_safe_pdf_text(item.get('status'))}; "
                    f"confidence {_format_v2_number(item.get('confidence'))}.",
                    styles["body"],
                )
            )
            elements.extend(_render_v2_limitations(item.get("limitations", []), styles))

    elements.append(PageBreak())
    elements.append(Paragraph("Appendix: Evidence &amp; Limitations", styles["heading"]))
    elements.append(
        Paragraph(
            f"Report contract: {_safe_pdf_text(report.get('report_version'))}; "
            f"action registry: {_safe_pdf_text(report.get('action_registry_version'))}; "
            f"source: {_safe_pdf_text(report.get('source'))}.",
            styles["body"],
        )
    )
    elements.append(Paragraph("Metric evidence references", styles["subheading"]))
    if metrics:
        for metric in metrics:
            reference_count = sum(
                len(metric.get(name, []))
                for name in ("evidence_refs", "timestamp_refs", "frame_refs")
            )
            elements.append(
                Paragraph(
                    f"{_safe_pdf_text(metric.get('metric_id'))} "
                    f"v{_safe_pdf_text(metric.get('metric_version'))}: "
                    f"{reference_count} persisted evidence reference(s); "
                    f"validity {_safe_pdf_text(metric.get('validity_state'))}; "
                    f"confidence {_format_v2_number(metric.get('confidence_score'))}.",
                    styles["small"],
                )
            )
    else:
        elements.append(Paragraph("No persisted V2 metric evidence was available.", styles["body"]))
    elements.append(Paragraph("Limitations", styles["subheading"]))
    limitations = report.get("limitations", [])
    if limitations:
        elements.extend(_render_v2_limitations(limitations, styles))
    else:
        elements.append(Paragraph("No additional limitations were persisted.", styles["body"]))
    return elements


def _render_v2_repetitions(repetitions: list[dict[str, Any]], styles: dict) -> list:
    elements: list[Any] = [Paragraph("Repetitions", styles["subheading"])]
    if not repetitions:
        elements.append(Paragraph("Unavailable from the persisted V2 evidence.", styles["body"]))
        return elements
    rows = [["ID", "Action", "Time (s)", "Confidence", "Validity"]]
    for repetition in repetitions:
        time_range = (
            f"{_format_v2_number(repetition.get('start_ts'))}-"
            f"{_format_v2_number(repetition.get('end_ts'))}"
        )
        rows.append(
            [
                _safe_pdf_text(repetition.get("repetition_id")),
                _safe_pdf_text(repetition.get("action_type")),
                time_range,
                _format_v2_number(repetition.get("segmentation_confidence")),
                _safe_pdf_text(repetition.get("validity_state")),
            ]
        )
    elements.append(_v2_table(rows, [1.0, 1.5, 1.25, 1.25, 1.5]))
    return elements


def _render_v2_phases(phases: list[dict[str, Any]], styles: dict) -> list:
    elements: list[Any] = [Paragraph("Phases", styles["subheading"])]
    if not phases:
        elements.append(Paragraph("Unavailable from the persisted V2 evidence.", styles["body"]))
        return elements
    rows = [["Phase", "Repetition", "Time (s)", "Confidence", "Validity"]]
    for phase in phases:
        rows.append(
            [
                _safe_pdf_text(phase.get("phase_name")),
                _safe_pdf_text(phase.get("repetition_id")),
                f"{_format_v2_number(phase.get('start_ts'))}-"
                f"{_format_v2_number(phase.get('end_ts'))}",
                _format_v2_number(phase.get("confidence")),
                _safe_pdf_text(phase.get("validity_state")),
            ]
        )
    elements.append(_v2_table(rows, [1.4, 1.1, 1.25, 1.25, 1.5]))
    return elements


def _render_v2_metrics(metrics: list[dict[str, Any]], styles: dict) -> list:
    elements: list[Any] = [Paragraph("V2 metrics", styles["subheading"])]
    if not metrics:
        elements.append(Paragraph("Unavailable from the persisted V2 evidence.", styles["body"]))
        return elements
    rows = [["Metric", "Value", "Class", "Confidence", "Validity / proxy"]]
    for metric in metrics:
        value = _format_v2_number(metric.get("raw_value"), metric.get("unit"))
        classification = _safe_pdf_text(metric.get("classification_status"))
        validity_proxy = (
            f"{_safe_pdf_text(metric.get('validity_state'))} / "
            f"{_safe_pdf_text(metric.get('proxy_state'))}"
        )
        rows.append(
            [
                _safe_pdf_text(metric.get("metric_id")),
                value,
                classification,
                _format_v2_number(metric.get("confidence_score")),
                validity_proxy,
            ]
        )
        if value == "Unavailable":
            rows.append(
                [
                    "",
                    Paragraph(
                        f"Unavailable: {_safe_pdf_text(metric.get('unavailable_reason'))}",
                        styles["small"],
                    ),
                    "",
                    "",
                    "",
                ]
            )
    elements.append(_v2_table(rows, [2.0, 1.0, 1.1, 1.0, 1.4]))
    return elements


def _render_v2_signal_group(title: str, signals: list[dict[str, Any]], styles: dict) -> list:
    elements: list[Any] = [Paragraph(title, styles["subheading"])]
    if not signals:
        elements.append(Paragraph("Unavailable from the persisted V2 evidence.", styles["body"]))
        return elements
    for signal in signals:
        repetitions = ", ".join(signal.get("supporting_repetition_ids", [])) or "Unavailable"
        elements.append(
            Paragraph(
                f"<b>{_safe_pdf_text(signal.get('metric_id'))}</b>: "
                f"{_safe_pdf_text(signal.get('summary'))} "
                f"(repetitions: {_safe_pdf_text(repetitions)}; "
                f"confidence: {_format_v2_number(signal.get('confidence_score'))})",
                styles["body"],
            )
        )
    return elements


def _render_v2_representative_repetitions(report: dict[str, Any], styles: dict) -> list:
    elements: list[Any] = [Paragraph("Representative repetitions", styles["subheading"])]
    selections = report.get("representative_repetitions", {})
    rendered = False
    for label in ("best", "needs_work"):
        selection = selections.get(label)
        if not selection or not selection.get("available"):
            continue
        rendered = True
        elements.append(
            Paragraph(
                f"<b>{label.replace('_', ' ').title()}:</b> "
                f"{_safe_pdf_text(selection.get('repetition_id'))} - "
                f"{_safe_pdf_text(selection.get('rationale'))} "
                f"(confidence: {_format_v2_number(selection.get('confidence_score'))})",
                styles["body"],
            )
        )
    if not rendered:
        elements.append(Paragraph("Unavailable from the persisted V2 evidence.", styles["body"]))
    return elements


def _render_v2_detail_lines(details: list[tuple[str, Any]], styles: dict) -> list:
    return [
        Paragraph(f"<b>{escape(label)}:</b> {_safe_pdf_text(value)}", styles["body"])
        for label, value in details
    ]


def _render_v2_limitations(limitations: list[Any], styles: dict) -> list:
    return [
        Paragraph(f"Limitation: {_safe_pdf_text(limitation)}", styles["small"])
        for limitation in limitations
        if limitation
    ]


def _v2_table(rows: list[list[Any]], widths: list[float]) -> Table:
    table = Table(rows, colWidths=[width * inch for width in widths], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_PRIMARY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONT", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), FONT_SMALL),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#BDC3C7")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return table
