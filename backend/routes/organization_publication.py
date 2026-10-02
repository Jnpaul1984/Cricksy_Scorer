"""Authenticated publication controls and the minimal anonymous projection."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.organization_publication import (
    OrganizationBrandingUpdate,
    OrganizationCommunitySettingsResponse,
    OrganizationCompetitionPublicationResponse,
    OrganizationPublicationSettingsResponse,
    PublicAnonymousLeaderboardsResponse,
    PublicCompetitionResponse,
    PublicFixtureResponse,
    PublicOrganizationCommunityResponse,
    PublicOrganizationResponse,
    PublicTeamResponse,
)
from backend.security import get_current_active_user
from backend.services import organization_publication_service, public_leaderboard_service
from backend.services import school_competition_service
from backend.services.school_competition_service import SchoolCompetitionServiceError
from backend.api.schemas.school_competitions import PublicOpaqueSchoolScorecard
from backend.services.organization_service import OrganizationServiceError
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, Response, status
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


@router.get("/api/public/organizations/{public_identifier}/competitions/{competition_public_key}", response_model=PublicCompetitionResponse)
async def public_competition(public_identifier: str, competition_public_key: str, db: Annotated[AsyncSession, Depends(get_db)]) -> PublicCompetitionResponse:
    projection = await organization_publication_service.get_public_competition(db, public_identifier=public_identifier, competition_public_key=competition_public_key)
    if projection is None:
        raise HTTPException(status_code=404, detail="Public competition not found")
    return projection

@router.get("/api/public/organizations/{public_identifier}/competitions/{competition_public_key}/fixtures/{fixture_public_identifier}", response_model=PublicFixtureResponse)
async def public_fixture(public_identifier: str, competition_public_key: str, fixture_public_identifier: str, db: Annotated[AsyncSession, Depends(get_db)]) -> PublicFixtureResponse:
    projection = await organization_publication_service.get_public_fixture(db, public_identifier=public_identifier, competition_public_key=competition_public_key, fixture_public_identifier=fixture_public_identifier)
    if projection is None:
        raise HTTPException(status_code=404, detail="Public fixture not found")
    return projection

@router.get("/api/public/organizations/{public_identifier}/competitions/{competition_public_key}/results/{fixture_public_identifier}", response_model=PublicFixtureResponse)
async def public_result(public_identifier: str, competition_public_key: str, fixture_public_identifier: str, db: Annotated[AsyncSession, Depends(get_db)]) -> PublicFixtureResponse:
    projection = await organization_publication_service.get_public_fixture(db, public_identifier=public_identifier, competition_public_key=competition_public_key, fixture_public_identifier=fixture_public_identifier, result_only=True)
    if projection is None:
        raise HTTPException(status_code=404, detail="Public result not found")
    return projection

@router.get("/api/public/organizations/{public_identifier}/competitions/{competition_public_key}/scorecards/{scorecard_public_identifier}", response_model=PublicOpaqueSchoolScorecard)
async def public_competition_scorecard(public_identifier: str, competition_public_key: str, scorecard_public_identifier: str, db: Annotated[AsyncSession, Depends(get_db)]) -> PublicOpaqueSchoolScorecard:
    game_id = await organization_publication_service.get_public_scorecard_game_id(db, public_identifier=public_identifier, competition_public_key=competition_public_key, scorecard_public_identifier=scorecard_public_identifier)
    if game_id is None:
        raise HTTPException(status_code=404, detail="Published scorecard not found")
    try:
        legacy = await school_competition_service.public_scorecard(db, game_id=game_id)
    except SchoolCompetitionServiceError:
        raise HTTPException(status_code=404, detail="Published scorecard not found") from None
    return PublicOpaqueSchoolScorecard(public_identifier=scorecard_public_identifier, **legacy.model_dump(exclude={"game_id"}))

@router.get(
    "/api/public/organizations/{public_identifier}/leaderboards",
    response_model=PublicAnonymousLeaderboardsResponse,
)
async def public_organization_leaderboards(
    public_identifier: str,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicAnonymousLeaderboardsResponse:
    """Anonymous final-only cricket totals for the public community page."""
    identity = await organization_publication_service.get_public_organization(
        db, public_identifier=public_identifier
    )
    if identity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public page not found")
    response.headers["Cache-Control"] = "no-store"
    organization_id = await organization_publication_service.get_organization_id_for_public_identifier(
        db, public_identifier=public_identifier
    )
    if organization_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public page not found")
    return await public_leaderboard_service.get_public_leaderboards(
        db, organization_id=organization_id
    )


@router.put("/api/organizations/{organization_id}/teams/{team_id}/public-publication/publish")
async def publish_team_to_community(
    organization_id: str,
    team_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    try:
        item = await organization_publication_service.set_team_publication_state(
            db,
            organization_id=organization_id,
            team_id=team_id,
            actor_user_id=current_user.id,
            publish=True,
        )
    except OrganizationServiceError as exc:
        _service_error(exc)
    return {
        "public_identifier": item.public_identifier,
        "publication_state": item.publication_state,
        "publication_version": item.publication_version,
    }


@router.get("/api/organizations/{organization_id}/teams/{team_id}/public-publication")
async def get_team_publication_settings(
    organization_id: str,
    team_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    try:
        return await organization_publication_service.get_team_publication_settings(
            db, organization_id=organization_id, team_id=team_id, actor_user_id=current_user.id
        )
    except OrganizationServiceError as exc:
        _service_error(exc)


@router.put("/api/organizations/{organization_id}/teams/{team_id}/public-publication/unpublish")
async def unpublish_team_from_community(
    organization_id: str,
    team_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    try:
        item = await organization_publication_service.set_team_publication_state(
            db,
            organization_id=organization_id,
            team_id=team_id,
            actor_user_id=current_user.id,
            publish=False,
        )
    except OrganizationServiceError as exc:
        _service_error(exc)
    return {
        "public_identifier": item.public_identifier,
        "publication_state": item.publication_state,
        "publication_version": item.publication_version,
    }


@router.get(
    "/api/public/organizations/{public_identifier}/teams/{team_public_identifier}",
    response_model=PublicTeamResponse,
)
async def public_team(
    public_identifier: str,
    team_public_identifier: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PublicTeamResponse:
    projection = await organization_publication_service.get_public_team(
        db,
        organization_public_identifier=public_identifier,
        team_public_identifier=team_public_identifier,
    )
    if projection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Public team not found")
    return PublicTeamResponse(**projection)
