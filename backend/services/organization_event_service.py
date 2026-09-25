"""Shared, tenant-safe organization event persistence and calendar composition."""

from __future__ import annotations

import datetime as dt
import uuid
from dataclasses import dataclass

import structlog
from backend.api.schemas.organization_events import (
    OrganizationCalendarItem,
    OrganizationEventCreate,
    OrganizationEventUpdate,
)
from backend.services import organization_service
from backend.services.organization_entitlement_service import require_organization_capability
from backend.sql_app.models import (
    Fixture,
    OrganizationEvent,
    OrganizationEventRosterPlayer,
    OrganizationEventTeam,
    OrganizationMembership,
    SchoolPlayerMembership,
    Team,
    Tournament,
)
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

ORGANIZATION_EVENT_CAPABILITY = "organization_events"
EVENT_READ_ROLES = frozenset({"owner", "admin", "coach", "scorer", "viewer"})
EVENT_WRITE_ROLES = frozenset({"owner", "admin", "coach"})


@dataclass(frozen=True)
class OrganizationEventServiceError(Exception):
    status_code: int
    detail: str


@dataclass(frozen=True)
class OrganizationEventRecord:
    event: OrganizationEvent
    team_ids: list[str]
    roster_membership_ids: list[str]


def _not_found(resource: str = "Event") -> OrganizationEventServiceError:
    return OrganizationEventServiceError(404, f"{resource} not found")


def _forbidden() -> OrganizationEventServiceError:
    return OrganizationEventServiceError(403, "Insufficient organization role")


def _invalid(detail: str) -> OrganizationEventServiceError:
    return OrganizationEventServiceError(422, detail)


def _utc(value: dt.datetime) -> dt.datetime:
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
    allowed_roles: frozenset[str],
) -> OrganizationMembership:
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        capability=ORGANIZATION_EVENT_CAPABILITY,
    )
    _, membership = await organization_service.get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if membership.role not in allowed_roles:
        logger.warning(
            "organization.event_role_denied",
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
) -> OrganizationEvent:
    event = await db.scalar(
        select(OrganizationEvent).where(
            OrganizationEvent.id == event_id,
            OrganizationEvent.organization_id == organization_id,
        )
    )
    if event is None:
        raise _not_found()
    return event


async def _audiences(
    db: AsyncSession,
    event_ids: list[str],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    team_map: dict[str, list[str]] = {event_id: [] for event_id in event_ids}
    player_map: dict[str, list[str]] = {event_id: [] for event_id in event_ids}
    if not event_ids:
        return team_map, player_map

    team_rows = await db.execute(
        select(OrganizationEventTeam.event_id, OrganizationEventTeam.team_id)
        .where(OrganizationEventTeam.event_id.in_(event_ids))
        .order_by(OrganizationEventTeam.event_id, OrganizationEventTeam.team_id)
    )
    for event_id, team_id in team_rows.tuples():
        team_map[event_id].append(team_id)

    player_rows = await db.execute(
        select(
            OrganizationEventRosterPlayer.event_id,
            OrganizationEventRosterPlayer.school_player_membership_id,
        )
        .where(OrganizationEventRosterPlayer.event_id.in_(event_ids))
        .order_by(
            OrganizationEventRosterPlayer.event_id,
            OrganizationEventRosterPlayer.school_player_membership_id,
        )
    )
    for event_id, roster_membership_id in player_rows.tuples():
        player_map[event_id].append(roster_membership_id)
    return team_map, player_map


async def _records(
    db: AsyncSession,
    events: list[OrganizationEvent],
) -> list[OrganizationEventRecord]:
    event_ids = [event.id for event in events]
    team_map, player_map = await _audiences(db, event_ids)
    return [
        OrganizationEventRecord(
            event=event,
            team_ids=team_map[event.id],
            roster_membership_ids=player_map[event.id],
        )
        for event in events
    ]


def _event_filters(
    *,
    organization_id: str,
    from_at: dt.datetime | None,
    to_at: dt.datetime | None,
    upcoming: bool,
    include_cancelled: bool,
    team_id: str | None,
) -> list[object]:
    filters: list[object] = [OrganizationEvent.organization_id == organization_id]
    if from_at is not None:
        filters.append(OrganizationEvent.start_at >= from_at)
    if to_at is not None:
        filters.append(OrganizationEvent.start_at < to_at)
    if upcoming:
        filters.append(OrganizationEvent.start_at >= dt.datetime.now(dt.UTC))
    if not include_cancelled:
        filters.append(OrganizationEvent.status != "cancelled")
    if team_id is not None:
        filters.append(
            or_(
                OrganizationEvent.participant_scope == "organization",
                OrganizationEvent.id.in_(
                    select(OrganizationEventTeam.event_id).where(
                        OrganizationEventTeam.organization_id == organization_id,
                        OrganizationEventTeam.team_id == team_id,
                    )
                ),
            )
        )
    return filters


async def _validate_scope(
    db: AsyncSession,
    *,
    organization_id: str,
    participant_scope: str,
    team_ids: list[str],
    roster_membership_ids: list[str],
) -> None:
    if participant_scope == "organization":
        if team_ids or roster_membership_ids:
            raise _invalid("Organization-scoped events cannot include participant IDs")
        return

    if participant_scope == "teams":
        if not team_ids or roster_membership_ids:
            raise _invalid("Team-scoped events require only team_ids")
        found_ids = set(
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
        if found_ids != set(team_ids):
            raise _not_found("Team")
        return

    if participant_scope == "selected_players":
        if not roster_membership_ids or team_ids:
            raise _invalid("Selected-player events require only roster_membership_ids")
        found_ids = set(
            (
                await db.scalars(
                    select(SchoolPlayerMembership.id).where(
                        SchoolPlayerMembership.organization_id == organization_id,
                        SchoolPlayerMembership.status == "active",
                        SchoolPlayerMembership.id.in_(roster_membership_ids),
                    )
                )
            ).all()
        )
        if found_ids != set(roster_membership_ids):
            raise _not_found("Roster player")
        return
    raise _invalid("Unsupported participant scope")


def _validate_time(start_at: dt.datetime, end_at: dt.datetime | None) -> None:
    if end_at is not None and _utc(end_at) <= _utc(start_at):
        raise _invalid("end_at must be later than start_at")


async def _replace_audience(
    db: AsyncSession,
    *,
    event_id: str,
    organization_id: str,
    team_ids: list[str],
    roster_membership_ids: list[str],
) -> None:
    await db.execute(
        delete(OrganizationEventTeam).where(OrganizationEventTeam.event_id == event_id)
    )
    await db.execute(
        delete(OrganizationEventRosterPlayer).where(
            OrganizationEventRosterPlayer.event_id == event_id
        )
    )
    db.add_all(
        [
            OrganizationEventTeam(
                event_id=event_id,
                organization_id=organization_id,
                team_id=team_id,
            )
            for team_id in team_ids
        ]
        + [
            OrganizationEventRosterPlayer(
                event_id=event_id,
                organization_id=organization_id,
                school_player_membership_id=roster_membership_id,
            )
            for roster_membership_id in roster_membership_ids
        ]
    )


async def create_event(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    payload: OrganizationEventCreate,
) -> OrganizationEventRecord:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=EVENT_WRITE_ROLES,
    )
    await _validate_scope(
        db,
        organization_id=organization_id,
        participant_scope=payload.participant_scope,
        team_ids=payload.team_ids,
        roster_membership_ids=payload.roster_membership_ids,
    )
    event = OrganizationEvent(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        event_type=payload.event_type,
        title=payload.title,
        description=payload.description,
        start_at=payload.start_at,
        end_at=payload.end_at,
        location=payload.location,
        participant_scope=payload.participant_scope,
        status="scheduled",
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
    )
    db.add(event)
    await db.flush()
    await _replace_audience(
        db,
        event_id=event.id,
        organization_id=organization_id,
        team_ids=payload.team_ids,
        roster_membership_ids=payload.roster_membership_ids,
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception(
            "organization.event_create_failed",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
        )
        raise
    await db.refresh(event)
    return OrganizationEventRecord(event, payload.team_ids, payload.roster_membership_ids)


async def get_event(
    db: AsyncSession,
    *,
    organization_id: str,
    event_id: str,
    actor_user_id: str,
) -> OrganizationEventRecord:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=EVENT_READ_ROLES,
    )
    event = await _event(db, organization_id=organization_id, event_id=event_id)
    return (await _records(db, [event]))[0]


async def list_events(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    from_at: dt.datetime | None,
    to_at: dt.datetime | None,
    upcoming: bool,
    include_cancelled: bool,
    team_id: str | None,
    limit: int,
    offset: int,
) -> tuple[list[OrganizationEventRecord], int]:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=EVENT_READ_ROLES,
    )
    from_at = _validated_boundary(from_at, "from_at")
    to_at = _validated_boundary(to_at, "to_at")
    if from_at is not None and to_at is not None and to_at <= from_at:
        raise _invalid("to_at must be later than from_at")
    if team_id is not None:
        team = await db.scalar(
            select(Team.id).where(
                Team.id == team_id,
                Team.organization_id == organization_id,
            )
        )
        if team is None:
            raise _not_found("Team")
    filters = _event_filters(
        organization_id=organization_id,
        from_at=from_at,
        to_at=to_at,
        upcoming=upcoming,
        include_cancelled=include_cancelled,
        team_id=team_id,
    )
    events = list(
        (
            await db.scalars(
                select(OrganizationEvent)
                .where(*filters)
                .order_by(OrganizationEvent.start_at, OrganizationEvent.id)
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )
    total = int(await db.scalar(select(func.count(OrganizationEvent.id)).where(*filters)) or 0)
    return await _records(db, events), total


async def update_event(
    db: AsyncSession,
    *,
    organization_id: str,
    event_id: str,
    actor_user_id: str,
    payload: OrganizationEventUpdate,
) -> OrganizationEventRecord:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=EVENT_WRITE_ROLES,
    )
    current = await _event(db, organization_id=organization_id, event_id=event_id)
    if current.status == "cancelled":
        raise OrganizationEventServiceError(409, "Cancelled events cannot be updated")
    current_record = (await _records(db, [current]))[0]
    changes = payload.model_dump(exclude_unset=True)
    participant_scope = changes.get("participant_scope", current.participant_scope)
    if participant_scope != current.participant_scope:
        team_ids = changes.get("team_ids", [])
        roster_membership_ids = changes.get("roster_membership_ids", [])
    else:
        team_ids = changes.get("team_ids", current_record.team_ids)
        roster_membership_ids = changes.get(
            "roster_membership_ids", current_record.roster_membership_ids
        )
    await _validate_scope(
        db,
        organization_id=organization_id,
        participant_scope=participant_scope,
        team_ids=team_ids,
        roster_membership_ids=roster_membership_ids,
    )
    start_at = changes.get("start_at", current.start_at)
    end_at = changes.get("end_at", current.end_at)
    _validate_time(start_at, end_at)

    for field, value in changes.items():
        if field not in {"team_ids", "roster_membership_ids"}:
            setattr(current, field, value)
    current.updated_by_user_id = actor_user_id
    if {"participant_scope", "team_ids", "roster_membership_ids"} & changes.keys():
        await _replace_audience(
            db,
            event_id=current.id,
            organization_id=organization_id,
            team_ids=team_ids,
            roster_membership_ids=roster_membership_ids,
        )
    await db.commit()
    await db.refresh(current)
    return OrganizationEventRecord(current, team_ids, roster_membership_ids)


async def cancel_event(
    db: AsyncSession,
    *,
    organization_id: str,
    event_id: str,
    actor_user_id: str,
) -> OrganizationEventRecord:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=EVENT_WRITE_ROLES,
    )
    event = await _event(db, organization_id=organization_id, event_id=event_id)
    if event.status != "cancelled":
        event.status = "cancelled"
        event.cancelled_at = dt.datetime.now(dt.UTC)
        event.cancelled_by_user_id = actor_user_id
        event.updated_by_user_id = actor_user_id
        await db.commit()
        await db.refresh(event)
    return (await _records(db, [event]))[0]


async def calendar(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    from_at: dt.datetime | None,
    to_at: dt.datetime | None,
    upcoming: bool,
    include_cancelled: bool,
    team_id: str | None,
    limit: int,
    offset: int,
) -> tuple[list[OrganizationCalendarItem], int]:
    await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=EVENT_READ_ROLES,
    )
    from_at = _validated_boundary(from_at, "from_at")
    to_at = _validated_boundary(to_at, "to_at")
    if from_at is not None and to_at is not None and to_at <= from_at:
        raise _invalid("to_at must be later than from_at")
    if team_id is not None:
        team = await db.scalar(
            select(Team.id).where(
                Team.id == team_id,
                Team.organization_id == organization_id,
            )
        )
        if team is None:
            raise _not_found("Team")

    event_filters = _event_filters(
        organization_id=organization_id,
        from_at=from_at,
        to_at=to_at,
        upcoming=upcoming,
        include_cancelled=include_cancelled,
        team_id=team_id,
    )
    window = limit + offset
    events = list(
        (
            await db.scalars(
                select(OrganizationEvent)
                .where(*event_filters)
                .order_by(OrganizationEvent.start_at, OrganizationEvent.id)
                .limit(window)
            )
        ).all()
    )
    event_total = int(
        await db.scalar(select(func.count(OrganizationEvent.id)).where(*event_filters)) or 0
    )
    event_records = await _records(db, events)

    fixture_filters: list[object] = [
        Tournament.organization_id == organization_id,
        Fixture.scheduled_date.is_not(None),
    ]
    if from_at is not None:
        fixture_filters.append(Fixture.scheduled_date >= from_at)
    if to_at is not None:
        fixture_filters.append(Fixture.scheduled_date < to_at)
    if upcoming:
        fixture_filters.append(Fixture.scheduled_date >= dt.datetime.now(dt.UTC))
    if not include_cancelled:
        fixture_filters.append(Fixture.status != "cancelled")
    if team_id is not None:
        fixture_filters.append(or_(Fixture.team_a_id == team_id, Fixture.team_b_id == team_id))

    fixture_query = (
        select(Fixture)
        .join(Tournament, Tournament.id == Fixture.tournament_id)
        .where(*fixture_filters)
        .order_by(Fixture.scheduled_date, Fixture.id)
        .limit(window)
    )
    fixtures = list((await db.scalars(fixture_query)).all())
    fixture_total = int(
        await db.scalar(
            select(func.count(Fixture.id))
            .join(Tournament, Tournament.id == Fixture.tournament_id)
            .where(*fixture_filters)
        )
        or 0
    )

    items = [
        OrganizationCalendarItem(
            source_type="organization_event",
            source_id=record.event.id,
            title=record.event.title,
            start_at=_utc(record.event.start_at),
            end_at=_utc(record.event.end_at) if record.event.end_at is not None else None,
            location=record.event.location,
            status=record.event.status,
            event_type=record.event.event_type,
            participant_scope=record.event.participant_scope,
            team_ids=record.team_ids,
            game_id=None,
            competition_id=None,
        )
        for record in event_records
    ]
    items.extend(
        OrganizationCalendarItem(
            source_type="fixture",
            source_id=fixture.id,
            title=f"{fixture.team_a_name} vs {fixture.team_b_name}",
            start_at=_utc(fixture.scheduled_date),
            end_at=None,
            location=fixture.venue,
            status=fixture.status,
            event_type=None,
            participant_scope=None,
            team_ids=[
                team_id for team_id in (fixture.team_a_id, fixture.team_b_id) if team_id is not None
            ],
            game_id=fixture.game_id,
            competition_id=fixture.tournament_id,
        )
        for fixture in fixtures
        if fixture.scheduled_date is not None
    )
    items.sort(key=lambda item: (item.start_at, item.source_type, item.source_id))
    return items[offset : offset + limit], event_total + fixture_total
