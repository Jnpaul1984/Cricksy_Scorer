from __future__ import annotations

import asyncio
import os
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError

from backend.api.schemas.organization_announcements import OrganizationAnnouncementRevisionRequest
from backend.services import organization_announcement_service
from backend.sql_app.database import get_session_local
from backend.sql_app.models import (
    OrganizationAnnouncement,
    OrganizationAnnouncementPublication,
    OrganizationNotification,
    OrganizationNotificationDeliveryOutcome,
    Team,
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


def _create_draft(
    client: TestClient,
    organization_id: str,
    actor: RegisteredUser,
    *,
    audience_type: str = "organization",
    team_id: str | None = None,
    title: str = "Training update",
    body: str = "Training starts at 17:00 on the main ground.",
) -> dict[str, Any]:
    response = client.post(
        f"/api/organizations/{organization_id}/announcements",
        json={
            "title": title,
            "body": body,
            "audience_type": audience_type,
            "team_id": team_id,
        },
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _publish(
    client: TestClient,
    organization_id: str,
    actor: RegisteredUser,
    announcement: dict[str, Any],
) -> dict[str, Any]:
    response = client.post(
        f"/api/organizations/{organization_id}/announcements/{announcement['id']}/publish",
        json={"expected_revision": announcement["revision"]},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("organization_type", ["school", "club"])
def test_school_and_club_drafts_are_private_and_send_nothing(
    school_client: TestClient,
    organization_type: str,
) -> None:
    owner = register_user(school_client, f"announce-{organization_type}-owner@example.com")
    viewer = register_user(school_client, f"announce-{organization_type}-viewer@example.com")
    organization = _organization(
        school_client, owner, organization_type, f"Announcement {organization_type}"
    )
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    draft = _create_draft(school_client, organization["id"], owner)
    assert draft["status"] == "draft"
    assert draft["revision"] == 1

    writer_feed = school_client.get(
        f"/api/organizations/{organization['id']}/announcements", headers=owner.headers
    )
    reader_feed = school_client.get(
        f"/api/organizations/{organization['id']}/announcements", headers=viewer.headers
    )
    assert writer_feed.status_code == 200
    assert writer_feed.json()["items"][0]["status"] == "draft"
    assert reader_feed.status_code == 200
    assert reader_feed.json()["items"] == []


@pytest.mark.parametrize("role", ["owner", "admin", "coach"])
def test_owner_admin_and_coach_can_author(
    school_client: TestClient,
    role: str,
) -> None:
    owner = register_user(school_client, f"announce-author-{role}-owner@example.com")
    organization = create_school(school_client, owner, f"Author {role}")
    actor = owner
    if role != "owner":
        actor = register_user(school_client, f"announce-author-{role}@example.com")
        add_membership(school_client, owner, organization["id"], actor.id, role)
    draft = _create_draft(school_client, organization["id"], actor)
    assert draft["created_by_user_id"] == actor.id


@pytest.mark.parametrize("role", ["scorer", "viewer"])
def test_scorer_and_viewer_are_read_only(
    school_client: TestClient,
    role: str,
) -> None:
    owner = register_user(school_client, f"announce-readonly-{role}-owner@example.com")
    actor = register_user(school_client, f"announce-readonly-{role}@example.com")
    organization = create_school(school_client, owner, f"Readonly {role}")
    add_membership(school_client, owner, organization["id"], actor.id, role)
    response = school_client.post(
        f"/api/organizations/{organization['id']}/announcements",
        json={
            "title": "Denied",
            "body": "This must remain a draft only in the request.",
            "audience_type": "organization",
            "team_id": None,
        },
        headers=actor.headers,
    )
    assert response.status_code == 403


async def test_organization_staff_and_team_recipient_rules(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "announce-audience-owner@example.com")
    admin = register_user(school_client, "announce-audience-admin@example.com")
    coach = register_user(school_client, "announce-audience-coach@example.com")
    other_coach = register_user(school_client, "announce-audience-other-coach@example.com")
    scorer = register_user(school_client, "announce-audience-scorer@example.com")
    viewer = register_user(school_client, "announce-audience-viewer@example.com")
    disabled = register_user(school_client, "announce-audience-disabled@example.com")
    organization = create_school(school_client, owner, "Audience School")
    for role, user in (
        ("admin", admin),
        ("coach", coach),
        ("coach", other_coach),
        ("scorer", scorer),
        ("viewer", viewer),
    ):
        add_membership(school_client, owner, organization["id"], user.id, role)
    disabled_membership = add_membership(
        school_client, owner, organization["id"], disabled.id, "viewer"
    )
    assert (
        school_client.patch(
            f"/api/organizations/{organization['id']}/memberships/{disabled_membership['id']}",
            json={"status": "disabled"},
            headers=owner.headers,
        ).status_code
        == 200
    )
    team_response = school_client.post(
        f"/api/organizations/{organization['id']}/teams",
        json={"name": "First XI", "coach_id": coach.id},
        headers=owner.headers,
    )
    assert team_response.status_code == 201, team_response.text
    team = team_response.json()

    # Retained roster players and legacy Team.players are intentionally not User recipients.
    user_count_before = 7
    roster = school_client.post(
        f"/api/organizations/{organization['id']}/players",
        json={"player_name": "Roster Only Child"},
        headers=owner.headers,
    )
    assert roster.status_code == 201, roster.text
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored_team = await session.get(Team, team["id"])
        assert stored_team is not None
        stored_team.owner_user_id = viewer.id
        stored_team.players = [{"id": "legacy", "name": "Not a User"}]
        await session.commit()
        assert await session.scalar(select(func.count(User.id))) == user_count_before

    organization_publication = _publish(
        school_client,
        organization["id"],
        owner,
        _create_draft(school_client, organization["id"], owner, title="Whole organization"),
    )
    assert organization_publication["eligible_recipient_count"] == 6

    staff_publication = _publish(
        school_client,
        organization["id"],
        owner,
        _create_draft(
            school_client,
            organization["id"],
            owner,
            audience_type="staff",
            title="Staff briefing",
        ),
    )
    assert staff_publication["eligible_recipient_count"] == 5

    team_draft = _create_draft(
        school_client,
        organization["id"],
        owner,
        audience_type="team",
        team_id=team["id"],
        title="First XI briefing",
    )
    team_publication = _publish(school_client, organization["id"], owner, team_draft)
    assert team_publication["eligible_recipient_count"] == 3

    for user in (owner, admin, coach):
        feed = school_client.get(
            f"/api/organizations/{organization['id']}/announcements", headers=user.headers
        )
        assert "First XI briefing" in {item["title"] for item in feed.json()["items"]}
    for user in (other_coach, scorer, viewer):
        feed = school_client.get(
            f"/api/organizations/{organization['id']}/announcements", headers=user.headers
        )
        titles = {item["title"] for item in feed.json()["items"]}
        assert "First XI briefing" not in titles
    assert "Staff briefing" not in {
        item["title"]
        for item in school_client.get(
            f"/api/organizations/{organization['id']}/announcements", headers=viewer.headers
        ).json()["items"]
    }
    assert "Staff briefing" in {
        item["title"]
        for item in school_client.get(
            f"/api/organizations/{organization['id']}/announcements", headers=scorer.headers
        ).json()["items"]
    }

    denied_team = school_client.post(
        f"/api/organizations/{organization['id']}/announcements",
        json={
            "title": "Wrong Team",
            "body": "An unassigned coach cannot target this Team.",
            "audience_type": "team",
            "team_id": team["id"],
        },
        headers=other_coach.headers,
    )
    assert denied_team.status_code == 403


async def test_publish_suppression_retry_new_version_and_immutable_snapshot(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "announce-version-owner@example.com")
    viewer = register_user(school_client, "announce-version-viewer@example.com")
    organization = create_club(school_client, owner, "Version Club")
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    disabled = school_client.patch(
        f"/api/organizations/{organization['id']}/notifications/preferences/organization_announcement",
        json={"enabled": False},
        headers=viewer.headers,
    )
    assert disabled.status_code == 200

    draft = _create_draft(
        school_client,
        organization["id"],
        owner,
        title="Original title",
        body="Original private body",
    )
    first = _publish(school_client, organization["id"], owner, draft)
    assert first["publication_version"] == 1
    assert first["delivered_count"] == 1
    assert first["suppressed_by_preference_count"] == 1
    retry = school_client.post(
        f"/api/organizations/{organization['id']}/announcements/{draft['id']}/publish",
        json={"expected_revision": draft["revision"]},
        headers=owner.headers,
    )
    assert retry.status_code == 201
    assert retry.json()["id"] == first["id"]

    assert (
        school_client.patch(
            f"/api/organizations/{organization['id']}/notifications/preferences/organization_announcement",
            json={"enabled": True},
            headers=viewer.headers,
        ).status_code
        == 200
    )
    retry_after_enable = school_client.post(
        f"/api/organizations/{organization['id']}/announcements/{draft['id']}/publish",
        json={"expected_revision": draft["revision"]},
        headers=owner.headers,
    )
    assert retry_after_enable.json()["suppressed_by_preference_count"] == 1
    assert (
        school_client.get(
            f"/api/organizations/{organization['id']}/notifications", headers=viewer.headers
        ).json()["total"]
        == 0
    )

    revision = school_client.post(
        f"/api/organizations/{organization['id']}/announcements/{draft['id']}/revisions",
        json={"expected_revision": draft["revision"]},
        headers=owner.headers,
    )
    assert revision.status_code == 201, revision.text
    updated = school_client.patch(
        f"/api/organizations/{organization['id']}/announcements/{draft['id']}",
        json={
            "expected_revision": revision.json()["revision"],
            "title": "Updated title",
            "body": "Updated private body",
        },
        headers=owner.headers,
    )
    assert updated.status_code == 200, updated.text
    second = _publish(school_client, organization["id"], owner, updated.json())
    assert second["publication_version"] == 2
    assert second["delivered_count"] == 2
    viewer_inbox = school_client.get(
        f"/api/organizations/{organization['id']}/notifications", headers=viewer.headers
    ).json()["items"]
    assert [item["title"] for item in viewer_inbox] == ["Updated title"]

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        publications = list(
            (
                await session.scalars(
                    select(OrganizationAnnouncementPublication)
                    .where(OrganizationAnnouncementPublication.announcement_id == draft["id"])
                    .order_by(OrganizationAnnouncementPublication.publication_version)
                )
            ).all()
        )
        assert [(row.title, row.body) for row in publications] == [
            ("Original title", "Original private body"),
            ("Updated title", "Updated private body"),
        ]
        assert (
            await session.scalar(
                select(func.count(OrganizationNotificationDeliveryOutcome.id)).where(
                    OrganizationNotificationDeliveryOutcome.organization_id == organization["id"]
                )
            )
            == 4
        )


def test_foreign_team_validation_content_bounds_and_membership_revocation(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "announce-tenant-owner@example.com")
    foreign_owner = register_user(school_client, "announce-tenant-foreign@example.com")
    viewer = register_user(school_client, "announce-tenant-viewer@example.com")
    organization = create_school(school_client, owner, "Tenant School")
    foreign = create_club(school_client, foreign_owner, "Foreign Club")
    membership = add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    foreign_team = school_client.post(
        f"/api/organizations/{foreign['id']}/teams",
        json={"name": "Foreign XI"},
        headers=foreign_owner.headers,
    ).json()
    denied = school_client.post(
        f"/api/organizations/{organization['id']}/announcements",
        json={
            "title": "Foreign",
            "body": "Must not reveal the Team.",
            "audience_type": "team",
            "team_id": foreign_team["id"],
        },
        headers=owner.headers,
    )
    assert denied.status_code == 404
    assert (
        school_client.post(
            f"/api/organizations/{organization['id']}/announcements",
            json={
                "title": "Oversized",
                "body": "x" * 6001,
                "audience_type": "organization",
            },
            headers=owner.headers,
        ).status_code
        == 422
    )
    published = _publish(
        school_client,
        organization["id"],
        owner,
        _create_draft(school_client, organization["id"], owner),
    )
    assert published["eligible_recipient_count"] == 2
    assert (
        school_client.patch(
            f"/api/organizations/{organization['id']}/memberships/{membership['id']}",
            json={"status": "disabled"},
            headers=owner.headers,
        ).status_code
        == 200
    )
    revoked = school_client.get(
        f"/api/organizations/{organization['id']}/announcements", headers=viewer.headers
    )
    assert revoked.status_code == 404


async def test_private_content_is_not_logged_and_no_chat_or_public_routes(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = register_user(school_client, "announce-private-owner@example.com")
    organization = create_school(school_client, owner, "Private School")
    logged: list[tuple[str, dict[str, Any]]] = []

    class RecordingLogger:
        def info(self, event: str, **values: Any) -> None:
            logged.append((event, values))

        def error(self, event: str, **values: Any) -> None:
            logged.append((event, values))

    monkeypatch.setattr(organization_announcement_service, "logger", RecordingLogger())
    title = "PRIVATE ANNOUNCEMENT TITLE"
    body = "PRIVATE ANNOUNCEMENT BODY MUST NOT APPEAR IN LOGS"
    draft = _create_draft(school_client, organization["id"], owner, title=title, body=body)
    _publish(school_client, organization["id"], owner, draft)
    assert title not in repr(logged)
    assert body not in repr(logged)
    assert school_client.get("/api/public/announcements").status_code == 404
    assert (
        school_client.get(
            f"/api/organizations/{organization['id']}/messages", headers=owner.headers
        ).status_code
        == 404
    )
    assert (
        school_client.post(
            f"/api/organizations/{organization['id']}/announcements/{draft['id']}/replies",
            json={"body": "No reply route"},
            headers=owner.headers,
        ).status_code
        == 404
    )


@pytest.mark.skipif(
    os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="Announcement locking and catalog validation require real PostgreSQL",
)
async def test_postgres_concurrent_publish_and_catalog_contract(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "announce-concurrency-owner@example.com")
    viewer = register_user(school_client, "announce-concurrency-viewer@example.com")
    organization = create_school(school_client, owner, "Concurrency School")
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    draft = _create_draft(school_client, organization["id"], owner)
    session_maker = get_session_local()
    start = asyncio.Event()

    async def publish_once() -> tuple[str, int, int]:
        async with session_maker() as session:
            await start.wait()
            publication = await organization_announcement_service.publish_announcement(
                session,
                organization_id=organization["id"],
                announcement_id=draft["id"],
                actor_user_id=owner.id,
                payload=OrganizationAnnouncementRevisionRequest(
                    expected_revision=draft["revision"]
                ),
            )
            usable = int(await session.scalar(select(func.count(User.id))) or 0)
            return publication.id, publication.publication_version, usable

    tasks = [asyncio.create_task(publish_once()) for _ in range(2)]
    start.set()
    results = await asyncio.gather(*tasks)
    assert len({publication_id for publication_id, _, _ in results}) == 1
    assert {version for _, version, _ in results} == {1}
    assert all(usable == 2 for _, _, usable in results)

    async with session_maker() as session:
        assert await session.scalar(select(func.count(OrganizationAnnouncementPublication.id))) == 1
        assert await session.scalar(select(func.count(OrganizationNotification.id))) == 2
        assert (
            await session.scalar(select(func.count(OrganizationNotificationDeliveryOutcome.id)))
            == 2
        )
        announcement = await session.get(OrganizationAnnouncement, draft["id"])
        assert announcement is not None
        assert announcement.status == "published"
        assert announcement.last_published_version == 1
        constraints = set(
            (
                await session.scalars(
                    text(
                        "SELECT conname FROM pg_constraint WHERE conrelid IN "
                        "('organization_announcements'::regclass, "
                        "'organization_announcement_publications'::regclass)"
                    )
                )
            ).all()
        )
        assert {
            "fk_organization_announcements_team_organization",
            "fk_organization_announcement_publications_announcement",
            "fk_organization_announcement_publications_team_organization",
            "uq_organization_announcement_publication_version",
            "ck_organization_announcements_team_audience",
            "ck_organization_announcement_publications_counts_total",
        } <= constraints
        announcement_delete_action = await session.scalar(
            text(
                "SELECT confdeltype::text FROM pg_constraint "
                "WHERE conname = "
                "'fk_organization_announcement_publications_announcement'"
            )
        )
        assert announcement_delete_action == "r"
        indexes = set(
            (
                await session.scalars(
                    text(
                        "SELECT indexname FROM pg_indexes WHERE tablename IN "
                        "('organization_announcements', "
                        "'organization_announcement_publications')"
                    )
                )
            ).all()
        )
        assert {
            "ix_organization_announcements_feed",
            "ix_organization_announcements_team",
            "ix_organization_announcement_publications_feed",
            "ix_organization_announcement_publications_team",
        } <= indexes

        with pytest.raises(IntegrityError):
            await session.execute(
                text("DELETE FROM organization_announcements WHERE id = :announcement_id"),
                {"announcement_id": draft["id"]},
            )
        await session.rollback()
        assert await session.scalar(select(func.count(User.id))) == 2
        assert await session.scalar(select(func.count(OrganizationAnnouncementPublication.id))) == 1
