"""Authenticated publication controls and the minimal anonymous projection."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.organization_publication import (
    OrganizationPublicationSettingsResponse,
    PublicOrganizationResponse,
)
from backend.security import get_current_active_user
from backend.services import organization_publication_service
from backend.services.organization_service import OrganizationServiceError
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["organization-publication"])


def _service_error(exc: OrganizationServiceError) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.get(
    "/api/organizations/{organization_id}/public-settings",
    response_model=OrganizationPublicationSettingsResponse,
)
async def get_publication_settings(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPublicationSettingsResponse:
    try:
        settings = await organization_publication_service.get_settings(
            db, organization_id=organization_id, actor_user_id=current_user.id
        )
    except OrganizationServiceError as exc:
        _service_error(exc)
    return OrganizationPublicationSettingsResponse.model_validate(settings)


async def _transition(
    *, organization_id: str, actor_user_id: str, db: AsyncSession, publish: bool
) -> OrganizationPublicationSettingsResponse:
    try:
        settings = await organization_publication_service.set_publication_state(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            publish=publish,
        )
    except OrganizationServiceError as exc:
        _service_error(exc)
    return OrganizationPublicationSettingsResponse.model_validate(settings)


@router.put(
    "/api/organizations/{organization_id}/public-settings/publish",
    response_model=OrganizationPublicationSettingsResponse,
)
async def publish_organization(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPublicationSettingsResponse:
    return await _transition(
        organization_id=organization_id, actor_user_id=current_user.id, db=db, publish=True
    )


@router.put(
    "/api/organizations/{organization_id}/public-settings/unpublish",
    response_model=OrganizationPublicationSettingsResponse,
)
async def unpublish_organization(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPublicationSettingsResponse:
    return await _transition(
        organization_id=organization_id, actor_user_id=current_user.id, db=db, publish=False
    )


@router.get(
    "/api/public/organizations/{public_identifier}",
    response_model=PublicOrganizationResponse,
)
async def public_organization(
    public_identifier: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicOrganizationResponse:
    projection = await organization_publication_service.get_public_organization(
        db, public_identifier=public_identifier
    )
    if projection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public page not found")
    identifier, display_name, organization_type = projection
    return PublicOrganizationResponse(
        public_identifier=identifier,
        display_name=display_name,
        organization_type=organization_type,  # type: ignore[arg-type]
    )
