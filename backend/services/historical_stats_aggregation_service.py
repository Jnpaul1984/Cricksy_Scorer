"""Phase 5N — Historical Stats Aggregation Layer: deterministic aggregation service.

Computes on-demand aggregate statistics from validated, fully-imported historical
cricket match data stored in the ``Game`` table.

Strict eligibility gates (all must pass before a game is included):
  1. ``Game.phases['historical_import']['is_historical'] == True``
  2. Linked ``HistoricalImportBatch.is_finalized == True``
  3. ``batch.applied_game_id`` is set
  4. ``batch.status == "valid"``
  5. ``batch.error_count == 0``
  6. ``batch.status`` is NOT in the metadata-only set:
     {scanned, metadata_extracted, pending_full_import}

Metadata-only records are counted and excluded — they are NEVER aggregated
as full historical data and are never marked training-eligible here.

All aggregation is deterministic Python logic. No AI/LLM services are used.
No official truth fields (scores, wickets, DLS outputs, innings state,
match result, official player stats) are mutated.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from typing import Any

from backend.api.schemas.historical_stats import (
    CompetitionAggregate,
    HistoricalMatchAggregateResponse,
    HistoricalStatsSummaryResponse,
    InningsAggregate,
    MatchAggregate,
    PlayerAggregate,
    SeasonAggregate,
    TeamAggregate,
    VenueAggregate,
)
from backend.services.cpl_team_alias_registry import canonicalize_team_name, normalize_team_name
from backend.services.analyst_access import scoped_games_stmt
from backend.sql_app.models import Game, GameStatus, HistoricalImportBatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Batch statuses that indicate the record is metadata-only (not fully imported).
_METADATA_ONLY_STATUSES: frozenset[str] = frozenset(
    {"scanned", "metadata_extracted", "pending_full_import"}
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _hist_meta(game: Game) -> dict[str, Any] | None:
    """Return the historical_import sub-dict from Game.phases, or None."""
    phases = game.phases if isinstance(game.phases, dict) else {}
    meta = phases.get("historical_import")
    if isinstance(meta, dict) and meta.get("is_historical"):
        return meta
    return None


def _innings_summary(game: Game) -> list[dict[str, Any]]:
    """Return the historical_innings_summary list from Game.phases."""
    phases = game.phases if isinstance(game.phases, dict) else {}
    raw = phases.get("historical_innings_summary")
    if isinstance(raw, list):
        return [inn for inn in raw if isinstance(inn, dict)]
    return []


def _is_metadata_only(batch: HistoricalImportBatch) -> bool:
    """Return True if the batch is metadata-only (pending full import)."""
    return batch.status in _METADATA_ONLY_STATUSES


def _is_eligible_for_aggregation(batch: HistoricalImportBatch) -> bool:
    """Return True only when the batch satisfies all eligibility gates.

    Must be:
    - Not metadata-only
    - Finalized (Phase 5D applied)
    - Has an applied game
    - Status is 'valid'
    - Zero errors
    """
    if _is_metadata_only(batch):
        return False
    if not batch.is_finalized:
        return False
    if not batch.applied_game_id:
        return False
    if batch.status != "valid":
        return False
    return batch.error_count == 0


def _safe_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return int(text)
    return None


def _parse_scorecard_wickets(score_text: str | None) -> int | None:
    if not score_text:
        return None
    parts = score_text.strip().split("/")
    if len(parts) < 2:
        return None
    wickets_text = "".join(ch for ch in parts[1] if ch.isdigit())
    if not wickets_text:
        return None
    return int(wickets_text)


def _extract_scorecard_text(innings_payload: dict[str, Any]) -> str | None:
    for key in ("score", "score_summary", "summary", "inning_summary", "scorecard"):
        value = innings_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _derive_winner(
    result_text: str | None,
    team_a_name: str,
    team_b_name: str,
) -> tuple[str | None, str | None, str]:
    if not result_text:
        return None, None, "none"
    lowered = result_text.lower()
    if any(token in lowered for token in ("tie", "draw", "abandon", "no result")):
        return None, None, "high"

    team_a_norm = normalize_team_name(team_a_name)
    team_b_norm = normalize_team_name(team_b_name)

    if team_a_norm and team_a_norm in normalize_team_name(result_text):
        return team_a_name, canonicalize_team_name(team_a_name)[0], "high"
    if team_b_norm and team_b_norm in normalize_team_name(result_text):
        return team_b_name, canonicalize_team_name(team_b_name)[0], "high"

    for marker in (" won", " beat", " defeated"):
        idx = lowered.find(marker)
        if idx <= 0:
            continue
        candidate = result_text[:idx].strip(" ,.;:")
        if candidate:
            candidate_canonical, _ = canonicalize_team_name(candidate)
            return candidate, candidate_canonical, "medium"

    return None, None, "none"


def _build_innings_aggregates(
    innings_list: list[dict[str, Any]],
) -> list[InningsAggregate]:
    """Build InningsAggregate objects from historical_innings_summary entries.

    Reads from existing stored data — does not mutate any source fields.
    """
    result: list[InningsAggregate] = []
    for inn in innings_list:
        runs = int(inn.get("runs") or 0)
        wickets = int(inn.get("wickets") or 0)
        overs_raw = inn.get("overs")
        overs = float(overs_raw) if overs_raw is not None else 0.0
        inning_no = int(inn.get("inning_no") or 0)
        team = inn.get("team")
        result.append(
            InningsAggregate(
                inning_no=inning_no,
                team=str(team) if team else None,
                runs=runs,
                wickets=wickets,
                overs=overs,
            )
        )
    return result


def _build_match_aggregate(
    game: Game,
    batch: HistoricalImportBatch,
    meta: dict[str, Any],
) -> MatchAggregate:
    """Build a MatchAggregate from a single eligible historical Game.

    Reads Game.phases, Game.team_a, Game.team_b, and Game.deliveries.
    Does not write or mutate any Game fields.
    """
    team_a_data = game.team_a if isinstance(game.team_a, dict) else {}
    team_b_data = game.team_b if isinstance(game.team_b, dict) else {}
    team_a_name = team_a_data.get("name") or "Team A"
    team_b_name = team_b_data.get("name") or "Team B"

    innings_list = _innings_summary(game)
    deliveries = game.deliveries if isinstance(game.deliveries, list) else []
    deliveries_by_inning: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for delivery in deliveries:
        if not isinstance(delivery, dict):
            continue
        inning_no = _safe_int(delivery.get("inning"))
        if inning_no is None:
            continue
        deliveries_by_inning[inning_no].append(delivery)

    first_inning_summary = (
        game.first_inning_summary if isinstance(game.first_inning_summary, dict) else {}
    )

    innings_aggregates: list[InningsAggregate] = []
    wicket_sources: set[str] = set()
    for inn in innings_list:
        inning_no = _safe_int(inn.get("inning_no")) or 0
        inning_deliveries = deliveries_by_inning.get(inning_no, [])
        runs_value = _safe_int(inn.get("runs"))
        wickets_value = _safe_int(inn.get("wickets"))
        if inning_deliveries:
            runs_value = sum(
                int(d.get("runs_off_bat") or 0) + int(d.get("extra_runs") or 0)
                for d in inning_deliveries
            )
            wickets_value = sum(1 for d in inning_deliveries if d.get("is_wicket"))
            wicket_sources.add("deliveries")
        elif wickets_value is not None:
            wicket_sources.add("innings_summary")
        else:
            scorecard_text = _extract_scorecard_text(inn)
            if not scorecard_text and inning_no == 1:
                scorecard_text = str(first_inning_summary.get("score") or "")
                if not scorecard_text:
                    fir_wkts = _safe_int(first_inning_summary.get("wickets"))
                    if fir_wkts is not None:
                        wickets_value = fir_wkts
                        wicket_sources.add("scorecard")
            parsed_wickets = _parse_scorecard_wickets(scorecard_text)
            if wickets_value is None and parsed_wickets is not None:
                wickets_value = parsed_wickets
                wicket_sources.add("scorecard")
            if runs_value is None and scorecard_text and "/" in scorecard_text:
                runs_text = "".join(ch for ch in scorecard_text.split("/", 1)[0] if ch.isdigit())
                if runs_text:
                    runs_value = int(runs_text)
        runs = runs_value if runs_value is not None else 0
        wickets = wickets_value if wickets_value is not None else 0
        overs_raw = inn.get("overs")
        overs = float(overs_raw) if overs_raw is not None else 0.0
        innings_aggregates.append(
            InningsAggregate(
                inning_no=inning_no,
                team=str(inn.get("team")) if inn.get("team") else None,
                runs=runs,
                wickets=wickets,
                overs=overs,
            )
        )

    total_runs = sum(i.runs for i in innings_aggregates)
    total_wickets = sum(i.wickets for i in innings_aggregates)

    has_delivery_data = bool(meta.get("deliveries_imported")) or bool(
        isinstance(game.deliveries, list) and len(game.deliveries) > 0
    )

    winner_team, winner_team_canonical, winner_confidence = _derive_winner(
        game.result if isinstance(game.result, str) else None,
        team_a_name,
        team_b_name,
    )
    team_a_canonical, _ = canonicalize_team_name(team_a_name)
    team_b_canonical, _ = canonicalize_team_name(team_b_name)

    phases = game.phases if isinstance(game.phases, dict) else {}
    phase_breakdown: dict[str, dict[str, int | float]] = {}
    for phase_name in ("powerplay", "middle", "death"):
        phase_payload = phases.get(phase_name)
        if not isinstance(phase_payload, dict):
            continue
        phase_breakdown[phase_name] = {
            "runs": int(phase_payload.get("runs") or 0),
            "wickets": int(phase_payload.get("wickets") or 0),
            "legal_balls": int(phase_payload.get("legal_balls") or 0),
            "overs": float(phase_payload.get("overs") or 0.0),
            "deliveries": int(phase_payload.get("deliveries") or 0),
        }

    wicket_derivation_source = "missing"
    if "deliveries" in wicket_sources:
        wicket_derivation_source = "deliveries"
    elif "scorecard" in wicket_sources:
        wicket_derivation_source = "scorecard"
    elif "innings_summary" in wicket_sources:
        wicket_derivation_source = "innings_summary"

    return MatchAggregate(
        match_id=game.id,
        teams=f"{team_a_name} vs {team_b_name}",
        team_a=team_a_name,
        team_b=team_b_name,
        import_batch_id=batch.id,
        source_filename=batch.source_filename,
        source_format=batch.source_format,
        competition=meta.get("event_name"),
        season=meta.get("season"),
        venue=meta.get("venue"),
        match_date=meta.get("match_date"),
        match_type=game.match_type,
        innings_count=len(innings_aggregates),
        total_runs=total_runs,
        total_wickets=total_wickets,
        innings_totals=innings_aggregates,
        winner_team=winner_team,
        winner_team_canonical=winner_team_canonical,
        winner_source="result_text" if winner_team else None,
        winner_confidence=winner_confidence,
        wicket_derivation_source=wicket_derivation_source,
        phase_breakdown=phase_breakdown,
        team_a_canonical=team_a_canonical,
        team_b_canonical=team_b_canonical,
        has_delivery_data=has_delivery_data,
    )


def _aggregate_batting(
    batting_scorecard: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Extract batting stats from a single game's batting_scorecard.

    Reads existing scorecard data — does not mutate any Game fields.
    Returns a dict keyed by player name.
    """
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(batting_scorecard, dict):
        return result
    for player_name, stats in batting_scorecard.items():
        if not isinstance(stats, dict):
            continue
        result[str(player_name)] = {
            "runs": int(stats.get("runs") or 0),
            "balls_faced": int(stats.get("balls_faced") or 0),
            "fours": int(stats.get("fours") or 0),
            "sixes": int(stats.get("sixes") or 0),
            "is_out": bool(stats.get("is_out", False)),
        }
    return result


def _aggregate_bowling(
    bowling_scorecard: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Extract bowling stats from a single game's bowling_scorecard.

    Reads existing scorecard data — does not mutate any Game fields.
    Returns a dict keyed by bowler name.
    """
    result: dict[str, dict[str, Any]] = {}
    if not isinstance(bowling_scorecard, dict):
        return result
    for player_name, stats in bowling_scorecard.items():
        if not isinstance(stats, dict):
            continue
        result[str(player_name)] = {
            "overs_bowled": float(stats.get("overs_bowled") or 0.0),
            "balls_bowled": int(stats.get("balls_bowled") or 0),
            "runs_conceded": int(stats.get("runs_conceded") or 0),
            "wickets_taken": int(stats.get("wickets_taken") or 0),
            "maidens": int(stats.get("maidens") or 0),
        }
    return result


def _build_player_aggregates(
    eligible_games: list[tuple[Game, HistoricalImportBatch, dict[str, Any]]],
) -> list[PlayerAggregate]:
    """Aggregate batting and bowling stats across all eligible games with delivery data.

    Only games where Phase 5F delivery import has been completed are included,
    since batting_scorecard and bowling_scorecard are populated by Phase 5F.
    """
    # Accumulate per-player stats across matches
    batting_acc: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"runs": 0, "balls_faced": 0, "fours": 0, "sixes": 0, "dismissals": 0, "matches": 0}
    )
    bowling_acc: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "overs_bowled": 0.0,
            "balls_bowled": 0,
            "runs_conceded": 0,
            "wickets_taken": 0,
            "maidens": 0,
            "matches": 0,
        }
    )

    for game, _batch, meta in eligible_games:
        # Only include scorecard data when deliveries have been imported
        if not meta.get("deliveries_imported"):
            continue

        batting_stats = _aggregate_batting(game.batting_scorecard or {})
        for player, bstats in batting_stats.items():
            acc = batting_acc[player]
            acc["runs"] += bstats["runs"]
            acc["balls_faced"] += bstats["balls_faced"]
            acc["fours"] += bstats["fours"]
            acc["sixes"] += bstats["sixes"]
            if bstats["is_out"]:
                acc["dismissals"] += 1
            acc["matches"] += 1

        bowling_stats = _aggregate_bowling(game.bowling_scorecard or {})
        for player, bwstats in bowling_stats.items():
            acc = bowling_acc[player]
            acc["overs_bowled"] += bwstats["overs_bowled"]
            acc["balls_bowled"] += bwstats["balls_bowled"]
            acc["runs_conceded"] += bwstats["runs_conceded"]
            acc["wickets_taken"] += bwstats["wickets_taken"]
            acc["maidens"] += bwstats["maidens"]
            acc["matches"] += 1

    all_players = set(batting_acc) | set(bowling_acc)
    result: list[PlayerAggregate] = []

    for player_name in sorted(all_players):
        bstats = batting_acc.get(player_name, {})
        bwstats = bowling_acc.get(player_name, {})

        balls_faced = bstats.get("balls_faced", 0)
        runs_scored = bstats.get("runs", 0)
        strike_rate = round((runs_scored / balls_faced) * 100, 2) if balls_faced > 0 else 0.0

        overs_bowled = bwstats.get("overs_bowled", 0.0)
        runs_conceded = bwstats.get("runs_conceded", 0)
        economy_rate = round(runs_conceded / overs_bowled, 2) if overs_bowled > 0 else 0.0

        matches_contributed = max(bstats.get("matches", 0), bwstats.get("matches", 0))

        result.append(
            PlayerAggregate(
                player_name=player_name,
                matches_contributed=matches_contributed,
                runs_scored=runs_scored,
                balls_faced=balls_faced,
                strike_rate=strike_rate,
                fours=bstats.get("fours", 0),
                sixes=bstats.get("sixes", 0),
                dismissals=bstats.get("dismissals", 0),
                overs_bowled=round(overs_bowled, 1),
                runs_conceded=runs_conceded,
                wickets=bwstats.get("wickets_taken", 0),
                economy_rate=economy_rate,
                maidens=bwstats.get("maidens", 0),
            )
        )

    return result


def _build_team_aggregates(
    eligible_games: list[tuple[Game, HistoricalImportBatch, dict[str, Any]]],
) -> list[TeamAggregate]:
    """Aggregate team stats across eligible historical matches.

    Uses historical_innings_summary to count runs, wickets per innings by team.
    """
    team_acc: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"matches": set(), "innings": 0, "total_runs": 0, "total_wickets": 0}
    )

    for game, _batch, _meta in eligible_games:
        innings_list = _innings_summary(game)
        team_a_data = game.team_a if isinstance(game.team_a, dict) else {}
        team_b_data = game.team_b if isinstance(game.team_b, dict) else {}
        team_names = {
            team_a_data.get("name") or "Team A",
            team_b_data.get("name") or "Team B",
        }
        # Count match for both teams
        for team_name in team_names:
            team_acc[team_name]["matches"].add(game.id)

        for inn in innings_list:
            team = str(inn.get("team") or "")
            if not team:
                continue
            runs = int(inn.get("runs") or 0)
            wickets = int(inn.get("wickets") or 0)
            team_acc[team]["innings"] += 1
            team_acc[team]["total_runs"] += runs
            team_acc[team]["total_wickets"] += wickets

    result: list[TeamAggregate] = []
    for team_name, acc in sorted(team_acc.items()):
        matches_played = len(acc["matches"])
        innings_batted = acc["innings"]
        total_runs = acc["total_runs"]
        total_wickets = acc["total_wickets"]
        avg_score = round(total_runs / innings_batted, 2) if innings_batted > 0 else 0.0
        avg_wickets = round(total_wickets / innings_batted, 2) if innings_batted > 0 else 0.0

        canonical_team_name, continuity_group = canonicalize_team_name(team_name)
        result.append(
            TeamAggregate(
                team_name=team_name,
                canonical_team_name=canonical_team_name,
                continuity_group=continuity_group,
                matches_played=matches_played,
                innings_batted=innings_batted,
                avg_score=avg_score,
                avg_wickets=avg_wickets,
                total_runs=total_runs,
                total_wickets=total_wickets,
            )
        )

    return result


def _build_venue_aggregates(
    eligible_games: list[tuple[Game, HistoricalImportBatch, dict[str, Any]]],
) -> list[VenueAggregate]:
    """Aggregate stats by venue across eligible historical matches."""
    venue_acc: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "match_count": 0,
            "first_innings_runs": [],
            "second_innings_runs": [],
            "total_runs": [],
            "total_wickets": [],
        }
    )

    for _game, _batch, meta in eligible_games:
        venue = meta.get("venue")
        if not venue or not str(venue).strip():
            continue
        venue_key = str(venue).strip()

        innings_list = _innings_summary(_game)
        acc = venue_acc[venue_key]
        acc["match_count"] += 1

        match_runs = 0
        match_wickets = 0
        for inn in innings_list:
            runs = int(inn.get("runs") or 0)
            wickets = int(inn.get("wickets") or 0)
            inning_no = int(inn.get("inning_no") or 0)
            match_runs += runs
            match_wickets += wickets
            if inning_no == 1:
                acc["first_innings_runs"].append(runs)
            elif inning_no == 2:
                acc["second_innings_runs"].append(runs)

        if innings_list:
            acc["total_runs"].append(match_runs)
            acc["total_wickets"].append(match_wickets)

    result: list[VenueAggregate] = []
    for venue_name, acc in sorted(venue_acc.items()):
        match_count = acc["match_count"]
        first_inn = acc["first_innings_runs"]
        second_inn = acc["second_innings_runs"]
        total_runs_list = acc["total_runs"]
        total_wickets_list = acc["total_wickets"]

        avg_first = round(sum(first_inn) / len(first_inn), 2) if first_inn else 0.0
        avg_second = round(sum(second_inn) / len(second_inn), 2) if second_inn else None
        avg_total = (
            round(sum(total_runs_list) / len(total_runs_list), 2) if total_runs_list else 0.0
        )
        avg_wickets = (
            round(sum(total_wickets_list) / len(total_wickets_list), 2)
            if total_wickets_list
            else 0.0
        )

        result.append(
            VenueAggregate(
                venue=venue_name,
                match_count=match_count,
                avg_first_innings_score=avg_first,
                avg_second_innings_score=avg_second,
                avg_total_runs=avg_total,
                avg_wickets=avg_wickets,
            )
        )

    return result


def _build_competition_aggregates(
    eligible_games: list[tuple[Game, HistoricalImportBatch, dict[str, Any]]],
) -> list[CompetitionAggregate]:
    """Aggregate stats by competition (event) across eligible historical matches."""
    comp_acc: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"match_count": 0, "total_runs": [], "total_wickets": []}
    )

    for game, _batch, meta in eligible_games:
        comp = meta.get("event_name")
        if not comp or not str(comp).strip():
            continue
        comp_key = str(comp).strip()

        innings_list = _innings_summary(game)
        acc = comp_acc[comp_key]
        acc["match_count"] += 1

        match_runs = sum(int(inn.get("runs") or 0) for inn in innings_list)
        match_wickets = sum(int(inn.get("wickets") or 0) for inn in innings_list)
        if innings_list:
            acc["total_runs"].append(match_runs)
            acc["total_wickets"].append(match_wickets)

    result: list[CompetitionAggregate] = []
    for comp_name, acc in sorted(comp_acc.items()):
        total_runs_list = acc["total_runs"]
        total_wickets_list = acc["total_wickets"]
        avg_total = (
            round(sum(total_runs_list) / len(total_runs_list), 2) if total_runs_list else 0.0
        )
        avg_wickets = (
            round(sum(total_wickets_list) / len(total_wickets_list), 2)
            if total_wickets_list
            else 0.0
        )

        result.append(
            CompetitionAggregate(
                competition=comp_name,
                match_count=acc["match_count"],
                avg_total_runs=avg_total,
                avg_wickets=avg_wickets,
            )
        )

    return result


def _build_season_aggregates(
    eligible_games: list[tuple[Game, HistoricalImportBatch, dict[str, Any]]],
) -> list[SeasonAggregate]:
    """Aggregate stats by season across eligible historical matches."""
    season_acc: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"match_count": 0, "total_runs": [], "total_wickets": []}
    )

    for game, _batch, meta in eligible_games:
        season = meta.get("season")
        if not season or not str(season).strip():
            continue
        season_key = str(season).strip()

        innings_list = _innings_summary(game)
        acc = season_acc[season_key]
        acc["match_count"] += 1

        match_runs = sum(int(inn.get("runs") or 0) for inn in innings_list)
        match_wickets = sum(int(inn.get("wickets") or 0) for inn in innings_list)
        if innings_list:
            acc["total_runs"].append(match_runs)
            acc["total_wickets"].append(match_wickets)

    result: list[SeasonAggregate] = []
    for season_name, acc in sorted(season_acc.items()):
        total_runs_list = acc["total_runs"]
        total_wickets_list = acc["total_wickets"]
        avg_total = (
            round(sum(total_runs_list) / len(total_runs_list), 2) if total_runs_list else 0.0
        )
        avg_wickets = (
            round(sum(total_wickets_list) / len(total_wickets_list), 2)
            if total_wickets_list
            else 0.0
        )

        result.append(
            SeasonAggregate(
                season=season_name,
                match_count=acc["match_count"],
                avg_total_runs=avg_total,
                avg_wickets=avg_wickets,
            )
        )

    return result


def _build_case_studies(
    matches: list[MatchAggregate],
    venues: list[VenueAggregate],
) -> list[dict[str, Any]]:
    studies: list[dict[str, Any]] = []
    if not matches:
        return studies

    high_scoring = max(matches, key=lambda m: (m.total_runs, m.match_id))
    studies.append(
        {
            "id": "high_scoring_match",
            "title": "High-scoring match",
            "insight": (
                f"{high_scoring.teams} produced {high_scoring.total_runs} runs in total "
                f"({high_scoring.match_date or 'date unknown'})."
            ),
            "source": f"match:{high_scoring.match_id}",
            "context": "Derived from innings total runs in validated historical imports.",
        }
    )

    powerplay_candidates = [
        m
        for m in matches
        if isinstance(m.phase_breakdown.get("powerplay"), dict)
        and int(m.phase_breakdown["powerplay"].get("legal_balls") or 0) > 0
    ]
    if powerplay_candidates:
        def _pp_run_rate(match: MatchAggregate) -> float:
            phase = match.phase_breakdown["powerplay"]
            legal_balls = int(phase.get("legal_balls") or 0)
            if legal_balls <= 0:
                return 0.0
            return float(phase.get("runs") or 0) / (legal_balls / 6)

        struggle = min(powerplay_candidates, key=lambda m: (_pp_run_rate(m), m.match_id))
        phase = struggle.phase_breakdown["powerplay"]
        studies.append(
            {
                "id": "powerplay_struggle",
                "title": "Powerplay struggle",
                "insight": (
                    f"{struggle.teams} scored {int(phase.get('runs') or 0)} runs in the powerplay "
                    f"across {int(phase.get('legal_balls') or 0)} legal balls."
                ),
                "source": f"match:{struggle.match_id}:powerplay",
                "context": "Derived from delivery phase breakdown.",
            }
        )

    death_candidates = [
        m
        for m in matches
        if isinstance(m.phase_breakdown.get("death"), dict)
        and int(m.phase_breakdown["death"].get("legal_balls") or 0) > 0
    ]
    if death_candidates:
        death_match = max(
            death_candidates,
            key=lambda m: (
                int(m.phase_breakdown["death"].get("runs") or 0),
                int(m.phase_breakdown["death"].get("wickets") or 0),
                m.match_id,
            ),
        )
        phase = death_match.phase_breakdown["death"]
        studies.append(
            {
                "id": "death_over_impact",
                "title": "Death-over impact",
                "insight": (
                    f"{death_match.teams} generated {int(phase.get('runs') or 0)} death-over runs "
                    f"with {int(phase.get('wickets') or 0)} wickets in that phase."
                ),
                "source": f"match:{death_match.match_id}:death",
                "context": "Derived from delivery phase breakdown.",
            }
        )

    if venues:
        venue_pattern = max(venues, key=lambda v: (v.avg_total_runs, v.match_count, v.venue))
        studies.append(
            {
                "id": "venue_scoring_pattern",
                "title": "Venue scoring pattern",
                "insight": (
                    f"{venue_pattern.venue} shows an average total of "
                    f"{venue_pattern.avg_total_runs:.1f} across {venue_pattern.match_count} match(es)."
                ),
                "source": f"venue:{venue_pattern.venue}",
                "context": "Derived from venue aggregate totals.",
            }
        )

    return studies


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def get_historical_stats_summary(
    db: AsyncSession,
    current_user: Any,
) -> HistoricalStatsSummaryResponse:
    """Build a full deterministic historical stats summary for the requesting user.

    - Applies org-scoping via ``scoped_games_stmt`` (mirrors Analyst Workspace).
    - Fetches all ``completed`` games accessible to the user.
    - Filters to historical imports with valid, finalized, fully-imported batches.
    - Excludes metadata-only records and tracks their count separately.
    - Aggregates match, player, team, venue, competition, and season statistics.

    No live scoring or official truth fields are mutated.
    No LLM/AI services are invoked — all logic is deterministic Python.
    """
    stmt = (
        scoped_games_stmt(current_user)
        .where(Game.status == GameStatus.completed)
        .order_by(Game.id.desc())
    )
    result = await db.execute(stmt)
    all_completed = result.scalars().all()

    # Collect batch IDs we need to fetch
    batch_id_to_game: dict[str, tuple[Game, dict[str, Any]]] = {}

    for game in all_completed:
        meta = _hist_meta(game)
        if not isinstance(meta, dict):
            continue
        batch_id = meta.get("batch_id")
        if not batch_id:
            continue
        batch_id_to_game[str(batch_id)] = (game, meta)

    # Fetch all referenced batches in one query
    batches: dict[str, HistoricalImportBatch] = {}
    if batch_id_to_game:
        batch_stmt = select(HistoricalImportBatch).where(
            HistoricalImportBatch.id.in_(list(batch_id_to_game.keys()))
        )
        batch_result = await db.execute(batch_stmt)
        for batch in batch_result.scalars().all():
            batches[batch.id] = batch

    eligible_games: list[tuple[Game, HistoricalImportBatch, dict[str, Any]]] = []
    metadata_only_count = 0
    invalid_count = 0

    for batch_id, (game, meta) in batch_id_to_game.items():
        batch = batches.get(batch_id)
        if batch is None:
            invalid_count += 1
            continue

        if _is_metadata_only(batch):
            metadata_only_count += 1
            continue

        if not _is_eligible_for_aggregation(batch):
            invalid_count += 1
            continue

        eligible_games.append((game, batch, meta))

    # Build aggregate outputs
    match_aggregates = [
        _build_match_aggregate(game, batch, meta) for game, batch, meta in eligible_games
    ]
    player_aggregates = _build_player_aggregates(eligible_games)
    team_aggregates = _build_team_aggregates(eligible_games)
    venue_aggregates = _build_venue_aggregates(eligible_games)
    competition_aggregates = _build_competition_aggregates(eligible_games)
    season_aggregates = _build_season_aggregates(eligible_games)
    case_studies = _build_case_studies(match_aggregates, venue_aggregates)

    winner_counts: dict[str, int] = defaultdict(int)
    for match in match_aggregates:
        if match.winner_team_canonical:
            winner_counts[match.winner_team_canonical] += 1
    top_team_by_wins: dict[str, Any] | None = None
    if winner_counts:
        best_team, wins = sorted(winner_counts.items(), key=lambda item: (-item[1], item[0]))[0]
        top_team_by_wins = {
            "team_name": best_team,
            "wins": wins,
            "source": "parsed_result_text",
            "confidence": "medium",
        }

    matches_with_parsed_winner = sum(1 for match in match_aggregates if match.winner_team is not None)
    scorecard_derived_wicket_matches = sum(
        1 for match in match_aggregates if match.wicket_derivation_source == "scorecard"
    )
    delivery_derived_wicket_matches = sum(
        1 for match in match_aggregates if match.wicket_derivation_source == "deliveries"
    )
    canonical_teams = {
        name
        for match in match_aggregates
        for name in (match.team_a_canonical, match.team_b_canonical)
        if name
    }
    venues_represented = len({m.venue for m in match_aggregates if m.venue})
    diagnostics = {
        "matches_imported": len(match_aggregates),
        "matches_with_parsed_winner": matches_with_parsed_winner,
        "matches_missing_winner_or_result": len(match_aggregates) - matches_with_parsed_winner,
        "delivery_complete_matches": sum(1 for match in match_aggregates if match.has_delivery_data),
        "delivery_derived_wicket_matches": delivery_derived_wicket_matches,
        "scorecard_derived_wicket_matches": scorecard_derived_wicket_matches,
        "canonical_teams_represented": len(canonical_teams),
        "venues_represented": venues_represented,
    }

    return HistoricalStatsSummaryResponse(
        total_eligible_matches=len(eligible_games),
        excluded_metadata_only_count=metadata_only_count,
        excluded_invalid_count=invalid_count,
        matches=match_aggregates,
        players=player_aggregates,
        teams=team_aggregates,
        venues=venue_aggregates,
        competitions=competition_aggregates,
        seasons=season_aggregates,
        diagnostics=diagnostics,
        top_team_by_wins=top_team_by_wins,
        case_studies=case_studies,
        generated_at=dt.datetime.now(dt.UTC),
    )


async def get_single_match_aggregate(
    db: AsyncSession,
    current_user: Any,
    match_id: str,
) -> HistoricalMatchAggregateResponse | None:
    """Build a single-match aggregate for a specific historical game.

    Returns None if the match is not found, not historical, or not eligible.

    The caller is responsible for raising HTTP 404 / 403 as appropriate.
    Reads existing data only — no official truth fields are mutated.
    """
    stmt = scoped_games_stmt(current_user).where(
        Game.id == match_id, Game.status == GameStatus.completed
    )
    result = await db.execute(stmt)
    game = result.scalar_one_or_none()
    if game is None:
        return None

    meta = _hist_meta(game)
    if not isinstance(meta, dict):
        return None

    batch_id = meta.get("batch_id")
    if not batch_id:
        return None

    batch_result = await db.execute(
        select(HistoricalImportBatch).where(HistoricalImportBatch.id == batch_id)
    )
    batch = batch_result.scalar_one_or_none()
    if batch is None:
        return None

    if _is_metadata_only(batch):
        return None

    if not _is_eligible_for_aggregation(batch):
        return None

    match_agg = _build_match_aggregate(game, batch, meta)

    # Per-match player aggregates (only when delivery data exists)
    player_aggregates = _build_player_aggregates([(game, batch, meta)])

    provenance: dict[str, Any] = {
        "match_id": game.id,
        "import_batch_id": batch.id,
        "source_filename": batch.source_filename,
        "source_format": batch.source_format,
        "source_hash_sha256": batch.source_hash_sha256,
        "source_type": "json",
        "validation_status": batch.status,
        "registration_status": (
            "registered"
            if (batch.is_finalized and batch.status == "valid" and batch.error_count == 0)
            else "not_registered"
        ),
        "imported_at": batch.created_at.isoformat() if batch.created_at else None,
        "competition": meta.get("event_name"),
        "season": meta.get("season"),
        "venue": meta.get("venue"),
        "match_date": meta.get("match_date"),
    }

    return HistoricalMatchAggregateResponse(
        match=match_agg,
        players=player_aggregates,
        provenance=provenance,
    )
