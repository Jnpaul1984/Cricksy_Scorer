"""Organization-scoped School master-roster operations for Phase 7E."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Literal

import structlog
from backend.api.schemas.organizations import (
    SchoolRosterPlayerCreate,
    SchoolRosterPlayerLink,
    SchoolRosterPlayerUpdate,
)
from backend.services import organization_service
from backend.services.organization_entitlement_service import (
    require_organization_capability,
)
from backend.sql_app.models import PlayerProfile, SchoolPlayerMembership
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

SCHOOL_ROSTER_CAPABILITY = "school_master_roster"
ROSTER_READ_ROLES = frozenset({"owner", "admin", "coach", "scorer", "viewer"})
ROSTER_WRITE_ROLES = frozenset({"owner", "admin", "coach"})
ROSTER_DEACTIVATE_ROLES = frozenset({"owner", "admin"})


@dataclass(frozen=True)
class OrganizationRosterServiceError(Exception):
    status_code: int
    detail: str


@dataclass(frozen=True)
class SchoolRosterRecord:
    membership: SchoolPlayerMembership
    player_profile: PlayerProfile


def _new_id() -> str:
    return str(uuid.uuid4())


def _roster_not_found() -> OrganizationRosterServiceError:
    return OrganizationRosterServiceError(404, "Roster player not found")


def _player_not_found() -> OrganizationRosterServiceError:
    return OrganizationRosterServiceError(404, "Player profile not found")


def _forbidden() -> OrganizationRosterServiceError:
    return OrganizationRosterServiceError(403, "Insufficient organization role")


def _duplicate() -> OrganizationRosterServiceError:
    return OrganizationRosterServiceError(409, "Player is already on this school roster")


async def _require_roster_role(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    allowed_roles: frozenset[str],
) -> None:
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability=SCHOOL_ROSTER_CAPABILITY,
    )
    _, membership = await organization_service.get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if membership.role not in allowed_roles:
        logger.warning(
            "organization.roster_role_denied",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            membership_role=membership.role,
        )
        raise _forbidden()


def _record(row: tuple[SchoolPlayerMembership, PlayerProfile]) -> SchoolRosterRecord:
    return SchoolRosterRecord(membership=row[0], player_profile=row[1])


async def _commit_new_membership(
    db: AsyncSession,
    *,
    membership: SchoolPlayerMembership,
    player_profile: PlayerProfile,
    organization_id: str,
    actor_user_id: str,
) -> SchoolRosterRecord:
    player_profile_id = player_profile.player_id
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.info(
            "organization.roster_duplicate",
            organization_id=organization_id,
            player_profile_id=player_profile_id,
            actor_user_id=actor_user_id,
        )
        raise _duplicate() from exc
    except Exception:
        await db.rollback()
        logger.exception(
            "organization.roster_create_failed",
            organization_id=organization_id,
            player_profile_id=player_profile_id,
            actor_user_id=actor_user_id,
        )
        raise
    await db.refresh(membership)
    return SchoolRosterRecord(membership=membership, player_profile=player_profile)


async def list_roster_players(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    status_filter: Literal["active", "inactive", "all"] = "active",
) -> list[SchoolRosterRecord]:
    await _require_roster_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=ROSTER_READ_ROLES,
    )
    query = (
        select(SchoolPlayerMembership, PlayerProfile)
        .join(
            PlayerProfile,
            PlayerProfile.player_id == SchoolPlayerMembership.player_profile_id,
        )
        .where(SchoolPlayerMembership.organization_id == organization_id)
        .order_by(PlayerProfile.player_name, SchoolPlayerMembership.id)
    )
    if status_filter != "all":
        query = query.where(SchoolPlayerMembership.status == status_filter)
    result = await db.execute(query)
    return [_record(row) for row in result.tuples().all()]


async def create_roster_player(
    db: AsyncSession,
    *,
    organization_id: str,
    payload: SchoolRosterPlayerCreate,
    actor_user_id: str,
) -> SchoolRosterRecord:
    await _require_roster_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=ROSTER_WRITE_ROLES,
    )
    player_profile = PlayerProfile(
        player_id=_new_id(),
        player_name=payload.player_name,
    )
    membership = SchoolPlayerMembership(
        id=_new_id(),
        organization_id=organization_id,
        player_profile_id=player_profile.player_id,
        status="active",
        student_identifier=payload.student_identifier,
        year_group=payload.year_group,
        created_by_user_id=actor_user_id,
    )
    db.add_all([player_profile, membership])
    return await _commit_new_membership(
        db,
        membership=membership,
        player_profile=player_profile,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
    )


async def link_roster_player(
    db: AsyncSession,
    *,
    organization_id: str,
    payload: SchoolRosterPlayerLink,
    actor_user_id: str,
) -> SchoolRosterRecord:
    await _require_roster_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=ROSTER_WRITE_ROLES,
    )
    player_profile = await db.get(PlayerProfile, payload.player_profile_id)
    if player_profile is None:
        raise _player_not_found()
    membership = SchoolPlayerMembership(
        id=_new_id(),
        organization_id=organization_id,
        player_profile_id=player_profile.player_id,
        status="active",
        student_identifier=payload.student_identifier,
        year_group=payload.year_group,
        created_by_user_id=actor_user_id,
    )
    db.add(membership)
    return await _commit_new_membership(
        db,
        membership=membership,
        player_profile=player_profile,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
    )


async def get_roster_player(
    db: AsyncSession,
    *,
    organization_id: str,
    roster_membership_id: str,
    actor_user_id: str,
) -> SchoolRosterRecord:
    await _require_roster_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=ROSTER_READ_ROLES,
    )
    result = await db.execute(
        select(SchoolPlayerMembership, PlayerProfile)
        .join(
            PlayerProfile,
            PlayerProfile.player_id == SchoolPlayerMembership.player_profile_id,
        )
        .where(
            SchoolPlayerMembership.id == roster_membership_id,
            SchoolPlayerMembership.organization_id == organization_id,
        )
    )
    row = result.tuples().one_or_none()
    if row is None:
        raise _roster_not_found()
    return _record(row)


async def update_roster_player(
    db: AsyncSession,
    *,
    organization_id: str,
    roster_membership_id: str,
    payload: SchoolRosterPlayerUpdate,
    actor_user_id: str,
) -> SchoolRosterRecord:
    await _require_roster_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=ROSTER_WRITE_ROLES,
    )
    record = await get_roster_player(
        db,
        organization_id=organization_id,
        roster_membership_id=roster_membership_id,
        actor_user_id=actor_user_id,
    )
    if (
        "status" in payload.model_fields_set
        and payload.status is not None
        and payload.status != record.membership.status
    ):
        await _require_roster_role(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            allowed_roles=ROSTER_DEACTIVATE_ROLES,
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "status" and value is None:
            continue
        setattr(record.membership, field, value)
    await db.commit()
    await db.refresh(record.membership)
    return record


async def deactivate_roster_player(
    db: AsyncSession,
    *,
    organization_id: str,
    roster_membership_id: str,
    actor_user_id: str,
) -> None:
    await _require_roster_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=ROSTER_DEACTIVATE_ROLES,
    )
    result = await db.execute(
        select(SchoolPlayerMembership).where(
            SchoolPlayerMembership.id == roster_membership_id,
            SchoolPlayerMembership.organization_id == organization_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise _roster_not_found()
    membership.status = "inactive"
    await db.commit()
