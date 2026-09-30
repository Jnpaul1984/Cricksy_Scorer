"""Authenticated publication controls and the minimal anonymous projection."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.organization_publication import (
    OrganizationBrandingUpdate,
    OrganizationCommunitySettingsResponse,
    OrganizationCompetitionPublicationResponse,
    OrganizationPublicationSettingsResponse,
    PublicOrganizationCommunityResponse,
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


@router.get(
    "/api/organizations/{organization_id}/community-settings",
    response_model=OrganizationCommunitySettingsResponse,
)
async def get_community_settings(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationCommunitySettingsResponse:
    try:
        return await organization_publication_service.get_community_settings(
            db, organization_id=organization_id, actor_user_id=current_user.id
        )
    except OrganizationServiceError as exc:
        _service_error(exc)


@router.put(
    "/api/organizations/{organization_id}/community-branding",
    response_model=OrganizationPublicationSettingsResponse,
)
async def update_community_branding(
    organization_id: str,
    payload: OrganizationBrandingUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationPublicationSettingsResponse:
    try:
        settings = await organization_publication_service.update_branding(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except OrganizationServiceError as exc:
        _service_error(exc)
    return OrganizationPublicationSettingsResponse.model_validate(settings)


async def _competition_transition(
    *,
    organization_id: str,
    competition_id: str,
    actor_user_id: str,
    db: AsyncSession,
    publish: bool,
) -> OrganizationCompetitionPublicationResponse:
    try:
        (
            publication,
            competition_name,
        ) = await organization_publication_service.set_competition_publication_state(
            db,
            organization_id=organization_id,
            competition_id=competition_id,
            actor_user_id=actor_user_id,
            publish=publish,
        )
    except OrganizationServiceError as exc:
        _service_error(exc)
    return OrganizationCompetitionPublicationResponse(
        competition_id=publication.competition_id,
        competition_name=competition_name,
        publication_state=publication.publication_state,  # type: ignore[arg-type]
        publication_version=publication.publication_version,
        published_at=publication.published_at,
        unpublished_at=publication.unpublished_at,
        updated_by_user_id=publication.updated_by_user_id,
    )


@router.put(
    "/api/organizations/{organization_id}/competitions/{competition_id}/community-publication/publish",
    response_model=OrganizationCompetitionPublicationResponse,
)
async def publish_competition_to_community(
    organization_id: str,
    competition_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationCompetitionPublicationResponse:
    return await _competition_transition(
        organization_id=organization_id,
        competition_id=competition_id,
        actor_user_id=current_user.id,
        db=db,
        publish=True,
    )


@router.put(
    "/api/organizations/{organization_id}/competitions/{competition_id}/community-publication/unpublish",
    response_model=OrganizationCompetitionPublicationResponse,
)
async def unpublish_competition_from_community(
    organization_id: str,
    competition_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationCompetitionPublicationResponse:
    return await _competition_transition(
        organization_id=organization_id,
        competition_id=competition_id,
        actor_user_id=current_user.id,
        db=db,
        publish=False,
    )


@router.get(
    "/api/public/organizations/{public_identifier}/community",
    response_model=PublicOrganizationCommunityResponse,
)
async def public_organization_community(
    public_identifier: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicOrganizationCommunityResponse:
    projection = await organization_publication_service.get_public_community(
        db, public_identifier=public_identifier
    )
    if projection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public page not found")
    return projection
