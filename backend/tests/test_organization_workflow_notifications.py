from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.sql_app.models import (
    OrganizationEvent,
    OrganizationNotification,
    OrganizationNotificationDeliveryOutcome,
    OrganizationPlayerAttendance,
    OrganizationPlayerAvailability,
    User,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_club,
    create_school,
    register_user,
)
from backend.tests.test_organization_availability import (
    _assign,
    _availability_url,
    _event,
    _player,
    _record,
)
from backend.tests.test_organization_selection_plans import _update_plan
from backend.tests.test_organization_selection_publications import (
    _prepared_plan,
    _publish,
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


def _notify_event(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    event_id: str,
    notification_type: str = "update",
):
    return client.post(
        f"/api/organizations/{organization_id}/events/{event_id}/notifications",
        json={"notification_type": notification_type},
        headers=actor.headers,
    )


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_event_update_uses_current_truth_and_does_not_mutate_cricket_domains(
    school_client: TestClient,
    organization_type: str,
) -> None:
    owner = register_user(school_client, f"workflow-event-{organization_type}-owner@example.com")
    viewer = register_user(school_client, f"workflow-event-{organization_type}-viewer@example.com")
    organization = _organization(
        school_client, owner, organization_type, f"Workflow {organization_type}"
    )
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    roster_player = _player(
        school_client, owner, organization["id"], f"{organization_type} roster-only player"
    )
    event = _event(
        school_client,
        owner,
        organization["id"],
        title="Current training truth",
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored_before = await session.get(OrganizationEvent, event["id"])
        assert stored_before is not None
        event_state = (
            stored_before.title,
            stored_before.start_at,
            stored_before.location,
            stored_before.status,
            stored_before.updated_at,
        )
        availability_before = await session.scalar(
            select(func.count(OrganizationPlayerAvailability.id))
        )
        attendance_before = await session.scalar(
            select(func.count(OrganizationPlayerAttendance.id))
        )
        user_count_before = await session.scalar(select(func.count(User.id)))

    response = _notify_event(school_client, owner, organization["id"], event["id"])
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["notification_type"] == "update"
    assert result["safe_user_recipient_count"] == 2
    assert result["delivered_count"] == 2
    assert result["unresolved_roster_recipient_count"] == 1

    repeated = _notify_event(school_client, owner, organization["id"], event["id"])
    assert repeated.status_code == 200
    assert repeated.json() == result

    async with session_maker() as session:
        stored_after = await session.get(OrganizationEvent, event["id"])
        assert stored_after is not None
        assert (
            stored_after.title,
            stored_after.start_at,
            stored_after.location,
            stored_after.status,
            stored_after.updated_at,
        ) == event_state
        assert (
            await session.scalar(select(func.count(OrganizationPlayerAvailability.id)))
            == availability_before
        )
        assert (
            await session.scalar(select(func.count(OrganizationPlayerAttendance.id)))
            == attendance_before
        )
        assert await session.scalar(select(func.count(User.id))) == user_count_before
        notifications = list(
            (
                await session.scalars(
                    select(OrganizationNotification).where(
                        OrganizationNotification.organization_id == organization["id"]
                    )
                )
            ).all()
        )
        assert len(notifications) == 2
        assert {row.recipient_user_id for row in notifications} == {owner.id, viewer.id}
        assert all(roster_player["player_name"] not in row.summary for row in notifications)


async def test_event_team_and_selected_player_audiences_preserve_identity_and_team_authority(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "workflow-event-team-owner@example.com")
    admin = register_user(school_client, "workflow-event-team-admin@example.com")
    coach = register_user(school_client, "workflow-event-team-coach@example.com")
    other_coach = register_user(school_client, "workflow-event-team-other-coach@example.com")
    organization = create_school(school_client, owner, "Workflow Team School")
    for role, user in (("admin", admin), ("coach", coach), ("coach", other_coach)):
        add_membership(school_client, owner, organization["id"], user.id, role)
    team = school_client.post(
        f"/api/organizations/{organization['id']}/teams",
        json={"name": "First XI", "coach_id": coach.id},
        headers=owner.headers,
    ).json()
    player = _player(school_client, owner, organization["id"], "Roster-only child")
    _assign(school_client, owner, organization["id"], team["id"], player["id"])
    team_event = _event(
        school_client,
        owner,
        organization["id"],
        title="First XI training",
        participant_scope="teams",
        team_ids=[team["id"]],
    )
    team_result = _notify_event(school_client, coach, organization["id"], team_event["id"])
    assert team_result.status_code == 200, team_result.text
    assert team_result.json()["safe_user_recipient_count"] == 3
    assert team_result.json()["unresolved_roster_recipient_count"] == 1
    assert (
        _notify_event(school_client, other_coach, organization["id"], team_event["id"]).status_code
        == 403
    )

    selected_event = _event(
        school_client,
        owner,
        organization["id"],
        title="Selected-player clinic",
        participant_scope="selected_players",
        roster_membership_ids=[player["id"]],
    )
    selected_result = _notify_event(school_client, owner, organization["id"], selected_event["id"])
    assert selected_result.status_code == 200
    assert selected_result.json()["safe_user_recipient_count"] == 0
    assert selected_result.json()["delivered_count"] == 0
    assert selected_result.json()["unresolved_roster_recipient_count"] == 1


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_event_cancellation_roles_tenant_hiding_and_durable_preference_suppression(
    school_client: TestClient,
    organization_type: str,
) -> None:
    owner = register_user(school_client, f"workflow-cancel-{organization_type}-owner@example.com")
    viewer = register_user(school_client, f"workflow-cancel-{organization_type}-viewer@example.com")
    scorer = register_user(school_client, f"workflow-cancel-{organization_type}-scorer@example.com")
    foreign_owner = register_user(
        school_client, f"workflow-cancel-{organization_type}-foreign@example.com"
    )
    organization = _organization(
        school_client, owner, organization_type, f"Workflow Cancel {organization_type}"
    )
    foreign_type = "club" if organization_type == "school" else "school"
    foreign = _organization(
        school_client, foreign_owner, foreign_type, f"Foreign Workflow {foreign_type}"
    )
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    add_membership(school_client, owner, organization["id"], scorer.id, "scorer")
    event = _event(school_client, owner, organization["id"], title="Cancelled training")

    assert (
        school_client.post(
            f"/api/organizations/{organization['id']}/events/{event['id']}/notifications",
            json={"notification_type": "unsupported"},
            headers=owner.headers,
        ).status_code
        == 422
    )
    assert (
        _notify_event(
            school_client, owner, organization["id"], event["id"], "cancellation"
        ).status_code
        == 409
    )
    for actor in (viewer, scorer):
        assert (
            _notify_event(school_client, actor, organization["id"], event["id"]).status_code == 403
        )
    assert (
        _notify_event(school_client, foreign_owner, foreign["id"], event["id"]).status_code == 404
    )
    cancelled = school_client.post(
        f"/api/organizations/{organization['id']}/events/{event['id']}/cancel",
        headers=owner.headers,
    )
    assert cancelled.status_code == 200
    assert (
        school_client.patch(
            f"/api/organizations/{organization['id']}/notifications/preferences/event",
            json={"enabled": False},
            headers=viewer.headers,
        ).status_code
        == 200
    )
    first = _notify_event(school_client, owner, organization["id"], event["id"], "cancellation")
    assert first.status_code == 200
    assert first.json()["delivered_count"] == 2
    assert first.json()["suppressed_by_preference_count"] == 1
    assert (
        school_client.patch(
            f"/api/organizations/{organization['id']}/notifications/preferences/event",
            json={"enabled": True},
            headers=viewer.headers,
        ).status_code
        == 200
    )
    retry = _notify_event(school_client, owner, organization["id"], event["id"], "cancellation")
    assert retry.json()["suppressed_by_preference_count"] == 1
    assert (
        school_client.get(
            f"/api/organizations/{organization['id']}/notifications",
            headers=viewer.headers,
        ).json()["total"]
        == 0
    )


async def test_published_selection_notification_is_exact_version_truthful_and_idempotent(
    school_client: TestClient,
) -> None:
    owner, organization, _, _, players, _, plan = _prepared_plan(school_client)
    admin = register_user(school_client, "workflow-selection-preference-admin@example.com")
    add_membership(school_client, owner, organization["id"], admin.id, "admin")
    foreign_owner = register_user(school_client, "workflow-selection-foreign@example.com")
    foreign = create_club(school_client, foreign_owner, "Foreign Selection Club")
    published = _publish(school_client, owner, organization["id"], plan)
    assert published.status_code == 201, published.text
    endpoint = (
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}"
        "/publications/1/notifications"
    )
    assert (
        school_client.patch(
            f"/api/organizations/{organization['id']}/notifications/preferences/selection",
            json={"enabled": False},
            headers=admin.headers,
        ).status_code
        == 200
    )
    first = school_client.post(endpoint, headers=owner.headers)
    assert first.status_code == 200, first.text
    result = first.json()
    assert result["publication_version"] == 1
    assert result["xi_roster_count"] == 11
    assert result["reserve_roster_count"] == 1
    assert result["unresolved_xi_count"] == 11
    assert result["unresolved_reserve_count"] == 1
    assert result["safe_user_recipient_count"] == 2
    assert result["delivered_count"] == 1
    assert result["suppressed_by_preference_count"] == 1
    assert (
        school_client.patch(
            f"/api/organizations/{organization['id']}/notifications/preferences/selection",
            json={"enabled": True},
            headers=admin.headers,
        ).status_code
        == 200
    )
    assert school_client.post(endpoint, headers=owner.headers).json() == result
    assert (
        school_client.post(
            f"/api/organizations/{foreign['id']}/selection-plans/{plan['id']}"
            "/publications/1/notifications",
            headers=foreign_owner.headers,
        ).status_code
        == 404
    )

    missing_draft = school_client.post(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}"
        "/publications/2/notifications",
        headers=owner.headers,
    )
    assert missing_draft.status_code == 404
    draft = school_client.post(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}/draft",
        json={"expected_revision": plan["revision"]},
        headers=owner.headers,
    )
    assert draft.status_code == 200
    changed = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {
            "expected_revision": draft.json()["revision"],
            "batting_order_roster_membership_ids": [player["id"] for player in players[10::-1]],
        },
    )
    second_publication = _publish(school_client, owner, organization["id"], changed.json())
    assert second_publication.status_code == 201
    second = school_client.post(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}"
        "/publications/2/notifications",
        headers=owner.headers,
    )
    assert second.status_code == 200
    assert second.json()["source_version"] == "2"
    assert second.json()["delivered_count"] == 2
    assert second.json()["suppressed_by_preference_count"] == 0
    assert (
        school_client.get(
            f"/api/organizations/{organization['id']}/notifications",
            headers=owner.headers,
        ).json()["total"]
        == 2
    )
    assert (
        school_client.get(
            f"/api/organizations/{organization['id']}/notifications",
            headers=admin.headers,
        ).json()["total"]
        == 1
    )


@pytest.mark.parametrize("role", ["admin", "coach"])
async def test_selection_notification_allows_governed_writers_and_denies_read_only_roles(
    school_client: TestClient,
    role: str,
) -> None:
    owner, organization, team, _, _, _, plan = _prepared_plan(school_client)
    actor = register_user(school_client, f"workflow-selection-{role}@example.com")
    add_membership(school_client, owner, organization["id"], actor.id, role)
    if role == "coach":
        response = school_client.patch(
            f"/api/organizations/{organization['id']}/teams/{team['id']}",
            json={"coach_id": actor.id},
            headers=owner.headers,
        )
        assert response.status_code == 200, response.text
    assert _publish(school_client, owner, organization["id"], plan).status_code == 201
    response = school_client.post(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}"
        "/publications/1/notifications",
        headers=actor.headers,
    )
    assert response.status_code == 200, response.text

    for readonly_role in ("scorer", "viewer"):
        readonly = register_user(
            school_client, f"workflow-selection-{role}-{readonly_role}@example.com"
        )
        add_membership(school_client, owner, organization["id"], readonly.id, readonly_role)
        denied = school_client.post(
            f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}"
            "/publications/1/notifications",
            headers=readonly.headers,
        )
        assert denied.status_code == 403


async def test_availability_reminder_is_bounded_idempotent_and_does_not_record_responses(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "workflow-availability-owner@example.com")
    coach = register_user(school_client, "workflow-availability-coach@example.com")
    organization = create_school(school_client, owner, "Workflow Availability School")
    add_membership(school_client, owner, organization["id"], coach.id, "coach")
    first = _player(school_client, owner, organization["id"], "No response one")
    second = _player(school_client, owner, organization["id"], "Responded player")
    event = _event(school_client, owner, organization["id"], title="Availability training")
    target_url = _availability_url(organization["id"], "event", event["id"])
    assert (
        school_client.patch(
            target_url,
            json={"response_deadline": "2099-01-01T12:00:00+00:00"},
            headers=owner.headers,
        ).status_code
        == 200
    )
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            "event",
            event["id"],
            second["id"],
            "available",
        ).status_code
        == 200
    )
    before = school_client.get(target_url, headers=owner.headers).json()
    reminder_url = f"{target_url}/reminders"
    response = school_client.post(reminder_url, headers=coach.headers)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["no_response_count"] == 1
    assert result["unresolved_roster_recipient_count"] == 1
    assert result["safe_user_recipient_count"] == 2
    assert result["delivered_count"] == 2
    assert school_client.post(reminder_url, headers=coach.headers).json() == result
    after = school_client.get(target_url, headers=owner.headers).json()
    assert after["counts"] == before["counts"]
    assert {item["roster_membership_id"]: item["state"] for item in after["players"]} == {
        first["id"]: None,
        second["id"]: "available",
    }

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert (
            await session.scalar(
                select(func.count(OrganizationNotificationDeliveryOutcome.id)).where(
                    OrganizationNotificationDeliveryOutcome.organization_id == organization["id"],
                    OrganizationNotificationDeliveryOutcome.category == "availability_reminder",
                )
            )
            == 2
        )


async def test_availability_reminder_foreign_target_revocation_and_preferences(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "workflow-reminder-owner@example.com")
    foreign_owner = register_user(school_client, "workflow-reminder-foreign@example.com")
    viewer = register_user(school_client, "workflow-reminder-viewer@example.com")
    scorer = register_user(school_client, "workflow-reminder-scorer@example.com")
    organization = create_club(school_client, owner, "Workflow Reminder Club")
    foreign = create_school(school_client, foreign_owner, "Foreign Reminder School")
    membership = add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    add_membership(school_client, owner, organization["id"], scorer.id, "scorer")
    _player(school_client, owner, organization["id"], "Roster-only reminder player")
    event = _event(school_client, owner, organization["id"], title="Reminder event")
    target_url = _availability_url(organization["id"], "event", event["id"])
    assert (
        school_client.patch(
            target_url,
            json={"response_deadline": None},
            headers=owner.headers,
        ).status_code
        == 200
    )
    assert school_client.post(f"{target_url}/reminders", headers=viewer.headers).status_code == 403
    assert school_client.post(f"{target_url}/reminders", headers=scorer.headers).status_code == 403
    assert (
        school_client.post(
            f"/api/organizations/{foreign['id']}/availability/event/{event['id']}/reminders",
            headers=foreign_owner.headers,
        ).status_code
        == 404
    )
    assert (
        school_client.patch(
            f"/api/organizations/{organization['id']}/notifications/preferences/availability_reminder",
            json={"enabled": False},
            headers=owner.headers,
        ).status_code
        == 200
    )
    suppressed = school_client.post(f"{target_url}/reminders", headers=owner.headers)
    assert suppressed.status_code == 200
    assert suppressed.json()["suppressed_by_preference_count"] == 1
    assert (
        school_client.patch(
            f"/api/organizations/{organization['id']}/notifications/preferences/availability_reminder",
            json={"enabled": True},
            headers=owner.headers,
        ).status_code
        == 200
    )
    assert (
        school_client.post(f"{target_url}/reminders", headers=owner.headers).json()[
            "suppressed_by_preference_count"
        ]
        == 1
    )
    assert (
        school_client.patch(
            f"/api/organizations/{organization['id']}/memberships/{membership['id']}",
            json={"status": "disabled"},
            headers=owner.headers,
        ).status_code
        == 200
    )
    assert school_client.post(f"{target_url}/reminders", headers=viewer.headers).status_code == 404


async def test_workflow_notifications_do_not_add_generic_messaging_or_send_routes(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "workflow-no-generic-messaging@example.com")
    organization = create_school(school_client, owner, "No Generic Messaging School")

    assert (
        school_client.post(
            f"/api/organizations/{organization['id']}/messages",
            json={"body": "direct message"},
            headers=owner.headers,
        ).status_code
        == 404
    )
    assert (
        school_client.post(
            f"/api/organizations/{organization['id']}/notifications/send",
            json={"title": "generic send"},
            headers=owner.headers,
        ).status_code
        == 405
    )
