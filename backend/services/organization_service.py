"""Organization and membership persistence with tenant-scoped authorization."""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from backend.api.schemas.organizations import (
    OrganizationCreate,
    OrganizationMembershipCreate,
    OrganizationMembershipUpdate,
)
from backend.sql_app.models import Organization, OrganizationMembership, User
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

ACTIVE_ORGANIZATION_STATUS = "active"
ACTIVE_MEMBERSHIP_STATUS = "active"
MEMBERSHIP_MANAGERS = {"owner", "admin"}


@dataclass(frozen=True)
class OrganizationServiceError(Exception):
    status_code: int
    detail: str


def _not_found() -> OrganizationServiceError:
    return OrganizationServiceError(404, "Organization not found")


def _membership_not_found() -> OrganizationServiceError:
    return OrganizationServiceError(404, "Membership not found")


def _forbidden() -> OrganizationServiceError:
    return OrganizationServiceError(403, "Insufficient organization role")


async def create_organization(
    db: AsyncSession,
    *,
    payload: OrganizationCreate,
    actor: User,
) -> tuple[Organization, OrganizationMembership]:
    """Create a school and its owner membership in one transaction."""
    actor_user_id = actor.id
    organization = Organization(
        name=payload.name,
        organization_type=payload.organization_type,
        status=ACTIVE_ORGANIZATION_STATUS,
        created_by_user_id=actor_user_id,
    )
    owner_membership = OrganizationMembership(
        organization=organization,
        user_id=actor_user_id,
        role="owner",
        status=ACTIVE_MEMBERSHIP_STATUS,
        created_by_user_id=actor_user_id,
    )
    db.add_all([organization, owner_membership])
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("organization.create_failed", actor_user_id=actor_user_id)
        raise
    await db.refresh(organization)
    await db.refresh(owner_membership)
    logger.info(
        "organization.created",
        organization_id=organization.id,
        actor_user_id=actor_user_id,
        membership_id=owner_membership.id,
    )
    return organization, owner_membership


async def list_organizations_for_user(
    db: AsyncSession,
    *,
    user_id: str,
) -> list[tuple[Organization, str]]:
    """Return active organizations for the user's active memberships only."""
    result = await db.execute(
        select(Organization, OrganizationMembership.role)
        .join(
            OrganizationMembership,
            OrganizationMembership.organization_id == Organization.id,
        )
        .where(
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.status == ACTIVE_MEMBERSHIP_STATUS,
            Organization.status == ACTIVE_ORGANIZATION_STATUS,
        )
        .order_by(Organization.name, Organization.id)
    )
    return list(result.all())


async def get_organization_for_member(
    db: AsyncSession,
    *,
    organization_id: str,
    user_id: str,
) -> tuple[Organization, OrganizationMembership]:
    """Load one active organization through an active scoped membership."""
    result = await db.execute(
        select(Organization, OrganizationMembership)
        .join(
            OrganizationMembership,
            OrganizationMembership.organization_id == Organization.id,
        )
        .where(
            Organization.id == organization_id,
            Organization.status == ACTIVE_ORGANIZATION_STATUS,
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == user_id,
            OrganizationMembership.status == ACTIVE_MEMBERSHIP_STATUS,
        )
    )
    row = result.one_or_none()
    if row is None:
        logger.warning(
            "organization.access_denied",
            organization_id=organization_id,
            actor_user_id=user_id,
        )
        raise _not_found()
    return row[0], row[1]


async def require_membership_manager(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
) -> tuple[Organization, OrganizationMembership]:
    organization, membership = await get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if membership.role not in MEMBERSHIP_MANAGERS:
        logger.warning(
            "organization.membership_management_denied",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
        raise _forbidden()
    return organization, membership


async def list_memberships(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    limit: int,
    offset: int,
) -> tuple[list[OrganizationMembership], int]:
    await require_membership_manager(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
    )
    rows = await db.execute(
        select(OrganizationMembership)
        .where(OrganizationMembership.organization_id == organization_id)
        .order_by(OrganizationMembership.created_at, OrganizationMembership.id)
        .limit(limit)
        .offset(offset)
    )
    total_result = await db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == organization_id
        )
    )
    return list(rows.scalars().all()), int(total_result.scalar_one())


async def add_membership(
    db: AsyncSession,
    *,
    organization_id: str,
    payload: OrganizationMembershipCreate,
    actor_user_id: str,
) -> OrganizationMembership:
    _, actor_membership = await require_membership_manager(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
    )

    user_result = await db.execute(select(User.id).where(User.id == payload.user_id))
    if user_result.scalar_one_or_none() is None:
        raise OrganizationServiceError(404, "User not found")

    existing_result = await db.execute(
        select(OrganizationMembership.id).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == payload.user_id,
        )
    )
    if existing_result.scalar_one_or_none() is not None:
        raise OrganizationServiceError(409, "Membership already exists")

    membership = OrganizationMembership(
        organization_id=organization_id,
        user_id=payload.user_id,
        role=payload.role,
        status=ACTIVE_MEMBERSHIP_STATUS,
        created_by_user_id=actor_user_id,
    )
    db.add(membership)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning(
            "organization.membership_conflict",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
        raise OrganizationServiceError(409, "Membership already exists") from exc
    except Exception:
        await db.rollback()
        logger.exception(
            "organization.membership_create_failed",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
        raise
    await db.refresh(membership)
    logger.info(
        "organization.membership_created",
        organization_id=organization_id,
        membership_id=membership.id,
        actor_user_id=actor_user_id,
        actor_membership_id=actor_membership.id,
    )
    return membership


async def _get_scoped_membership(
    db: AsyncSession,
    *,
    organization_id: str,
    membership_id: str,
) -> OrganizationMembership:
    result = await db.execute(
        select(OrganizationMembership).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.id == membership_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise _membership_not_found()
    return membership


async def _lock_organization_for_membership_mutation(
    db: AsyncSession,
    *,
    organization_id: str,
) -> None:
    """Serialize membership mutations on the authoritative organization row."""
    result = await db.execute(
        select(Organization.id)
        .where(
            Organization.id == organization_id,
            Organization.status == ACTIVE_ORGANIZATION_STATUS,
        )
        .with_for_update()
    )
    if result.scalar_one_or_none() is None:
        raise _not_found()


async def _ensure_another_active_owner(
    db: AsyncSession,
    *,
    organization_id: str,
    excluded_membership_id: str,
) -> None:
    result = await db.execute(
        select(func.count(OrganizationMembership.id)).where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.role == "owner",
            OrganizationMembership.status == ACTIVE_MEMBERSHIP_STATUS,
            OrganizationMembership.id != excluded_membership_id,
        )
    )
    if int(result.scalar_one()) < 1:
        raise OrganizationServiceError(409, "Organization must retain an active owner")


async def update_membership(
    db: AsyncSession,
    *,
    organization_id: str,
    membership_id: str,
    payload: OrganizationMembershipUpdate,
    actor_user_id: str,
) -> OrganizationMembership:
    await _lock_organization_for_membership_mutation(
        db,
        organization_id=organization_id,
    )
    _, actor_membership = await require_membership_manager(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
    )
    target = await _get_scoped_membership(
        db,
        organization_id=organization_id,
        membership_id=membership_id,
    )

    if actor_membership.role == "admin" and (target.role == "owner" or payload.role == "owner"):
        raise _forbidden()

    removes_active_owner = (
        target.role == "owner"
        and target.status == "active"
        and ((payload.role is not None and payload.role != "owner") or payload.status == "disabled")
    )
    if removes_active_owner:
        await _ensure_another_active_owner(
            db,
            organization_id=organization_id,
            excluded_membership_id=target.id,
        )

    if payload.role is not None:
        target.role = payload.role
    if payload.status is not None:
        target.status = payload.status

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception(
            "organization.membership_update_failed",
            organization_id=organization_id,
            membership_id=membership_id,
            actor_user_id=actor_user_id,
        )
        raise
    await db.refresh(target)
    logger.info(
        "organization.membership_updated",
        organization_id=organization_id,
        membership_id=target.id,
        actor_user_id=actor_user_id,
    )
    return target


async def disable_membership(
    db: AsyncSession,
    *,
    organization_id: str,
    membership_id: str,
    actor_user_id: str,
) -> OrganizationMembership:
    return await update_membership(
        db,
        organization_id=organization_id,
        membership_id=membership_id,
        payload=OrganizationMembershipUpdate(status="disabled"),
        actor_user_id=actor_user_id,
    )
