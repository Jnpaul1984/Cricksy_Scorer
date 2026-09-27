"""Private shared School/Club draft selection-plan routes."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.organization_selection_plans import (
    OrganizationSelectionCandidateResponse,
    OrganizationSelectionPlanCreate,
    OrganizationSelectionPlanResponse,
    OrganizationSelectionPlanUpdate,
)
from backend.security import get_current_active_user
from backend.services import (
    organization_entitlement_service,
    organization_selection_plan_service,
    organization_service,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/organizations", tags=["organization-selection-plans"])

SERVICE_ERRORS = (
    organization_selection_plan_service.OrganizationSelectionPlanServiceError,
    organization_service.OrganizationServiceError,
    organization_entitlement_service.OrganizationCapabilityError,
)


def _raise_service_error(
    exc: (
        organization_selection_plan_service.OrganizationSelectionPlanServiceError
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
