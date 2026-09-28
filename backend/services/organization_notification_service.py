"""Private organization notification inbox, preferences, and deterministic creation."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

import structlog
from backend.api.schemas.organization_notifications import OrganizationNotificationCreate
from backend.services import organization_service
from backend.services.organization_entitlement_service import require_organization_capability
from backend.sql_app.models import OrganizationNotification, OrganizationNotificationPreference
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

ORGANIZATION_NOTIFICATION_CAPABILITY = "organization_notifications"
NOTIFICATION_CATEGORIES = (
    "organization_announcement",
    "team_announcement",
    "event",
    "selection",
    "availability_reminder",
)
CATEGORY_SOURCE_TYPES = {
    "organization_announcement": "organization_announcement",
    "team_announcement": "team_announcement",
    "event": "organization_event",
    "selection": "selection_publication",
    "availability_reminder": "availability_target",
}


@dataclass(frozen=True)
class OrganizationNotificationServiceError(Exception):
    status_code: int
    detail: str


@dataclass(frozen=True)
class NotificationCreationResult:
    notification: OrganizationNotification | None
    created: bool
    suppressed_by_preference: bool


def _not_found() -> OrganizationNotificationServiceError:
    return OrganizationNotificationServiceError(404, "Notification not found")


def _invalid(detail: str) -> OrganizationNotificationServiceError:
    return OrganizationNotificationServiceError(422, detail)


async def _authorize(
    db: AsyncSession,
    *,
    organization_id: str,
    user_id: str,
) -> None:
    await require_organization_capability(
        db,
        organization_id=organization_id,
        actor_user_id=user_id,
        capability=ORGANIZATION_NOTIFICATION_CAPABILITY,
    )


def _validate_category_source(payload: OrganizationNotificationCreate) -> None:
    if CATEGORY_SOURCE_TYPES[payload.category] != payload.source_type:
        raise _invalid("Notification category and source type do not match")
    if payload.source_id is None and payload.source_key is None:
        raise _invalid("Notification source_id or source_key is required")
    if payload.origin == "actor" and payload.actor_user_id is None:
        raise _invalid("Actor-origin notifications require actor_user_id")
    if payload.origin == "system" and payload.actor_user_id is not None:
        raise _invalid("System-origin notifications must not supply actor_user_id")


async def _existing_logical_notification(
    db: AsyncSession,
    *,
    organization_id: str,
    recipient_user_id: str,
    idempotency_key: str,
) -> OrganizationNotification | None:
    return await db.scalar(
        select(OrganizationNotification).where(
            OrganizationNotification.organization_id == organization_id,
            OrganizationNotification.recipient_user_id == recipient_user_id,
            OrganizationNotification.idempotency_key == idempotency_key,
        )
    )


async def _preference_enabled(
    db: AsyncSession,
    *,
    organization_id: str,
    user_id: str,
    category: str,
) -> bool:
    preference = await db.scalar(
        select(OrganizationNotificationPreference.enabled).where(
            OrganizationNotificationPreference.organization_id == organization_id,
            OrganizationNotificationPreference.user_id == user_id,
            OrganizationNotificationPreference.category == category,
        )
    )
    return True if preference is None else bool(preference)


async def create_notification(
    db: AsyncSession,
    *,
    organization_id: str,
    payload: OrganizationNotificationCreate,
) -> NotificationCreationResult:
    """Create one future-delivery notification without exposing a client send route."""
    _validate_category_source(payload)
    await _authorize(
        db,
        organization_id=organization_id,
        user_id=payload.recipient_user_id,
    )
    if payload.actor_user_id is not None:
        await organization_service.get_organization_for_member(
            db,
            organization_id=organization_id,
            user_id=payload.actor_user_id,
        )

    existing = await _existing_logical_notification(
        db,
        organization_id=organization_id,
        recipient_user_id=payload.recipient_user_id,
        idempotency_key=payload.idempotency_key,
    )
    if existing is not None:
        return NotificationCreationResult(existing, created=False, suppressed_by_preference=False)

    if not await _preference_enabled(
        db,
        organization_id=organization_id,
        user_id=payload.recipient_user_id,
        category=payload.category,
    ):
        logger.info(
            "organization.notification_suppressed",
            organization_id=organization_id,
            recipient_user_id=payload.recipient_user_id,
            category=payload.category,
            idempotency_key=payload.idempotency_key,
        )
        return NotificationCreationResult(None, created=False, suppressed_by_preference=True)

    notification = OrganizationNotification(
        organization_id=organization_id,
        recipient_user_id=payload.recipient_user_id,
        category=payload.category,
        source_type=payload.source_type,
        source_id=payload.source_id,
        source_version=payload.source_version,
        source_key=payload.source_key,
        idempotency_key=payload.idempotency_key,
        title=payload.title,
        summary=payload.summary,
        origin=payload.origin,
        actor_user_id=payload.actor_user_id,
        created_at=dt.datetime.now(dt.UTC),
    )
    db.add(notification)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _existing_logical_notification(
            db,
            organization_id=organization_id,
            recipient_user_id=payload.recipient_user_id,
            idempotency_key=payload.idempotency_key,
        )
        if existing is None:
            raise _invalid("Notification conflicts with its organization contract") from None
        logger.info(
            "organization.notification_duplicate_suppressed",
            organization_id=organization_id,
            recipient_user_id=payload.recipient_user_id,
            category=payload.category,
            idempotency_key=payload.idempotency_key,
        )
        return NotificationCreationResult(existing, created=False, suppressed_by_preference=False)
    except Exception:
        await db.rollback()
        # Database exception text can include bound title/summary parameters.
        # Keep operational logs metadata-only and let the sanitized API boundary
        # handle the failure without recording private notification content.
        logger.error(
            "organization.notification_create_failed",
            organization_id=organization_id,
            recipient_user_id=payload.recipient_user_id,
            category=payload.category,
            idempotency_key=payload.idempotency_key,
        )
        raise OrganizationNotificationServiceError(
            500, "Notification could not be created"
        ) from None

    await db.refresh(notification)
    logger.info(
        "organization.notification_created",
        organization_id=organization_id,
        notification_id=notification.id,
        recipient_user_id=payload.recipient_user_id,
        category=payload.category,
        idempotency_key=payload.idempotency_key,
    )
    return NotificationCreationResult(notification, created=True, suppressed_by_preference=False)


async def list_notifications(
    db: AsyncSession,
    *,
    organization_id: str,
    recipient_user_id: str,
    category: str | None,
    unread_only: bool,
    limit: int,
    offset: int,
) -> tuple[list[OrganizationNotification], int]:
    await _authorize(db, organization_id=organization_id, user_id=recipient_user_id)
    predicates = [
        OrganizationNotification.organization_id == organization_id,
        OrganizationNotification.recipient_user_id == recipient_user_id,
    ]
    if category is not None:
        predicates.append(OrganizationNotification.category == category)
    if unread_only:
        predicates.append(OrganizationNotification.read_at.is_(None))
    rows = await db.scalars(
        select(OrganizationNotification)
        .where(*predicates)
        .order_by(
            OrganizationNotification.created_at.desc(),
            OrganizationNotification.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )
    total = await db.scalar(select(func.count(OrganizationNotification.id)).where(*predicates))
    return list(rows.all()), int(total or 0)


async def unread_count(
    db: AsyncSession,
    *,
    organization_id: str,
    recipient_user_id: str,
) -> int:
    await _authorize(db, organization_id=organization_id, user_id=recipient_user_id)
    total = await db.scalar(
        select(func.count(OrganizationNotification.id)).where(
            OrganizationNotification.organization_id == organization_id,
            OrganizationNotification.recipient_user_id == recipient_user_id,
            OrganizationNotification.read_at.is_(None),
        )
    )
    return int(total or 0)


async def get_notification(
    db: AsyncSession,
    *,
    organization_id: str,
    notification_id: str,
    recipient_user_id: str,
) -> OrganizationNotification:
    await _authorize(db, organization_id=organization_id, user_id=recipient_user_id)
    notification = await db.scalar(
        select(OrganizationNotification).where(
            OrganizationNotification.id == notification_id,
            OrganizationNotification.organization_id == organization_id,
            OrganizationNotification.recipient_user_id == recipient_user_id,
        )
    )
    if notification is None:
        raise _not_found()
    return notification


async def mark_notification_read(
    db: AsyncSession,
    *,
    organization_id: str,
    notification_id: str,
    recipient_user_id: str,
) -> OrganizationNotification:
    await _authorize(db, organization_id=organization_id, user_id=recipient_user_id)
    notification = await db.scalar(
        select(OrganizationNotification)
        .where(
            OrganizationNotification.id == notification_id,
            OrganizationNotification.organization_id == organization_id,
            OrganizationNotification.recipient_user_id == recipient_user_id,
        )
        .with_for_update()
    )
    if notification is None:
        raise _not_found()
    if notification.read_at is None:
        notification.read_at = dt.datetime.now(dt.UTC)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception(
                "organization.notification_mark_read_failed",
                organization_id=organization_id,
                notification_id=notification_id,
                recipient_user_id=recipient_user_id,
            )
            raise
        await db.refresh(notification)
    return notification


async def list_preferences(
    db: AsyncSession,
    *,
    organization_id: str,
    user_id: str,
) -> list[OrganizationNotificationPreference | tuple[str, bool]]:
    await _authorize(db, organization_id=organization_id, user_id=user_id)
    rows = list(
        (
            await db.scalars(
                select(OrganizationNotificationPreference).where(
                    OrganizationNotificationPreference.organization_id == organization_id,
                    OrganizationNotificationPreference.user_id == user_id,
                )
            )
        ).all()
    )
    by_category = {row.category: row for row in rows}
    return [by_category.get(category, (category, True)) for category in NOTIFICATION_CATEGORIES]


async def update_preference(
    db: AsyncSession,
    *,
    organization_id: str,
    user_id: str,
    category: str,
    enabled: bool,
) -> OrganizationNotificationPreference:
    await _authorize(db, organization_id=organization_id, user_id=user_id)
    if category not in NOTIFICATION_CATEGORIES:
        raise _invalid("Unsupported notification category")
    preference = await db.scalar(
        select(OrganizationNotificationPreference)
        .where(
            OrganizationNotificationPreference.organization_id == organization_id,
            OrganizationNotificationPreference.user_id == user_id,
            OrganizationNotificationPreference.category == category,
        )
        .with_for_update()
    )
    if preference is None:
        preference = OrganizationNotificationPreference(
            organization_id=organization_id,
            user_id=user_id,
            category=category,
            enabled=enabled,
        )
        db.add(preference)
    else:
        preference.enabled = enabled
        preference.updated_at = dt.datetime.now(dt.UTC)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception(
            "organization.notification_preference_update_failed",
            organization_id=organization_id,
            user_id=user_id,
            category=category,
        )
        raise
    await db.refresh(preference)
    return preference
