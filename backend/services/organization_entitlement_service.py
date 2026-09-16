"""Organization-scoped School Free entitlement persistence and capability checks."""

from __future__ import annotations

import datetime as dt
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.database import get_db
from backend.sql_app.models import Organization, OrganizationEntitlement, User

logger = structlog.get_logger(__name__)

SCHOOL_FREE_PLAN_KEY = "school_free"
ACTIVE_ENTITLEMENT_STATUS = "active"
SYSTEM_ENTITLEMENT_SOURCE = "system"

SCHOOL_FREE_CAPABILITIES = frozenset(
    {
        "school_matches_unlimited",
        "school_master_roster",
        "school_persistent_teams",
        "school_team_rosters",
        "school_match_playing_xi",
        "school_basic_statistics",
        "school_fixtures_results",
        "school_live_scorecards",
        "school_competitions",
    }
)
SCHOOL_FREE_EXCLUDED_CAPABILITIES = frozenset(
    {
        "advanced_ai",
        "video_analysis",
        "advanced_analytics",
        "analyst_tooling",
        "premium_coaching",
        "premium_broadcast_video",
    }
)
PLAN_CAPABILITIES: dict[str, frozenset[str]] = {
    SCHOOL_FREE_PLAN_KEY: SCHOOL_FREE_CAPABILITIES,
}


class OrganizationCapabilityError(Exception):
    """Raised when an active organization lacks a requested capability."""

    def __init__(self, capability: str) -> None:
        self.capability = capability
        super().__init__(f"Organization capability is not enabled: {capability}")


def capabilities_for_plan(plan_key: str) -> frozenset[str]:
    """Return the explicitly approved capabilities for an organization plan."""
    return PLAN_CAPABILITIES.get(plan_key, frozenset())


async def _get_school_for_provisioning(
    db: AsyncSession,
    *,
    organization_id: str,
) -> Organization:
    result = await db.execute(
        select(Organization)
        .where(
            Organization.id == organization_id,
            Organization.organization_type == "school",
        )
        .with_for_update()
    )
    organization = result.scalar_one_or_none()
    if organization is None:
        raise ValueError("School organization not found")
    return organization


async def ensure_school_free_entitlement(
    db: AsyncSession,
    *,
    organization_id: str,
) -> tuple[OrganizationEntitlement, bool]:
    """Idempotently add School Free to one exact school without committing."""
    await _get_school_for_provisioning(db, organization_id=organization_id)
    for pending in db.new:
        if (
            isinstance(pending, OrganizationEntitlement)
            and pending.organization_id == organization_id
            and pending.plan_key == SCHOOL_FREE_PLAN_KEY
        ):
            return pending, False
    result = await db.execute(
        select(OrganizationEntitlement).where(
            OrganizationEntitlement.organization_id == organization_id,
            OrganizationEntitlement.plan_key == SCHOOL_FREE_PLAN_KEY,
        )
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        return existing, False

    entitlement = OrganizationEntitlement(
        organization_id=organization_id,
        plan_key=SCHOOL_FREE_PLAN_KEY,
        status=ACTIVE_ENTITLEMENT_STATUS,
        source=SYSTEM_ENTITLEMENT_SOURCE,
    )
    db.add(entitlement)
    return entitlement, True


async def provision_existing_school_free_entitlement(
    db: AsyncSession,
    *,
    organization_id: str,
) -> tuple[OrganizationEntitlement, bool]:
    """Controlled, auditable, exact-school provisioning for pre-Phase-7C schools."""
    entitlement, created = await ensure_school_free_entitlement(
        db,
        organization_id=organization_id,
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception(
            "organization.entitlement_existing_school_provision_failed",
            organization_id=organization_id,
        )
        raise
    await db.refresh(entitlement)
    logger.info(
        "organization.entitlement_existing_school_provisioned",
        organization_id=organization_id,
        entitlement_id=entitlement.id,
        created=created,
        source=entitlement.source,
    )
    return entitlement, created


async def get_effective_organization_entitlement(
    db: AsyncSession,
    *,
    organization_id: str,
) -> OrganizationEntitlement | None:
    """Load the active, current entitlement using organization-scoped predicates."""
    now = dt.datetime.now(dt.UTC)
    result = await db.execute(
        select(OrganizationEntitlement)
        .join(Organization, Organization.id == OrganizationEntitlement.organization_id)
        .where(
            OrganizationEntitlement.organization_id == organization_id,
            Organization.id == organization_id,
            Organization.organization_type == "school",
            Organization.status == "active",
            OrganizationEntitlement.plan_key == SCHOOL_FREE_PLAN_KEY,
            OrganizationEntitlement.status == ACTIVE_ENTITLEMENT_STATUS,
            OrganizationEntitlement.effective_from <= now,
            or_(
                OrganizationEntitlement.effective_until.is_(None),
                OrganizationEntitlement.effective_until > now,
            ),
        )
    )
    return result.scalar_one_or_none()


async def organization_has_capability(
    db: AsyncSession,
    *,
    organization_id: str,
    capability: str,
) -> bool:
    """Return whether one active school organization has an approved capability."""
    entitlement = await get_effective_organization_entitlement(
        db,
        organization_id=organization_id,
    )
    return entitlement is not None and capability in capabilities_for_plan(entitlement.plan_key)


async def require_organization_capability(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    capability: str,
) -> None:
    """Require active scoped membership and an explicit organization capability."""
    from backend.services.organization_service import get_organization_for_member

    await get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if not await organization_has_capability(
        db,
        organization_id=organization_id,
        capability=capability,
    ):
        raise OrganizationCapabilityError(capability)


def require_organization_capability_dependency(
    capability: str,
) -> Callable[..., Awaitable[None]]:
    """Build a FastAPI dependency for future organization-scoped capability gates."""
    from backend.security import get_current_active_user

    async def _require(
        organization_id: str,
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> None:
        from backend.services.organization_service import OrganizationServiceError

        try:
            await require_organization_capability(
                db,
                organization_id=organization_id,
                actor_user_id=current_user.id,
                capability=capability,
            )
        except OrganizationServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
        except OrganizationCapabilityError as exc:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Organization capability not enabled: {capability}",
            ) from exc

    return _require
