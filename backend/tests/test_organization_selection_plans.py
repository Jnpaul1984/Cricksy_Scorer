from __future__ import annotations

import asyncio
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, insert, select, update
from sqlalchemy.exc import IntegrityError

from backend.api.schemas.organization_selection_plans import (
    OrganizationSelectionPlanCreate,
    OrganizationSelectionPlanUpdate,
)
from backend.services.organization_selection_plan_service import (
    OrganizationSelectionPlanServiceError,
    create_or_open_selection_plan,
    update_selection_plan,
)
from backend.sql_app.database import get_session_local
from backend.sql_app.models import (
    Fixture,
    OrganizationAvailabilityTarget,
    OrganizationSelectionPlan,
    OrganizationSelectionPlanPlayer,
    PlayerProfile,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
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


def _player(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    name: str,
) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/players",
        json={"player_name": name, "year_group": "Year 10"},
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


def _fixture(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    first_team_id: str,
    second_team_id: str,
    *,
    name: str = "Selection Cup",
) -> dict:
    competition = client.post(
        f"/api/organizations/{organization_id}/competitions",
        json={"name": name, "tournament_type": "league"},
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
    response = client.post(
        f"/api/organizations/{organization_id}/competitions/{competition_id}/fixtures",
        json={
            "team_a_id": first_team_id,
            "team_b_id": second_team_id,
            "scheduled_date": "2099-04-01T14:00:00+00:00",
        },
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_plan(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    team_id: str,
    fixture_id: str,
):
    return client.post(
        f"/api/organizations/{organization_id}/selection-plans",
        json={"team_id": team_id, "fixture_id": fixture_id},
        headers=actor.headers,
    )


def _lookup_plan(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    team_id: str,
    fixture_id: str,
):
    return client.get(
        f"/api/organizations/{organization_id}/selection-plans",
        params={"team_id": team_id, "fixture_id": fixture_id},
        headers=actor.headers,
    )


def _update_plan(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    plan_id: str,
    payload: dict,
):
    return client.patch(
        f"/api/organizations/{organization_id}/selection-plans/{plan_id}",
        json=payload,
        headers=actor.headers,
    )


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_shared_school_club_draft_creation_candidates_and_no_user_identity(
    school_client: TestClient,
    organization_type: str,
) -> None:
    owner = register_user(school_client, f"selection-{organization_type}@example.com")
    organization = (
        create_school(school_client, owner, "Selection School")
        if organization_type == "school"
        else create_club(school_client, owner, "Selection Club")
    )
    team = _team(school_client, owner, organization["id"], "First XI")
    opponent = _team(school_client, owner, organization["id"], "Second XI")
    player = _player(school_client, owner, organization["id"], "Roster Only Player")
    _assign(school_client, owner, organization["id"], team["id"], player["id"])
    fixture = _fixture(
        school_client,
        owner,
        organization["id"],
        team["id"],
        opponent["id"],
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored_team = await session.get(Team, team["id"])
        assert stored_team is not None
        stored_team.players = [{"id": "legacy-only", "name": "Not Authority"}]
        await session.commit()

    created = _create_plan(school_client, owner, organization["id"], team["id"], fixture["id"])
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["organization_id"] == organization["id"]
    assert body["status"] == "draft"
    assert body["revision"] == 1
    assert body["xi_roster_membership_ids"] == []
    assert body["reserve_roster_membership_ids"] == []

    candidates = school_client.get(
        f"/api/organizations/{organization['id']}/selection-plans/{body['id']}/candidates",
        headers=owner.headers,
    )
    assert candidates.status_code == 200, candidates.text
    assert candidates.json()["candidates"] == [
        {
            "roster_membership_id": player["id"],
            "player_profile_id": player["player_profile_id"],
            "player_name": "Roster Only Player",
            "eligible": True,
            "availability_state": None,
        }
    ]
    assert "Not Authority" not in candidates.text

    async with session_maker() as session:
        assert await session.scalar(select(func.count(User.id))) == 1
        assert await session.get(PlayerProfile, player["player_profile_id"]) is not None


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_candidates_compose_fixture_availability_without_materializing_reads(
    school_client: TestClient,
    organization_type: str,
) -> None:
    owner = register_user(
        school_client,
        f"selection-availability-{organization_type}@example.com",
    )
    organization = (
        create_school(school_client, owner, "Availability Selection School")
        if organization_type == "school"
        else create_club(school_client, owner, "Availability Selection Club")
    )
    team = _team(school_client, owner, organization["id"], "Availability XI")
    opponent = _team(school_client, owner, organization["id"], "Availability Opponent")
    players = [
        _player(school_client, owner, organization["id"], name)
        for name in ("Available Player", "Unavailable Player", "Maybe Player", "No Response Player")
    ]
    assignments = [
        _assign(school_client, owner, organization["id"], team["id"], player["id"])
        for player in players
    ]
    fixture = _fixture(
        school_client,
        owner,
        organization["id"],
        team["id"],
        opponent["id"],
        name=f"{organization_type.title()} Availability Cup",
    )
    plan = _create_plan(
        school_client,
        owner,
        organization["id"],
        team["id"],
        fixture["id"],
    ).json()
    candidates_url = (
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}/candidates"
    )

    first_read = school_client.get(candidates_url, headers=owner.headers)
    assert first_read.status_code == 200, first_read.text
    assert {candidate["availability_state"] for candidate in first_read.json()["candidates"]} == {
        None
    }
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert (
            await session.scalar(
                select(func.count(OrganizationAvailabilityTarget.id)).where(
                    OrganizationAvailabilityTarget.organization_id == organization["id"]
                )
            )
            == 0
        )

    for player, state in zip(players[:3], ("available", "unavailable", "maybe"), strict=True):
        recorded = school_client.put(
            f"/api/organizations/{organization['id']}/availability/fixture/{fixture['id']}"
            f"/players/{player['id']}",
            json={"state": state},
            headers=owner.headers,
        )
        assert recorded.status_code == 200, recorded.text

    composed = school_client.get(candidates_url, headers=owner.headers)
    assert composed.status_code == 200, composed.text
    assert {
        candidate["player_name"]: candidate["availability_state"]
        for candidate in composed.json()["candidates"]
    } == {
        "Available Player": "available",
        "Unavailable Player": "unavailable",
        "Maybe Player": "maybe",
        "No Response Player": None,
    }

    deactivate = school_client.delete(
        f"/api/organizations/{organization['id']}/teams/{team['id']}"
        f"/players/{assignments[0]['id']}",
        headers=owner.headers,
    )
    assert deactivate.status_code == 204, deactivate.text
    after_inactive = school_client.get(candidates_url, headers=owner.headers)
    assert after_inactive.status_code == 200, after_inactive.text
    assert "Available Player" not in {
        candidate["player_name"] for candidate in after_inactive.json()["candidates"]
    }

    advisory_update = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {
            "expected_revision": 1,
            "xi_roster_membership_ids": [players[1]["id"], players[2]["id"]],
            "reserve_roster_membership_ids": [players[3]["id"]],
        },
    )
    assert advisory_update.status_code == 200, advisory_update.text
    assert advisory_update.json()["revision"] == 2

    ineligible_update = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {
            "expected_revision": 2,
            "xi_roster_membership_ids": [players[0]["id"]],
            "reserve_roster_membership_ids": [],
        },
    )
    assert ineligible_update.status_code == 422


async def test_read_only_roles_discover_existing_plan_by_team_fixture_context(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "selection-lookup-owner@example.com")
    scorer = register_user(school_client, "selection-lookup-scorer@example.com")
    viewer = register_user(school_client, "selection-lookup-viewer@example.com")
    foreign_owner = register_user(school_client, "selection-lookup-foreign@example.com")
    organization = create_school(school_client, owner, "Lookup School")
    add_membership(school_client, owner, organization["id"], scorer.id, "scorer")
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")

    team = _team(school_client, owner, organization["id"], "Lookup XI")
    opponent = _team(school_client, owner, organization["id"], "Lookup Opponent")
    fixture = _fixture(
        school_client,
        owner,
        organization["id"],
        team["id"],
        opponent["id"],
        name="Lookup Cup",
    )
    created = _create_plan(
        school_client,
        owner,
        organization["id"],
        team["id"],
        fixture["id"],
    )
    assert created.status_code == 201, created.text
    plan = created.json()

    for actor in (scorer, viewer):
        discovered = _lookup_plan(
            school_client,
            actor,
            organization["id"],
            team["id"],
            fixture["id"],
        )
        assert discovered.status_code == 200, discovered.text
        assert discovered.json()["id"] == plan["id"]

    by_id = school_client.get(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}",
        headers=viewer.headers,
    )
    assert by_id.status_code == 200, by_id.text
    assert by_id.json()["id"] == plan["id"]

    missing_team = _team(school_client, owner, organization["id"], "Missing Plan XI")
    missing_opponent = _team(
        school_client,
        owner,
        organization["id"],
        "Missing Plan Opponent",
    )
    missing_fixture = _fixture(
        school_client,
        owner,
        organization["id"],
        missing_team["id"],
        missing_opponent["id"],
        name="Missing Plan Cup",
    )
    for actor in (scorer, viewer):
        denied_create = _create_plan(
            school_client,
            actor,
            organization["id"],
            missing_team["id"],
            missing_fixture["id"],
        )
        assert denied_create.status_code == 403

    missing = _lookup_plan(
        school_client,
        viewer,
        organization["id"],
        missing_team["id"],
        missing_fixture["id"],
    )
    assert missing.status_code == 404
    assert missing.json()["detail"] == "Selection plan not found"

    foreign = create_club(school_client, foreign_owner, "Foreign Lookup Club")
    foreign_team = _team(school_client, foreign_owner, foreign["id"], "Foreign Lookup XI")
    foreign_opponent = _team(
        school_client,
        foreign_owner,
        foreign["id"],
        "Foreign Lookup Opponent",
    )
    foreign_fixture = _fixture(
        school_client,
        foreign_owner,
        foreign["id"],
        foreign_team["id"],
        foreign_opponent["id"],
        name="Foreign Lookup Cup",
    )
    foreign_contexts = (
        (foreign_team["id"], fixture["id"]),
        (team["id"], foreign_fixture["id"]),
        (foreign_team["id"], foreign_fixture["id"]),
    )
    for foreign_team_id, foreign_fixture_id in foreign_contexts:
        hidden = _lookup_plan(
            school_client,
            scorer,
            organization["id"],
            foreign_team_id,
            foreign_fixture_id,
        )
        assert hidden.status_code == 404
        assert hidden.json()["detail"] == "Selection plan not found"


async def test_aggregate_update_revision_idempotency_roles_and_draft_rules(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "selection-rules-owner@example.com")
    organization = create_school(school_client, owner, "Rules School")
    team = _team(school_client, owner, organization["id"], "Rules XI")
    opponent = _team(school_client, owner, organization["id"], "Rules Opponent")
    players = [
        _player(school_client, owner, organization["id"], f"Player {index:02d}")
        for index in range(1, 14)
    ]
    for player in players:
        _assign(school_client, owner, organization["id"], team["id"], player["id"])
    fixture = _fixture(
        school_client,
        owner,
        organization["id"],
        team["id"],
        opponent["id"],
    )
    plan = _create_plan(school_client, owner, organization["id"], team["id"], fixture["id"]).json()

    actors: dict[str, RegisteredUser] = {"owner": owner}
    for role in ("admin", "coach", "scorer", "viewer"):
        actor = register_user(school_client, f"selection-{role}@example.com")
        add_membership(school_client, owner, organization["id"], actor.id, role)
        actors[role] = actor

    first = _update_plan(
        school_client,
        actors["coach"],
        organization["id"],
        plan["id"],
        {
            "expected_revision": 1,
            "xi_roster_membership_ids": [players[0]["id"], players[1]["id"]],
            "reserve_roster_membership_ids": [players[2]["id"]],
            "captain_roster_membership_id": players[0]["id"],
            "wicketkeeper_roster_membership_id": players[1]["id"],
        },
    )
    assert first.status_code == 200, first.text
    assert first.json()["revision"] == 2
    assert first.json()["updated_by_user_id"] == actors["coach"].id

    repeated = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {
            "expected_revision": 1,
            "xi_roster_membership_ids": [players[1]["id"], players[0]["id"]],
            "reserve_roster_membership_ids": [players[2]["id"]],
            "captain_roster_membership_id": players[0]["id"],
            "wicketkeeper_roster_membership_id": players[1]["id"],
        },
    )
    assert repeated.status_code == 200, repeated.text
    assert repeated.json()["revision"] == 2

    partial = _update_plan(
        school_client,
        actors["admin"],
        organization["id"],
        plan["id"],
        {"expected_revision": 2, "captain_roster_membership_id": None},
    )
    assert partial.status_code == 200, partial.text
    assert partial.json()["revision"] == 3
    assert partial.json()["captain_roster_membership_id"] is None
    assert len(partial.json()["xi_roster_membership_ids"]) == 2

    for role in ("scorer", "viewer"):
        read = school_client.get(
            f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}",
            headers=actors[role].headers,
        )
        assert read.status_code == 200
        denied = _update_plan(
            school_client,
            actors[role],
            organization["id"],
            plan["id"],
            {"expected_revision": 3, "reserve_roster_membership_ids": []},
        )
        assert denied.status_code == 403

    outsider = register_user(school_client, "selection-outsider@example.com")
    hidden = school_client.get(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}",
        headers=outsider.headers,
    )
    assert hidden.status_code == 404

    too_many = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {
            "expected_revision": 3,
            "xi_roster_membership_ids": [player["id"] for player in players[:12]],
        },
    )
    duplicate_xi = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {
            "expected_revision": 3,
            "xi_roster_membership_ids": [players[0]["id"], players[0]["id"]],
        },
    )
    duplicate_reserve = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {
            "expected_revision": 3,
            "reserve_roster_membership_ids": [players[2]["id"], players[2]["id"]],
        },
    )
    overlap = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {
            "expected_revision": 3,
            "xi_roster_membership_ids": [players[0]["id"]],
            "reserve_roster_membership_ids": [players[0]["id"]],
        },
    )
    captain_outside = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {"expected_revision": 3, "captain_roster_membership_id": players[3]["id"]},
    )
    wicketkeeper_outside = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {"expected_revision": 3, "wicketkeeper_roster_membership_id": players[3]["id"]},
    )
    null_xi = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {"expected_revision": 3, "xi_roster_membership_ids": None},
    )
    assert all(
        response.status_code == 422
        for response in (
            too_many,
            duplicate_xi,
            duplicate_reserve,
            overlap,
            captain_outside,
            wicketkeeper_outside,
            null_xi,
        )
    )
    after = school_client.get(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}",
        headers=owner.headers,
    )
    assert after.status_code == 200
    assert after.json()["revision"] == 3


async def test_tenant_fixture_team_and_active_normalized_roster_enforcement(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "selection-tenant-a@example.com")
    foreign_owner = register_user(school_client, "selection-tenant-b@example.com")
    organization = create_school(school_client, owner, "Tenant A")
    foreign = create_club(school_client, foreign_owner, "Tenant B")
    team = _team(school_client, owner, organization["id"], "Tenant A XI")
    opponent = _team(school_client, owner, organization["id"], "Tenant A Opponent")
    unrepresented = _team(school_client, owner, organization["id"], "Not In Fixture")
    foreign_team = _team(school_client, foreign_owner, foreign["id"], "Foreign XI")
    foreign_opponent = _team(school_client, foreign_owner, foreign["id"], "Foreign Opponent")
    fixture = _fixture(school_client, owner, organization["id"], team["id"], opponent["id"])
    foreign_fixture = _fixture(
        school_client,
        foreign_owner,
        foreign["id"],
        foreign_team["id"],
        foreign_opponent["id"],
        name="Foreign Cup",
    )

    assert (
        _create_plan(
            school_client,
            owner,
            organization["id"],
            foreign_team["id"],
            fixture["id"],
        ).status_code
        == 404
    )
    assert (
        _create_plan(
            school_client,
            owner,
            organization["id"],
            team["id"],
            foreign_fixture["id"],
        ).status_code
        == 404
    )
    not_represented = _create_plan(
        school_client,
        owner,
        organization["id"],
        unrepresented["id"],
        fixture["id"],
    )
    assert not_represented.status_code == 422

    player = _player(school_client, owner, organization["id"], "Eligible")
    unassigned = _player(school_client, owner, organization["id"], "Unassigned")
    inactive = _player(school_client, owner, organization["id"], "Inactive")
    inactive_master = _player(school_client, owner, organization["id"], "Inactive Master Roster")
    assignment = _assign(school_client, owner, organization["id"], team["id"], player["id"])
    inactive_assignment = _assign(
        school_client, owner, organization["id"], team["id"], inactive["id"]
    )
    _assign(
        school_client,
        owner,
        organization["id"],
        team["id"],
        inactive_master["id"],
    )
    plan = _create_plan(school_client, owner, organization["id"], team["id"], fixture["id"]).json()
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        team_membership = await session.get(SchoolTeamPlayerMembership, inactive_assignment["id"])
        assert team_membership is not None
        team_membership.status = "inactive"
        master_membership = await session.get(SchoolPlayerMembership, inactive_master["id"])
        assert master_membership is not None
        master_membership.status = "inactive"
        ambiguous_fixture = Fixture(
            tournament_id=fixture["tournament_id"],
            team_a_name=team["name"],
            team_b_name="External Opponent",
            team_a_id=team["id"],
            team_b_id=None,
            status="scheduled",
        )
        session.add(ambiguous_fixture)
        await session.commit()
        await session.refresh(ambiguous_fixture)
        ambiguous_fixture_id = ambiguous_fixture.id

    ambiguous = _create_plan(
        school_client,
        owner,
        organization["id"],
        team["id"],
        ambiguous_fixture_id,
    )
    assert ambiguous.status_code == 422
    assert ambiguous.json()["detail"] == "Fixture must use two normalized organization Teams"

    valid = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {"expected_revision": 1, "xi_roster_membership_ids": [player["id"]]},
    )
    assert valid.status_code == 200
    for candidate_id in (unassigned["id"], inactive["id"], inactive_master["id"]):
        rejected = _update_plan(
            school_client,
            owner,
            organization["id"],
            plan["id"],
            {"expected_revision": 2, "reserve_roster_membership_ids": [candidate_id]},
        )
        assert rejected.status_code == 422
    assert assignment["school_player_membership_id"] == player["id"]

    hidden = school_client.get(
        f"/api/organizations/{foreign['id']}/selection-plans/{plan['id']}",
        headers=foreign_owner.headers,
    )
    assert hidden.status_code == 404


async def test_one_plan_identity_and_history_free_fixture_competition_cleanup(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "selection-lifecycle@example.com")
    organization = create_school(school_client, owner, "Lifecycle School")
    team = _team(school_client, owner, organization["id"], "Lifecycle XI")
    opponent = _team(school_client, owner, organization["id"], "Lifecycle Opponent")
    fixture = _fixture(school_client, owner, organization["id"], team["id"], opponent["id"])
    first = _create_plan(school_client, owner, organization["id"], team["id"], fixture["id"])
    second = _create_plan(school_client, owner, organization["id"], team["id"], fixture["id"])
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]

    fixture_url = (
        f"/api/organizations/{organization['id']}/competitions/{fixture['tournament_id']}"
        f"/fixtures/{fixture['id']}"
    )
    deleted = school_client.delete(fixture_url, headers=owner.headers)
    assert deleted.status_code == 204, deleted.text

    second_fixture = _fixture(
        school_client,
        owner,
        organization["id"],
        team["id"],
        opponent["id"],
        name="Second Lifecycle Cup",
    )
    plan = _create_plan(
        school_client,
        owner,
        organization["id"],
        team["id"],
        second_fixture["id"],
    )
    assert plan.status_code == 201
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        retained = await session.get(OrganizationSelectionPlan, plan.json()["id"])
        assert retained is not None
        retained.status = "published"
        await session.commit()
    competition_url = (
        f"/api/organizations/{organization['id']}/competitions/"
        f"{second_fixture['tournament_id']}"
    )
    protected = school_client.delete(competition_url, headers=owner.headers)
    assert protected.status_code == 409
    assert protected.json() == {
        "detail": "Competition cannot be deleted while retained selection evidence exists"
    }
    async with session_maker() as session:
        retained = await session.get(OrganizationSelectionPlan, plan.json()["id"])
        assert retained is not None
        retained.status = "draft"
        await session.commit()
    deleted_competition = school_client.delete(competition_url, headers=owner.headers)
    assert deleted_competition.status_code == 204, deleted_competition.text

    async with session_maker() as session:
        assert await session.scalar(select(func.count(OrganizationSelectionPlan.id))) == 0


@pytest.mark.skipif(
    os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="Selection-plan concurrency requires real PostgreSQL",
)
async def test_postgres_concurrent_create_returns_one_stable_plan(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "selection-create-race@example.com")
    organization = create_school(school_client, owner, "Create Race School")
    team = _team(school_client, owner, organization["id"], "Race XI")
    opponent = _team(school_client, owner, organization["id"], "Race Opponent")
    fixture = _fixture(school_client, owner, organization["id"], team["id"], opponent["id"])
    session_maker = get_session_local()
    start = asyncio.Event()
    ready = 0
    ready_lock = asyncio.Lock()

    async def create():
        nonlocal ready
        async with session_maker() as session:
            async with ready_lock:
                ready += 1
                if ready == 2:
                    start.set()
            await start.wait()
            return await create_or_open_selection_plan(
                session,
                organization_id=organization["id"],
                actor_user_id=owner.id,
                payload=OrganizationSelectionPlanCreate(
                    team_id=team["id"], fixture_id=fixture["id"]
                ),
            )

    outcomes = await asyncio.wait_for(asyncio.gather(create(), create()), timeout=10)
    assert outcomes[0].id == outcomes[1].id
    assert outcomes[0].revision == outcomes[1].revision == 1
    async with session_maker() as session:
        assert await session.scalar(select(func.count(OrganizationSelectionPlan.id))) == 1


@pytest.mark.skipif(
    os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="Selection-plan revision locking requires real PostgreSQL",
)
async def test_postgres_concurrent_mutation_has_one_winner_and_usable_loser(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "selection-update-race@example.com")
    organization = create_club(school_client, owner, "Update Race Club")
    team = _team(school_client, owner, organization["id"], "Race XI")
    opponent = _team(school_client, owner, organization["id"], "Race Opponent")
    players = [
        _player(school_client, owner, organization["id"], name) for name in ("Race One", "Race Two")
    ]
    for player in players:
        _assign(school_client, owner, organization["id"], team["id"], player["id"])
    fixture = _fixture(school_client, owner, organization["id"], team["id"], opponent["id"])
    plan = _create_plan(school_client, owner, organization["id"], team["id"], fixture["id"]).json()
    session_maker = get_session_local()
    start = asyncio.Event()
    ready = 0
    ready_lock = asyncio.Lock()

    async def update(player_id: str):
        nonlocal ready
        async with session_maker() as session:
            async with ready_lock:
                ready += 1
                if ready == 2:
                    start.set()
            await start.wait()
            try:
                outcome = await update_selection_plan(
                    session,
                    organization_id=organization["id"],
                    plan_id=plan["id"],
                    actor_user_id=owner.id,
                    payload=OrganizationSelectionPlanUpdate(
                        expected_revision=1,
                        xi_roster_membership_ids=[player_id],
                    ),
                )
                return ("success", outcome.revision, player_id)
            except OrganizationSelectionPlanServiceError as exc:
                assert exc.status_code == 409
                assert await session.scalar(select(func.count(User.id))) == 1
                return ("conflict", None, player_id)

    outcomes = await asyncio.wait_for(
        asyncio.gather(update(players[0]["id"]), update(players[1]["id"])), timeout=10
    )
    assert sorted(item[0] for item in outcomes) == ["conflict", "success"]
    async with session_maker() as session:
        current = await session.scalar(
            select(OrganizationSelectionPlan).where(OrganizationSelectionPlan.id == plan["id"])
        )
        assert current is not None
        assert current.revision == 2
        rows = list(
            (
                await session.scalars(
                    select(OrganizationSelectionPlanPlayer).where(
                        OrganizationSelectionPlanPlayer.selection_plan_id == plan["id"]
                    )
                )
            ).all()
        )
        assert len(rows) == 1
        assert rows[0].school_player_membership_id in {player["id"] for player in players}

        with pytest.raises(IntegrityError):
            await session.execute(
                insert(OrganizationSelectionPlanPlayer).values(
                    selection_plan_id=plan["id"],
                    school_player_membership_id=rows[0].school_player_membership_id,
                    organization_id=organization["id"],
                    selection_role="reserve",
                )
            )
            await session.commit()
        await session.rollback()
        assert await session.scalar(select(func.count(OrganizationSelectionPlan.id))) == 1


@pytest.mark.skipif(
    os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="Selection-plan composite constraints require real PostgreSQL",
)
async def test_postgres_composite_tenancy_and_state_constraints_reject_unsafe_rows(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "selection-fk-a@example.com")
    foreign_owner = register_user(school_client, "selection-fk-b@example.com")
    organization = create_school(school_client, owner, "Constraint School")
    foreign = create_club(school_client, foreign_owner, "Constraint Club")
    team = _team(school_client, owner, organization["id"], "Constraint XI")
    opponent = _team(school_client, owner, organization["id"], "Constraint Opponent")
    foreign_team = _team(school_client, foreign_owner, foreign["id"], "Foreign XI")
    foreign_opponent = _team(school_client, foreign_owner, foreign["id"], "Foreign Opponent")
    player = _player(school_client, owner, organization["id"], "Constraint Player")
    foreign_player = _player(
        school_client, foreign_owner, foreign["id"], "Foreign Constraint Player"
    )
    _assign(school_client, owner, organization["id"], team["id"], player["id"])
    fixture = _fixture(school_client, owner, organization["id"], team["id"], opponent["id"])
    foreign_fixture = _fixture(
        school_client,
        foreign_owner,
        foreign["id"],
        foreign_team["id"],
        foreign_opponent["id"],
        name="Foreign Constraint Cup",
    )
    plan = _create_plan(school_client, owner, organization["id"], team["id"], fixture["id"]).json()
    session_maker = get_session_local()

    def unsafe_plan(*, team_id: str, fixture_row: dict) -> OrganizationSelectionPlan:
        return OrganizationSelectionPlan(
            id=str(uuid.uuid4()),
            organization_id=organization["id"],
            team_id=team_id,
            fixture_id=fixture_row["id"],
            fixture_tournament_id=fixture_row["tournament_id"],
            status="draft",
            revision=1,
            created_by_user_id=owner.id,
            updated_by_user_id=owner.id,
        )

    async with session_maker() as session:
        for row in (
            unsafe_plan(team_id=foreign_team["id"], fixture_row=fixture),
            unsafe_plan(team_id=team["id"], fixture_row=foreign_fixture),
        ):
            session.add(row)
            with pytest.raises(IntegrityError):
                await session.commit()
            await session.rollback()
            assert await session.scalar(select(func.count(OrganizationSelectionPlan.id))) == 1

        session.add(
            OrganizationSelectionPlanPlayer(
                selection_plan_id=plan["id"],
                school_player_membership_id=foreign_player["id"],
                organization_id=organization["id"],
                selection_role="xi",
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        for values in ({"status": "unsafe"}, {"revision": 0}):
            with pytest.raises(IntegrityError):
                await session.execute(
                    update(OrganizationSelectionPlan)
                    .where(OrganizationSelectionPlan.id == plan["id"])
                    .values(**values)
                )
                await session.commit()
            await session.rollback()
            assert await session.scalar(select(func.count(User.id))) == 2
