"""Organization-scoped School Free statistics, fixtures, and results routes."""

from __future__ import annotations

from typing import Annotated, Never

from backend.api.schemas.school_statistics import (
    SchoolFixtureSummary,
    SchoolMatchResult,
    SchoolPlayerStatistics,
    SchoolTeamStatistics,
)
from backend.security import get_current_active_user
from backend.services import organization_service, school_statistics_service
from backend.services.organization_entitlement_service import OrganizationCapabilityError
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["school-statistics"])


def _raise_service_error(exc: Exception) -> Never:
    if isinstance(exc, OrganizationCapabilityError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization capability not enabled: {exc.capability}",
        ) from exc
    if isinstance(
        exc,
        (
            organization_service.OrganizationServiceError,
            school_statistics_service.SchoolStatisticsServiceError,
        ),
    ):
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    raise exc


SERVICE_ERRORS = (
    organization_service.OrganizationServiceError,
    school_statistics_service.SchoolStatisticsServiceError,
    OrganizationCapabilityError,
)


@router.get(
    "/api/organizations/{organization_id}/statistics/players",
    response_model=list[SchoolPlayerStatistics],
)
async def list_player_statistics(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SchoolPlayerStatistics]:
    try:
        return await school_statistics_service.player_statistics(
            db, organization_id=organization_id, actor_user_id=current_user.id
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/api/organizations/{organization_id}/statistics/players/{player_profile_id}",
    response_model=SchoolPlayerStatistics,
)
async def get_player_statistics(
    organization_id: str,
    player_profile_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolPlayerStatistics:
    try:
        rows = await school_statistics_service.player_statistics(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            player_profile_id=player_profile_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return rows[0]


@router.get(
    "/api/organizations/{organization_id}/statistics/teams",
    response_model=list[SchoolTeamStatistics],
)
async def list_team_statistics(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SchoolTeamStatistics]:
    try:
        return await school_statistics_service.team_statistics(
            db, organization_id=organization_id, actor_user_id=current_user.id
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/api/organizations/{organization_id}/statistics/teams/{team_id}",
    response_model=SchoolTeamStatistics,
)
async def get_team_statistics(
    organization_id: str,
    team_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolTeamStatistics:
    try:
        rows = await school_statistics_service.team_statistics(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            team_id=team_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return rows[0]


@router.get(
    "/api/organizations/{organization_id}/results",
    response_model=list[SchoolMatchResult],
)
async def list_results(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SchoolMatchResult]:
    try:
        return await school_statistics_service.match_results(
            db, organization_id=organization_id, actor_user_id=current_user.id
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/api/organizations/{organization_id}/fixtures",
    response_model=list[SchoolFixtureSummary],
)
async def list_fixtures(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SchoolFixtureSummary]:
    try:
        return await school_statistics_service.fixture_summaries(
            db, organization_id=organization_id, actor_user_id=current_user.id
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
