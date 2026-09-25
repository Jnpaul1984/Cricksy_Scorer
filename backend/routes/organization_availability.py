"""Shared School/Club organization player availability routes."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.organization_availability import (
    AvailabilityFilter,
    AvailabilityTargetType,
    OrganizationAvailabilitySummaryResponse,
    OrganizationAvailabilityTargetResponse,
    OrganizationAvailabilityTargetUpdate,
    OrganizationPlayerAvailabilityHistoryResponse,
    OrganizationPlayerAvailabilityResponse,
    OrganizationPlayerAvailabilityUpdate,
)
from backend.security import get_current_active_user
from backend.services import (
    organization_availability_service,
    organization_entitlement_service,
    organization_service,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/organizations", tags=["organization-availability"])

SERVICE_ERRORS = (
    organization_availability_service.OrganizationAvailabilityServiceError,
    organization_service.OrganizationServiceError,
    organization_entitlement_service.OrganizationCapabilityError,
)


def _raise_service_error(
    exc: (
        organization_availability_service.OrganizationAvailabilityServiceError
        | organization_service.OrganizationServiceError
        | organization_entitlement_service.OrganizationCapabilityError
    ),
) -> NoReturn:
    if isinstance(exc, organization_entitlement_service.OrganizationCapabilityError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization capability not enabled: {exc.capability}",
        ) from exc
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "/{organization_id}/availability/{target_type}/{target_id}",
    response_model=OrganizationAvailabilitySummaryResponse,
)
async def get_availability_summary(
    organization_id: str,
    target_type: AvailabilityTargetType,
    target_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    state_filter: Annotated[AvailabilityFilter | None, Query(alias="state")] = None,
    team_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> OrganizationAvailabilitySummaryResponse:
    try:
        return await organization_availability_service.availability_summary(
            db,
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
            actor_user_id=current_user.id,
            state_filter=state_filter,
            team_id=team_id,
            limit=limit,
            offset=offset,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.patch(
    "/{organization_id}/availability/{target_type}/{target_id}",
    response_model=OrganizationAvailabilityTargetResponse,
)
async def update_availability_target(
    organization_id: str,
    target_type: AvailabilityTargetType,
    target_id: str,
    payload: OrganizationAvailabilityTargetUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationAvailabilityTargetResponse:
    try:
        return await organization_availability_service.update_target_deadline(
            db,
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
            actor_user_id=current_user.id,
            response_deadline=payload.response_deadline,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.put(
    "/{organization_id}/availability/{target_type}/{target_id}/players/{roster_membership_id}",
    response_model=OrganizationPlayerAvailabilityResponse,
)
async def record_player_availability(
    organization_id: str,
    target_type: AvailabilityTargetType,
    target_id: str,
    roster_membership_id: str,
    payload: OrganizationPlayerAvailabilityUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPlayerAvailabilityResponse:
    try:
        return await organization_availability_service.record_player_availability(
            db,
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
            roster_membership_id=roster_membership_id,
            actor_user_id=current_user.id,
            state=payload.state,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/{organization_id}/availability/{target_type}/{target_id}/players/{roster_membership_id}/history",
    response_model=OrganizationPlayerAvailabilityHistoryResponse,
)
async def get_player_availability_history(
    organization_id: str,
    target_type: AvailabilityTargetType,
    target_id: str,
    roster_membership_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPlayerAvailabilityHistoryResponse:
    try:
        return await organization_availability_service.player_availability_history(
            db,
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
            roster_membership_id=roster_membership_id,
            actor_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
