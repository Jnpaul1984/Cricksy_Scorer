"""Private shared School/Club draft selection-plan routes."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.organization_selection_plans import (
    OrganizationSelectionCandidateResponse,
    OrganizationSelectionHandoffResponse,
    OrganizationSelectionPlanCreate,
    OrganizationSelectionPlanResponse,
    OrganizationSelectionPlanUpdate,
    OrganizationSelectionPublicationResponse,
    OrganizationSelectionRevisionRequest,
)
from backend.api.schemas.organization_workflow_notifications import (
    OrganizationSelectionNotificationResult,
)
from backend.security import get_current_active_user
from backend.services import (
    organization_entitlement_service,
    organization_selection_plan_service,
    organization_service,
    organization_workflow_notification_service,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/organizations", tags=["organization-selection-plans"])

SERVICE_ERRORS = (
    organization_selection_plan_service.OrganizationSelectionPlanServiceError,
    organization_service.OrganizationServiceError,
    organization_entitlement_service.OrganizationCapabilityError,
    organization_workflow_notification_service.OrganizationWorkflowNotificationServiceError,
)


def _raise_service_error(
    exc: (
        organization_selection_plan_service.OrganizationSelectionPlanServiceError
        | organization_service.OrganizationServiceError
        | organization_entitlement_service.OrganizationCapabilityError
        | organization_workflow_notification_service.OrganizationWorkflowNotificationServiceError
    ),
) -> NoReturn:
    if isinstance(exc, organization_entitlement_service.OrganizationCapabilityError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization capability not enabled: {exc.capability}",
        ) from exc
    if (
        isinstance(
            exc,
            organization_workflow_notification_service.OrganizationWorkflowNotificationServiceError,
        )
        and exc.status_code >= 500
    ):
        raise HTTPException(
            status_code=exc.status_code,
            detail="Workflow notification service encountered a problem",
        ) from exc
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post(
    "/{organization_id}/selection-plans",
    response_model=OrganizationSelectionPlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_or_open_selection_plan(
    organization_id: str,
    payload: OrganizationSelectionPlanCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSelectionPlanResponse:
    try:
        return await organization_selection_plan_service.create_or_open_selection_plan(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/{organization_id}/selection-plans",
    response_model=OrganizationSelectionPlanResponse,
)
async def get_selection_plan_by_context(
    organization_id: str,
    team_id: Annotated[str, Query(min_length=1)],
    fixture_id: Annotated[str, Query(min_length=1)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSelectionPlanResponse:
    try:
        return await organization_selection_plan_service.get_selection_plan_by_context(
            db,
            organization_id=organization_id,
            team_id=team_id,
            fixture_id=fixture_id,
            actor_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/{organization_id}/selection-plans/{plan_id}",
    response_model=OrganizationSelectionPlanResponse,
)
async def get_selection_plan(
    organization_id: str,
    plan_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSelectionPlanResponse:
    try:
        return await organization_selection_plan_service.get_selection_plan(
            db,
            organization_id=organization_id,
            plan_id=plan_id,
            actor_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.patch(
    "/{organization_id}/selection-plans/{plan_id}",
    response_model=OrganizationSelectionPlanResponse,
)
async def update_selection_plan(
    organization_id: str,
    plan_id: str,
    payload: OrganizationSelectionPlanUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSelectionPlanResponse:
    try:
        return await organization_selection_plan_service.update_selection_plan(
            db,
            organization_id=organization_id,
            plan_id=plan_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.post(
    "/{organization_id}/selection-plans/{plan_id}/publish",
    response_model=OrganizationSelectionPublicationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def publish_selection_plan(
    organization_id: str,
    plan_id: str,
    payload: OrganizationSelectionRevisionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSelectionPublicationResponse:
    try:
        return await organization_selection_plan_service.publish_selection_plan(
            db,
            organization_id=organization_id,
            plan_id=plan_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.post(
    "/{organization_id}/selection-plans/{plan_id}/draft",
    response_model=OrganizationSelectionPlanResponse,
)
async def begin_selection_plan_draft(
    organization_id: str,
    plan_id: str,
    payload: OrganizationSelectionRevisionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSelectionPlanResponse:
    try:
        return await organization_selection_plan_service.begin_selection_plan_draft(
            db,
            organization_id=organization_id,
            plan_id=plan_id,
            actor_user_id=current_user.id,
            payload=payload,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/{organization_id}/selection-plans/{plan_id}/publications",
    response_model=list[OrganizationSelectionPublicationResponse],
)
async def list_selection_publications(
    organization_id: str,
    plan_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[OrganizationSelectionPublicationResponse]:
    try:
        return await organization_selection_plan_service.list_selection_publications(
            db,
            organization_id=organization_id,
            plan_id=plan_id,
            actor_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/{organization_id}/selection-plans/{plan_id}/publications/{publication_version}",
    response_model=OrganizationSelectionPublicationResponse,
)
async def get_selection_publication(
    organization_id: str,
    plan_id: str,
    publication_version: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSelectionPublicationResponse:
    try:
        return await organization_selection_plan_service.get_selection_publication(
            db,
            organization_id=organization_id,
            plan_id=plan_id,
            publication_version=publication_version,
            actor_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.post(
    "/{organization_id}/selection-plans/{plan_id}/publications/{publication_version}/notifications",
    response_model=OrganizationSelectionNotificationResult,
)
async def notify_selection_publication(
    organization_id: str,
    plan_id: str,
    publication_version: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSelectionNotificationResult:
    try:
        return await organization_workflow_notification_service.notify_selection_publication(
            db,
            organization_id=organization_id,
            plan_id=plan_id,
            publication_version=publication_version,
            actor_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.post(
    "/{organization_id}/selection-plans/{plan_id}/publications/{publication_version}/handoff",
    response_model=OrganizationSelectionHandoffResponse,
)
async def prepare_selection_handoff(
    organization_id: str,
    plan_id: str,
    publication_version: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSelectionHandoffResponse:
    """Explicitly prepare one published version for the existing match-setup flow."""
    try:
        prepared = await organization_selection_plan_service.prepare_selection_handoff(
            db,
            organization_id=organization_id,
            plan_id=plan_id,
            publication_version=publication_version,
            actor_user_id=current_user.id,
        )
        return prepared.response
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/{organization_id}/selection-plans/{plan_id}/candidates",
    response_model=OrganizationSelectionCandidateResponse,
)
async def get_selection_candidates(
    organization_id: str,
    plan_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationSelectionCandidateResponse:
    try:
        return await organization_selection_plan_service.selection_candidates(
            db,
            organization_id=organization_id,
            plan_id=plan_id,
            actor_user_id=current_user.id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
