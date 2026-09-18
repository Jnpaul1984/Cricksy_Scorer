"""Authenticated organization-scoped School match setup routes."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.school_matches import SchoolMatchCreate, SchoolMatchCreateResponse
from backend.security import get_current_active_user
from backend.services import (
    organization_entitlement_service,
    organization_service,
    school_match_service,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/organizations", tags=["school-matches"])


def _service_error(
    exc: (
        organization_service.OrganizationServiceError
        | organization_entitlement_service.OrganizationCapabilityError
        | school_match_service.SchoolMatchServiceError
    ),
) -> NoReturn:
    if isinstance(exc, organization_entitlement_service.OrganizationCapabilityError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization capability not enabled: {exc.capability}",
        ) from exc
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post(
    "/{organization_id}/matches",
    response_model=SchoolMatchCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_school_match(
    organization_id: str,
    payload: SchoolMatchCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolMatchCreateResponse:
    try:
        game = await school_match_service.create_school_match(
            db,
            organization_id=organization_id,
            payload=payload,
            actor_user_id=current_user.id,
        )
    except (
        organization_service.OrganizationServiceError,
        organization_entitlement_service.OrganizationCapabilityError,
        school_match_service.SchoolMatchServiceError,
    ) as exc:
        _service_error(exc)

    return SchoolMatchCreateResponse(
        game_id=game.id,
        organization_id=organization_id,
        team_a_id=str(game.team_a["school_source"]["team_id"]),
        team_b_id=str(game.team_b["school_source"]["team_id"]),
        team_a_name=str(game.team_a["name"]),
        team_b_name=str(game.team_b["name"]),
        team_a_player_profile_ids=[str(player["id"]) for player in game.team_a["players"]],
        team_b_player_profile_ids=[str(player["id"]) for player in game.team_b["players"]],
    )
