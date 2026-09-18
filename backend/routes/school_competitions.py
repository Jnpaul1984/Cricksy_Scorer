"""Organization-scoped School competition, fixture, and publication routes."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.school_competitions import (
    PublicSchoolScorecard,
    SchoolCompetitionCreate,
    SchoolCompetitionResponse,
    SchoolCompetitionTeamAdd,
    SchoolCompetitionTeamResponse,
    SchoolCompetitionUpdate,
    SchoolFixtureCreate,
    SchoolFixtureGameLink,
    SchoolFixtureResponse,
    SchoolFixtureUpdate,
    SchoolPublicationResponse,
    SchoolPublicationUpdate,
    SchoolStandingsResponse,
)
from backend.security import get_current_active_user
from backend.services import (
    organization_entitlement_service,
    organization_service,
    school_competition_service,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["school-competitions"])


def _raise_service_error(
    exc: (
        school_competition_service.SchoolCompetitionServiceError
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


SERVICE_ERRORS = (
    school_competition_service.SchoolCompetitionServiceError,
    organization_service.OrganizationServiceError,
    organization_entitlement_service.OrganizationCapabilityError,
)


@router.get(
    "/api/organizations/{organization_id}/competitions",
    response_model=list[SchoolCompetitionResponse],
)
async def list_competitions(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SchoolCompetitionResponse]:
    try:
        rows = await school_competition_service.list_competitions(
            db, organization_id=organization_id, actor_user_id=current_user.id
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return [SchoolCompetitionResponse.model_validate(row) for row in rows]


@router.post(
    "/api/organizations/{organization_id}/competitions",
    response_model=SchoolCompetitionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_competition(
    organization_id: str,
    payload: SchoolCompetitionCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolCompetitionResponse:
    try:
        row = await school_competition_service.create_competition(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return SchoolCompetitionResponse.model_validate(row)


@router.get(
    "/api/organizations/{organization_id}/competitions/{competition_id}",
    response_model=SchoolCompetitionResponse,
)
async def get_competition(
    organization_id: str,
    competition_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolCompetitionResponse:
    try:
        row = await school_competition_service.get_competition(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return SchoolCompetitionResponse.model_validate(row)


@router.patch(
    "/api/organizations/{organization_id}/competitions/{competition_id}",
    response_model=SchoolCompetitionResponse,
)
async def update_competition(
    organization_id: str,
    competition_id: str,
    payload: SchoolCompetitionUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolCompetitionResponse:
    try:
        row = await school_competition_service.update_competition(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return SchoolCompetitionResponse.model_validate(row)


@router.delete(
    "/api/organizations/{organization_id}/competitions/{competition_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_competition(
    organization_id: str,
    competition_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    try:
        await school_competition_service.delete_competition(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/api/organizations/{organization_id}/competitions/{competition_id}/teams",
    response_model=list[SchoolCompetitionTeamResponse],
)
async def list_teams(
    organization_id: str,
    competition_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SchoolCompetitionTeamResponse]:
    try:
        rows = await school_competition_service.list_teams(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return [SchoolCompetitionTeamResponse.model_validate(row) for row in rows]


@router.post(
    "/api/organizations/{organization_id}/competitions/{competition_id}/teams",
    response_model=SchoolCompetitionTeamResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_team(
    organization_id: str,
    competition_id: str,
    payload: SchoolCompetitionTeamAdd,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolCompetitionTeamResponse:
    try:
        row = await school_competition_service.add_team(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
            team_id=payload.team_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return SchoolCompetitionTeamResponse.model_validate(row)


@router.delete(
    "/api/organizations/{organization_id}/competitions/{competition_id}/teams/{entrant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_team(
    organization_id: str,
    competition_id: str,
    entrant_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    try:
        await school_competition_service.remove_team(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
            entrant_id=entrant_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/api/organizations/{organization_id}/competitions/{competition_id}/fixtures",
    response_model=list[SchoolFixtureResponse],
)
async def list_fixtures(
    organization_id: str,
    competition_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SchoolFixtureResponse]:
    try:
        rows = await school_competition_service.list_fixtures(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return [SchoolFixtureResponse.model_validate(row) for row in rows]


@router.post(
    "/api/organizations/{organization_id}/competitions/{competition_id}/fixtures",
    response_model=SchoolFixtureResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_fixture(
    organization_id: str,
    competition_id: str,
    payload: SchoolFixtureCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolFixtureResponse:
    try:
        row = await school_competition_service.create_fixture(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return SchoolFixtureResponse.model_validate(row)


@router.get(
    "/api/organizations/{organization_id}/competitions/{competition_id}/fixtures/{fixture_id}",
    response_model=SchoolFixtureResponse,
)
async def get_fixture(
    organization_id: str,
    competition_id: str,
    fixture_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolFixtureResponse:
    try:
        row = await school_competition_service.get_fixture(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
            fixture_id=fixture_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return SchoolFixtureResponse.model_validate(row)


@router.patch(
    "/api/organizations/{organization_id}/competitions/{competition_id}/fixtures/{fixture_id}",
    response_model=SchoolFixtureResponse,
)
async def update_fixture(
    organization_id: str,
    competition_id: str,
    fixture_id: str,
    payload: SchoolFixtureUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolFixtureResponse:
    try:
        row = await school_competition_service.update_fixture(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
            fixture_id=fixture_id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return SchoolFixtureResponse.model_validate(row)


@router.delete(
    "/api/organizations/{organization_id}/competitions/{competition_id}/fixtures/{fixture_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_fixture(
    organization_id: str,
    competition_id: str,
    fixture_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    try:
        await school_competition_service.delete_fixture(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
            fixture_id=fixture_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/api/organizations/{organization_id}/competitions/{competition_id}/fixtures/{fixture_id}/game",
    response_model=SchoolFixtureResponse,
)
async def link_fixture_game(
    organization_id: str,
    competition_id: str,
    fixture_id: str,
    payload: SchoolFixtureGameLink,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolFixtureResponse:
    try:
        row = await school_competition_service.link_fixture_game(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
            fixture_id=fixture_id,
            game_id=payload.game_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return SchoolFixtureResponse.model_validate(row)


@router.get(
    "/api/organizations/{organization_id}/competitions/{competition_id}/standings",
    response_model=SchoolStandingsResponse,
)
async def get_standings(
    organization_id: str,
    competition_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolStandingsResponse:
    try:
        return await school_competition_service.standings(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            competition_id=competition_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/api/organizations/{organization_id}/matches/{game_id}/publication",
    response_model=SchoolPublicationResponse,
)
async def get_publication(
    organization_id: str,
    game_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolPublicationResponse:
    try:
        _, state = await school_competition_service.publication(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            game_id=game_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return SchoolPublicationResponse(
        game_id=game_id, organization_id=organization_id, publication_state=state
    )


@router.patch(
    "/api/organizations/{organization_id}/matches/{game_id}/publication",
    response_model=SchoolPublicationResponse,
)
async def update_publication(
    organization_id: str,
    game_id: str,
    payload: SchoolPublicationUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolPublicationResponse:
    try:
        _, state = await school_competition_service.publication(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            game_id=game_id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return SchoolPublicationResponse(
        game_id=game_id, organization_id=organization_id, publication_state=state
    )


@router.get("/public/school-scorecards/{game_id}", response_model=PublicSchoolScorecard)
async def public_school_scorecard(
    game_id: str, db: Annotated[AsyncSession, Depends(get_db)]
) -> PublicSchoolScorecard:
    try:
        return await school_competition_service.public_scorecard(db, game_id=game_id)
    except school_competition_service.SchoolCompetitionServiceError as exc:
        _raise_service_error(exc)
