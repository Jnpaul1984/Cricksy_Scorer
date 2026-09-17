"""Organization-scoped normalized School Team roster operations for Phase 7F."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog
from backend.api.schemas.organizations import (
    SchoolTeamRosterPlayerCreate,
    SchoolTeamRosterPlayerUpdate,
)
from backend.services import organization_service
from backend.services.organization_entitlement_service import (
    require_organization_capability,
)
from backend.sql_app.models import (
    PlayerProfile,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
)
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

TEAM_CAPABILITY = "school_persistent_teams"
TEAM_ROSTER_CAPABILITY = "school_team_rosters"
TEAM_ROSTER_READ_ROLES = frozenset({"owner", "admin", "coach", "scorer", "viewer"})
TEAM_ROSTER_WRITE_ROLES = frozenset({"owner", "admin", "coach"})


@dataclass(frozen=True)
class OrganizationTeamRosterServiceError(Exception):
    status_code: int
    detail: str


@dataclass(frozen=True)
class SchoolTeamRosterRecord:
    membership: SchoolTeamPlayerMembership
    team: Team
    school_player_membership: SchoolPlayerMembership
    player_profile: PlayerProfile

    @property
    def operationally_available(self) -> bool:
        """Phase 7I eligibility input without implementing match selection."""
        return (
            self.membership.status == "active"
            and self.school_player_membership.status == "active"
            and self.team.status == "active"
        )


def _new_id() -> str:
    return str(uuid.uuid4())


def _team_not_found() -> OrganizationTeamRosterServiceError:
    return OrganizationTeamRosterServiceError(404, "Team not found")


def _school_player_not_found() -> OrganizationTeamRosterServiceError:
    return OrganizationTeamRosterServiceError(404, "Roster player not found")


def _team_roster_player_not_found() -> OrganizationTeamRosterServiceError:
    return OrganizationTeamRosterServiceError(404, "Team roster player not found")


def _forbidden() -> OrganizationTeamRosterServiceError:
    return OrganizationTeamRosterServiceError(403, "Insufficient organization role")


def _duplicate() -> OrganizationTeamRosterServiceError:
    return OrganizationTeamRosterServiceError(409, "Player is already on this Team roster")


def _archived_team() -> OrganizationTeamRosterServiceError:
    return OrganizationTeamRosterServiceError(
        409, "Archived Team cannot receive roster assignments"
    )


def _inactive_school_player() -> OrganizationTeamRosterServiceError:
    return OrganizationTeamRosterServiceError(
        409, "Inactive School roster player cannot be assigned"
    )


async def _require_team_roster_role(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    allowed_roles: frozenset[str],
) -> None:
    """Require both Phase 7C capabilities plus the scoped membership role."""
    for capability in (TEAM_CAPABILITY, TEAM_ROSTER_CAPABILITY):
        await require_organization_capability(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            capability=capability,
        )
    _, membership = await organization_service.get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if membership.role not in allowed_roles:
        logger.warning(
            "organization.team_roster_role_denied",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            membership_role=membership.role,
        )
        raise _forbidden()


async def _get_team(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
) -> Team:
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


async def _get_school_player(
    db: AsyncSession,
    *,
    organization_id: str,
    school_player_membership_id: str,
) -> SchoolPlayerMembership:
    result = await db.execute(
        select(SchoolPlayerMembership).where(
            SchoolPlayerMembership.id == school_player_membership_id,
            SchoolPlayerMembership.organization_id == organization_id,
        )
    )
    membership = result.scalar_one_or_none()
    if membership is None:
        raise _school_player_not_found()
    return membership


def _record_query():
    # Same-organization equality is deliberately enforced in service joins. Adding
    # composite parent keys solely for 7F would broaden the protected Team/School
    # roster schemas; the ordinary FKs remain the database deletion authority.
    return (
        select(
            SchoolTeamPlayerMembership,
            Team,
            SchoolPlayerMembership,
            PlayerProfile,
        )
        .join(
            Team,
            and_(
                Team.id == SchoolTeamPlayerMembership.team_id,
                Team.organization_id == SchoolTeamPlayerMembership.organization_id,
            ),
        )
        .join(
            SchoolPlayerMembership,
            and_(
                SchoolPlayerMembership.id == SchoolTeamPlayerMembership.school_player_membership_id,
                SchoolPlayerMembership.organization_id
                == SchoolTeamPlayerMembership.organization_id,
            ),
        )
        .join(
            PlayerProfile,
            PlayerProfile.player_id == SchoolPlayerMembership.player_profile_id,
        )
    )


def _record(
    row: tuple[
        SchoolTeamPlayerMembership,
        Team,
        SchoolPlayerMembership,
        PlayerProfile,
    ],
) -> SchoolTeamRosterRecord:
    return SchoolTeamRosterRecord(
        membership=row[0],
        team=row[1],
        school_player_membership=row[2],
        player_profile=row[3],
    )


async def list_team_roster_players(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    actor_user_id: str,
) -> list[SchoolTeamRosterRecord]:
    await _require_team_roster_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=TEAM_ROSTER_READ_ROLES,
    )
    await _get_team(db, organization_id=organization_id, team_id=team_id)
    result = await db.execute(
        _record_query()
        .where(
            SchoolTeamPlayerMembership.organization_id == organization_id,
            SchoolTeamPlayerMembership.team_id == team_id,
        )
        .order_by(PlayerProfile.player_name, SchoolTeamPlayerMembership.id)
    )
    return [_record(row) for row in result.tuples().all()]


async def create_team_roster_player(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    payload: SchoolTeamRosterPlayerCreate,
    actor_user_id: str,
) -> SchoolTeamRosterRecord:
    await _require_team_roster_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=TEAM_ROSTER_WRITE_ROLES,
    )
    team = await _get_team(db, organization_id=organization_id, team_id=team_id)
    if team.status != "active":
        raise _archived_team()
    school_player = await _get_school_player(
        db,
        organization_id=organization_id,
        school_player_membership_id=payload.school_player_membership_id,
    )
    if school_player.status != "active":
        raise _inactive_school_player()

    existing = await db.scalar(
        select(SchoolTeamPlayerMembership.id).where(
            SchoolTeamPlayerMembership.team_id == team_id,
            SchoolTeamPlayerMembership.school_player_membership_id
            == payload.school_player_membership_id,
        )
    )
    if existing is not None:
        raise _duplicate()

    membership = SchoolTeamPlayerMembership(
        id=_new_id(),
        organization_id=organization_id,
        team_id=team_id,
        school_player_membership_id=payload.school_player_membership_id,
        status="active",
        created_by_user_id=actor_user_id,
    )
    db.add(membership)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.info(
            "organization.team_roster_duplicate",
            organization_id=organization_id,
            team_id=team_id,
            school_player_membership_id=payload.school_player_membership_id,
            actor_user_id=actor_user_id,
        )
        raise _duplicate() from exc
    except Exception:
        await db.rollback()
        logger.exception(
            "organization.team_roster_create_failed",
            organization_id=organization_id,
            team_id=team_id,
            school_player_membership_id=payload.school_player_membership_id,
            actor_user_id=actor_user_id,
        )
        raise
    return await get_team_roster_player(
        db,
        organization_id=organization_id,
        team_id=team_id,
        team_roster_membership_id=membership.id,
        actor_user_id=actor_user_id,
    )


async def get_team_roster_player(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    team_roster_membership_id: str,
    actor_user_id: str,
) -> SchoolTeamRosterRecord:
    await _require_team_roster_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=TEAM_ROSTER_READ_ROLES,
    )
    result = await db.execute(
        _record_query().where(
            SchoolTeamPlayerMembership.id == team_roster_membership_id,
            SchoolTeamPlayerMembership.organization_id == organization_id,
            SchoolTeamPlayerMembership.team_id == team_id,
        )
    )
    row = result.tuples().one_or_none()
    if row is None:
        raise _team_roster_player_not_found()
    return _record(row)


async def update_team_roster_player(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    team_roster_membership_id: str,
    payload: SchoolTeamRosterPlayerUpdate,
    actor_user_id: str,
) -> SchoolTeamRosterRecord:
    await _require_team_roster_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=TEAM_ROSTER_WRITE_ROLES,
    )
    record = await get_team_roster_player(
        db,
        organization_id=organization_id,
        team_id=team_id,
        team_roster_membership_id=team_roster_membership_id,
        actor_user_id=actor_user_id,
    )
    if payload.status == "active" and record.membership.status != "active":
        if record.team.status != "active":
            raise _archived_team()
        if record.school_player_membership.status != "active":
            raise _inactive_school_player()
    if payload.status != record.membership.status:
        record.membership.status = payload.status
        await db.commit()
        await db.refresh(record.membership)
    return record


async def deactivate_team_roster_player(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    team_roster_membership_id: str,
    actor_user_id: str,
) -> None:
    await _require_team_roster_role(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=TEAM_ROSTER_WRITE_ROLES,
    )
    record = await get_team_roster_player(
        db,
        organization_id=organization_id,
        team_id=team_id,
        team_roster_membership_id=team_roster_membership_id,
        actor_user_id=actor_user_id,
    )
    if record.membership.status != "inactive":
        record.membership.status = "inactive"
        await db.commit()
