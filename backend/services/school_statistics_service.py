"""Query-time School Free statistics derived from official persisted match truth."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Literal

from backend.api.schemas.school_statistics import (
    SchoolFixtureSummary,
    SchoolMatchResult,
    SchoolPlayerStatistics,
    SchoolTeamStatistics,
)
from backend.domain.constants import CREDIT_BOWLER, norm_extra
from backend.services import organization_service
from backend.services.organization_entitlement_service import (
    FREE_CRICKET_ORGANIZATION_TYPES,
    require_organization_capability,
)
from backend.sql_app import models
from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

READ_ROLES = frozenset({"owner", "admin", "coach", "scorer", "viewer"})


@dataclass(frozen=True)
class SchoolStatisticsServiceError(Exception):
    status_code: int
    detail: str


def _not_found(resource: str) -> SchoolStatisticsServiceError:
    return SchoolStatisticsServiceError(404, f"{resource} not found")


async def _authorize(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    capability: str,
) -> None:
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability=capability,
    )
    organization, membership = await organization_service.get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if (
        organization.organization_type not in FREE_CRICKET_ORGANIZATION_TYPES
        or membership.role not in READ_ROLES
    ):
        raise SchoolStatisticsServiceError(403, "Insufficient organization role")


def _school_games_stmt(organization_id: str) -> Select[tuple[models.Game]]:
    """Filter School Games in SQL before JSON-ledger aggregation."""
    org_a = models.Game.team_a["school_source"]["organization_id"].as_string()
    org_b = models.Game.team_b["school_source"]["organization_id"].as_string()
    return select(models.Game).where(
        or_(
            and_(org_a == organization_id, or_(org_b == organization_id, org_b.is_(None))),
            and_(org_b == organization_id, org_a.is_(None)),
        )
    )


def _source(team: dict[str, Any]) -> tuple[str | None, str | None]:
    source = team.get("school_source")
    if not isinstance(source, dict):
        return None, None
    organization_id = source.get("organization_id")
    team_id = source.get("team_id")
    return (
        organization_id if isinstance(organization_id, str) else None,
        team_id if isinstance(team_id, str) else None,
    )


def _canonical_xi(team: dict[str, Any]) -> set[str]:
    """Accept only canonical IDs frozen by Phase 7I, never names/current rosters."""
    playing_xi = team.get("playing_xi")
    players = team.get("players")
    if not isinstance(playing_xi, list) or not isinstance(players, list):
        return set()
    frozen_profiles = {
        str(player["id"])
        for player in players
        if isinstance(player, dict)
        and isinstance(player.get("id"), str)
        and player.get("player_profile_id") == player.get("id")
    }
    return {str(player_id) for player_id in playing_xi if str(player_id) in frozen_profiles}


def _snapshot_xi(team: dict[str, Any]) -> set[str]:
    """Return IDs frozen in any match side, including match-local opponents."""
    playing_xi = team.get("playing_xi")
    players = team.get("players")
    if not isinstance(playing_xi, list) or not isinstance(players, list):
        return set()
    frozen_ids = {
        str(player["id"])
        for player in players
        if isinstance(player, dict) and isinstance(player.get("id"), str)
    }
    return {str(player_id) for player_id in playing_xi if str(player_id) in frozen_ids}


def _started(game: models.Game) -> bool:
    if game.deliveries:
        return True
    return game.status in {
        models.GameStatus.started,
        models.GameStatus.in_progress,
        models.GameStatus.live,
        models.GameStatus.completed,
        models.GameStatus.abandoned,
    }


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _result_text(value: str | None) -> str | None:
    """Normalize legacy text and the scorer's persisted structured result."""
    if value is None:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        decoded = json.loads(normalized)
    except (json.JSONDecodeError, TypeError):
        return normalized
    if isinstance(decoded, dict):
        result_text = decoded.get("result_text")
        if isinstance(result_text, str) and result_text.strip():
            return result_text.strip()
    return normalized


def _overs_from_balls(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}"


def _delivery_values(delivery: dict[str, Any]) -> tuple[int, int, str | None]:
    extra = norm_extra(delivery.get("extra_type"))
    off_bat = _safe_int(delivery.get("runs_off_bat"))
    extra_runs = _safe_int(delivery.get("extra_runs"))
    if extra == "wd":
        bowler_runs = max(1, extra_runs or _safe_int(delivery.get("runs_scored")) or 1)
    elif extra == "nb":
        bowler_runs = 1 + off_bat
    elif extra is None:
        bowler_runs = off_bat
    else:
        bowler_runs = 0
    return off_bat, bowler_runs, extra


def _game_sides(
    game: models.Game,
) -> tuple[str | None, str | None, set[str], set[str]]:
    _, team_a_id = _source(game.team_a)
    _, team_b_id = _source(game.team_b)
    return team_a_id, team_b_id, _canonical_xi(game.team_a), _canonical_xi(game.team_b)


def _player_accumulator() -> dict[str, Any]:
    return {
        "matches": 0,
        "innings": set(),
        "runs": 0,
        "highest_score": 0,
        "balls_faced": 0,
        "fours": 0,
        "sixes": 0,
        "outs": set(),
        "bowling_innings": set(),
        "balls_bowled": 0,
        "runs_conceded": 0,
        "wickets": 0,
        "best": None,
    }


def _aggregate_players(
    games: list[models.Game],
    profile_ids: set[str],
) -> dict[str, dict[str, Any]]:
    totals = {profile_id: _player_accumulator() for profile_id in profile_ids}
    for game in games:
        _, _, xi_a, xi_b = _game_sides(game)
        participants = (xi_a | xi_b) & profile_ids
        if _started(game):
            for player_id in participants:
                totals[player_id]["matches"] += 1

        innings_runs: dict[tuple[int, str], int] = defaultdict(int)
        innings_bowling: dict[tuple[int, str], list[int]] = defaultdict(lambda: [0, 0])
        for delivery in game.deliveries or []:
            if not isinstance(delivery, dict):
                continue
            inning = max(1, _safe_int(delivery.get("inning")) or 1)
            striker_id = str(delivery.get("striker_id") or "")
            bowler_id = str(delivery.get("bowler_id") or "")
            dismissed_id = str(delivery.get("dismissed_player_id") or striker_id)
            off_bat, bowler_runs, extra = _delivery_values(delivery)

            if striker_id in participants:
                key = (inning, striker_id)
                totals[striker_id]["innings"].add((game.id, inning))
                totals[striker_id]["runs"] += off_bat
                innings_runs[key] += off_bat
                if extra not in {"wd", "nb"}:
                    totals[striker_id]["balls_faced"] += 1
                if off_bat == 4:
                    totals[striker_id]["fours"] += 1
                elif off_bat == 6:
                    totals[striker_id]["sixes"] += 1

            dismissal_type = str(delivery.get("dismissal_type") or "").strip().lower()
            if delivery.get("is_wicket") and dismissal_type and dismissed_id in participants:
                totals[dismissed_id]["innings"].add((game.id, inning))
                totals[dismissed_id]["outs"].add((game.id, inning))

            if bowler_id in participants:
                totals[bowler_id]["bowling_innings"].add((game.id, inning))
                totals[bowler_id]["runs_conceded"] += bowler_runs
                innings_bowling[(inning, bowler_id)][1] += bowler_runs
                if extra not in {"wd", "nb"}:
                    totals[bowler_id]["balls_bowled"] += 1
                if delivery.get("is_wicket") and dismissal_type in CREDIT_BOWLER:
                    totals[bowler_id]["wickets"] += 1
                    innings_bowling[(inning, bowler_id)][0] += 1

        for (_, player_id), runs in innings_runs.items():
            totals[player_id]["highest_score"] = max(totals[player_id]["highest_score"], runs)
        for (_, player_id), figures in innings_bowling.items():
            candidate = (figures[0], figures[1])
            current = totals[player_id]["best"]
            if (
                current is None
                or candidate[0] > current[0]
                or (candidate[0] == current[0] and candidate[1] < current[1])
            ):
                totals[player_id]["best"] = candidate
    return totals


def _player_response(
    membership: models.SchoolPlayerMembership,
    profile: models.PlayerProfile,
    values: dict[str, Any],
) -> SchoolPlayerStatistics:
    dismissals = len(values["outs"])
    wickets = int(values["wickets"])
    balls = int(values["balls_bowled"])
    best = values["best"]
    return SchoolPlayerStatistics(
        player_profile_id=profile.player_id,
        player_name=profile.player_name,
        roster_status=membership.status,
        matches=int(values["matches"]),
        innings=len(values["innings"]),
        runs=int(values["runs"]),
        highest_score=int(values["highest_score"]),
        batting_average=(round(values["runs"] / dismissals, 2) if dismissals else None),
        balls_faced=int(values["balls_faced"]),
        strike_rate=(
            round(values["runs"] * 100 / values["balls_faced"], 2) if values["balls_faced"] else 0.0
        ),
        fours=int(values["fours"]),
        sixes=int(values["sixes"]),
        bowling_innings=len(values["bowling_innings"]),
        balls_bowled=balls,
        overs=_overs_from_balls(balls),
        runs_conceded=int(values["runs_conceded"]),
        wickets=wickets,
        bowling_average=(round(values["runs_conceded"] / wickets, 2) if wickets else None),
        economy=(round(values["runs_conceded"] * 6 / balls, 2) if balls else None),
        best_bowling=(f"{best[0]}/{best[1]}" if best is not None else None),
    )


async def player_statistics(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    player_profile_id: str | None = None,
) -> list[SchoolPlayerStatistics]:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_basic_statistics",
    )
    roster_stmt = (
        select(models.SchoolPlayerMembership, models.PlayerProfile)
        .join(
            models.PlayerProfile,
            models.PlayerProfile.player_id == models.SchoolPlayerMembership.player_profile_id,
        )
        .where(models.SchoolPlayerMembership.organization_id == organization_id)
    )
    if player_profile_id is not None:
        roster_stmt = roster_stmt.where(
            models.SchoolPlayerMembership.player_profile_id == player_profile_id
        )
    roster_rows = (await db.execute(roster_stmt.order_by(models.PlayerProfile.player_name))).all()
    if player_profile_id is not None and not roster_rows:
        raise _not_found("Player")
    profiles = {profile.player_id for _, profile in roster_rows}
    games = list((await db.scalars(_school_games_stmt(organization_id))).all())
    aggregate = _aggregate_players(games, profiles)
    return [
        _player_response(membership, profile, aggregate[profile.player_id])
        for membership, profile in roster_rows
    ]


def _team_accumulator() -> dict[str, int]:
    return {
        "matches": 0,
        "wins": 0,
        "losses": 0,
        "ties": 0,
        "draws": 0,
        "no_results": 0,
        "runs_scored": 0,
        "runs_conceded": 0,
        "wickets_taken": 0,
        "wickets_lost": 0,
    }


def _side_for_player(player_id: str, xi_a: set[str], xi_b: set[str]) -> Literal["a", "b"] | None:
    if player_id in xi_a and player_id not in xi_b:
        return "a"
    if player_id in xi_b and player_id not in xi_a:
        return "b"
    return None


def _game_team_totals(game: models.Game) -> dict[str, dict[str, int]]:
    xi_a = _snapshot_xi(game.team_a)
    xi_b = _snapshot_xi(game.team_b)
    values = {"a": {"runs": 0, "wickets": 0}, "b": {"runs": 0, "wickets": 0}}
    for delivery in game.deliveries or []:
        if not isinstance(delivery, dict):
            continue
        striker_id = str(delivery.get("striker_id") or "")
        batting_side = _side_for_player(striker_id, xi_a, xi_b)
        if batting_side is None:
            continue
        values[batting_side]["runs"] += _safe_int(delivery.get("runs_scored"))
        if delivery.get("is_wicket") and str(delivery.get("dismissal_type") or "").strip():
            dismissed_id = str(delivery.get("dismissed_player_id") or striker_id)
            if _side_for_player(dismissed_id, xi_a, xi_b) == batting_side:
                values[batting_side]["wickets"] += 1
    return values


def _apply_result(
    game: models.Game,
    school_sides: dict[Literal["a", "b"], str],
    totals: dict[str, dict[str, int]],
) -> None:
    if game.status == models.GameStatus.abandoned:
        for team_id in school_sides.values():
            totals[team_id]["no_results"] += 1
        return
    if game.status != models.GameStatus.completed:
        return
    result = _result_text(game.result) or ""
    lowered = result.lower()
    if lowered == "match tied":
        for team_id in school_sides.values():
            totals[team_id]["ties"] += 1
    elif lowered == "match drawn":
        for team_id in school_sides.values():
            totals[team_id]["draws"] += 1
    elif lowered in {"no result", "match abandoned"}:
        for team_id in school_sides.values():
            totals[team_id]["no_results"] += 1
    elif " won by " in result:
        winner_name = result.split(" won by ", 1)[0]
        name_a = str(game.team_a.get("name", ""))
        name_b = str(game.team_b.get("name", ""))
        winner_side: Literal["a", "b"] | None = None
        if name_a != name_b and winner_name == name_a:
            winner_side = "a"
        elif name_a != name_b and winner_name == name_b:
            winner_side = "b"
        for side, team_id in school_sides.items():
            if winner_side is None:
                totals[team_id]["no_results"] += 1
            elif side == winner_side:
                totals[team_id]["wins"] += 1
            else:
                totals[team_id]["losses"] += 1
    else:
        for team_id in school_sides.values():
            totals[team_id]["no_results"] += 1


async def team_statistics(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    team_id: str | None = None,
) -> list[SchoolTeamStatistics]:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_basic_statistics",
    )
    team_stmt = select(models.Team).where(models.Team.organization_id == organization_id)
    if team_id is not None:
        team_stmt = team_stmt.where(models.Team.id == team_id)
    teams = list((await db.scalars(team_stmt.order_by(models.Team.name, models.Team.id))).all())
    if team_id is not None and not teams:
        raise _not_found("Team")
    values = {team.id: _team_accumulator() for team in teams}
    games = list((await db.scalars(_school_games_stmt(organization_id))).all())
    for game in games:
        source_a, source_b, _, _ = _game_sides(game)
        school_sides: dict[Literal["a", "b"], str] = {}
        if source_a is not None and source_a in values:
            school_sides["a"] = source_a
        if source_b is not None and source_b in values and source_b != source_a:
            school_sides["b"] = source_b
        if not school_sides:
            continue
        if _started(game):
            for team_id in school_sides.values():
                values[team_id]["matches"] += 1
        game_totals = _game_team_totals(game)
        for side, team_id in school_sides.items():
            opponent_side = "b" if side == "a" else "a"
            values[team_id]["runs_scored"] += game_totals[side]["runs"]
            values[team_id]["runs_conceded"] += game_totals[opponent_side]["runs"]
            values[team_id]["wickets_lost"] += game_totals[side]["wickets"]
            values[team_id]["wickets_taken"] += game_totals[opponent_side]["wickets"]
        _apply_result(game, school_sides, values)
    return [
        SchoolTeamStatistics(
            team_id=team.id,
            team_name=team.name,
            team_status=team.status,
            **values[team.id],
        )
        for team in teams
    ]


def _match_result(game: models.Game) -> SchoolMatchResult | None:
    team_a_id, team_b_id, _, _ = _game_sides(game)
    if (team_a_id is None and team_b_id is None) or (
        team_a_id is not None and team_a_id == team_b_id
    ):
        return None
    totals = _game_team_totals(game)
    publication = game.publication_state or "private"
    return SchoolMatchResult(
        game_id=game.id,
        team_a_id=team_a_id,
        team_a_name=str(game.team_a.get("name", "")),
        team_b_id=team_b_id,
        team_b_name=str(game.team_b.get("name", "")),
        status=game.status.value,
        result=_result_text(game.result),
        publication_state=publication,
        current_inning=game.current_inning,
        team_a_runs=totals["a"]["runs"],
        team_a_wickets=totals["a"]["wickets"],
        team_b_runs=totals["b"]["runs"],
        team_b_wickets=totals["b"]["wickets"],
        public_scorecard_available=publication in {"published_live", "published_final"},
    )


async def match_results(
    db: AsyncSession, *, organization_id: str, actor_user_id: str
) -> list[SchoolMatchResult]:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_fixtures_results",
    )
    games = list(
        (await db.scalars(_school_games_stmt(organization_id).order_by(models.Game.id))).all()
    )
    return [result for game in games if (result := _match_result(game)) is not None]


async def fixture_summaries(
    db: AsyncSession, *, organization_id: str, actor_user_id: str
) -> list[SchoolFixtureSummary]:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_fixtures_results",
    )
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
    )
    rows = await db.execute(
        select(models.Fixture, models.Tournament, models.Game)
        .join(
            models.Tournament,
            and_(
                models.Tournament.id == models.Fixture.tournament_id,
                models.Tournament.organization_id == organization_id,
            ),
        )
        .outerjoin(models.Game, models.Game.id == models.Fixture.game_id)
        .where(
            models.Fixture.team_a_id.is_not(None),
            models.Fixture.team_b_id.is_not(None),
        )
        .order_by(
            models.Fixture.scheduled_date,
            models.Fixture.match_number,
            models.Fixture.id,
        )
    )
    output: list[SchoolFixtureSummary] = []
    for fixture, competition, game in rows:
        publication = (game.publication_state or "private") if game is not None else None
        output.append(
            SchoolFixtureSummary(
                fixture_id=fixture.id,
                competition_id=competition.id,
                competition_name=competition.name,
                team_a_id=str(fixture.team_a_id),
                team_a_name=fixture.team_a_name,
                team_b_id=str(fixture.team_b_id),
                team_b_name=fixture.team_b_name,
                match_number=fixture.match_number,
                venue=fixture.venue,
                scheduled_date=fixture.scheduled_date,
                fixture_status=fixture.status,
                game_id=fixture.game_id,
                game_status=game.status.value if game is not None else None,
                result=_result_text(game.result) if game is not None else None,
                publication_state=publication,
                public_scorecard_available=publication in {"published_live", "published_final"},
            )
        )
    return output
