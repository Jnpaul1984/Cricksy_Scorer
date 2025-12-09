"""
AI Match Summary Service.

This module provides rich AI-style narrative summaries for matches,
including headline, narrative, tactical themes, and player highlights.

Uses the existing MatchCaseStudy data as the foundation and generates
rule-based text for V1.

TODO: Replace rule-based generation with actual LLM integration.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel

from backend.api.schemas.case_study import (
    CaseStudyKeyPlayer,
    CaseStudyMatch,
    CaseStudyPhase,
    MatchCaseStudyResponse,
)
from backend.services.analytics_case_study import build_match_case_study

# ---------------------------------------------------------------------------
# Pydantic Schema
# ---------------------------------------------------------------------------


class MatchAiSummary(BaseModel):
    """Rich AI-generated narrative summary for a match."""

    match_id: str
    headline: str
    narrative: str
    tactical_themes: list[str]
    player_highlights: list[str]
    tags: list[str]
    generated_at: datetime


# ---------------------------------------------------------------------------
# Helper: Determine Winner Name
# ---------------------------------------------------------------------------


def _extract_winner_name(match: CaseStudyMatch) -> str | None:
    """Extract the winner's name from the result string."""
    result_lower = match.result.lower()

    # Try to find "X won by" pattern
    if " won " in result_lower:
        # e.g., "Lions won by 18 runs"
        winner_part = match.result.split(" won ")[0].strip()
        return winner_part

    return None


# ---------------------------------------------------------------------------
# Helper: Generate Headline
# ---------------------------------------------------------------------------


def _generate_headline(
    match: CaseStudyMatch,
    key_phase: CaseStudyPhase | None,
    top_player: CaseStudyKeyPlayer | None,
) -> str:
    """Generate a concise 1-sentence headline for the match."""
    winner = _extract_winner_name(match)

    # If we have a winner and a standout player
    if winner and top_player:
        if top_player.batting and top_player.batting.runs >= 50:
            return (
                f"{top_player.name}'s {top_player.batting.runs} "
                f"powers {winner} to victory in {match.format} clash."
            )
        elif top_player.bowling and top_player.bowling.wickets >= 3:
            return (
                f"{top_player.name}'s {top_player.bowling.wickets}-wicket haul "
                f"seals {winner}'s win."
            )

    # If we have a decisive phase
    if winner and key_phase:
        phase_name = key_phase.id.lower()
        if key_phase.impact == "positive":
            return f"{winner} dominate the {phase_name} to claim {match.format} victory."
        else:
            return f"{winner} edge home despite struggles in the {phase_name}."

    # Generic fallback
    if winner:
        return f"{winner} win in a competitive {match.format} encounter."

    return f"Thrilling {match.format} match ends in a tightly contested finish."


# ---------------------------------------------------------------------------
# Helper: Generate Narrative
# ---------------------------------------------------------------------------


def _generate_narrative(
    match: CaseStudyMatch,
    phases: list[CaseStudyPhase],
    key_players: list[CaseStudyKeyPlayer],
) -> str:
    """Generate a 2-4 sentence narrative summary."""
    parts: list[str] = []

    # Match overview
    parts.append(f"In this {match.format} encounter, {match.result}.")

    # First innings summary
    if match.innings:
        inn1 = match.innings[0]
        parts.append(
            f"{inn1.team} set a target with {inn1.runs}/{inn1.wickets} "
            f"in {inn1.overs} overs at a run rate of {inn1.run_rate}."
        )

    # Key phase impact
    if phases:
        key_phase = max(phases, key=lambda p: abs(p.net_swing_vs_par))
        phase_name = key_phase.label.split("(")[0].strip().lower()
        if key_phase.impact == "positive":
            parts.append(
                f"The {phase_name} proved decisive, "
                f"with {key_phase.runs} runs scored at {key_phase.run_rate} RPO, "
                f"{key_phase.net_swing_vs_par:+d} above par."
            )
        else:
            parts.append(
                f"The {phase_name} was challenging, "
                f"yielding only {key_phase.runs} runs with {key_phase.wickets} wickets lost."
            )

    # Standout performer
    if key_players:
        top = key_players[0]
        if top.batting and top.batting.runs >= 30:
            sr = top.batting.strike_rate
            parts.append(
                f"{top.name} was the standout with {top.batting.runs} runs "
                f"at a strike rate of {sr:.1f}."
            )
        elif top.bowling and top.bowling.wickets >= 2:
            eco = top.bowling.economy
            parts.append(
                f"{top.name} led the bowling attack with {top.bowling.wickets} wickets "
                f"at an economy of {eco:.2f}."
            )

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Helper: Extract Tactical Themes
# ---------------------------------------------------------------------------


def _extract_tactical_themes(
    phases: list[CaseStudyPhase],
) -> tuple[list[str], list[str]]:
    """
    Extract tactical themes from phase analysis.

    Returns (themes, tags).
    """
    themes: list[str] = []
    tags: list[str] = []

    # Group phases by id for analysis
    by_id: dict[str, list[CaseStudyPhase]] = {}
    for p in phases:
        by_id.setdefault(p.id, []).append(p)

    # Powerplay analysis
    pp_phases = by_id.get("powerplay", [])
    for pp in pp_phases:
        if pp.net_swing_vs_par >= 10:
            themes.append(
                f"Strong powerplay performance with {pp.runs} runs, "
                f"{pp.net_swing_vs_par:+d} above par."
            )
            tags.append("powerplay_domination")
        elif pp.net_swing_vs_par <= -10:
            themes.append(
                f"Powerplay struggles cost runs, falling {abs(pp.net_swing_vs_par)} below par."
            )
            tags.append("powerplay_struggle")

    # Death overs analysis
    death_phases = by_id.get("death", [])
    for death in death_phases:
        if death.net_swing_vs_par >= 10:
            themes.append(
                f"Explosive finish in the death overs with {death.runs} runs, "
                f"{death.net_swing_vs_par:+d} above par."
            )
            tags.append("death_surge")
        elif death.net_swing_vs_par <= -10 or death.wickets >= 3:
            themes.append(
                f"Death overs collapse: {death.wickets} wickets lost, "
                f"{death.net_swing_vs_par} below par."
            )
            tags.append("death_collapse")

    # Middle overs analysis
    middle_phases = by_id.get("middle", [])
    for mid in middle_phases:
        if mid.net_swing_vs_par <= -10:
            themes.append("Scoring slowed significantly in the middle overs.")
            tags.append("middle_squeeze")
        elif mid.net_swing_vs_par >= 10:
            themes.append(f"Strong middle-overs acceleration with {mid.runs} runs.")
            tags.append("middle_acceleration")

    # Fallback if no significant swings
    if not themes:
        themes.append("Both sides traded momentum across phases without a single dominant spell.")
        tags.append("balanced_contest")

    return themes, tags


# ---------------------------------------------------------------------------
# Helper: Extract Player Highlights
# ---------------------------------------------------------------------------


def _extract_player_highlights(
    key_players: list[CaseStudyKeyPlayer],
) -> list[str]:
    """Extract notable player performances as highlight strings."""
    highlights: list[str] = []

    for player in key_players[:4]:  # Top 4 players
        parts: list[str] = []

        # Batting highlight
        if player.batting and player.batting.runs >= 20:
            balls = player.batting.balls
            runs = player.batting.runs
            boundaries = player.batting.boundaries
            fours = boundaries.get("fours", 0) if boundaries else 0
            sixes = boundaries.get("sixes", 0) if boundaries else 0

            if runs >= 50:
                parts.append(f"{player.name}'s brilliant {runs}({balls}) anchored the innings")
            elif runs >= 30:
                parts.append(f"{player.name} contributed a useful {runs}({balls})")
            else:
                parts.append(f"{player.name} made {runs} off {balls} balls")

            if fours + sixes >= 5:
                parts[-1] += f" with {fours} fours and {sixes} sixes"

        # Bowling highlight
        if player.bowling and player.bowling.wickets >= 1:
            wkts = player.bowling.wickets
            runs_conceded = player.bowling.runs
            overs = player.bowling.overs
            eco = player.bowling.economy

            if wkts >= 3:
                if parts:
                    parts.append(f"and also claimed {wkts} wickets for {runs_conceded} runs")
                else:
                    parts.append(
                        f"{player.name}'s match-winning spell of {wkts}/{runs_conceded} "
                        f"in {overs} overs was decisive"
                    )
            elif wkts >= 2 and not parts:
                parts.append(f"{player.name} picked up {wkts} wickets at {eco:.2f} economy")

        # Fielding highlight
        if player.fielding:
            catches = player.fielding.catches
            run_outs = player.fielding.run_outs
            if catches >= 2 or run_outs >= 1:
                if parts:
                    parts.append(f"and was sharp in the field with {catches} catches")
                else:
                    parts.append(f"{player.name} contributed with {catches} catches in the field")

        if parts:
            highlights.append(". ".join(parts) + ".")

    # Fallback if no highlights extracted
    if not highlights:
        highlights.append(
            "Multiple players made contributions, but no single standout performance emerged."
        )

    return highlights


# ---------------------------------------------------------------------------
# Main Service Function
# ---------------------------------------------------------------------------


async def build_match_ai_summary(
    match_id: str,
    user_id: str,
) -> MatchAiSummary:
    """
    Build a rich AI-style narrative summary for a match.

    This is a rule-based V1 implementation that derives insights from
    the existing MatchCaseStudy data structure.

    TODO: Replace rule-based generation with actual LLM call for richer,
    more natural language summaries.

    Args:
        match_id: The match UUID string
        user_id: The user requesting the summary (for auth/logging)

    Returns:
        MatchAiSummary with headline, narrative, themes, highlights, and tags

    Raises:
        ValueError: If match not found
    """
    # Fetch the full case study (reuse existing logic)
    case_study: MatchCaseStudyResponse = await build_match_case_study(
        match_id=match_id,
        user_id=user_id,
    )

    match = case_study.match
    phases = case_study.phases
    key_players = case_study.key_players

    # Determine key phase and top player for headline
    key_phase = max(phases, key=lambda p: abs(p.net_swing_vs_par)) if phases else None
    top_player = key_players[0] if key_players else None

    # Generate components
    headline = _generate_headline(match, key_phase, top_player)
    narrative = _generate_narrative(match, phases, key_players)
    tactical_themes, tags = _extract_tactical_themes(phases)
    player_highlights = _extract_player_highlights(key_players)

    return MatchAiSummary(
        match_id=match.id,
        headline=headline,
        narrative=narrative,
        tactical_themes=tactical_themes,
        player_highlights=player_highlights,
        tags=tags,
        generated_at=datetime.now(UTC),
    )
