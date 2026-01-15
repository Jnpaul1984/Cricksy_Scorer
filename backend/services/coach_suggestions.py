"""
AI Coaching Suggestions Generator

Phase 3: Generate coaching suggestions based on findings, goals, and compliance.

CRITICAL RULES:
- AI assists only, never overrides coach intent
- Suggestions must be explainable and traceable to findings
- One primary focus per session (avoid overwhelming)
- Drills come from existing drill databases only
- Player-facing text is simplified and optional

"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _rank_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Rank findings by priority: severity → compliance failure → persistence.

    Args:
        findings: List of finding objects with code, title, severity, metrics

    Returns:
        Sorted findings list (highest priority first)
    """

    def priority_score(finding: dict[str, Any]) -> tuple[int, int]:
        # Severity ranking: critical=3, moderate=2, minor=1, informational=0
        severity_map = {
            "critical": 3,
            "moderate": 2,
            "minor": 1,
            "informational": 0,
        }
        severity = finding.get("severity", "informational")
        severity_rank = severity_map.get(severity, 0)

        # Check if this finding has a low score (< 0.60 = persistent issue)
        metrics = finding.get("metrics", {})
        score = 0.0
        for _metric_name, metric_val in metrics.items():
            if isinstance(metric_val, dict) and "score" in metric_val:
                score = float(metric_val["score"])
                break

        # Persistent issue if score < 0.60
        is_persistent = 1 if score < 0.60 else 0

        # Return (severity_rank, is_persistent) for sorting (descending)
        return (-severity_rank, -is_persistent)

    sorted_findings = sorted(findings, key=priority_score)
    return sorted_findings


def _select_focus(
    findings: list[dict[str, Any]],
    outcomes: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Select primary and optional secondary focus areas.

    Args:
        findings: Ranked findings (highest priority first)
        outcomes: Outcomes vs goals (zone/metric compliance)

    Returns:
        {primary_focus, secondary_focus, rationale}
    """
    primary_focus = None
    secondary_focus = None
    rationale = []

    if not findings:
        return {
            "primary_focus": "No critical issues detected",
            "secondary_focus": None,
            "rationale": ["All metrics within acceptable ranges"],
        }

    # Strategy 1: Check for critical failed goal compliance
    if outcomes:
        metric_outcomes = outcomes.get("metrics", [])
        failed_metrics = [m for m in metric_outcomes if not m.get("passed", True)]

        if failed_metrics:
            # Primary focus = first failed goal
            failed = failed_metrics[0]
            primary_focus = failed.get("title", "Goal compliance")
            rationale.append(
                f"Coach goal not met: {failed.get('code', 'N/A')} "
                f"(target: {failed.get('target_score', 0):.0%}, "
                f"actual: {failed.get('actual_score', 0):.0%})"
            )

    # Strategy 2: Fallback to highest severity finding
    if not primary_focus and findings:
        top_finding = findings[0]
        primary_focus = top_finding.get("title", "Technical focus needed")
        rationale.append(
            f"Highest priority finding: {top_finding.get('code', 'N/A')} "
            f"(severity: {top_finding.get('severity', 'N/A')})"
        )

    # Strategy 3: Secondary focus = second finding if exists and different
    if len(findings) > 1:
        second_finding = findings[1]
        if second_finding.get("title") != primary_focus:
            secondary_focus = second_finding.get("title")
            rationale.append(f"Secondary area: {second_finding.get('code', 'N/A')}")

    return {
        "primary_focus": primary_focus or "General technique refinement",
        "secondary_focus": secondary_focus,
        "rationale": rationale,
    }


def _select_coaching_cues(findings: list[dict[str, Any]], max_cues: int = 3) -> list[str]:
    """
    Extract coaching cues from top findings.

    Args:
        findings: Ranked findings
        max_cues: Maximum number of cues to return

    Returns:
        List of coaching cue strings
    """
    cues = []
    for finding in findings[:max_cues]:
        finding_cues = finding.get("coaching_cues", [])
        if finding_cues and isinstance(finding_cues, list):
            # Take first cue from each finding
            cues.append(finding_cues[0])

    return cues[:max_cues]


def _select_drills(findings: list[dict[str, Any]], max_drills: int = 3) -> list[str]:
    """
    Extract suggested drills from top findings.

    Args:
        findings: Ranked findings
        max_drills: Maximum number of drills to return

    Returns:
        List of drill strings (from existing drill databases)
    """
    drills = []
    seen = set()  # Avoid duplicates

    for finding in findings[:3]:  # Top 3 findings only
        finding_drills = finding.get("suggested_drills", [])
        if finding_drills and isinstance(finding_drills, list):
            for drill in finding_drills[:2]:  # Max 2 drills per finding
                if drill not in seen:
                    drills.append(drill)
                    seen.add(drill)
                    if len(drills) >= max_drills:
                        return drills

    return drills


def _propose_next_goal(
    findings: list[dict[str, Any]],
    outcomes: dict[str, Any] | None,
) -> dict[str, Any]:
    """
    Propose next session goal based on outcomes and trends.

    Args:
        findings: Ranked findings
        outcomes: Current goal outcomes

    Returns:
        {type, description, target}
    """
    # Strategy 1: If goal failed, propose refinement
    if outcomes:
        metric_outcomes = outcomes.get("metrics", [])
        failed_metrics = [m for m in metric_outcomes if not m.get("passed", True)]

        if failed_metrics:
            failed = failed_metrics[0]
            return {
                "type": "metric_improvement",
                "description": f"Improve {failed.get('title', 'metric')} score",
                "target": round(failed.get("target_score", 0.70) + 0.05, 2),  # Slightly higher
                "metric_code": failed.get("code"),
            }

        # Strategy 2: If goal passed, maintain or increase
        passed_metrics = [m for m in metric_outcomes if m.get("passed", True)]
        if passed_metrics:
            passed = passed_metrics[0]
            return {
                "type": "metric_maintenance",
                "description": f"Maintain {passed.get('title', 'metric')} consistency",
                "target": round(passed.get("target_score", 0.70), 2),
                "metric_code": passed.get("code"),
            }

    # Strategy 3: Focus on highest severity finding
    if findings:
        top_finding = findings[0]
        metrics = top_finding.get("metrics", {})
        current_score = 0.0
        for _metric_name, metric_val in metrics.items():
            if isinstance(metric_val, dict) and "score" in metric_val:
                current_score = float(metric_val["score"])
                break

        return {
            "type": "finding_improvement",
            "description": f"Address {top_finding.get('title', 'technical issue')}",
            "target": round(min(current_score + 0.15, 0.85), 2),
            "metric_code": top_finding.get("code"),
        }

    # Fallback: General improvement
    return {
        "type": "general",
        "description": "Refine overall technique consistency",
        "target": 0.75,
    }


def generate_coach_suggestions(
    job: Any,  # VideoAnalysisJob
    previous_jobs: list[Any] | None = None,
) -> dict[str, Any]:
    """
    Generate coaching suggestions for a completed analysis job.

    Args:
        job: VideoAnalysisJob with deep_findings, outcomes, goal_compliance_pct
        previous_jobs: Optional list of prior jobs (for trend analysis)

    Returns:
        {
            primary_focus: str,
            secondary_focus: str | None,
            coaching_cues: list[str],
            drills: list[str],
            proposed_next_goal: dict,
            rationale: list[str],
        }

    RULES:
    - Only ONE primary focus per session
    - Drills come from existing drill databases (in findings)
    - Suggestions are traceable to findings/outcomes
    - Coach approval required before application
    """
    # Extract findings from job
    deep_findings = job.deep_findings or {}
    findings_list = deep_findings.get("findings", [])
    outcomes = job.outcomes

    # Rank findings by priority
    ranked_findings = _rank_findings(findings_list)

    # Select focus areas
    focus = _select_focus(ranked_findings, outcomes)

    # Extract coaching cues
    cues = _select_coaching_cues(ranked_findings, max_cues=3)

    # Extract drills
    drills = _select_drills(ranked_findings, max_drills=3)

    # Propose next goal
    next_goal = _propose_next_goal(ranked_findings, outcomes)

    # Build rationale
    rationale = focus["rationale"].copy()
    if job.goal_compliance_pct is not None:
        rationale.append(f"Overall compliance: {job.goal_compliance_pct:.0%}")

    # Optional: Trend analysis from previous jobs
    if previous_jobs and len(previous_jobs) > 0:
        rationale.append(f"Based on {len(previous_jobs)} previous session(s)")

    return {
        "primary_focus": focus["primary_focus"],
        "secondary_focus": focus["secondary_focus"],
        "coaching_cues": cues,
        "drills": drills,
        "proposed_next_goal": next_goal,
        "rationale": rationale,
    }


def generate_player_summary(coach_suggestions: dict[str, Any]) -> dict[str, Any]:
    """
    Translate coach suggestions into simplified player-facing language.

    Args:
        coach_suggestions: Output from generate_coach_suggestions()

    Returns:
        {
            focus: str,
            what_to_practice: list[str],
            encouragement: str,
        }

    RULES:
    - Remove technical metrics and severity labels
    - Use simple, positive language
    - Keep intent clear without jargon
    """
    primary_focus = coach_suggestions.get("primary_focus", "Technique")
    drills = coach_suggestions.get("drills", [])
    cues = coach_suggestions.get("coaching_cues", [])

    # Simplify focus statement
    focus = f"Focus on: {primary_focus}"

    # Simplify what to practice (drills + cues combined)
    what_to_practice = []

    # Add simplified drills (first 2)
    for drill in drills[:2]:
        # Remove technical jargon: "VMO (vastus medialis obliquus)" → "leg muscle"
        simplified = drill.replace("VMO (vastus medialis obliquus)", "leg muscle")
        simplified = simplified.replace("proprioceptive", "balance")
        what_to_practice.append(simplified)

    # Add simplified cues (first 1-2)
    for cue in cues[:2]:
        what_to_practice.append(cue)

    # Generate encouragement
    proposed_goal = coach_suggestions.get("proposed_next_goal", {})
    goal_desc = proposed_goal.get("description", "")

    if "improve" in goal_desc.lower():
        encouragement = "Keep practicing! You're making progress toward your goals."
    elif "maintain" in goal_desc.lower():
        encouragement = "Great work! Now focus on consistency."
    else:
        encouragement = "Stay committed to the fundamentals. Improvement takes time."

    return {
        "focus": focus,
        "what_to_practice": what_to_practice[:3],  # Max 3 items
        "encouragement": encouragement,
    }
