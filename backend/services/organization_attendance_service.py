"""Tenant-safe, auditable attendance for organization-owned events."""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

import structlog
from backend.api.schemas.organization_attendance import (
    AttendanceFilter,
    AttendanceState,
    OrganizationAttendanceCounts,
    OrganizationAttendancePlayer,
    OrganizationAttendanceRegisterResponse,
    OrganizationAttendanceSummaryResponse,
    OrganizationPlayerAttendanceHistoryEntry,
    OrganizationPlayerAttendanceHistoryResponse,
    OrganizationPlayerAttendanceResponse,
)
from backend.services import organization_service
from backend.services.organization_entitlement_service import require_organization_capability
from backend.sql_app.models import (
    OrganizationEvent,
    OrganizationEventRosterPlayer,
    OrganizationEventTeam,
    OrganizationMembership,
    OrganizationPlayerAttendance,
    OrganizationPlayerAttendanceHistory,
    PlayerProfile,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
)
from sqlalchemy import Select, and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

ORGANIZATION_ATTENDANCE_CAPABILITY = "organization_attendance"
ATTENDANCE_ROLES = frozenset({"owner", "admin", "coach"})


@dataclass(frozen=True)
class OrganizationAttendanceServiceError(Exception):
    status_code: int
    detail: str


@dataclass(frozen=True)
class EligiblePlayer:
    membership: SchoolPlayerMembership
    profile: PlayerProfile
    team_ids: tuple[str, ...]


def _not_found(resource: str) -> OrganizationAttendanceServiceError:
    return OrganizationAttendanceServiceError(404, f"{resource} not found")


def _forbidden() -> OrganizationAttendanceServiceError:
    return OrganizationAttendanceServiceError(403, "Insufficient organization role")


def _invalid(detail: str) -> OrganizationAttendanceServiceError:
    return OrganizationAttendanceServiceError(422, detail)


def _conflict(detail: str) -> OrganizationAttendanceServiceError:
    return OrganizationAttendanceServiceError(409, detail)


def _utc(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC)


def _validated_boundary(value: dt.datetime | None, field: str) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise _invalid(f"{field} must include a timezone offset")
    return value.astimezone(dt.UTC)


async def _authorize(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
) -> OrganizationMembership:
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability=ORGANIZATION_ATTENDANCE_CAPABILITY,
    )
    _, membership = await organization_service.get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if membership.role not in ATTENDANCE_ROLES:
        logger.warning(
            "organization.attendance_role_denied",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            membership_role=membership.role,
        )
        raise _forbidden()
    return membership


async def _event(
    db: AsyncSession,
    *,
    organization_id: str,
    event_id: str,
    lock: bool = False,
) -> OrganizationEvent:
    statement = select(OrganizationEvent).where(
        OrganizationEvent.id == event_id,
        OrganizationEvent.organization_id == organization_id,
    )
    if lock:
        statement = statement.with_for_update()
    event = await db.scalar(statement)
    if event is None:
        raise _not_found("Event")
    return event


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


async def _event_audience(
    db: AsyncSession,
    *,
    event: OrganizationEvent,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    team_ids = tuple(
        (
            await db.scalars(
                select(OrganizationEventTeam.team_id)
                .where(
                    OrganizationEventTeam.event_id == event.id,
                    OrganizationEventTeam.organization_id == event.organization_id,
                )
                .order_by(OrganizationEventTeam.team_id)
            )
        ).all()
    )
    selected_ids = tuple(
        (
            await db.scalars(
                select(OrganizationEventRosterPlayer.school_player_membership_id)
                .where(
                    OrganizationEventRosterPlayer.event_id == event.id,
                    OrganizationEventRosterPlayer.organization_id == event.organization_id,
                )
                .order_by(OrganizationEventRosterPlayer.school_player_membership_id)
            )
        ).all()
    )
    return team_ids, selected_ids


async def _eligible_players(
    db: AsyncSession,
    *,
    event: OrganizationEvent,
    team_id: str | None,
) -> list[EligiblePlayer]:
    team_ids, selected_ids = await _event_audience(db, event=event)
    if team_id is not None:
        team = await db.scalar(
            select(Team).where(
                Team.id == team_id,
                Team.organization_id == event.organization_id,
            )
        )
        if team is None:
            raise _not_found("Team")
        if team.status != "active":
            raise _invalid("Attendance register requires an active Team")
        if event.participant_scope == "teams" and team_id not in team_ids:
            raise _invalid("Team is not represented by this event")

    statement = (
        select(SchoolPlayerMembership, PlayerProfile)
        .join(
            PlayerProfile,
            PlayerProfile.player_id == SchoolPlayerMembership.player_profile_id,
        )
        .where(
            SchoolPlayerMembership.organization_id == event.organization_id,
            SchoolPlayerMembership.status == "active",
        )
    )
    if event.participant_scope == "selected_players":
        statement = statement.where(SchoolPlayerMembership.id.in_(selected_ids))
    elif event.participant_scope == "teams":
        statement = statement.where(
            SchoolPlayerMembership.id.in_(
                _active_team_membership_ids(
                    organization_id=event.organization_id,
                    team_ids=team_ids,
                )
            )
        )
    if team_id is not None:
        statement = statement.where(
            SchoolPlayerMembership.id.in_(
                _active_team_membership_ids(
                    organization_id=event.organization_id,
                    team_ids=(team_id,),
                )
            )
        )
    rows = list(
        (
            await db.execute(
                statement.order_by(PlayerProfile.player_name, SchoolPlayerMembership.id)
            )
        ).tuples()
    )
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
                SchoolTeamPlayerMembership.organization_id == event.organization_id,
                SchoolTeamPlayerMembership.status == "active",
                Team.status == "active",
                SchoolTeamPlayerMembership.school_player_membership_id.in_(membership_ids),
            )
            .order_by(
                SchoolTeamPlayerMembership.school_player_membership_id,
                SchoolTeamPlayerMembership.team_id,
            )
        )
        for membership_id, current_team_id in (await db.execute(team_statement)).tuples():
            team_map[membership_id].append(current_team_id)
    return [
        EligiblePlayer(membership, profile, tuple(team_map[membership.id]))
        for membership, profile in rows
    ]


def _counts(states: list[str | None]) -> OrganizationAttendanceCounts:
    present = states.count("present")
    absent = states.count("absent")
    excused = states.count("excused")
    unmarked = states.count(None)
    denominator = present + absent
    percentage = round(present / denominator * 100, 2) if denominator else None
    return OrganizationAttendanceCounts(
        present=present,
        absent=absent,
        excused=excused,
        unmarked=unmarked,
        total=len(states),
        attendance_percentage=percentage,
    )


async def attendance_register(
    db: AsyncSession,
    *,
    organization_id: str,
    event_id: str,
    actor_user_id: str,
    state_filter: AttendanceFilter | None,
    team_id: str | None,
    limit: int,
    offset: int,
) -> OrganizationAttendanceRegisterResponse:
    await _authorize(db, organization_id=organization_id, actor_user_id=actor_user_id)
    event = await _event(db, organization_id=organization_id, event_id=event_id)
    eligible = await _eligible_players(db, event=event, team_id=team_id)
    eligible_by_id = {record.membership.id: record for record in eligible}
    current_rows = list(
        (
            await db.scalars(
                select(OrganizationPlayerAttendance).where(
                    OrganizationPlayerAttendance.organization_id == organization_id,
                    OrganizationPlayerAttendance.organization_event_id == event_id,
                )
            )
        ).all()
    )
    current_by_id = {row.school_player_membership_id: row for row in current_rows}

    # Retained records remain readable even when a roster or Team membership later becomes inactive.
    missing_ids = set(current_by_id) - set(eligible_by_id)
    retained: dict[str, EligiblePlayer] = {}
    if missing_ids and team_id is None:
        rows = list(
            (
                await db.execute(
                    select(SchoolPlayerMembership, PlayerProfile)
                    .join(
                        PlayerProfile,
                        PlayerProfile.player_id == SchoolPlayerMembership.player_profile_id,
                    )
                    .where(
                        SchoolPlayerMembership.organization_id == organization_id,
                        SchoolPlayerMembership.id.in_(missing_ids),
                    )
                )
            ).tuples()
        )
        retained = {
            membership.id: EligiblePlayer(membership, profile, ()) for membership, profile in rows
        }

    records = list(eligible_by_id.values()) + list(retained.values())
    records.sort(key=lambda record: (record.profile.player_name, record.membership.id))
    all_states = [
        current_by_id[record.membership.id].state if record.membership.id in current_by_id else None
        for record in records
    ]
    players: list[OrganizationAttendancePlayer] = []
    for record in records:
        current = current_by_id.get(record.membership.id)
        effective = current.state if current is not None else "unmarked"
        if state_filter is not None and effective != state_filter:
            continue
        players.append(
            OrganizationAttendancePlayer(
                roster_membership_id=record.membership.id,
                player_profile_id=record.profile.player_id,
                player_name=record.profile.player_name,
                team_ids=list(record.team_ids),
                eligible=record.membership.id in eligible_by_id,
                state=current.state if current is not None else None,
                recorded_by_user_id=current.recorded_by_user_id if current is not None else None,
                recorded_at=_utc(current.recorded_at) if current is not None else None,
            )
        )
    return OrganizationAttendanceRegisterResponse(
        organization_id=organization_id,
        event_id=event.id,
        event_title=event.title,
        event_status=event.status,
        start_at=_utc(event.start_at),  # type: ignore[arg-type]
        counts=_counts(all_states),
        players=players[offset : offset + limit],
        total=len(players),
        limit=limit,
        offset=offset,
    )


async def record_player_attendance(
    db: AsyncSession,
    *,
    organization_id: str,
    event_id: str,
    roster_membership_id: str,
    actor_user_id: str,
    state: AttendanceState,
) -> OrganizationPlayerAttendanceResponse:
    await _authorize(db, organization_id=organization_id, actor_user_id=actor_user_id)
    # The authoritative event row serializes first write, correction, cancellation and deletion.
    event = await _event(
        db,
        organization_id=organization_id,
        event_id=event_id,
        lock=True,
    )
    if event.status == "cancelled":
        raise _conflict("Cancelled events cannot receive attendance changes")
    starts_at = _utc(event.start_at)
    if starts_at is not None and dt.datetime.now(dt.UTC) < starts_at:
        raise _conflict("Attendance cannot be recorded before the event starts")
    roster_player = await db.scalar(
        select(SchoolPlayerMembership).where(
            SchoolPlayerMembership.id == roster_membership_id,
            SchoolPlayerMembership.organization_id == organization_id,
        )
    )
    if roster_player is None:
        raise _not_found("Roster player")
    if roster_player.status != "active":
        raise _invalid("Inactive roster players cannot receive attendance changes")
    eligible_ids = {
        record.membership.id for record in await _eligible_players(db, event=event, team_id=None)
    }
    if roster_membership_id not in eligible_ids:
        raise _invalid("Roster player is not eligible for this event")

    current = await db.scalar(
        select(OrganizationPlayerAttendance)
        .where(
            OrganizationPlayerAttendance.organization_id == organization_id,
            OrganizationPlayerAttendance.organization_event_id == event_id,
            OrganizationPlayerAttendance.school_player_membership_id == roster_membership_id,
        )
        .with_for_update()
    )
    if current is not None and current.state == state:
        await db.commit()
        return OrganizationPlayerAttendanceResponse(
            organization_id=organization_id,
            event_id=event_id,
            roster_membership_id=roster_membership_id,
            player_profile_id=roster_player.player_profile_id,
            state=state,
            recorded_by_user_id=current.recorded_by_user_id,
            recorded_at=_utc(current.recorded_at),  # type: ignore[arg-type]
        )

    recorded_at = dt.datetime.now(dt.UTC)
    if current is None:
        current = OrganizationPlayerAttendance(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            organization_event_id=event_id,
            school_player_membership_id=roster_membership_id,
            state=state,
            recorded_by_user_id=actor_user_id,
            recorded_at=recorded_at,
        )
        db.add(current)
    else:
        current.state = state
        current.recorded_by_user_id = actor_user_id
        current.recorded_at = recorded_at
    db.add(
        OrganizationPlayerAttendanceHistory(
            id=str(uuid.uuid4()),
            organization_id=organization_id,
            organization_event_id=event_id,
            school_player_membership_id=roster_membership_id,
            state=state,
            recorded_by_user_id=actor_user_id,
            recorded_at=recorded_at,
        )
    )
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        logger.warning(
            "organization.attendance_concurrent_conflict",
            organization_id=organization_id,
            event_id=event_id,
            roster_membership_id=roster_membership_id,
        )
        raise _conflict("Attendance was updated concurrently; retry safely") from exc
    await db.refresh(current)
    return OrganizationPlayerAttendanceResponse(
        organization_id=organization_id,
        event_id=event_id,
        roster_membership_id=roster_membership_id,
        player_profile_id=roster_player.player_profile_id,
        state=state,
        recorded_by_user_id=current.recorded_by_user_id,
        recorded_at=_utc(current.recorded_at),  # type: ignore[arg-type]
    )


async def player_attendance_history(
    db: AsyncSession,
    *,
    organization_id: str,
    event_id: str,
    roster_membership_id: str,
    actor_user_id: str,
) -> OrganizationPlayerAttendanceHistoryResponse:
    await _authorize(db, organization_id=organization_id, actor_user_id=actor_user_id)
    await _event(db, organization_id=organization_id, event_id=event_id)
    roster_player = await db.scalar(
        select(SchoolPlayerMembership).where(
            SchoolPlayerMembership.id == roster_membership_id,
            SchoolPlayerMembership.organization_id == organization_id,
        )
    )
    if roster_player is None:
        raise _not_found("Roster player")
    history = list(
        (
            await db.scalars(
                select(OrganizationPlayerAttendanceHistory)
                .where(
                    OrganizationPlayerAttendanceHistory.organization_id == organization_id,
                    OrganizationPlayerAttendanceHistory.organization_event_id == event_id,
                    OrganizationPlayerAttendanceHistory.school_player_membership_id
                    == roster_membership_id,
                )
                .order_by(
                    OrganizationPlayerAttendanceHistory.recorded_at,
                    OrganizationPlayerAttendanceHistory.id,
                )
            )
        ).all()
    )
    return OrganizationPlayerAttendanceHistoryResponse(
        organization_id=organization_id,
        event_id=event_id,
        roster_membership_id=roster_membership_id,
        player_profile_id=roster_player.player_profile_id,
        items=[
            OrganizationPlayerAttendanceHistoryEntry(
                id=item.id,
                state=item.state,
                recorded_by_user_id=item.recorded_by_user_id,
                recorded_at=_utc(item.recorded_at),  # type: ignore[arg-type]
            )
            for item in history
        ],
    )


async def attendance_summary(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    from_at: dt.datetime | None,
    to_at: dt.datetime | None,
    team_id: str | None,
    roster_membership_id: str | None,
) -> OrganizationAttendanceSummaryResponse:
    await _authorize(db, organization_id=organization_id, actor_user_id=actor_user_id)
    from_at = _validated_boundary(from_at, "from_at")
    to_at = _validated_boundary(to_at, "to_at")
    if from_at is not None and to_at is not None and to_at <= from_at:
        raise _invalid("to_at must be later than from_at")
    if team_id is not None and roster_membership_id is not None:
        raise _invalid("Choose either team_id or roster_membership_id")
    if team_id is not None:
        team = await db.scalar(
            select(Team).where(Team.id == team_id, Team.organization_id == organization_id)
        )
        if team is None:
            raise _not_found("Team")
    if roster_membership_id is not None:
        roster_player = await db.scalar(
            select(SchoolPlayerMembership).where(
                SchoolPlayerMembership.id == roster_membership_id,
                SchoolPlayerMembership.organization_id == organization_id,
            )
        )
        if roster_player is None:
            raise _not_found("Roster player")

    filters: list[object] = [
        OrganizationEvent.organization_id == organization_id,
        OrganizationEvent.start_at <= dt.datetime.now(dt.UTC),
    ]
    if from_at is not None:
        filters.append(OrganizationEvent.start_at >= from_at)
    if to_at is not None:
        filters.append(OrganizationEvent.start_at < to_at)
    events = list(
        (
            await db.scalars(
                select(OrganizationEvent)
                .where(*filters)
                .order_by(OrganizationEvent.start_at, OrganizationEvent.id)
            )
        ).all()
    )
    states: list[str | None] = []
    represented_events = 0
    for event in events:
        try:
            eligible = await _eligible_players(db, event=event, team_id=team_id)
        except OrganizationAttendanceServiceError as exc:
            if team_id is not None and exc.status_code == 422:
                continue
            raise
        eligible_ids = {record.membership.id for record in eligible}
        current_rows = list(
            (
                await db.scalars(
                    select(OrganizationPlayerAttendance).where(
                        OrganizationPlayerAttendance.organization_id == organization_id,
                        OrganizationPlayerAttendance.organization_event_id == event.id,
                    )
                )
            ).all()
        )
        current_by_id = {row.school_player_membership_id: row for row in current_rows}
        if roster_membership_id is not None:
            if (
                roster_membership_id not in eligible_ids
                and roster_membership_id not in current_by_id
            ):
                continue
            if event.status == "cancelled" and roster_membership_id not in current_by_id:
                continue
            states.append(
                current_by_id[roster_membership_id].state
                if roster_membership_id in current_by_id
                else None
            )
        else:
            included_ids = eligible_ids | (set(current_by_id) if team_id is None else set())
            if event.status == "cancelled" and not set(current_by_id).intersection(included_ids):
                continue
            states.extend(
                current_by_id[membership_id].state if membership_id in current_by_id else None
                for membership_id in included_ids
            )
        represented_events += 1
    return OrganizationAttendanceSummaryResponse(
        organization_id=organization_id,
        from_at=from_at,
        to_at=to_at,
        team_id=team_id,
        roster_membership_id=roster_membership_id,
        counts=_counts(states),
        event_count=represented_events,
    )
