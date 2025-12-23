"""
Coach Report Generation Service

Converts findings JSON into narrative coaching reports with:
- Summary of key issues
- Prioritized action items
- Drill recommendations
- Weekly training plan
- Personalized notes

Supports two modes:
1. Deterministic (template-based, default) - always works
2. LLM-enhanced (if configured) - creates narrative reports via AI

The LLM receives only findings_payload and is instructed to avoid
inventing measurements or contradicting evidence.
"""

from __future__ import annotations

import logging

from backend.config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# Constants: Deterministic Templates
# ============================================================================

FINDING_SEVERITY_PRIORITY = {
    "high": 1,
    "medium": 2,
    "low": 3,
}

FINDING_TO_PRIORITY_DRILLS = {
    "HEAD_MOVEMENT": [
        "Mirror batting - observe head position throughout shot",
        "Wall batting - keep eyes locked on contact point",
        "Neck stability exercises before net sessions",
    ],
    "BALANCE_DRIFT": [
        "Balance board proprioceptive training",
        "Single-leg stance strength work",
        "Wide base batting drills with weight check",
    ],
    "KNEE_COLLAPSE": [
        "Knee bracing stability exercises",
        "Quad and glute strengthening",
        "Step-up drills with proper alignment",
    ],
    "ROTATION_TIMING": [
        "Hip rotation isolation drills",
        "Medicine ball rotational throws",
        "Explosive hip drive practice",
    ],
    "ELBOW_DROP": [
        "Arm positioning drills with partner feedback",
        "Elbow height awareness exercises",
        "Bat path visualization with slow-motion analysis",
    ],
}

SUMMARY_TEMPLATES = {
    "excellent": (
        "Your technique shows strong fundamentals across all evaluated metrics. "
        "Focus on consistency and maintaining this high standard in match situations."
    ),
    "good": (
        "Your technique demonstrates solid fundamentals with a few minor areas to refine. "
        "The recommended drills will help eliminate the remaining inconsistencies."
    ),
    "fair": (
        "Your technique has several areas requiring focused improvement. "
        "Prioritize the high-severity findings and work systematically through the drills."
    ),
    "poor": (
        "Your technique requires comprehensive improvement across multiple areas. "
        "Start with the highest-priority findings and build foundational movement patterns."
    ),
}

WEEKLY_PLAN_TEMPLATE = [
    {
        "day": "Monday",
        "focus": "Foundation & Strength",
        "duration": "60 min",
        "activities": ["Warm-up (10min)", "Prioritized drills (35min)", "Cool-down (15min)"],
    },
    {
        "day": "Tuesday",
        "focus": "Technique Isolation",
        "duration": "45 min",
        "activities": ["Drill sets (30min)", "Self-analysis & video review (15min)"],
    },
    {
        "day": "Wednesday",
        "focus": "Rest & Recovery",
        "duration": "30 min",
        "activities": ["Light mobility work", "Flexibility training"],
    },
    {
        "day": "Thursday",
        "focus": "Integration & Game Practice",
        "duration": "75 min",
        "activities": [
            "Drills (20min)",
            "Net practice focusing on issues (45min)",
            "Review (10min)",
        ],
    },
    {
        "day": "Friday",
        "focus": "Reinforcement",
        "duration": "60 min",
        "activities": ["Priority drills (25min)", "Match simulation (30min)", "Analysis (5min)"],
    },
    {
        "day": "Saturday",
        "focus": "Match Play (Optional)",
        "duration": "Varies",
        "activities": ["Apply learned patterns in actual match or practice game"],
    },
    {
        "day": "Sunday",
        "focus": "Analysis & Planning",
        "duration": "30 min",
        "activities": ["Review week's progress", "Adjust next week's focus", "Record improvements"],
    },
]


# ============================================================================
# Utility Functions
# ============================================================================


def _get_summary_level(findings: list[dict]) -> str:
    """Determine overall summary level based on findings."""
    if not findings:
        return "excellent"

    high_count = sum(1 for f in findings if f.get("severity") == "high")
    medium_count = sum(1 for f in findings if f.get("severity") == "medium")

    if high_count >= 3:
        return "poor"
    elif high_count >= 1 or medium_count >= 2:
        return "fair"
    elif medium_count >= 1:
        return "good"
    else:
        return "good"


def _get_top_issues(findings: list[dict], top_n: int = 3) -> list[dict]:
    """Extract top N issues sorted by severity and title."""
    sorted_findings = sorted(
        findings,
        key=lambda f: (
            FINDING_SEVERITY_PRIORITY.get(f.get("severity", "low"), 99),
            f.get("title", ""),
        ),
    )

    return [
        {
            "issue": f.get("title", "Unknown"),
            "severity": f.get("severity", "low"),
            "why_it_matters": f.get("why_it_matters", ""),
            "cues": f.get("cues", [])[:2],  # Top 2 cues
        }
        for f in sorted_findings[:top_n]
    ]


def _get_recommended_drills(findings: list[dict], max_drills: int = 8) -> list[str]:
    """Extract unique drills from findings, limited to max_drills."""
    all_drills: list[str] = []

    # Sort by severity to prioritize high-severity drills
    sorted_findings = sorted(
        findings,
        key=lambda f: FINDING_SEVERITY_PRIORITY.get(f.get("severity", "low"), 99),
    )

    for finding in sorted_findings:
        code = finding.get("code", "")
        if code in FINDING_TO_PRIORITY_DRILLS:
            for drill in FINDING_TO_PRIORITY_DRILLS[code]:
                if drill not in all_drills and len(all_drills) < max_drills:
                    all_drills.append(drill)

    return all_drills


def _build_weekly_plan(findings: list[dict], player_context: dict | None = None) -> list[dict]:
    """Build personalized weekly plan based on findings."""
    # Start with template - convert to mutable dicts
    plan: list[dict] = [day.copy() for day in WEEKLY_PLAN_TEMPLATE]

    # Inject specific drills into the plan
    top_drills = _get_recommended_drills(findings, max_drills=3)

    # Customize Monday with top drills
    if top_drills:
        plan[0]["activities"][1] = f"Prioritized drills: {', '.join(top_drills[:2])} (35min)"

    # Customize Thursday with focus area
    high_severity = [f for f in findings if f.get("severity") == "high"]
    if high_severity:
        focus_code = high_severity[0].get("code", "")
        plan[3]["focus"] = f"Technique Isolation: {focus_code.replace('_', ' ').title()}"

    return plan


# ============================================================================
# Report Generation
# ============================================================================


def generate_report_text(
    findings_payload: dict,
    player_context: dict | None = None,
) -> dict:
    """
    Generate a coaching report from findings JSON.

    Deterministic by default. If COACH_REPORT_LLM_ENABLED is true,
    calls LLM for narrative enhancement (not implemented in MVP).

    Args:
        findings_payload: Output from generate_findings()
            Expected structure:
            {
                "overall_level": "low|medium|high",
                "findings": [...],
                "context": {...}
            }
        player_context: Optional context about the player
            {
                "name": "Player Name",
                "role": "batter|bowler",
                "age": int,
                "experience": "months|years"
            }

    Returns:
        {
            "summary": str,
            "top_issues": [...],
            "drills": [...],
            "one_week_plan": [...],
            "notes": str,
            "generated_with_llm": bool
        }
    """
    findings = findings_payload.get("findings", [])
    context = findings_payload.get("context", {})

    # Merge contexts
    effective_context = {}
    if player_context:
        effective_context.update(player_context)
    if context:
        effective_context.update(context)

    logger.info(f"Generating report for {len(findings)} findings")

    # Deterministic path (always works)
    summary_level = _get_summary_level(findings)
    summary_text = SUMMARY_TEMPLATES.get(summary_level, SUMMARY_TEMPLATES["good"])

    # Personalize summary
    player_name = effective_context.get("name", "Your")
    summary_text = f"{player_name}'s Analysis: {summary_text}"

    # Build core report
    report = {
        "summary": summary_text,
        "top_issues": _get_top_issues(findings),
        "drills": _get_recommended_drills(findings),
        "one_week_plan": _build_weekly_plan(findings, effective_context),
        "notes": _generate_notes(findings, effective_context),
        "generated_with_llm": False,
    }

    # LLM enhancement (MVP: not implemented, placeholder)
    if getattr(settings, "COACH_REPORT_LLM_ENABLED", False):
        logger.info("LLM enhancement requested but not yet implemented in MVP")
        # TODO: Integrate with AI service when ready
        # report = _enhance_with_llm(report, findings_payload, effective_context)

    return report


def _generate_notes(findings: list[dict], player_context: dict | None = None) -> str:
    """Generate personalized closing notes."""
    notes_parts = []

    if not findings:
        return "Excellent technique! Continue maintaining your current practice standards."

    high_severity = [f for f in findings if f.get("severity") == "high"]

    if high_severity:
        notes_parts.append(
            f"Priority: Focus on the {len(high_severity)} high-severity finding(s) first. "
            "Building strong fundamentals in these areas will elevate your overall performance."
        )

    if len(findings) >= 3:
        notes_parts.append(
            "Consider working with a coach for personalized feedback on drill execution. "
            "Video analysis of your technique can help identify subtle issues."
        )

    notes_parts.append(
        "Progress is built on consistency. Dedicate time to these drills 5-6 days per week "
        "and measure improvements every 2 weeks."
    )

    if player_context and player_context.get("role") == "bowler":
        notes_parts.append("Remember that bowling action changes are gradual - patience is key.")
    elif player_context and player_context.get("role") == "batter":
        notes_parts.append("Muscle memory develops through repetition - focus on quality reps.")

    return " ".join(notes_parts)


# ============================================================================
# LLM Enhancement (Placeholder for Future)
# ============================================================================


def _enhance_with_llm(
    deterministic_report: dict,
    findings_payload: dict,
    context: dict | None = None,
) -> dict:
    """
    Enhance deterministic report with LLM narrative.

    TODO: Implement when ai_service is available.
    The LLM should:
    1. Receive ONLY findings_payload and context
    2. Be instructed to NOT invent measurements
    3. Rewrite summary and notes for better narrative flow
    4. Keep all structured data (drills, plan) from deterministic path

    Args:
        deterministic_report: Base report from generate_report_text()
        findings_payload: Original findings dict
        context: Player context if provided

    Returns:
        Enhanced report with LLM-generated summary and notes
    """
    logger.warning("LLM enhancement not yet implemented")
    return deterministic_report
