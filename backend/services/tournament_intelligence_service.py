"""Phase 10S.1 / 10S.2 — Tournament Intelligence Service.

Provides deterministic tournament-level intelligence derived from historical
match data classified by Phase 10S. Builds on the existing historical stats
aggregation and analyst registry classification foundations.

Phase 10S.2 adds: tournament podcast rundown generation, season review narrative,
champion journey block, road-to-final block, and structured podcast sections.

All logic is deterministic Python — no AI/LLM services are used.
No official standings, stats, or champion claims are fabricated.
Every output is labeled with its derivation source and confidence level.
"""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from backend.api.schemas.historical_stats import (
    MatchAggregate,
    SeasonOutcomeAggregate,
)
from backend.api.schemas.tournament_intelligence import (
    DerivedStandingsRow,
    TeamJourneyMatch,
    TeamJourneyResponse,
    TeamJourneySummary,
    TournamentChampionJourney,
    TournamentDataCompleteness,
    TournamentGroupKey,
    TournamentGroupSummary,
    TournamentGroupsResponse,
    TournamentKnockoutContext,
    TournamentMatchHighlight,
    TournamentPlayerLeader,
    TournamentPodcastFacts,
    TournamentPodcastRundown,
    TournamentPodcastSection,
    TournamentRoadToFinal,
    TournamentSeasonReview,
    TournamentSummaryResponse,
)
from backend.services.analyst_registry_service import classify_competition, classify_gender
from backend.services.cpl_team_alias_registry import canonicalize_team_name
from backend.sql_app.models import Game, GameStatus, HistoricalImportBatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Stage label detection (mirrors historical_stats_aggregation_service)
# ---------------------------------------------------------------------------

_FINAL_STAGE_RE = re.compile(r"\bgrand\s+final\b|\bfinal\b", re.I)
_SEMI_FINAL_STAGE_RE = re.compile(r"\bsemi[\s-]?final\b", re.I)
_QUALIFIER_STAGE_RE = re.compile(r"\bqualifier\b", re.I)
_ELIMINATOR_STAGE_RE = re.compile(r"\beliminator\b", re.I)
_PLAYOFF_STAGE_RE = re.compile(r"\bplay[\s-]?off\b|\bknock[\s-]?out\b", re.I)
_SEASON_YEAR_RE = re.compile(r"(?:19|20)\d{2}")

# Metadata-only batch statuses (mirrors historical_stats_aggregation_service)
_METADATA_ONLY_STATUSES: frozenset[str] = frozenset(
    {"scanned", "metadata_extracted", "pending_full_import"}
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _hist_meta(game: Game) -> dict[str, Any] | None:
    phases = game.phases if isinstance(game.phases, dict) else {}
    meta = phases.get("historical_import")
    if isinstance(meta, dict) and meta.get("is_historical"):
        return meta
    return None


def _is_metadata_only(batch: HistoricalImportBatch) -> bool:
    return batch.status in _METADATA_ONLY_STATUSES


def _is_eligible(batch: HistoricalImportBatch) -> bool:
    if _is_metadata_only(batch):
        return False
    if not batch.is_finalized:
        return False
    if not batch.applied_game_id:
        return False
    if batch.status != "valid":
        return False
    return batch.error_count == 0


def _innings_summary(game: Game) -> list[dict[str, Any]]:
    phases = game.phases if isinstance(game.phases, dict) else {}
    raw = phases.get("historical_innings_summary")
    if isinstance(raw, list):
        return [inn for inn in raw if isinstance(inn, dict)]
    return []


def _pluralize(count: int, singular: str, plural: str | None = None) -> str:
    """Return '<count> <singular>' or '<count> <plural>' based on count."""
    if plural is None:
        plural = singular + "s"
    return f"{count} {singular}" if count == 1 else f"{count} {plural}"


def _detect_stage_label(meta: dict[str, Any], match_title: str | None = None) -> str | None:
    candidates: list[str] = []
    for key in ("competition_stage", "tournament_round"):
        value = meta.get(key)
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())
    if match_title:
        candidates.append(match_title)
    for text in candidates:
        if _SEMI_FINAL_STAGE_RE.search(text):
            return "Semi Final"
        if _QUALIFIER_STAGE_RE.search(text):
            return "Qualifier"
        if _ELIMINATOR_STAGE_RE.search(text):
            return "Eliminator"
        if _PLAYOFF_STAGE_RE.search(text):
            return "Playoff"
        if _FINAL_STAGE_RE.search(text):
            return "Final"
    return None


def _is_final_stage(stage_label: str | None) -> bool:
    if not stage_label:
        return False
    lowered = stage_label.lower()
    return "final" in lowered and "semi" not in lowered


def _season_year_value(season: str | None) -> int | None:
    if not season:
        return None
    match = _SEASON_YEAR_RE.search(season)
    return int(match.group(0)) if match else None


def _derive_format_family(match_type: str | None, format_str: str | None = None) -> str:
    """Coerce format to a family label."""
    for val in (match_type, format_str):
        if not val:
            continue
        low = val.lower()
        if "t20" in low or "twenty" in low:
            return "T20"
        if "odi" in low or "one.day" in low or "one day" in low or "list a" in low:
            return "ODI"
        if "test" in low or "first.class" in low or "first class" in low:
            return "TEST"
    return "unknown"


def _derive_outcome(
    result_text: str | None,
    team_name: str,
) -> str:
    """Return win | loss | tie | no_result | unknown for a team given result text."""
    if not result_text:
        return "unknown"
    low = result_text.lower()
    if any(t in low for t in ("tie", "draw", "no result", "abandon")):
        return "tie" if "tie" in low else "no_result"
    # Win signals: team name appears before " won " / " beat " / " defeated "
    for marker in (" won", " beat", " defeated"):
        idx = low.find(marker)
        if idx > 0:
            preceding = result_text[:idx].lower()
            if team_name.lower() in preceding:
                return "win"
            return "loss"
    return "unknown"


def _completeness_level(game: Game, meta: dict[str, Any]) -> str:
    """Return data_completeness label from a game."""
    if meta.get("deliveries_imported") or (
        isinstance(game.deliveries, list) and len(game.deliveries) > 0
    ):
        return "delivery_complete"
    phases = game.phases if isinstance(game.phases, dict) else {}
    if any(phases.get(ph) for ph in ("powerplay", "middle", "death")):
        return "phase_level"
    innings = _innings_summary(game)
    if innings:
        return "innings_totals"
    return "metadata_only"


# ---------------------------------------------------------------------------
# Group matches by tournament key
# ---------------------------------------------------------------------------

EligibleGame = tuple[Game, HistoricalImportBatch, dict[str, Any], MatchAggregate]


def _group_eligible_games(
    eligible_games: list[EligibleGame],
) -> dict[tuple[str, str, str, str | None, str], list[EligibleGame]]:
    """Group eligible games by (competition_code, competition_name, gender, season, format_family).

    Uses conservative classification — unknown values are kept as 'unknown'
    rather than being forced into incorrect groups.
    """
    groups: dict[tuple[str, str, str, str | None, str], list[EligibleGame]] = defaultdict(list)

    for entry in eligible_games:
        game, _batch, meta, match = entry
        event_name = meta.get("event_name") if isinstance(meta.get("event_name"), str) else None
        competition_code, competition_name = classify_competition(event_name)
        gender_category = classify_gender(competition_code, meta.get("gender"))
        format_family = _derive_format_family(
            game.match_type, meta.get("match_format") or meta.get("format")
        )
        season_value = match.season

        key = (competition_code, competition_name, gender_category, season_value, format_family)
        groups[key].append(entry)

    return groups


# ---------------------------------------------------------------------------
# Derived standings
# ---------------------------------------------------------------------------


def _build_derived_standings(
    group_games: list[EligibleGame],
) -> list[DerivedStandingsRow]:
    """Derive a standings table from match results within a tournament group.

    Points: 2 for win, 1 for tie/no-result, 0 for loss.
    NRR is computed only when innings runs and overs are available.
    All output is labeled 'derived' — not official standings.
    """
    team_acc: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "played": 0,
            "wins": 0,
            "losses": 0,
            "ties": 0,
            "no_results": 0,
            "points": 0,
            "runs_for": 0,
            "overs_faced": 0.0,
            "runs_against": 0,
            "overs_bowled": 0.0,
            "nrr_computable": True,
            "canonical": None,
        }
    )

    for game, _batch, _meta, match in group_games:
        team_a = match.team_a or "Team A"
        team_b = match.team_b or "Team B"
        team_a_canonical = match.team_a_canonical or team_a
        team_b_canonical = match.team_b_canonical or team_b

        # Initialise canonical names
        if team_acc[team_a]["canonical"] is None:
            team_acc[team_a]["canonical"] = team_a_canonical
        if team_acc[team_b]["canonical"] is None:
            team_acc[team_b]["canonical"] = team_b_canonical

        winner = match.winner_team_canonical or match.winner_team

        # Derive win/loss/tie from result text or winner field
        result_low = (game.result or "").lower()
        if any(t in result_low for t in ("no result", "abandon")):
            outcome = "no_result"
        elif any(t in result_low for t in ("tie", "draw")):
            outcome = "tie"
        elif winner:
            if winner in (team_a_canonical, team_a):
                outcome = "a_wins"
            elif winner in (team_b_canonical, team_b):
                outcome = "b_wins"
            else:
                outcome = "unknown"
        else:
            outcome = "unknown"

        for team_name in (team_a, team_b):
            team_acc[team_name]["played"] += 1

        if outcome == "a_wins":
            team_acc[team_a]["wins"] += 1
            team_acc[team_a]["points"] += 2
            team_acc[team_b]["losses"] += 1
        elif outcome == "b_wins":
            team_acc[team_b]["wins"] += 1
            team_acc[team_b]["points"] += 2
            team_acc[team_a]["losses"] += 1
        elif outcome == "tie":
            team_acc[team_a]["ties"] += 1
            team_acc[team_a]["points"] += 1
            team_acc[team_b]["ties"] += 1
            team_acc[team_b]["points"] += 1
        elif outcome == "no_result":
            team_acc[team_a]["no_results"] += 1
            team_acc[team_a]["points"] += 1
            team_acc[team_b]["no_results"] += 1
            team_acc[team_b]["points"] += 1

        # NRR: accumulate innings runs/overs where available
        innings_list = _innings_summary(game)
        innings_by_no: dict[int, dict[str, Any]] = {
            int(inn.get("inning_no") or 0): inn for inn in innings_list
        }
        inn1 = innings_by_no.get(1)
        inn2 = innings_by_no.get(2)

        inn1_team = str(inn1.get("team") or "") if inn1 else ""
        inn2_team = str(inn2.get("team") or "") if inn2 else ""

        # Determine which team batted first
        for team_name in (team_a, team_b):
            if inn1 and inn1_team and team_name.lower() in inn1_team.lower():
                # team_name batted first (innings 1)
                inn1_runs = int(inn1.get("runs") or 0)
                inn1_overs = float(inn1.get("overs") or 0)
                team_acc[team_name]["runs_for"] += inn1_runs
                team_acc[team_name]["overs_faced"] += inn1_overs if inn1_overs > 0 else 0
                if inn2:
                    inn2_runs = int(inn2.get("runs") or 0)
                    inn2_overs = float(inn2.get("overs") or 0)
                    team_acc[team_name]["runs_against"] += inn2_runs
                    team_acc[team_name]["overs_bowled"] += inn2_overs if inn2_overs > 0 else 0
            elif inn2 and inn2_team and team_name.lower() in inn2_team.lower():
                # team_name batted second (innings 2)
                inn2_runs = int(inn2.get("runs") or 0)
                inn2_overs = float(inn2.get("overs") or 0)
                team_acc[team_name]["runs_for"] += inn2_runs
                team_acc[team_name]["overs_faced"] += inn2_overs if inn2_overs > 0 else 0
                if inn1:
                    inn1_runs = int(inn1.get("runs") or 0)
                    inn1_overs = float(inn1.get("overs") or 0)
                    team_acc[team_name]["runs_against"] += inn1_runs
                    team_acc[team_name]["overs_bowled"] += inn1_overs if inn1_overs > 0 else 0
            else:
                # Can't assign innings — mark NRR as unavailable
                team_acc[team_name]["nrr_computable"] = False

    rows: list[DerivedStandingsRow] = []
    for team_name, acc in team_acc.items():
        nrr: float | None = None
        nrr_available = False
        if acc["nrr_computable"] and acc["overs_faced"] > 0 and acc["overs_bowled"] > 0:
            run_rate_for = acc["runs_for"] / acc["overs_faced"]
            run_rate_against = acc["runs_against"] / acc["overs_bowled"]
            nrr = round(run_rate_for - run_rate_against, 3)
            nrr_available = True

        confidence = "medium" if acc["wins"] + acc["losses"] > 0 else "low"

        rows.append(
            DerivedStandingsRow(
                team_name=team_name,
                canonical_team_name=acc["canonical"],
                played=acc["played"],
                wins=acc["wins"],
                losses=acc["losses"],
                ties=acc["ties"],
                no_results=acc["no_results"],
                points=acc["points"],
                net_run_rate=nrr,
                nrr_available=nrr_available,
                confidence=confidence,  # type: ignore[arg-type]
            )
        )

    # Sort by points desc, then NRR desc (None last), then team name
    rows.sort(
        key=lambda r: (
            -r.points,
            -(r.net_run_rate if r.net_run_rate is not None else float("-inf")),
            r.team_name,
        )
    )
    return rows


# ---------------------------------------------------------------------------
# Tournament summary
# ---------------------------------------------------------------------------


def _build_tournament_summary(
    group_key: TournamentGroupKey,
    group_games: list[EligibleGame],
    season_outcomes: list[SeasonOutcomeAggregate],
) -> TournamentSummaryResponse:
    """Build a full TournamentSummaryResponse for one tournament group."""

    if not group_games:
        return TournamentSummaryResponse(
            group_key=group_key,
            match_count=0,
            data_completeness=TournamentDataCompleteness(
                total_matches=0,
                matches_with_result=0,
                matches_missing_result=0,
                delivery_complete_matches=0,
                phase_level_matches=0,
                innings_totals_matches=0,
                metadata_only_matches=0,
            ),
        )

    # --- Basic counts ---
    teams_set: set[str] = set()
    venues_set: set[str] = set()
    total_runs = 0
    total_wickets = 0
    team_totals: list[tuple[int, str]] = []  # (runs, team) for highest/lowest
    match_margins_runs: list[tuple[int, str, str, str]] = []  # (margin, team, title, match_id)
    match_margins_wkts: list[tuple[int, str, str, str]] = []
    match_total_runs: list[tuple[int, str, str, str]] = []  # (total, teams_str, match_id, date)

    dc_delivery = 0
    dc_phase = 0
    dc_innings = 0
    dc_metadata = 0
    matches_with_result = 0

    for game, _batch, meta, match in group_games:
        ta = match.team_a or "Team A"
        tb = match.team_b or "Team B"
        teams_set.add(ta)
        teams_set.add(tb)
        if match.venue:
            venues_set.add(match.venue)
        elif meta.get("venue"):
            venues_set.add(str(meta["venue"]))

        # Completeness
        level = _completeness_level(game, meta)
        if level == "delivery_complete":
            dc_delivery += 1
        elif level == "phase_level":
            dc_phase += 1
        elif level == "innings_totals":
            dc_innings += 1
        else:
            dc_metadata += 1

        if game.result or match.winner_team:
            matches_with_result += 1

        # Runs from innings summary
        for inn in _innings_summary(game):
            runs = int(inn.get("runs") or 0)
            wkts = int(inn.get("wickets") or 0)
            team = str(inn.get("team") or "")
            total_runs += runs
            total_wickets += wkts
            if runs > 0 and team:
                team_totals.append((runs, team))

        # Match total for highlight detection
        match_title = f"{ta} vs {tb}"
        match_id = game.id
        match_date = match.match_date or ""
        m_total = sum(int(inn.get("runs") or 0) for inn in _innings_summary(game))
        if m_total > 0:
            match_total_runs.append((m_total, match_title, match_id, match_date))

        # Derive margin for win highlights (basic text parsing)
        result_text = game.result or ""
        runs_margin_m = re.search(r"won by (\d+) runs", result_text, re.I)
        wkts_margin_m = re.search(r"won by (\d+) wickets?", result_text, re.I)
        if runs_margin_m:
            margin_val = int(runs_margin_m.group(1))
            match_margins_runs.append((margin_val, match.winner_team or "", match_title, match_id))
        if wkts_margin_m:
            margin_val = int(wkts_margin_m.group(1))
            match_margins_wkts.append((margin_val, match.winner_team or "", match_title, match_id))

    # --- Build highlights ---
    biggest_win_runs: TournamentMatchHighlight | None = None
    biggest_win_wkts: TournamentMatchHighlight | None = None
    closest_match: TournamentMatchHighlight | None = None

    if match_margins_runs:
        biggest = max(match_margins_runs, key=lambda x: (x[0], x[3]))
        biggest_win_runs = TournamentMatchHighlight(
            match_id=biggest[3],
            match_title=biggest[2],
            result=f"Won by {biggest[0]} runs",
            highlight_type="biggest_win_runs",
            detail=f"{biggest[1]} won by {biggest[0]} runs",
        )
        if len(match_margins_runs) > 1:
            closest = min(match_margins_runs, key=lambda x: (x[0], x[3]))
            closest_match = TournamentMatchHighlight(
                match_id=closest[3],
                match_title=closest[2],
                result=f"Won by {closest[0]} runs",
                highlight_type="closest_match",
                detail=f"Closest finish: {closest[1]} won by {closest[0]} runs",
            )

    if match_margins_wkts:
        biggest_w = min(match_margins_wkts, key=lambda x: (x[0], x[3]))  # fewer wickets = closer
        biggest_win_wkts = TournamentMatchHighlight(
            match_id=biggest_w[3],
            match_title=biggest_w[2],
            result=f"Won by {biggest_w[0]} wicket(s)",
            highlight_type="biggest_win_wickets",
            detail=f"{biggest_w[1]} won by {biggest_w[0]} wicket(s)",
        )
        if closest_match is None and len(match_margins_wkts) > 0:
            closest_w = min(match_margins_wkts, key=lambda x: (x[0], x[3]))
            if closest_w[0] <= 2:
                closest_match = TournamentMatchHighlight(
                    match_id=closest_w[3],
                    match_title=closest_w[2],
                    result=f"Won by {closest_w[0]} wicket(s)",
                    highlight_type="closest_match",
                    detail=f"Narrow finish: {closest_w[1]} won by {closest_w[0]} wicket(s)",
                )

    # --- Highest/lowest team totals ---
    highest_total: int | None = None
    highest_total_by: str | None = None
    lowest_total: int | None = None
    lowest_total_by: str | None = None

    if team_totals:
        high_entry = max(team_totals, key=lambda x: (x[0], x[1]))
        highest_total = high_entry[0]
        highest_total_by = high_entry[1]
        # Lowest completed: >0 (avoid DNB)
        completed = [t for t in team_totals if t[0] >= 20]
        if completed:
            low_entry = min(completed, key=lambda x: (x[0], x[1]))
            lowest_total = low_entry[0]
            lowest_total_by = low_entry[1]

    # --- Derived standings ---
    derived_standings = _build_derived_standings(group_games)

    # --- Knockout context ---
    knockout_ctx = _build_knockout_context(group_games, season_outcomes, group_key)

    # --- Player leaders from scorecard data ---
    top_run_scorer: TournamentPlayerLeader | None = None
    top_wicket_taker: TournamentPlayerLeader | None = None

    batting_acc: dict[str, dict[str, Any]] = defaultdict(lambda: {"runs": 0, "matches": 0})
    bowling_acc: dict[str, dict[str, Any]] = defaultdict(lambda: {"wickets": 0, "matches": 0})
    for game, _batch, meta, _match in group_games:
        if meta.get("deliveries_imported") or (
            isinstance(game.deliveries, list) and len(game.deliveries) > 0
        ):
            for player, stats in (game.batting_scorecard or {}).items():
                if isinstance(stats, dict):
                    batting_acc[str(player)]["runs"] += int(stats.get("runs") or 0)
                    batting_acc[str(player)]["matches"] += 1
            for player, stats in (game.bowling_scorecard or {}).items():
                if isinstance(stats, dict):
                    bowling_acc[str(player)]["wickets"] += int(
                        stats.get("wickets_taken") or stats.get("wickets") or 0
                    )
                    bowling_acc[str(player)]["matches"] += 1

    if batting_acc:
        top_bat = max(batting_acc.items(), key=lambda x: (-x[1]["runs"], x[0]))
        if top_bat[1]["runs"] > 0:
            top_run_scorer = TournamentPlayerLeader(
                player_name=top_bat[0],
                value=top_bat[1]["runs"],
                matches_contributed=top_bat[1]["matches"],
                stat_type="runs",
                confidence="medium",
            )
    if bowling_acc:
        top_bowl = max(bowling_acc.items(), key=lambda x: (-x[1]["wickets"], x[0]))
        if top_bowl[1]["wickets"] > 0:
            top_wicket_taker = TournamentPlayerLeader(
                player_name=top_bowl[0],
                value=top_bowl[1]["wickets"],
                matches_contributed=top_bowl[1]["matches"],
                stat_type="wickets",
                confidence="medium",
            )

    # --- Data completeness ---
    missing_result = len(group_games) - matches_with_result
    confidence_level: str
    if dc_delivery > len(group_games) // 2:
        confidence_level = "high"
    elif (
        dc_delivery + dc_phase > len(group_games) // 2
        or matches_with_result > len(group_games) // 2
    ):
        confidence_level = "medium"
    else:
        confidence_level = "low"

    data_completeness = TournamentDataCompleteness(
        total_matches=len(group_games),
        matches_with_result=matches_with_result,
        matches_missing_result=missing_result,
        delivery_complete_matches=dc_delivery,
        phase_level_matches=dc_phase,
        innings_totals_matches=dc_innings,
        metadata_only_matches=dc_metadata,
        confidence_level=confidence_level,  # type: ignore[arg-type]
        note=(
            f"{dc_delivery} delivery-complete, {dc_phase} phase-level, "
            f"{dc_innings} innings-totals, {dc_metadata} metadata-only."
        ),
    )

    # --- Podcast facts ---
    podcast_facts = _build_podcast_facts(
        group_key=group_key,
        derived_standings=derived_standings,
        knockout_ctx=knockout_ctx,
        top_run_scorer=top_run_scorer,
        match_total_runs=match_total_runs,
        venues=list(venues_set),
        group_games=group_games,
    )

    return TournamentSummaryResponse(
        group_key=group_key,
        match_count=len(group_games),
        teams=sorted(teams_set),
        venues=sorted(venues_set),
        total_runs=total_runs,
        total_wickets=total_wickets,
        highest_team_total=highest_total,
        highest_team_total_by=highest_total_by,
        lowest_completed_total=lowest_total,
        lowest_completed_total_by=lowest_total_by,
        closest_match=closest_match,
        biggest_win_by_runs=biggest_win_runs,
        biggest_win_by_wickets=biggest_win_wkts,
        top_run_scorer=top_run_scorer,
        top_wicket_taker=top_wicket_taker,
        derived_standings=derived_standings,
        knockout_context=knockout_ctx,
        data_completeness=data_completeness,
        podcast_facts=podcast_facts,
    )


def _build_knockout_context(
    group_games: list[EligibleGame],
    season_outcomes: list[SeasonOutcomeAggregate],
    group_key: TournamentGroupKey,
) -> TournamentKnockoutContext:
    """Build knockout/finals context from stage labels and existing season outcomes."""

    # First, look for a matching SeasonOutcomeAggregate (from Phase 10O/10S)
    for outcome in season_outcomes:
        if (
            outcome.competition_code == group_key.competition_code
            and outcome.season == group_key.season
            and outcome.gender_category == group_key.gender_category
        ):
            outcome_semi_finals = [
                TournamentMatchHighlight(
                    match_id=m.match_id,
                    match_title=m.match_title,
                    match_date=m.match_date,
                    stage_label=m.stage_label,
                    result=m.result,
                    highlight_type="semi_final",
                )
                for m in outcome.playoff_stage_matches_detected
                if m.stage_label in ("Semi Final", "Eliminator")
            ]
            outcome_qualifiers = [
                TournamentMatchHighlight(
                    match_id=m.match_id,
                    match_title=m.match_title,
                    match_date=m.match_date,
                    stage_label=m.stage_label,
                    result=m.result,
                    highlight_type="qualifier",
                )
                for m in outcome.playoff_stage_matches_detected
                if m.stage_label in ("Qualifier", "Playoff")
            ]
            return TournamentKnockoutContext(
                champion_team=outcome.champion_team_raw,
                champion_team_canonical=outcome.champion_team_canonical,
                runner_up_team=outcome.runner_up_team_raw,
                runner_up_team_canonical=outcome.runner_up_team_canonical,
                final_match_id=outcome.final_match_id,
                final_match_title=outcome.final_match_title,
                final_match_date=outcome.final_match_date,
                final_result=outcome.final_result,
                semi_final_matches=outcome_semi_finals,
                qualifier_matches=outcome_qualifiers,
                outcome_source=outcome.outcome_source,
                confidence=outcome.confidence,
            )

    # Fallback: scan group games for stage labels
    semi_finals: list[TournamentMatchHighlight] = []
    qualifiers: list[TournamentMatchHighlight] = []
    final_candidates: list[EligibleGame] = []

    for entry in group_games:
        game, _batch, meta, match = entry
        ta = match.team_a or "Team A"
        tb = match.team_b or "Team B"
        match_title = f"{ta} vs {tb}"
        stage_label = _detect_stage_label(meta, match_title)
        if not stage_label:
            continue
        hl = TournamentMatchHighlight(
            match_id=game.id,
            match_title=match_title,
            match_date=match.match_date,
            stage_label=stage_label,
            result=game.result,
            highlight_type=stage_label.lower().replace(" ", "_"),
        )
        if _is_final_stage(stage_label):
            final_candidates.append(entry)
        elif stage_label in ("Semi Final", "Eliminator"):
            semi_finals.append(hl)
        elif stage_label in ("Qualifier", "Playoff"):
            qualifiers.append(hl)

    if not final_candidates:
        return TournamentKnockoutContext(
            outcome_source="final_not_detected",
            semi_final_matches=semi_finals,
            qualifier_matches=qualifiers,
        )

    # Use first (or only) final candidate
    final_entry = final_candidates[0]
    f_game, _f_batch, _f_meta, f_match = final_entry
    champion = f_match.winner_team
    champion_canonical = f_match.winner_team_canonical

    runner_up: str | None = None
    runner_up_canonical: str | None = None
    if champion:
        ta_c = f_match.team_a_canonical or f_match.team_a
        tb_c = f_match.team_b_canonical or f_match.team_b
        if champion_canonical == ta_c:
            runner_up = f_match.team_b
            runner_up_canonical = f_match.team_b_canonical or f_match.team_b
        elif champion_canonical == tb_c:
            runner_up = f_match.team_a
            runner_up_canonical = f_match.team_a_canonical or f_match.team_a

    return TournamentKnockoutContext(
        champion_team=champion,
        champion_team_canonical=champion_canonical,
        runner_up_team=runner_up,
        runner_up_team_canonical=runner_up_canonical,
        final_match_id=f_game.id,
        final_match_title=f"{f_match.team_a or 'Team A'} vs {f_match.team_b or 'Team B'}",
        final_match_date=f_match.match_date,
        final_result=f_game.result,
        semi_final_matches=semi_finals,
        qualifier_matches=qualifiers,
        outcome_source="detected_final_result" if champion else "final_without_parsed_winner",
        confidence="high" if f_match.winner_confidence == "high" else "medium",
    )


def _build_podcast_facts(
    group_key: TournamentGroupKey,
    derived_standings: list[DerivedStandingsRow],
    knockout_ctx: TournamentKnockoutContext,
    top_run_scorer: TournamentPlayerLeader | None,
    match_total_runs: list[tuple[int, str, str, str]],
    venues: list[str],
    group_games: list[EligibleGame],
) -> TournamentPodcastFacts:
    """Build deterministic podcast talking-point facts."""

    season_label = group_key.season
    competition_label = group_key.competition_name or group_key.competition_code

    champion = knockout_ctx.champion_team_canonical or knockout_ctx.champion_team
    finalist = knockout_ctx.runner_up_team_canonical or knockout_ctx.runner_up_team

    strongest_by_wins: str | None = None
    if derived_standings:
        leader = derived_standings[0]
        if leader.wins > 0:
            strongest_by_wins = leader.canonical_team_name or leader.team_name

    highest_match_title: str | None = None
    highest_match_total: int | None = None
    if match_total_runs:
        top_match = max(match_total_runs, key=lambda x: (x[0], x[2]))
        highest_match_title = top_match[1]
        highest_match_total = top_match[0]

    # Top scoring venue: count runs by venue
    venue_runs: dict[str, int] = defaultdict(int)
    for game, _batch, meta, match in group_games:
        venue_key = match.venue or (str(meta.get("venue") or "")).strip() or None
        if not venue_key:
            continue
        m_runs = sum(int(inn.get("runs") or 0) for inn in _innings_summary(game))
        venue_runs[venue_key] += m_runs

    top_venue: str | None = None
    if venue_runs:
        top_venue = max(venue_runs.items(), key=lambda x: (x[1], x[0]))[0]

    key_note: str | None = None
    if champion and finalist:
        key_note = f"{champion} defeated {finalist} to claim the title."
    elif champion:
        key_note = f"{champion} were detected as champions from the final match."
    elif strongest_by_wins:
        key_note = f"{strongest_by_wins} led on wins in the derived standings."

    confidence = knockout_ctx.confidence if champion else "low"

    return TournamentPodcastFacts(
        competition_label=competition_label,
        season_label=season_label,
        champion=champion,
        finalist=finalist,
        strongest_team_by_wins=strongest_by_wins,
        top_scoring_venue=top_venue,
        highest_scoring_match_title=highest_match_title,
        highest_match_total_runs=highest_match_total,
        key_journey_note=key_note,
        confidence=confidence,  # type: ignore[arg-type]
        source_label="derived from imported match data — not official",
    )


# ---------------------------------------------------------------------------
# Team journey
# ---------------------------------------------------------------------------


def _build_team_journey(
    team_name: str,
    group_key: TournamentGroupKey,
    group_games: list[EligibleGame],
) -> TeamJourneyResponse:
    """Build a team-specific journey view within a tournament group."""

    canonical_team, _ = canonicalize_team_name(team_name)

    journey_matches: list[TeamJourneyMatch] = []

    total_runs_for = 0
    total_runs_against = 0
    wins = 0
    losses = 0
    ties = 0
    no_results = 0

    batting_acc: dict[str, int] = defaultdict(int)

    for game, _batch, meta, match in group_games:
        ta = match.team_a or "Team A"
        tb = match.team_b or "Team B"
        ta_c = match.team_a_canonical or ta
        tb_c = match.team_b_canonical or tb

        team_lower = team_name.lower()
        team_is_a = team_lower in ta.lower() or team_lower in ta_c.lower()
        team_is_b = team_lower in tb.lower() or team_lower in tb_c.lower()

        if not team_is_a and not team_is_b:
            continue

        opponent = tb if team_is_a else ta
        venue = match.venue or (str(meta.get("venue") or "")).strip() or None
        stage_label = _detect_stage_label(meta, f"{ta} vs {tb}")

        # Determine outcome
        outcome_str = _derive_outcome(game.result, team_name)

        team_runs: int | None = None
        opp_runs: int | None = None
        innings_list = _innings_summary(game)
        for inn in innings_list:
            inn_team = str(inn.get("team") or "")
            runs_val = int(inn.get("runs") or 0)
            if team_lower in inn_team.lower():
                team_runs = runs_val
                total_runs_for += runs_val
            elif inn_team:
                opp_runs = runs_val
                total_runs_against += runs_val

        if outcome_str == "win":
            wins += 1
        elif outcome_str == "loss":
            losses += 1
        elif outcome_str == "tie":
            ties += 1
        elif outcome_str == "no_result":
            no_results += 1

        # Batting scorecard aggregation
        if meta.get("deliveries_imported") or (
            isinstance(game.deliveries, list) and len(game.deliveries) > 0
        ):
            for player, stats in (game.batting_scorecard or {}).items():
                if isinstance(stats, dict):
                    batting_acc[str(player)] += int(stats.get("runs") or 0)

        margin_note: str | None = None
        if game.result:
            m = re.search(r"won by (\d+ (?:runs?|wickets?))", game.result, re.I)
            if m:
                margin_note = (
                    f"Won by {m.group(1)}" if outcome_str == "win" else f"Lost ({m.group(0)})"
                )

        journey_matches.append(
            TeamJourneyMatch(
                match_id=game.id,
                match_title=f"{ta} vs {tb}",
                match_date=match.match_date,
                opponent=opponent,
                venue=venue,
                result=game.result,
                outcome=outcome_str,  # type: ignore[arg-type]
                team_runs=team_runs,
                opponent_runs=opp_runs,
                stage_label=stage_label,
                highlight=margin_note,
            )
        )

    # Sort chronologically
    journey_matches.sort(key=lambda m: (m.match_date or "", m.match_id))

    # Best win / worst defeat / closest match
    wins_list = [m for m in journey_matches if m.outcome == "win"]
    losses_list = [m for m in journey_matches if m.outcome == "loss"]

    best_win: TeamJourneyMatch | None = None
    if wins_list:
        # Best win = largest runs margin or wins at knockout stage
        stage_wins = [m for m in wins_list if m.stage_label in ("Final", "Semi Final")]
        best_win = stage_wins[0] if stage_wins else wins_list[0]

    worst_defeat: TeamJourneyMatch | None = None
    if losses_list:
        worst_defeat = losses_list[-1]  # last loss in time order

    closest_m: TeamJourneyMatch | None = None
    all_decided = [m for m in journey_matches if m.outcome in ("win", "loss")]
    if all_decided:
        # Closest = smallest absolute runs difference (approximate)
        def _run_diff(jm: TeamJourneyMatch) -> int:
            if jm.team_runs is not None and jm.opponent_runs is not None:
                return abs(jm.team_runs - jm.opponent_runs)
            return 9999

        closest_m = min(all_decided, key=_run_diff)

    # Top scorer
    top_scorer_name: str | None = None
    top_scorer_runs: int | None = None
    if batting_acc:
        top = max(batting_acc.items(), key=lambda x: (-x[1], x[0]))
        if top[1] > 0:
            top_scorer_name = top[0]
            top_scorer_runs = top[1]

    summary = TeamJourneySummary(
        wins=wins,
        losses=losses,
        ties=ties,
        no_results=no_results,
        total_runs_for=total_runs_for,
        total_runs_against=total_runs_against,
        best_win=best_win,
        worst_defeat=worst_defeat,
        closest_match=closest_m,
        top_scorer_name=top_scorer_name,
        top_scorer_runs=top_scorer_runs,
    )

    total = wins + losses + ties + no_results
    dc = TournamentDataCompleteness(
        total_matches=total,
        matches_with_result=wins + losses + ties,
        matches_missing_result=no_results,
        delivery_complete_matches=0,
        phase_level_matches=0,
        innings_totals_matches=total,
        metadata_only_matches=0,
    )

    return TeamJourneyResponse(
        team_name=team_name,
        canonical_team_name=canonical_team,
        group_key=group_key,
        matches=journey_matches,
        summary=summary,
        data_completeness=dc,
    )


# ---------------------------------------------------------------------------
# Phase 10S.2 — Tournament Podcast Rundown builder
# ---------------------------------------------------------------------------


def _build_season_review(
    group_key: TournamentGroupKey,
    knockout_ctx: TournamentKnockoutContext,
    derived_standings: list[DerivedStandingsRow],
    match_count: int,
    data_completeness: TournamentDataCompleteness,
) -> TournamentSeasonReview:
    """Build a presenter-ready season review narrative from deterministic facts."""

    comp = group_key.competition_name or group_key.competition_code
    season = group_key.season or "unknown season"
    champion = knockout_ctx.champion_team_canonical or knockout_ctx.champion_team
    finalist = knockout_ctx.runner_up_team_canonical or knockout_ctx.runner_up_team
    confidence = data_completeness.confidence_level

    if champion and finalist and knockout_ctx.final_result:
        narrative = (
            f"The {season} {comp} season ended with {champion} lifting the title "
            f"after the final against {finalist}. "
            f"Final result (derived): {knockout_ctx.final_result}. "
        )
    elif champion and finalist:
        narrative = (
            f"The {season} {comp} season concluded with {champion} detected as champions "
            f"and {finalist} as runners-up based on imported match data. "
        )
    elif champion:
        narrative = (
            f"The {season} {comp} season concluded with {champion} detected as champions "
            f"from the final match. "
        )
    else:
        narrative = (
            f"The {season} {comp} season featured {_pluralize(match_count, 'imported match', 'imported matches')}. "
            f"No champion data was detected from the available match results. "
        )

    if derived_standings:
        leader = derived_standings[0]
        leader_name = leader.canonical_team_name or leader.team_name
        narrative += (
            f"In the derived standings (estimated, not official), "
            f"{leader_name} led with {_pluralize(leader.wins, 'win')} from {_pluralize(leader.played, 'match', 'matches')}. "
        )

    narrative += (
        "These derived standings are estimated from imported match results "
        "and are not official standings."
    )

    return TournamentSeasonReview(
        competition_label=comp,
        season_label=season,
        narrative=narrative,
        confidence=confidence,  # type: ignore[arg-type]
        source_label="derived from imported match data — not official",
    )


def _build_champion_journey(
    knockout_ctx: TournamentKnockoutContext,
    derived_standings: list[DerivedStandingsRow],
    summary: TournamentSummaryResponse,
) -> TournamentChampionJourney | None:
    """Build the champion journey block when champion data exists."""

    champion = knockout_ctx.champion_team_canonical or knockout_ctx.champion_team
    if not champion:
        return None

    finalist = knockout_ctx.runner_up_team_canonical or knockout_ctx.runner_up_team
    final_result = knockout_ctx.final_result

    # Derived group standing for champion
    derived_standing: str | None = None
    if derived_standings:
        for i, row in enumerate(derived_standings):
            row_name = row.canonical_team_name or row.team_name
            if row_name and champion.lower() in row_name.lower():
                ordinal = ["1st", "2nd", "3rd"][i] if i < 3 else f"{i + 1}th"
                derived_standing = (
                    f"{ordinal} in derived standings "
                    f"({row.wins}W / {row.losses}L — estimated, not official)"
                )
                break

    # Best win and closest match from summary
    best_win_title: str | None = None
    if summary.biggest_win_by_runs and summary.biggest_win_by_runs.detail:
        best_win_title = summary.biggest_win_by_runs.match_title
    elif summary.biggest_win_by_wickets and summary.biggest_win_by_wickets.detail:
        best_win_title = summary.biggest_win_by_wickets.match_title

    closest_title: str | None = None
    if summary.closest_match:
        closest_title = summary.closest_match.match_title

    # Key note
    if champion and finalist and final_result:
        key_note = f"{champion} defeated {finalist} to claim the title. Result: {final_result}."
    elif champion and finalist:
        key_note = (
            f"{champion} were detected as champions; {finalist} were the detected runners-up."
        )
    else:
        key_note = f"{champion} were detected as champions from the final match."

    return TournamentChampionJourney(
        champion_team=champion,
        final_opponent=finalist,
        final_result=final_result,
        derived_group_standing=derived_standing,
        best_win_title=best_win_title,
        closest_match_title=closest_title,
        key_note=key_note,
        confidence=knockout_ctx.confidence,
        source_label="derived from imported match data — not official",
    )


def _build_road_to_final(
    knockout_ctx: TournamentKnockoutContext,
) -> TournamentRoadToFinal | None:
    """Build the road-to-final block when finalist context exists."""

    champion = knockout_ctx.champion_team_canonical or knockout_ctx.champion_team
    finalist = knockout_ctx.runner_up_team_canonical or knockout_ctx.runner_up_team

    if not champion and not finalist:
        return None

    semi_titles = [m.match_title for m in knockout_ctx.semi_final_matches if m.match_title]
    qualifier_titles = [m.match_title for m in knockout_ctx.qualifier_matches if m.match_title]

    if champion and finalist and knockout_ctx.final_result:
        narrative = (
            f"{champion} met {finalist} in the final. "
            f"Detected result: {knockout_ctx.final_result}."
        )
    elif champion and finalist:
        narrative = (
            f"{champion} and {finalist} were detected as finalists. "
            "No final result text was found in the imported data."
        )
    elif champion:
        narrative = f"{champion} were detected as champions from the final match."
    else:
        narrative = "Finalist data could not be determined from the imported match data."

    if semi_titles:
        narrative += (
            f" Possible knockout-stage matches detected (semi-final or eliminator stage label): "
            f"{', '.join(semi_titles)}."
        )
    if qualifier_titles:
        narrative += (
            f" Possible knockout-stage matches detected (qualifier or playoff stage label): "
            f"{', '.join(qualifier_titles)}."
        )

    return TournamentRoadToFinal(
        finalist_a=champion,
        finalist_b=finalist,
        final_result=knockout_ctx.final_result,
        semi_final_titles=semi_titles,
        qualifier_titles=qualifier_titles,
        narrative=narrative,
        confidence=knockout_ctx.confidence,
        source_label="derived from imported match data — not official",
    )


def _build_rundown_sections(
    group_key: TournamentGroupKey,
    summary: TournamentSummaryResponse,
    champion_journey: TournamentChampionJourney | None,
    road_to_final: TournamentRoadToFinal | None,
    season_review: TournamentSeasonReview,
) -> list[TournamentPodcastSection]:
    """Build ordered podcast rundown sections from tournament summary."""

    comp = group_key.competition_name or group_key.competition_code
    season = group_key.season or "unknown season"
    confidence = summary.data_completeness.confidence_level
    champion = (
        summary.knockout_context.champion_team_canonical or summary.knockout_context.champion_team
    )
    finalist = (
        summary.knockout_context.runner_up_team_canonical or summary.knockout_context.runner_up_team
    )
    sections: list[TournamentPodcastSection] = []

    # 1. Opening hook
    if champion:
        hook_body = (
            f"Welcome to the {comp} {season} season review. "
            f"This season ended with {champion} lifting the title. "
            "All facts are derived from imported match data — not official records."
        )
    else:
        hook_body = (
            f"Welcome to the {comp} {season} season review. "
            f"This season featured {_pluralize(summary.match_count, 'imported match', 'imported matches')}. "
            "All facts are derived from imported match data — not official records."
        )
    sections.append(
        TournamentPodcastSection(
            section_key="opening_hook",
            title="Opening Hook",
            body=hook_body,
            confidence=confidence,  # type: ignore[arg-type]
        )
    )

    # 2. Tournament setup
    n_teams = len(summary.teams)
    n_venues = len(summary.venues)
    venues_listed = "; ".join(sorted(summary.venues)[:3]) if summary.venues else None
    setup_lines = [
        f"The {season} {comp} featured {_pluralize(summary.match_count, 'imported match', 'imported matches')}.",
        f"Teams ({n_teams}): {', '.join(sorted(summary.teams)[:6])}."
        if summary.teams
        else "Team data unavailable.",
    ]
    if venues_listed:
        if n_venues > 3:
            setup_lines.append(f"Venues ({n_venues} total, top 3 listed): {venues_listed}.")
        else:
            setup_lines.append(f"{_pluralize(n_venues, 'Venue')}: {venues_listed}.")
    else:
        setup_lines.append("Venue data unavailable.")
    setup_body = " ".join(setup_lines)
    sections.append(
        TournamentPodcastSection(
            section_key="tournament_setup",
            title="Tournament Setup",
            body=setup_body,
            confidence=confidence,  # type: ignore[arg-type]
        )
    )

    # 3. Champion story
    if champion_journey and champion_journey.champion_team:
        champ_body = f"Champion (detected): {champion_journey.champion_team}."
        if champion_journey.final_opponent:
            champ_body += f" They defeated {champion_journey.final_opponent} in the final."
        if champion_journey.final_result:
            champ_body += f" Final result: {champion_journey.final_result}."
        if champion_journey.derived_group_standing:
            champ_body += f" {champion_journey.derived_group_standing}."
        champ_body += (
            " Note: champion detection is derived from stage labels and result text — "
            "not from official records."
        )
        champ_confidence = champion_journey.confidence
    else:
        champ_body = (
            "No champion data was detected from the available imported match data. "
            "This may mean the tournament final was not included in the import, "
            "or stage labels were not present."
        )
        champ_confidence = "unknown"
    sections.append(
        TournamentPodcastSection(
            section_key="champion_story",
            title="Champion Story",
            body=champ_body,
            confidence=champ_confidence,  # type: ignore[arg-type]
        )
    )

    # 4. Final match context
    if road_to_final and road_to_final.narrative:
        final_body = road_to_final.narrative
        final_confidence = road_to_final.confidence
    else:
        final_body = (
            "Final match context could not be determined from the imported data. "
            "No final stage label was detected."
        )
        final_confidence = "unknown"
    sections.append(
        TournamentPodcastSection(
            section_key="final_context",
            title="Final Match Context",
            body=final_body,
            confidence=final_confidence,  # type: ignore[arg-type]
        )
    )

    # 5. Standings / group-stage story
    standings_body: str
    if summary.derived_standings:
        top3 = summary.derived_standings[:3]
        rows_str = "; ".join(
            f"{row.canonical_team_name or row.team_name} "
            f"({row.wins}W/{row.losses}L, {row.points}pts)"
            for row in top3
        )
        standings_body = (
            f"Derived standings (top 3, estimated — not official): {rows_str}. "
            "Points: 2 per win, 1 per tie/no-result, 0 per loss. "
            "These are estimated from imported match results, not official standings."
        )
    else:
        standings_body = (
            "Derived standings are unavailable for this tournament. "
            "Insufficient result data was found in the imported matches."
        )
    sections.append(
        TournamentPodcastSection(
            section_key="standings_story",
            title="Standings / Group-Stage Story",
            body=standings_body,
            confidence=confidence,  # type: ignore[arg-type]
        )
    )

    # 6. Team journey spotlight (top team by wins if available)
    if summary.derived_standings:
        spotlight_team = (
            summary.derived_standings[0].canonical_team_name
            or summary.derived_standings[0].team_name
        )
        spotlight_row = summary.derived_standings[0]
        spotlight_body = (
            f"Team spotlight: {spotlight_team} led the derived standings "
            f"with {_pluralize(spotlight_row.wins, 'win')} from {_pluralize(spotlight_row.played, 'match', 'matches')}. "
            "Use the Team Journey tab to view their full campaign match-by-match."
        )
    else:
        spotlight_body = "No team journey spotlight available — insufficient standings data."
    sections.append(
        TournamentPodcastSection(
            section_key="team_spotlight",
            title="Team Journey Spotlight",
            body=spotlight_body,
            confidence=confidence,  # type: ignore[arg-type]
        )
    )

    # 7. Key matches
    key_lines: list[str] = []
    if summary.biggest_win_by_runs and summary.biggest_win_by_runs.detail:
        key_lines.append(
            f"Biggest win (runs): {summary.biggest_win_by_runs.detail} "
            f"({summary.biggest_win_by_runs.match_title})."
        )
    if summary.biggest_win_by_wickets and summary.biggest_win_by_wickets.detail:
        key_lines.append(
            f"Biggest win (wickets): {summary.biggest_win_by_wickets.detail} "
            f"({summary.biggest_win_by_wickets.match_title})."
        )
    if summary.closest_match and summary.closest_match.detail:
        key_lines.append(
            f"Closest finish: {summary.closest_match.detail} "
            f"({summary.closest_match.match_title})."
        )
    key_body = "\n".join(key_lines) if key_lines else "No key match highlights available."
    sections.append(
        TournamentPodcastSection(
            section_key="key_matches",
            title="Key Matches",
            body=key_body,
            confidence=confidence,  # type: ignore[arg-type]
        )
    )

    # 8. Player storylines
    player_lines: list[str] = []
    if summary.top_run_scorer and summary.top_run_scorer.value > 0:
        player_lines.append(
            f"Top run scorer (derived): {summary.top_run_scorer.player_name} "
            f"— {int(summary.top_run_scorer.value)} runs from "
            f"{_pluralize(summary.top_run_scorer.matches_contributed, 'match', 'matches')}."
        )
    if summary.top_wicket_taker and summary.top_wicket_taker.value > 0:
        player_lines.append(
            f"Top wicket taker (derived): {summary.top_wicket_taker.player_name} "
            f"— {int(summary.top_wicket_taker.value)} wickets from "
            f"{_pluralize(summary.top_wicket_taker.matches_contributed, 'match', 'matches')}."
        )
    if player_lines:
        player_body = " ".join(player_lines)
        player_body += (
            " Note: player stats are derived from scorecard/delivery data "
            "only where available — not official."
        )
        player_confidence = "medium"
    else:
        player_body = (
            "Player leaderboards are unavailable because player-level scorecard or "
            "delivery-player data was not found in the imported tournament records. "
            "Confidence: unknown."
        )
        player_confidence = "unknown"
    sections.append(
        TournamentPodcastSection(
            section_key="player_storylines",
            title="Top Player Storylines",
            body=player_body,
            confidence=player_confidence,  # type: ignore[arg-type]
        )
    )

    # 9. Venue / scoring patterns
    if summary.venues and summary.total_runs > 0:
        avg_per_match = summary.total_runs // summary.match_count if summary.match_count else 0
        podcast_facts = summary.podcast_facts
        top_venue_str = (
            f" Top scoring venue: {podcast_facts.top_scoring_venue}."
            if podcast_facts and podcast_facts.top_scoring_venue
            else ""
        )
        highest_total_str = (
            f" Highest team total: {summary.highest_team_total} "
            f"({summary.highest_team_total_by})."
            if summary.highest_team_total and summary.highest_team_total_by
            else ""
        )
        wickets_str = (
            f"{summary.total_wickets} wickets"
            if summary.total_wickets > 0
            else "wicket data unavailable from imported records"
        )
        venue_body = (
            f"Tournament scoring: {summary.total_runs} total runs, "
            f"{wickets_str} across {_pluralize(summary.match_count, 'match', 'matches')}. "
            f"Average match total: ~{avg_per_match} runs."
            f"{top_venue_str}{highest_total_str}"
        )
    else:
        venue_body = "Venue and scoring pattern data is unavailable for this tournament."
    sections.append(
        TournamentPodcastSection(
            section_key="venue_patterns",
            title="Venue & Scoring Patterns",
            body=venue_body,
            confidence=confidence,  # type: ignore[arg-type]
        )
    )

    # 10. Tactical themes (high-level observation from derived data)
    format_family = group_key.format_family or "unknown"
    if summary.total_wickets > 0:
        wickets_label = f"{summary.total_wickets} total wickets"
    else:
        wickets_label = "wicket totals unavailable for this tournament import"
    tactical_body = (
        f"Format: {format_family}. "
        f"This tournament produced {summary.total_runs} total runs "
        f"and {wickets_label}. "
    )
    if summary.total_wickets > 0 and summary.total_runs > 0:
        run_rate_per_wkt = round(summary.total_runs / summary.total_wickets, 1)
        tactical_body += f"Average runs per wicket (derived): {run_rate_per_wkt}. "
    tactical_body += (
        "Tactical analysis is derived from match result and scoring data only. "
        "Deeper tactical insights require ball-by-ball delivery data."
    )
    sections.append(
        TournamentPodcastSection(
            section_key="tactical_themes",
            title="Tactical Themes",
            body=tactical_body,
            confidence=confidence,  # type: ignore[arg-type]
        )
    )

    # 11. Debate questions
    debate_lines: list[str] = []
    if champion and finalist:
        debate_lines.append(
            f"Did {champion} truly deserve the title, "
            f"or did {finalist} underperform in the final?"
        )
    if summary.derived_standings:
        top_team = (
            summary.derived_standings[0].canonical_team_name
            or summary.derived_standings[0].team_name
        )
        debate_lines.append(
            f"Were {top_team}'s derived standings a fair reflection of their season?"
        )
    if summary.top_run_scorer:
        debate_lines.append(
            f"Was {summary.top_run_scorer.player_name} the standout performer of the season?"
        )
    debate_lines.append("How reliable are these derived standings without official data?")

    debate_body = "\n".join(f"- {line}" for line in debate_lines)
    sections.append(
        TournamentPodcastSection(
            section_key="debate_questions",
            title="Debate Questions",
            body=debate_body,
            confidence=confidence,  # type: ignore[arg-type]
        )
    )

    # 12. Data trust note
    dc = summary.data_completeness
    trust_body = (
        f"Data trust: {dc.confidence_level} confidence. "
        f"{dc.matches_with_result}/{dc.total_matches} matches have result data. "
        f"{dc.delivery_complete_matches} matches have ball-by-ball delivery data. "
        "All standings and outcomes are derived from imported match data — not official. "
        "Source: validated historical imports only."
    )
    sections.append(
        TournamentPodcastSection(
            section_key="data_trust_note",
            title="Data Trust Note",
            body=trust_body,
            confidence=confidence,  # type: ignore[arg-type]
            note="Required trust/provenance note for all podcast outputs.",
        )
    )

    return sections


def build_tournament_podcast_rundown(
    summary: TournamentSummaryResponse,
) -> TournamentPodcastRundown:
    """Build a full tournament podcast rundown from a TournamentSummaryResponse.

    Phase 10S.2: deterministic, presenter-ready tournament narrative sections.
    Derives all content from the existing summary. No LLM/AI calls are made.
    """

    group_key = summary.group_key
    knockout_ctx = summary.knockout_context

    # Season review
    season_review = _build_season_review(
        group_key=group_key,
        knockout_ctx=knockout_ctx,
        derived_standings=summary.derived_standings,
        match_count=summary.match_count,
        data_completeness=summary.data_completeness,
    )

    # Champion journey
    champion_journey = _build_champion_journey(
        knockout_ctx=knockout_ctx,
        derived_standings=summary.derived_standings,
        summary=summary,
    )

    # Road to final
    road_to_final = _build_road_to_final(knockout_ctx=knockout_ctx)

    # Ordered sections
    sections = _build_rundown_sections(
        group_key=group_key,
        summary=summary,
        champion_journey=champion_journey,
        road_to_final=road_to_final,
        season_review=season_review,
    )

    overall_confidence = summary.data_completeness.confidence_level

    return TournamentPodcastRundown(
        group_key=group_key,
        season_review=season_review,
        champion_journey=champion_journey,
        road_to_final=road_to_final,
        sections=sections,
        overall_confidence=overall_confidence,  # type: ignore[arg-type]
        source_label=(
            "Source: derived from imported match data. "
            "Derived standings are estimated and not official."
        ),
    )


async def _fetch_eligible_games(
    db: AsyncSession,
    current_user: Any,
) -> list[tuple[Game, HistoricalImportBatch, dict[str, Any]]]:
    """Fetch and filter eligible historical games from DB."""
    from backend.services.analyst_access import scoped_games_stmt

    stmt = (
        scoped_games_stmt(current_user)
        .where(Game.status == GameStatus.completed)
        .order_by(Game.id.desc())
    )
    result = await db.execute(stmt)
    all_completed = result.scalars().all()

    batch_id_to_game: dict[str, tuple[Game, dict[str, Any]]] = {}
    for game in all_completed:
        meta = _hist_meta(game)
        if not isinstance(meta, dict):
            continue
        batch_id = meta.get("batch_id")
        if not batch_id:
            continue
        batch_id_to_game[str(batch_id)] = (game, meta)

    batches: dict[str, HistoricalImportBatch] = {}
    if batch_id_to_game:
        batch_stmt = select(HistoricalImportBatch).where(
            HistoricalImportBatch.id.in_(list(batch_id_to_game.keys()))
        )
        batch_result = await db.execute(batch_stmt)
        for batch in batch_result.scalars().all():
            batches[batch.id] = batch

    eligible: list[tuple[Game, HistoricalImportBatch, dict[str, Any]]] = []
    for batch_id, (game, meta) in batch_id_to_game.items():
        batch = batches.get(batch_id)
        if batch is None or not _is_eligible(batch):
            continue
        eligible.append((game, batch, meta))

    return eligible


async def get_tournament_groups(
    db: AsyncSession,
    current_user: Any,
) -> TournamentGroupsResponse:
    """Return all discoverable tournament/season groups from the match registry.

    Phase 10S.1: read-only, deterministic. Requires analyst_pro or org_pro role.
    """
    from backend.services.historical_stats_aggregation_service import _build_match_aggregate

    raw_games = await _fetch_eligible_games(db, current_user)
    if not raw_games:
        return TournamentGroupsResponse(groups=[], total=0)

    eligible_with_agg: list[EligibleGame] = [
        (game, batch, meta, _build_match_aggregate(game, batch, meta))
        for game, batch, meta in raw_games
    ]

    groups_map = _group_eligible_games(eligible_with_agg)

    # Build season outcomes to detect champions
    from backend.services.historical_stats_aggregation_service import _build_season_outcomes

    match_aggregates = [entry[3] for entry in eligible_with_agg]
    season_outcomes = _build_season_outcomes(
        [(g, b, m) for g, b, m, _ in eligible_with_agg], match_aggregates
    )
    # Index outcomes by (competition_code, season, gender)
    outcome_index: dict[tuple[str, str | None, str], SeasonOutcomeAggregate] = {}
    for outcome in season_outcomes:
        outcome_index[(outcome.competition_code, outcome.season, outcome.gender_category)] = outcome

    summaries: list[TournamentGroupSummary] = []
    for (
        competition_code,
        competition_name,
        gender_category,
        season_value,
        format_family,
    ), group_games in sorted(
        groups_map.items(),
        key=lambda item: (
            item[0][1] or "",
            item[0][3] or "",
            item[0][2],
        ),
    ):
        season_year = _season_year_value(season_value)
        gk = TournamentGroupKey(
            competition_code=competition_code,
            competition_name=competition_name,
            season=season_value,
            season_year=season_year,
            gender_category=gender_category,
            format_family=format_family,
            source_type="historical_import",
        )

        group_outcome = outcome_index.get((competition_code, season_value, gender_category))
        champion_detected = bool(group_outcome and group_outcome.champion_team_canonical)
        champion_team = (
            group_outcome.champion_team_canonical
            if group_outcome and group_outcome.champion_team_canonical
            else None
        )
        confidence = group_outcome.confidence if group_outcome else "unknown"
        has_result = any(
            bool(g.result or match_agg.winner_team) for g, _b, _m, match_agg in group_games
        )
        has_delivery = any(
            bool(
                meta.get("deliveries_imported")
                or (isinstance(g.deliveries, list) and len(g.deliveries) > 0)
            )
            for g, _b, meta, _ in group_games
        )
        teams_set: set[str] = set()
        for _, _, _, match_agg in group_games:
            if match_agg.team_a:
                teams_set.add(match_agg.team_a)
            if match_agg.team_b:
                teams_set.add(match_agg.team_b)

        summaries.append(
            TournamentGroupSummary(
                group_key=gk,
                match_count=len(group_games),
                teams_count=len(teams_set),
                has_result_data=has_result,
                has_delivery_data=has_delivery,
                champion_detected=champion_detected,
                champion_team=champion_team,
                confidence=confidence,  # type: ignore[arg-type]
            )
        )

    return TournamentGroupsResponse(groups=summaries, total=len(summaries))


async def get_tournament_summary(
    db: AsyncSession,
    current_user: Any,
    competition_code: str,
    season: str | None,
    gender_category: str,
) -> TournamentSummaryResponse | None:
    """Return a full tournament intelligence summary for one group.

    Phase 10S.1: read-only, deterministic. Returns None if no matching games found.
    """
    from backend.services.historical_stats_aggregation_service import (
        _build_match_aggregate,
        _build_season_outcomes,
    )

    raw_games = await _fetch_eligible_games(db, current_user)
    if not raw_games:
        return None

    eligible_with_agg: list[EligibleGame] = [
        (game, batch, meta, _build_match_aggregate(game, batch, meta))
        for game, batch, meta in raw_games
    ]

    groups_map = _group_eligible_games(eligible_with_agg)

    # Find matching group
    target_games: list[EligibleGame] = []
    target_competition_name: str | None = None
    target_format_family: str = "unknown"

    for (
        cc,
        comp_name,
        gender,
        season_val,
        fmt_family,
    ), group_games in groups_map.items():
        if (
            cc == competition_code
            and gender == gender_category
            and (season is None or season_val == season)
        ):
            target_games.extend(group_games)
            target_competition_name = comp_name
            target_format_family = fmt_family

    if not target_games:
        return None

    season_year = _season_year_value(season)
    group_key = TournamentGroupKey(
        competition_code=competition_code,
        competition_name=target_competition_name,
        season=season,
        season_year=season_year,
        gender_category=gender_category,
        format_family=target_format_family,
        source_type="historical_import",
    )

    # Build season outcomes for knockout context
    match_aggregates = [entry[3] for entry in eligible_with_agg]
    season_outcomes = _build_season_outcomes(
        [(g, b, m) for g, b, m, _ in eligible_with_agg], match_aggregates
    )

    return _build_tournament_summary(group_key, target_games, season_outcomes)


async def get_team_journey(
    db: AsyncSession,
    current_user: Any,
    competition_code: str,
    season: str | None,
    gender_category: str,
    team_name: str,
) -> TeamJourneyResponse | None:
    """Return a team's journey within a competition/season.

    Phase 10S.1: read-only, deterministic. Returns None if no matching games found.
    """
    from backend.services.historical_stats_aggregation_service import _build_match_aggregate

    raw_games = await _fetch_eligible_games(db, current_user)
    if not raw_games:
        return None

    eligible_with_agg: list[EligibleGame] = [
        (game, batch, meta, _build_match_aggregate(game, batch, meta))
        for game, batch, meta in raw_games
    ]

    groups_map = _group_eligible_games(eligible_with_agg)

    target_games: list[EligibleGame] = []
    target_competition_name: str | None = None
    target_format_family: str = "unknown"

    for (
        cc,
        comp_name,
        gender,
        season_val,
        fmt_family,
    ), group_games in groups_map.items():
        if (
            cc == competition_code
            and gender == gender_category
            and (season is None or season_val == season)
        ):
            target_games.extend(group_games)
            target_competition_name = comp_name
            target_format_family = fmt_family

    if not target_games:
        return None

    season_year = _season_year_value(season)
    group_key = TournamentGroupKey(
        competition_code=competition_code,
        competition_name=target_competition_name,
        season=season,
        season_year=season_year,
        gender_category=gender_category,
        format_family=target_format_family,
        source_type="historical_import",
    )

    return _build_team_journey(team_name, group_key, target_games)


async def get_tournament_podcast_rundown(
    db: AsyncSession,
    current_user: Any,
    competition_code: str,
    season: str | None,
    gender_category: str,
) -> TournamentPodcastRundown | None:
    """Return a full tournament podcast rundown for one competition/season group.

    Phase 10S.2: read-only, deterministic. Builds the rundown from the same
    underlying summary data as get_tournament_summary(). Returns None if no
    matching games are found.
    """
    summary = await get_tournament_summary(
        db, current_user, competition_code, season, gender_category
    )
    if summary is None:
        return None
    return build_tournament_podcast_rundown(summary)
