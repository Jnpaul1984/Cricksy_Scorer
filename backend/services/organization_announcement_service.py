"""Tenant-safe structured announcements with atomic in-app notification fan-out."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import structlog
from backend.api.schemas.organization_announcements import (
    OrganizationAnnouncementCreate,
    OrganizationAnnouncementFeedItem,
    OrganizationAnnouncementRevisionRequest,
    OrganizationAnnouncementUpdate,
)
from backend.api.schemas.organization_notifications import OrganizationNotificationCreate
from backend.services import organization_notification_service, organization_service
from backend.services.organization_entitlement_service import require_organization_capability
from backend.sql_app.models import (
    OrganizationAnnouncement,
    OrganizationAnnouncementPublication,
    OrganizationMembership,
    Team,
    User,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

ANNOUNCEMENT_CAPABILITY = "organization_notifications"
ANNOUNCEMENT_WRITE_ROLES = frozenset({"owner", "admin", "coach"})
ANNOUNCEMENT_READ_ROLES = frozenset({"owner", "admin", "coach", "scorer", "viewer"})
STAFF_AUDIENCE_ROLES = frozenset({"owner", "admin", "coach", "scorer"})
ORGANIZATION_ADMIN_ROLES = frozenset({"owner", "admin"})


@dataclass(frozen=True)
class OrganizationAnnouncementServiceError(Exception):
    status_code: int
    detail: str


def _not_found() -> OrganizationAnnouncementServiceError:
    return OrganizationAnnouncementServiceError(404, "Announcement not found")


def _forbidden() -> OrganizationAnnouncementServiceError:
    return OrganizationAnnouncementServiceError(403, "Insufficient organization role")


def _invalid(detail: str) -> OrganizationAnnouncementServiceError:
    return OrganizationAnnouncementServiceError(422, detail)


def _conflict(detail: str) -> OrganizationAnnouncementServiceError:
    return OrganizationAnnouncementServiceError(409, detail)


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
        capability=ANNOUNCEMENT_CAPABILITY,
    )
    _, membership = await organization_service.get_organization_for_member(
        db,
        organization_id=organization_id,
        user_id=actor_user_id,
    )
    if membership.role not in allowed_roles:
        raise _forbidden()
    return membership


async def _team_for_audience(
    db: AsyncSession,
    *,
    organization_id: str,
    team_id: str | None,
    actor_user_id: str,
    actor_role: str,
) -> Team:
    if team_id is None:
        raise _invalid("Team audience requires team_id")
    team = await db.scalar(
        select(Team).where(
            Team.id == team_id,
            Team.organization_id == organization_id,
            Team.status == "active",
        )
    )
    if team is None:
        raise _not_found()
    if actor_role == "coach" and team.coach_user_id != actor_user_id:
        raise _forbidden()
    return team


async def _validate_audience(
    db: AsyncSession,
    *,
    organization_id: str,
    audience_type: str,
    team_id: str | None,
    actor_user_id: str,
    actor_role: str,
) -> Team | None:
    if audience_type == "team":
        return await _team_for_audience(
            db,
            organization_id=organization_id,
            team_id=team_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
        )
    if team_id is not None:
        raise _invalid("team_id is only valid for Team audience")
    return None


async def create_announcement(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    payload: OrganizationAnnouncementCreate,
) -> OrganizationAnnouncement:
    membership = await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=ANNOUNCEMENT_WRITE_ROLES,
    )
    await _validate_audience(
        db,
        organization_id=organization_id,
        audience_type=payload.audience_type,
        team_id=payload.team_id,
        actor_user_id=actor_user_id,
        actor_role=membership.role,
    )
    announcement = OrganizationAnnouncement(
        organization_id=organization_id,
        audience_type=payload.audience_type,
        team_id=payload.team_id,
        title=payload.title,
        body=payload.body,
        status="draft",
        revision=1,
        last_published_version=0,
        created_by_user_id=actor_user_id,
        updated_by_user_id=actor_user_id,
    )
    db.add(announcement)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.error(
            "organization.announcement_create_failed",
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            audience_type=payload.audience_type,
            team_id=payload.team_id,
        )
        raise OrganizationAnnouncementServiceError(
            500, "Announcement could not be created"
        ) from None
    await db.refresh(announcement)
    logger.info(
        "organization.announcement_created",
        organization_id=organization_id,
        announcement_id=announcement.id,
        actor_user_id=actor_user_id,
        audience_type=announcement.audience_type,
        team_id=announcement.team_id,
    )
    return announcement


async def _locked_announcement(
    db: AsyncSession,
    *,
    organization_id: str,
    announcement_id: str,
) -> OrganizationAnnouncement:
    announcement = await db.scalar(
        select(OrganizationAnnouncement)
        .where(
            OrganizationAnnouncement.id == announcement_id,
            OrganizationAnnouncement.organization_id == organization_id,
        )
        .with_for_update()
    )
    if announcement is None:
        raise _not_found()
    return announcement


async def update_announcement(
    db: AsyncSession,
    *,
    organization_id: str,
    announcement_id: str,
    actor_user_id: str,
    payload: OrganizationAnnouncementUpdate,
) -> OrganizationAnnouncement:
    membership = await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=ANNOUNCEMENT_WRITE_ROLES,
    )
    announcement = await _locked_announcement(
        db,
        organization_id=organization_id,
        announcement_id=announcement_id,
    )
    if announcement.status != "draft":
        raise _conflict("Published announcements require an explicit new draft revision")
    if announcement.revision != payload.expected_revision:
        raise _conflict("Announcement revision changed; refresh and try again")

    changes = payload.model_dump(exclude_unset=True)
    changes.pop("expected_revision")
    audience_type = changes.get("audience_type", announcement.audience_type)
    if audience_type != "team" and "team_id" not in changes:
        team_id = None
    else:
        team_id = changes.get("team_id", announcement.team_id)
    await _validate_audience(
        db,
        organization_id=organization_id,
        audience_type=audience_type,
        team_id=team_id,
        actor_user_id=actor_user_id,
        actor_role=membership.role,
    )

    new_values = {
        "title": changes.get("title", announcement.title),
        "body": changes.get("body", announcement.body),
        "audience_type": audience_type,
        "team_id": team_id,
    }
    if all(getattr(announcement, field) == value for field, value in new_values.items()):
        return announcement
    for field, value in new_values.items():
        setattr(announcement, field, value)
    announcement.revision += 1
    announcement.updated_by_user_id = actor_user_id
    announcement.updated_at = dt.datetime.now(dt.UTC)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.error(
            "organization.announcement_update_failed",
            organization_id=organization_id,
            announcement_id=announcement_id,
            actor_user_id=actor_user_id,
        )
        raise OrganizationAnnouncementServiceError(
            500, "Announcement could not be updated"
        ) from None
    await db.refresh(announcement)
    return announcement


async def create_revision(
    db: AsyncSession,
    *,
    organization_id: str,
    announcement_id: str,
    actor_user_id: str,
    payload: OrganizationAnnouncementRevisionRequest,
) -> OrganizationAnnouncement:
    membership = await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=ANNOUNCEMENT_WRITE_ROLES,
    )
    announcement = await _locked_announcement(
        db,
        organization_id=organization_id,
        announcement_id=announcement_id,
    )
    if announcement.revision != payload.expected_revision:
        raise _conflict("Announcement revision changed; refresh and try again")
    if announcement.status != "published":
        raise _conflict("Only a published announcement can start a new draft revision")
    await _validate_audience(
        db,
        organization_id=organization_id,
        audience_type=announcement.audience_type,
        team_id=announcement.team_id,
        actor_user_id=actor_user_id,
        actor_role=membership.role,
    )
    announcement.status = "draft"
    announcement.revision += 1
    announcement.updated_by_user_id = actor_user_id
    announcement.updated_at = dt.datetime.now(dt.UTC)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.error(
            "organization.announcement_revision_failed",
            organization_id=organization_id,
            announcement_id=announcement_id,
            actor_user_id=actor_user_id,
        )
        raise OrganizationAnnouncementServiceError(
            500, "Announcement revision could not be created"
        ) from None
    await db.refresh(announcement)
    return announcement


async def _recipients(
    db: AsyncSession,
    *,
    organization_id: str,
    audience_type: str,
    team: Team | None,
) -> list[str]:
    rows = (
        await db.execute(
            select(OrganizationMembership.user_id, OrganizationMembership.role)
            .join(User, User.id == OrganizationMembership.user_id)
            .where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.status == "active",
                User.is_active.is_(True),
            )
            .order_by(OrganizationMembership.user_id)
        )
    ).all()
    if audience_type == "organization":
        return [user_id for user_id, _ in rows]
    if audience_type == "staff":
        return [user_id for user_id, role in rows if role in STAFF_AUDIENCE_ROLES]
    if team is None:
        raise _invalid("Team audience requires an active Team")
    return [
        user_id
        for user_id, role in rows
        if role in ORGANIZATION_ADMIN_ROLES or (role == "coach" and team.coach_user_id == user_id)
    ]


def _notification_contract(
    *,
    announcement: OrganizationAnnouncement,
    publication_version: int,
    recipient_user_id: str,
    actor_user_id: str,
) -> OrganizationNotificationCreate:
    is_team = announcement.audience_type == "team"
    return OrganizationNotificationCreate(
        recipient_user_id=recipient_user_id,
        category="team_announcement" if is_team else "organization_announcement",
        source_type="team_announcement" if is_team else "organization_announcement",
        source_id=announcement.id,
        source_version=str(publication_version),
        source_key=announcement.audience_type,
        idempotency_key=(
            f"announcement:{announcement.id}:publication:{publication_version}:"
            f"recipient:{recipient_user_id}"
        ),
        title=announcement.title,
        summary=announcement.body[:1000],
        origin="actor",
        actor_user_id=actor_user_id,
    )


async def publish_announcement(
    db: AsyncSession,
    *,
    organization_id: str,
    announcement_id: str,
    actor_user_id: str,
    payload: OrganizationAnnouncementRevisionRequest,
) -> OrganizationAnnouncementPublication:
    membership = await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=ANNOUNCEMENT_WRITE_ROLES,
    )
    announcement = await _locked_announcement(
        db,
        organization_id=organization_id,
        announcement_id=announcement_id,
    )
    if announcement.revision != payload.expected_revision:
        raise _conflict("Announcement revision changed; refresh and try again")
    if announcement.status == "published":
        existing = await db.scalar(
            select(OrganizationAnnouncementPublication).where(
                OrganizationAnnouncementPublication.announcement_id == announcement.id,
                OrganizationAnnouncementPublication.organization_id == organization_id,
                OrganizationAnnouncementPublication.publication_version
                == announcement.last_published_version,
                OrganizationAnnouncementPublication.announcement_revision == announcement.revision,
            )
        )
        if existing is None:
            raise OrganizationAnnouncementServiceError(
                500, "Announcement publication could not be loaded"
            )
        return existing

    team = await _validate_audience(
        db,
        organization_id=organization_id,
        audience_type=announcement.audience_type,
        team_id=announcement.team_id,
        actor_user_id=actor_user_id,
        actor_role=membership.role,
    )
    recipient_ids = await _recipients(
        db,
        organization_id=organization_id,
        audience_type=announcement.audience_type,
        team=team,
    )
    publication_version = announcement.last_published_version + 1
    delivered = 0
    suppressed = 0
    try:
        for recipient_user_id in recipient_ids:
            result = await organization_notification_service.create_notification(
                db,
                organization_id=organization_id,
                payload=_notification_contract(
                    announcement=announcement,
                    publication_version=publication_version,
                    recipient_user_id=recipient_user_id,
                    actor_user_id=actor_user_id,
                ),
                commit=False,
            )
            if result.suppressed_by_preference:
                suppressed += 1
            else:
                delivered += 1

        publication = OrganizationAnnouncementPublication(
            announcement_id=announcement.id,
            organization_id=organization_id,
            publication_version=publication_version,
            announcement_revision=announcement.revision,
            audience_type=announcement.audience_type,
            team_id=announcement.team_id,
            title=announcement.title,
            body=announcement.body,
            published_by_user_id=actor_user_id,
            published_at=dt.datetime.now(dt.UTC),
            eligible_recipient_count=len(recipient_ids),
            delivered_count=delivered,
            suppressed_by_preference_count=suppressed,
            unresolved_recipient_count=0,
        )
        db.add(publication)
        announcement.status = "published"
        announcement.last_published_version = publication_version
        announcement.updated_by_user_id = actor_user_id
        announcement.updated_at = dt.datetime.now(dt.UTC)
        await db.commit()
    except OrganizationAnnouncementServiceError:
        await db.rollback()
        raise
    except Exception:
        await db.rollback()
        logger.error(
            "organization.announcement_publish_failed",
            organization_id=organization_id,
            announcement_id=announcement_id,
            actor_user_id=actor_user_id,
            audience_type=announcement.audience_type,
            team_id=announcement.team_id,
            publication_version=publication_version,
        )
        raise OrganizationAnnouncementServiceError(
            500, "Announcement could not be published"
        ) from None
    await db.refresh(publication)
    logger.info(
        "organization.announcement_published",
        organization_id=organization_id,
        announcement_id=announcement_id,
        actor_user_id=actor_user_id,
        audience_type=publication.audience_type,
        team_id=publication.team_id,
        publication_version=publication.publication_version,
        eligible_recipient_count=publication.eligible_recipient_count,
        delivered_count=publication.delivered_count,
        suppressed_by_preference_count=publication.suppressed_by_preference_count,
    )
    return publication


def _visible_to_member(
    *,
    audience_type: str,
    team_id: str | None,
    membership: OrganizationMembership,
    teams: dict[str, Team],
) -> bool:
    if audience_type == "organization":
        return True
    if audience_type == "staff":
        return membership.role in STAFF_AUDIENCE_ROLES
    if membership.role in ORGANIZATION_ADMIN_ROLES:
        return True
    team = teams.get(team_id or "")
    return bool(
        team is not None and membership.role == "coach" and team.coach_user_id == membership.user_id
    )


async def list_feed(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    limit: int,
    offset: int,
) -> tuple[list[OrganizationAnnouncementFeedItem], int]:
    membership = await _authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        allowed_roles=ANNOUNCEMENT_READ_ROLES,
    )
    announcements = list(
        (
            await db.scalars(
                select(OrganizationAnnouncement).where(
                    OrganizationAnnouncement.organization_id == organization_id
                )
            )
        ).all()
    )
    publications = list(
        (
            await db.scalars(
                select(OrganizationAnnouncementPublication).where(
                    OrganizationAnnouncementPublication.organization_id == organization_id
                )
            )
        ).all()
    )
    team_ids = {
        item.team_id for item in [*announcements, *publications] if item.team_id is not None
    }
    teams = {
        team.id: team
        for team in (
            (
                await db.scalars(
                    select(Team).where(
                        Team.organization_id == organization_id,
                        Team.id.in_(team_ids),
                    )
                )
            ).all()
            if team_ids
            else []
        )
    }
    by_id = {announcement.id: announcement for announcement in announcements}
    items: list[OrganizationAnnouncementFeedItem] = []
    for publication in publications:
        announcement = by_id.get(publication.announcement_id)
        if announcement is None or not _visible_to_member(
            audience_type=publication.audience_type,
            team_id=publication.team_id,
            membership=membership,
            teams=teams,
        ):
            continue
        items.append(
            OrganizationAnnouncementFeedItem(
                announcement_id=announcement.id,
                organization_id=organization_id,
                title=publication.title,
                body=publication.body,
                audience_type=publication.audience_type,
                team_id=publication.team_id,
                status="published",
                revision=publication.announcement_revision,
                publication_version=publication.publication_version,
                published_by_user_id=publication.published_by_user_id,
                published_at=publication.published_at,
                eligible_recipient_count=publication.eligible_recipient_count,
                delivered_count=publication.delivered_count,
                suppressed_by_preference_count=publication.suppressed_by_preference_count,
                unresolved_recipient_count=publication.unresolved_recipient_count,
                created_by_user_id=announcement.created_by_user_id,
                created_at=announcement.created_at,
                updated_at=publication.published_at,
            )
        )
    if membership.role in ANNOUNCEMENT_WRITE_ROLES:
        for announcement in announcements:
            if announcement.status != "draft" or not _visible_to_member(
                audience_type=announcement.audience_type,
                team_id=announcement.team_id,
                membership=membership,
                teams=teams,
            ):
                continue
            items.append(
                OrganizationAnnouncementFeedItem(
                    announcement_id=announcement.id,
                    organization_id=organization_id,
                    title=announcement.title,
                    body=announcement.body,
                    audience_type=announcement.audience_type,
                    team_id=announcement.team_id,
                    status="draft",
                    revision=announcement.revision,
                    publication_version=None,
                    published_by_user_id=None,
                    published_at=None,
                    eligible_recipient_count=None,
                    delivered_count=None,
                    suppressed_by_preference_count=None,
                    unresolved_recipient_count=None,
                    created_by_user_id=announcement.created_by_user_id,
                    created_at=announcement.created_at,
                    updated_at=announcement.updated_at,
                )
            )
    items.sort(key=lambda item: (item.updated_at, item.announcement_id), reverse=True)
    return items[offset : offset + limit], len(items)
