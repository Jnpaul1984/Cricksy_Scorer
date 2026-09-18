"""CRUD operations for tournament management"""

from __future__ import annotations

import inspect
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.sql_app import models, schemas


async def _maybe_await(result: Any) -> None:
    """Await AsyncMock/awaitable results transparently."""
    if inspect.isawaitable(result):
        await result


async def create_tournament(
    db: AsyncSession, tournament_in: schemas.TournamentCreate
) -> models.Tournament:
    """Create a new tournament"""
    tournament = models.Tournament(
        name=tournament_in.name,
        description=tournament_in.description,
        tournament_type=tournament_in.tournament_type,
        start_date=tournament_in.start_date,
        end_date=tournament_in.end_date,
        organization_id=None,
    )
    await _maybe_await(db.add(tournament))
    await db.commit()
    await db.refresh(tournament)
    return tournament


async def get_tournament(db: AsyncSession, tournament_id: str) -> models.Tournament | None:
    """Get a legacy tournament by ID.

    Organization-owned tournaments are available only through the School APIs.
    """
    result = await db.execute(
        select(models.Tournament)
        .options(selectinload(models.Tournament.teams))
        .where(
            models.Tournament.id == tournament_id,
            models.Tournament.organization_id.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_tournaments(
    db: AsyncSession, skip: int = 0, limit: int = 100
) -> list[models.Tournament]:
    """Get legacy tournaments, excluding organization-owned School competitions."""
    result = await db.execute(
        select(models.Tournament)
        .options(selectinload(models.Tournament.teams))
        .where(models.Tournament.organization_id.is_(None))
        .offset(skip)
        .limit(limit)
        .order_by(models.Tournament.created_at.desc())
    )
    return list(result.scalars().all())


async def update_tournament(
    db: AsyncSession, tournament_id: str, tournament_update: schemas.TournamentUpdate
) -> models.Tournament | None:
    """Update a tournament"""
    tournament = await get_tournament(db, tournament_id)
    if not tournament:
        return None

    update_data = tournament_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(tournament, field, value)

    await db.commit()
    # Re-fetch to ensure we have the latest state and avoid "not persistent" errors
    return await get_tournament(db, tournament_id)


async def delete_tournament(db: AsyncSession, tournament_id: str) -> bool:
    """Delete a tournament"""
    tournament = await get_tournament(db, tournament_id)
    if not tournament:
        return False

    await db.delete(tournament)
    await db.commit()
    return True


# Team management


async def add_team_to_tournament(
    db: AsyncSession, tournament_id: str, team_data: schemas.TeamAdd
) -> models.TournamentTeam | None:
    """Add a team to a tournament"""
    tournament = await get_tournament(db, tournament_id)
    if not tournament:
        return None

    team = models.TournamentTeam(
        tournament_id=tournament_id,
        team_name=team_data.team_name,
        team_data=team_data.team_data,
    )
    await _maybe_await(db.add(team))
    await db.commit()
    await db.refresh(team)
    return team


async def get_tournament_teams(db: AsyncSession, tournament_id: str) -> list[models.TournamentTeam]:
    """Get teams only when their parent tournament is legacy/unscoped."""
    result = await db.execute(
        select(models.TournamentTeam)
        .join(
            models.Tournament,
            models.Tournament.id == models.TournamentTeam.tournament_id,
        )
        .where(
            models.TournamentTeam.tournament_id == tournament_id,
            models.Tournament.organization_id.is_(None),
        )
        .order_by(
            models.TournamentTeam.points.desc(),
            models.TournamentTeam.net_run_rate.desc(),
        )
    )
    return list(result.scalars().all())


async def update_team_stats(
    db: AsyncSession,
    tournament_id: str,
    team_name: str,
    won: bool = False,
    lost: bool = False,
    drawn: bool = False,
    runs_scored: int = 0,
    runs_conceded: int = 0,
    overs_faced: float = 0.0,
    overs_bowled: float = 0.0,
) -> models.TournamentTeam | None:
    """Update team statistics after a match"""
    result = await db.execute(
        select(models.TournamentTeam)
        .join(
            models.Tournament,
            models.Tournament.id == models.TournamentTeam.tournament_id,
        )
        .where(
            models.TournamentTeam.tournament_id == tournament_id,
            models.TournamentTeam.team_name == team_name,
            models.Tournament.organization_id.is_(None),
        )
    )
    team = result.scalar_one_or_none()
    if not team:
        return None

    team.matches_played += 1
    if won:
        team.matches_won += 1
        team.points += 2  # Standard points for a win
    elif lost:
        team.matches_lost += 1
    elif drawn:
        team.matches_drawn += 1
        team.points += 1  # Standard points for a draw

    # Calculate net run rate
    if overs_faced > 0 and overs_bowled > 0:
        run_rate_for = runs_scored / overs_faced
        run_rate_against = runs_conceded / overs_bowled
        team.net_run_rate = run_rate_for - run_rate_against

    await db.commit()
    await db.refresh(team)
    return team


# Fixture management


async def create_fixture(
    db: AsyncSession, fixture_in: schemas.FixtureCreate
) -> models.Fixture | None:
    """Create a fixture only within a legacy/unscoped tournament."""
    if await get_tournament(db, fixture_in.tournament_id) is None:
        return None

    fixture = models.Fixture(
        tournament_id=fixture_in.tournament_id,
        match_number=fixture_in.match_number,
        team_a_name=fixture_in.team_a_name,
        team_b_name=fixture_in.team_b_name,
        venue=fixture_in.venue,
        scheduled_date=fixture_in.scheduled_date,
    )
    await _maybe_await(db.add(fixture))
    await db.commit()
    await db.refresh(fixture)
    return fixture


async def get_fixture(db: AsyncSession, fixture_id: str) -> models.Fixture | None:
    """Get a fixture only when its parent tournament is legacy/unscoped."""
    result = await db.execute(
        select(models.Fixture)
        .join(models.Tournament, models.Tournament.id == models.Fixture.tournament_id)
        .where(
            models.Fixture.id == fixture_id,
            models.Tournament.organization_id.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def get_tournament_fixtures(db: AsyncSession, tournament_id: str) -> list[models.Fixture]:
    """Get fixtures only when their parent tournament is legacy/unscoped."""
    result = await db.execute(
        select(models.Fixture)
        .join(models.Tournament, models.Tournament.id == models.Fixture.tournament_id)
        .where(
            models.Fixture.tournament_id == tournament_id,
            models.Tournament.organization_id.is_(None),
        )
        .order_by(models.Fixture.scheduled_date, models.Fixture.match_number)
    )
    return list(result.scalars().all())


async def update_fixture(
    db: AsyncSession, fixture_id: str, fixture_update: schemas.FixtureUpdate
) -> models.Fixture | None:
    """Update a fixture"""
    fixture = await get_fixture(db, fixture_id)
    if not fixture:
        return None

    update_data = fixture_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(fixture, field, value)

    await db.commit()
    await db.refresh(fixture)
    return fixture


async def delete_fixture(db: AsyncSession, fixture_id: str) -> bool:
    """Delete a fixture"""
    fixture = await get_fixture(db, fixture_id)
    if not fixture:
        return False

    await db.delete(fixture)
    await db.commit()
    return True


async def get_points_table(db: AsyncSession, tournament_id: str) -> list[schemas.PointsTableEntry]:
    """Get the points table for a tournament"""
    teams = await get_tournament_teams(db, tournament_id)
    return [
        schemas.PointsTableEntry(
            team_name=team.team_name,
            matches_played=team.matches_played,
            matches_won=team.matches_won,
            matches_lost=team.matches_lost,
            matches_drawn=team.matches_drawn,
            points=team.points,
            net_run_rate=team.net_run_rate,
        )
        for team in teams
    ]


async def create_tournament_eager(
    db: AsyncSession, tournament_create: schemas.TournamentCreate
) -> models.Tournament:
    """Create tournament and re-query with teams eagerly loaded."""
    # Use existing create_tournament to insert/commit the tournament
    created = await create_tournament(db, tournament_create)

    # Re-query to eagerly load teams (so Pydantic/fastapi won't trigger lazy IO)
    result = await db.execute(
        select(models.Tournament)
        .options(selectinload(models.Tournament.teams))
        .filter_by(id=created.id)
    )
    tournament_with_teams = result.scalar_one()
    return tournament_with_teams
