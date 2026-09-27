from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.services.organization_attendance_service import record_player_attendance
from backend.sql_app.database import get_session_local
from backend.sql_app.models import (
    OrganizationPlayerAttendance,
    OrganizationPlayerAttendanceHistory,
    PlayerProfile,
    SchoolTeamPlayerMembership,
    User,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_club,
    create_school,
    register_user,
)


def _player(client: TestClient, actor: RegisteredUser, organization_id: str, name: str) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/players",
        json={"player_name": name, "year_group": "Year 9"},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _team(client: TestClient, actor: RegisteredUser, organization_id: str, name: str) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/teams",
        json={"name": name},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _assign(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    team_id: str,
    roster_membership_id: str,
) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/teams/{team_id}/players",
        json={"school_player_membership_id": roster_membership_id},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _event(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    *,
    start_at: str = "2020-01-10T09:00:00-04:00",
    participant_scope: str = "organization",
    team_ids: list[str] | None = None,
    roster_membership_ids: list[str] | None = None,
) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/events",
        json={
            "event_type": "training",
            "title": "Training",
            "description": None,
            "start_at": start_at,
            "end_at": None,
            "location": "Main Ground",
            "participant_scope": participant_scope,
            "team_ids": team_ids or [],
            "roster_membership_ids": roster_membership_ids or [],
        },
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _record(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    event_id: str,
    roster_membership_id: str,
    state: str,
):
    return client.put(
        f"/api/organizations/{organization_id}/attendance/events/{event_id}/players/"
        f"{roster_membership_id}",
        json={"state": state},
        headers=actor.headers,
    )


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_school_and_club_attendance_states_history_identity_and_idempotency(
    school_client: TestClient, organization_type: str
) -> None:
    owner = register_user(school_client, f"attendance-{organization_type}@example.com")
    organization = (
        create_school(school_client, owner, "Attendance School")
        if organization_type == "school"
        else create_club(school_client, owner, "Attendance Club")
    )
    player = _player(school_client, owner, organization["id"], "Roster Only Player")
    event = _event(school_client, owner, organization["id"])

    for state in ("present", "absent", "excused"):
        response = _record(
            school_client, owner, organization["id"], event["id"], player["id"], state
        )
        assert response.status_code == 200, response.text
        assert response.json()["state"] == state
        assert response.json()["recorded_by_user_id"] == owner.id
    repeated = _record(
        school_client, owner, organization["id"], event["id"], player["id"], "excused"
    )
    assert repeated.status_code == 200

    history = school_client.get(
        f"/api/organizations/{organization['id']}/attendance/events/{event['id']}/players/"
        f"{player['id']}/history",
        headers=owner.headers,
    )
    assert [item["state"] for item in history.json()["items"]] == [
        "present",
        "absent",
        "excused",
    ]
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert await session.scalar(select(func.count(User.id))) == 1
        profile = await session.get(PlayerProfile, player["player_profile_id"])
        assert profile is not None
        assert await session.scalar(select(func.count(OrganizationPlayerAttendance.id))) == 1
        assert await session.scalar(select(func.count(OrganizationPlayerAttendanceHistory.id))) == 3


async def test_register_unmarked_filters_counts_and_percentage_denominator(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "attendance-metrics@example.com")
    organization = create_school(school_client, owner, "Metrics School")
    players = [
        _player(school_client, owner, organization["id"], name)
        for name in ("Alice", "Bob", "Cara", "Drew")
    ]
    event = _event(school_client, owner, organization["id"])
    for player, state in zip(players[:3], ("present", "absent", "excused"), strict=True):
        assert (
            _record(
                school_client,
                owner,
                organization["id"],
                event["id"],
                player["id"],
                state,
            ).status_code
            == 200
        )
    url = f"/api/organizations/{organization['id']}/attendance/events/{event['id']}"
    register = school_client.get(url, headers=owner.headers)
    assert register.status_code == 200
    assert register.json()["counts"] == {
        "present": 1,
        "absent": 1,
        "excused": 1,
        "unmarked": 1,
        "total": 4,
        "attendance_percentage": 50.0,
    }
    unmarked = school_client.get(url, params={"state": "unmarked"}, headers=owner.headers)
    assert [row["player_name"] for row in unmarked.json()["players"]] == ["Drew"]

    second_event = _event(school_client, owner, organization["id"])
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            second_event["id"],
            players[0]["id"],
            "excused",
        ).status_code
        == 200
    )
    player_summary = school_client.get(
        f"/api/organizations/{organization['id']}/attendance/summary",
        params={"roster_membership_id": players[0]["id"]},
        headers=owner.headers,
    )
    assert player_summary.status_code == 200
    assert player_summary.json()["counts"]["attendance_percentage"] == 100.0
    excused_summary = school_client.get(
        f"/api/organizations/{organization['id']}/attendance/summary",
        params={"roster_membership_id": players[2]["id"]},
        headers=owner.headers,
    )
    assert excused_summary.json()["counts"]["attendance_percentage"] is None


async def test_summary_includes_only_started_attendance_relevant_events(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "attendance-summary-inclusion@example.com")
    organization = create_school(school_client, owner, "Summary Inclusion School")
    team = _team(school_client, owner, organization["id"], "Summary XI")
    players = [
        _player(school_client, owner, organization["id"], name)
        for name in ("Present Player", "Absent Player", "Excused Player")
    ]
    for player in players:
        _assign(school_client, owner, organization["id"], team["id"], player["id"])

    outside_range = _event(
        school_client,
        owner,
        organization["id"],
        start_at="2018-01-10T09:00:00-04:00",
        participant_scope="teams",
        team_ids=[team["id"]],
    )
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            outside_range["id"],
            players[0]["id"],
            "present",
        ).status_code
        == 200
    )

    started = _event(
        school_client,
        owner,
        organization["id"],
        start_at="2020-01-10T09:00:00-04:00",
        participant_scope="teams",
        team_ids=[team["id"]],
    )
    for player, state in zip(players, ("present", "absent", "excused"), strict=True):
        assert (
            _record(
                school_client,
                owner,
                organization["id"],
                started["id"],
                player["id"],
                state,
            ).status_code
            == 200
        )

    cancelled_with_attendance = _event(
        school_client,
        owner,
        organization["id"],
        start_at="2020-02-10T09:00:00-04:00",
        participant_scope="teams",
        team_ids=[team["id"]],
    )
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            cancelled_with_attendance["id"],
            players[0]["id"],
            "excused",
        ).status_code
        == 200
    )
    assert (
        school_client.post(
            f"/api/organizations/{organization['id']}/events/"
            f"{cancelled_with_attendance['id']}/cancel",
            headers=owner.headers,
        ).status_code
        == 200
    )

    cancelled_without_attendance = _event(
        school_client,
        owner,
        organization["id"],
        start_at="2020-03-10T09:00:00-04:00",
        participant_scope="teams",
        team_ids=[team["id"]],
    )
    assert (
        school_client.post(
            f"/api/organizations/{organization['id']}/events/"
            f"{cancelled_without_attendance['id']}/cancel",
            headers=owner.headers,
        ).status_code
        == 200
    )

    _event(
        school_client,
        owner,
        organization["id"],
        start_at="2099-01-10T09:00:00-04:00",
        participant_scope="teams",
        team_ids=[team["id"]],
    )

    summary_url = f"/api/organizations/{organization['id']}/attendance/summary"
    unbounded = school_client.get(summary_url, headers=owner.headers)
    assert unbounded.status_code == 200
    assert unbounded.json()["event_count"] == 3

    bounds = {"from_at": "2019-01-01T00:00:00Z", "to_at": "2021-01-01T00:00:00Z"}
    bounded = school_client.get(summary_url, params=bounds, headers=owner.headers)
    assert bounded.status_code == 200
    assert bounded.json()["event_count"] == 2
    assert bounded.json()["counts"] == {
        "present": 1,
        "absent": 1,
        "excused": 2,
        "unmarked": 2,
        "total": 6,
        "attendance_percentage": 50.0,
    }

    player_summary = school_client.get(
        summary_url,
        params={**bounds, "roster_membership_id": players[0]["id"]},
        headers=owner.headers,
    )
    assert player_summary.status_code == 200
    assert player_summary.json()["event_count"] == 2
    assert player_summary.json()["counts"] == {
        "present": 1,
        "absent": 0,
        "excused": 1,
        "unmarked": 0,
        "total": 2,
        "attendance_percentage": 100.0,
    }

    team_summary = school_client.get(
        summary_url,
        params={**bounds, "team_id": team["id"]},
        headers=owner.headers,
    )
    assert team_summary.status_code == 200
    assert team_summary.json()["event_count"] == 2
    assert team_summary.json()["counts"] == bounded.json()["counts"]

    zero_denominator = school_client.get(
        summary_url,
        params={**bounds, "roster_membership_id": players[2]["id"]},
        headers=owner.headers,
    )
    assert zero_denominator.status_code == 200
    assert zero_denominator.json()["event_count"] == 1
    assert zero_denominator.json()["counts"]["excused"] == 1
    assert zero_denominator.json()["counts"]["attendance_percentage"] is None


async def test_timing_cancellation_unsupported_input_and_session_recovery(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "attendance-timing@example.com")
    organization = create_school(school_client, owner, "Timing School")
    player = _player(school_client, owner, organization["id"], "Timed Player")
    future = _event(school_client, owner, organization["id"], start_at="2099-01-10T09:00:00-04:00")
    before = _record(
        school_client, owner, organization["id"], future["id"], player["id"], "present"
    )
    assert before.status_code == 409
    unsupported = _record(
        school_client, owner, organization["id"], future["id"], player["id"], "unmarked"
    )
    assert unsupported.status_code == 422
    free_text = school_client.put(
        f"/api/organizations/{organization['id']}/attendance/events/{future['id']}/players/"
        f"{player['id']}",
        json={"state": "present", "reason": "Private note"},
        headers=owner.headers,
    )
    assert free_text.status_code == 422

    past = _event(school_client, owner, organization["id"])
    assert (
        _record(
            school_client, owner, organization["id"], past["id"], player["id"], "present"
        ).status_code
        == 200
    )
    cancelled = school_client.post(
        f"/api/organizations/{organization['id']}/events/{past['id']}/cancel",
        headers=owner.headers,
    )
    assert cancelled.status_code == 200
    rejected = _record(school_client, owner, organization["id"], past["id"], player["id"], "absent")
    assert rejected.status_code == 409
    register = school_client.get(
        f"/api/organizations/{organization['id']}/attendance/events/{past['id']}",
        headers=owner.headers,
    )
    assert register.status_code == 200
    assert register.json()["players"][0]["state"] == "present"


async def test_role_matrix_tenant_isolation_and_private_route_only(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "attendance-role-owner@example.com")
    organization = create_school(school_client, owner, "Role School")
    player = _player(school_client, owner, organization["id"], "Role Player")
    event = _event(school_client, owner, organization["id"])
    register_url = f"/api/organizations/{organization['id']}/attendance/events/{event['id']}"
    for role in ("admin", "coach", "scorer", "viewer"):
        member = register_user(school_client, f"attendance-{role}@example.com")
        add_membership(school_client, owner, organization["id"], member.id, role)
        read = school_client.get(register_url, headers=member.headers)
        if role in {"admin", "coach"}:
            assert read.status_code == 200
            assert (
                _record(
                    school_client,
                    member,
                    organization["id"],
                    event["id"],
                    player["id"],
                    "present",
                ).status_code
                == 200
            )
        else:
            assert read.status_code == 403
            assert (
                _record(
                    school_client,
                    member,
                    organization["id"],
                    event["id"],
                    player["id"],
                    "absent",
                ).status_code
                == 403
            )

    foreign_owner = register_user(school_client, "attendance-foreign@example.com")
    foreign = create_club(school_client, foreign_owner, "Foreign Club")
    assert (
        school_client.get(
            f"/api/organizations/{foreign['id']}/attendance/events/{event['id']}",
            headers=foreign_owner.headers,
        ).status_code
        == 404
    )


async def test_normalized_team_and_selected_player_eligibility_and_inactive_rejection(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "attendance-eligibility@example.com")
    organization = create_school(school_client, owner, "Eligibility School")
    team = _team(school_client, owner, organization["id"], "First XI")
    selected = _player(school_client, owner, organization["id"], "Selected")
    unassigned = _player(school_client, owner, organization["id"], "Unassigned")
    assignment = _assign(school_client, owner, organization["id"], team["id"], selected["id"])
    team_event = _event(
        school_client,
        owner,
        organization["id"],
        participant_scope="teams",
        team_ids=[team["id"]],
    )
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            team_event["id"],
            unassigned["id"],
            "present",
        ).status_code
        == 422
    )
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            team_event["id"],
            selected["id"],
            "present",
        ).status_code
        == 200
    )
    team_register = school_client.get(
        f"/api/organizations/{organization['id']}/attendance/events/{team_event['id']}",
        params={"team_id": team["id"]},
        headers=owner.headers,
    )
    assert team_register.status_code == 200
    assert [row["roster_membership_id"] for row in team_register.json()["players"]] == [
        selected["id"]
    ]
    selected_scope_event = _event(
        school_client,
        owner,
        organization["id"],
        participant_scope="selected_players",
        roster_membership_ids=[selected["id"], unassigned["id"]],
    )
    selected_team_register = school_client.get(
        f"/api/organizations/{organization['id']}/attendance/events/"
        f"{selected_scope_event['id']}",
        params={"team_id": team["id"]},
        headers=owner.headers,
    )
    assert selected_team_register.status_code == 200
    assert [row["roster_membership_id"] for row in selected_team_register.json()["players"]] == [
        selected["id"]
    ]
    school_client.delete(
        f"/api/organizations/{organization['id']}/teams/{team['id']}/players/{assignment['id']}",
        headers=owner.headers,
    )
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            team_event["id"],
            selected["id"],
            "absent",
        ).status_code
        == 422
    )
    retained = school_client.get(
        f"/api/organizations/{organization['id']}/attendance/events/{team_event['id']}",
        headers=owner.headers,
    )
    assert retained.status_code == 200
    assert retained.json()["players"][0]["state"] == "present"

    selected_event = _event(
        school_client,
        owner,
        organization["id"],
        participant_scope="selected_players",
        roster_membership_ids=[unassigned["id"]],
    )
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            selected_event["id"],
            selected["id"],
            "present",
        ).status_code
        == 422
    )


async def test_event_delete_retains_attendance_history_and_empty_event_deletes(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "attendance-delete@example.com")
    organization = create_school(school_client, owner, "Retention School")
    player = _player(school_client, owner, organization["id"], "Retained Player")
    retained_event = _event(school_client, owner, organization["id"])
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            retained_event["id"],
            player["id"],
            "present",
        ).status_code
        == 200
    )
    rejected = school_client.delete(
        f"/api/organizations/{organization['id']}/events/{retained_event['id']}",
        headers=owner.headers,
    )
    assert rejected.status_code == 409
    history = school_client.get(
        f"/api/organizations/{organization['id']}/attendance/events/{retained_event['id']}/"
        f"players/{player['id']}/history",
        headers=owner.headers,
    )
    assert history.status_code == 200
    assert len(history.json()["items"]) == 1
    assert (
        school_client.get(
            f"/api/organizations/{organization['id']}/events/{retained_event['id']}",
            headers=owner.headers,
        ).status_code
        == 200
    )

    empty_event = _event(school_client, owner, organization["id"])
    deleted = school_client.delete(
        f"/api/organizations/{organization['id']}/events/{empty_event['id']}",
        headers=owner.headers,
    )
    assert deleted.status_code == 204
    assert (
        school_client.get(
            f"/api/organizations/{organization['id']}/events/{empty_event['id']}",
            headers=owner.headers,
        ).status_code
        == 404
    )


async def test_event_delete_preserves_availability_history_but_removes_empty_target(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "attendance-availability-retention@example.com")
    organization = create_school(school_client, owner, "Availability Retention School")
    player = _player(school_client, owner, organization["id"], "Available Player")
    retained_event = _event(school_client, owner, organization["id"])
    availability = school_client.put(
        f"/api/organizations/{organization['id']}/availability/event/{retained_event['id']}/"
        f"players/{player['id']}",
        json={"state": "available"},
        headers=owner.headers,
    )
    assert availability.status_code == 200
    rejected = school_client.delete(
        f"/api/organizations/{organization['id']}/events/{retained_event['id']}",
        headers=owner.headers,
    )
    assert rejected.status_code == 409
    history = school_client.get(
        f"/api/organizations/{organization['id']}/availability/event/{retained_event['id']}/"
        f"players/{player['id']}/history",
        headers=owner.headers,
    )
    assert history.status_code == 200
    assert len(history.json()["items"]) == 1

    empty_target_event = _event(school_client, owner, organization["id"])
    target = school_client.patch(
        f"/api/organizations/{organization['id']}/availability/event/{empty_target_event['id']}",
        json={"response_deadline": None},
        headers=owner.headers,
    )
    assert target.status_code == 200
    deleted = school_client.delete(
        f"/api/organizations/{organization['id']}/events/{empty_target_event['id']}",
        headers=owner.headers,
    )
    assert deleted.status_code == 204


@pytest.mark.skipif(
    os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="Attendance serialization requires real PostgreSQL",
)
async def test_postgres_concurrent_attendance_keeps_one_current_and_complete_history(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "attendance-concurrency@example.com")
    organization = create_school(school_client, owner, "Concurrency School")
    player = _player(school_client, owner, organization["id"], "Concurrent Player")
    event = _event(school_client, owner, organization["id"])
    session_maker = get_session_local()
    start = asyncio.Event()
    ready = 0
    ready_lock = asyncio.Lock()

    async def update(state: str):
        nonlocal ready
        async with session_maker() as session:
            async with ready_lock:
                ready += 1
                if ready == 2:
                    start.set()
            await start.wait()
            return await record_player_attendance(
                session,
                organization_id=organization["id"],
                event_id=event["id"],
                roster_membership_id=player["id"],
                actor_user_id=owner.id,
                state=state,  # type: ignore[arg-type]
            )

    outcomes = await asyncio.wait_for(
        asyncio.gather(update("present"), update("absent")), timeout=10
    )
    assert {outcome.state for outcome in outcomes} == {"present", "absent"}
    async with session_maker() as session:
        current = list((await session.scalars(select(OrganizationPlayerAttendance))).all())
        history = list(
            (
                await session.scalars(
                    select(OrganizationPlayerAttendanceHistory).order_by(
                        OrganizationPlayerAttendanceHistory.recorded_at,
                        OrganizationPlayerAttendanceHistory.id,
                    )
                )
            ).all()
        )
        assert len(current) == 1
        assert len(history) == 2
        assert current[0].state == history[-1].state
        assert {item.state for item in history} == {"present", "absent"}
        assert await session.scalar(select(func.count(SchoolTeamPlayerMembership.id))) == 0
