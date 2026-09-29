"""Manual in-app notifications that reflect, but never mutate, cricket workflow truth."""

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import dataclass

import structlog
from backend.api.schemas.organization_notifications import OrganizationNotificationCreate
from backend.api.schemas.organization_workflow_notifications import (
    OrganizationAvailabilityReminderResult,
    OrganizationEventNotificationResult,
    OrganizationSelectionNotificationResult,
)
from backend.services import (
    organization_announcement_service,
    organization_availability_service,
    organization_notification_service,
    organization_service,
)
from backend.services.organization_entitlement_service import require_organization_capability
from backend.sql_app.models import (
    OrganizationEvent,
    OrganizationEventRosterPlayer,
    OrganizationEventTeam,
    OrganizationMembership,
    OrganizationPlayerAvailability,
    OrganizationSelectionPublication,
    OrganizationSelectionPublicationPlayer,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
)
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

WORKFLOW_NOTIFICATION_CAPABILITY = "organization_notifications"
WORKFLOW_WRITE_ROLES = frozenset({"owner", "admin", "coach"})


@dataclass(frozen=True)
class OrganizationWorkflowNotificationServiceError(Exception):
    status_code: int
    detail: str


def _not_found(resource: str) -> OrganizationWorkflowNotificationServiceError:
    return OrganizationWorkflowNotificationServiceError(404, f"{resource} not found")


def _forbidden() -> OrganizationWorkflowNotificationServiceError:
    return OrganizationWorkflowNotificationServiceError(403, "Insufficient organization role")


def _conflict(detail: str) -> OrganizationWorkflowNotificationServiceError:
    return OrganizationWorkflowNotificationServiceError(409, detail)


def _utc(value: dt.datetime) -> dt.datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC)


def _timestamp_version(value: dt.datetime) -> str:
    return _utc(value).isoformat(timespec="microseconds").replace("+00:00", "Z")


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
        capability=WORKFLOW_NOTIFICATION_CAPABILITY,
    )
    _, membership = await organization_service.get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if membership.role not in WORKFLOW_WRITE_ROLES:
        raise _forbidden()
    return membership


async def _active_roster_ids(
    db: AsyncSession,
    *,
    organization_id: str,
) -> set[str]:
    return set(
        (
            await db.scalars(
                select(SchoolPlayerMembership.id).where(
                    SchoolPlayerMembership.organization_id == organization_id,
                    SchoolPlayerMembership.status == "active",
                )
            )
        ).all()
    )


async def _active_team_roster_ids(
    db: AsyncSession,
    *,
    organization_id: str,
    team_ids: tuple[str, ...],
) -> set[str]:
    if not team_ids:
        return set()
    return set(
        (
            await db.scalars(
                select(SchoolTeamPlayerMembership.school_player_membership_id)
                .join(
                    SchoolPlayerMembership,
                    and_(
                        SchoolPlayerMembership.id
                        == SchoolTeamPlayerMembership.school_player_membership_id,
                        SchoolPlayerMembership.organization_id
                        == SchoolTeamPlayerMembership.organization_id,
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
                    SchoolTeamPlayerMembership.organization_id == organization_id,
                    SchoolTeamPlayerMembership.team_id.in_(team_ids),
                    SchoolTeamPlayerMembership.status == "active",
                    SchoolPlayerMembership.status == "active",
                    Team.status == "active",
                )
            )
        ).all()
    )


async def _fan_out(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    recipient_ids: list[str],
    category: str,
    source_type: str,
    source_id: str,
    source_version: str,
    source_key: str,
    title: str,
    summary: str,
) -> tuple[int, int]:
    delivered = 0
    suppressed = 0
    for recipient_user_id in recipient_ids:
        try:
            result = await organization_notification_service.create_notification(
                db,
                organization_id=organization_id,
                payload=OrganizationNotificationCreate(
                    recipient_user_id=recipient_user_id,
                    category=category,  # type: ignore[arg-type]
                    source_type=source_type,  # type: ignore[arg-type]
                    source_id=source_id,
                    source_version=source_version,
                    source_key=source_key,
                    idempotency_key=(
                        f"{source_key}:version:{source_version}:recipient:{recipient_user_id}"
                    ),
                    title=title,
                    summary=summary,
                    origin="actor",
                    actor_user_id=actor_user_id,
                ),
                commit=False,
            )
        except organization_notification_service.OrganizationNotificationServiceError as exc:
            raise OrganizationWorkflowNotificationServiceError(exc.status_code, exc.detail) from exc
        if result.suppressed_by_preference:
            suppressed += 1
        else:
            delivered += 1
    return delivered, suppressed


async def _safe_recipients(
    db: AsyncSession,
    *,
    organization_id: str,
    audience_type: str,
    actor_user_id: str,
    actor_role: str,
    team_ids: tuple[str, ...] = (),
) -> list[str]:
    try:
        return await organization_announcement_service.resolve_safe_user_recipients(
            db,
            organization_id=organization_id,
            audience_type=audience_type,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            team_ids=team_ids,
        )
    except organization_announcement_service.OrganizationAnnouncementServiceError as exc:
        raise OrganizationWorkflowNotificationServiceError(exc.status_code, exc.detail) from exc


async def notify_event(
    db: AsyncSession,
    *,
    organization_id: str,
    event_id: str,
    actor_user_id: str,
    notification_type: str,
) -> OrganizationEventNotificationResult:
    membership = await _authorize(db, organization_id=organization_id, actor_user_id=actor_user_id)
    event = await db.scalar(
        select(OrganizationEvent)
        .where(
            OrganizationEvent.id == event_id,
            OrganizationEvent.organization_id == organization_id,
        )
        .with_for_update()
    )
    if event is None:
        raise _not_found("Event")
    if notification_type == "cancellation" and event.status != "cancelled":
        raise _conflict("Cancel the event before sending a cancellation notification")
    if notification_type == "update" and event.status != "scheduled":
        raise _conflict("Cancelled events require a cancellation notification")

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
    selected_ids = set(
        (
            await db.scalars(
                select(OrganizationEventRosterPlayer.school_player_membership_id).where(
                    OrganizationEventRosterPlayer.event_id == event.id,
                    OrganizationEventRosterPlayer.organization_id == organization_id,
                )
            )
        ).all()
    )
    if event.participant_scope == "organization":
        recipient_ids = await _safe_recipients(
            db,
            organization_id=organization_id,
            audience_type="organization",
            actor_user_id=actor_user_id,
            actor_role=membership.role,
        )
        unresolved_ids = await _active_roster_ids(db, organization_id=organization_id)
    elif event.participant_scope == "teams":
        recipient_ids = await _safe_recipients(
            db,
            organization_id=organization_id,
            audience_type="team",
            actor_user_id=actor_user_id,
            actor_role=membership.role,
            team_ids=team_ids,
        )
        unresolved_ids = await _active_team_roster_ids(
            db, organization_id=organization_id, team_ids=team_ids
        )
    else:
        recipient_ids = []
        active_ids = await _active_roster_ids(db, organization_id=organization_id)
        unresolved_ids = selected_ids & active_ids

    source_version = _timestamp_version(event.updated_at)
    kind_label = "cancelled" if notification_type == "cancellation" else "updated"
    source_key = f"event:{event.id}:{notification_type}"
    try:
        delivered, suppressed = await _fan_out(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            recipient_ids=recipient_ids,
            category="event",
            source_type="organization_event",
            source_id=event.id,
            source_version=source_version,
            source_key=source_key,
            title=f"Event {kind_label}: {event.title}",
            summary=(
                f"{event.title} is {event.status}. "
                f"Starts {_utc(event.start_at).isoformat()} at {event.location}."
            ),
        )
        await db.commit()
    except OrganizationWorkflowNotificationServiceError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        logger.error(
            "organization.workflow_event_notification_failed",
            organization_id=organization_id,
            event_id=event_id,
            actor_user_id=actor_user_id,
            notification_type=notification_type,
        )
        raise OrganizationWorkflowNotificationServiceError(
            500, "Event notification could not be sent"
        ) from None
    return OrganizationEventNotificationResult(
        source_type="organization_event",
        source_id=event.id,
        source_version=source_version,
        notification_type=notification_type,  # type: ignore[arg-type]
        safe_user_recipient_count=len(recipient_ids),
        delivered_count=delivered,
        suppressed_by_preference_count=suppressed,
        unresolved_roster_recipient_count=len(unresolved_ids),
    )


async def notify_selection_publication(
    db: AsyncSession,
    *,
    organization_id: str,
    plan_id: str,
    publication_version: int,
    actor_user_id: str,
) -> OrganizationSelectionNotificationResult:
    membership = await _authorize(db, organization_id=organization_id, actor_user_id=actor_user_id)
    publication = await db.scalar(
        select(OrganizationSelectionPublication)
        .where(
            OrganizationSelectionPublication.organization_id == organization_id,
            OrganizationSelectionPublication.selection_plan_id == plan_id,
            OrganizationSelectionPublication.publication_version == publication_version,
        )
        .with_for_update()
    )
    if publication is None:
        raise _not_found("Selection publication")
    team = await db.scalar(
        select(Team).where(
            Team.id == publication.team_id,
            Team.organization_id == organization_id,
            Team.status == "active",
        )
    )
    if team is None:
        raise _not_found("Team")
    recipient_ids = await _safe_recipients(
        db,
        organization_id=organization_id,
        audience_type="team",
        actor_user_id=actor_user_id,
        actor_role=membership.role,
        team_ids=(publication.team_id,),
    )
    player_roles = list(
        (
            await db.scalars(
                select(OrganizationSelectionPublicationPlayer.selection_role).where(
                    OrganizationSelectionPublicationPlayer.publication_id == publication.id,
                    OrganizationSelectionPublicationPlayer.organization_id == organization_id,
                )
            )
        ).all()
    )
    xi_count = player_roles.count("xi")
    reserve_count = player_roles.count("reserve")
    source_version = str(publication.publication_version)
    source_key = f"selection:{plan_id}:publication:{publication.publication_version}:staff"
    try:
        delivered, suppressed = await _fan_out(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            recipient_ids=recipient_ids,
            category="selection",
            source_type="selection_publication",
            source_id=publication.id,
            source_version=source_version,
            source_key=source_key,
            title=f"Selection published: {team.name}",
            summary=(
                f"Selection version {publication.publication_version} has {xi_count} planned XI "
                f"and {reserve_count} reserves. This staff notice does not change the match Playing XI."
            ),
        )
        await db.commit()
    except OrganizationWorkflowNotificationServiceError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        logger.error(
            "organization.workflow_selection_notification_failed",
            organization_id=organization_id,
            plan_id=plan_id,
            publication_version=publication_version,
            actor_user_id=actor_user_id,
        )
        raise OrganizationWorkflowNotificationServiceError(
            500, "Selection notification could not be sent"
        ) from None
    return OrganizationSelectionNotificationResult(
        source_type="selection_publication",
        source_id=publication.id,
        source_version=source_version,
        selection_plan_id=plan_id,
        publication_version=publication.publication_version,
        safe_user_recipient_count=len(recipient_ids),
        delivered_count=delivered,
        suppressed_by_preference_count=suppressed,
        unresolved_roster_recipient_count=xi_count + reserve_count,
        xi_roster_count=xi_count,
        reserve_roster_count=reserve_count,
        unresolved_xi_count=xi_count,
        unresolved_reserve_count=reserve_count,
    )


async def send_availability_reminder(
    db: AsyncSession,
    *,
    organization_id: str,
    target_type: str,
    target_id: str,
    actor_user_id: str,
) -> OrganizationAvailabilityReminderResult:
    membership = await _authorize(db, organization_id=organization_id, actor_user_id=actor_user_id)
    try:
        source = await organization_availability_service._source(
            db,
            organization_id=organization_id,
            target_type=target_type,  # type: ignore[arg-type]
            target_id=target_id,
            lock=True,
        )
        target = await organization_availability_service._target(db, source=source, lock=True)
        if target is None:
            raise _not_found("Availability target")
        eligible = await organization_availability_service._eligible_players(
            db, source=source, team_id=None
        )
    except organization_availability_service.OrganizationAvailabilityServiceError as exc:
        raise OrganizationWorkflowNotificationServiceError(exc.status_code, exc.detail) from exc
    state_rows = list(
        (
            await db.execute(
                select(
                    OrganizationPlayerAvailability.school_player_membership_id,
                    OrganizationPlayerAvailability.state,
                    OrganizationPlayerAvailability.recorded_at,
                ).where(
                    OrganizationPlayerAvailability.organization_id == organization_id,
                    OrganizationPlayerAvailability.target_id == target.id,
                )
            )
        ).tuples()
    )
    responded_ids = {row[0] for row in state_rows}
    no_response_ids = sorted(
        record.membership.id for record in eligible if record.membership.id not in responded_ids
    )

    if source.participant_scope == "teams" or source.target_type == "fixture":
        recipient_ids = await _safe_recipients(
            db,
            organization_id=organization_id,
            audience_type="team",
            actor_user_id=actor_user_id,
            actor_role=membership.role,
            team_ids=source.team_ids,
        )
    else:
        recipient_ids = await _safe_recipients(
            db,
            organization_id=organization_id,
            audience_type="staff",
            actor_user_id=actor_user_id,
            actor_role=membership.role,
        )

    version_material = "|".join(
        [
            _timestamp_version(target.updated_at),
            *(f"eligible:{record.membership.id}" for record in eligible),
            *(
                f"response:{membership_id}:{state}:{_timestamp_version(recorded_at)}"
                for membership_id, state, recorded_at in sorted(state_rows)
            ),
        ]
    )
    source_version = hashlib.sha256(version_material.encode("utf-8")).hexdigest()[:32]
    source_key = f"availability:{target.id}:manual-reminder"
    try:
        delivered, suppressed = await _fan_out(
            db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            recipient_ids=recipient_ids,
            category="availability_reminder",
            source_type="availability_target",
            source_id=target.id,
            source_version=source_version,
            source_key=source_key,
            title=f"Availability reminder: {source.title}",
            summary=(
                f"{len(no_response_ids)} availability responses are outstanding for "
                f"{source.title}. This is a staff operational reminder and does not record a response."
            ),
        )
        await db.commit()
    except OrganizationWorkflowNotificationServiceError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        logger.error(
            "organization.workflow_availability_reminder_failed",
            organization_id=organization_id,
            target_type=target_type,
            target_id=target_id,
            actor_user_id=actor_user_id,
        )
        raise OrganizationWorkflowNotificationServiceError(
            500, "Availability reminder could not be sent"
        ) from None
    return OrganizationAvailabilityReminderResult(
        source_type="availability_target",
        source_id=target.id,
        source_version=source_version,
        target_type=source.target_type,
        no_response_count=len(no_response_ids),
        safe_user_recipient_count=len(recipient_ids),
        delivered_count=delivered,
        suppressed_by_preference_count=suppressed,
        unresolved_roster_recipient_count=len(no_response_ids),
    )
