"""Private shared School/Club structured announcement routes."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.organization_announcements import (
    OrganizationAnnouncementCreate,
    OrganizationAnnouncementFeedResponse,
    OrganizationAnnouncementPublicationResponse,
    OrganizationAnnouncementResponse,
    OrganizationAnnouncementRevisionRequest,
    OrganizationAnnouncementUpdate,
)
from backend.security import get_current_active_user
from backend.services import (
    organization_announcement_service,
    organization_entitlement_service,
    organization_service,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/organizations", tags=["organization-announcements"])

SERVICE_ERRORS = (
    organization_announcement_service.OrganizationAnnouncementServiceError,
    organization_service.OrganizationServiceError,
    organization_entitlement_service.OrganizationCapabilityError,
)


def _raise_service_error(
    exc: (
        organization_announcement_service.OrganizationAnnouncementServiceError
        | organization_service.OrganizationServiceError
        | organization_entitlement_service.OrganizationCapabilityError
    ),
) -> NoReturn:
    if isinstance(exc, organization_entitlement_service.OrganizationCapabilityError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization capability not enabled: {exc.capability}",
        ) from exc
    if exc.status_code >= 500:
        raise HTTPException(
            status_code=exc.status_code,
            detail="Announcement service encountered a problem",
        ) from exc
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "/{organization_id}/announcements",
    response_model=OrganizationAnnouncementFeedResponse,
)
async def list_announcements(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0, le=10_000)] = 0,
) -> OrganizationAnnouncementFeedResponse:
    try:
        items, total = await organization_announcement_service.list_feed(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            limit=limit,
            offset=offset,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationAnnouncementFeedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{organization_id}/announcements",
    response_model=OrganizationAnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_announcement(
    organization_id: str,
    payload: OrganizationAnnouncementCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationAnnouncementResponse:
    try:
        announcement = await organization_announcement_service.create_announcement(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationAnnouncementResponse.model_validate(announcement)


@router.patch(
    "/{organization_id}/announcements/{announcement_id}",
    response_model=OrganizationAnnouncementResponse,
)
async def update_announcement(
    organization_id: str,
    announcement_id: str,
    payload: OrganizationAnnouncementUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationAnnouncementResponse:
    try:
        announcement = await organization_announcement_service.update_announcement(
            db,
            organization_id=organization_id,
            announcement_id=announcement_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationAnnouncementResponse.model_validate(announcement)


@router.post(
    "/{organization_id}/announcements/{announcement_id}/revisions",
    response_model=OrganizationAnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_announcement_revision(
    organization_id: str,
    announcement_id: str,
    payload: OrganizationAnnouncementRevisionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationAnnouncementResponse:
    try:
        announcement = await organization_announcement_service.create_revision(
            db,
            organization_id=organization_id,
            announcement_id=announcement_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationAnnouncementResponse.model_validate(announcement)


@router.post(
    "/{organization_id}/announcements/{announcement_id}/publish",
    response_model=OrganizationAnnouncementPublicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def publish_announcement(
    organization_id: str,
    announcement_id: str,
    payload: OrganizationAnnouncementRevisionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationAnnouncementPublicationResponse:
    try:
        publication = await organization_announcement_service.publish_announcement(
            db,
            organization_id=organization_id,
            announcement_id=announcement_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return OrganizationAnnouncementPublicationResponse.model_validate(publication)
