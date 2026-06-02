"""Phase 10T — CPL Current-Season Roster: FastAPI routes.

Exposes:
  GET  /api/cpl-roster/teams        → list registered teams
  POST /api/cpl-roster/teams        → register a new team

  GET    /api/cpl-roster/players        → list players (optionally by team/season)
  POST   /api/cpl-roster/players        → register a new player
  PATCH  /api/cpl-roster/players/{id}   → update a player record

  POST /api/cpl-roster/import/preview   → preview a roster import (dry-run)
  POST /api/cpl-roster/import/apply     → apply a roster import (confirmed)

All endpoints:
- Require analyst_pro or org_pro role.
- Safe duplicate prevention by normalized player/team names.
- Returning-player detection across prior seasons.
- No historical import data is mutated.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.api.schemas.cpl_roster import (
    CplPlayerCreate,
    CplPlayerListResponse,
    CplPlayerResponse,
    CplPlayerUpdate,
    CplTeamCreate,
    CplTeamListResponse,
    CplTeamResponse,
    RosterImportApplyRequest,
    RosterImportApplyResponse,
    RosterImportPreviewResponse,
    RosterImportRow,
)
from backend.services.cpl_roster_service import (
    apply_roster_import,
    create_player,
    create_team,
    list_players,
    list_teams,
    preview_roster_import,
    update_player,
)
from backend.sql_app.database import get_db

router = APIRouter(prefix="/api/cpl-roster", tags=["cpl-roster"])

AllowedRoles = ["analyst_pro", "org_pro"]


# ---------------------------------------------------------------------------
# Team endpoints
# ---------------------------------------------------------------------------


@router.get("/teams", response_model=CplTeamListResponse)
async def list_cpl_teams(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
    competition_code: str = Query("CPL_MEN"),
    season: str | None = Query(None),
) -> CplTeamListResponse:
    """List registered CPL teams for a season.

    If season is omitted, returns teams from all seasons.
    """
    return await list_teams(db, competition_code=competition_code, season=season)


@router.post("/teams", response_model=CplTeamResponse, status_code=201)
async def register_cpl_team(
    body: CplTeamCreate,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> CplTeamResponse:
    """Register a new CPL team for a season.

    Raises 409 if a team with the same normalized name already exists.
    """
    try:
        team = await create_team(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CplTeamResponse.model_validate(team)


# ---------------------------------------------------------------------------
# Player endpoints
# ---------------------------------------------------------------------------


@router.get("/players", response_model=CplPlayerListResponse)
async def list_cpl_players(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
    competition_code: str = Query("CPL_MEN"),
    season: str | None = Query(None),
    team_name: str | None = Query(None),
    player_status: str | None = Query(None, alias="status"),
) -> CplPlayerListResponse:
    """List registered CPL players.

    Optionally filter by season, team, or status.
    Returns returning_count and new_count in the response.
    """
    return await list_players(
        db,
        competition_code=competition_code,
        season=season,
        team_name=team_name,
        status=player_status,
    )


@router.post("/players", response_model=CplPlayerResponse, status_code=201)
async def register_cpl_player(
    body: CplPlayerCreate,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> CplPlayerResponse:
    """Register a new CPL player for a season.

    Automatically detects returning players from prior seasons.
    Raises 409 if player already exists for this season.
    """
    try:
        player = await create_player(db, body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return CplPlayerResponse.model_validate(player)


@router.patch("/players/{player_id}", response_model=CplPlayerResponse)
async def update_cpl_player(
    player_id: str,
    body: CplPlayerUpdate,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> CplPlayerResponse:
    """Update a registered CPL player record (status, team, aliases, etc.)."""
    player = await update_player(db, player_id, body)
    if player is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Player '{player_id}' not found.",
        )
    return CplPlayerResponse.model_validate(player)


# ---------------------------------------------------------------------------
# Roster import endpoints
# ---------------------------------------------------------------------------


class RosterImportPreviewBody(BaseModel):
    """Request body for roster import preview."""

    rows: list[RosterImportRow]
    competition_code: str = "CPL_MEN"
    season: str


@router.post("/import/preview", response_model=RosterImportPreviewResponse)
async def roster_import_preview(
    body: RosterImportPreviewBody,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> RosterImportPreviewResponse:
    """Preview a roster import without applying any changes.

    Shows new teams, existing teams matched, new players, existing players
    matched, duplicates, returning players, warnings, and blockers.

    No data is changed by this endpoint.
    """
    if not body.rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No import rows provided.",
        )
    return await preview_roster_import(
        db,
        rows=body.rows,
        competition_code=body.competition_code,
        season=body.season,
    )


@router.post("/import/apply", response_model=RosterImportApplyResponse)
async def roster_import_apply(
    body: RosterImportApplyRequest,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> RosterImportApplyResponse:
    """Apply a previously previewed roster import.

    Requires confirm=true in the request body.
    Idempotent: existing records are updated rather than duplicated.
    """
    if not body.rows:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No import rows provided.",
        )
    return await apply_roster_import(db, body)
