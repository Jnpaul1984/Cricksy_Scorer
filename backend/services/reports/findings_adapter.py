"""
Coach Report V2: Common findings schema and adapter.

Converts analysis-specific findings (bowling/batting/wicketkeeping/fielding)
into a universal structure for consistent PDF rendering.
"""

from __future__ import annotations

from typing import Any, TypedDict


class VideoEvidence(TypedDict, total=False):
    """Video evidence structure."""

    worst_frames: list[dict[str, Any]]
    bad_segments: list[dict[str, Any]]


class CommonFinding(TypedDict):
    """
    Universal finding structure for all analysis types.

    This schema enables consistent PDF rendering across bowling, batting,
    wicketkeeping, and fielding reports.
    """

    code: str  # Finding code (e.g., "HEAD_MOVEMENT", "INCONSISTENT_RELEASE_POINT")
    title: str  # Human-readable title (e.g., "Head Movement")
    severity: str  # "high", "medium", "low"
    what_happening: str  # 1-2 sentences: what's wrong
    why_matters: str  # 1-2 sentences: impact in coach language
    drills: list[str]  # Max 3 drills
    metrics: dict[str, Any]  # Compact metrics (score, threshold, pass/fail)
    evidence: VideoEvidence  # Timestamp ranges and worst frames
    phase: str | None  # Optional: "Quick" or "Deep" for legacy context


def adapt_finding(finding: dict[str, Any], analysis_phase: str | None = None) -> CommonFinding:
    """
    Convert an analysis-specific finding to CommonFinding schema.

    Args:
        finding: Raw finding dict from coach_findings.generate_*_findings()
        analysis_phase: Optional "Quick" or "Deep" label

    Returns:
        CommonFinding with standardized structure
    """
    # Extract core fields
    code = finding.get("code", "UNKNOWN")
    title = finding.get("title", "Unknown Finding")
    severity = finding.get("severity", "low")

    # Extract what's happening (from cues or evidence description)
    cues = finding.get("cues", [])
    what_happening = " ".join(cues[:2]) if cues else "Technical issue detected in video analysis."
    # Truncate to 2 sentences max
    sentences = what_happening.split(". ")
    what_happening = ". ".join(sentences[:2])
    if not what_happening.endswith("."):
        what_happening += "."

    # Extract why it matters (first cue if multiple, or derive from title)
    why_matters = finding.get("why_matters") or _generate_why_matters(title, severity)

    # Extract drills (max 3)
    drills = finding.get("suggested_drills", [])[:3]

    # Extract metrics in compact format
    evidence_dict = finding.get("evidence", {})
    metrics = {}
    for key, val in evidence_dict.items():
        if isinstance(val, (int, float)):
            metrics[key] = val

    # Extract video evidence
    video_evidence: VideoEvidence = finding.get("video_evidence", {})  # type: ignore

    return CommonFinding(
        code=code,
        title=title,
        severity=severity,
        what_happening=what_happening,
        why_matters=why_matters,
        drills=drills,
        metrics=metrics,
        evidence=video_evidence,
        phase=analysis_phase,
    )


def consolidate_findings(
    quick_findings: dict[str, Any] | None, deep_findings: dict[str, Any] | None
) -> list[CommonFinding]:
    """
    Consolidate Quick and Deep findings into a single unified list.

    Rules:
    - Prefer Deep findings when both exist for the same code
    - Mark Quick-only findings with phase="Quick" as a small note
    - Remove duplicates by code
    - Sort by severity (high → medium → low)

    Args:
        quick_findings: Quick analysis findings dict
        deep_findings: Deep analysis findings dict

    Returns:
        Unified list of CommonFindings, sorted by severity
    """
    findings_by_code: dict[str, CommonFinding] = {}

    # Process Quick findings first
    if quick_findings and "findings" in quick_findings:
        for finding in quick_findings["findings"]:
            code = finding.get("code")
            if code:
                findings_by_code[code] = adapt_finding(finding, analysis_phase="Quick")

    # Process Deep findings (overwrites Quick if same code)
    if deep_findings and "findings" in deep_findings:
        for finding in deep_findings["findings"]:
            code = finding.get("code")
            if code:
                findings_by_code[code] = adapt_finding(finding, analysis_phase="Deep")

    # Sort by severity
    severity_order = {"high": 0, "medium": 1, "low": 2}
    consolidated = sorted(
        findings_by_code.values(), key=lambda f: (severity_order.get(f["severity"], 3), f["title"])
    )

    return consolidated


def extract_top_priorities(
    findings: list[CommonFinding], max_count: int = 3
) -> list[CommonFinding]:
    """
    Extract top priority findings for Coach Summary page.

    Args:
        findings: Consolidated findings list
        max_count: Maximum number of top priorities (default 2-3)

    Returns:
        Top priority findings (high severity first)
    """
    # Filter high severity findings first
    high_severity = [f for f in findings if f["severity"] == "high"]
    if len(high_severity) >= max_count:
        return high_severity[:max_count]

    # If not enough high, add medium severity
    medium_severity = [f for f in findings if f["severity"] == "medium"]
    top_priorities = high_severity + medium_severity
    return top_priorities[:max_count]


def extract_secondary_focus(
    findings: list[CommonFinding], top_priorities: list[CommonFinding], max_count: int = 2
) -> list[CommonFinding]:
    """
    Extract secondary focus findings (not in top priorities).

    Args:
        findings: All consolidated findings
        top_priorities: Findings already in top priorities
        max_count: Maximum secondary items (default 1-2)

    Returns:
        Secondary focus findings
    """
    top_codes = {f["code"] for f in top_priorities}
    remaining = [f for f in findings if f["code"] not in top_codes]
    return remaining[:max_count]


def generate_this_week_actions(findings: list[CommonFinding]) -> list[str]:
    """
    Generate "This Week's Focus" action bullets (max 3).

    Args:
        findings: All consolidated findings

    Returns:
        3 action bullets derived from top findings
    """
    actions = []

    # Take first 3 findings and extract primary drill from each
    for finding in findings[:3]:
        drills = finding.get("drills", [])
        if drills:
            # Format as action: "Work on [drill]"
            action = f"Work on: {drills[0]}"
            actions.append(action)
        else:
            # Fallback: use title as action
            action = f"Address: {finding['title']}"
            actions.append(action)

    # Ensure exactly 3 bullets
    while len(actions) < 3:
        actions.append("Continue technique review and practice")

    return actions[:3]


def _generate_why_matters(title: str, severity: str) -> str:
    """
    Generate a default "why it matters" statement if not provided.

    Args:
        title: Finding title
        severity: Severity level

    Returns:
        Coach-friendly explanation of impact
    """
    impact_map = {
        "high": "Critical issue that affects performance and increases injury risk.",
        "medium": "Important technique flaw that limits effectiveness and consistency.",
        "low": "Minor adjustment that can improve overall efficiency.",
    }

    base_impact = impact_map.get(severity, "Technique adjustment needed.")
    return f"{title} impacts your mechanics. {base_impact}"
