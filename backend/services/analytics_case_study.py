"""
Service layer for building Match Case Study analytics.

This module assembles all data required for the MatchCaseStudyResponse,
including match metadata, phase breakdowns, key players, and AI summaries.
"""

from __future__ import annotations

import contextlib
from collections import defaultdict
from datetime import date, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.case_study import (
    CaseStudyAIBlock,
    CaseStudyAnalystCallout,
    CaseStudyDismissalByBowlerType,
    CaseStudyDismissalByShotType,
    CaseStudyDismissalByZone,
    CaseStudyDismissalPatterns,
    CaseStudyInningsAnalysis,
    CaseStudyInningsSummary,
    CaseStudyKeyPhase,
    CaseStudyKeyPlayer,
    CaseStudyMatch,
    CaseStudyMomentumSummary,
    CaseStudyMultiDayInningsContext,
    CaseStudyMultiDaySummary,
    CaseStudyPhase,
    CaseStudyPlayerBatting,
    CaseStudyPlayerBowling,
    CaseStudyPlayerFielding,
    CaseStudyStoryBlocks,
    CaseStudySwingMetric,
    MatchCaseStudyResponse,
)
from backend.services.historical_import_delivery_service import (
    cricket_overs_from_legal_balls,
    cricket_overs_to_legal_balls,
    legal_balls_to_decimal_overs,
)
from backend.sql_app.database import get_session_local
from backend.sql_app.models import Game

# -----------------------------------------------------------------------------
# Phase Definitions
# -----------------------------------------------------------------------------


def _display_overs_from_game_state(overs_completed: int, balls_this_over: int) -> float:
    return cricket_overs_from_legal_balls((int(overs_completed) * 6) + int(balls_this_over))


def _display_overs_to_decimal_overs(overs_value: Any, legal_balls: Any = None) -> float:
    if isinstance(legal_balls, int):
        return legal_balls_to_decimal_overs(legal_balls)
    return legal_balls_to_decimal_overs(cricket_overs_to_legal_balls(overs_value))


def _resolved_result(game: Game) -> str:
    if isinstance(game.result, str) and game.result.strip():
        return game.result.strip()
    status_value = game.status.value if hasattr(game.status, "value") else str(game.status)
    if status_value == "completed":
        return "Completed"
    return "In progress"


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


def _resolve_analysis_mode(
    raw_match_type: str,
    overs_per_side: int,
    innings_count: int,
    days_limit: int | None = None,
) -> Literal["limited_overs", "test_multi_day", "unknown"]:
    normalized = (raw_match_type or "").strip().upper()
    if (
        normalized in {"TEST", "FIRST_CLASS", "FIRST-CLASS", "MULTI_DAY", "MULTI-DAY"}
        or innings_count >= 3
        or (isinstance(days_limit, int) and days_limit > 1)
    ):
        return "test_multi_day"
    if normalized in {"T20", "ODI"} or (
        innings_count <= 2 and overs_per_side > 0 and overs_per_side <= 50
    ):
        return "limited_overs"
    return "unknown"


def _test_multi_day_ranges(overs_value: float) -> list[tuple[str, str, int, int]]:
    max_over = max(1, int(overs_value))
    first_band_end = min(max_over, 20)
    second_band_end = min(max_over, 50)
    ranges = [("custom", f"Overs 1-{first_band_end}", 1, first_band_end)]
    if second_band_end > first_band_end:
        ranges.append(
            (
                "custom",
                f"Overs {first_band_end + 1}-{second_band_end}",
                first_band_end + 1,
                second_band_end,
            )
        )
    if max_over > second_band_end:
        ranges.append(
            ("custom", f"Overs {second_band_end + 1}-{max_over}", second_band_end + 1, max_over)
        )
    return ranges


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
        inning = _delivery_innings_number(d)
        if inning != innings_number:
            continue

        over_num = int(d.get("over_number") or d.get("over") or 1)
        # Total runs for this ball
        runs = d.get("runs_off_bat", 0) + d.get("extra_runs", 0)
        # Fallback to runs_scored if breakdown not available
        if runs == 0 and d.get("runs_scored"):
            runs = d.get("runs_scored", 0)

        per_over_runs[over_num] += runs

        if d.get("is_wicket"):
            per_over_wickets[over_num] += 1

    return dict(per_over_runs), dict(per_over_wickets)


def _delivery_innings_number(delivery: dict[str, Any]) -> int:
    inning = delivery.get("inning")
    if not isinstance(inning, int):
        inning = delivery.get("inning_no")
    if not isinstance(inning, int):
        inning = delivery.get("innings")
    return int(inning) if isinstance(inning, int) and inning > 0 else 1


def _delivery_player_name(delivery: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = delivery.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


# -----------------------------------------------------------------------------
# Phase Stats Computation
# -----------------------------------------------------------------------------


def _compute_phase_stats(
    phase_ranges: list[tuple[str, str, int, int]],
    per_over_runs: dict[int, int],
    per_over_wickets: dict[int, int],
    total_runs: int,
    total_overs: float,
    innings_index: int | None = None,
    team: str | None = None,
    level: Literal["innings", "match"] = "innings",
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
                innings_index=innings_index,
                team=team,
                level=level,
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
    innings_index: int | None = None,
    level: Literal["innings", "match"] = "innings",
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
        innings_index=innings_index,
        phase_id=key_phase.id,
        level=level,
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
                    strike_rate=(
                        round((bs["runs"] / bs["balls"] * 100), 1) if bs["balls"] > 0 else 0.0
                    ),
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
    innings_number: int,
    phase_ranges: list[tuple[str, str, int, int]],
) -> CaseStudyDismissalPatterns:
    """
    Aggregate dismissal patterns from deliveries.
    """
    inning_deliveries = [d for d in deliveries if _delivery_innings_number(d) == innings_number]
    if not inning_deliveries:
        return CaseStudyDismissalPatterns(
            innings_index=innings_number - 1,
            summary="No ball-by-ball deliveries available for this innings.",
            fallback_reason="No ball-by-ball data available.",
        )

    wicket_deliveries = [d for d in inning_deliveries if d.get("is_wicket")]
    if not wicket_deliveries:
        return CaseStudyDismissalPatterns(
            innings_index=innings_number - 1,
            summary="No wicket deliveries recorded for this innings.",
            fallback_reason="No wickets recorded in available delivery data.",
        )

    by_type: dict[str, int] = defaultdict(int)
    by_phase: dict[str, int] = defaultdict(int)
    by_band: dict[str, int] = defaultdict(int)
    by_bowler: dict[str, int] = defaultdict(int)
    by_fielder: dict[str, int] = defaultdict(int)
    by_batter: dict[str, int] = defaultdict(int)
    by_shot: dict[str, int] = defaultdict(int)
    by_zone: dict[str, int] = defaultdict(int)
    over_wickets: dict[int, int] = defaultdict(int)
    wicket_timeline: list[dict[str, Any]] = []
    dismissal_type_available = False

    def phase_label_for_over(over_num: int) -> str:
        for pid, label, start, end in phase_ranges:
            if start <= over_num <= end:
                by_phase[pid] += 1
                return label
        by_phase["other"] += 1
        return "Other"

    for idx, d in enumerate(
        sorted(
            wicket_deliveries,
            key=lambda w: (
                int(w.get("over_number") or w.get("over") or 1),
                int(w.get("ball_number") or 0),
            ),
        ),
        start=1,
    ):
        over_num = int(d.get("over_number") or d.get("over") or 1)
        phase_label = phase_label_for_over(over_num)
        over_wickets[over_num] += 1

        dismissal = str(d.get("dismissal_type") or "").strip()
        if dismissal:
            dismissal_type_available = True
            by_type[dismissal] += 1
        else:
            by_type["Unknown"] += 1

        if over_num <= 6:
            band = "1-6"
        elif over_num <= 15:
            band = "7-15"
        else:
            band = "16+"
        by_band[band] += 1

        bowler_name = _delivery_player_name(d, "bowler_name", "bowler")
        if bowler_name:
            by_bowler[bowler_name] += 1
        fielder_name = _delivery_player_name(d, "fielder_name", "fielder")
        if fielder_name:
            by_fielder[fielder_name] += 1
        batter_name = _delivery_player_name(d, "batter_name", "striker_name", "player_out_name")
        if batter_name:
            by_batter[batter_name] += 1

        shot = str(d.get("shot_type") or "").strip()
        if shot:
            by_shot[shot] += 1
        zone = str(d.get("wagon_zone") or d.get("shot_map") or "").strip()
        if zone:
            by_zone[zone] += 1

        wicket_timeline.append(
            {
                "wicket_number": idx,
                "over": over_num,
                "ball": int(d.get("ball_number") or 0),
                "phase": phase_label,
                "dismissal_type": dismissal or None,
                "batter": batter_name,
                "bowler": bowler_name,
                "fielder": fielder_name,
            }
        )

    cluster_callout = None
    if over_wickets:
        overs = sorted(over_wickets)
        best_window = (0, overs[0], overs[0])
        for start in overs:
            end = start + 2
            wickets_in_window = sum(v for o, v in over_wickets.items() if start <= o <= end)
            if wickets_in_window > best_window[0]:
                best_window = (wickets_in_window, start, end)
        if best_window[0] >= 2:
            cluster_callout = (
                f"Wicket cluster: {best_window[0]} wickets fell between overs "
                f"{best_window[1]}-{best_window[2]}."
            )

    fallback_reason = None
    if not dismissal_type_available:
        fallback_reason = "Dismissal type unavailable in source data."

    return CaseStudyDismissalPatterns(
        innings_index=innings_number - 1,
        summary=(
            f"{len(wicket_deliveries)} wickets fell in innings {innings_number}. "
            f"Most came in {max(by_phase.items(), key=lambda x: x[1])[0]}."
        ),
        total_wickets=len(wicket_deliveries),
        wickets_by_phase=[
            {"phase_id": pid, "wickets": wickets}
            for pid, wickets in sorted(by_phase.items(), key=lambda x: -x[1])
        ],
        wickets_by_over_band=[
            {"band": band, "wickets": wickets}
            for band, wickets in sorted(by_band.items(), key=lambda x: -x[1])
        ],
        dismissal_types=[
            {"type": dtype, "wickets": wickets}
            for dtype, wickets in sorted(by_type.items(), key=lambda x: -x[1])
        ],
        bowler_involvement=[
            {"name": name, "wickets": wickets}
            for name, wickets in sorted(by_bowler.items(), key=lambda x: -x[1])
        ],
        fielding_involvement=[
            {"name": name, "dismissals": dismissals}
            for name, dismissals in sorted(by_fielder.items(), key=lambda x: -x[1])
        ],
        dismissed_batters=[name for name, _ in sorted(by_batter.items(), key=lambda x: -x[1])],
        wicket_timeline=wicket_timeline,
        wicket_cluster_callout=cluster_callout,
        fallback_reason=fallback_reason,
        by_bowler_type=[
            CaseStudyDismissalByBowlerType(type=name, wickets=wickets)
            for name, wickets in sorted(by_bowler.items(), key=lambda x: -x[1])
        ],
        by_shot_type=[
            CaseStudyDismissalByShotType(shot=shot, wickets=wickets)
            for shot, wickets in sorted(by_shot.items(), key=lambda x: -x[1])
        ],
        by_zone=[
            CaseStudyDismissalByZone(zone=zone, wickets=wickets)
            for zone, wickets in sorted(by_zone.items(), key=lambda x: -x[1])
        ],
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
        ml_model_version="case-study-baseline-v1",
        tokens_used=None,
    )


def _find_phase(phases: list[CaseStudyPhase], phase_id: str) -> CaseStudyPhase | None:
    return next((phase for phase in phases if phase.id == phase_id), None)


def _build_story_blocks(
    innings_summary: CaseStudyInningsSummary,
    phases: list[CaseStudyPhase],
    strongest_phase: CaseStudyPhase | None,
    weakest_phase: CaseStudyPhase | None,
    analysis_mode: Literal["limited_overs", "test_multi_day", "unknown"] = "limited_overs",
    innings_number: int = 1,
) -> CaseStudyStoryBlocks:
    if analysis_mode == "test_multi_day":
        return CaseStudyStoryBlocks(
            opening_story=(
                f"Innings {innings_number}: {innings_summary.team} scored "
                f"{innings_summary.runs}/{innings_summary.wickets} in {innings_summary.overs} overs."
            ),
            middle_overs_story="Session-safe progression is used; limited-overs phase labels are intentionally disabled.",
            death_overs_story="Late-innings output is summarized with innings-safe wording only.",
            scoring_acceleration=f"Overall innings run rate: {innings_summary.run_rate:.2f}.",
            wickets_by_phase=(
                f"Total wickets in innings {innings_number}: {innings_summary.wickets}."
            ),
            strongest_phase="Strongest segment is unavailable for Test/multi-day phase-safe mode.",
            weakest_phase="Weakest segment is unavailable for Test/multi-day phase-safe mode.",
            innings_outcome_contribution=(
                f"{innings_summary.team} contributed {innings_summary.runs} runs in innings {innings_number}."
            ),
        )

    opening = _find_phase(phases, "powerplay")
    middle = _find_phase(phases, "middle")
    death = _find_phase(phases, "death")
    strongest_label = strongest_phase.label if strongest_phase else "No phase data"
    weakest_label = weakest_phase.label if weakest_phase else "No phase data"
    return CaseStudyStoryBlocks(
        opening_story=(
            f"{innings_summary.team} scored {opening.runs} and lost {opening.wickets} wickets in the opening phase."
            if opening
            else "Opening phase story unavailable from current data."
        ),
        middle_overs_story=(
            f"Middle overs returned {middle.runs} runs for {middle.wickets} wickets."
            if middle
            else "Middle-overs story unavailable from current data."
        ),
        death_overs_story=(
            f"Death overs produced {death.runs} runs with {death.wickets} wickets."
            if death
            else "Death-overs story unavailable from current data."
        ),
        scoring_acceleration=(
            f"Run-rate changed from {opening.run_rate:.2f} in the opening phase to {death.run_rate:.2f} in the death overs."
            if opening and death
            else f"Overall run rate finished at {innings_summary.run_rate:.2f}."
        ),
        wickets_by_phase=", ".join(f"{phase.id}: {phase.wickets}" for phase in phases)
        if phases
        else "Wickets by phase unavailable.",
        strongest_phase=f"Strongest phase: {strongest_label}.",
        weakest_phase=f"Weakest phase: {weakest_label}.",
        innings_outcome_contribution=(
            f"{innings_summary.team} posted {innings_summary.runs}/{innings_summary.wickets} in {innings_summary.overs} overs."
        ),
    )


def _build_innings_callouts(
    innings_number: int,
    phases: list[CaseStudyPhase],
    dismissal_patterns: CaseStudyDismissalPatterns,
    analysis_mode: Literal["limited_overs", "test_multi_day", "unknown"] = "limited_overs",
) -> list[CaseStudyAnalystCallout]:
    callouts: list[CaseStudyAnalystCallout] = []
    if analysis_mode == "test_multi_day":
        if dismissal_patterns.wicket_cluster_callout:
            callouts.append(
                CaseStudyAnalystCallout(
                    title="Wicket cluster",
                    innings=innings_number,
                    phase="Innings segment",
                    category="dismissal",
                    severity="info",
                    explanation=dismissal_patterns.wicket_cluster_callout,
                    source_metrics=[f"total_wickets={dismissal_patterns.total_wickets}"],
                    confidence=0.85,
                    why_it_matters="Clusters indicate deterministic pressure swings without relying on T20 phase assumptions.",
                )
            )
        if dismissal_patterns.total_wickets >= 5:
            callouts.append(
                CaseStudyAnalystCallout(
                    title="High wicket pressure",
                    innings=innings_number,
                    phase="Innings",
                    category="bowling",
                    severity="warning",
                    explanation=(
                        f"Innings {innings_number} lost {dismissal_patterns.total_wickets} wickets "
                        "in recorded delivery data."
                    ),
                    source_metrics=[f"total_wickets={dismissal_patterns.total_wickets}"],
                    confidence=0.8,
                    why_it_matters="Sustained wicket pressure often drives Test/multi-day momentum changes.",
                )
            )
        return callouts

    middle = _find_phase(phases, "middle")
    death = _find_phase(phases, "death")
    strongest = max(phases, key=lambda p: p.net_swing_vs_par, default=None)
    weakest = min(phases, key=lambda p: p.net_swing_vs_par, default=None)

    if middle and (middle.net_swing_vs_par <= -8 or middle.wickets >= 3):
        callouts.append(
            CaseStudyAnalystCallout(
                title="Middle-over choke",
                innings=innings_number,
                phase="Middle overs",
                category="momentum",
                severity="warning",
                explanation=(
                    f"Innings {innings_number} scored {middle.runs} and lost {middle.wickets} wickets "
                    f"between overs {middle.start_over}-{middle.end_over}."
                ),
                source_metrics=[
                    f"runs={middle.runs}",
                    f"wickets={middle.wickets}",
                    f"net_vs_par={middle.net_swing_vs_par}",
                ],
                confidence=0.9,
                why_it_matters="Middle-over slowdown often determines defendable totals and chase pressure.",
            )
        )
    if death and death.net_swing_vs_par >= 8:
        callouts.append(
            CaseStudyAnalystCallout(
                title="Death-over surge",
                innings=innings_number,
                phase="Death overs",
                category="batting",
                severity="positive",
                explanation=(
                    f"Innings {innings_number} finished {death.net_swing_vs_par:+d} vs par in overs "
                    f"{death.start_over}-{death.end_over}."
                ),
                source_metrics=[
                    f"runs={death.runs}",
                    f"run_rate={death.run_rate}",
                    f"net_vs_par={death.net_swing_vs_par}",
                ],
                confidence=0.9,
                why_it_matters="Death-over acceleration changes totals quickly and shifts match pressure.",
            )
        )
    if dismissal_patterns.wicket_cluster_callout:
        callouts.append(
            CaseStudyAnalystCallout(
                title="Wicket cluster",
                innings=innings_number,
                phase="Wickets",
                category="dismissal",
                severity="info",
                explanation=dismissal_patterns.wicket_cluster_callout,
                source_metrics=[f"total_wickets={dismissal_patterns.total_wickets}"],
                confidence=0.85,
                why_it_matters="Clusters create momentum shocks and often decide innings direction.",
            )
        )
    if strongest:
        callouts.append(
            CaseStudyAnalystCallout(
                title="Strongest phase",
                innings=innings_number,
                phase=strongest.label,
                category="momentum",
                severity="info",
                explanation=f"{strongest.label} was the strongest segment at {strongest.net_swing_vs_par:+d} vs par.",
                source_metrics=[
                    f"phase={strongest.id}",
                    f"net_vs_par={strongest.net_swing_vs_par}",
                ],
                confidence=0.8,
                why_it_matters="Strong phases reveal where control was established.",
            )
        )
    if weakest and strongest and weakest.id != strongest.id:
        callouts.append(
            CaseStudyAnalystCallout(
                title="Weakest phase",
                innings=innings_number,
                phase=weakest.label,
                category="momentum",
                severity="warning",
                explanation=f"{weakest.label} underperformed at {weakest.net_swing_vs_par:+d} vs par.",
                source_metrics=[f"phase={weakest.id}", f"net_vs_par={weakest.net_swing_vs_par}"],
                confidence=0.8,
                why_it_matters="Weak phases expose tactical windows for the opposition.",
            )
        )
    return callouts


def _build_multi_day_summary(match: CaseStudyMatch) -> CaseStudyMultiDaySummary:
    cumulative_runs: dict[str, int] = defaultdict(int)
    innings_rows: list[CaseStudyMultiDayInningsContext] = []
    for idx, inn in enumerate(match.innings, start=1):
        cumulative_runs[inn.team] += inn.runs
        opponent_total = max(
            (runs for team, runs in cumulative_runs.items() if team != inn.team), default=0
        )
        deliveries = cricket_overs_to_legal_balls(inn.overs)
        innings_rows.append(
            CaseStudyMultiDayInningsContext(
                innings_number=idx,
                team=inn.team,
                runs=inn.runs,
                wickets=inn.wickets,
                overs=inn.overs,
                deliveries=deliveries,
                lead_deficit_after_innings=cumulative_runs[inn.team] - opponent_total,
            )
        )

    result_lower = (match.result or "").lower()
    match_status: Literal["won", "lost", "draw", "tie", "no_result", "unknown"] = "unknown"
    if "won" in result_lower:
        match_status = "won"
    elif "lost" in result_lower:
        match_status = "lost"
    elif "draw" in result_lower:
        match_status = "draw"
    elif "tie" in result_lower:
        match_status = "tie"
    elif "no result" in result_lower or "abandoned" in result_lower:
        match_status = "no_result"

    fourth_note = None
    if len(innings_rows) >= 4:
        chasing_team = innings_rows[3].team
        opposition_total = sum(row.runs for row in innings_rows[:3] if row.team != chasing_team)
        chasing_prior = sum(row.runs for row in innings_rows[:3] if row.team == chasing_team)
        target = opposition_total - chasing_prior + 1
        if target > 0:
            remaining = target - innings_rows[3].runs
            if remaining > 0:
                fourth_note = (
                    f"Fourth-innings chase context: {chasing_team} required {target}, "
                    f"finishing {remaining} short in recorded totals."
                )
            else:
                fourth_note = f"Fourth-innings chase context: {chasing_team} exceeded the implied target of {target}."

    return CaseStudyMultiDaySummary(
        match_status=match_status,
        innings=innings_rows,
        fourth_innings_chase_note=fourth_note,
    )


def _build_match_callouts(
    match: CaseStudyMatch,
    analysis_mode: Literal["limited_overs", "test_multi_day", "unknown"] = "limited_overs",
) -> list[CaseStudyAnalystCallout]:
    if analysis_mode == "test_multi_day":
        return [
            CaseStudyAnalystCallout(
                title="Test/multi-day limited-analysis notice",
                level="match",
                innings=None,
                phase="Full match",
                category="outcome",
                severity="info",
                explanation=(
                    "Test/multi-day analysis is currently limited and uses innings/session-safe summaries."
                ),
                source_metrics=[f"innings_count={len(match.innings)}"],
                confidence=0.95,
                why_it_matters="This prevents misleading limited-overs framing for 3/4-innings matches.",
            )
        ]

    innings = match.innings[:2]
    if len(innings) < 2:
        return []
    run_diff = innings[0].runs - innings[1].runs
    return [
        CaseStudyAnalystCallout(
            title="Match outcome context",
            level="match",
            innings=None,
            phase="Full match",
            category="outcome",
            severity="info",
            explanation=f"{match.result} (innings run differential: {run_diff:+d}).",
            source_metrics=[
                f"innings_1_runs={innings[0].runs}",
                f"innings_2_runs={innings[1].runs}",
            ],
            confidence=0.95,
            why_it_matters="Outcome context anchors innings-level insights to the final result.",
        )
    ]


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
    raw_match_type = game.match_type.upper() if game.match_type else "T20"
    match_format = raw_match_type
    if match_format not in ("T20", "ODI", "TEST"):
        match_format = "CUSTOM"

    # Detect whether this is a historical import (Phase 5D+)
    game_phases_blob = game.phases if isinstance(game.phases, dict) else {}
    hist_meta = game_phases_blob.get("historical_import")
    is_historical = isinstance(hist_meta, dict) and bool(hist_meta.get("is_historical"))
    hist_innings = game_phases_blob.get("historical_innings_summary") or []
    deliveries_imported = (
        isinstance(hist_meta, dict) and bool(hist_meta.get("deliveries_imported"))
    ) or bool(isinstance(game.deliveries, list) and len(game.deliveries) > 0)

    # 3) Build innings summaries
    innings_summaries: list[CaseStudyInningsSummary] = []

    if is_historical and hist_innings:
        for inn in hist_innings:
            if not isinstance(inn, dict):
                continue
            inn_runs = int(inn.get("runs") or 0)
            inn_overs = float(inn.get("overs") or 0.0)
            decimal_overs = _display_overs_to_decimal_overs(inn_overs, inn.get("legal_balls"))
            innings_summaries.append(
                CaseStudyInningsSummary(
                    team=inn.get("team") or team_a_name,
                    runs=inn_runs,
                    wickets=int(inn.get("wickets") or 0),
                    overs=inn_overs,
                    run_rate=round(inn_runs / max(decimal_overs, 0.1), 2),
                )
            )
    elif game.first_inning_summary:
        # Live scoring data (Phase 5F imported or real live game)
        fis = game.first_inning_summary
        display_overs = float(fis.get("overs", 0))
        innings_summaries.append(
            CaseStudyInningsSummary(
                team=fis.get("batting_team", team_a_name),
                runs=fis.get("runs", 0),
                wickets=fis.get("wickets", 0),
                overs=display_overs,
                run_rate=round(
                    fis.get("runs", 0) / max(_display_overs_to_decimal_overs(display_overs), 0.1),
                    2,
                ),
            )
        )

    # Second innings (live or historical post-Phase-5F)
    if not is_historical:
        if game.current_inning >= 2 or not innings_summaries:
            overs_display = _display_overs_from_game_state(
                game.overs_completed, game.balls_this_over
            )
            decimal_overs = legal_balls_to_decimal_overs(
                (game.overs_completed * 6) + game.balls_this_over
            )
            innings_summaries.append(
                CaseStudyInningsSummary(
                    team=game.batting_team_name or team_b_name,
                    runs=game.total_runs,
                    wickets=game.total_wickets,
                    overs=overs_display,
                    run_rate=round(game.total_runs / max(decimal_overs, 0.1), 2),
                )
            )
    else:
        # For historical games, second innings is populated by Phase 5F delivery import
        # or by the historical_innings_summary (already added above in the hist_innings loop)
        if deliveries_imported and game.first_inning_summary:
            first_fis = game.first_inning_summary
            if innings_summaries:
                first_overs = float(first_fis.get("overs", 0))
                innings_summaries[0] = CaseStudyInningsSummary(
                    team=first_fis.get("batting_team", innings_summaries[0].team),
                    runs=int(first_fis.get("runs", innings_summaries[0].runs)),
                    wickets=int(first_fis.get("wickets", innings_summaries[0].wickets)),
                    overs=first_overs,
                    run_rate=round(
                        int(first_fis.get("runs", innings_summaries[0].runs))
                        / max(_display_overs_to_decimal_overs(first_overs), 0.1),
                        2,
                    ),
                )
            overs_display = _display_overs_from_game_state(
                game.overs_completed, game.balls_this_over
            )
            decimal_overs = legal_balls_to_decimal_overs(
                (game.overs_completed * 6) + game.balls_this_over
            )
            second_summary = CaseStudyInningsSummary(
                team=game.batting_team_name
                or (hist_innings[1].get("team") if len(hist_innings) > 1 else team_b_name),
                runs=game.total_runs,
                wickets=game.total_wickets,
                overs=overs_display,
                run_rate=round(game.total_runs / max(decimal_overs, 0.1), 2),
            )
            if len(innings_summaries) >= 2:
                innings_summaries[1] = second_summary
            else:
                innings_summaries.append(second_summary)

    # 4) Build CaseStudyMatch
    match_date = date.today()  # Game model doesn't have created_at exposed as date
    if hasattr(game, "created_at") and game.created_at:
        match_date = game.created_at.date()

    # For historical imports, use the match date from metadata if available
    if is_historical and isinstance(hist_meta, dict):
        raw_date = hist_meta.get("match_date")
        if raw_date:
            with contextlib.suppress(ValueError, TypeError):
                match_date = date.fromisoformat(str(raw_date))

    case_study_match = CaseStudyMatch(
        id=game.id,
        date=match_date,
        format=match_format,  # type: ignore[arg-type]
        home_team=team_a_name,
        away_team=team_b_name,
        teams_label=f"{team_a_name} vs {team_b_name}",
        venue=hist_meta.get("venue") if isinstance(hist_meta, dict) else None,
        event_name=hist_meta.get("event_name") if isinstance(hist_meta, dict) else None,
        season=hist_meta.get("season") if isinstance(hist_meta, dict) else None,
        match_number=hist_meta.get("match_number") if isinstance(hist_meta, dict) else None,
        source_dates=hist_meta.get("source_dates") if isinstance(hist_meta, dict) else [],
        result=_resolved_result(game),
        overs_per_side=overs_per_side,
        innings=innings_summaries,
    )
    analysis_mode = _resolve_analysis_mode(
        raw_match_type=raw_match_type,
        overs_per_side=overs_per_side,
        innings_count=len(innings_summaries),
        days_limit=game.days_limit,
    )
    multi_day_summary = (
        _build_multi_day_summary(case_study_match) if analysis_mode == "test_multi_day" else None
    )

    # 5) Get deliveries and key players
    deliveries = game.deliveries or []
    key_players = _compute_player_stats(
        deliveries,
        game.batting_scorecard or {},
        game.bowling_scorecard or {},
        team_a,
        team_b,
    )

    # 6) Determine winner from result
    winning_team = None
    if game.result:
        if team_a_name.lower() in game.result.lower():
            winning_team = team_a_name
        elif team_b_name.lower() in game.result.lower():
            winning_team = team_b_name

    # 7) Build innings-level intelligence
    phase_ranges = _get_phase_ranges(match_format, overs_per_side)
    innings_analysis: list[CaseStudyInningsAnalysis] = []
    for innings_index, innings_summary in enumerate(innings_summaries):
        innings_number = innings_index + 1
        per_over_runs, per_over_wickets = _aggregate_per_over(deliveries, innings_number)
        total_runs = innings_summary.runs
        total_overs = max(_display_overs_to_decimal_overs(innings_summary.overs), 0.1)
        innings_phase_ranges = (
            _test_multi_day_ranges(innings_summary.overs)
            if analysis_mode == "test_multi_day"
            else phase_ranges
        )

        if analysis_mode == "test_multi_day":
            phases = []
            key_phase = CaseStudyKeyPhase(
                title=f"Innings {innings_number} summary",
                detail=(
                    f"{innings_summary.team} scored {innings_summary.runs}/{innings_summary.wickets} "
                    f"in {innings_summary.overs} overs."
                ),
                innings_index=innings_index,
                team=innings_summary.team,
                level="innings",
                overs_range=None,
                reason_codes=["innings_safe_summary"],
            )
            momentum_summary = CaseStudyMomentumSummary(
                title="Innings-safe momentum summary",
                subtitle=(
                    "Test/multi-day analysis is currently limited and uses innings/session-safe summaries."
                ),
                winning_side=winning_team,
                innings_index=innings_index,
                phase_id=None,
                level="innings",
                swing_metric=None,
            )
        elif per_over_runs:
            phases = _compute_phase_stats(
                innings_phase_ranges,
                per_over_runs,
                per_over_wickets,
                total_runs,
                total_overs,
                innings_index=innings_index,
                team=innings_summary.team,
                level="innings",
            )
            key_phase_obj, reason_code = _determine_key_phase(phases)
            key_phase = CaseStudyKeyPhase(
                title=f"{key_phase_obj.label} Analysis",
                detail=(
                    f"Scored {key_phase_obj.runs} runs with {key_phase_obj.wickets} wickets lost. "
                    f"Run rate: {key_phase_obj.run_rate}, {key_phase_obj.impact_label}."
                ),
                innings_index=innings_index,
                team=innings_summary.team,
                level="innings",
                overs_range={
                    "start_over": key_phase_obj.start_over,
                    "end_over": key_phase_obj.end_over,
                },
                reason_codes=[reason_code],
            )
            total_swing = sum(p.net_swing_vs_par for p in phases if p.impact == "positive")
            momentum_summary = _build_momentum_summary(
                key_phase_obj,
                winning_team,
                total_swing,
                innings_index=innings_index,
                level="innings",
            )
        else:
            phases = []
            key_phase = CaseStudyKeyPhase(
                title="Phase data not yet available",
                detail=(
                    "Delivery-level data has not been imported yet for this innings."
                    if is_historical
                    else "No delivery data available for this innings."
                ),
                innings_index=innings_index,
                team=innings_summary.team,
                level="innings",
                overs_range=None,
                reason_codes=[],
            )
            momentum_summary = CaseStudyMomentumSummary(
                title="Momentum data not yet available",
                subtitle="No delivery data available for this innings.",
                winning_side=winning_team,
                innings_index=innings_index,
                phase_id=None,
                level="innings",
                swing_metric=None,
            )

        dismissal_patterns = _compute_dismissal_patterns(
            deliveries, innings_number, innings_phase_ranges
        )
        strongest_phase = max(phases, key=lambda p: p.net_swing_vs_par) if phases else None
        weakest_phase = min(phases, key=lambda p: p.net_swing_vs_par) if phases else None
        story_blocks = _build_story_blocks(
            innings_summary,
            phases,
            strongest_phase,
            weakest_phase,
            analysis_mode=analysis_mode,
            innings_number=innings_number,
        )
        callouts = _build_innings_callouts(
            innings_number,
            phases,
            dismissal_patterns,
            analysis_mode=analysis_mode,
        )
        innings_analysis.append(
            CaseStudyInningsAnalysis(
                innings_index=innings_index,
                team=innings_summary.team,
                deterministic_summary=(
                    f"Innings {innings_number}: {innings_summary.team} scored "
                    f"{innings_summary.runs}/{innings_summary.wickets} in {innings_summary.overs} overs."
                ),
                momentum_summary=momentum_summary,
                key_phase=key_phase,
                phases=phases,
                key_players=key_players,
                key_players_scope="match",
                dismissal_patterns=dismissal_patterns,
                story_blocks=story_blocks,
                callouts=callouts,
            )
        )

    selected_innings = innings_analysis[0] if innings_analysis else None
    phases = selected_innings.phases if selected_innings else []
    key_phase = (
        selected_innings.key_phase
        if selected_innings
        else CaseStudyKeyPhase(
            title="Phase data not yet available",
            detail="No innings analysis available.",
            level="match",
        )
    )
    momentum_summary = (
        selected_innings.momentum_summary
        if selected_innings
        else CaseStudyMomentumSummary(
            title="Momentum data not yet available",
            subtitle="No innings analysis available.",
            level="match",
        )
    )
    selected_dismissal_patterns = selected_innings.dismissal_patterns if selected_innings else None

    # 8) Generate AI summary
    ai_block = _generate_ai_summary(case_study_match, phases, key_players)
    match_callouts = _build_match_callouts(case_study_match, analysis_mode=analysis_mode)

    # 9) Return complete response
    return MatchCaseStudyResponse(
        analysis_mode=analysis_mode,
        match=case_study_match,
        momentum_summary=momentum_summary,
        key_phase=key_phase,
        phases=phases,
        key_players=key_players,
        dismissal_patterns=selected_dismissal_patterns,
        innings_analysis=innings_analysis,
        match_callouts=match_callouts,
        match_level_summary=f"{case_study_match.teams_label}: {case_study_match.result}",
        multi_day_summary=multi_day_summary,
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
