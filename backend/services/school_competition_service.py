"""Tenant-safe School competition, fixture, standings, and publication contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from backend.api.schemas.school_competitions import (
    PublicSchoolScorecard,
    SchoolCompetitionCreate,
    SchoolCompetitionUpdate,
    SchoolFixtureCreate,
    SchoolFixtureUpdate,
    SchoolPublicationUpdate,
    SchoolStandingEntry,
    SchoolStandingsResponse,
)
from backend.services import organization_service
from backend.services.organization_entitlement_service import (
    organization_has_capability,
    require_organization_capability,
)
from backend.sql_app import models
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

READ_ROLES = frozenset({"owner", "admin", "coach", "scorer", "viewer"})
EDIT_ROLES = frozenset({"owner", "admin", "coach"})
DELETE_ROLES = frozenset({"owner", "admin"})
LINK_ROLES = frozenset({"owner", "admin", "coach", "scorer"})
PUBLISH_ROLES = LINK_ROLES


@dataclass(frozen=True)
class SchoolCompetitionServiceError(Exception):
    status_code: int
    detail: str


def _not_found(resource: str) -> SchoolCompetitionServiceError:
    return SchoolCompetitionServiceError(404, f"{resource} not found")


def _forbidden() -> SchoolCompetitionServiceError:
    return SchoolCompetitionServiceError(403, "Insufficient organization role")


async def _authorize(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    capability: str,
    allowed_roles: frozenset[str],
) -> models.OrganizationMembership:
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability=capability,
    )
    organization, membership = await organization_service.get_organization_for_member(
        db, organization_id=organization_id, user_id=actor_user_id
    )
    if organization.organization_type != "school" or membership.role not in allowed_roles:
        raise _forbidden()
    return membership


async def _competition(
    db: AsyncSession, *, organization_id: str, competition_id: str
) -> models.Tournament:
    competition = await db.scalar(
        select(models.Tournament).where(
            models.Tournament.id == competition_id,
            models.Tournament.organization_id == organization_id,
        )
    )
    if competition is None:
        raise _not_found("Competition")
    return competition


async def list_competitions(
    db: AsyncSession, *, organization_id: str, actor_user_id: str
) -> list[models.Tournament]:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
        allowed_roles=READ_ROLES,
    )
    result = await db.scalars(
        select(models.Tournament)
        .where(models.Tournament.organization_id == organization_id)
        .order_by(models.Tournament.start_date, models.Tournament.name, models.Tournament.id)
    )
    return list(result.all())


async def create_competition(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    payload: SchoolCompetitionCreate,
) -> models.Tournament:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
        allowed_roles=EDIT_ROLES,
    )
    competition = models.Tournament(organization_id=organization_id, **payload.model_dump())
    db.add(competition)
    await db.commit()
    await db.refresh(competition)
    return competition


async def get_competition(
    db: AsyncSession, *, organization_id: str, actor_user_id: str, competition_id: str
) -> models.Tournament:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
        allowed_roles=READ_ROLES,
    )
    return await _competition(db, organization_id=organization_id, competition_id=competition_id)


async def update_competition(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    competition_id: str,
    payload: SchoolCompetitionUpdate,
) -> models.Tournament:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
        allowed_roles=EDIT_ROLES,
    )
    competition = await _competition(
        db, organization_id=organization_id, competition_id=competition_id
    )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(competition, field, value)
    await db.commit()
    await db.refresh(competition)
    return competition


async def delete_competition(
    db: AsyncSession, *, organization_id: str, actor_user_id: str, competition_id: str
) -> None:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
        allowed_roles=DELETE_ROLES,
    )
    competition = await _competition(
        db, organization_id=organization_id, competition_id=competition_id
    )
    await db.delete(competition)
    await db.commit()


async def add_team(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    competition_id: str,
    team_id: str,
) -> models.TournamentTeam:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
        allowed_roles=EDIT_ROLES,
    )
    await _competition(db, organization_id=organization_id, competition_id=competition_id)
    team = await db.scalar(
        select(models.Team).where(
            models.Team.id == team_id,
            models.Team.organization_id == organization_id,
            models.Team.status == "active",
        )
    )
    if team is None:
        raise _not_found("Team")
    entrant = models.TournamentTeam(
        tournament_id=competition_id, team_id=team.id, team_name=team.name, team_data={}
    )
    db.add(entrant)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise SchoolCompetitionServiceError(409, "Team already belongs to competition") from exc
    await db.refresh(entrant)
    return entrant


async def list_teams(
    db: AsyncSession, *, organization_id: str, actor_user_id: str, competition_id: str
) -> list[models.TournamentTeam]:
    await get_competition(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        competition_id=competition_id,
    )
    rows = await db.scalars(
        select(models.TournamentTeam)
        .where(
            models.TournamentTeam.tournament_id == competition_id,
            models.TournamentTeam.team_id.is_not(None),
        )
        .order_by(models.TournamentTeam.team_name, models.TournamentTeam.id)
    )
    return list(rows.all())


async def remove_team(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    competition_id: str,
    entrant_id: int,
) -> None:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
        allowed_roles=DELETE_ROLES,
    )
    await _competition(db, organization_id=organization_id, competition_id=competition_id)
    entrant = await db.scalar(
        select(models.TournamentTeam).where(
            models.TournamentTeam.id == entrant_id,
            models.TournamentTeam.tournament_id == competition_id,
            models.TournamentTeam.team_id.is_not(None),
        )
    )
    if entrant is None:
        raise _not_found("Competition Team")
    fixture = await db.scalar(
        select(models.Fixture.id).where(
            models.Fixture.tournament_id == competition_id,
            (models.Fixture.team_a_id == entrant.team_id)
            | (models.Fixture.team_b_id == entrant.team_id),
        )
    )
    if fixture is not None:
        raise SchoolCompetitionServiceError(409, "Team is referenced by a fixture")
    await db.delete(entrant)
    await db.commit()


async def _fixture(
    db: AsyncSession, *, organization_id: str, competition_id: str, fixture_id: str
) -> models.Fixture:
    await _competition(db, organization_id=organization_id, competition_id=competition_id)
    fixture = await db.scalar(
        select(models.Fixture).where(
            models.Fixture.id == fixture_id,
            models.Fixture.tournament_id == competition_id,
            models.Fixture.team_a_id.is_not(None),
            models.Fixture.team_b_id.is_not(None),
        )
    )
    if fixture is None:
        raise _not_found("Fixture")
    return fixture


async def create_fixture(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    competition_id: str,
    payload: SchoolFixtureCreate,
) -> models.Fixture:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_fixtures_results",
        allowed_roles=EDIT_ROLES,
    )
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
    )
    await _competition(db, organization_id=organization_id, competition_id=competition_id)
    rows = await db.execute(
        select(models.Team.id, models.Team.name).where(
            models.Team.organization_id == organization_id,
            models.Team.status == "active",
            models.Team.id.in_([payload.team_a_id, payload.team_b_id]),
        )
    )
    teams = {row.id: row.name for row in rows}
    if set(teams) != {payload.team_a_id, payload.team_b_id}:
        raise _not_found("Team")
    entrant_ids = set(
        (
            await db.scalars(
                select(models.TournamentTeam.team_id).where(
                    models.TournamentTeam.tournament_id == competition_id,
                    models.TournamentTeam.team_id.in_([payload.team_a_id, payload.team_b_id]),
                )
            )
        ).all()
    )
    if entrant_ids != {payload.team_a_id, payload.team_b_id}:
        raise SchoolCompetitionServiceError(422, "Fixture Teams must be competition entrants")
    values = payload.model_dump(exclude={"team_a_id", "team_b_id"})
    fixture = models.Fixture(
        tournament_id=competition_id,
        team_a_id=payload.team_a_id,
        team_b_id=payload.team_b_id,
        team_a_name=teams[payload.team_a_id],
        team_b_name=teams[payload.team_b_id],
        **values,
    )
    db.add(fixture)
    await db.commit()
    await db.refresh(fixture)
    return fixture


async def list_fixtures(
    db: AsyncSession, *, organization_id: str, actor_user_id: str, competition_id: str
) -> list[models.Fixture]:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_fixtures_results",
        allowed_roles=READ_ROLES,
    )
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
    )
    await _competition(db, organization_id=organization_id, competition_id=competition_id)
    rows = await db.scalars(
        select(models.Fixture)
        .where(
            models.Fixture.tournament_id == competition_id,
            models.Fixture.team_a_id.is_not(None),
            models.Fixture.team_b_id.is_not(None),
        )
        .order_by(models.Fixture.scheduled_date, models.Fixture.match_number, models.Fixture.id)
    )
    return list(rows.all())


async def get_fixture(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    competition_id: str,
    fixture_id: str,
) -> models.Fixture:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_fixtures_results",
        allowed_roles=READ_ROLES,
    )
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
    )
    return await _fixture(
        db, organization_id=organization_id, competition_id=competition_id, fixture_id=fixture_id
    )


async def update_fixture(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    competition_id: str,
    fixture_id: str,
    payload: SchoolFixtureUpdate,
) -> models.Fixture:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_fixtures_results",
        allowed_roles=EDIT_ROLES,
    )
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
    )
    fixture = await _fixture(
        db, organization_id=organization_id, competition_id=competition_id, fixture_id=fixture_id
    )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(fixture, field, value)
    await db.commit()
    await db.refresh(fixture)
    return fixture


async def delete_fixture(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    competition_id: str,
    fixture_id: str,
) -> None:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_fixtures_results",
        allowed_roles=DELETE_ROLES,
    )
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
    )
    fixture = await _fixture(
        db, organization_id=organization_id, competition_id=competition_id, fixture_id=fixture_id
    )
    await db.delete(fixture)
    await db.commit()


def _school_source(team: dict[str, Any]) -> tuple[str | None, str | None]:
    source = team.get("school_source")
    if not isinstance(source, dict):
        return None, None
    organization_id = source.get("organization_id")
    team_id = source.get("team_id")
    return (
        organization_id if isinstance(organization_id, str) else None,
        team_id if isinstance(team_id, str) else None,
    )


def school_game_organization_id(game: models.Game) -> str | None:
    org_a, _ = _school_source(game.team_a)
    org_b, _ = _school_source(game.team_b)
    return org_a if org_a is not None and org_a == org_b else None


async def link_fixture_game(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    competition_id: str,
    fixture_id: str,
    game_id: str,
) -> models.Fixture:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_fixtures_results",
        allowed_roles=LINK_ROLES,
    )
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
    )
    fixture = await _fixture(
        db, organization_id=organization_id, competition_id=competition_id, fixture_id=fixture_id
    )
    game = await db.get(models.Game, game_id)
    if game is None:
        raise _not_found("Game")
    org_a, team_a_id = _school_source(game.team_a)
    org_b, team_b_id = _school_source(game.team_b)
    if (
        org_a != organization_id
        or org_b != organization_id
        or team_a_id != fixture.team_a_id
        or team_b_id != fixture.team_b_id
    ):
        raise _not_found("Game")
    already_linked = await db.scalar(
        select(models.Fixture.id).where(
            models.Fixture.game_id == game_id,
            models.Fixture.id != fixture.id,
            models.Fixture.team_a_id.is_not(None),
            models.Fixture.team_b_id.is_not(None),
        )
    )
    if already_linked is not None:
        raise SchoolCompetitionServiceError(409, "Game is already linked to a fixture")
    fixture.game_id = game_id
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise SchoolCompetitionServiceError(409, "Game is already linked to a fixture") from exc
    await db.refresh(fixture)
    return fixture


def _winner_team_id(game: models.Game, fixture: models.Fixture) -> str | Literal["draw"] | None:
    if game.result == "Match tied":
        return "draw"
    if not game.result or " won by " not in game.result:
        return None
    winner_name = game.result.split(" won by ", 1)[0]
    team_a_name = str(game.team_a.get("name", ""))
    team_b_name = str(game.team_b.get("name", ""))
    if team_a_name == team_b_name:
        return None
    if winner_name == team_a_name:
        return fixture.team_a_id
    if winner_name == team_b_name:
        return fixture.team_b_id
    return None


async def standings(
    db: AsyncSession, *, organization_id: str, actor_user_id: str, competition_id: str
) -> SchoolStandingsResponse:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_competitions",
        allowed_roles=READ_ROLES,
    )
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_fixtures_results",
    )
    await _competition(db, organization_id=organization_id, competition_id=competition_id)
    entrants = (
        await db.scalars(
            select(models.TournamentTeam).where(
                models.TournamentTeam.tournament_id == competition_id,
                models.TournamentTeam.team_id.is_not(None),
            )
        )
    ).all()
    values: dict[str, dict[str, int | str]] = {
        str(entry.team_id): {
            "team_id": str(entry.team_id),
            "team_name": entry.team_name,
            "matches_played": 0,
            "matches_won": 0,
            "matches_lost": 0,
            "matches_drawn": 0,
            "points": 0,
        }
        for entry in entrants
    }
    rows = await db.execute(
        select(models.Fixture, models.Game)
        .join(models.Game, models.Game.id == models.Fixture.game_id)
        .where(
            models.Fixture.tournament_id == competition_id,
            models.Fixture.team_a_id.is_not(None),
            models.Fixture.team_b_id.is_not(None),
            models.Game.status == models.GameStatus.completed,
        )
    )
    unresolved = 0
    seen_games: set[str] = set()
    for fixture, game in rows:
        if game.id in seen_games:
            continue
        seen_games.add(game.id)
        if fixture.team_a_id not in values or fixture.team_b_id not in values:
            unresolved += 1
            continue
        winner = _winner_team_id(game, fixture)
        if winner is None:
            unresolved += 1
            continue
        a = values[str(fixture.team_a_id)]
        b = values[str(fixture.team_b_id)]
        a["matches_played"] = int(a["matches_played"]) + 1
        b["matches_played"] = int(b["matches_played"]) + 1
        if winner == "draw":
            a["matches_drawn"] = int(a["matches_drawn"]) + 1
            b["matches_drawn"] = int(b["matches_drawn"]) + 1
            a["points"] = int(a["points"]) + 1
            b["points"] = int(b["points"]) + 1
        else:
            loser = b if winner == fixture.team_a_id else a
            winning = a if winner == fixture.team_a_id else b
            winning["matches_won"] = int(winning["matches_won"]) + 1
            winning["points"] = int(winning["points"]) + 2
            loser["matches_lost"] = int(loser["matches_lost"]) + 1
    entries = [SchoolStandingEntry.model_validate(value) for value in values.values()]
    entries.sort(key=lambda item: (-item.points, -item.matches_won, item.team_name, item.team_id))
    return SchoolStandingsResponse(
        competition_id=competition_id,
        entries=entries,
        unresolved_completed_games=unresolved,
    )


async def require_school_game_member(
    db: AsyncSession, *, game: models.Game, user: models.User | None
) -> None:
    organization_id = school_game_organization_id(game)
    if organization_id is None:
        return
    if user is None or not user.is_active:
        raise _not_found("Game")
    try:
        await organization_service.get_organization_for_member(
            db, organization_id=organization_id, user_id=user.id
        )
    except organization_service.OrganizationServiceError as exc:
        raise _not_found("Game") from exc


async def publication(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    game_id: str,
    payload: SchoolPublicationUpdate | None = None,
) -> tuple[models.Game, str]:
    allowed_roles = PUBLISH_ROLES if payload is not None else READ_ROLES
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability="school_live_scorecards",
        allowed_roles=allowed_roles,
    )
    game = await db.get(models.Game, game_id)
    if game is None or school_game_organization_id(game) != organization_id:
        raise _not_found("Game")
    if payload is not None:
        if (
            payload.publication_state == "published_final"
            and game.status != models.GameStatus.completed
        ):
            raise SchoolCompetitionServiceError(409, "Only a completed Game can be final-published")
        game.publication_state = payload.publication_state
        await db.commit()
        await db.refresh(game)
    return game, game.publication_state or "private"


def _public_team(team: dict[str, Any]) -> dict[str, Any]:
    raw_players = team.get("players")
    players: list[Any] = raw_players if isinstance(raw_players, list) else []
    return {
        "name": str(team.get("name", "")),
        "players": [
            {"name": str(player.get("name", ""))} for player in players if isinstance(player, dict)
        ],
    }


def _public_card(card: dict[str, Any]) -> list[dict[str, Any]]:
    allowed = {
        "runs",
        "balls_faced",
        "fours",
        "sixes",
        "is_out",
        "how_out",
        "overs_bowled",
        "runs_conceded",
        "wickets_taken",
    }
    rows: list[dict[str, Any]] = []
    for value in card.values():
        if not isinstance(value, dict):
            continue
        player_name = value.get("player_name", value.get("name"))
        if not isinstance(player_name, str):
            continue
        rows.append(
            {"player_name": player_name, **{key: value[key] for key in allowed if key in value}}
        )
    return rows


async def public_scorecard(db: AsyncSession, *, game_id: str) -> PublicSchoolScorecard:
    game = await db.get(models.Game, game_id)
    if game is None:
        raise _not_found("Scorecard")
    organization_id = school_game_organization_id(game)
    if organization_id is None or not await organization_has_capability(
        db, organization_id=organization_id, capability="school_live_scorecards"
    ):
        raise _not_found("Scorecard")
    if game.publication_state not in {"published_live", "published_final"}:
        raise _not_found("Scorecard")
    return PublicSchoolScorecard(
        game_id=game.id,
        publication_state=game.publication_state,
        status=game.status.value,
        team_a=_public_team(game.team_a),
        team_b=_public_team(game.team_b),
        match_type=game.match_type,
        overs_limit=game.overs_limit,
        days_limit=game.days_limit,
        overs_per_day=game.overs_per_day,
        toss_winner_team=game.toss_winner_team,
        decision=game.decision,
        batting_team_name=game.batting_team_name,
        bowling_team_name=game.bowling_team_name,
        total_runs=game.total_runs,
        total_wickets=game.total_wickets,
        overs_completed=game.overs_completed,
        balls_this_over=game.balls_this_over,
        current_inning=game.current_inning,
        result=game.result,
        batting_scorecard=_public_card(game.batting_scorecard),
        bowling_scorecard=_public_card(game.bowling_scorecard),
    )
