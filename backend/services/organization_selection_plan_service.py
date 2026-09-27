"""Tenant-safe shared School/Club draft selection-plan operations."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import structlog
from backend.api.schemas.organization_selection_plans import (
    OrganizationSelectionCandidate,
    OrganizationSelectionCandidateResponse,
    OrganizationSelectionPlanCreate,
    OrganizationSelectionPlanResponse,
    OrganizationSelectionPlanUpdate,
)
from backend.services import organization_service
from backend.services.organization_entitlement_service import require_organization_capability
from backend.sql_app.models import (
    Fixture,
    Organization,
    OrganizationSelectionPlan,
    OrganizationSelectionPlanPlayer,
    PlayerProfile,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
    Tournament,
)
from sqlalchemy import and_, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

SELECTION_PLAN_CAPABILITY = "organization_selection_plans"
SELECTION_READ_ROLES = frozenset({"owner", "admin", "coach", "scorer", "viewer"})
SELECTION_WRITE_ROLES = frozenset({"owner", "admin", "coach"})


@dataclass(frozen=True)
class OrganizationSelectionPlanServiceError(Exception):
    status_code: int
    detail: str


def _not_found(resource: str) -> OrganizationSelectionPlanServiceError:
    return OrganizationSelectionPlanServiceError(404, f"{resource} not found")


def _forbidden() -> OrganizationSelectionPlanServiceError:
    return OrganizationSelectionPlanServiceError(403, "Insufficient organization role")


def _invalid(detail: str) -> OrganizationSelectionPlanServiceError:
    return OrganizationSelectionPlanServiceError(422, detail)


def _conflict(detail: str) -> OrganizationSelectionPlanServiceError:
    return OrganizationSelectionPlanServiceError(409, detail)


async def _authorize(
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
        capability=SELECTION_PLAN_CAPABILITY,
    )
    _, membership = await organization_service.get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if membership.role not in allowed_roles:
        raise _forbidden()


async def _team_and_fixture(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    fixture_id: str,
) -> tuple[Team, Fixture]:
    team = await db.scalar(
        select(Team).where(
            Team.id == team_id,
            Team.organization_id == organization_id,
        )
    )
    if team is None:
        raise _not_found("Team")
    if team.status != "active":
        raise _conflict("Archived Team cannot be used for a selection plan")

    row = (
        await db.execute(
            select(Fixture, Tournament)
            .join(Tournament, Tournament.id == Fixture.tournament_id)
            .where(
                Fixture.id == fixture_id,
                Tournament.organization_id == organization_id,
            )
        )
    ).one_or_none()
    if row is None:
        raise _not_found("Fixture")
    fixture: Fixture = row[0]
    if fixture.status != "scheduled":
        raise _conflict("Only scheduled Fixtures can receive a draft selection plan")
    if fixture.team_a_id is None or fixture.team_b_id is None:
        raise _invalid("Fixture must use two normalized organization Teams")
    if fixture.team_a_id == fixture.team_b_id:
        raise _invalid("Fixture Team identity is ambiguous")
    if team.id not in {fixture.team_a_id, fixture.team_b_id}:
        raise _invalid("Selection Team is not represented by this Fixture")
    fixture_team_ids = set(
        (
            await db.scalars(
                select(Team.id).where(
                    Team.organization_id == organization_id,
                    Team.status == "active",
                    Team.id.in_([fixture.team_a_id, fixture.team_b_id]),
                )
            )
        ).all()
    )
    if fixture_team_ids != {fixture.team_a_id, fixture.team_b_id}:
        raise _invalid("Fixture must use two active normalized organization Teams")
    return team, fixture


async def _plan(
    db: AsyncSession,
    *,
    organization_id: str,
    plan_id: str,
    lock: bool = False,
) -> OrganizationSelectionPlan:
    statement = select(OrganizationSelectionPlan).where(
        OrganizationSelectionPlan.id == plan_id,
        OrganizationSelectionPlan.organization_id == organization_id,
    )
    if lock:
        statement = statement.with_for_update()
    plan = await db.scalar(statement)
    if plan is None:
        raise _not_found("Selection plan")
    return plan


async def _selection_memberships(
    db: AsyncSession,
    *,
    organization_id: str,
    plan_id: str,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    rows = list(
        (
            await db.execute(
                select(
                    OrganizationSelectionPlanPlayer.school_player_membership_id,
                    OrganizationSelectionPlanPlayer.selection_role,
                )
                .where(
                    OrganizationSelectionPlanPlayer.organization_id == organization_id,
                    OrganizationSelectionPlanPlayer.selection_plan_id == plan_id,
                )
                .order_by(
                    OrganizationSelectionPlanPlayer.selection_role,
                    OrganizationSelectionPlanPlayer.school_player_membership_id,
                )
            )
        ).all()
    )
    xi = tuple(sorted(row[0] for row in rows if row[1] == "xi"))
    reserves = tuple(sorted(row[0] for row in rows if row[1] == "reserve"))
    return xi, reserves


async def _response(
    db: AsyncSession,
    plan: OrganizationSelectionPlan,
) -> OrganizationSelectionPlanResponse:
    xi, reserves = await _selection_memberships(
        db,
        organization_id=plan.organization_id,
        plan_id=plan.id,
    )
    return OrganizationSelectionPlanResponse(
        id=plan.id,
        organization_id=plan.organization_id,
        team_id=plan.team_id,
        fixture_id=plan.fixture_id,
        status=plan.status,  # type: ignore[arg-type]
        revision=plan.revision,
        xi_roster_membership_ids=list(xi),
        reserve_roster_membership_ids=list(reserves),
        captain_roster_membership_id=plan.captain_roster_membership_id,
        wicketkeeper_roster_membership_id=plan.wicketkeeper_roster_membership_id,
        created_by_user_id=plan.created_by_user_id,
        updated_by_user_id=plan.updated_by_user_id,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


async def create_or_open_selection_plan(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    payload: OrganizationSelectionPlanCreate,
) -> OrganizationSelectionPlanResponse:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=SELECTION_WRITE_ROLES,
    )
    organization = await db.scalar(
        select(Organization)
        .where(Organization.id == organization_id, Organization.status == "active")
        .with_for_update()
    )
    if organization is None:
        raise _not_found("Organization")
    _, fixture = await _team_and_fixture(
        db,
        organization_id=organization_id,
        team_id=payload.team_id,
        fixture_id=payload.fixture_id,
    )
    existing = await db.scalar(
        select(OrganizationSelectionPlan).where(
            OrganizationSelectionPlan.organization_id == organization_id,
            OrganizationSelectionPlan.team_id == payload.team_id,
            OrganizationSelectionPlan.fixture_id == payload.fixture_id,
        )
    )
    if existing is not None:
        await db.commit()
        return await _response(db, existing)

    plan = OrganizationSelectionPlan(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        team_id=payload.team_id,
        fixture_id=fixture.id,
        fixture_tournament_id=fixture.tournament_id,
        status="draft",
        revision=1,
        captain_roster_membership_id=None,
        wicketkeeper_roster_membership_id=None,
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
    )
    db.add(plan)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict("Selection plan was created concurrently; open the existing plan") from exc
    await db.refresh(plan)
    return await _response(db, plan)


async def get_selection_plan(
    db: AsyncSession,
    *,
    organization_id: str,
    plan_id: str,
    actor_user_id: str,
) -> OrganizationSelectionPlanResponse:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=SELECTION_READ_ROLES,
    )
    plan = await _plan(db, organization_id=organization_id, plan_id=plan_id)
    return await _response(db, plan)


async def _validate_active_candidates(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str,
    roster_membership_ids: set[str],
) -> None:
    if not roster_membership_ids:
        return
    eligible = set(
        (
            await db.scalars(
                select(SchoolPlayerMembership.id)
                .join(
                    SchoolTeamPlayerMembership,
                    and_(
                        SchoolTeamPlayerMembership.school_player_membership_id
                        == SchoolPlayerMembership.id,
                        SchoolTeamPlayerMembership.organization_id
                        == SchoolPlayerMembership.organization_id,
                    ),
                )
                .join(
                    Team,
                    and_(
                        Team.id == SchoolTeamPlayerMembership.team_id,
                        Team.organization_id == SchoolTeamPlayerMembership.organization_id,
                    ),
                )
                .where(
                    SchoolPlayerMembership.organization_id == organization_id,
                    SchoolPlayerMembership.status == "active",
                    SchoolTeamPlayerMembership.organization_id == organization_id,
                    SchoolTeamPlayerMembership.team_id == team_id,
                    SchoolTeamPlayerMembership.status == "active",
                    Team.status == "active",
                    SchoolPlayerMembership.id.in_(roster_membership_ids),
                )
            )
        ).all()
    )
    if eligible != roster_membership_ids:
        raise _invalid("One or more players are not active normalized Team roster candidates")


async def update_selection_plan(
    db: AsyncSession,
    *,
    organization_id: str,
    plan_id: str,
    actor_user_id: str,
    payload: OrganizationSelectionPlanUpdate,
) -> OrganizationSelectionPlanResponse:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=SELECTION_WRITE_ROLES,
    )
    plan = await _plan(db, organization_id=organization_id, plan_id=plan_id, lock=True)
    if plan.status != "draft":
        raise _conflict("Only draft selection plans can be changed")
    current_xi, current_reserves = await _selection_memberships(
        db,
        organization_id=organization_id,
        plan_id=plan.id,
    )
    supplied = payload.model_fields_set
    next_xi = (
        tuple(sorted(payload.xi_roster_membership_ids))
        if "xi_roster_membership_ids" in supplied
        else current_xi
    )
    next_reserves = (
        tuple(sorted(payload.reserve_roster_membership_ids))
        if "reserve_roster_membership_ids" in supplied
        else current_reserves
    )
    next_captain = (
        payload.captain_roster_membership_id
        if "captain_roster_membership_id" in supplied
        else plan.captain_roster_membership_id
    )
    next_wicketkeeper = (
        payload.wicketkeeper_roster_membership_id
        if "wicketkeeper_roster_membership_id" in supplied
        else plan.wicketkeeper_roster_membership_id
    )

    if len(next_xi) > 11:
        raise _invalid("Planned XI cannot contain more than 11 players")
    if len(set(next_xi)) != len(next_xi):
        raise _invalid("Planned XI cannot contain duplicate roster memberships")
    if len(set(next_reserves)) != len(next_reserves):
        raise _invalid("Reserves cannot contain duplicate roster memberships")
    if set(next_xi) & set(next_reserves):
        raise _invalid("A player cannot be both planned XI and reserve")
    if next_captain is not None and next_captain not in next_xi:
        raise _invalid("Captain must be a member of the planned XI")
    if next_wicketkeeper is not None and next_wicketkeeper not in next_xi:
        raise _invalid("Wicketkeeper must be a member of the planned XI")

    material_state = (
        next_xi,
        next_reserves,
        next_captain,
        next_wicketkeeper,
    )
    current_state = (
        current_xi,
        current_reserves,
        plan.captain_roster_membership_id,
        plan.wicketkeeper_roster_membership_id,
    )
    if payload.expected_revision != plan.revision:
        if material_state == current_state:
            await db.commit()
            return await _response(db, plan)
        raise _conflict(f"Selection plan revision is stale; current revision is {plan.revision}")
    if material_state == current_state:
        await db.commit()
        return await _response(db, plan)

    await _validate_active_candidates(
        db,
        organization_id=organization_id,
        team_id=plan.team_id,
        roster_membership_ids=set(next_xi) | set(next_reserves),
    )
    await db.execute(
        delete(OrganizationSelectionPlanPlayer).where(
            OrganizationSelectionPlanPlayer.organization_id == organization_id,
            OrganizationSelectionPlanPlayer.selection_plan_id == plan.id,
        )
    )
    db.add_all(
        [
            OrganizationSelectionPlanPlayer(
                selection_plan_id=plan.id,
                school_player_membership_id=membership_id,
                organization_id=organization_id,
                selection_role=role,
            )
            for role, membership_ids in (("xi", next_xi), ("reserve", next_reserves))
            for membership_id in membership_ids
        ]
    )
    plan.captain_roster_membership_id = next_captain
    plan.wicketkeeper_roster_membership_id = next_wicketkeeper
    plan.updated_by_user_id = actor_user_id
    plan.revision += 1
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning(
            "organization.selection_plan_update_conflict",
            organization_id=organization_id,
            plan_id=plan_id,
        )
        raise _conflict("Selection plan update conflicted; reload and retry") from exc
    await db.refresh(plan)
    return await _response(db, plan)


async def selection_candidates(
    db: AsyncSession,
    *,
    organization_id: str,
    plan_id: str,
    actor_user_id: str,
) -> OrganizationSelectionCandidateResponse:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=SELECTION_READ_ROLES,
    )
    plan = await _plan(db, organization_id=organization_id, plan_id=plan_id)
    rows = list(
        (
            await db.execute(
                select(SchoolPlayerMembership, PlayerProfile)
                .join(
                    SchoolTeamPlayerMembership,
                    and_(
                        SchoolTeamPlayerMembership.school_player_membership_id
                        == SchoolPlayerMembership.id,
                        SchoolTeamPlayerMembership.organization_id
                        == SchoolPlayerMembership.organization_id,
                    ),
                )
                .join(
                    Team,
                    and_(
                        Team.id == SchoolTeamPlayerMembership.team_id,
                        Team.organization_id == SchoolTeamPlayerMembership.organization_id,
                    ),
                )
                .join(
                    PlayerProfile,
                    PlayerProfile.player_id == SchoolPlayerMembership.player_profile_id,
                )
                .where(
                    SchoolPlayerMembership.organization_id == organization_id,
                    SchoolPlayerMembership.status == "active",
                    SchoolTeamPlayerMembership.organization_id == organization_id,
                    SchoolTeamPlayerMembership.team_id == plan.team_id,
                    SchoolTeamPlayerMembership.status == "active",
                    Team.status == "active",
                )
                .order_by(PlayerProfile.player_name, SchoolPlayerMembership.id)
            )
        ).all()
    )
    return OrganizationSelectionCandidateResponse(
        organization_id=organization_id,
        team_id=plan.team_id,
        fixture_id=plan.fixture_id,
        candidates=[
            OrganizationSelectionCandidate(
                roster_membership_id=membership.id,
                player_profile_id=membership.player_profile_id,
                player_name=profile.player_name,
                eligible=True,
            )
            for membership, profile in rows
        ],
    )
