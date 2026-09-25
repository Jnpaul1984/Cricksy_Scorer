from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.sql_app.models import OrganizationEvent, PlayerProfile, User
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_club,
    create_school,
    register_user,
)


def _event_payload(
    *,
    title: str = "Training",
    start_at: str = "2099-01-10T09:00:00-04:00",
    participant_scope: str = "organization",
    team_ids: list[str] | None = None,
    roster_membership_ids: list[str] | None = None,
) -> dict:
    return {
        "event_type": "training",
        "title": title,
        "description": "Fielding and fitness",
        "start_at": start_at,
        "end_at": "2099-01-10T11:00:00-04:00" if "01-10" in start_at else None,
        "location": "Main Ground",
        "participant_scope": participant_scope,
        "team_ids": team_ids or [],
        "roster_membership_ids": roster_membership_ids or [],
    }


def _create_event(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    payload: dict | None = None,
) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/events",
        json=payload or _event_payload(),
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_team(
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


def _create_roster_player(
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


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_school_and_club_share_event_crud_cancellation_and_timezone_contract(
    school_client: TestClient,
    organization_type: str,
) -> None:
    owner = register_user(school_client, f"{organization_type}-event-owner@example.com")
    organization = (
        create_school(school_client, owner, "Calendar School")
        if organization_type == "school"
        else create_club(school_client, owner, "Calendar Club")
    )

    created = _create_event(school_client, owner, organization["id"])
    assert created["organization_id"] == organization["id"]
    assert created["event_type"] == "training"
    assert created["participant_scope"] == "organization"
    assert created["start_at"] == "2099-01-10T13:00:00Z"
    assert created["end_at"] == "2099-01-10T15:00:00Z"
    assert created["created_by_user_id"] == owner.id
    assert created["updated_by_user_id"] == owner.id

    exact = school_client.get(
        f"/api/organizations/{organization['id']}/events/{created['id']}",
        headers=owner.headers,
    )
    assert exact.status_code == 200
    updated = school_client.patch(
        f"/api/organizations/{organization['id']}/events/{created['id']}",
        json={"event_type": "other", "title": "Awards Evening", "location": "Hall"},
        headers=owner.headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["event_type"] == "other"
    assert updated.json()["title"] == "Awards Evening"

    cancelled = school_client.post(
        f"/api/organizations/{organization['id']}/events/{created['id']}/cancel",
        headers=owner.headers,
    )
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_by_user_id"] == owner.id
    assert cancelled.json()["cancelled_at"].endswith("Z")
    assert (
        school_client.get(
            f"/api/organizations/{organization['id']}/events", headers=owner.headers
        ).json()["items"]
        == []
    )
    history = school_client.get(
        f"/api/organizations/{organization['id']}/events",
        params={"include_cancelled": "true"},
        headers=owner.headers,
    )
    assert history.status_code == 200
    assert [item["id"] for item in history.json()["items"]] == [created["id"]]
    assert history.json()["items"][0]["status"] == "cancelled"


async def test_team_and_selected_roster_participants_are_tenant_safe_and_login_independent(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "event-participants-owner@example.com")
    foreign_owner = register_user(school_client, "event-participants-foreign@example.com")
    organization = create_school(school_client, owner, "Participants School")
    foreign = create_school(school_client, foreign_owner, "Foreign School")
    first_team = _create_team(school_client, owner, organization["id"], "First XI")
    second_team = _create_team(school_client, owner, organization["id"], "Second XI")
    foreign_team = _create_team(school_client, foreign_owner, foreign["id"], "Foreign XI")
    roster_player = _create_roster_player(
        school_client, owner, organization["id"], "Roster Only Player"
    )
    foreign_player = _create_roster_player(
        school_client, foreign_owner, foreign["id"], "Foreign Player"
    )

    organization_event = _create_event(
        school_client,
        owner,
        organization["id"],
        _event_payload(title="Whole organization"),
    )
    team_event = _create_event(
        school_client,
        owner,
        organization["id"],
        _event_payload(
            title="Squad training",
            participant_scope="teams",
            team_ids=[first_team["id"]],
        ),
    )
    player_event = _create_event(
        school_client,
        owner,
        organization["id"],
        _event_payload(
            title="Specialist clinic",
            participant_scope="selected_players",
            roster_membership_ids=[roster_player["id"]],
        ),
    )
    assert player_event["roster_membership_ids"] == [roster_player["id"]]

    first_calendar = school_client.get(
        f"/api/organizations/{organization['id']}/calendar",
        params={"team_id": first_team["id"]},
        headers=owner.headers,
    )
    second_calendar = school_client.get(
        f"/api/organizations/{organization['id']}/calendar",
        params={"team_id": second_team["id"]},
        headers=owner.headers,
    )
    assert first_calendar.status_code == second_calendar.status_code == 200
    assert {item["source_id"] for item in first_calendar.json()["items"]} == {
        organization_event["id"],
        team_event["id"],
    }
    assert [item["source_id"] for item in second_calendar.json()["items"]] == [
        organization_event["id"]
    ]

    for payload in (
        _event_payload(
            title="Foreign Team",
            participant_scope="teams",
            team_ids=[foreign_team["id"]],
        ),
        _event_payload(
            title="Foreign Player",
            participant_scope="selected_players",
            roster_membership_ids=[foreign_player["id"]],
        ),
    ):
        rejected = school_client.post(
            f"/api/organizations/{organization['id']}/events",
            json=payload,
            headers=owner.headers,
        )
        assert rejected.status_code == 404

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        profile = await session.get(PlayerProfile, roster_player["player_profile_id"])
        users = int(await session.scalar(select(func.count(User.id))) or 0)
        assert profile is not None
        assert profile.player_name == "Roster Only Player"
        assert users == 2


async def test_foreign_event_exact_id_is_not_found(school_client: TestClient) -> None:
    first_owner = register_user(school_client, "event-tenant-a@example.com")
    second_owner = register_user(school_client, "event-tenant-b@example.com")
    first = create_school(school_client, first_owner, "First School")
    second = create_club(school_client, second_owner, "Second Club")
    event = _create_event(school_client, first_owner, first["id"])

    for method, suffix, payload in (
        ("get", "", None),
        ("patch", "", {"title": "Leaked"}),
        ("post", "/cancel", None),
    ):
        response = school_client.request(
            method,
            f"/api/organizations/{second['id']}/events/{event['id']}{suffix}",
            json=payload,
            headers=second_owner.headers,
        )
        assert response.status_code == 404


async def test_event_role_matrix_makes_scorer_and_viewer_read_only(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "event-role-owner@example.com")
    organization = create_school(school_client, owner, "Role School")
    event = _create_event(school_client, owner, organization["id"])
    actors: dict[str, RegisteredUser] = {"owner": owner}
    for role in ("admin", "coach", "scorer", "viewer"):
        actor = register_user(school_client, f"event-role-{role}@example.com")
        add_membership(school_client, owner, organization["id"], actor.id, role)
        actors[role] = actor

    for role in ("owner", "admin", "coach"):
        created = school_client.post(
            f"/api/organizations/{organization['id']}/events",
            json=_event_payload(title=f"{role} event"),
            headers=actors[role].headers,
        )
        assert created.status_code == 201, created.text

    for role in ("scorer", "viewer"):
        listed = school_client.get(
            f"/api/organizations/{organization['id']}/events",
            headers=actors[role].headers,
        )
        assert listed.status_code == 200
        for method, suffix, payload in (
            ("post", "", _event_payload(title="Forbidden")),
            ("patch", f"/{event['id']}", {"title": "Forbidden"}),
            ("post", f"/{event['id']}/cancel", None),
        ):
            response = school_client.request(
                method,
                f"/api/organizations/{organization['id']}/events{suffix}",
                json=payload,
                headers=actors[role].headers,
            )
            assert response.status_code == 403


async def test_upcoming_events_are_deterministic_bounded_and_require_aware_timestamps(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "event-order-owner@example.com")
    organization = create_club(school_client, owner, "Ordering Club")
    _create_event(
        school_client,
        owner,
        organization["id"],
        _event_payload(title="Later", start_at="2099-03-02T10:00:00+00:00"),
    )
    first = _create_event(
        school_client,
        owner,
        organization["id"],
        _event_payload(title="Sooner", start_at="2099-03-01T10:00:00+00:00"),
    )
    _create_event(
        school_client,
        owner,
        organization["id"],
        _event_payload(title="Past", start_at="2020-03-01T10:00:00+00:00"),
    )
    response = school_client.get(
        f"/api/organizations/{organization['id']}/events",
        params={"upcoming": "true", "limit": 1},
        headers=owner.headers,
    )
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert [item["id"] for item in response.json()["items"]] == [first["id"]]

    naive = school_client.post(
        f"/api/organizations/{organization['id']}/events",
        json={**_event_payload(), "start_at": "2099-01-10T09:00:00"},
        headers=owner.headers,
    )
    assert naive.status_code == 422


async def test_calendar_projects_fixture_without_copying_match_truth(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "event-fixture-owner@example.com")
    organization = create_school(school_client, owner, "Fixture School")
    team_a = _create_team(school_client, owner, organization["id"], "Blue XI")
    team_b = _create_team(school_client, owner, organization["id"], "Gold XI")
    competition = school_client.post(
        f"/api/organizations/{organization['id']}/competitions",
        json={"name": "House Cup", "tournament_type": "league"},
        headers=owner.headers,
    )
    assert competition.status_code == 201, competition.text
    competition_id = competition.json()["id"]
    for team in (team_a, team_b):
        entrant = school_client.post(
            f"/api/organizations/{organization['id']}/competitions/{competition_id}/teams",
            json={"team_id": team["id"]},
            headers=owner.headers,
        )
        assert entrant.status_code == 201, entrant.text
    fixture = school_client.post(
        f"/api/organizations/{organization['id']}/competitions/{competition_id}/fixtures",
        json={
            "team_a_id": team_a["id"],
            "team_b_id": team_b["id"],
            "venue": "Main Ground",
            "scheduled_date": "2099-04-01T14:00:00+00:00",
        },
        headers=owner.headers,
    )
    assert fixture.status_code == 201, fixture.text

    calendar = school_client.get(
        f"/api/organizations/{organization['id']}/calendar",
        params={"team_id": team_a["id"], "upcoming": "true"},
        headers=owner.headers,
    )
    assert calendar.status_code == 200, calendar.text
    assert calendar.json()["total"] == 1
    item = calendar.json()["items"][0]
    assert item == {
        "source_type": "fixture",
        "source_id": fixture.json()["id"],
        "title": "Blue XI vs Gold XI",
        "start_at": "2099-04-01T14:00:00Z",
        "end_at": None,
        "location": "Main Ground",
        "status": "scheduled",
        "event_type": None,
        "participant_scope": None,
        "team_ids": [team_a["id"], team_b["id"]],
        "game_id": None,
        "competition_id": competition_id,
    }
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert int(await session.scalar(select(func.count(OrganizationEvent.id))) or 0) == 0


@pytest.mark.parametrize(
    "field",
    [
        "event_type",
        "title",
        "start_at",
        "location",
        "participant_scope",
        "team_ids",
        "roster_membership_ids",
    ],
)
async def test_event_patch_rejects_explicit_null_without_mutation(
    school_client: TestClient,
    field: str,
) -> None:
    owner = register_user(school_client, f"event-null-{field}@example.com")
    organization = create_school(school_client, owner, f"Null {field} School")
    event = _create_event(school_client, owner, organization["id"])

    rejected = school_client.patch(
        f"/api/organizations/{organization['id']}/events/{event['id']}",
        json={field: None},
        headers=owner.headers,
    )
    assert rejected.status_code == 422, rejected.text
    assert "Internal Server Error" not in rejected.text

    unchanged = school_client.get(
        f"/api/organizations/{organization['id']}/events/{event['id']}",
        headers=owner.headers,
    )
    assert unchanged.status_code == 200, unchanged.text
    assert unchanged.json() == event

    usable = school_client.patch(
        f"/api/organizations/{organization['id']}/events/{event['id']}",
        json={"title": "Session Still Usable"},
        headers=owner.headers,
    )
    assert usable.status_code == 200, usable.text
    assert usable.json()["title"] == "Session Still Usable"

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        persisted = await session.get(OrganizationEvent, event["id"])
        assert persisted is not None
        assert persisted.title == "Session Still Usable"


def test_event_patch_allows_clearing_optional_fields(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "event-clear-optional@example.com")
    organization = create_school(school_client, owner, "Clear Optional School")
    event = _create_event(school_client, owner, organization["id"])

    response = school_client.patch(
        f"/api/organizations/{organization['id']}/events/{event['id']}",
        json={"description": None, "end_at": None},
        headers=owner.headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["description"] is None
    assert response.json()["end_at"] is None
    assert response.json()["title"] == event["title"]


def test_event_schema_rejects_invalid_end_and_unsupported_recurrence(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "event-schema-owner@example.com")
    organization = create_school(school_client, owner, "Schema School")
    invalid_end = school_client.post(
        f"/api/organizations/{organization['id']}/events",
        json={
            **_event_payload(),
            "end_at": "2099-01-10T08:00:00-04:00",
        },
        headers=owner.headers,
    )
    recurrence = school_client.post(
        f"/api/organizations/{organization['id']}/events",
        json={**_event_payload(), "recurrence_rule": "FREQ=WEEKLY"},
        headers=owner.headers,
    )
    assert invalid_end.status_code == 422
    assert recurrence.status_code == 422
