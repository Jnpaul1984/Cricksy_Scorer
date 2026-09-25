from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from backend.services.organization_availability_service import record_player_availability
from backend.sql_app.database import get_session_local
from backend.sql_app.models import (
    Fixture,
    OrganizationAvailabilityTarget,
    OrganizationPlayerAvailability,
    OrganizationPlayerAvailabilityHistory,
    PlayerProfile,
    SchoolTeamPlayerMembership,
    Team,
    Tournament,
    User,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_club,
    create_school,
    register_user,
)


def _player(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    name: str,
) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/players",
        json={"player_name": name, "year_group": "Year 9"},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _team(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    name: str,
) -> dict:
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
    title: str = "Training",
    event_type: str = "training",
    participant_scope: str = "organization",
    team_ids: list[str] | None = None,
    roster_membership_ids: list[str] | None = None,
) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/events",
        json={
            "event_type": event_type,
            "title": title,
            "description": None,
            "start_at": "2099-01-10T09:00:00-04:00",
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


def _availability_url(
    organization_id: str,
    target_type: str,
    target_id: str,
) -> str:
    return f"/api/organizations/{organization_id}/availability/{target_type}/{target_id}"


def _record(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    target_type: str,
    target_id: str,
    roster_membership_id: str,
    state: str,
):
    return client.put(
        f"{_availability_url(organization_id, target_type, target_id)}"
        f"/players/{roster_membership_id}",
        json={"state": state},
        headers=actor.headers,
    )


def _fixture(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    first_team_id: str,
    second_team_id: str,
) -> dict:
    competition = client.post(
        f"/api/organizations/{organization_id}/competitions",
        json={"name": "Availability Cup", "tournament_type": "league"},
        headers=actor.headers,
    )
    assert competition.status_code == 201, competition.text
    competition_id = competition.json()["id"]
    for team_id in (first_team_id, second_team_id):
        entrant = client.post(
            f"/api/organizations/{organization_id}/competitions/{competition_id}/teams",
            json={"team_id": team_id},
            headers=actor.headers,
        )
        assert entrant.status_code == 201, entrant.text
    fixture = client.post(
        f"/api/organizations/{organization_id}/competitions/{competition_id}/fixtures",
        json={
            "team_a_id": first_team_id,
            "team_b_id": second_team_id,
            "venue": "Main Ground",
            "scheduled_date": "2099-02-01T14:00:00+00:00",
        },
        headers=actor.headers,
    )
    assert fixture.status_code == 201, fixture.text
    return fixture.json()


@pytest.mark.parametrize("organization_type", ["school", "club"])
@pytest.mark.parametrize("event_type", ["training", "other"])
async def test_event_availability_states_deadline_history_and_no_user_identity(
    school_client: TestClient,
    organization_type: str,
    event_type: str,
) -> None:
    owner = register_user(
        school_client, f"availability-{organization_type}-{event_type}@example.com"
    )
    organization = (
        create_school(school_client, owner, "Availability School")
        if organization_type == "school"
        else create_club(school_client, owner, "Availability Club")
    )
    first = _player(school_client, owner, organization["id"], "Alice Able")
    second = _player(school_client, owner, organization["id"], "Bob Baker")
    event = _event(
        school_client,
        owner,
        organization["id"],
        event_type=event_type,
        title=f"{event_type.title()} Session",
    )
    url = _availability_url(organization["id"], "event", event["id"])

    deadline = school_client.patch(
        url,
        json={"response_deadline": "2020-01-01T08:30:00-04:00"},
        headers=owner.headers,
    )
    assert deadline.status_code == 200, deadline.text
    assert deadline.json()["response_deadline"] == "2020-01-01T12:30:00Z"
    assert deadline.json()["deadline_passed"] is True

    for state in ("available", "unavailable", "maybe"):
        response = _record(
            school_client,
            owner,
            organization["id"],
            "event",
            event["id"],
            first["id"],
            state,
        )
        assert response.status_code == 200, response.text
        assert response.json()["state"] == state
        assert response.json()["recorded_by_user_id"] == owner.id
        assert response.json()["recorded_after_deadline"] is True

    repeated = _record(
        school_client,
        owner,
        organization["id"],
        "event",
        event["id"],
        first["id"],
        "maybe",
    )
    assert repeated.status_code == 200

    summary = school_client.get(url, headers=owner.headers)
    assert summary.status_code == 200, summary.text
    assert summary.json()["counts"] == {
        "available": 0,
        "unavailable": 0,
        "maybe": 1,
        "no_response": 1,
        "total": 2,
    }
    assert [row["player_name"] for row in summary.json()["players"]] == [
        "Alice Able",
        "Bob Baker",
    ]
    unanswered = school_client.get(url, params={"state": "no_response"}, headers=owner.headers)
    assert unanswered.status_code == 200
    assert unanswered.json()["total"] == 1
    assert unanswered.json()["players"][0]["roster_membership_id"] == second["id"]

    history = school_client.get(f"{url}/players/{first['id']}/history", headers=owner.headers)
    assert history.status_code == 200, history.text
    assert [item["state"] for item in history.json()["items"]] == [
        "available",
        "unavailable",
        "maybe",
    ]
    assert all(item["recorded_by_user_id"] == owner.id for item in history.json()["items"])
    assert all(item["recorded_after_deadline"] is True for item in history.json()["items"])

    cleared = school_client.patch(
        url,
        json={"response_deadline": None},
        headers=owner.headers,
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["response_deadline"] is None
    assert cleared.json()["deadline_passed"] is False

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        profile = await session.get(PlayerProfile, first["player_profile_id"])
        user_count = int(await session.scalar(select(func.count(User.id))) or 0)
        history_count = int(
            await session.scalar(select(func.count(OrganizationPlayerAvailabilityHistory.id))) or 0
        )
        assert profile is not None
        assert user_count == 1
        assert history_count == 3


async def test_availability_rejects_unsupported_fields_states_and_keeps_session_usable(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "availability-validation@example.com")
    organization = create_school(school_client, owner, "Validation School")
    player = _player(school_client, owner, organization["id"], "Valid Player")
    event = _event(school_client, owner, organization["id"])
    url = _availability_url(organization["id"], "event", event["id"])

    unsupported = _record(
        school_client,
        owner,
        organization["id"],
        "event",
        event["id"],
        player["id"],
        "unknown",
    )
    comment = school_client.put(
        f"{url}/players/{player['id']}",
        json={"state": "available", "reason": "private detail"},
        headers=owner.headers,
    )
    naive_deadline = school_client.patch(
        url,
        json={"response_deadline": "2099-01-01T10:00:00"},
        headers=owner.headers,
    )
    assert unsupported.status_code == comment.status_code == naive_deadline.status_code == 422
    assert "Internal Server Error" not in unsupported.text + comment.text + naive_deadline.text

    valid = _record(
        school_client,
        owner,
        organization["id"],
        "event",
        event["id"],
        player["id"],
        "available",
    )
    assert valid.status_code == 200, valid.text
    assert school_client.get(url, headers=owner.headers).status_code == 200


async def test_role_matrix_and_non_member_denial(school_client: TestClient) -> None:
    owner = register_user(school_client, "availability-role-owner@example.com")
    organization = create_school(school_client, owner, "Role School")
    player = _player(school_client, owner, organization["id"], "Role Player")
    event = _event(school_client, owner, organization["id"])
    url = _availability_url(organization["id"], "event", event["id"])
    actors: dict[str, RegisteredUser] = {"owner": owner}
    for role in ("admin", "coach", "scorer", "viewer"):
        actor = register_user(school_client, f"availability-{role}@example.com")
        add_membership(school_client, owner, organization["id"], actor.id, role)
        actors[role] = actor

    for role, state in (("owner", "available"), ("admin", "maybe"), ("coach", "unavailable")):
        response = _record(
            school_client,
            actors[role],
            organization["id"],
            "event",
            event["id"],
            player["id"],
            state,
        )
        assert response.status_code == 200, response.text
        assert response.json()["recorded_by_user_id"] == actors[role].id

    for role in ("scorer", "viewer"):
        assert school_client.get(url, headers=actors[role].headers).status_code == 200
        denied = _record(
            school_client,
            actors[role],
            organization["id"],
            "event",
            event["id"],
            player["id"],
            "available",
        )
        assert denied.status_code == 403
        deadline = school_client.patch(
            url,
            json={"response_deadline": "2099-01-01T10:00:00+00:00"},
            headers=actors[role].headers,
        )
        assert deadline.status_code == 403

    history = school_client.get(
        f"{url}/players/{player['id']}/history", headers=actors["viewer"].headers
    )
    assert history.status_code == 200
    assert [item["recorded_by_user_id"] for item in history.json()["items"]] == [
        owner.id,
        actors["admin"].id,
        actors["coach"].id,
    ]

    outsider = register_user(school_client, "availability-outsider@example.com")
    assert school_client.get(url, headers=outsider.headers).status_code == 404


async def test_event_eligibility_tenant_isolation_and_inactive_memberships(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "availability-eligibility@example.com")
    foreign_owner = register_user(school_client, "availability-foreign@example.com")
    organization = create_school(school_client, owner, "Eligibility School")
    foreign = create_club(school_client, foreign_owner, "Foreign Club")
    team = _team(school_client, owner, organization["id"], "First XI")
    eligible = _player(school_client, owner, organization["id"], "Eligible Player")
    unassigned = _player(school_client, owner, organization["id"], "Unassigned Player")
    selected = _player(school_client, owner, organization["id"], "Selected Player")
    foreign_player = _player(school_client, foreign_owner, foreign["id"], "Foreign Player")
    assignment = _assign(school_client, owner, organization["id"], team["id"], eligible["id"])
    team_event = _event(
        school_client,
        owner,
        organization["id"],
        participant_scope="teams",
        team_ids=[team["id"]],
    )
    selected_event = _event(
        school_client,
        owner,
        organization["id"],
        title="Selected clinic",
        participant_scope="selected_players",
        roster_membership_ids=[selected["id"]],
    )

    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            "event",
            team_event["id"],
            eligible["id"],
            "available",
        ).status_code
        == 200
    )
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            "event",
            team_event["id"],
            unassigned["id"],
            "available",
        ).status_code
        == 422
    )
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            "event",
            selected_event["id"],
            selected["id"],
            "maybe",
        ).status_code
        == 200
    )
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            "event",
            selected_event["id"],
            eligible["id"],
            "maybe",
        ).status_code
        == 422
    )
    cross_player = _record(
        school_client,
        owner,
        organization["id"],
        "event",
        team_event["id"],
        foreign_player["id"],
        "available",
    )
    assert cross_player.status_code == 404
    foreign_event = _event(school_client, foreign_owner, foreign["id"])
    assert (
        school_client.get(
            _availability_url(organization["id"], "event", foreign_event["id"]),
            headers=owner.headers,
        ).status_code
        == 404
    )

    deactivated = school_client.delete(
        f"/api/organizations/{organization['id']}/teams/{team['id']}/players/{assignment['id']}",
        headers=owner.headers,
    )
    assert deactivated.status_code == 204
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            "event",
            team_event["id"],
            eligible["id"],
            "unavailable",
        ).status_code
        == 422
    )
    inactive_master = school_client.patch(
        f"/api/organizations/{organization['id']}/players/{selected['id']}",
        json={"status": "inactive"},
        headers=owner.headers,
    )
    assert inactive_master.status_code == 200, inactive_master.text
    assert (
        _record(
            school_client,
            owner,
            organization["id"],
            "event",
            selected_event["id"],
            selected["id"],
            "available",
        ).status_code
        == 422
    )

    overview = school_client.get(
        _availability_url(organization["id"], "event", team_event["id"]),
        params={"team_id": team["id"]},
        headers=owner.headers,
    )
    assert overview.status_code == 200
    assert overview.json()["counts"]["total"] == 0


async def test_fixture_availability_uses_only_normalized_active_team_rosters(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "availability-fixture@example.com")
    organization = create_club(school_client, owner, "Fixture Club")
    first_team = _team(school_client, owner, organization["id"], "First XI")
    second_team = _team(school_client, owner, organization["id"], "Second XI")
    first_player = _player(school_client, owner, organization["id"], "First Player")
    second_player = _player(school_client, owner, organization["id"], "Second Player")
    outsider = _player(school_client, owner, organization["id"], "Roster Only")
    _assign(school_client, owner, organization["id"], first_team["id"], first_player["id"])
    _assign(school_client, owner, organization["id"], second_team["id"], second_player["id"])
    fixture = _fixture(
        school_client,
        owner,
        organization["id"],
        first_team["id"],
        second_team["id"],
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored_team = await session.get(Team, first_team["id"])
        assert stored_team is not None
        stored_team.players = [{"id": "legacy-name", "name": "Roster Only"}]
        await session.commit()

    first_response = _record(
        school_client,
        owner,
        organization["id"],
        "fixture",
        fixture["id"],
        first_player["id"],
        "available",
    )
    second_response = _record(
        school_client,
        owner,
        organization["id"],
        "fixture",
        fixture["id"],
        second_player["id"],
        "maybe",
    )
    rejected = _record(
        school_client,
        owner,
        organization["id"],
        "fixture",
        fixture["id"],
        outsider["id"],
        "available",
    )
    assert first_response.status_code == second_response.status_code == 200
    assert rejected.status_code == 422

    summary = school_client.get(
        _availability_url(organization["id"], "fixture", fixture["id"]),
        headers=owner.headers,
    )
    assert summary.status_code == 200, summary.text
    assert summary.json()["counts"] == {
        "available": 1,
        "unavailable": 0,
        "maybe": 1,
        "no_response": 0,
        "total": 2,
    }
    assert {row["roster_membership_id"] for row in summary.json()["players"]} == {
        first_player["id"],
        second_player["id"],
    }

    filtered = school_client.get(
        _availability_url(organization["id"], "fixture", fixture["id"]),
        params={"team_id": first_team["id"], "state": "available"},
        headers=owner.headers,
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["players"][0]["roster_membership_id"] == first_player["id"]

    async with session_maker() as session:
        competition = await session.scalar(
            select(Tournament).where(Tournament.organization_id == organization["id"])
        )
        assert competition is not None
        unsafe_fixture = Fixture(
            tournament_id=competition.id,
            team_a_name="Legacy A",
            team_b_name="Legacy B",
            team_a_id=None,
            team_b_id=None,
            scheduled_date=None,
            status="scheduled",
        )
        session.add(unsafe_fixture)
        await session.commit()
        await session.refresh(unsafe_fixture)
        unsafe_fixture_id = unsafe_fixture.id
    unsafe = school_client.get(
        _availability_url(organization["id"], "fixture", unsafe_fixture_id),
        headers=owner.headers,
    )
    assert unsafe.status_code == 422
    assert unsafe.json() == {
        "detail": "Fixture availability requires two normalized organization Teams"
    }

    foreign_owner = register_user(school_client, "availability-fixture-foreign@example.com")
    foreign = create_school(school_client, foreign_owner, "Foreign Fixture School")
    foreign_exact = school_client.get(
        _availability_url(foreign["id"], "fixture", fixture["id"]),
        headers=foreign_owner.headers,
    )
    assert foreign_exact.status_code == 404


@pytest.mark.skipif(
    os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="Availability serialization requires real PostgreSQL",
)
async def test_postgres_concurrent_updates_leave_one_current_state_and_immutable_history(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "availability-concurrency@example.com")
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
            return await record_player_availability(
                session,
                organization_id=organization["id"],
                target_type="event",
                target_id=event["id"],
                roster_membership_id=player["id"],
                actor_user_id=owner.id,
                state=state,  # type: ignore[arg-type]
            )

    outcomes = await asyncio.wait_for(
        asyncio.gather(update("available"), update("unavailable")), timeout=10
    )
    assert {outcome.state for outcome in outcomes} == {"available", "unavailable"}

    async with session_maker() as session:
        current = list((await session.scalars(select(OrganizationPlayerAvailability))).all())
        history = list(
            (
                await session.scalars(
                    select(OrganizationPlayerAvailabilityHistory).order_by(
                        OrganizationPlayerAvailabilityHistory.recorded_at,
                        OrganizationPlayerAvailabilityHistory.id,
                    )
                )
            ).all()
        )
        assert len(current) == 1
        assert len(history) == 2
        assert current[0].state == history[-1].state
        assert {item.state for item in history} == {"available", "unavailable"}

        team_memberships = int(
            await session.scalar(select(func.count(SchoolTeamPlayerMembership.id))) or 0
        )
        assert team_memberships == 0


@pytest.mark.skipif(
    os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="Composite availability tenancy requires real PostgreSQL",
)
async def test_postgres_composite_target_fk_rejects_cross_tenant_event_reference(
    school_client: TestClient,
) -> None:
    first_owner = register_user(school_client, "availability-composite-a@example.com")
    second_owner = register_user(school_client, "availability-composite-b@example.com")
    first = create_school(school_client, first_owner, "Composite A")
    second = create_club(school_client, second_owner, "Composite B")
    event = _event(school_client, first_owner, first["id"])
    session_maker = get_session_local()

    async with session_maker() as session:
        session.add(
            OrganizationAvailabilityTarget(
                organization_id=second["id"],
                target_type="event",
                organization_event_id=event["id"],
                fixture_id=None,
                fixture_tournament_id=None,
                response_deadline=None,
                created_by_user_id=second_owner.id,
                updated_by_user_id=second_owner.id,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()
        assert await session.scalar(select(func.count(OrganizationAvailabilityTarget.id))) == 0
