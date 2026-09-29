from __future__ import annotations

import asyncio
import os
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from backend.api.schemas.organization_notifications import OrganizationNotificationCreate
from backend.services import organization_notification_service, organization_service
from backend.sql_app.database import get_session_local
from backend.sql_app.models import (
    Organization,
    OrganizationNotification,
    OrganizationNotificationDeliveryOutcome,
    User,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_club,
    create_school,
    register_user,
)


def _organization(
    client: TestClient,
    owner: RegisteredUser,
    organization_type: str,
    name: str,
) -> dict[str, Any]:
    return (
        create_school(client, owner, name)
        if organization_type == "school"
        else create_club(client, owner, name)
    )


def _payload(
    recipient: RegisteredUser,
    *,
    key: str,
    category: str = "event",
    actor: RegisteredUser | None = None,
    title: str = "Training update",
    summary: str = "Training starts at 17:00.",
) -> OrganizationNotificationCreate:
    source_type = {
        "organization_announcement": "organization_announcement",
        "team_announcement": "team_announcement",
        "event": "organization_event",
        "selection": "selection_publication",
        "availability_reminder": "availability_target",
    }[category]
    return OrganizationNotificationCreate(
        recipient_user_id=recipient.id,
        category=category,  # type: ignore[arg-type]
        source_type=source_type,  # type: ignore[arg-type]
        source_id=f"source-{key}",
        source_version="1",
        source_key=None,
        idempotency_key=key,
        title=title,
        summary=summary,
        origin="actor" if actor is not None else "system",
        actor_user_id=actor.id if actor is not None else None,
    )


async def _create(
    client: TestClient,
    organization_id: str,
    payload: OrganizationNotificationCreate,
) -> organization_notification_service.NotificationCreationResult:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        return await organization_notification_service.create_notification(
            session,
            organization_id=organization_id,
            payload=payload,
        )


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_school_and_club_all_roles_read_only_their_own_inbox(
    school_client: TestClient,
    organization_type: str,
) -> None:
    owner = register_user(school_client, f"notification-{organization_type}-owner@example.com")
    organization = _organization(
        school_client, owner, organization_type, f"Notification {organization_type}"
    )
    actors = [("owner", owner)]
    for role in ("admin", "coach", "scorer", "viewer"):
        user = register_user(school_client, f"notification-{organization_type}-{role}@example.com")
        add_membership(school_client, owner, organization["id"], user.id, role)
        actors.append((role, user))

    created: dict[str, str] = {}
    for role, user in actors:
        result = await _create(
            school_client,
            organization["id"],
            _payload(user, key=f"{organization_type}-{role}", actor=owner),
        )
        assert result.created is True
        assert result.notification is not None
        created[role] = result.notification.id

    for role, user in actors:
        inbox = school_client.get(
            f"/api/organizations/{organization['id']}/notifications",
            headers=user.headers,
        )
        assert inbox.status_code == 200, inbox.text
        assert inbox.json()["total"] == 1
        assert [item["id"] for item in inbox.json()["items"]] == [created[role]]
        assert inbox.json()["items"][0]["recipient_user_id"] == user.id

    hidden = school_client.get(
        f"/api/organizations/{organization['id']}/notifications/{created['viewer']}",
        headers=owner.headers,
    )
    assert hidden.status_code == 404


async def test_inbox_order_filters_pagination_unread_count_and_idempotent_read(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "notification-inbox-owner@example.com")
    organization = create_school(school_client, owner, "Inbox School")
    first = await _create(
        school_client,
        organization["id"],
        _payload(owner, key="inbox-1", actor=owner, title="First"),
    )
    await asyncio.sleep(0.01)
    second = await _create(
        school_client,
        organization["id"],
        _payload(
            owner,
            key="inbox-2",
            category="selection",
            actor=owner,
            title="Second",
        ),
    )
    await asyncio.sleep(0.01)
    third = await _create(
        school_client,
        organization["id"],
        _payload(owner, key="inbox-3", actor=owner, title="Third"),
    )
    ids = [result.notification.id for result in (first, second, third) if result.notification]
    assert len(ids) == 3

    inbox = school_client.get(
        f"/api/organizations/{organization['id']}/notifications",
        params={"limit": 2, "offset": 0},
        headers=owner.headers,
    )
    assert inbox.status_code == 200
    assert inbox.json()["total"] == 3
    assert [item["title"] for item in inbox.json()["items"]] == ["Third", "Second"]
    page_two = school_client.get(
        f"/api/organizations/{organization['id']}/notifications",
        params={"limit": 2, "offset": 2},
        headers=owner.headers,
    )
    assert [item["title"] for item in page_two.json()["items"]] == ["First"]
    category = school_client.get(
        f"/api/organizations/{organization['id']}/notifications",
        params={"category": "selection"},
        headers=owner.headers,
    )
    assert category.json()["total"] == 1
    assert category.json()["items"][0]["title"] == "Second"
    assert category.json()["items"][0]["read_at"] is None
    assert school_client.get(
        f"/api/organizations/{organization['id']}/notifications/unread-count",
        headers=owner.headers,
    ).json() == {"unread_count": 3}

    notification_id = ids[1]
    read = school_client.post(
        f"/api/organizations/{organization['id']}/notifications/{notification_id}/read",
        headers=owner.headers,
    )
    assert read.status_code == 200, read.text
    read_at = read.json()["read_at"]
    assert read_at is not None and read_at.endswith("Z")
    repeated = school_client.post(
        f"/api/organizations/{organization['id']}/notifications/{notification_id}/read",
        headers=owner.headers,
    )
    assert repeated.status_code == 200
    assert repeated.json()["read_at"] == read_at
    assert school_client.get(
        f"/api/organizations/{organization['id']}/notifications/unread-count",
        headers=owner.headers,
    ).json() == {"unread_count": 2}
    unread = school_client.get(
        f"/api/organizations/{organization['id']}/notifications",
        params={"unread_only": "true"},
        headers=owner.headers,
    )
    assert unread.json()["total"] == 2
    assert notification_id not in {item["id"] for item in unread.json()["items"]}
    oversized = school_client.get(
        f"/api/organizations/{organization['id']}/notifications",
        params={"limit": 101},
        headers=owner.headers,
    )
    assert oversized.status_code == 422


async def test_tenant_recipient_membership_and_organization_status_are_revalidated(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "notification-tenant-owner-a@example.com")
    owner_b = register_user(school_client, "notification-tenant-owner-b@example.com")
    viewer = register_user(school_client, "notification-disabled-viewer@example.com")
    outsider = register_user(school_client, "notification-outsider@example.com")
    org_a = create_school(school_client, owner_a, "Tenant A")
    org_b = create_club(school_client, owner_b, "Tenant B")
    membership = add_membership(school_client, owner_a, org_a["id"], viewer.id, "viewer")
    result = await _create(
        school_client,
        org_a["id"],
        _payload(viewer, key="tenant-private", actor=owner_a),
    )
    assert result.notification is not None
    notification_id = result.notification.id

    for actor, organization_id in (
        (owner_b, org_a["id"]),
        (outsider, org_a["id"]),
        (viewer, org_b["id"]),
    ):
        denied = school_client.get(
            f"/api/organizations/{organization_id}/notifications/{notification_id}",
            headers=actor.headers,
        )
        assert denied.status_code == 404

    disabled = school_client.patch(
        f"/api/organizations/{org_a['id']}/memberships/{membership['id']}",
        json={"status": "disabled"},
        headers=owner_a.headers,
    )
    assert disabled.status_code == 200
    for suffix, method in (
        ("notifications", school_client.get),
        ("notifications/unread-count", school_client.get),
        ("notifications/preferences", school_client.get),
        (f"notifications/{notification_id}/read", school_client.post),
    ):
        response = method(f"/api/organizations/{org_a['id']}/{suffix}", headers=viewer.headers)
        assert response.status_code == 404

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        organization = await session.get(Organization, org_a["id"])
        assert organization is not None
        organization.status = "suspended"
        await session.commit()
    inactive = school_client.get(
        f"/api/organizations/{org_a['id']}/notifications",
        headers=owner_a.headers,
    )
    assert inactive.status_code == 404


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_preferences_are_recipient_owned_future_only_and_default_enabled(
    school_client: TestClient,
    organization_type: str,
) -> None:
    owner = register_user(school_client, f"notification-pref-{organization_type}-owner@example.com")
    other = register_user(school_client, f"notification-pref-{organization_type}-other@example.com")
    foreign = register_user(
        school_client, f"notification-pref-{organization_type}-foreign@example.com"
    )
    organization = _organization(
        school_client, owner, organization_type, f"Preference {organization_type}"
    )
    add_membership(school_client, owner, organization["id"], other.id, "viewer")
    existing = await _create(
        school_client,
        organization["id"],
        _payload(other, key=f"{organization_type}-existing", actor=owner),
    )
    assert existing.notification is not None

    defaults = school_client.get(
        f"/api/organizations/{organization['id']}/notifications/preferences",
        headers=other.headers,
    )
    assert defaults.status_code == 200
    assert [item["category"] for item in defaults.json()["items"]] == list(
        organization_notification_service.NOTIFICATION_CATEGORIES
    )
    assert all(item["enabled"] for item in defaults.json()["items"])

    changed = school_client.patch(
        f"/api/organizations/{organization['id']}/notifications/preferences/event",
        json={"enabled": False},
        headers=other.headers,
    )
    assert changed.status_code == 200, changed.text
    assert changed.json()["user_id"] == other.id
    assert changed.json()["enabled"] is False
    suppressed = await _create(
        school_client,
        organization["id"],
        _payload(other, key=f"{organization_type}-future", actor=owner),
    )
    assert suppressed.notification is None
    assert suppressed.suppressed_by_preference is True
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert (
            await session.scalar(
                select(func.count(OrganizationNotificationDeliveryOutcome.id)).where(
                    OrganizationNotificationDeliveryOutcome.organization_id == organization["id"],
                    OrganizationNotificationDeliveryOutcome.recipient_user_id == other.id,
                    OrganizationNotificationDeliveryOutcome.idempotency_key
                    == f"{organization_type}-future",
                    OrganizationNotificationDeliveryOutcome.outcome == "suppressed_by_preference",
                )
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count(OrganizationNotification.id)).where(
                    OrganizationNotification.organization_id == organization["id"],
                    OrganizationNotification.recipient_user_id == other.id,
                    OrganizationNotification.idempotency_key == f"{organization_type}-future",
                )
            )
            == 0
        )
    enabled = school_client.patch(
        f"/api/organizations/{organization['id']}/notifications/preferences/event",
        json={"enabled": True},
        headers=other.headers,
    )
    assert enabled.status_code == 200, enabled.text
    retried_suppression = await _create(
        school_client,
        organization["id"],
        _payload(other, key=f"{organization_type}-future", actor=owner),
    )
    assert retried_suppression.notification is None
    assert retried_suppression.created is False
    assert retried_suppression.suppressed_by_preference is True
    new_delivery = await _create(
        school_client,
        organization["id"],
        _payload(other, key=f"{organization_type}-after-enable", actor=owner),
    )
    assert new_delivery.notification is not None
    assert new_delivery.created is True
    retry_existing = await _create(
        school_client,
        organization["id"],
        _payload(other, key=f"{organization_type}-existing", actor=owner),
    )
    assert retry_existing.notification is not None
    assert retry_existing.notification.id == existing.notification.id
    inbox = school_client.get(
        f"/api/organizations/{organization['id']}/notifications",
        headers=other.headers,
    )
    assert inbox.json()["total"] == 2
    assert {item["idempotency_key"] for item in inbox.json()["items"]} == {
        f"{organization_type}-existing",
        f"{organization_type}-after-enable",
    }
    owner_preferences = school_client.get(
        f"/api/organizations/{organization['id']}/notifications/preferences",
        headers=owner.headers,
    )
    assert (
        next(item for item in owner_preferences.json()["items"] if item["category"] == "event")[
            "enabled"
        ]
        is True
    )
    foreign_update = school_client.patch(
        f"/api/organizations/{organization['id']}/notifications/preferences/event",
        json={"enabled": False},
        headers=foreign.headers,
    )
    assert foreign_update.status_code == 404


async def test_internal_creation_is_deterministic_bounded_private_and_has_no_send_route(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = register_user(school_client, "notification-private-owner@example.com")
    organization = create_school(school_client, owner, "Private Inbox")
    logged: list[tuple[str, dict[str, Any]]] = []

    class RecordingLogger:
        def info(self, event: str, **values: Any) -> None:
            logged.append((event, values))

        def error(self, event: str, **values: Any) -> None:
            logged.append((event, values))

        def exception(self, event: str, **values: Any) -> None:
            logged.append((event, values))

    monkeypatch.setattr(organization_notification_service, "logger", RecordingLogger())
    payload = _payload(
        owner,
        key="private-log-key",
        actor=owner,
        title="Private title",
        summary="PRIVATE BODY MUST NOT APPEAR IN LOGS",
    )
    first = await _create(school_client, organization["id"], payload)
    repeated = await _create(school_client, organization["id"], payload)
    assert first.created is True and first.notification is not None
    assert repeated.created is False and repeated.notification is not None
    assert repeated.notification.id == first.notification.id
    flattened_log = repr(logged)
    assert payload.title not in flattened_log
    assert payload.summary not in flattened_log

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert await session.scalar(select(func.count(OrganizationNotification.id))) == 1
        users_before = await session.scalar(select(func.count(User.id)))
    fake_payload = payload.model_copy(
        update={"recipient_user_id": "roster-only-player-without-user", "idempotency_key": "fake"}
    )
    async with session_maker() as session:
        with pytest.raises(organization_service.OrganizationServiceError):
            await organization_notification_service.create_notification(
                session,
                organization_id=organization["id"],
                payload=fake_payload,
            )
        assert await session.scalar(select(func.count(User.id))) == users_before

    no_send = school_client.post(
        f"/api/organizations/{organization['id']}/notifications",
        json=payload.model_dump(),
        headers=owner.headers,
    )
    assert no_send.status_code == 405
    assert school_client.get("/api/public/notifications").status_code == 404
    assert (
        school_client.get(
            f"/api/organizations/{organization['id']}/messages", headers=owner.headers
        ).status_code
        == 404
    )
    table_names = set(OrganizationNotification.metadata.tables)
    assert not any("conversation" in table or "device_token" in table for table in table_names)

    async def authorize_without_database(*args: Any, **kwargs: Any) -> None:
        return None

    async def no_existing_outcome(*args: Any, **kwargs: Any) -> None:
        return None

    async def preference_enabled(*args: Any, **kwargs: Any) -> bool:
        return True

    class FaultingSession:
        rolled_back = False

        def add(self, value: Any) -> None:
            return None

        async def flush(self) -> None:
            return None

        async def commit(self) -> None:
            raise RuntimeError(payload.summary)

        async def rollback(self) -> None:
            self.rolled_back = True

    monkeypatch.setattr(organization_notification_service, "_authorize", authorize_without_database)
    monkeypatch.setattr(
        organization_notification_service,
        "_existing_logical_outcome",
        no_existing_outcome,
    )
    monkeypatch.setattr(
        organization_notification_service,
        "_preference_enabled",
        preference_enabled,
    )
    faulting_session = FaultingSession()
    with pytest.raises(
        organization_notification_service.OrganizationNotificationServiceError
    ) as failure:
        await organization_notification_service.create_notification(
            faulting_session,  # type: ignore[arg-type]
            organization_id=organization["id"],
            payload=payload.model_copy(
                update={
                    "idempotency_key": "private-failure",
                    "origin": "system",
                    "actor_user_id": None,
                }
            ),
        )
    assert failure.value.status_code == 500
    assert failure.value.detail == "Notification could not be created"
    assert faulting_session.rolled_back is True
    assert payload.summary not in repr(logged)


@pytest.mark.skipif(
    os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="Notification concurrency and catalog validation require real PostgreSQL",
)
async def test_postgres_concurrent_logical_creation_and_tenant_constraints(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "notification-concurrency-owner@example.com")
    foreign_owner = register_user(school_client, "notification-concurrency-foreign@example.com")
    organization = create_school(school_client, owner, "Concurrent Inbox")
    foreign_org = create_club(school_client, foreign_owner, "Foreign Inbox")
    payload = _payload(owner, key="concurrent-one-row", actor=owner)
    session_maker = get_session_local()
    start = asyncio.Event()

    async def create_once(
        creation_payload: OrganizationNotificationCreate,
        gate: asyncio.Event,
    ) -> tuple[bool, bool, int]:
        async with session_maker() as session:
            await gate.wait()
            result = await organization_notification_service.create_notification(
                session,
                organization_id=organization["id"],
                payload=creation_payload,
            )
            user_count = await session.scalar(select(func.count(User.id)))
            return result.created, result.suppressed_by_preference, int(user_count or 0)

    tasks = [asyncio.create_task(create_once(payload, start)) for _ in range(2)]
    start.set()
    results = await asyncio.gather(*tasks)
    assert sorted(created for created, _, _ in results) == [False, True]
    assert all(not suppressed for _, suppressed, _ in results)
    assert all(user_count == 2 for _, _, user_count in results)

    disabled = school_client.patch(
        f"/api/organizations/{organization['id']}/notifications/preferences/event",
        json={"enabled": False},
        headers=owner.headers,
    )
    assert disabled.status_code == 200, disabled.text
    suppressed_payload = _payload(owner, key="concurrent-suppressed", actor=owner)
    suppression_start = asyncio.Event()
    suppression_tasks = [
        asyncio.create_task(create_once(suppressed_payload, suppression_start)) for _ in range(2)
    ]
    suppression_start.set()
    suppression_results = await asyncio.gather(*suppression_tasks)
    assert all(not created for created, _, _ in suppression_results)
    assert all(suppressed for _, suppressed, _ in suppression_results)
    assert all(user_count == 2 for _, _, user_count in suppression_results)

    enabled = school_client.patch(
        f"/api/organizations/{organization['id']}/notifications/preferences/event",
        json={"enabled": True},
        headers=owner.headers,
    )
    assert enabled.status_code == 200, enabled.text
    retried_suppression = await _create(school_client, organization["id"], suppressed_payload)
    assert retried_suppression.notification is None
    assert retried_suppression.suppressed_by_preference is True
    new_delivery = await _create(
        school_client,
        organization["id"],
        _payload(owner, key="after-concurrent-suppression", actor=owner),
    )
    assert new_delivery.created is True
    assert new_delivery.notification is not None

    async with session_maker() as session:
        assert await session.scalar(select(func.count(OrganizationNotification.id))) == 2
        assert (
            await session.scalar(
                select(func.count(OrganizationNotificationDeliveryOutcome.id)).where(
                    OrganizationNotificationDeliveryOutcome.idempotency_key
                    == "concurrent-suppressed"
                )
            )
            == 1
        )
        assert (
            await session.scalar(
                select(func.count(OrganizationNotification.id)).where(
                    OrganizationNotification.idempotency_key == "concurrent-suppressed"
                )
            )
            == 0
        )
        assert await session.scalar(select(func.count(User.id))) == 2
        invalid = OrganizationNotification(
            organization_id=foreign_org["id"],
            recipient_user_id=owner.id,
            category="event",
            source_type="organization_event",
            source_id="cross-tenant",
            source_version=None,
            source_key=None,
            idempotency_key="cross-tenant",
            title="Cross tenant",
            summary="Must fail",
            origin="system",
            actor_user_id=None,
        )
        session.add(invalid)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
        assert await session.scalar(select(func.count(User.id))) == 2

        constraints = set(
            (
                await session.scalars(
                    text(
                        "SELECT conname FROM pg_constraint "
                        "WHERE conrelid IN ('organization_notifications'::regclass, "
                        "'organization_notification_preferences'::regclass, "
                        "'organization_notification_delivery_outcomes'::regclass)"
                    )
                )
            ).all()
        )
        assert {
            "fk_organization_notifications_recipient_membership",
            "fk_organization_notifications_recipient_user",
            "uq_organization_notifications_logical_delivery",
            "ck_organization_notifications_category_source",
            "ck_organization_notifications_source_identity",
            "fk_organization_notification_preferences_membership",
            "uq_organization_notification_preferences_user_category",
            "fk_org_notification_delivery_outcomes_membership",
            "fk_org_notification_delivery_outcomes_notification",
            "uq_org_notification_delivery_outcomes_logical",
            "ck_org_notification_delivery_outcomes_binding",
        } <= constraints
        indexes = set(
            (
                await session.scalars(
                    text(
                        "SELECT indexname FROM pg_indexes WHERE tablename IN "
                        "('organization_notifications', 'organization_notification_preferences', "
                        "'organization_notification_delivery_outcomes')"
                    )
                )
            ).all()
        )
        assert {
            "ix_organization_notifications_inbox",
            "ix_organization_notifications_unread",
            "ix_organization_notifications_category",
            "ix_organization_notification_preferences_user",
            "ix_org_notification_delivery_outcomes_recipient",
        } <= indexes
        outcome_columns = set(
            (
                await session.scalars(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_schema = 'public' AND "
                        "table_name = 'organization_notification_delivery_outcomes'"
                    )
                )
            ).all()
        )
        assert {
            "organization_id",
            "recipient_user_id",
            "category",
            "idempotency_key",
            "outcome",
            "notification_id",
        } <= outcome_columns
        assert {"title", "summary"}.isdisjoint(outcome_columns)
