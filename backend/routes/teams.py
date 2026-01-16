"""
Teams API routes for organization-level team management.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.security import get_current_user
from backend.sql_app.database import get_db
from backend.sql_app.models import Team, User
from backend.sql_app.schemas import TeamCreate, TeamRead, TeamUpdate
from backend.services.org_stats import (
    calculate_org_stats,
    get_org_teams_stats,
    get_tournament_leaderboards,
)


router = APIRouter(prefix="/api/teams", tags=["teams"])


def _can_manage_teams(user: User) -> bool:
    """Check if user has permission to manage teams."""
    role = (user.role or "").lower()
    return role in ("org_pro", "superuser", "coach_pro")


@router.get("", response_model=list[TeamRead])
async def list_teams(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[Team]:
    """
    List all teams the current user can access.
    - org_pro/superuser: see all teams they own
    - coach_pro: see teams they are assigned as coach
    """
    role = (user.role or "").lower()

    if role == "superuser":
        # Superusers can see all teams
        result = await db.execute(select(Team))
    elif role in ("org_pro", "coach_pro"):
        # See teams they own or coach
        result = await db.execute(
            select(Team).where((Team.owner_user_id == user.id) | (Team.coach_user_id == user.id))
        )
    else:
        # Regular users - no teams
        return []

    return list(result.scalars().all())


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team(
    payload: TeamCreate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Team:
    """Create a new team. Requires org_pro, coach_pro, or superuser role."""
    if not _can_manage_teams(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team management requires org_pro, coach_pro, or superuser role",
        )

    team = Team(
        name=payload.name,
        home_ground=payload.home_ground,
        season=payload.season,
        owner_user_id=user.id,
        coach_user_id=payload.coach_id,
        coach_name=payload.coach_name,
        players=[p.model_dump() for p in payload.players],
        competitions=[c.model_dump() for c in payload.competitions],
    )
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team


@router.get("/{team_id}", response_model=TeamRead)
async def get_team(
    team_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Team:
    """Get a specific team by ID."""
    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check access
    role = (user.role or "").lower()
    if role != "superuser" and team.owner_user_id != user.id and team.coach_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this team",
        )

    return team


@router.put("/{team_id}", response_model=TeamRead)
async def update_team(
    team_id: str,
    payload: TeamUpdate,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Team:
    """Update a team. Requires ownership or superuser role."""
    if not _can_manage_teams(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team management requires org_pro, coach_pro, or superuser role",
        )

    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check ownership (superuser can edit any)
    role = (user.role or "").lower()
    if role != "superuser" and team.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the team owner can edit this team",
        )

    # Update fields
    if payload.name is not None:
        team.name = payload.name
    if payload.home_ground is not None:
        team.home_ground = payload.home_ground
    if payload.season is not None:
        team.season = payload.season
    if payload.coach_name is not None:
        team.coach_name = payload.coach_name
    if payload.coach_id is not None:
        team.coach_user_id = payload.coach_id
    if payload.players is not None:
        team.players = [p.model_dump() for p in payload.players]
    if payload.competitions is not None:
        team.competitions = [c.model_dump() for c in payload.competitions]

    await db.commit()
    await db.refresh(team)
    return team


@router.delete("/{team_id}", responses={204: {"description": "Team deleted successfully"}})
async def delete_team(
    team_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a team. Requires ownership or superuser role."""
    if not _can_manage_teams(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team management requires org_pro, coach_pro, or superuser role",
        )

    result = await db.execute(select(Team).where(Team.id == team_id))
    team = result.scalar_one_or_none()

    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Team not found",
        )

    # Check ownership (superuser can delete any)
    role = (user.role or "").lower()
    if role != "superuser" and team.owner_user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the team owner can delete this team",
        )

    await db.delete(team)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

# ==============================================================================
# Organization Statistics Endpoints
# ==============================================================================


@router.get("/organizations/{org_id}/stats")
async def get_organization_stats(
    org_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Get organization-wide statistics including:
    - Total teams and matches played
    - Season win rate
    - Average run rate
    - Phase-based net run rates
    """
    return await calculate_org_stats(db, org_id)


@router.get("/organizations/{org_id}/teams")
async def get_organization_teams(
    org_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, list[dict[str, Any]]]:
    """
    Get statistics for all teams in an organization.
    
    Returns team records, win percentages, NRR, and average scores.
    """
    teams_stats = await get_org_teams_stats(db, org_id)
    return {"teams": teams_stats}