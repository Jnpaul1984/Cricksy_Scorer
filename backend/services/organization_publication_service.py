"""Default-private, reversible organization publication persistence."""

from __future__ import annotations

import re
import uuid

import structlog
from backend.services.organization_service import (
    ACTIVE_MEMBERSHIP_STATUS,
    ACTIVE_ORGANIZATION_STATUS,
    OrganizationServiceError,
)
from backend.sql_app.models import Organization, OrganizationMembership, OrganizationPublicSettings
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

PUBLIC_IDENTIFIER_PATTERN = re.compile(r"^org_[0-9a-f]{24}$")
PUBLICATION_MANAGERS = {"owner", "admin"}
_PUBLIC_IDENTIFIER_NAMESPACE = uuid.UUID("f095452d-9128-46ac-9a82-d504819bcb64")
_PUBLIC_IDENTIFIER_UNIQUE_CONSTRAINT = "uq_organization_public_settings_public_identifier"
_PUBLIC_SETTINGS_PRIMARY_KEY_CONSTRAINT = "organization_public_settings_pkey"


def public_identifier_candidate(organization_id: str, collision_attempt: int = 0) -> str:
    """Derive an opaque stable candidate without exposing the tenant UUID."""
    seed = f"{organization_id}:{collision_attempt}"
    return f"org_{uuid.uuid5(_PUBLIC_IDENTIFIER_NAMESPACE, seed).hex[:24]}"


def _integrity_constraint_name(exc: IntegrityError) -> str | None:
    current: BaseException | None = exc.orig
    while current is not None:
        constraint_name = getattr(current, "constraint_name", None)
        if isinstance(constraint_name, str):
            return constraint_name
        current = current.__cause__ or current.__context__
    return None


async def create_default_settings(
    db: AsyncSession, *, organization_id: str
) -> OrganizationPublicSettings:
    """Insert one settings row, retrying identifier collisions under DB authority."""
    for collision_attempt in range(100):
        settings = OrganizationPublicSettings(
            organization_id=organization_id,
            public_identifier=public_identifier_candidate(organization_id, collision_attempt),
            publication_state="unpublished",
        )
        try:
            async with db.begin_nested():
                db.add(settings)
                await db.flush()
        except IntegrityError as exc:
            constraint_name = _integrity_constraint_name(exc)
            if constraint_name == _PUBLIC_SETTINGS_PRIMARY_KEY_CONSTRAINT:
                existing = await db.get(OrganizationPublicSettings, organization_id)
                if existing is not None:
                    return existing
            if constraint_name == _PUBLIC_IDENTIFIER_UNIQUE_CONSTRAINT:
                continue
            raise
        return settings
    raise RuntimeError("Unable to allocate organization public identifier")


async def _lock_active_organization(db: AsyncSession, *, organization_id: str) -> Organization:
    organization = await db.scalar(
        select(Organization)
        .where(
            Organization.id == organization_id,
            Organization.status == ACTIVE_ORGANIZATION_STATUS,
        )
        .with_for_update()
    )
    if organization is None:
        raise OrganizationServiceError(404, "Organization not found")
    return organization


async def _current_membership(
    db: AsyncSession, *, organization_id: str, actor_user_id: str, manage: bool
) -> OrganizationMembership:
    membership = await db.scalar(
        select(OrganizationMembership)
        .join(Organization, Organization.id == OrganizationMembership.organization_id)
        .where(
            OrganizationMembership.organization_id == organization_id,
            OrganizationMembership.user_id == actor_user_id,
            OrganizationMembership.status == ACTIVE_MEMBERSHIP_STATUS,
            Organization.status == ACTIVE_ORGANIZATION_STATUS,
        )
    )
    if membership is None:
        raise OrganizationServiceError(404, "Organization not found")
    if manage and membership.role not in PUBLICATION_MANAGERS:
        raise OrganizationServiceError(403, "Insufficient organization role")
    return membership


async def get_settings(
    db: AsyncSession, *, organization_id: str, actor_user_id: str
) -> OrganizationPublicSettings:
    await _current_membership(
        db, organization_id=organization_id, actor_user_id=actor_user_id, manage=False
    )
    settings = await db.get(OrganizationPublicSettings, organization_id)
    if settings is None:
        raise OrganizationServiceError(404, "Organization not found")
    return settings


async def set_publication_state(
    db: AsyncSession, *, organization_id: str, actor_user_id: str, publish: bool
) -> OrganizationPublicSettings:
    """Serialize with membership changes and make repeated transitions idempotent."""
    await _lock_active_organization(db, organization_id=organization_id)
    await _current_membership(
        db, organization_id=organization_id, actor_user_id=actor_user_id, manage=True
    )
    settings = await db.scalar(
        select(OrganizationPublicSettings)
        .where(OrganizationPublicSettings.organization_id == organization_id)
        .with_for_update()
    )
    if settings is None:
        settings = await create_default_settings(db, organization_id=organization_id)
        await db.flush()

    requested_state = "published" if publish else "unpublished"
    if settings.publication_state != requested_state:
        now = await db.scalar(select(func.now()))
        settings.publication_state = requested_state
        settings.publication_version += 1
        settings.updated_by_user_id = actor_user_id
        if publish:
            settings.published_at = now
            settings.published_by_user_id = actor_user_id
        else:
            settings.unpublished_at = now
            settings.unpublished_by_user_id = actor_user_id
    await db.commit()
    await db.refresh(settings)
    logger.info(
        "organization.publication_changed",
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        publication_state=settings.publication_state,
        publication_version=settings.publication_version,
    )
    return settings


async def get_public_organization(
    db: AsyncSession, *, public_identifier: str
) -> tuple[str, str, str] | None:
    if not PUBLIC_IDENTIFIER_PATTERN.fullmatch(public_identifier):
        return None
    row = (
        await db.execute(
            select(
                OrganizationPublicSettings.public_identifier,
                Organization.name,
                Organization.organization_type,
            )
            .join(Organization, Organization.id == OrganizationPublicSettings.organization_id)
            .where(
                OrganizationPublicSettings.public_identifier == public_identifier,
                OrganizationPublicSettings.publication_state == "published",
                Organization.status == ACTIVE_ORGANIZATION_STATUS,
            )
            .limit(1)
        )
    ).one_or_none()
    return None if row is None else (row[0], row[1], row[2])
