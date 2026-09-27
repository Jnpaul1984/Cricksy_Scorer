"""Private School/Club organization event attendance routes."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, NoReturn

from backend.api.schemas.organization_attendance import (
    AttendanceFilter,
    OrganizationAttendanceRegisterResponse,
    OrganizationAttendanceSummaryResponse,
    OrganizationPlayerAttendanceHistoryResponse,
    OrganizationPlayerAttendanceResponse,
    OrganizationPlayerAttendanceUpdate,
)
from backend.security import get_current_active_user
from backend.services import (
    organization_attendance_service,
    organization_entitlement_service,
    organization_service,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/organizations", tags=["organization-attendance"])

SERVICE_ERRORS = (
    organization_attendance_service.OrganizationAttendanceServiceError,
    organization_service.OrganizationServiceError,
    organization_entitlement_service.OrganizationCapabilityError,
)


def _raise_service_error(
    exc: (
        organization_attendance_service.OrganizationAttendanceServiceError
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
    "/{organization_id}/attendance/events/{event_id}",
    response_model=OrganizationAttendanceRegisterResponse,
)
async def get_attendance_register(
    organization_id: str,
    event_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    state_filter: Annotated[AttendanceFilter | None, Query(alias="state")] = None,
    team_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> OrganizationAttendanceRegisterResponse:
    try:
        return await organization_attendance_service.attendance_register(
            db,
            organization_id=organization_id,
            event_id=event_id,
            actor_user_id=current_user.id,
            state_filter=state_filter,
            team_id=team_id,
            limit=limit,
            offset=offset,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.put(
    "/{organization_id}/attendance/events/{event_id}/players/{roster_membership_id}",
    response_model=OrganizationPlayerAttendanceResponse,
)
async def record_player_attendance(
    organization_id: str,
    event_id: str,
    roster_membership_id: str,
    payload: OrganizationPlayerAttendanceUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPlayerAttendanceResponse:
    try:
        return await organization_attendance_service.record_player_attendance(
            db,
            organization_id=organization_id,
            event_id=event_id,
            roster_membership_id=roster_membership_id,
            actor_user_id=current_user.id,
            state=payload.state,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/{organization_id}/attendance/events/{event_id}/players/{roster_membership_id}/history",
    response_model=OrganizationPlayerAttendanceHistoryResponse,
)
async def get_player_attendance_history(
    organization_id: str,
    event_id: str,
    roster_membership_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPlayerAttendanceHistoryResponse:
    try:
        return await organization_attendance_service.player_attendance_history(
            db,
            organization_id=organization_id,
            event_id=event_id,
            roster_membership_id=roster_membership_id,
            actor_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/{organization_id}/attendance/summary",
    response_model=OrganizationAttendanceSummaryResponse,
)
async def get_attendance_summary(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_at: Annotated[dt.datetime | None, Query()] = None,
    to_at: Annotated[dt.datetime | None, Query()] = None,
    team_id: Annotated[str | None, Query()] = None,
    roster_membership_id: Annotated[str | None, Query()] = None,
) -> OrganizationAttendanceSummaryResponse:
    try:
        return await organization_attendance_service.attendance_summary(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            from_at=from_at,
            to_at=to_at,
            team_id=team_id,
            roster_membership_id=roster_membership_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
