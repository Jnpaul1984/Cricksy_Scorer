"""Independent default-off authorization and operator lifecycle for Team Performance."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from backend.sql_app import models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

TEAM_PERFORMANCE_READ_ROLES = frozenset({"owner", "admin", "coach"})


@dataclass(frozen=True)
class TeamPerformanceAccessError(Exception):
    status_code: int
    detail: str


class TeamPerformanceGrantOperationError(ValueError):
    """An operator grant/revoke command cannot be applied as requested."""


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _as_utc(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC)


async def grant_organization_team_performance(
    db: AsyncSession,
    *,
    organization_id: str,
    operator_user_id: str,
    reason: str,
    effective_from: dt.datetime | None = None,
    effective_until: dt.datetime | None = None,
) -> tuple[models.OrganizationTeamPerformanceGrant, bool]:
    """Create one auditable grant; repeated identical active grants are idempotent."""
    normalized_reason = reason.strip()
    if not normalized_reason or len(normalized_reason) > 2000:
        raise TeamPerformanceGrantOperationError(
            "A grant reason of 1 to 2000 characters is required"
        )
    if not operator_user_id.strip():
        raise TeamPerformanceGrantOperationError("An operator user ID is required")
    operator_user_id = operator_user_id.strip()
    if (
        await db.scalar(
            select(models.User.id).where(
                models.User.id == operator_user_id,
                models.User.is_active.is_(True),
            )
        )
        is None
    ):
        raise TeamPerformanceGrantOperationError("An active operator account is required")

    now = _now()
    start = effective_from or now
    if start.tzinfo is None or (effective_until is not None and effective_until.tzinfo is None):
        raise TeamPerformanceGrantOperationError(
            "Grant validity timestamps must include a timezone"
        )
    if effective_until is not None and effective_until <= start:
        raise TeamPerformanceGrantOperationError("Grant expiry must be after its effective start")

    organization = await db.scalar(
        select(models.Organization)
        .where(
            models.Organization.id == organization_id,
            models.Organization.status == "active",
            models.Organization.organization_type.in_({"school", "club"}),
        )
        .with_for_update()
    )
    if organization is None:
        raise TeamPerformanceGrantOperationError("Active School/Club organization not found")

    active_grant = await db.scalar(
        select(models.OrganizationTeamPerformanceGrant)
        .where(
            models.OrganizationTeamPerformanceGrant.organization_id == organization_id,
            models.OrganizationTeamPerformanceGrant.status == "active",
        )
        .order_by(models.OrganizationTeamPerformanceGrant.granted_at.desc())
        .with_for_update()
    )
    if active_grant is not None:
        if active_grant.effective_until is not None:
            expiry = _as_utc(active_grant.effective_until)
            if expiry is not None and expiry <= now:
                active_grant.status = "expired"
                await db.flush()
                active_grant = None
        if active_grant is not None:
            same_request = (
                active_grant.granted_by_user_id == operator_user_id
                and active_grant.grant_reason == normalized_reason
                and _as_utc(active_grant.effective_until) == _as_utc(effective_until)
                and (
                    effective_from is None
                    or _as_utc(active_grant.effective_from) == _as_utc(effective_from)
                )
            )
            if same_request:
                return active_grant, False
            raise TeamPerformanceGrantOperationError(
                "An active Team Performance grant already exists"
            )

    grant = models.OrganizationTeamPerformanceGrant(
        organization_id=organization_id,
        status="active",
        effective_from=start,
        effective_until=effective_until,
        granted_by_user_id=operator_user_id,
        grant_reason=normalized_reason,
        granted_at=now,
    )
    db.add(grant)
    await db.flush()
    return grant, True


async def revoke_organization_team_performance(
    db: AsyncSession,
    *,
    organization_id: str,
    operator_user_id: str,
    reason: str,
) -> tuple[models.OrganizationTeamPerformanceGrant, bool]:
    """Revoke the current grant while retaining operator and reason audit data."""
    normalized_reason = reason.strip()
    if not normalized_reason or len(normalized_reason) > 2000:
        raise TeamPerformanceGrantOperationError(
            "A revocation reason of 1 to 2000 characters is required"
        )
    if not operator_user_id.strip():
        raise TeamPerformanceGrantOperationError("An operator user ID is required")
    operator_user_id = operator_user_id.strip()
    if (
        await db.scalar(
            select(models.User.id).where(
                models.User.id == operator_user_id,
                models.User.is_active.is_(True),
            )
        )
        is None
    ):
        raise TeamPerformanceGrantOperationError("An active operator account is required")

    await db.scalar(
        select(models.Organization)
        .where(models.Organization.id == organization_id)
        .with_for_update()
    )
    grant = await db.scalar(
        select(models.OrganizationTeamPerformanceGrant)
        .where(
            models.OrganizationTeamPerformanceGrant.organization_id == organization_id,
            models.OrganizationTeamPerformanceGrant.status == "active",
        )
        .order_by(models.OrganizationTeamPerformanceGrant.granted_at.desc())
        .with_for_update()
    )
    if grant is None:
        previously_revoked = await db.scalar(
            select(models.OrganizationTeamPerformanceGrant)
            .where(
                models.OrganizationTeamPerformanceGrant.organization_id == organization_id,
                models.OrganizationTeamPerformanceGrant.status == "revoked",
                models.OrganizationTeamPerformanceGrant.revoked_by_user_id == operator_user_id,
                models.OrganizationTeamPerformanceGrant.revocation_reason == normalized_reason,
            )
            .order_by(models.OrganizationTeamPerformanceGrant.revoked_at.desc())
            .limit(1)
        )
        if previously_revoked is not None:
            return previously_revoked, False
        raise TeamPerformanceGrantOperationError("No active Team Performance grant exists")

    now = _now()
    if grant.effective_until is not None:
        expiry = _as_utc(grant.effective_until)
        if expiry is not None and expiry <= now:
            grant.status = "expired"
            await db.flush()
            raise TeamPerformanceGrantOperationError("No active Team Performance grant exists")
    grant.status = "revoked"
    grant.revoked_by_user_id = operator_user_id
    grant.revoked_at = now
    grant.revocation_reason = normalized_reason
    await db.flush()
    return grant, True


async def require_team_performance_access(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    actor_user_id: str,
) -> models.Team:
    """Revalidate active principal, organization membership, grant, and exact Team."""
    user_is_active = await db.scalar(
        select(models.User.id).where(
            models.User.id == actor_user_id,
            models.User.is_active.is_(True),
        )
    )
    if user_is_active is None:
        raise TeamPerformanceAccessError(404, "Organization not found")

    from backend.services.organization_service import (
        OrganizationServiceError,
        get_organization_for_member,
    )

    try:
        organization, membership = await get_organization_for_member(
            db,
            organization_id=organization_id,
            user_id=actor_user_id,
        )
    except OrganizationServiceError as exc:
        raise TeamPerformanceAccessError(404, "Organization not found") from exc

    if (
        organization.organization_type not in {"school", "club"}
        or membership.role not in TEAM_PERFORMANCE_READ_ROLES
    ):
        raise TeamPerformanceAccessError(403, "Team Performance is unavailable")

    now = _now()
    grant = await db.scalar(
        select(models.OrganizationTeamPerformanceGrant.id)
        .where(
            models.OrganizationTeamPerformanceGrant.organization_id == organization_id,
            models.OrganizationTeamPerformanceGrant.status == "active",
            models.OrganizationTeamPerformanceGrant.effective_from <= now,
            (
                models.OrganizationTeamPerformanceGrant.effective_until.is_(None)
                | (models.OrganizationTeamPerformanceGrant.effective_until > now)
            ),
        )
        .order_by(models.OrganizationTeamPerformanceGrant.granted_at.desc())
        .limit(1)
    )
    if grant is None:
        raise TeamPerformanceAccessError(403, "Team Performance is unavailable")

    team = await db.scalar(
        select(models.Team).where(
            models.Team.id == team_id,
            models.Team.organization_id == organization_id,
        )
    )
    if team is None:
        raise TeamPerformanceAccessError(404, "Team not found")
    return team
