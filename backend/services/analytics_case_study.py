"""
Service layer for building Match Case Study analytics.

This module assembles all data required for the MatchCaseStudyResponse,
including match metadata, phase breakdowns, key players, and AI summaries.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.case_study import (
    CaseStudyAIBlock,
    CaseStudyDismissalByBowlerType,
    CaseStudyDismissalByShotType,
    CaseStudyDismissalByZone,
    CaseStudyDismissalPatterns,
    CaseStudyInningsSummary,
    CaseStudyKeyPhase,
    CaseStudyKeyPlayer,
    CaseStudyMatch,
    CaseStudyMomentumSummary,
    CaseStudyPhase,
    CaseStudyPlayerBatting,
    CaseStudyPlayerBowling,
    CaseStudyPlayerFielding,
    CaseStudySwingMetric,
    MatchCaseStudyResponse,
)
from backend.sql_app.database import get_session_local
from backend.sql_app.models import Game

# -----------------------------------------------------------------------------
# Phase Definitions
# -----------------------------------------------------------------------------


def _get_phase_ranges(match_format: str, overs_per_side: int) -> list[tuple[str, str, int, int]]:
    """
    Return phase definitions based on match format.

    Returns list of (id, label, start_over, end_over).
    """
    if match_format.upper() == "T20" or overs_per_side == 20:
        return [
            ("powerplay", "Powerplay (1-6)", 1, 6),
            ("middle", "Middle Overs (7-15)", 7, 15),
            ("death", "Death Overs (16-20)", 16, 20),
        ]
    elif match_format.upper() == "ODI" or overs_per_side >= 40:
        return [
            ("powerplay", "Powerplay (1-10)", 1, 10),
            ("middle", "Middle Overs (11-40)", 11, 40),
            ("death", "Death Overs (41-50)", 41, min(overs_per_side, 50)),
        ]
    else:
        # Generic 3-part split for custom formats
        n = overs_per_side
        pp_end = max(1, n // 3)
        mid_end = max(pp_end + 1, 2 * n // 3)
        return [
            ("powerplay", f"Early Overs (1-{pp_end})", 1, pp_end),
            ("middle", f"Middle Overs ({pp_end + 1}-{mid_end})", pp_end + 1, mid_end),
            ("death", f"Late Overs ({mid_end + 1}-{n})", mid_end + 1, n),
        ]


# -----------------------------------------------------------------------------
# Per-Over Aggregation
# -----------------------------------------------------------------------------


def _aggregate_per_over(
    deliveries: list[dict[str, Any]], innings_number: int
) -> tuple[dict[int, int], dict[int, int]]:
    """
    Aggregate runs and wickets per over for a specific innings.

    Returns (per_over_runs, per_over_wickets) dicts keyed by over_number.
    """
    per_over_runs: dict[int, int] = defaultdict(int)
    per_over_wickets: dict[int, int] = defaultdict(int)

    for d in deliveries:
        inning = d.get("inning", 1)
        if inning != innings_number:
            continue

        over_num = d.get("over_number", 1)
        # Total runs for this ball
        runs = d.get("runs_off_bat", 0) + d.get("extra_runs", 0)
        # Fallback to runs_scored if breakdown not available
        if runs == 0 and d.get("runs_scored"):
            runs = d.get("runs_scored", 0)

        per_over_runs[over_num] += runs

        if d.get("is_wicket"):
            per_over_wickets[over_num] += 1

    return dict(per_over_runs), dict(per_over_wickets)


# -----------------------------------------------------------------------------
# Phase Stats Computation
# -----------------------------------------------------------------------------


def _compute_phase_stats(
    phase_ranges: list[tuple[str, str, int, int]],
    per_over_runs: dict[int, int],
    per_over_wickets: dict[int, int],
    total_runs: int,
    total_overs: float,
) -> list[CaseStudyPhase]:
    """
    Compute stats for each phase and return CaseStudyPhase objects.
    """
    # Calculate average runs per over for par calculation
    avg_rpo = total_runs / total_overs if total_overs > 0 else 6.0

    phases: list[CaseStudyPhase] = []
    for phase_id, label, start_over, end_over in phase_ranges:
        phase_runs = sum(per_over_runs.get(o, 0) for o in range(start_over, end_over + 1))
        phase_wickets = sum(per_over_wickets.get(o, 0) for o in range(start_over, end_over + 1))
        overs_in_phase = end_over - start_over + 1
        run_rate = round(phase_runs / overs_in_phase, 2) if overs_in_phase > 0 else 0.0

        # Par expectation
        expected_runs = avg_rpo * overs_in_phase
        net_swing = round(phase_runs - expected_runs)

        # Determine impact
        if net_swing > 5:
            impact: Literal["positive", "negative", "neutral"] = "positive"
            impact_label = f"+{net_swing} vs par"
        elif net_swing < -5:
            impact = "negative"
            impact_label = f"{net_swing} vs par"
        else:
            impact = "neutral"
            impact_label = "On par"

        phases.append(
            CaseStudyPhase(
                id=phase_id,  # type: ignore[arg-type]
                label=label,
                start_over=start_over,
                end_over=end_over,
                runs=phase_runs,
                wickets=phase_wickets,
                run_rate=run_rate,
                net_swing_vs_par=net_swing,
                impact=impact,
                impact_label=impact_label,
            )
        )

    return phases


# -----------------------------------------------------------------------------
# Key Phase & Momentum
# -----------------------------------------------------------------------------


def _determine_key_phase(
    phases: list[CaseStudyPhase],
) -> tuple[CaseStudyPhase, str]:
    """
    Determine the key phase (highest absolute net_swing_vs_par).

    Returns (key_phase, reason_code).
    """
    if not phases:
        # Fallback
        return phases[0] if phases else None, "unknown"  # type: ignore[return-value]

    key = max(phases, key=lambda p: abs(p.net_swing_vs_par))

    if key.impact == "positive":
        if key.id == "death":
            reason = "death_acceleration"
        elif key.id == "powerplay":
            reason = "strong_start"
        else:
            reason = "middle_consolidation"
    else:
        if key.id == "middle":
            reason = "middle_collapse"
        elif key.id == "powerplay":
            reason = "early_wickets"
        else:
            reason = "death_struggles"

    return key, reason


def _build_momentum_summary(
    key_phase: CaseStudyPhase,
    winning_team: str | None,
    total_swing: int,
) -> CaseStudyMomentumSummary:
    """Build the momentum summary based on key phase analysis."""
    phase_name = key_phase.label.split("(")[0].strip()

    if key_phase.impact == "positive":
        title = f"Strong performance in {phase_name.lower()}"
        subtitle = (
            f"Scored {key_phase.runs} runs in overs {key_phase.start_over}-{key_phase.end_over}, "
            f"{key_phase.net_swing_vs_par:+d} above par"
        )
    else:
        title = f"Struggled in {phase_name.lower()}"
        subtitle = (
            f"Only {key_phase.runs} runs with {key_phase.wickets} wickets lost, "
            f"{key_phase.net_swing_vs_par} below par"
        )

    return CaseStudyMomentumSummary(
        title=title,
        subtitle=subtitle,
        winning_side=winning_team,
        swing_metric=CaseStudySwingMetric(
            runs_above_par=total_swing,
            win_probability_shift=None,  # Would require ML model
        ),
    )


# -----------------------------------------------------------------------------
# Key Player Impact Computation
# -----------------------------------------------------------------------------


def _compute_player_stats(
    deliveries: list[dict[str, Any]],
    batting_scorecard: dict[str, Any],
    bowling_scorecard: dict[str, Any],
    team_a: dict[str, Any],
    team_b: dict[str, Any],
) -> list[CaseStudyKeyPlayer]:
    """
    Compute key player stats and impact scores.

    Returns top 5 players by impact score.
    """
    # Build player name/team lookup
    player_info: dict[str, dict[str, str]] = {}
    for team_data, team_name in [
        (team_a, team_a.get("name", "Team A")),
        (team_b, team_b.get("name", "Team B")),
    ]:
        for p in team_data.get("players", []):
            player_info[p["id"]] = {"name": p["name"], "team": team_name}

    # Aggregate batting stats
    batter_stats: dict[str, dict[str, Any]] = {}
    for pid, entry in batting_scorecard.items():
        if not isinstance(entry, dict):
            continue
        batter_stats[pid] = {
            "runs": entry.get("runs", 0),
            "balls": entry.get("balls_faced", 0),
            "fours": entry.get("fours", 0),
            "sixes": entry.get("sixes", 0),
            "is_out": entry.get("is_out", False),
        }

    # Aggregate bowling stats
    bowler_stats: dict[str, dict[str, Any]] = {}
    for pid, entry in bowling_scorecard.items():
        if not isinstance(entry, dict):
            continue
        overs = entry.get("overs_bowled", 0.0)
        runs = entry.get("runs_conceded", 0)
        wickets = entry.get("wickets_taken", 0)
        bowler_stats[pid] = {
            "overs": overs,
            "runs": runs,
            "wickets": wickets,
            "maidens": entry.get("maidens", 0),
            "economy": round(runs / overs, 2) if overs > 0 else 0.0,
        }

    # Count fielding contributions from deliveries
    fielding_stats: dict[str, dict[str, int]] = defaultdict(
        lambda: {"catches": 0, "run_outs": 0, "stumpings": 0}
    )
    for d in deliveries:
        if d.get("is_wicket") and d.get("fielder_id"):
            fielder_id = d["fielder_id"]
            dismissal = d.get("dismissal_type", "").lower()
            if "caught" in dismissal:
                fielding_stats[fielder_id]["catches"] += 1
            elif "run out" in dismissal:
                fielding_stats[fielder_id]["run_outs"] += 1
            elif "stumped" in dismissal:
                fielding_stats[fielder_id]["stumpings"] += 1

    # Compute impact scores
    impact_scores: dict[str, float] = {}
    for pid in set(list(batter_stats.keys()) + list(bowler_stats.keys())):
        score = 0.0

        # Batting impact
        if pid in batter_stats:
            bs = batter_stats[pid]
            runs = bs["runs"]
            balls = bs["balls"]
            fours = bs["fours"]
            sixes = bs["sixes"]
            # Base: runs + boundary bonus
            batting_base = runs + (fours * 2) + (sixes * 3)
            # Strike rate multiplier
            sr = (runs / balls * 100) if balls > 0 else 0
            sr_multiplier = sr / 100 if sr > 0 else 1.0
            score += batting_base * min(sr_multiplier, 2.0)

        # Bowling impact
        if pid in bowler_stats:
            bw = bowler_stats[pid]
            wickets = bw["wickets"]
            overs = bw["overs"]
            economy = bw["economy"]
            # Wickets are valuable, low economy is good
            bowling_impact = (wickets * 25) - (economy * overs * 0.5)
            score += max(0, bowling_impact)

        # Fielding impact
        if pid in fielding_stats:
            fs = fielding_stats[pid]
            score += fs["catches"] * 5 + fs["run_outs"] * 7 + fs["stumpings"] * 6

        impact_scores[pid] = round(score, 1)

    # Determine max for normalization
    max_impact = max(impact_scores.values()) if impact_scores else 1.0

    # Build key player list
    players: list[CaseStudyKeyPlayer] = []
    for pid, score in sorted(impact_scores.items(), key=lambda x: -x[1])[:5]:
        info = player_info.get(pid, {"name": "Unknown", "team": "Unknown"})

        # Determine role
        has_batting = pid in batter_stats and batter_stats[pid]["runs"] > 0
        has_bowling = pid in bowler_stats and bowler_stats[pid]["overs"] > 0
        if has_batting and has_bowling:
            role = "All-rounder"
        elif has_bowling:
            role = "Bowler"
        else:
            role = "Batter"

        # Impact level
        if score >= 0.7 * max_impact:
            impact_level: Literal["high", "medium", "low"] = "high"
        elif score >= 0.4 * max_impact:
            impact_level = "medium"
        else:
            impact_level = "low"

        # Build sub-objects
        batting = None
        if pid in batter_stats:
            bs = batter_stats[pid]
            if bs["runs"] > 0 or bs["balls"] > 0:
                batting = CaseStudyPlayerBatting(
                    innings=1,
                    runs=bs["runs"],
                    balls=bs["balls"],
                    strike_rate=round((bs["runs"] / bs["balls"] * 100), 1)
                    if bs["balls"] > 0
                    else 0.0,
                    boundaries={"fours": bs["fours"], "sixes": bs["sixes"]},
                )

        bowling = None
        if pid in bowler_stats:
            bw = bowler_stats[pid]
            if bw["overs"] > 0:
                bowling = CaseStudyPlayerBowling(
                    overs=bw["overs"],
                    maidens=bw["maidens"],
                    runs=bw["runs"],
                    wickets=bw["wickets"],
                    economy=bw["economy"],
                )

        fielding = None
        if pid in fielding_stats:
            fs = fielding_stats[pid]
            if fs["catches"] > 0 or fs["run_outs"] > 0 or fs["stumpings"] > 0:
                fielding = CaseStudyPlayerFielding(
                    catches=fs["catches"],
                    run_outs=fs["run_outs"],
                    drops=0,  # Not tracked in deliveries
                )

        # Impact label
        if batting and batting.runs >= 50:
            impact_label = f"Scored {batting.runs} off {batting.balls} balls"
        elif bowling and bowling.wickets >= 3:
            impact_label = f"{bowling.wickets}/{bowling.runs} in {bowling.overs} overs"
        elif bowling and bowling.wickets >= 1:
            impact_label = f"Took {bowling.wickets} wicket(s)"
        elif batting:
            impact_label = f"Contributed {batting.runs} runs"
        else:
            impact_label = "Key contribution"

        players.append(
            CaseStudyKeyPlayer(
                id=pid,
                name=info["name"],
                team=info["team"],
                role=role,
                batting=batting,
                bowling=bowling,
                fielding=fielding,
                impact=impact_level,
                impact_label=impact_label,
                impact_score=score,
            )
        )

    return players


# -----------------------------------------------------------------------------
# Dismissal Patterns
# -----------------------------------------------------------------------------


def _compute_dismissal_patterns(
    deliveries: list[dict[str, Any]],
) -> CaseStudyDismissalPatterns | None:
    """
    Aggregate dismissal patterns from deliveries.
    """
    wicket_deliveries = [d for d in deliveries if d.get("is_wicket")]
    if not wicket_deliveries:
        return None

    by_type: dict[str, int] = defaultdict(int)
    by_shot: dict[str, int] = defaultdict(int)
    by_zone: dict[str, int] = defaultdict(int)

    for d in wicket_deliveries:
        dismissal = d.get("dismissal_type", "Unknown")
        by_type[dismissal] += 1

        # Shot type (if available in shot_map or similar)
        shot = d.get("shot_type", "Unknown")
        if shot and shot != "Unknown":
            by_shot[shot] += 1

        # Zone (from shot_map or wagon_zone)
        zone = d.get("wagon_zone") or d.get("shot_map", "Unknown")
        if zone and zone != "Unknown":
            by_zone[zone] += 1

    # Build summary
    total_wickets = len(wicket_deliveries)
    most_common_type = max(by_type.items(), key=lambda x: x[1])[0] if by_type else None
    summary = f"{total_wickets} wickets fell in this match."
    if most_common_type:
        summary = (
            f"Most dismissals were {most_common_type.lower()} "
            f"({by_type[most_common_type]} wickets)."
        )

    return CaseStudyDismissalPatterns(
        summary=summary,
        by_bowler_type=[
            CaseStudyDismissalByBowlerType(type=k, wickets=v)
            for k, v in sorted(by_type.items(), key=lambda x: -x[1])
        ],
        by_shot_type=[
            CaseStudyDismissalByShotType(shot=k, wickets=v)
            for k, v in sorted(by_shot.items(), key=lambda x: -x[1])
        ]
        if by_shot
        else [],
        by_zone=[
            CaseStudyDismissalByZone(zone=k, wickets=v)
            for k, v in sorted(by_zone.items(), key=lambda x: -x[1])
        ]
        if by_zone
        else [],
    )


# -----------------------------------------------------------------------------
# AI Summary Generation (Baseline)
# -----------------------------------------------------------------------------


def _generate_ai_summary(
    match: CaseStudyMatch,
    phases: list[CaseStudyPhase],
    key_players: list[CaseStudyKeyPlayer],
) -> CaseStudyAIBlock:
    """
    Generate a simple baseline match summary (no external AI call).
    """
    # Build a readable summary
    parts = []

    # Match overview
    parts.append(f"In this {match.format} match between {match.teams_label}, {match.result}.")

    # First innings summary
    if match.innings:
        inn1 = match.innings[0]
        parts.append(
            f"{inn1.team} batted first, scoring {inn1.runs}/{inn1.wickets} "
            f"in {inn1.overs} overs (RR: {inn1.run_rate})."
        )

    # Key phase
    if phases:
        key = max(phases, key=lambda p: abs(p.net_swing_vs_par))
        if key.impact == "positive":
            parts.append(
                f"The {key.label.split('(')[0].strip().lower()} proved decisive "
                f"with {key.runs} runs scored at {key.run_rate} RPO."
            )
        else:
            parts.append(
                f"The {key.label.split('(')[0].strip().lower()} was challenging "
                f"with only {key.runs} runs and {key.wickets} wickets lost."
            )

    # Top performer
    if key_players:
        top = key_players[0]
        if top.batting and top.batting.runs >= 30:
            parts.append(f"{top.name} was the standout performer with {top.batting.runs} runs.")
        elif top.bowling and top.bowling.wickets >= 2:
            parts.append(f"{top.name} starred with the ball, taking {top.bowling.wickets} wickets.")

    summary = " ".join(parts)

    return CaseStudyAIBlock(
        match_summary=summary,
        generated_at=datetime.utcnow(),
        model_version="case-study-baseline-v1",
        tokens_used=None,
    )


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------


async def build_match_case_study(
    match_id: str,
    user_id: str | int,
) -> MatchCaseStudyResponse:
    """
    Build a complete case study response for a match.

    Args:
        match_id: The unique identifier for the match.
        user_id: The ID of the requesting user (for access control / personalization).

    Returns:
        MatchCaseStudyResponse with all analytics data.

    Raises:
        ValueError: If the match is not found.
    """
    # Check for mock match IDs first (for development/testing)
    if match_id == "m1":
        return _build_m1_mock_case_study()
    if match_id == "m2":
        return _build_m2_mock_case_study()

    # Load from database
    async with get_session_local()() as session:
        return await _build_case_study_from_db(session, match_id, user_id)


async def _build_case_study_from_db(
    session: AsyncSession,
    match_id: str,
    user_id: str | int,
) -> MatchCaseStudyResponse:
    """
    Build case study from actual database data.
    """
    # 1) Load match
    stmt = select(Game).where(Game.id == match_id)
    result = await session.execute(stmt)
    game = result.scalar_one_or_none()

    if game is None:
        raise ValueError("Match not found")

    # TODO: Verify user has access to this match (org/team membership check)

    # 2) Extract match metadata
    team_a = game.team_a or {}
    team_b = game.team_b or {}
    team_a_name = team_a.get("name", "Team A")
    team_b_name = team_b.get("name", "Team B")

    overs_per_side = game.overs_limit or 20
    match_format = game.match_type.upper() if game.match_type else "T20"
    if match_format not in ("T20", "ODI", "TEST"):
        match_format = "CUSTOM"

    # 3) Build innings summaries from first_inning_summary and current state
    innings_summaries: list[CaseStudyInningsSummary] = []

    # First innings (from first_inning_summary if completed)
    if game.first_inning_summary:
        fis = game.first_inning_summary
        innings_summaries.append(
            CaseStudyInningsSummary(
                team=fis.get("batting_team", team_a_name),
                runs=fis.get("runs", 0),
                wickets=fis.get("wickets", 0),
                overs=float(fis.get("overs", 0)),
                run_rate=round(fis.get("runs", 0) / max(fis.get("overs", 1), 0.1), 2),
            )
        )

    # Second innings (or current if game in progress)
    if game.current_inning >= 2 or not innings_summaries:
        overs_completed = game.overs_completed + (game.balls_this_over / 6)
        innings_summaries.append(
            CaseStudyInningsSummary(
                team=game.batting_team_name or team_b_name,
                runs=game.total_runs,
                wickets=game.total_wickets,
                overs=round(overs_completed, 1),
                run_rate=round(game.total_runs / max(overs_completed, 0.1), 2),
            )
        )

    # 4) Build CaseStudyMatch
    match_date = date.today()  # Game model doesn't have created_at exposed as date
    if hasattr(game, "created_at") and game.created_at:
        match_date = game.created_at.date()

    case_study_match = CaseStudyMatch(
        id=game.id,
        date=match_date,
        format=match_format,  # type: ignore[arg-type]
        home_team=team_a_name,
        away_team=team_b_name,
        teams_label=f"{team_a_name} vs {team_b_name}",
        venue=None,  # Not stored in Game model
        result=game.result or "In progress",
        overs_per_side=overs_per_side,
        innings=innings_summaries,
    )

    # 5) Get deliveries and compute per-over stats
    deliveries = game.deliveries or []

    # Use first innings for phase analysis
    per_over_runs, per_over_wickets = _aggregate_per_over(deliveries, 1)

    # Get first innings totals
    if game.first_inning_summary:
        fis = game.first_inning_summary
        total_runs_inn1 = fis.get("runs", 0)
        total_overs_inn1 = float(fis.get("overs", 0)) or sum(1 for _ in per_over_runs)
    else:
        total_runs_inn1 = sum(per_over_runs.values())
        total_overs_inn1 = float(len(per_over_runs)) if per_over_runs else 1.0

    # 6) Compute phase breakdown
    phase_ranges = _get_phase_ranges(match_format, overs_per_side)
    phases = _compute_phase_stats(
        phase_ranges,
        per_over_runs,
        per_over_wickets,
        total_runs_inn1,
        total_overs_inn1,
    )

    # 7) Determine key phase and momentum
    key_phase_obj, reason_code = _determine_key_phase(phases)

    key_phase = CaseStudyKeyPhase(
        title=f"{key_phase_obj.label} Analysis",
        detail=(
            f"Scored {key_phase_obj.runs} runs with {key_phase_obj.wickets} wickets lost. "
            f"Run rate: {key_phase_obj.run_rate}, {key_phase_obj.impact_label}."
        ),
        overs_range={
            "start_over": key_phase_obj.start_over,
            "end_over": key_phase_obj.end_over,
        },
        reason_codes=[reason_code],
    )

    # Total swing for momentum
    total_swing = sum(p.net_swing_vs_par for p in phases if p.impact == "positive")

    # Determine winner from result
    winning_team = None
    if game.result:
        if team_a_name.lower() in game.result.lower():
            winning_team = team_a_name
        elif team_b_name.lower() in game.result.lower():
            winning_team = team_b_name

    momentum_summary = _build_momentum_summary(key_phase_obj, winning_team, total_swing)

    # 8) Compute key players
    key_players = _compute_player_stats(
        deliveries,
        game.batting_scorecard or {},
        game.bowling_scorecard or {},
        team_a,
        team_b,
    )

    # 9) Compute dismissal patterns
    dismissal_patterns = _compute_dismissal_patterns(deliveries)

    # 10) Generate AI summary
    ai_block = _generate_ai_summary(case_study_match, phases, key_players)

    # 11) Return complete response
    return MatchCaseStudyResponse(
        match=case_study_match,
        momentum_summary=momentum_summary,
        key_phase=key_phase,
        phases=phases,
        key_players=key_players,
        dismissal_patterns=dismissal_patterns,
        ai=ai_block,
    )


# -----------------------------------------------------------------------------
# Mock Data Functions (for development/testing)
# -----------------------------------------------------------------------------


def _build_m1_mock_case_study() -> MatchCaseStudyResponse:
    """Build mock case study for match m1: Lions vs Falcons."""
    match = CaseStudyMatch(
        id="m1",
        date=date(2025, 11, 28),
        format="T20",
        home_team="Lions",
        away_team="Falcons",
        teams_label="Lions vs Falcons",
        venue="Eden Gardens",
        result="Lions won by 18 runs",
        overs_per_side=20,
        innings=[
            CaseStudyInningsSummary(
                team="Lions",
                runs=187,
                wickets=5,
                overs=20.0,
                run_rate=9.35,
            ),
            CaseStudyInningsSummary(
                team="Falcons",
                runs=169,
                wickets=8,
                overs=20.0,
                run_rate=8.45,
            ),
        ],
    )

    momentum_summary = CaseStudyMomentumSummary(
        title="Lions dominated the death overs",
        subtitle="Key acceleration in overs 16-20 proved decisive",
        winning_side="Lions",
        swing_metric=CaseStudySwingMetric(
            runs_above_par=22,
            win_probability_shift=0.35,
        ),
    )

    key_phase = CaseStudyKeyPhase(
        title="Death Overs Surge",
        detail="Lions scored 68/1 in overs 16-20, including 4 sixes. "
        "Falcons bowlers conceded 14+ runs in each of the last 3 overs.",
        overs_range={"start_over": 16, "end_over": 20},
        reason_codes=["high_strike_rate", "boundary_percentage", "wicket_preservation"],
    )

    phases = [
        CaseStudyPhase(
            id="powerplay",
            label="Powerplay (1-6)",
            start_over=1,
            end_over=6,
            runs=52,
            wickets=1,
            run_rate=8.67,
            net_swing_vs_par=4,
            impact="positive",
            impact_label="+4 vs par",
        ),
        CaseStudyPhase(
            id="middle",
            label="Middle Overs (7-15)",
            start_over=7,
            end_over=15,
            runs=67,
            wickets=3,
            run_rate=7.44,
            net_swing_vs_par=-4,
            impact="negative",
            impact_label="-4 vs par",
        ),
        CaseStudyPhase(
            id="death",
            label="Death Overs (16-20)",
            start_over=16,
            end_over=20,
            runs=68,
            wickets=1,
            run_rate=13.6,
            net_swing_vs_par=22,
            impact="positive",
            impact_label="+22 vs par",
        ),
    ]

    key_players = [
        CaseStudyKeyPlayer(
            id="player-101",
            name="Marcus Thompson",
            team="Lions",
            role="All-rounder",
            batting=CaseStudyPlayerBatting(
                innings=1,
                runs=72,
                balls=48,
                strike_rate=150.0,
                boundaries={"fours": 6, "sixes": 3},
            ),
            bowling=CaseStudyPlayerBowling(
                overs=4.0,
                maidens=0,
                runs=28,
                wickets=2,
                economy=7.0,
            ),
            fielding=None,
            impact="high",
            impact_label="Match-winning 72 off 48",
            impact_score=9.2,
        ),
        CaseStudyKeyPlayer(
            id="player-205",
            name="Raj Sharma",
            team="Lions",
            role="Bowler",
            batting=None,
            bowling=CaseStudyPlayerBowling(
                overs=4.0,
                maidens=1,
                runs=24,
                wickets=3,
                economy=6.0,
            ),
            fielding=None,
            impact="high",
            impact_label="3/24 in 4 overs",
            impact_score=8.5,
        ),
        CaseStudyKeyPlayer(
            id="player-312",
            name="David Clarke",
            team="Falcons",
            role="Batter",
            batting=CaseStudyPlayerBatting(
                innings=1,
                runs=58,
                balls=42,
                strike_rate=138.1,
                boundaries={"fours": 5, "sixes": 2},
            ),
            bowling=None,
            fielding=None,
            impact="medium",
            impact_label="Top scorer for Falcons",
            impact_score=7.1,
        ),
    ]

    dismissal_patterns = CaseStudyDismissalPatterns(
        summary="Pace bowlers dominated with 6 of 8 wickets. "
        "Aggressive shots in the death overs led to 4 dismissals.",
        by_bowler_type=[
            CaseStudyDismissalByBowlerType(type="Pace", wickets=6),
            CaseStudyDismissalByBowlerType(type="Spin", wickets=2),
        ],
        by_shot_type=[
            CaseStudyDismissalByShotType(shot="Drive", wickets=3),
            CaseStudyDismissalByShotType(shot="Pull/Hook", wickets=2),
            CaseStudyDismissalByShotType(shot="Slog", wickets=2),
            CaseStudyDismissalByShotType(shot="Edge", wickets=1),
        ],
        by_zone=[
            CaseStudyDismissalByZone(zone="Deep Midwicket", wickets=3),
            CaseStudyDismissalByZone(zone="Covers", wickets=2),
            CaseStudyDismissalByZone(zone="Behind Wicket", wickets=2),
            CaseStudyDismissalByZone(zone="Bowled", wickets=1),
        ],
    )

    ai_block = CaseStudyAIBlock(
        match_summary=(
            "A high-scoring T20 encounter saw Lions post 187/5, powered by "
            "Marcus Thompson's explosive 72 off 48 balls. The death overs proved "
            "decisive as Lions added 68 runs while losing just one wicket. "
            "Falcons' chase started well with David Clarke (58) but tight bowling "
            "from Raj Sharma (3/24) restricted them to 169/8. Lions' ability to "
            "accelerate in the final phase was the key difference."
        ),
        generated_at=datetime.utcnow(),
        model_version="gpt-4o-2024-11-01",
        tokens_used=312,
    )

    return MatchCaseStudyResponse(
        match=match,
        momentum_summary=momentum_summary,
        key_phase=key_phase,
        phases=phases,
        key_players=key_players,
        dismissal_patterns=dismissal_patterns,
        ai=ai_block,
    )


def _build_m2_mock_case_study() -> MatchCaseStudyResponse:
    """Build mock case study for match m2: Tigers vs Eagles."""
    match = CaseStudyMatch(
        id="m2",
        date=date(2025, 11, 25),
        format="T20",
        home_team="Tigers",
        away_team="Eagles",
        teams_label="Tigers vs Eagles",
        venue="Wankhede Stadium",
        result="Eagles won by 4 wickets",
        overs_per_side=20,
        innings=[
            CaseStudyInningsSummary(
                team="Tigers",
                runs=156,
                wickets=7,
                overs=20.0,
                run_rate=7.8,
            ),
            CaseStudyInningsSummary(
                team="Eagles",
                runs=159,
                wickets=6,
                overs=19.2,
                run_rate=8.22,
            ),
        ],
    )

    momentum_summary = CaseStudyMomentumSummary(
        title="Eagles' middle-overs masterclass",
        subtitle="Spin bowling strangled Tigers in overs 7-15",
        winning_side="Eagles",
        swing_metric=CaseStudySwingMetric(
            runs_above_par=15,
            win_probability_shift=0.28,
        ),
    )

    key_phase = CaseStudyKeyPhase(
        title="Spin Stranglehold",
        detail="Eagles spinners conceded just 42/4 in overs 7-15, "
        "building pressure that led to risky shots and regular wickets.",
        overs_range={"start_over": 7, "end_over": 15},
        reason_codes=["low_economy", "dot_ball_percentage", "wicket_clusters"],
    )

    phases = [
        CaseStudyPhase(
            id="powerplay",
            label="Powerplay (1-6)",
            start_over=1,
            end_over=6,
            runs=48,
            wickets=1,
            run_rate=8.0,
            net_swing_vs_par=2,
            impact="positive",
            impact_label="+2 vs par",
        ),
        CaseStudyPhase(
            id="middle",
            label="Middle Overs (7-15)",
            start_over=7,
            end_over=15,
            runs=42,
            wickets=4,
            run_rate=4.67,
            net_swing_vs_par=-18,
            impact="negative",
            impact_label="-18 vs par",
        ),
        CaseStudyPhase(
            id="death",
            label="Death Overs (16-20)",
            start_over=16,
            end_over=20,
            runs=66,
            wickets=2,
            run_rate=13.2,
            net_swing_vs_par=12,
            impact="positive",
            impact_label="+12 vs par",
        ),
    ]

    key_players = [
        CaseStudyKeyPlayer(
            id="player-401",
            name="Anil Patel",
            team="Eagles",
            role="Bowler",
            batting=None,
            bowling=CaseStudyPlayerBowling(
                overs=4.0,
                maidens=1,
                runs=18,
                wickets=3,
                economy=4.5,
            ),
            fielding=CaseStudyPlayerFielding(
                catches=1,
                run_outs=0,
                drops=0,
            ),
            impact="high",
            impact_label="3/18 choked the middle overs",
            impact_score=9.0,
        ),
        CaseStudyKeyPlayer(
            id="player-502",
            name="Chris Morgan",
            team="Eagles",
            role="Batter",
            batting=CaseStudyPlayerBatting(
                innings=1,
                runs=64,
                balls=51,
                strike_rate=125.5,
                boundaries={"fours": 7, "sixes": 1},
            ),
            bowling=None,
            fielding=None,
            impact="high",
            impact_label="Anchored the chase with 64*",
            impact_score=8.7,
        ),
    ]

    dismissal_patterns = CaseStudyDismissalPatterns(
        summary="Spin accounted for 5 of 7 wickets. "
        "Most dismissals came from defensive prods and mistimed sweeps.",
        by_bowler_type=[
            CaseStudyDismissalByBowlerType(type="Spin", wickets=5),
            CaseStudyDismissalByBowlerType(type="Pace", wickets=2),
        ],
        by_shot_type=[
            CaseStudyDismissalByShotType(shot="Sweep", wickets=3),
            CaseStudyDismissalByShotType(shot="Defense", wickets=2),
            CaseStudyDismissalByShotType(shot="Drive", wickets=2),
        ],
        by_zone=[
            CaseStudyDismissalByZone(zone="Short Leg", wickets=2),
            CaseStudyDismissalByZone(zone="Slip", wickets=2),
            CaseStudyDismissalByZone(zone="Deep Square", wickets=2),
            CaseStudyDismissalByZone(zone="Bowled", wickets=1),
        ],
    )

    ai_block = CaseStudyAIBlock(
        match_summary=(
            "A masterful spin bowling display from Anil Patel (3/18) derailed "
            "Tigers' innings in the middle overs, restricting them to 156/7. "
            "Eagles' chase was anchored by Chris Morgan's unbeaten 64, who "
            "paced the innings perfectly despite early pressure. The spin-friendly "
            "conditions at Wankhede proved decisive as Eagles won with 4 balls to spare."
        ),
        generated_at=datetime.utcnow(),
        model_version="gpt-4o-2024-11-01",
        tokens_used=287,
    )

    return MatchCaseStudyResponse(
        match=match,
        momentum_summary=momentum_summary,
        key_phase=key_phase,
        phases=phases,
        key_players=key_players,
        dismissal_patterns=dismissal_patterns,
        ai=ai_block,
    )
