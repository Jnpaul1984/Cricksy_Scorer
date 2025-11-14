"""Tournament management API endpoints"""

from __future__ import annotations

from typing import Annotated, Any

from backend.sql_app import schemas, tournament_crud
from backend.sql_app.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.post("/", response_model=schemas.TournamentResponse, status_code=201)
async def create_tournament(
    tournament: schemas.TournamentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Create a new tournament"""
    return await tournament_crud.create_tournament(db, tournament)


@router.get("/", response_model=list[schemas.TournamentResponse])
async def list_tournaments(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """List all tournaments"""
    return await tournament_crud.get_tournaments(db, skip=skip, limit=limit)


@router.get("/{tournament_id}", response_model=schemas.TournamentResponse)
async def get_tournament(
    tournament_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Get a specific tournament"""
    tournament = await tournament_crud.get_tournament(db, tournament_id)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament


@router.patch("/{tournament_id}", response_model=schemas.TournamentResponse)
async def update_tournament(
    tournament_id: str,
    tournament_update: schemas.TournamentUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Update a tournament"""
    tournament = await tournament_crud.update_tournament(db, tournament_id, tournament_update)
    if not tournament:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return tournament


@router.delete("/{tournament_id}")
async def delete_tournament(
    tournament_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Delete a tournament"""
    success = await tournament_crud.delete_tournament(db, tournament_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return {"status": "deleted"}


# Team management endpoints


@router.post(
    "/{tournament_id}/teams", response_model=schemas.TournamentTeamResponse, status_code=201
)
async def add_team(
    tournament_id: str,
    team: schemas.TeamAdd,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Add a team to a tournament"""
    result = await tournament_crud.add_team_to_tournament(db, tournament_id, team)
    if not result:
        raise HTTPException(status_code=404, detail="Tournament not found")
    return result


@router.get("/{tournament_id}/teams", response_model=list[schemas.TournamentTeamResponse])
async def get_teams(
    tournament_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Get all teams in a tournament"""
    return await tournament_crud.get_tournament_teams(db, tournament_id)


@router.get("/{tournament_id}/points-table", response_model=list[schemas.PointsTableEntry])
async def get_points_table(
    tournament_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Get the points table for a tournament"""
    return await tournament_crud.get_points_table(db, tournament_id)


# Fixture management endpoints


@router.post("/fixtures", response_model=schemas.FixtureResponse, status_code=201)
async def create_fixture(
    fixture: schemas.FixtureCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Create a new fixture"""
    return await tournament_crud.create_fixture(db, fixture)


@router.get("/fixtures/{fixture_id}", response_model=schemas.FixtureResponse)
async def get_fixture(
    fixture_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Get a specific fixture"""
    fixture = await tournament_crud.get_fixture(db, fixture_id)
    if not fixture:
        raise HTTPException(status_code=404, detail="Fixture not found")
    return fixture


@router.get("/{tournament_id}/fixtures", response_model=list[schemas.FixtureResponse])
async def get_fixtures(
    tournament_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Get all fixtures for a tournament"""
    return await tournament_crud.get_tournament_fixtures(db, tournament_id)


@router.patch("/fixtures/{fixture_id}", response_model=schemas.FixtureResponse)
async def update_fixture(
    fixture_id: str,
    fixture_update: schemas.FixtureUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Any:
    """Update a fixture"""
    fixture = await tournament_crud.update_fixture(db, fixture_id, fixture_update)
    if not fixture:
        raise HTTPException(status_code=404, detail="Fixture not found")
    return fixture


@router.delete("/fixtures/{fixture_id}")
async def delete_fixture(
    fixture_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Delete a fixture"""
    success = await tournament_crud.delete_fixture(db, fixture_id)
    if not success:
        raise HTTPException(status_code=404, detail="Fixture not found")
    return {"status": "deleted"}
