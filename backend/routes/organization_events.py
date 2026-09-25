"""Shared School/Club organization event and composed calendar routes."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, NoReturn

from backend.api.schemas.organization_events import (
    OrganizationCalendarResponse,
    OrganizationEventCreate,
    OrganizationEventListResponse,
    OrganizationEventResponse,
    OrganizationEventUpdate,
)
from backend.security import get_current_active_user
from backend.services import (
    organization_entitlement_service,
    organization_event_service,
    organization_service,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/organizations", tags=["organization-events"])

SERVICE_ERRORS = (
    organization_event_service.OrganizationEventServiceError,
    organization_service.OrganizationServiceError,
    organization_entitlement_service.OrganizationCapabilityError,
)


def _raise_service_error(
    exc: (
        organization_event_service.OrganizationEventServiceError
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


def _response(
    record: organization_event_service.OrganizationEventRecord,
) -> OrganizationEventResponse:
    event = record.event
    return OrganizationEventResponse(
        id=event.id,
        organization_id=event.organization_id,
        event_type=event.event_type,
        title=event.title,
        description=event.description,
        start_at=event.start_at,
        end_at=event.end_at,
        location=event.location,
        participant_scope=event.participant_scope,
        team_ids=record.team_ids,
        roster_membership_ids=record.roster_membership_ids,
        status=event.status,
        created_by_user_id=event.created_by_user_id,
        updated_by_user_id=event.updated_by_user_id,
        cancelled_by_user_id=event.cancelled_by_user_id,
        cancelled_at=event.cancelled_at,
        created_at=event.created_at,
        updated_at=event.updated_at,
    )


@router.post(
    "/{organization_id}/events",
    response_model=OrganizationEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_event(
    organization_id: str,
    payload: OrganizationEventCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationEventResponse:
    try:
        record = await organization_event_service.create_event(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return _response(record)


@router.get(
    "/{organization_id}/events",
    response_model=OrganizationEventListResponse,
)
async def list_events(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_at: Annotated[dt.datetime | None, Query()] = None,
    to_at: Annotated[dt.datetime | None, Query()] = None,
    upcoming: Annotated[bool, Query()] = False,
    include_cancelled: Annotated[bool, Query()] = False,
    team_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> OrganizationEventListResponse:
    try:
        records, total = await organization_event_service.list_events(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            from_at=from_at,
            to_at=to_at,
            upcoming=upcoming,
            include_cancelled=include_cancelled,
            team_id=team_id,
            limit=limit,
            offset=offset,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationEventListResponse(
        items=[_response(record) for record in records],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{organization_id}/events/{event_id}",
    response_model=OrganizationEventResponse,
)
async def get_event(
    organization_id: str,
    event_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationEventResponse:
    try:
        record = await organization_event_service.get_event(
            db,
            organization_id=organization_id,
            event_id=event_id,
            actor_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return _response(record)


@router.patch(
    "/{organization_id}/events/{event_id}",
    response_model=OrganizationEventResponse,
)
async def update_event(
    organization_id: str,
    event_id: str,
    payload: OrganizationEventUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationEventResponse:
    try:
        record = await organization_event_service.update_event(
            db,
            organization_id=organization_id,
            event_id=event_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return _response(record)


@router.post(
    "/{organization_id}/events/{event_id}/cancel",
    response_model=OrganizationEventResponse,
)
async def cancel_event(
    organization_id: str,
    event_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationEventResponse:
    try:
        record = await organization_event_service.cancel_event(
            db,
            organization_id=organization_id,
            event_id=event_id,
            actor_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return _response(record)


@router.get(
    "/{organization_id}/calendar",
    response_model=OrganizationCalendarResponse,
)
async def organization_calendar(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    from_at: Annotated[dt.datetime | None, Query()] = None,
    to_at: Annotated[dt.datetime | None, Query()] = None,
    upcoming: Annotated[bool, Query()] = False,
    include_cancelled: Annotated[bool, Query()] = False,
    team_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> OrganizationCalendarResponse:
    try:
        items, total = await organization_event_service.calendar(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            from_at=from_at,
            to_at=to_at,
            upcoming=upcoming,
            include_cancelled=include_cancelled,
            team_id=team_id,
            limit=limit,
            offset=offset,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationCalendarResponse(items=items, total=total, limit=limit, offset=offset)
