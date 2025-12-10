"""
Match Context Package Service.

Generates a comprehensive JSON representation of a match for AI/LLM consumption.
Includes metadata, phase breakdowns, player performances, and AI callouts.

Type Hierarchy:
- MatchContextPackage: Full match context (~15-20k tokens)
- CommentaryContext: Minimal slice for live commentary (<3k tokens)
- CaseStudyContext: Deep analysis context (~8k tokens)
- PlayerProfileContext: Single player focus (~1k tokens)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.sql_app import models


# =============================================================================
# Core Type Definitions
# =============================================================================


class PhaseEvent(TypedDict, total=False):
    """
    A notable event within a match phase (boundary, wicket, etc.).

    Used to track key moments that influenced the phase outcome.
    """

    over: float  # Over number (e.g., 5.3 = 5th over, 3rd ball)
    ball: int  # Ball number within the over (1-6)
    event_type: Literal["boundary_4", "boundary_6", "wicket", "dot_ball", "extra"]
    runs: int  # Runs scored on this ball
    description: str  # Human-readable description (e.g., "SIX over long-on")
    player_id: str | None  # ID of the batter/bowler involved
    player_name: str | None  # Name for display


class PhaseBreakdown(TypedDict):
    """
    Statistical breakdown of a single match phase.

    Phases are defined by over ranges:
    - T20: Powerplay (1-6), Middle (7-15), Death (16-20)
    - ODI: Powerplay (1-10), Middle (11-40), Death (41-50)
    """

    phase_id: str  # Unique ID: "{phase}_{innings}" (e.g., "powerplay_1")
    label: str  # Display label: "Powerplay", "Middle Overs", "Death Overs"
    innings: int  # 1 or 2
    team: str  # Batting team name
    over_range: tuple[float, float]  # Start and end overs (e.g., (0.1, 6.0))
    runs: int  # Total runs scored in this phase
    wickets: int  # Wickets lost in this phase
    balls: int  # Legal deliveries bowled
    run_rate: float  # Runs per over for this phase
    boundaries_4: int  # Number of fours hit
    boundaries_6: int  # Number of sixes hit
    dot_balls: int  # Balls with zero runs (excluding wickets)
    extras: int  # Wides, no-balls, byes, leg-byes
    notable_events: list[PhaseEvent]  # Key moments (wickets, big hits)


class PlayerPerformance(TypedDict, total=False):
    """
    Summary of a player's performance across the match.

    Includes batting, bowling, and fielding contributions plus AI-derived metrics.
    """

    player_id: str  # Unique player identifier
    player_name: str  # Display name
    team: str  # Team the player represents
    role: Literal["batter", "bowler", "all-rounder", "wicket-keeper"]

    # Batting stats (None if did not bat)
    batting: dict[str, Any] | None
    # Expected keys: runs, balls_faced, fours, sixes, strike_rate, is_out, dismissal_type

    # Bowling stats (None if did not bowl)
    bowling: dict[str, Any] | None
    # Expected keys: overs, runs_conceded, wickets, maidens, economy

    # Fielding stats (None if no fielding involvement)
    fielding: dict[str, Any] | None
    # Expected keys: catches, run_outs, stumpings

    # AI-computed impact score (0-100 scale, higher = more impactful)
    impact_score: float | None

    # AI-generated performance tags
    tags: list[str]
    # Common tags: "fifty_plus", "wicket_taker", "economical", "anchor",
    #              "impact_innings", "match_winner", "early_wickets"


class MatchCallout(TypedDict, total=False):
    """
    A high-level AI-generated insight or callout for the match.

    Used to highlight key moments, turning points, or notable performances.
    """

    id: str  # Unique callout ID
    category: str  # Category: "momentum", "player", "phase", "result"
    title: str  # Short headline (e.g., "Explosive Powerplay")
    body: str  # Detailed explanation (1-2 sentences)
    severity: Literal["info", "positive", "warning", "critical"]
    scope: str | None  # What this callout relates to (e.g., "innings_1", "player_X")


class InningsSummary(TypedDict):
    """
    High-level summary of an innings.

    Provides quick overview without detailed ball-by-ball data.
    """

    innings_number: int  # 1 or 2
    team: str  # Batting team name
    runs: int  # Total runs scored
    wickets: int  # Wickets lost
    overs: float  # Overs faced (e.g., 19.4)
    run_rate: float  # Overall run rate


class MatchContextPackage(TypedDict):
    """
    Complete match context package for AI/LLM consumption.

    This is the master data structure containing all match information.
    Designed to be comprehensive but may be large (~15-20k tokens).

    Use derived contexts for specific use cases:
    - CommentaryContext: Live commentary (<3k tokens)
    - CaseStudyContext: Deep analysis (~8k tokens)
    - PlayerProfileContext: Player focus (~1k tokens)
    """

    # -------------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------------
    match_id: str  # Unique match identifier
    generated_at: str  # ISO timestamp of when this package was created
    format: str  # Match format: "T20", "ODI", "Test", etc.
    overs_per_side: int | None  # Max overs per innings (None for Test)
    venue: str | None  # Stadium/ground name

    # -------------------------------------------------------------------------
    # Teams
    # -------------------------------------------------------------------------
    team_a: dict[str, Any]
    # Structure: {"name": str, "players": [{"id": str, "name": str, "role": str}]}

    team_b: dict[str, Any]
    # Structure: {"name": str, "players": [{"id": str, "name": str, "role": str}]}

    # -------------------------------------------------------------------------
    # Toss & Result
    # -------------------------------------------------------------------------
    toss: dict[str, str | None]
    # Structure: {"winner": str, "decision": "bat" | "bowl"}

    result: str | None  # Match result (e.g., "Lions won by 5 wickets")
    winner: str | None  # Winning team name

    # -------------------------------------------------------------------------
    # Innings Data
    # -------------------------------------------------------------------------
    innings: list[InningsSummary]  # Summary for each innings

    # -------------------------------------------------------------------------
    # Detailed Analysis
    # -------------------------------------------------------------------------
    phase_breakdowns: list[PhaseBreakdown]  # Per-phase stats for all innings
    player_performances: list[PlayerPerformance]  # All player stats
    callouts: list[MatchCallout]  # AI-generated insights


# =============================================================================
# Commentary Context Types (Minimal - <3k tokens)
# =============================================================================


class CommentaryPlayerSlice(TypedDict):
    """
    Minimal player info for live commentary context.

    Stripped down to essential info for real-time LLM inference.
    """

    name: str  # Player display name
    team: str  # Team name
    role: str  # Playing role
    summary: str  # One-line stat summary (e.g., "45 off 30" or "2/24 in 3 ov")
    impact_score: float | None  # Optional impact rating


class CommentaryContext(TypedDict):
    """
    Minimal MCP slice optimized for live commentary LLM use.

    Target size: <3k tokens for real-time inference.

    Use case: Generating ball-by-ball or over-by-over commentary
    during a live match. Focuses on current situation, recent events,
    and key performers without full match history.
    """

    # -------------------------------------------------------------------------
    # Match Identification
    # -------------------------------------------------------------------------
    match_id: str
    format: str  # "T20", "ODI", etc.
    batting_team: str  # Currently batting team
    bowling_team: str  # Currently bowling team

    # -------------------------------------------------------------------------
    # Current Score State
    # -------------------------------------------------------------------------
    score: str  # Formatted score (e.g., "145/3 in 15.2 overs")
    run_rate: float  # Current run rate
    required_rate: float | None  # Required rate (chase only)
    target: int | None  # Target score (chase only)
    runs_needed: int | None  # Runs to win (chase only)
    balls_remaining: int | None  # Balls left (chase only)

    # -------------------------------------------------------------------------
    # Phase Context
    # -------------------------------------------------------------------------
    current_phase: str  # "powerplay", "middle", or "death"
    phase_summary: str  # Brief phase stats (e.g., "Middle: 45/2 at 6.5 RPO")

    # -------------------------------------------------------------------------
    # Recent Action (last 2 overs)
    # -------------------------------------------------------------------------
    recent_events: list[dict[str, Any]]  # Key events for immediate context

    # -------------------------------------------------------------------------
    # Key Performers
    # -------------------------------------------------------------------------
    top_performers: list[CommentaryPlayerSlice]  # Max 3 players

    # -------------------------------------------------------------------------
    # AI Summary
    # -------------------------------------------------------------------------
    situation_summary: str  # 1-2 sentence match situation


# -----------------------------------------------------------------------------
# Commentary Context Helper
# -----------------------------------------------------------------------------


def get_context_for_commentary(mcp: dict[str, Any]) -> CommentaryContext:
    """
    Extract a minimal MCP slice optimized for live commentary LLM use.

    Designed to be <3k tokens for real-time inference.

    Args:
        mcp: Full MatchContextPackage dict.

    Returns:
        CommentaryContext with minimal, focused data for commentary generation.
    """
    # Extract basic metadata
    match_id = mcp.get("match_id", "unknown")
    match_format = mcp.get("format", "T20")
    overs_per_side = mcp.get("overs_per_side") or 20

    # Get teams (strip player lists)
    team_a = mcp.get("team_a", {})
    team_b = mcp.get("team_b", {})
    team_a_name = team_a.get("name", "Team A")
    team_b_name = team_b.get("name", "Team B")

    # Get current innings info
    innings_list = mcp.get("innings", [])
    current_innings = innings_list[-1] if innings_list else None

    if current_innings:
        batting_team = current_innings.get("team", team_a_name)
        runs = current_innings.get("runs", 0)
        wickets = current_innings.get("wickets", 0)
        overs = current_innings.get("overs", 0.0)
        run_rate = current_innings.get("run_rate", 0.0)
        innings_number = current_innings.get("innings_number", 1)
    else:
        batting_team = team_a_name
        runs = 0
        wickets = 0
        overs = 0.0
        run_rate = 0.0
        innings_number = 1

    # Determine bowling team
    bowling_team = team_b_name if batting_team == team_a_name else team_a_name

    # Format score string
    score = f"{runs}/{wickets} in {overs:.1f} overs"

    # Chase context (2nd innings)
    target: int | None = None
    required_rate: float | None = None
    runs_needed: int | None = None
    balls_remaining: int | None = None

    if innings_number >= 2 and len(innings_list) >= 2:
        first_innings = innings_list[0]
        target = first_innings.get("runs", 0) + 1
        runs_needed = target - runs
        overs_remaining = overs_per_side - overs
        balls_remaining = int(overs_remaining * 6)
        if overs_remaining > 0:
            required_rate = round(runs_needed / overs_remaining, 2)

    # Determine current phase from overs
    current_over = int(overs)
    if overs_per_side <= 20:
        if current_over < 6:
            current_phase = "powerplay"
        elif current_over < 15:
            current_phase = "middle"
        else:
            current_phase = "death"
    else:
        if current_over < 10:
            current_phase = "powerplay"
        elif current_over < 40:
            current_phase = "middle"
        else:
            current_phase = "death"

    # Get phase breakdown for current phase and innings
    phase_breakdowns = mcp.get("phase_breakdowns", [])
    current_phase_data = None
    for pb in phase_breakdowns:
        if pb.get("innings") == innings_number and pb.get("phase_id", "").startswith(current_phase):
            current_phase_data = pb
            break

    if current_phase_data:
        phase_summary = (
            f"{current_phase_data.get('label', current_phase.title())}: "
            f"{current_phase_data.get('runs', 0)}/{current_phase_data.get('wickets', 0)} "
            f"at {current_phase_data.get('run_rate', 0):.1f} RPO"
        )
    else:
        phase_summary = f"{current_phase.title()} overs in progress"

    # Extract recent events (last 2 overs) from phase breakdowns
    recent_events: list[dict[str, Any]] = []
    min_over = max(0, overs - 2.0)

    for pb in phase_breakdowns:
        if pb.get("innings") != innings_number:
            continue
        for event in pb.get("notable_events", []):
            event_over = event.get("over", 0)
            if event_over >= min_over:
                recent_events.append(
                    {
                        "over": event_over,
                        "type": event.get("event_type", "unknown"),
                        "description": event.get("description", ""),
                    }
                )

    # Sort by over (descending) and limit to 6 events
    recent_events.sort(key=lambda e: e.get("over", 0), reverse=True)
    recent_events = recent_events[:6]

    # Get top 3 performers (by impact score)
    player_performances = mcp.get("player_performances", [])
    top_performers: list[CommentaryPlayerSlice] = []

    for player in player_performances[:3]:  # Already sorted by impact
        name = player.get("player_name", "Unknown")
        team = player.get("team", "")
        role = player.get("role", "batter")
        impact = player.get("impact_score")

        # Build summary string
        batting = player.get("batting")
        bowling = player.get("bowling")
        summary_parts = []

        if batting and batting.get("runs", 0) > 0:
            sr = batting.get("strike_rate", 0)
            summary_parts.append(
                f"{batting['runs']} off {batting.get('balls_faced', 0)} (SR {sr:.0f})"
            )

        if bowling and bowling.get("wickets", 0) > 0:
            summary_parts.append(
                f"{bowling['wickets']}/{bowling.get('runs_conceded', 0)} "
                f"in {bowling.get('overs', 0)} ov"
            )

        summary = " | ".join(summary_parts) if summary_parts else "Yet to make impact"

        top_performers.append(
            CommentaryPlayerSlice(
                name=name,
                team=team,
                role=role,
                summary=summary,
                impact_score=impact,
            )
        )

    # Generate situation summary
    situation_summary = _generate_situation_summary(
        innings_number=innings_number,
        batting_team=batting_team,
        runs=runs,
        wickets=wickets,
        overs=overs,
        overs_per_side=overs_per_side,
        target=target,
        runs_needed=runs_needed,
        required_rate=required_rate,
        current_phase=current_phase,
        recent_events=recent_events,
    )

    return CommentaryContext(
        match_id=match_id,
        format=match_format,
        batting_team=batting_team,
        bowling_team=bowling_team,
        score=score,
        run_rate=round(run_rate, 2),
        required_rate=required_rate,
        target=target,
        runs_needed=runs_needed,
        balls_remaining=balls_remaining,
        current_phase=current_phase,
        phase_summary=phase_summary,
        recent_events=recent_events,
        top_performers=top_performers,
        situation_summary=situation_summary,
    )


def _generate_situation_summary(
    innings_number: int,
    batting_team: str,
    runs: int,
    wickets: int,
    overs: float,
    overs_per_side: int,
    target: int | None,
    runs_needed: int | None,
    required_rate: float | None,
    current_phase: str,
    recent_events: list[dict[str, Any]],
) -> str:
    """Generate a 1-2 sentence match situation summary."""
    parts = []

    # Wickets in hand context
    wickets_in_hand = 10 - wickets

    if innings_number == 1:
        # First innings - building/setting target
        if wickets <= 2:
            if runs >= (overs * 8):
                parts.append(
                    f"{batting_team} building a strong total "
                    f"with {wickets_in_hand} wickets in hand."
                )
            else:
                parts.append(
                    f"{batting_team} looking to accelerate with plenty of wickets in hand."
                )
        elif wickets >= 5:
            parts.append(f"{batting_team} in a spot of bother at {runs}/{wickets}.")
        else:
            parts.append(f"{batting_team} steady at {runs}/{wickets} in the {current_phase}.")
    else:
        # Chase scenario
        if target and runs_needed:
            if runs_needed <= 0:
                parts.append(f"{batting_team} have won the match!")
            elif wickets >= 8:
                parts.append(
                    f"{batting_team} hanging on, needing {runs_needed} "
                    f"with just {wickets_in_hand} wickets left."
                )
            elif required_rate and required_rate > 12:
                parts.append(
                    f"Tough ask for {batting_team} - need {runs_needed} at {required_rate:.1f} RPO."
                )
            elif required_rate and required_rate < 6:
                parts.append(
                    f"{batting_team} cruising, need just {runs_needed} at {required_rate:.1f} RPO."
                )
            else:
                parts.append(f"{batting_team} need {runs_needed} to win from here.")

    # Add recent event context
    recent_wickets = sum(1 for e in recent_events if e.get("type") == "wicket")
    recent_boundaries = sum(
        1 for e in recent_events if e.get("type") in ("boundary_4", "boundary_6")
    )

    if recent_wickets >= 2:
        parts.append("Wickets tumbling in recent overs.")
    elif recent_boundaries >= 3:
        parts.append("Boundaries flowing in the last couple of overs.")

    return " ".join(parts) if parts else f"{batting_team} at {runs}/{wickets}."


# =============================================================================
# Case Study Context Types (Deep Analysis - ~8k tokens)
# =============================================================================


class CaseStudyPhaseSummary(TypedDict):
    """
    Phase data with plain-language narrative for case study analysis.

    Includes statistical data plus AI-generated narrative explaining
    what happened in this phase and why it mattered.
    """

    phase_id: str  # Unique ID: "{phase}_{innings}"
    label: str  # Display label: "Powerplay", "Middle Overs", "Death Overs"
    innings: int  # 1 or 2
    team: str  # Batting team name
    over_range: tuple[float, float]  # Start and end overs
    runs: int  # Runs scored
    wickets: int  # Wickets lost
    run_rate: float  # Phase run rate
    boundaries: int  # Total 4s + 6s combined
    dot_ball_percentage: float  # Percentage of dot balls
    impact_events: list[dict[str, Any]]  # Key moments only (wickets, sixes)
    narrative: str  # 1-3 sentence plain-language summary


class CaseStudyPlayerSummary(TypedDict):
    """
    Player summary with narrative for case study analysis.

    Includes compact stats plus AI-generated narrative explaining
    the player's contribution and impact on the match.
    """

    player_id: str  # Unique player identifier
    player_name: str  # Display name
    team: str  # Team name
    role: str  # Playing role

    # Compact batting stats (None if did not bat)
    batting: dict[str, Any] | None
    # Keys: runs, balls, sr, 4s, 6s, out

    # Compact bowling stats (None if did not bowl)
    bowling: dict[str, Any] | None
    # Keys: overs, runs, wickets, econ

    impact_score: float | None  # 0-100 impact score
    impact_rating: str  # "high" (40+), "medium" (20-40), "low" (<20)
    tags: list[str]  # Performance tags
    narrative: str  # Plain-language contribution summary


class CaseStudyContext(TypedDict):
    """
    Comprehensive match context for deep case study analysis.

    Target size: ~8k tokens for detailed LLM analysis.

    Use case: Post-match analysis, tactical breakdowns, coaching insights,
    and generating detailed match reports. Includes narratives and
    analytical context not present in the raw MCP.
    """

    # -------------------------------------------------------------------------
    # Match Identification
    # -------------------------------------------------------------------------
    match_id: str
    format: str  # "T20", "ODI", etc.
    venue: str | None  # Stadium name
    overs_per_side: int | None  # Max overs

    # -------------------------------------------------------------------------
    # Teams (names only - no full rosters to save tokens)
    # -------------------------------------------------------------------------
    team_a: str  # Team A name
    team_b: str  # Team B name
    toss_winner: str | None  # Who won the toss
    toss_decision: str | None  # "bat" or "bowl"

    # -------------------------------------------------------------------------
    # Result
    # -------------------------------------------------------------------------
    result: str | None  # Full result string (e.g., "Lions won by 5 wickets")
    winner: str | None  # Winning team name
    margin: str | None  # Victory margin (e.g., "5 wickets", "20 runs")

    # -------------------------------------------------------------------------
    # Innings Data
    # -------------------------------------------------------------------------
    innings: list[dict[str, Any]]  # Compact innings summaries

    # -------------------------------------------------------------------------
    # Phase Analysis (with narratives)
    # -------------------------------------------------------------------------
    phases: list[CaseStudyPhaseSummary]  # All phases with AI narratives

    # -------------------------------------------------------------------------
    # Player Analysis (with narratives)
    # -------------------------------------------------------------------------
    players: list[CaseStudyPlayerSummary]  # All players with AI narratives

    # -------------------------------------------------------------------------
    # AI Insights
    # -------------------------------------------------------------------------
    callouts: list[dict[str, Any]]  # Key match insights
    match_tags: list[str]  # High-level tags (e.g., "close_finish", "collapse")
    match_narrative: str  # Overall 2-3 sentence match summary


# -----------------------------------------------------------------------------
# Case Study Context Helpers
# -----------------------------------------------------------------------------


def summarize_phase_for_case_study(phase_data: dict[str, Any]) -> str:
    """
    Generate a plain-language phase summary from stats.

    Args:
        phase_data: A PhaseBreakdown dict or similar phase stats.

    Returns:
        A 1-3 sentence narrative summary of the phase.
    """
    label = phase_data.get("label", "Phase")
    team = phase_data.get("team", "The batting side")
    runs = phase_data.get("runs", 0)
    wickets = phase_data.get("wickets", 0)
    run_rate = phase_data.get("run_rate", 0.0)
    balls = phase_data.get("balls", 0)
    boundaries_4 = phase_data.get("boundaries_4", 0)
    boundaries_6 = phase_data.get("boundaries_6", 0)
    dot_balls = phase_data.get("dot_balls", 0)
    over_range = phase_data.get("over_range", (0, 0))

    total_boundaries = boundaries_4 + boundaries_6
    dot_pct = (dot_balls / balls * 100) if balls > 0 else 0

    parts = []

    # Opening statement
    if "powerplay" in label.lower():
        if run_rate >= 9:
            parts.append(
                f"{team} dominated the powerplay, racing to {runs}/{wickets} "
                f"at {run_rate:.1f} runs per over."
            )
        elif run_rate >= 7:
            parts.append(
                f"{team} had a solid powerplay, scoring {runs}/{wickets} at {run_rate:.1f} RPO."
            )
        elif wickets >= 3:
            parts.append(
                f"{team} struggled in the powerplay, losing {wickets} early wickets "
                f"while managing just {runs} runs."
            )
        else:
            parts.append(
                f"{team} scored {runs}/{wickets} in the powerplay at a run rate of {run_rate:.1f}."
            )
    elif "middle" in label.lower():
        if wickets >= 3:
            parts.append(
                f"The middle overs saw {team} lose {wickets} wickets "
                f"while accumulating {runs} runs."
            )
        elif run_rate >= 7:
            parts.append(
                f"{team} kept the momentum going through the middle overs "
                f"with {runs} runs at {run_rate:.1f} RPO."
            )
        else:
            parts.append(f"{team} consolidated during the middle overs, scoring {runs}/{wickets}.")
    elif "death" in label.lower():
        if run_rate >= 10:
            parts.append(
                f"{team} finished strong at the death, blasting {runs} runs "
                f"in the final overs at {run_rate:.1f} RPO."
            )
        elif wickets >= 3:
            parts.append(
                f"The death overs proved costly for {team}, who lost {wickets} wickets "
                f"while adding {runs} runs."
            )
        else:
            parts.append(
                f"{team} scored {runs}/{wickets} in the death overs "
                f"at {run_rate:.1f} runs per over."
            )
    else:
        parts.append(
            f"In overs {over_range[0]:.0f}-{over_range[1]:.0f}, {team} scored "
            f"{runs}/{wickets} at {run_rate:.1f} RPO."
        )

    # Boundary context
    if boundaries_6 >= 3:
        parts.append(f"Power hitting was on display with {boundaries_6} sixes.")
    elif total_boundaries >= 6:
        parts.append(
            f"The phase featured {total_boundaries} boundaries "
            f"({boundaries_4} fours, {boundaries_6} sixes)."
        )

    # Dot ball pressure
    if dot_pct >= 40:
        parts.append(f"Bowlers maintained pressure with {dot_pct:.0f}% dot balls.")

    return " ".join(parts)


def _summarize_player_for_case_study(player: dict[str, Any]) -> str:
    """Generate a plain-language contribution summary for a player."""
    name = player.get("player_name", "Player")
    role = player.get("role", "player")
    batting = player.get("batting")
    bowling = player.get("bowling")
    tags = player.get("tags", [])

    parts = []

    # Batting contribution
    if batting:
        runs = batting.get("runs", 0)
        balls = batting.get("balls_faced", 0)
        sr = batting.get("strike_rate", 0)
        sixes = batting.get("sixes", 0)

        if runs >= 50:
            parts.append(
                f"{name} anchored the innings with a crucial {runs} off {balls} balls "
                f"(SR {sr:.0f})."
            )
        elif runs >= 30 and sr >= 150:
            parts.append(
                f"{name} played an impactful cameo of {runs} off {balls} "
                f"at a strike rate of {sr:.0f}."
            )
        elif runs >= 20:
            parts.append(f"{name} contributed {runs} runs off {balls} balls.")

        if sixes >= 3:
            parts.append(f"Hit {sixes} sixes in a power-packed display.")

    # Bowling contribution
    if bowling:
        wickets = bowling.get("wickets", 0)
        runs_conceded = bowling.get("runs_conceded", 0)
        overs = bowling.get("overs", 0)
        economy = bowling.get("economy", 0)

        if wickets >= 3:
            parts.append(
                f"{name} was the pick of the bowlers with figures of "
                f"{wickets}/{runs_conceded} in {overs} overs."
            )
        elif wickets >= 2 and economy <= 6:
            parts.append(
                f"{name} bowled economically, taking {wickets}/{runs_conceded} "
                f"at {economy:.1f} RPO."
            )
        elif wickets >= 1:
            parts.append(
                f"{name} chipped in with {wickets} wicket(s), conceding {runs_conceded} runs."
            )

    # Tag-based insights
    if "collapse_trigger" in tags:
        parts.append("Triggered a collapse with quick wickets.")
    if "death_overs_anchor" in tags and not parts:
        parts.append(f"{name} was crucial at the death.")
    if "early_wickets" in tags:
        parts.append("Made early inroads with the new ball.")

    if not parts:
        if role == "batter":
            parts.append(f"{name} did not make a significant impact with the bat.")
        elif role == "bowler":
            parts.append(f"{name} went wicketless in this match.")
        else:
            parts.append(f"{name} had a quiet game.")

    return " ".join(parts)


def _derive_impact_rating(impact_score: float | None) -> str:
    """Convert numeric impact score to rating."""
    if impact_score is None:
        return "low"
    if impact_score >= 40:
        return "high"
    if impact_score >= 20:
        return "medium"
    return "low"


def _generate_match_narrative(
    mcp: dict[str, Any],
    phases: list[CaseStudyPhaseSummary],
    players: list[CaseStudyPlayerSummary],
) -> str:
    """Generate an overall match narrative for case study."""
    team_a = (
        mcp.get("team_a", {}).get("name", "Team A")
        if isinstance(mcp.get("team_a"), dict)
        else mcp.get("team_a", "Team A")
    )
    team_b = (
        mcp.get("team_b", {}).get("name", "Team B")
        if isinstance(mcp.get("team_b"), dict)
        else mcp.get("team_b", "Team B")
    )
    result = mcp.get("result")
    match_format = mcp.get("format", "T20")

    innings_list = mcp.get("innings", [])
    parts = []

    # Opening
    parts.append(f"In this {match_format} encounter between {team_a} and {team_b},")

    # Innings summary
    if len(innings_list) >= 1:
        inn1 = innings_list[0]
        parts.append(
            f"{inn1.get('team', team_a)} batted first and posted "
            f"{inn1.get('runs', 0)}/{inn1.get('wickets', 0)} in {inn1.get('overs', 0)} overs."
        )

    if len(innings_list) >= 2:
        inn2 = innings_list[1]
        parts.append(
            f"{inn2.get('team', team_b)} responded with "
            f"{inn2.get('runs', 0)}/{inn2.get('wickets', 0)}."
        )

    # Key performers
    high_impact = [p for p in players if p.get("impact_rating") == "high"]
    if high_impact:
        names = [p["player_name"] for p in high_impact[:2]]
        parts.append(f"Key performances came from {' and '.join(names)}.")

    # Result
    if result:
        parts.append(result)

    return " ".join(parts)


def _extract_match_tags(mcp: dict[str, Any], phases: list[CaseStudyPhaseSummary]) -> list[str]:
    """Extract high-level match tags for categorization."""
    tags = []
    innings_list = mcp.get("innings", [])
    callouts = mcp.get("callouts", [])

    # Check for high-scoring match
    total_runs = sum(inn.get("runs", 0) for inn in innings_list)
    if total_runs >= 350:
        tags.append("high_scoring")
    elif total_runs <= 200 and len(innings_list) >= 2:
        tags.append("low_scoring")

    # Check for close finish
    if len(innings_list) >= 2:
        diff = abs(innings_list[0].get("runs", 0) - innings_list[1].get("runs", 0))
        if diff <= 10:
            tags.append("close_finish")
        if diff >= 50:
            tags.append("dominant_victory")

    # Check callouts for patterns
    for callout in callouts:
        title = callout.get("title", "").lower()
        if "collapse" in title:
            tags.append("collapse")
        if "explosive" in title or "surge" in title:
            tags.append("explosive_batting")

    # Phase-based tags
    for phase in phases:
        if phase.get("wickets", 0) >= 4:
            tags.append("bowling_phase_dominance")
            break
        if phase.get("run_rate", 0) >= 12:
            tags.append("explosive_phase")
            break

    return list(set(tags))  # Deduplicate


def get_context_for_case_study(mcp: dict[str, Any]) -> CaseStudyContext:
    """
    Extract full context from MCP for deep case study analysis.

    Designed to be comprehensive but still <8k tokens for LLM analysis.

    Args:
        mcp: Full MatchContextPackage dict.

    Returns:
        CaseStudyContext with all innings, phases, players, and callouts.
    """
    # Extract metadata
    match_id = mcp.get("match_id", "unknown")
    match_format = mcp.get("format", "T20")
    venue = mcp.get("venue")
    overs_per_side = mcp.get("overs_per_side")

    # Teams (names only)
    team_a_data = mcp.get("team_a", {})
    team_b_data = mcp.get("team_b", {})
    team_a = (
        team_a_data.get("name", "Team A") if isinstance(team_a_data, dict) else str(team_a_data)
    )
    team_b = (
        team_b_data.get("name", "Team B") if isinstance(team_b_data, dict) else str(team_b_data)
    )

    # Toss
    toss_data = mcp.get("toss", {})
    toss_winner = toss_data.get("winner") if isinstance(toss_data, dict) else None
    toss_decision = toss_data.get("decision") if isinstance(toss_data, dict) else None

    # Result
    result = mcp.get("result")
    winner = mcp.get("winner")

    # Derive margin from result string
    margin: str | None = None
    if result and " by " in result.lower():
        # Extract margin like "by 5 wickets" or "by 20 runs"
        margin = result.split(" by ")[-1].strip()

    # Innings summaries (keep all)
    innings_list = mcp.get("innings", [])
    innings_summaries = [
        {
            "innings_number": inn.get("innings_number", i + 1),
            "team": inn.get("team", ""),
            "runs": inn.get("runs", 0),
            "wickets": inn.get("wickets", 0),
            "overs": inn.get("overs", 0),
            "run_rate": round(inn.get("run_rate", 0), 2),
        }
        for i, inn in enumerate(innings_list)
    ]

    # Process phases with narratives
    phase_breakdowns = mcp.get("phase_breakdowns", [])
    phases: list[CaseStudyPhaseSummary] = []

    for pb in phase_breakdowns:
        balls = pb.get("balls", 0)
        dot_balls = pb.get("dot_balls", 0)
        dot_pct = (dot_balls / balls * 100) if balls > 0 else 0

        # Extract key impact events only (wickets and sixes)
        notable = pb.get("notable_events", [])
        impact_events = [
            {"over": e.get("over"), "type": e.get("event_type"), "desc": e.get("description")}
            for e in notable
            if e.get("event_type") in ("wicket", "boundary_6")
        ][:5]  # Limit to 5 key events per phase

        narrative = summarize_phase_for_case_study(pb)

        phases.append(
            CaseStudyPhaseSummary(
                phase_id=pb.get("phase_id", ""),
                label=pb.get("label", ""),
                innings=pb.get("innings", 1),
                team=pb.get("team", ""),
                over_range=pb.get("over_range", (0, 0)),
                runs=pb.get("runs", 0),
                wickets=pb.get("wickets", 0),
                run_rate=round(pb.get("run_rate", 0), 2),
                boundaries=pb.get("boundaries_4", 0) + pb.get("boundaries_6", 0),
                dot_ball_percentage=round(dot_pct, 1),
                impact_events=impact_events,
                narrative=narrative,
            )
        )

    # Process players with narratives
    player_performances = mcp.get("player_performances", [])
    players: list[CaseStudyPlayerSummary] = []

    for player in player_performances:
        impact_score = player.get("impact_score")
        impact_rating = _derive_impact_rating(impact_score)
        narrative = _summarize_player_for_case_study(player)

        # Compact batting/bowling - only key stats
        batting = player.get("batting")
        bowling = player.get("bowling")

        compact_batting = None
        if batting:
            compact_batting = {
                "runs": batting.get("runs", 0),
                "balls": batting.get("balls_faced", 0),
                "sr": round(batting.get("strike_rate", 0), 1),
                "4s": batting.get("fours", 0),
                "6s": batting.get("sixes", 0),
                "out": batting.get("is_out", False),
            }

        compact_bowling = None
        if bowling:
            compact_bowling = {
                "overs": bowling.get("overs", 0),
                "runs": bowling.get("runs_conceded", 0),
                "wickets": bowling.get("wickets", 0),
                "econ": round(bowling.get("economy", 0), 2),
            }

        players.append(
            CaseStudyPlayerSummary(
                player_id=player.get("player_id", ""),
                player_name=player.get("player_name", "Unknown"),
                team=player.get("team", ""),
                role=player.get("role", "player"),
                batting=compact_batting,
                bowling=compact_bowling,
                impact_score=round(impact_score, 1) if impact_score else None,
                impact_rating=impact_rating,
                tags=player.get("tags", []),
                narrative=narrative,
            )
        )

    # Callouts (compact format)
    raw_callouts = mcp.get("callouts", [])
    callouts = [
        {
            "id": c.get("id", ""),
            "category": c.get("category", ""),
            "title": c.get("title", ""),
            "body": c.get("body", ""),
            "severity": c.get("severity", "info"),
        }
        for c in raw_callouts
    ]

    # Generate match-level tags
    match_tags = _extract_match_tags(mcp, phases)

    # Generate overall match narrative
    match_narrative = _generate_match_narrative(mcp, phases, players)

    return CaseStudyContext(
        match_id=match_id,
        format=match_format,
        venue=venue,
        overs_per_side=overs_per_side,
        team_a=team_a,
        team_b=team_b,
        toss_winner=toss_winner,
        toss_decision=toss_decision,
        result=result,
        winner=winner,
        margin=margin,
        innings=innings_summaries,
        phases=phases,
        players=players,
        callouts=callouts,
        match_tags=match_tags,
        match_narrative=match_narrative,
    )


# =============================================================================
# Player Profile Context Types (Single Player - ~1k tokens)
# =============================================================================


class PlayerProfileContext(TypedDict):
    """
    Single player's performance context for AI summary generation.

    Target size: ~1k tokens for focused player analysis.

    Use case: Player profile pages, individual performance summaries,
    career stat integration, and player-focused AI commentary.
    Includes match context to situate the performance.
    """

    # -------------------------------------------------------------------------
    # Player Identification
    # -------------------------------------------------------------------------
    player_id: str  # Unique player identifier
    player_name: str  # Display name
    team: str  # Team the player played for
    role: str  # Playing role: "batter", "bowler", "all-rounder", "wicket-keeper"

    # -------------------------------------------------------------------------
    # Match Context
    # -------------------------------------------------------------------------
    match_id: str  # Match identifier
    match_format: str  # "T20", "ODI", etc.
    opponent: str  # Opposition team name
    venue: str | None  # Stadium name
    result: str | None  # Full result string
    match_result_for_team: str | None  # "won", "lost", "tied", "no result"

    # -------------------------------------------------------------------------
    # Batting Performance (None if did not bat)
    # -------------------------------------------------------------------------
    batting: dict[str, Any] | None
    # Keys: runs, balls_faced, fours, sixes, strike_rate, is_out, dismissal

    # -------------------------------------------------------------------------
    # Bowling Performance (None if did not bowl)
    # -------------------------------------------------------------------------
    bowling: dict[str, Any] | None
    # Keys: overs, balls_bowled, runs_conceded, wickets, maidens, economy

    # -------------------------------------------------------------------------
    # Fielding Contributions (None if no fielding involvement)
    # -------------------------------------------------------------------------
    fielding: dict[str, Any] | None
    # Keys: catches, run_outs, stumpings

    # -------------------------------------------------------------------------
    # Impact Assessment
    # -------------------------------------------------------------------------
    impact_score: float | None  # 0-100 scale, higher = more impactful
    impact_rating: str  # "high" (40+), "medium" (20-40), "low" (<20)
    tags: list[str]  # AI-generated tags (e.g., "anchor", "economical", "match_winner")

    # -------------------------------------------------------------------------
    # AI-Generated Content
    # -------------------------------------------------------------------------
    performance_narrative: str  # 1-2 sentence performance summary
    headline_stat: str  # Short stat display (e.g., "72* (48)" or "3/28 (4 ov)")


def get_context_for_player_profile(
    mcp: dict[str, Any],
    player_id: str,
) -> PlayerProfileContext | None:
    """
    Extract a specific player's performance from the MCP for AI summary.

    Args:
        mcp: Full MatchContextPackage dict.
        player_id: The ID of the player to extract.

    Returns:
        PlayerProfileContext for the player, or None if player not found.
    """
    # Find player in player_performances
    player_performances = mcp.get("player_performances", [])
    player_data: dict[str, Any] | None = None

    for p in player_performances:
        if p.get("player_id") == player_id:
            player_data = p
            break

    # Fallback: search in team rosters if not in performances
    if player_data is None:
        player_data = _find_player_in_teams(mcp, player_id)

    if player_data is None:
        return None

    # Extract player info
    player_name = player_data.get("player_name", "Unknown Player")
    team = player_data.get("team", "")
    role = player_data.get("role", "player")

    # Extract match context
    match_id = mcp.get("match_id", "unknown")
    match_format = mcp.get("format", "T20")
    venue = mcp.get("venue")
    result = mcp.get("result")

    # Determine opponent
    team_a = mcp.get("team_a", {})
    team_b = mcp.get("team_b", {})
    team_a_name = team_a.get("name", "Team A") if isinstance(team_a, dict) else str(team_a)
    team_b_name = team_b.get("name", "Team B") if isinstance(team_b, dict) else str(team_b)

    if team.lower() == team_a_name.lower():
        opponent = team_b_name
    elif team.lower() == team_b_name.lower():
        opponent = team_a_name
    else:
        opponent = team_b_name if team_a_name else team_a_name

    # Determine match result for player's team
    match_result_for_team = _determine_result_for_team(result, team)

    # Extract batting stats
    batting = player_data.get("batting")
    if batting:
        batting = _normalize_batting_stats(batting)

    # Extract bowling stats
    bowling = player_data.get("bowling")
    if bowling:
        bowling = _normalize_bowling_stats(bowling)

    # Extract fielding stats
    fielding = player_data.get("fielding")
    if fielding:
        fielding = _normalize_fielding_stats(fielding)

    # Impact score and rating
    impact_score = player_data.get("impact_score")
    impact_rating = _derive_impact_rating(impact_score)

    # Tags
    tags = player_data.get("tags", [])

    # Generate performance narrative
    performance_narrative = _generate_player_narrative(
        player_name=player_name,
        team=team,
        opponent=opponent,
        batting=batting,
        bowling=bowling,
        fielding=fielding,
        tags=tags,
        result=match_result_for_team,
    )

    # Generate headline stat
    headline_stat = _generate_headline_stat(batting, bowling)

    return PlayerProfileContext(
        player_id=player_id,
        player_name=player_name,
        team=team,
        role=role,
        match_id=match_id,
        match_format=match_format,
        opponent=opponent,
        venue=venue,
        result=result,
        match_result_for_team=match_result_for_team,
        batting=batting,
        bowling=bowling,
        fielding=fielding,
        impact_score=round(impact_score, 1) if impact_score else None,
        impact_rating=impact_rating,
        tags=tags,
        performance_narrative=performance_narrative,
        headline_stat=headline_stat,
    )


def _find_player_in_teams(mcp: dict[str, Any], player_id: str) -> dict[str, Any] | None:
    """Search for player in team rosters when not in player_performances."""
    for team_key in ["team_a", "team_b"]:
        team_data = mcp.get(team_key, {})
        if not isinstance(team_data, dict):
            continue

        team_name = team_data.get("name", "")
        players = team_data.get("players", [])

        for player in players:
            if player.get("id") == player_id:
                # Return a minimal player data dict
                return {
                    "player_id": player_id,
                    "player_name": player.get("name", "Unknown"),
                    "team": team_name,
                    "role": player.get("role", "player"),
                    "batting": None,
                    "bowling": None,
                    "impact_score": None,
                    "tags": [],
                }

    return None


def _determine_result_for_team(result: str | None, team: str) -> str | None:
    """Determine if the team won, lost, or tied based on result string."""
    if not result:
        return None

    result_lower = result.lower()

    if "no result" in result_lower or "abandoned" in result_lower:
        return "no result"
    if "tied" in result_lower or "tie" in result_lower:
        return "tied"

    # Check if team name appears before "won"
    if team.lower() in result_lower and "won" in result_lower:
        # Check if team name is the winner
        won_idx = result_lower.find("won")
        team_idx = result_lower.find(team.lower())
        if team_idx < won_idx:
            return "won"

    # If another team won, this team lost
    if "won" in result_lower:
        return "lost"

    return None


def _normalize_batting_stats(batting: dict[str, Any]) -> dict[str, Any]:
    """Normalize batting stats to a consistent format."""
    runs = batting.get("runs", 0)
    balls = batting.get("balls_faced", batting.get("balls", 0))
    fours = batting.get("fours", batting.get("4s", 0))
    sixes = batting.get("sixes", batting.get("6s", 0))
    is_out = batting.get("is_out", True)
    dismissal = batting.get("dismissal_type", batting.get("dismissal"))
    strike_rate = batting.get("strike_rate")

    if strike_rate is None and balls > 0:
        strike_rate = round((runs / balls) * 100, 2)

    return {
        "runs": runs,
        "balls_faced": balls,
        "fours": fours,
        "sixes": sixes,
        "strike_rate": round(strike_rate, 2) if strike_rate else 0.0,
        "is_out": is_out,
        "dismissal": dismissal if is_out else None,
    }


def _normalize_bowling_stats(bowling: dict[str, Any]) -> dict[str, Any]:
    """Normalize bowling stats to a consistent format."""
    overs = bowling.get("overs", 0)
    runs_conceded = bowling.get("runs_conceded", bowling.get("runs", 0))
    wickets = bowling.get("wickets", 0)
    maidens = bowling.get("maidens", 0)
    economy = bowling.get("economy")

    if economy is None and overs > 0:
        economy = round(runs_conceded / overs, 2)

    # Convert overs to balls for precision
    if isinstance(overs, float):
        whole_overs = int(overs)
        balls = whole_overs * 6 + int((overs - whole_overs) * 10)
    else:
        balls = overs * 6

    return {
        "overs": overs,
        "balls_bowled": balls,
        "runs_conceded": runs_conceded,
        "wickets": wickets,
        "maidens": maidens,
        "economy": round(economy, 2) if economy else 0.0,
    }


def _normalize_fielding_stats(fielding: dict[str, Any]) -> dict[str, Any]:
    """Normalize fielding stats to a consistent format."""
    return {
        "catches": fielding.get("catches", 0),
        "run_outs": fielding.get("run_outs", fielding.get("runouts", 0)),
        "stumpings": fielding.get("stumpings", 0),
    }


def _generate_player_narrative(
    player_name: str,
    team: str,
    opponent: str,
    batting: dict[str, Any] | None,
    bowling: dict[str, Any] | None,
    fielding: dict[str, Any] | None,
    tags: list[str],
    result: str | None,
) -> str:
    """Generate a 1-2 sentence narrative of the player's performance."""
    parts = []

    # Batting narrative
    if batting and batting.get("runs", 0) > 0:
        runs = batting["runs"]
        balls = batting.get("balls_faced", 0)
        sr = batting.get("strike_rate", 0)
        sixes = batting.get("sixes", 0)
        is_out = batting.get("is_out", True)

        if runs >= 50:
            not_out = " not out" if not is_out else ""
            parts.append(
                f"{player_name} played a standout innings of {runs}{not_out} "
                f"off {balls} balls (SR {sr:.0f})."
            )
        elif runs >= 30 and sr >= 150:
            parts.append(
                f"{player_name} contributed a quick-fire {runs} off {balls} balls "
                f"at a strike rate of {sr:.0f}."
            )
        elif runs >= 20:
            parts.append(f"{player_name} scored a useful {runs} runs off {balls} balls.")

        if sixes >= 3 and not any("six" in p.lower() for p in parts):
            parts.append(f"Hit {sixes} sixes in a power-packed display.")

    # Bowling narrative
    if bowling and (bowling.get("wickets", 0) > 0 or bowling.get("overs", 0) > 0):
        wickets = bowling["wickets"]
        runs_conceded = bowling.get("runs_conceded", 0)
        overs = bowling.get("overs", 0)
        economy = bowling.get("economy", 0)

        if wickets >= 3:
            parts.append(
                f"{player_name} was devastating with the ball, "
                f"taking {wickets}/{runs_conceded} in {overs} overs."
            )
        elif wickets >= 2 and economy <= 7:
            parts.append(
                f"{player_name} was economical, finishing with {wickets}/{runs_conceded} "
                f"at {economy:.1f} RPO."
            )
        elif wickets >= 1:
            parts.append(
                f"{player_name} picked up {wickets} wicket(s), conceding {runs_conceded} runs."
            )
        elif overs >= 2 and economy <= 6:
            parts.append(
                f"{player_name} bowled tightly, giving away just {runs_conceded} runs "
                f"in {overs} overs."
            )

    # Fielding narrative
    if fielding:
        catches = fielding.get("catches", 0)
        run_outs = fielding.get("run_outs", 0)
        stumpings = fielding.get("stumpings", 0)

        if catches >= 2:
            parts.append(f"Took {catches} catches in the field.")
        elif catches == 1 and (run_outs > 0 or stumpings > 0):
            parts.append(
                "Contributed in the field with a catch and direct involvement in a dismissal."
            )

    # Tag-based additions
    if "match_winner" in tags:
        parts.append("A match-winning performance.")
    elif "anchor" in tags and not parts:
        parts.append(f"{player_name} played the anchor role for {team}.")
    elif "economical" in tags and not parts:
        parts.append(f"{player_name} was the most economical bowler.")

    # Result context
    if result == "won" and parts:
        parts.append(f"Helped {team} secure the victory against {opponent}.")

    # Fallback
    if not parts:
        return (
            f"{player_name} played for {team} against {opponent} "
            f"but had limited impact on the match."
        )

    return " ".join(parts)


def _generate_headline_stat(
    batting: dict[str, Any] | None,
    bowling: dict[str, Any] | None,
) -> str:
    """Generate a short headline stat string."""
    parts = []

    if batting and batting.get("runs", 0) > 0:
        runs = batting["runs"]
        balls = batting.get("balls_faced", 0)
        is_out = batting.get("is_out", True)
        not_out = "*" if not is_out else ""
        parts.append(f"{runs}{not_out} ({balls})")

    if bowling and bowling.get("overs", 0) > 0:
        wickets = bowling.get("wickets", 0)
        runs_conceded = bowling.get("runs_conceded", 0)
        overs = bowling.get("overs", 0)
        parts.append(f"{wickets}/{runs_conceded} ({overs} ov)")

    if not parts:
        return "Did not bat/bowl"

    return " & ".join(parts)


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def _derive_phase(over_number: int, overs_limit: int | None) -> str:
    """Derive match phase from over number."""
    if overs_limit is None or overs_limit <= 0:
        overs_limit = 20  # Default to T20

    if overs_limit <= 20:
        # T20 phases
        if over_number < 6:
            return "powerplay"
        elif over_number < 15:
            return "middle"
        else:
            return "death"
    else:
        # ODI/50-over phases
        if over_number < 10:
            return "powerplay"
        elif over_number < 40:
            return "middle"
        else:
            return "death"


def _get_phase_over_range(phase: str, overs_limit: int | None) -> tuple[float, float]:
    """Get the over range for a phase."""
    if overs_limit is None or overs_limit <= 0:
        overs_limit = 20

    if overs_limit <= 20:
        ranges = {
            "powerplay": (0.1, 6.0),
            "middle": (6.1, 15.0),
            "death": (15.1, 20.0),
        }
    else:
        ranges = {
            "powerplay": (0.1, 10.0),
            "middle": (10.1, 40.0),
            "death": (40.1, float(overs_limit)),
        }
    return ranges.get(phase, (0.1, float(overs_limit)))


def _get_phase_label(phase: str) -> str:
    """Get human-readable label for a phase."""
    labels = {
        "powerplay": "Powerplay",
        "middle": "Middle Overs",
        "death": "Death Overs",
    }
    return labels.get(phase, phase.title())


def get_phase_breakdowns(
    deliveries: list[dict[str, Any]],
    overs_limit: int | None,
    batting_team: str,
    innings_number: int = 1,
) -> list[PhaseBreakdown]:
    """
    Analyze deliveries and return per-phase breakdowns.

    Args:
        deliveries: List of delivery dicts from the match.
        overs_limit: Total overs per innings (determines phase boundaries).
        batting_team: Name of the batting team.
        innings_number: Which innings (1 or 2).

    Returns:
        List of PhaseBreakdown dicts, one per phase.
    """
    # Initialize phase accumulators
    phases_data: dict[str, dict[str, Any]] = {
        "powerplay": {
            "runs": 0,
            "wickets": 0,
            "balls": 0,
            "boundaries_4": 0,
            "boundaries_6": 0,
            "dot_balls": 0,
            "extras": 0,
            "events": [],
        },
        "middle": {
            "runs": 0,
            "wickets": 0,
            "balls": 0,
            "boundaries_4": 0,
            "boundaries_6": 0,
            "dot_balls": 0,
            "extras": 0,
            "events": [],
        },
        "death": {
            "runs": 0,
            "wickets": 0,
            "balls": 0,
            "boundaries_4": 0,
            "boundaries_6": 0,
            "dot_balls": 0,
            "extras": 0,
            "events": [],
        },
    }

    for d in deliveries:
        over_number = d.get("over_number", 0)
        ball_number = d.get("ball_number", 0)
        runs = d.get("runs_scored", 0) or d.get("runs_off_bat", 0) or 0
        extra_runs = d.get("extra_runs", 0) or 0
        is_wicket = d.get("is_wicket", False)
        extra_type = d.get("extra_type") or d.get("extra")
        striker_id = d.get("striker_id")
        dismissal_type = d.get("dismissal_type")
        dismissed_player_id = d.get("dismissed_player_id")

        phase = _derive_phase(over_number, overs_limit)
        pd = phases_data[phase]
        over_decimal = float(over_number) + (ball_number / 10)

        pd["runs"] += runs + extra_runs
        pd["balls"] += 1

        # Count extras
        if extra_type:
            pd["extras"] += extra_runs or 1

        # Dot ball
        if runs == 0 and not extra_type and not is_wicket:
            pd["dot_balls"] += 1

        # Boundaries
        if runs == 4:
            pd["boundaries_4"] += 1
            pd["events"].append(
                PhaseEvent(
                    over=over_decimal,
                    ball=ball_number,
                    event_type="boundary_4",
                    runs=4,
                    description="FOUR",
                    player_id=striker_id,
                )
            )
        elif runs == 6:
            pd["boundaries_6"] += 1
            pd["events"].append(
                PhaseEvent(
                    over=over_decimal,
                    ball=ball_number,
                    event_type="boundary_6",
                    runs=6,
                    description="SIX",
                    player_id=striker_id,
                )
            )

        # Wickets
        if is_wicket:
            pd["wickets"] += 1
            pd["events"].append(
                PhaseEvent(
                    over=over_decimal,
                    ball=ball_number,
                    event_type="wicket",
                    runs=0,
                    description=f"WICKET ({dismissal_type or 'out'})",
                    player_id=dismissed_player_id or striker_id,
                )
            )

    # Build final breakdowns
    breakdowns: list[PhaseBreakdown] = []
    for phase_key in ["powerplay", "middle", "death"]:
        pd = phases_data[phase_key]
        if pd["balls"] == 0:
            continue  # Skip phases with no data

        overs = pd["balls"] / 6
        run_rate = pd["runs"] / overs if overs > 0 else 0.0
        over_range = _get_phase_over_range(phase_key, overs_limit)

        breakdowns.append(
            PhaseBreakdown(
                phase_id=f"{phase_key}_{innings_number}",
                label=_get_phase_label(phase_key),
                innings=innings_number,
                team=batting_team,
                over_range=over_range,
                runs=pd["runs"],
                wickets=pd["wickets"],
                balls=pd["balls"],
                run_rate=round(run_rate, 2),
                boundaries_4=pd["boundaries_4"],
                boundaries_6=pd["boundaries_6"],
                dot_balls=pd["dot_balls"],
                extras=pd["extras"],
                notable_events=pd["events"][:10],  # Limit to 10 events per phase
            )
        )

    return breakdowns


def summarize_player_performance(
    player_id: str,
    player_name: str,
    team: str,
    batting_scorecard: dict[str, Any] | None,
    bowling_scorecard: dict[str, Any] | None,
    deliveries: list[dict[str, Any]],
    overs_limit: int | None,
) -> PlayerPerformance:
    """
    Generate a player performance summary with tags.

    Args:
        player_id: The player's unique ID.
        player_name: The player's display name.
        team: The team name.
        batting_scorecard: Batting stats dict (runs, balls, is_out, etc.).
        bowling_scorecard: Bowling stats dict (overs, runs, wickets, etc.).
        deliveries: Full deliveries list for context analysis.
        overs_limit: Match format for phase analysis.

    Returns:
        PlayerPerformance dict with stats and tags.
    """
    tags: list[str] = []
    role: Literal["batter", "bowler", "all-rounder", "wicket-keeper"] = "batter"

    # Batting stats
    batting: dict[str, Any] | None = None
    if batting_scorecard:
        runs = batting_scorecard.get("runs", 0)
        balls = batting_scorecard.get("balls", 0) or batting_scorecard.get("balls_faced", 0)
        is_out = batting_scorecard.get("is_out", False)
        fours = batting_scorecard.get("fours", 0)
        sixes = batting_scorecard.get("sixes", 0)
        dismissal_type = batting_scorecard.get("dismissal_type")

        strike_rate = (runs / balls * 100) if balls > 0 else 0.0

        batting = {
            "runs": runs,
            "balls_faced": balls,
            "strike_rate": round(strike_rate, 2),
            "fours": fours,
            "sixes": sixes,
            "is_out": is_out,
            "dismissal_type": dismissal_type,
        }

        # Generate batting tags
        if runs >= 50:
            tags.append("fifty_plus")
        if runs >= 30 and strike_rate >= 150:
            tags.append("impact_innings")
        if sixes >= 3:
            tags.append("power_hitter")
        if balls >= 20 and strike_rate < 100:
            tags.append("anchor")

        # Check for death overs performance
        death_runs = sum(
            d.get("runs_off_bat", 0) or d.get("runs_scored", 0) or 0
            for d in deliveries
            if d.get("striker_id") == player_id
            and _derive_phase(d.get("over_number", 0), overs_limit) == "death"
        )
        if death_runs >= 20:
            tags.append("death_overs_anchor")

    # Bowling stats
    bowling: dict[str, Any] | None = None
    if bowling_scorecard:
        overs = bowling_scorecard.get("overs", 0) or bowling_scorecard.get("overs_bowled", 0)
        runs_conceded = bowling_scorecard.get("runs", 0) or bowling_scorecard.get(
            "runs_conceded", 0
        )
        wickets = bowling_scorecard.get("wickets", 0) or bowling_scorecard.get("wickets_taken", 0)
        maidens = bowling_scorecard.get("maidens", 0)

        economy = (runs_conceded / overs) if overs > 0 else 0.0

        bowling = {
            "overs": overs,
            "runs_conceded": runs_conceded,
            "wickets": wickets,
            "maidens": maidens,
            "economy": round(economy, 2),
        }

        # Determine role
        role = "all-rounder" if batting and batting.get("runs", 0) >= 20 else "bowler"

        # Generate bowling tags
        if wickets >= 3:
            tags.append("wicket_taker")
        if wickets >= 2 and economy <= 6.0:
            tags.append("economical_spell")

        # Check for early wickets
        early_wickets = sum(
            1
            for d in deliveries
            if d.get("bowler_id") == player_id
            and d.get("is_wicket", False)
            and d.get("over_number", 99) < 6
        )
        if early_wickets >= 2:
            tags.append("early_wickets")

        # Check for collapse trigger
        wicket_overs = [
            d.get("over_number", 0)
            for d in deliveries
            if d.get("bowler_id") == player_id and d.get("is_wicket", False)
        ]
        if len(wicket_overs) >= 2:
            # Check if wickets came in quick succession
            wicket_overs.sort()
            for i in range(len(wicket_overs) - 1):
                if wicket_overs[i + 1] - wicket_overs[i] <= 2:
                    tags.append("collapse_trigger")
                    break

    # Calculate impact score (simplified)
    impact_score: float | None = None
    if batting or bowling:
        bat_impact = 0.0
        bowl_impact = 0.0

        if batting:
            runs = batting.get("runs", 0)
            sr = batting.get("strike_rate", 100)
            # Runs contribute positively, high strike rate bonus
            bat_impact = runs * 1.0 + (sr - 100) * 0.1

        if bowling:
            wickets = bowling.get("wickets", 0)
            economy = bowling.get("economy", 8.0)
            # Wickets contribute, low economy bonus
            bowl_impact = wickets * 15.0 + (8.0 - economy) * 5.0

        impact_score = round(bat_impact + bowl_impact, 1)

    return PlayerPerformance(
        player_id=player_id,
        player_name=player_name,
        team=team,
        role=role,
        batting=batting,
        bowling=bowling,
        fielding=None,  # TODO: Add fielding stats when available
        impact_score=impact_score,
        tags=tags,
    )


def generate_callouts(
    phase_breakdowns: list[PhaseBreakdown],
    player_performances: list[PlayerPerformance],
    result: str | None,
) -> list[MatchCallout]:
    """
    Generate high-level AI callouts based on match analysis.

    Args:
        phase_breakdowns: List of phase breakdowns.
        player_performances: List of player performances.
        result: Match result string.

    Returns:
        List of MatchCallout dicts.
    """
    callouts: list[MatchCallout] = []

    # Analyze phases for callouts
    for phase in phase_breakdowns:
        # High run rate in powerplay
        if phase["phase_id"].startswith("powerplay") and phase["run_rate"] >= 9.0:
            callouts.append(
                MatchCallout(
                    id=f"callout_{phase['phase_id']}_high_rr",
                    category="Batting",
                    title="Explosive Powerplay",
                    body=(
                        f"{phase['team']} scored at {phase['run_rate']} RPO "
                        f"in the powerplay with {phase['boundaries_6']} sixes."
                    ),
                    severity="positive",
                    scope=phase["label"],
                )
            )

        # Wicket cluster (3+ wickets in a phase)
        if phase["wickets"] >= 3:
            callouts.append(
                MatchCallout(
                    id=f"callout_{phase['phase_id']}_wickets",
                    category="Bowling",
                    title=f"Wickets in {phase['label']}",
                    body=(
                        f"{phase['wickets']} wickets fell in the {phase['label'].lower()}, "
                        f"creating pressure."
                    ),
                    severity="warning",
                    scope=phase["label"],
                )
            )

        # Death overs surge
        if phase["phase_id"].startswith("death") and phase["run_rate"] >= 10.0:
            callouts.append(
                MatchCallout(
                    id=f"callout_{phase['phase_id']}_surge",
                    category="Batting",
                    title="Death Overs Surge",
                    body=(
                        f"Strong finish with {phase['runs']} runs "
                        f"at {phase['run_rate']} RPO in the death."
                    ),
                    severity="positive",
                    scope=phase["label"],
                )
            )

        # Death overs struggle
        if (
            phase["phase_id"].startswith("death")
            and phase["run_rate"] < 7.0
            and phase["wickets"] >= 2
        ):
            callouts.append(
                MatchCallout(
                    id=f"callout_{phase['phase_id']}_struggle",
                    category="Batting",
                    title="Death Overs Struggle",
                    body=(
                        f"Struggled at the death with {phase['wickets']} wickets "
                        f"and only {phase['run_rate']} RPO."
                    ),
                    severity="warning",
                    scope=phase["label"],
                )
            )

    # Analyze players for callouts
    for player in player_performances:
        if "fifty_plus" in player.get("tags", []):
            callouts.append(
                MatchCallout(
                    id=f"callout_player_{player['player_id']}_fifty",
                    category="Players",
                    title="Key Innings",
                    body=(
                        f"{player['player_name']} scored a crucial half-century "
                        f"for {player['team']}."
                    ),
                    severity="positive",
                    scope=player["player_name"],
                )
            )

        if "collapse_trigger" in player.get("tags", []):
            callouts.append(
                MatchCallout(
                    id=f"callout_player_{player['player_id']}_collapse",
                    category="Bowling",
                    title="Collapse Trigger",
                    body=f"{player['player_name']} triggered a collapse with quick wickets.",
                    severity="positive",
                    scope=player["player_name"],
                )
            )

    return callouts


# -----------------------------------------------------------------------------
# Main Service Function
# -----------------------------------------------------------------------------


async def generate_match_context_package(
    match_id: str,
    db: AsyncSession,
) -> MatchContextPackage:
    """
    Generate a comprehensive match context package for AI/LLM consumption.

    Args:
        match_id: The game/match ID.
        db: Async database session.

    Returns:
        MatchContextPackage with full match context.

    Raises:
        ValueError: If the match is not found.
    """
    # Fetch the game
    result = await db.execute(select(models.Game).where(models.Game.id == match_id))
    game = result.scalar_one_or_none()

    if game is None:
        raise ValueError(f"Match {match_id} not found")

    # Extract team info
    team_a = game.team_a or {}
    team_b = game.team_b or {}
    team_a_name = team_a.get("name", "Team A")
    team_b_name = team_b.get("name", "Team B")

    # Determine format
    overs_limit = game.overs_limit
    if overs_limit and overs_limit <= 20:
        match_format = "T20"
    elif overs_limit and overs_limit <= 50:
        match_format = "ODI"
    elif overs_limit and overs_limit > 50:
        match_format = "TEST"
    else:
        match_format = "CUSTOM"

    # Get deliveries
    deliveries: list[dict[str, Any]] = game.deliveries or []

    # Determine batting team for first innings
    batting_team = game.batting_team_name or team_a_name

    # Build phase breakdowns
    phase_breakdowns = get_phase_breakdowns(
        deliveries=deliveries,
        overs_limit=overs_limit,
        batting_team=batting_team,
        innings_number=1,
    )

    # Build player performances
    player_performances: list[PlayerPerformance] = []
    batting_scorecard: dict[str, Any] = game.batting_scorecard or {}
    bowling_scorecard: dict[str, Any] = game.bowling_scorecard or {}

    # Collect all players from scorecards
    all_player_ids = set(batting_scorecard.keys()) | set(bowling_scorecard.keys())

    # Get player names from team rosters
    team_a_players = {p.get("id"): p.get("name", "Unknown") for p in team_a.get("players", [])}
    team_b_players = {p.get("id"): p.get("name", "Unknown") for p in team_b.get("players", [])}
    all_players = {**team_a_players, **team_b_players}

    for player_id in all_player_ids:
        player_name = all_players.get(player_id, f"Player {player_id[:8]}")
        team = team_a_name if player_id in team_a_players else team_b_name

        perf = summarize_player_performance(
            player_id=player_id,
            player_name=player_name,
            team=team,
            batting_scorecard=batting_scorecard.get(player_id),
            bowling_scorecard=bowling_scorecard.get(player_id),
            deliveries=deliveries,
            overs_limit=overs_limit,
        )
        player_performances.append(perf)

    # Sort by impact score
    player_performances.sort(key=lambda p: p.get("impact_score") or 0, reverse=True)

    # Generate callouts
    callouts = generate_callouts(
        phase_breakdowns=phase_breakdowns,
        player_performances=player_performances,
        result=game.result,
    )

    # Build innings summary
    innings_summaries: list[InningsSummary] = []
    total_balls = len([d for d in deliveries if d.get("extra_type") not in ["wide", "no_ball"]])
    total_overs = total_balls / 6 if total_balls else 0
    total_runs = sum(
        (d.get("runs_scored", 0) or d.get("runs_off_bat", 0) or 0) + (d.get("extra_runs", 0) or 0)
        for d in deliveries
    )
    total_wickets = sum(1 for d in deliveries if d.get("is_wicket", False))

    if deliveries:
        innings_summaries.append(
            InningsSummary(
                innings_number=1,
                team=batting_team,
                runs=total_runs,
                wickets=total_wickets,
                overs=round(total_overs, 1),
                run_rate=round(total_runs / total_overs, 2) if total_overs else 0.0,
            )
        )

    # Include second innings from first_inning_summary if available
    first_inn = game.first_inning_summary
    if first_inn:
        innings_summaries.insert(
            0,
            InningsSummary(
                innings_number=1,
                team=first_inn.get("team", team_a_name),
                runs=first_inn.get("runs", 0),
                wickets=first_inn.get("wickets", 0),
                overs=first_inn.get("overs", 0.0),
                run_rate=first_inn.get("run_rate", 0.0),
            ),
        )
        # Adjust current innings to be innings 2
        if innings_summaries and len(innings_summaries) > 1:
            innings_summaries[1]["innings_number"] = 2

    # Determine winner
    winner = game.get_winner()

    return MatchContextPackage(
        match_id=match_id,
        generated_at=datetime.now(UTC).isoformat(),
        format=match_format,
        overs_per_side=overs_limit,
        venue=None,  # TODO: Add venue when available in model
        team_a={
            "id": team_a.get("id", "team_a"),
            "name": team_a_name,
            "players": team_a.get("players", []),
        },
        team_b={
            "id": team_b.get("id", "team_b"),
            "name": team_b_name,
            "players": team_b.get("players", []),
        },
        toss={
            "winner": game.toss_winner_team,
            "decision": game.decision,
        },
        result=game.result,
        winner=winner,
        innings=innings_summaries,
        phase_breakdowns=phase_breakdowns,
        player_performances=player_performances,
        callouts=callouts,
    )
