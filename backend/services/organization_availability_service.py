"""Tenant-safe player availability for authoritative organization events and fixtures."""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

import structlog
from backend.api.schemas.organization_availability import (
    AvailabilityFilter,
    AvailabilityState,
    AvailabilityTargetType,
    OrganizationAvailabilityCounts,
    OrganizationAvailabilityPlayer,
    OrganizationAvailabilitySummaryResponse,
    OrganizationAvailabilityTargetResponse,
    OrganizationPlayerAvailabilityHistoryEntry,
    OrganizationPlayerAvailabilityHistoryResponse,
    OrganizationPlayerAvailabilityResponse,
)
from backend.services import organization_service
from backend.services.organization_entitlement_service import require_organization_capability
from backend.sql_app.models import (
    Fixture,
    OrganizationAvailabilityTarget,
    OrganizationEvent,
    OrganizationEventRosterPlayer,
    OrganizationEventTeam,
    OrganizationMembership,
    OrganizationPlayerAvailability,
    OrganizationPlayerAvailabilityHistory,
    PlayerProfile,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
    Tournament,
)
from sqlalchemy import Select, and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

ORGANIZATION_AVAILABILITY_CAPABILITY = "organization_availability"
AVAILABILITY_READ_ROLES = frozenset({"owner", "admin", "coach", "scorer", "viewer"})
AVAILABILITY_WRITE_ROLES = frozenset({"owner", "admin", "coach"})


@dataclass(frozen=True)
class OrganizationAvailabilityServiceError(Exception):
    status_code: int
    detail: str


@dataclass(frozen=True)
class AvailabilitySource:
    target_type: AvailabilityTargetType
    target_id: str
    organization_id: str
    title: str
    starts_at: dt.datetime | None
    participant_scope: str | None
    team_ids: tuple[str, ...]
    selected_roster_membership_ids: tuple[str, ...]
    tournament_id: str | None


@dataclass(frozen=True)
class EligiblePlayer:
    membership: SchoolPlayerMembership
    profile: PlayerProfile
    team_ids: tuple[str, ...]


def _not_found(resource: str) -> OrganizationAvailabilityServiceError:
    return OrganizationAvailabilityServiceError(404, f"{resource} not found")


def _forbidden() -> OrganizationAvailabilityServiceError:
    return OrganizationAvailabilityServiceError(403, "Insufficient organization role")


def _invalid(detail: str) -> OrganizationAvailabilityServiceError:
    return OrganizationAvailabilityServiceError(422, detail)


def _conflict(detail: str) -> OrganizationAvailabilityServiceError:
    return OrganizationAvailabilityServiceError(409, detail)


def _utc(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC)


async def _authorize(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    allowed_roles: frozenset[str],
) -> OrganizationMembership:
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability=ORGANIZATION_AVAILABILITY_CAPABILITY,
    )
    _, membership = await organization_service.get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if membership.role not in allowed_roles:
        logger.warning(
            "organization.availability_role_denied",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            membership_role=membership.role,
        )
        raise _forbidden()
    return membership


async def _event_source(
    db: AsyncSession,
    *,
    organization_id: str,
    event_id: str,
    lock: bool,
) -> AvailabilitySource:
    statement = select(OrganizationEvent).where(
        OrganizationEvent.id == event_id,
        OrganizationEvent.organization_id == organization_id,
    )
    if lock:
        statement = statement.with_for_update()
    event = await db.scalar(statement)
    if event is None:
        raise _not_found("Event")

    team_ids = tuple(
        (
            await db.scalars(
                select(OrganizationEventTeam.team_id)
                .where(
                    OrganizationEventTeam.event_id == event.id,
                    OrganizationEventTeam.organization_id == organization_id,
                )
                .order_by(OrganizationEventTeam.team_id)
            )
        ).all()
    )
    player_ids = tuple(
        (
            await db.scalars(
                select(OrganizationEventRosterPlayer.school_player_membership_id)
                .where(
                    OrganizationEventRosterPlayer.event_id == event.id,
                    OrganizationEventRosterPlayer.organization_id == organization_id,
                )
                .order_by(OrganizationEventRosterPlayer.school_player_membership_id)
            )
        ).all()
    )
    return AvailabilitySource(
        target_type="event",
        target_id=event.id,
        organization_id=organization_id,
        title=event.title,
        starts_at=_utc(event.start_at),
        participant_scope=event.participant_scope,
        team_ids=team_ids,
        selected_roster_membership_ids=player_ids,
        tournament_id=None,
    )


async def _fixture_source(
    db: AsyncSession,
    *,
    organization_id: str,
    fixture_id: str,
    lock: bool,
) -> AvailabilitySource:
    statement = (
        select(Fixture)
        .join(Tournament, Tournament.id == Fixture.tournament_id)
        .where(
            Fixture.id == fixture_id,
            Tournament.organization_id == organization_id,
        )
    )
    if lock:
        statement = statement.with_for_update()
    fixture = await db.scalar(statement)
    if fixture is None:
        raise _not_found("Fixture")
    if fixture.team_a_id is None or fixture.team_b_id is None:
        raise _invalid("Fixture availability requires two normalized organization Teams")

    team_ids = (fixture.team_a_id, fixture.team_b_id)
    teams = set(
        (
            await db.scalars(
                select(Team.id).where(
                    Team.organization_id == organization_id,
                    Team.status == "active",
                    Team.id.in_(team_ids),
                )
            )
        ).all()
    )
    if teams != set(team_ids):
        raise _invalid("Fixture availability requires active normalized organization Teams")
    return AvailabilitySource(
        target_type="fixture",
        target_id=fixture.id,
        organization_id=organization_id,
        title=f"{fixture.team_a_name} vs {fixture.team_b_name}",
        starts_at=_utc(fixture.scheduled_date),
        participant_scope=None,
        team_ids=team_ids,
        selected_roster_membership_ids=(),
        tournament_id=fixture.tournament_id,
    )


async def _source(
    db: AsyncSession,
    *,
    organization_id: str,
    target_type: AvailabilityTargetType,
    target_id: str,
    lock: bool = False,
) -> AvailabilitySource:
    if target_type == "event":
        return await _event_source(
            db,
            organization_id=organization_id,
            event_id=target_id,
            lock=lock,
        )
    return await _fixture_source(
        db,
        organization_id=organization_id,
        fixture_id=target_id,
        lock=lock,
    )


def _target_predicates(source: AvailabilitySource) -> tuple[object, ...]:
    if source.target_type == "event":
        return (
            OrganizationAvailabilityTarget.organization_id == source.organization_id,
            OrganizationAvailabilityTarget.target_type == "event",
            OrganizationAvailabilityTarget.organization_event_id == source.target_id,
        )
    return (
        OrganizationAvailabilityTarget.organization_id == source.organization_id,
        OrganizationAvailabilityTarget.target_type == "fixture",
        OrganizationAvailabilityTarget.fixture_id == source.target_id,
    )


async def _target(
    db: AsyncSession,
    *,
    source: AvailabilitySource,
    lock: bool = False,
) -> OrganizationAvailabilityTarget | None:
    statement = select(OrganizationAvailabilityTarget).where(*_target_predicates(source))
    if lock:
        statement = statement.with_for_update()
    return await db.scalar(statement)


async def _ensure_target(
    db: AsyncSession,
    *,
    source: AvailabilitySource,
    actor_user_id: str,
) -> OrganizationAvailabilityTarget:
    target = await _target(db, source=source, lock=True)
    if target is not None:
        return target
    target = OrganizationAvailabilityTarget(
        id=str(uuid.uuid4()),
        organization_id=source.organization_id,
        target_type=source.target_type,
        organization_event_id=source.target_id if source.target_type == "event" else None,
        fixture_id=source.target_id if source.target_type == "fixture" else None,
        fixture_tournament_id=source.tournament_id,
        response_deadline=None,
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
    )
    db.add(target)
    await db.flush()
    return target


def _active_team_membership_ids(
    *, organization_id: str, team_ids: tuple[str, ...]
) -> Select[tuple[str]]:
    return (
        select(SchoolTeamPlayerMembership.school_player_membership_id)
        .join(
            Team,
            and_(
                Team.id == SchoolTeamPlayerMembership.team_id,
                Team.organization_id == SchoolTeamPlayerMembership.organization_id,
            ),
        )
        .where(
            SchoolTeamPlayerMembership.organization_id == organization_id,
            SchoolTeamPlayerMembership.status == "active",
            Team.status == "active",
            SchoolTeamPlayerMembership.team_id.in_(team_ids),
        )
    )


async def _eligible_players(
    db: AsyncSession,
    *,
    source: AvailabilitySource,
    team_id: str | None,
) -> list[EligiblePlayer]:
    if team_id is not None:
        team = await db.scalar(
            select(Team).where(
                Team.id == team_id,
                Team.organization_id == source.organization_id,
            )
        )
        if team is None:
            raise _not_found("Team")
        if team.status != "active":
            raise _invalid("Availability overview requires an active Team")
        if source.team_ids and team_id not in source.team_ids:
            raise _invalid("Team is not represented by this availability target")

    statement = (
        select(SchoolPlayerMembership, PlayerProfile)
        .join(
            PlayerProfile,
            PlayerProfile.player_id == SchoolPlayerMembership.player_profile_id,
        )
        .where(
            SchoolPlayerMembership.organization_id == source.organization_id,
            SchoolPlayerMembership.status == "active",
        )
    )
    if source.participant_scope == "selected_players":
        statement = statement.where(
            SchoolPlayerMembership.id.in_(source.selected_roster_membership_ids)
        )
    elif source.participant_scope == "teams" or source.target_type == "fixture":
        statement = statement.where(
            SchoolPlayerMembership.id.in_(
                _active_team_membership_ids(
                    organization_id=source.organization_id,
                    team_ids=source.team_ids,
                )
            )
        )
    if team_id is not None:
        statement = statement.where(
            SchoolPlayerMembership.id.in_(
                _active_team_membership_ids(
                    organization_id=source.organization_id,
                    team_ids=(team_id,),
                )
            )
        )
    statement = statement.order_by(PlayerProfile.player_name, SchoolPlayerMembership.id)
    rows = list((await db.execute(statement)).tuples())
    membership_ids = [membership.id for membership, _ in rows]
    team_map: dict[str, list[str]] = {membership_id: [] for membership_id in membership_ids}
    if membership_ids:
        team_statement = (
            select(
                SchoolTeamPlayerMembership.school_player_membership_id,
                SchoolTeamPlayerMembership.team_id,
            )
            .join(
                Team,
                and_(
                    Team.id == SchoolTeamPlayerMembership.team_id,
                    Team.organization_id == SchoolTeamPlayerMembership.organization_id,
                ),
            )
            .where(
                SchoolTeamPlayerMembership.organization_id == source.organization_id,
                SchoolTeamPlayerMembership.status == "active",
                Team.status == "active",
                SchoolTeamPlayerMembership.school_player_membership_id.in_(membership_ids),
            )
            .order_by(
                SchoolTeamPlayerMembership.school_player_membership_id,
                SchoolTeamPlayerMembership.team_id,
            )
        )
        if source.team_ids:
            team_statement = team_statement.where(
                SchoolTeamPlayerMembership.team_id.in_(source.team_ids)
            )
        for membership_id, current_team_id in (await db.execute(team_statement)).tuples():
            team_map[membership_id].append(current_team_id)

    return [
        EligiblePlayer(membership, profile, tuple(team_map[membership.id]))
        for membership, profile in rows
    ]


def _deadline_passed(deadline: dt.datetime | None) -> bool:
    normalized = _utc(deadline)
    return normalized is not None and dt.datetime.now(dt.UTC) > normalized


def _target_response(
    source: AvailabilitySource,
    target: OrganizationAvailabilityTarget | None,
) -> OrganizationAvailabilityTargetResponse:
    deadline = _utc(target.response_deadline) if target is not None else None
    return OrganizationAvailabilityTargetResponse(
        target_type=source.target_type,
        target_id=source.target_id,
        title=source.title,
        starts_at=source.starts_at,
        response_deadline=deadline,
        deadline_passed=_deadline_passed(deadline),
    )


async def availability_summary(
    db: AsyncSession,
    *,
    organization_id: str,
    target_type: AvailabilityTargetType,
    target_id: str,
    actor_user_id: str,
    state_filter: AvailabilityFilter | None,
    team_id: str | None,
    limit: int,
    offset: int,
) -> OrganizationAvailabilitySummaryResponse:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=AVAILABILITY_READ_ROLES,
    )
    source = await _source(
        db,
        organization_id=organization_id,
        target_type=target_type,
        target_id=target_id,
    )
    target = await _target(db, source=source)
    eligible = await _eligible_players(db, source=source, team_id=team_id)
    current_by_player: dict[str, OrganizationPlayerAvailability] = {}
    if target is not None and eligible:
        current_rows = await db.scalars(
            select(OrganizationPlayerAvailability).where(
                OrganizationPlayerAvailability.organization_id == organization_id,
                OrganizationPlayerAvailability.target_id == target.id,
                OrganizationPlayerAvailability.school_player_membership_id.in_(
                    [record.membership.id for record in eligible]
                ),
            )
        )
        current_by_player = {row.school_player_membership_id: row for row in current_rows.all()}

    counts = {"available": 0, "unavailable": 0, "maybe": 0, "no_response": 0}
    players: list[OrganizationAvailabilityPlayer] = []
    for record in eligible:
        current = current_by_player.get(record.membership.id)
        current_state = current.state if current is not None else "no_response"
        counts[current_state] += 1
        if state_filter is not None and current_state != state_filter:
            continue
        players.append(
            OrganizationAvailabilityPlayer(
                roster_membership_id=record.membership.id,
                player_profile_id=record.profile.player_id,
                player_name=record.profile.player_name,
                team_ids=list(record.team_ids),
                state=current.state if current is not None else None,
                recorded_by_user_id=(current.recorded_by_user_id if current is not None else None),
                recorded_at=_utc(current.recorded_at) if current is not None else None,
                recorded_after_deadline=(
                    current.recorded_after_deadline if current is not None else False
                ),
            )
        )
    return OrganizationAvailabilitySummaryResponse(
        target=_target_response(source, target),
        counts=OrganizationAvailabilityCounts(
            available=counts["available"],
            unavailable=counts["unavailable"],
            maybe=counts["maybe"],
            no_response=counts["no_response"],
            total=len(eligible),
        ),
        players=players[offset : offset + limit],
        total=len(players),
        limit=limit,
        offset=offset,
    )


async def update_target_deadline(
    db: AsyncSession,
    *,
    organization_id: str,
    target_type: AvailabilityTargetType,
    target_id: str,
    actor_user_id: str,
    response_deadline: dt.datetime | None,
) -> OrganizationAvailabilityTargetResponse:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=AVAILABILITY_WRITE_ROLES,
    )
    source = await _source(
        db,
        organization_id=organization_id,
        target_type=target_type,
        target_id=target_id,
        lock=True,
    )
    target = await _ensure_target(db, source=source, actor_user_id=actor_user_id)
    target.response_deadline = response_deadline
    target.updated_by_user_id = actor_user_id
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _conflict("Availability target was updated concurrently") from exc
    await db.refresh(target)
    return _target_response(source, target)


async def record_player_availability(
    db: AsyncSession,
    *,
    organization_id: str,
    target_type: AvailabilityTargetType,
    target_id: str,
    roster_membership_id: str,
    actor_user_id: str,
    state: AvailabilityState,
) -> OrganizationPlayerAvailabilityResponse:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=AVAILABILITY_WRITE_ROLES,
    )
    source = await _source(
        db,
        organization_id=organization_id,
        target_type=target_type,
        target_id=target_id,
        lock=True,
    )
    roster_player = await db.scalar(
        select(SchoolPlayerMembership).where(
            SchoolPlayerMembership.id == roster_membership_id,
            SchoolPlayerMembership.organization_id == organization_id,
        )
    )
    if roster_player is None:
        raise _not_found("Roster player")
    if roster_player.status != "active":
        raise _invalid("Inactive roster players cannot receive new availability responses")
    eligible = await _eligible_players(db, source=source, team_id=None)
    if roster_membership_id not in {record.membership.id for record in eligible}:
        raise _invalid("Roster player is not eligible for this availability target")

    target = await _ensure_target(db, source=source, actor_user_id=actor_user_id)
    current = await db.scalar(
        select(OrganizationPlayerAvailability)
        .where(
            OrganizationPlayerAvailability.organization_id == organization_id,
            OrganizationPlayerAvailability.target_id == target.id,
            OrganizationPlayerAvailability.school_player_membership_id == roster_membership_id,
        )
        .with_for_update()
    )
    if current is not None and current.state == state:
        await db.commit()
        return OrganizationPlayerAvailabilityResponse(
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
            roster_membership_id=roster_membership_id,
            player_profile_id=roster_player.player_profile_id,
            state=state,
            recorded_by_user_id=current.recorded_by_user_id,
            recorded_at=_utc(current.recorded_at),
            recorded_after_deadline=current.recorded_after_deadline,
        )

    recorded_at = dt.datetime.now(dt.UTC)
    deadline = _utc(target.response_deadline)
    after_deadline = deadline is not None and recorded_at > deadline
    if current is None:
        current = OrganizationPlayerAvailability(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            target_id=target.id,
            school_player_membership_id=roster_membership_id,
            state=state,
            recorded_by_user_id=actor_user_id,
            recorded_at=recorded_at,
            recorded_after_deadline=after_deadline,
        )
        db.add(current)
    else:
        current.state = state
        current.recorded_by_user_id = actor_user_id
        current.recorded_at = recorded_at
        current.recorded_after_deadline = after_deadline
    db.add(
        OrganizationPlayerAvailabilityHistory(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            target_id=target.id,
            school_player_membership_id=roster_membership_id,
            state=state,
            recorded_by_user_id=actor_user_id,
            recorded_at=recorded_at,
            recorded_after_deadline=after_deadline,
        )
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning(
            "organization.availability_concurrent_conflict",
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
            roster_membership_id=roster_membership_id,
        )
        raise _conflict("Availability response was updated concurrently; retry safely") from exc
    await db.refresh(current)
    return OrganizationPlayerAvailabilityResponse(
        organization_id=organization_id,
        target_type=target_type,
        target_id=target_id,
        roster_membership_id=roster_membership_id,
        player_profile_id=roster_player.player_profile_id,
        state=state,
        recorded_by_user_id=current.recorded_by_user_id,
        recorded_at=_utc(current.recorded_at),
        recorded_after_deadline=current.recorded_after_deadline,
    )


async def player_availability_history(
    db: AsyncSession,
    *,
    organization_id: str,
    target_type: AvailabilityTargetType,
    target_id: str,
    roster_membership_id: str,
    actor_user_id: str,
) -> OrganizationPlayerAvailabilityHistoryResponse:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=AVAILABILITY_READ_ROLES,
    )
    source = await _source(
        db,
        organization_id=organization_id,
        target_type=target_type,
        target_id=target_id,
    )
    roster_player = await db.scalar(
        select(SchoolPlayerMembership).where(
            SchoolPlayerMembership.id == roster_membership_id,
            SchoolPlayerMembership.organization_id == organization_id,
        )
    )
    if roster_player is None:
        raise _not_found("Roster player")
    target = await _target(db, source=source)
    history: list[OrganizationPlayerAvailabilityHistory] = []
    if target is not None:
        history = list(
            (
                await db.scalars(
                    select(OrganizationPlayerAvailabilityHistory)
                    .where(
                        OrganizationPlayerAvailabilityHistory.organization_id == organization_id,
                        OrganizationPlayerAvailabilityHistory.target_id == target.id,
                        OrganizationPlayerAvailabilityHistory.school_player_membership_id
                        == roster_membership_id,
                    )
                    .order_by(
                        OrganizationPlayerAvailabilityHistory.recorded_at,
                        OrganizationPlayerAvailabilityHistory.id,
                    )
                )
            ).all()
        )
    return OrganizationPlayerAvailabilityHistoryResponse(
        organization_id=organization_id,
        target_type=target_type,
        target_id=target_id,
        roster_membership_id=roster_membership_id,
        player_profile_id=roster_player.player_profile_id,
        items=[
            OrganizationPlayerAvailabilityHistoryEntry(
                id=item.id,
                state=item.state,
                recorded_by_user_id=item.recorded_by_user_id,
                recorded_at=_utc(item.recorded_at),
                recorded_after_deadline=item.recorded_after_deadline,
            )
            for item in history
        ],
    )
