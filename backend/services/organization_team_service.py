"""Organization-scoped persistent School team operations for Phase 7D."""

from __future__ import annotations

from dataclasses import dataclass

import structlog
from backend.api.schemas.organizations import SchoolTeamCreate, SchoolTeamUpdate
from backend.services import organization_service
from backend.services.organization_entitlement_service import (
    require_organization_capability,
)
from backend.sql_app.models import Team
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

SCHOOL_TEAM_CAPABILITY = "school_persistent_teams"
TEAM_READ_ROLES = frozenset({"owner", "admin", "coach", "scorer", "viewer"})
TEAM_WRITE_ROLES = frozenset({"owner", "admin", "coach"})
TEAM_ARCHIVE_ROLES = frozenset({"owner", "admin"})


@dataclass(frozen=True)
class OrganizationTeamServiceError(Exception):
    status_code: int
    detail: str


def _team_not_found() -> OrganizationTeamServiceError:
    return OrganizationTeamServiceError(404, "Team not found")


def _forbidden() -> OrganizationTeamServiceError:
    return OrganizationTeamServiceError(403, "Insufficient organization role")


async def _require_team_role(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    allowed_roles: frozenset[str],
) -> None:
    """Reuse the Phase 7C gate, then apply the membership-role matrix."""
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability=SCHOOL_TEAM_CAPABILITY,
    )
    _, membership = await organization_service.get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if membership.role not in allowed_roles:
        logger.warning(
            "organization.team_role_denied",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            membership_role=membership.role,
        )
        raise _forbidden()


async def list_teams(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
) -> list[Team]:
    await _require_team_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=TEAM_READ_ROLES,
    )
    result = await db.execute(
        select(Team)
        .where(
            Team.organization_id == organization_id,
            Team.status == "active",
        )
        .order_by(Team.name, Team.id)
    )
    return list(result.scalars().all())


async def create_team(
    db: AsyncSession,
    *,
    organization_id: str,
    payload: SchoolTeamCreate,
    actor_user_id: str,
) -> Team:
    await _require_team_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=TEAM_WRITE_ROLES,
    )
    team = Team(
        organization_id=organization_id,
        status="active",
        name=payload.name,
        home_ground=payload.home_ground,
        season=payload.season,
        owner_user_id=actor_user_id,
        coach_user_id=payload.coach_id,
        coach_name=payload.coach_name,
        players=[],
        competitions=[],
    )
    db.add(team)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception(
            "organization.team_create_failed",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
        raise
    await db.refresh(team)
    return team


async def get_team(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    actor_user_id: str,
) -> Team:
    await _require_team_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=TEAM_READ_ROLES,
    )
    result = await db.execute(
        select(Team).where(
            Team.id == team_id,
            Team.organization_id == organization_id,
        )
    )
    team = result.scalar_one_or_none()
    if team is None:
        raise _team_not_found()
    return team


async def update_team(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    payload: SchoolTeamUpdate,
    actor_user_id: str,
) -> Team:
    await _require_team_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=TEAM_WRITE_ROLES,
    )
    result = await db.execute(
        select(Team).where(
            Team.id == team_id,
            Team.organization_id == organization_id,
        )
    )
    team = result.scalar_one_or_none()
    if team is None:
        raise _team_not_found()

    changes = payload.model_dump(exclude_unset=True)
    if "coach_id" in changes:
        team.coach_user_id = changes.pop("coach_id")
    for field, value in changes.items():
        setattr(team, field, value)

    await db.commit()
    await db.refresh(team)
    return team


async def archive_team(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    actor_user_id: str,
) -> None:
    await _require_team_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=TEAM_ARCHIVE_ROLES,
    )
    result = await db.execute(
        select(Team).where(
            Team.id == team_id,
            Team.organization_id == organization_id,
        )
    )
    team = result.scalar_one_or_none()
    if team is None:
        raise _team_not_found()
    team.status = "archived"
    await db.commit()
