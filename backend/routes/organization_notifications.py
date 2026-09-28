"""Recipient-owned School/Club in-app notification routes."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.organization_notifications import (
    OrganizationNotificationCategory,
    OrganizationNotificationListResponse,
    OrganizationNotificationPreferenceListResponse,
    OrganizationNotificationPreferenceResponse,
    OrganizationNotificationPreferenceUpdate,
    OrganizationNotificationResponse,
    OrganizationNotificationUnreadCountResponse,
)
from backend.security import get_current_active_user
from backend.services import (
    organization_entitlement_service,
    organization_notification_service,
    organization_service,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import OrganizationNotificationPreference, User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/organizations", tags=["organization-notifications"])

SERVICE_ERRORS = (
    organization_notification_service.OrganizationNotificationServiceError,
    organization_service.OrganizationServiceError,
    organization_entitlement_service.OrganizationCapabilityError,
)


def _raise_service_error(
    exc: (
        organization_notification_service.OrganizationNotificationServiceError
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
    "/{organization_id}/notifications",
    response_model=OrganizationNotificationListResponse,
)
async def list_notifications(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Annotated[OrganizationNotificationCategory | None, Query()] = None,
    unread_only: Annotated[bool, Query()] = False,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> OrganizationNotificationListResponse:
    try:
        items, total = await organization_notification_service.list_notifications(
            db,
            organization_id=organization_id,
            recipient_user_id=current_user.id,
            category=category,
            unread_only=unread_only,
            limit=limit,
            offset=offset,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationNotificationListResponse(
        items=[OrganizationNotificationResponse.model_validate(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{organization_id}/notifications/unread-count",
    response_model=OrganizationNotificationUnreadCountResponse,
)
async def unread_count(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationNotificationUnreadCountResponse:
    try:
        count = await organization_notification_service.unread_count(
            db,
            organization_id=organization_id,
            recipient_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationNotificationUnreadCountResponse(unread_count=count)


@router.get(
    "/{organization_id}/notifications/preferences",
    response_model=OrganizationNotificationPreferenceListResponse,
)
async def list_preferences(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationNotificationPreferenceListResponse:
    try:
        preferences = await organization_notification_service.list_preferences(
            db,
            organization_id=organization_id,
            user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    items: list[OrganizationNotificationPreferenceResponse] = []
    for preference in preferences:
        if isinstance(preference, OrganizationNotificationPreference):
            items.append(
                OrganizationNotificationPreferenceResponse(
                    organization_id=preference.organization_id,
                    user_id=preference.user_id,
                    category=preference.category,
                    enabled=preference.enabled,
                    created_at=preference.created_at,
                    updated_at=preference.updated_at,
                )
            )
        else:
            category, enabled = preference
            items.append(
                OrganizationNotificationPreferenceResponse(
                    organization_id=organization_id,
                    user_id=current_user.id,
                    category=category,
                    enabled=enabled,
                    created_at=None,
                    updated_at=None,
                )
            )
    return OrganizationNotificationPreferenceListResponse(items=items)


@router.patch(
    "/{organization_id}/notifications/preferences/{category}",
    response_model=OrganizationNotificationPreferenceResponse,
)
async def update_preference(
    organization_id: str,
    category: OrganizationNotificationCategory,
    payload: OrganizationNotificationPreferenceUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationNotificationPreferenceResponse:
    try:
        preference = await organization_notification_service.update_preference(
            db,
            organization_id=organization_id,
            user_id=current_user.id,
            category=category,
            enabled=payload.enabled,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationNotificationPreferenceResponse(
        organization_id=preference.organization_id,
        user_id=preference.user_id,
        category=preference.category,
        enabled=preference.enabled,
        created_at=preference.created_at,
        updated_at=preference.updated_at,
    )


@router.get(
    "/{organization_id}/notifications/{notification_id}",
    response_model=OrganizationNotificationResponse,
)
async def get_notification(
    organization_id: str,
    notification_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationNotificationResponse:
    try:
        notification = await organization_notification_service.get_notification(
            db,
            organization_id=organization_id,
            notification_id=notification_id,
            recipient_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationNotificationResponse.model_validate(notification)


@router.post(
    "/{organization_id}/notifications/{notification_id}/read",
    response_model=OrganizationNotificationResponse,
)
async def mark_notification_read(
    organization_id: str,
    notification_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationNotificationResponse:
    try:
        notification = await organization_notification_service.mark_notification_read(
            db,
            organization_id=organization_id,
            notification_id=notification_id,
            recipient_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationNotificationResponse.model_validate(notification)
