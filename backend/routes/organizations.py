"""Phase 7B organization and organization-membership API routes."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.organizations import (
    OrganizationCreate,
    OrganizationEntitlementResponse,
    OrganizationEntitlementRecordResponse,
    OrganizationMembershipCreate,
    OrganizationMembershipListResponse,
    OrganizationMembershipResponse,
    OrganizationMembershipUpdate,
    OrganizationResponse,
    OrganizationWithMembershipResponse,
)
from backend.security import get_current_active_user
from backend.services import organization_service
from backend.services import organization_entitlement_service
from backend.sql_app.database import get_db
from backend.sql_app.models import Organization, User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/organizations", tags=["organizations"])


def _service_error(exc: organization_service.OrganizationServiceError) -> NoReturn:
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


def _organization_with_role(
    organization: Organization,
    membership_role: str,
) -> OrganizationWithMembershipResponse:
    organization_data = OrganizationResponse.model_validate(organization).model_dump()
    return OrganizationWithMembershipResponse(
        **organization_data,
        membership_role=membership_role,
    )


@router.post(
    "",
    response_model=OrganizationWithMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization(
    payload: OrganizationCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationWithMembershipResponse:
    organization, membership = await organization_service.create_organization(
        db,
        payload=payload,
        actor=current_user,
    )
    return _organization_with_role(organization, membership.role)


@router.get("", response_model=list[OrganizationWithMembershipResponse])
async def list_organizations(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[OrganizationWithMembershipResponse]:
    rows = await organization_service.list_organizations_for_user(
        db,
        user_id=current_user.id,
    )
    return [_organization_with_role(organization, role) for organization, role in rows]


@router.get(
    "/{organization_id}/entitlements",
    response_model=OrganizationEntitlementResponse,
)
async def get_organization_entitlements(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationEntitlementResponse:
    try:
        await organization_service.require_membership_manager(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
        )
    except organization_service.OrganizationServiceError as exc:
        _service_error(exc)

    entitlement = await organization_entitlement_service.get_effective_organization_entitlement(
        db,
        organization_id=organization_id,
    )
    if entitlement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization entitlement not found"
        )
    entitlement_data = OrganizationEntitlementRecordResponse.model_validate(
        entitlement
    ).model_dump()
    return OrganizationEntitlementResponse(
        **entitlement_data,
        capabilities=sorted(
            organization_entitlement_service.capabilities_for_plan(entitlement.plan_key)
        ),
        excluded_capabilities=sorted(
            organization_entitlement_service.SCHOOL_FREE_EXCLUDED_CAPABILITIES
        ),
    )


@router.get("/{organization_id}", response_model=OrganizationWithMembershipResponse)
async def get_organization(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationWithMembershipResponse:
    try:
        organization, membership = await organization_service.get_organization_for_member(
            db,
            organization_id=organization_id,
            user_id=current_user.id,
        )
    except organization_service.OrganizationServiceError as exc:
        _service_error(exc)
    return _organization_with_role(organization, membership.role)


@router.get(
    "/{organization_id}/me",
    response_model=OrganizationMembershipResponse,
)
async def get_my_membership(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationMembershipResponse:
    try:
        _, membership = await organization_service.get_organization_for_member(
            db,
            organization_id=organization_id,
            user_id=current_user.id,
        )
    except organization_service.OrganizationServiceError as exc:
        _service_error(exc)
    return OrganizationMembershipResponse.model_validate(membership)


@router.get(
    "/{organization_id}/memberships",
    response_model=OrganizationMembershipListResponse,
)
async def list_organization_memberships(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> OrganizationMembershipListResponse:
    try:
        memberships, total = await organization_service.list_memberships(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            limit=limit,
            offset=offset,
        )
    except organization_service.OrganizationServiceError as exc:
        _service_error(exc)
    return OrganizationMembershipListResponse(
        items=[OrganizationMembershipResponse.model_validate(item) for item in memberships],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/{organization_id}/memberships",
    response_model=OrganizationMembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_organization_membership(
    organization_id: str,
    payload: OrganizationMembershipCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationMembershipResponse:
    try:
        membership = await organization_service.add_membership(
            db,
            organization_id=organization_id,
            payload=payload,
            actor_user_id=current_user.id,
        )
    except organization_service.OrganizationServiceError as exc:
        _service_error(exc)
    return OrganizationMembershipResponse.model_validate(membership)


@router.patch(
    "/{organization_id}/memberships/{membership_id}",
    response_model=OrganizationMembershipResponse,
)
async def update_organization_membership(
    organization_id: str,
    membership_id: str,
    payload: OrganizationMembershipUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationMembershipResponse:
    try:
        membership = await organization_service.update_membership(
            db,
            organization_id=organization_id,
            membership_id=membership_id,
            payload=payload,
            actor_user_id=current_user.id,
        )
    except organization_service.OrganizationServiceError as exc:
        _service_error(exc)
    return OrganizationMembershipResponse.model_validate(membership)


@router.delete(
    "/{organization_id}/memberships/{membership_id}",
    response_model=OrganizationMembershipResponse,
)
async def disable_organization_membership(
    organization_id: str,
    membership_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationMembershipResponse:
    try:
        membership = await organization_service.disable_membership(
            db,
            organization_id=organization_id,
            membership_id=membership_id,
            actor_user_id=current_user.id,
        )
    except organization_service.OrganizationServiceError as exc:
        _service_error(exc)
    return OrganizationMembershipResponse.model_validate(membership)
