from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from backend.api.schemas.organizations import SchoolTeamRosterPlayerCreate
from backend.services import (
    organization_entitlement_service,
    organization_team_roster_service,
)
from backend.sql_app.models import (
    Organization,
    OrganizationEntitlement,
    OrganizationMembership,
    PlayerProfile,
    RoleEnum,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
    User,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_school,
    register_user,
)


def _teams_url(organization_id: str) -> str:
    return f"/api/organizations/{organization_id}/teams"


def _school_players_url(organization_id: str) -> str:
    return f"/api/organizations/{organization_id}/players"


def _team_players_url(organization_id: str, team_id: str) -> str:
    return f"{_teams_url(organization_id)}/{team_id}/players"


def _create_team(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    name: str,
) -> dict:
    response = client.post(
        _teams_url(organization_id),
        json={"name": name, "home_ground": "School Oval", "season": "2026"},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_school_player(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    name: str,
    *,
    student_identifier: str | None = None,
) -> dict:
    response = client.post(
        _school_players_url(organization_id),
        json={
            "player_name": name,
            "student_identifier": student_identifier,
            "year_group": "Year 10",
        },
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _assign_player(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    team_id: str,
    school_player_membership_id: str,
) -> dict:
    response = client.post(
        _team_players_url(organization_id, team_id),
        json={"school_player_membership_id": school_player_membership_id},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("role", ["owner", "admin", "coach"])
async def test_team_roster_writers_assign_deactivate_and_reactivate_same_identity(
    school_client: TestClient,
    role: str,
) -> None:
    owner = register_user(school_client, f"team-roster-{role}-owner@example.com")
    actor = owner
    organization = create_school(school_client, owner, f"{role.title()} Team Roster School")
    if role != "owner":
        actor = register_user(school_client, f"team-roster-{role}@example.com")
        add_membership(school_client, owner, organization["id"], actor.id, role)
    team = _create_team(school_client, owner, organization["id"], "U15")
    school_player = _create_school_player(
        school_client,
        owner,
        organization["id"],
        "John Smith",
        student_identifier="STU-001",
    )
    legacy_players = [{"id": "legacy-json-player", "name": "Legacy JSON Player"}]
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored_team = await session.get(Team, team["id"])
        assert stored_team is not None
        stored_team.players = legacy_players
        await session.commit()

    assigned = _assign_player(
        school_client,
        actor,
        organization["id"],
        team["id"],
        school_player["id"],
    )
    assert assigned["school_player_membership_id"] == school_player["id"]
    assert assigned["player_profile_id"] == school_player["player_profile_id"]
    assert assigned["operationally_available"] is True

    active_duplicate = school_client.post(
        _team_players_url(organization["id"], team["id"]),
        json={"school_player_membership_id": school_player["id"]},
        headers=actor.headers,
    )
    assert active_duplicate.status_code == 409
    assert active_duplicate.json() == {"detail": "Player is already on this Team roster"}

    deactivated = school_client.delete(
        f"{_team_players_url(organization['id'], team['id'])}/{assigned['id']}",
        headers=actor.headers,
    )
    assert deactivated.status_code == 204
    retained = school_client.get(
        f"{_team_players_url(organization['id'], team['id'])}/{assigned['id']}",
        headers=actor.headers,
    )
    assert retained.status_code == 200
    assert retained.json()["status"] == "inactive"
    assert retained.json()["operationally_available"] is False

    inactive_duplicate = school_client.post(
        _team_players_url(organization["id"], team["id"]),
        json={"school_player_membership_id": school_player["id"]},
        headers=actor.headers,
    )
    assert inactive_duplicate.status_code == 409

    reactivated = school_client.patch(
        f"{_team_players_url(organization['id'], team['id'])}/{assigned['id']}",
        json={"status": "active"},
        headers=actor.headers,
    )
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["id"] == assigned["id"]
    assert reactivated.json()["school_player_membership_id"] == school_player["id"]
    assert reactivated.json()["player_profile_id"] == school_player["player_profile_id"]
    assert reactivated.json()["operationally_available"] is True

    listed = school_client.get(
        _team_players_url(organization["id"], team["id"]), headers=actor.headers
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [assigned["id"]]

    async with session_maker() as session:
        assert (
            await session.scalar(
                select(func.count(SchoolTeamPlayerMembership.id)).where(
                    SchoolTeamPlayerMembership.team_id == team["id"],
                    SchoolTeamPlayerMembership.school_player_membership_id == school_player["id"],
                )
            )
            == 1
        )
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == 1
        stored_team = await session.get(Team, team["id"])
        assert stored_team is not None
        assert stored_team.players == legacy_players


@pytest.mark.parametrize("role", ["scorer", "viewer"])
def test_scorer_and_viewer_can_read_but_cannot_mutate_team_roster(
    school_client: TestClient,
    role: str,
) -> None:
    owner = register_user(school_client, f"team-roster-{role}-owner@example.com")
    reader = register_user(school_client, f"team-roster-{role}@example.com")
    organization = create_school(school_client, owner, f"{role.title()} Team Roster School")
    add_membership(school_client, owner, organization["id"], reader.id, role)
    team = _create_team(school_client, owner, organization["id"], "Readers XI")
    first_player = _create_school_player(
        school_client, owner, organization["id"], "Readable Player"
    )
    second_player = _create_school_player(school_client, owner, organization["id"], "Denied Player")
    assigned = _assign_player(
        school_client, owner, organization["id"], team["id"], first_player["id"]
    )

    listed = school_client.get(
        _team_players_url(organization["id"], team["id"]), headers=reader.headers
    )
    exact = school_client.get(
        f"{_team_players_url(organization['id'], team['id'])}/{assigned['id']}",
        headers=reader.headers,
    )
    create = school_client.post(
        _team_players_url(organization["id"], team["id"]),
        json={"school_player_membership_id": second_player["id"]},
        headers=reader.headers,
    )
    update = school_client.patch(
        f"{_team_players_url(organization['id'], team['id'])}/{assigned['id']}",
        json={"status": "inactive"},
        headers=reader.headers,
    )
    remove = school_client.delete(
        f"{_team_players_url(organization['id'], team['id'])}/{assigned['id']}",
        headers=reader.headers,
    )
    assert listed.status_code == exact.status_code == 200
    assert create.status_code == update.status_code == remove.status_code == 403


async def test_nonmember_disabled_membership_and_inactive_school_are_denied(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-roster-gates-owner@example.com")
    outsider = register_user(school_client, "team-roster-gates-outsider@example.com")
    organization = create_school(school_client, owner, "Team Roster Gates School")
    team = _create_team(school_client, owner, organization["id"], "Gate XI")
    url = _team_players_url(organization["id"], team["id"])

    nonmember = school_client.get(url, headers=outsider.headers)
    assert nonmember.status_code == 404
    assert nonmember.json() == {"detail": "Organization not found"}

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        membership = await session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization["id"],
                OrganizationMembership.user_id == owner.id,
            )
        )
        assert membership is not None
        membership.status = "disabled"
        await session.commit()
    assert school_client.get(url, headers=owner.headers).status_code == 404

    async with session_maker() as session:
        membership = await session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization["id"],
                OrganizationMembership.user_id == owner.id,
            )
        )
        stored_organization = await session.get(Organization, organization["id"])
        assert membership is not None and stored_organization is not None
        membership.status = "active"
        stored_organization.status = "suspended"
        await session.commit()
    assert school_client.get(url, headers=owner.headers).status_code == 404


def test_cross_tenant_and_cross_team_ids_are_tenant_safe(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "team-roster-tenant-a@example.com")
    owner_b = register_user(school_client, "team-roster-tenant-b@example.com")
    school_a = create_school(school_client, owner_a, "Team Roster Tenant A")
    school_b = create_school(school_client, owner_b, "Team Roster Tenant B")
    add_membership(school_client, owner_b, school_b["id"], owner_a.id, "admin")
    team_a = _create_team(school_client, owner_a, school_a["id"], "Secret Team A")
    team_b = _create_team(school_client, owner_b, school_b["id"], "Team B")
    other_team_b = _create_team(school_client, owner_b, school_b["id"], "Other Team B")
    player_a = _create_school_player(school_client, owner_a, school_a["id"], "Secret Student A")
    player_b = _create_school_player(school_client, owner_b, school_b["id"], "Student B")
    assigned_a = _assign_player(
        school_client, owner_a, school_a["id"], team_a["id"], player_a["id"]
    )
    assigned_b = _assign_player(
        school_client, owner_b, school_b["id"], team_b["id"], player_b["id"]
    )

    cross_school_team = school_client.get(
        _team_players_url(school_b["id"], team_a["id"]), headers=owner_a.headers
    )
    cross_school_player = school_client.post(
        _team_players_url(school_b["id"], team_b["id"]),
        json={"school_player_membership_id": player_a["id"]},
        headers=owner_a.headers,
    )
    cross_school_exact = school_client.get(
        f"{_team_players_url(school_b['id'], team_b['id'])}/{assigned_a['id']}",
        headers=owner_a.headers,
    )
    cross_team_exact = school_client.get(
        f"{_team_players_url(school_b['id'], other_team_b['id'])}/{assigned_b['id']}",
        headers=owner_a.headers,
    )

    assert cross_school_team.status_code == 404
    assert cross_school_team.json() == {"detail": "Team not found"}
    assert cross_school_player.status_code == 404
    assert cross_school_player.json() == {"detail": "Roster player not found"}
    assert cross_school_exact.status_code == cross_team_exact.status_code == 404
    assert (
        cross_school_exact.json()
        == cross_team_exact.json()
        == {"detail": "Team roster player not found"}
    )
    denied_text = " ".join(
        response.text
        for response in (
            cross_school_team,
            cross_school_player,
            cross_school_exact,
            cross_team_exact,
        )
    ).lower()
    assert "secret team" not in denied_text
    assert "secret student" not in denied_text


async def test_archived_team_and_inactive_school_player_assignment_are_denied(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-roster-inactive-owner@example.com")
    organization = create_school(school_client, owner, "Inactive Assignment School")
    archived_team = _create_team(school_client, owner, organization["id"], "Archived Team")
    active_team = _create_team(school_client, owner, organization["id"], "Active Team")
    school_player = _create_school_player(
        school_client, owner, organization["id"], "Inactive Student"
    )
    archived = school_client.delete(
        f"{_teams_url(organization['id'])}/{archived_team['id']}", headers=owner.headers
    )
    assert archived.status_code == 204

    archived_assignment = school_client.post(
        _team_players_url(organization["id"], archived_team["id"]),
        json={"school_player_membership_id": school_player["id"]},
        headers=owner.headers,
    )
    assert archived_assignment.status_code == 409
    assert archived_assignment.json() == {
        "detail": "Archived Team cannot receive roster assignments"
    }

    school_client.patch(
        f"{_school_players_url(organization['id'])}/{school_player['id']}",
        json={"status": "inactive"},
        headers=owner.headers,
    )
    inactive_assignment = school_client.post(
        _team_players_url(organization["id"], active_team["id"]),
        json={"school_player_membership_id": school_player["id"]},
        headers=owner.headers,
    )
    assert inactive_assignment.status_code == 409
    assert inactive_assignment.json() == {
        "detail": "Inactive School roster player cannot be assigned"
    }


@pytest.mark.parametrize(
    "missing_capability",
    ["school_persistent_teams", "school_team_rosters"],
)
def test_both_team_roster_capabilities_are_required(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    missing_capability: str,
) -> None:
    owner = register_user(school_client, f"team-roster-cap-{missing_capability}@example.com")
    organization = create_school(school_client, owner, f"Missing {missing_capability} School")
    team = _create_team(school_client, owner, organization["id"], "Capability XI")
    approved = organization_entitlement_service.SCHOOL_FREE_CAPABILITIES - {missing_capability}
    monkeypatch.setitem(
        organization_entitlement_service.PLAN_CAPABILITIES,
        organization_entitlement_service.SCHOOL_FREE_PLAN_KEY,
        frozenset(approved),
    )

    response = school_client.get(
        _team_players_url(organization["id"], team["id"]), headers=owner.headers
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": f"Organization capability not enabled: {missing_capability}"
    }


async def test_disabled_school_free_entitlement_denies_team_roster_access(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-roster-disabled-cap@example.com")
    organization = create_school(school_client, owner, "Disabled Team Roster School")
    team = _create_team(school_client, owner, organization["id"], "Disabled Cap XI")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        assert entitlement is not None
        entitlement.status = "disabled"
        await session.commit()

    response = school_client.get(
        _team_players_url(organization["id"], team["id"]), headers=owner.headers
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "Organization capability not enabled: school_persistent_teams"
    }


@pytest.mark.parametrize("global_authority", ["org_pro", "superuser", "user_org_id"])
async def test_global_and_legacy_authority_do_not_bypass_team_roster_membership(
    school_client: TestClient,
    global_authority: str,
) -> None:
    owner = register_user(school_client, f"team-roster-{global_authority}-owner@example.com")
    outsider = register_user(school_client, f"team-roster-{global_authority}-outsider@example.com")
    organization = create_school(school_client, owner, "No Team Roster Bypass School")
    team = _create_team(school_client, owner, organization["id"], "Private XI")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(User, outsider.id)
        assert stored is not None
        if global_authority == "org_pro":
            stored.role = RoleEnum.org_pro
        elif global_authority == "superuser":
            stored.is_superuser = True
        else:
            stored.org_id = organization["id"]
        await session.commit()

    response = school_client.get(
        _team_players_url(organization["id"], team["id"]), headers=outsider.headers
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Organization not found"}


async def test_same_player_multiple_teams_and_same_name_players_one_team(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-roster-identity-owner@example.com")
    organization = create_school(school_client, owner, "Canonical Identity School")
    u15 = _create_team(school_client, owner, organization["id"], "U15")
    first_xi = _create_team(school_client, owner, organization["id"], "First XI")
    john_a = _create_school_player(
        school_client, owner, organization["id"], "John Smith", student_identifier="A"
    )
    john_b = _create_school_player(
        school_client, owner, organization["id"], "John Smith", student_identifier="B"
    )

    a_u15 = _assign_player(school_client, owner, organization["id"], u15["id"], john_a["id"])
    a_first = _assign_player(school_client, owner, organization["id"], first_xi["id"], john_a["id"])
    b_u15 = _assign_player(school_client, owner, organization["id"], u15["id"], john_b["id"])

    assert a_u15["school_player_membership_id"] == a_first["school_player_membership_id"]
    assert a_u15["player_profile_id"] == a_first["player_profile_id"]
    assert a_u15["team_id"] != a_first["team_id"]
    assert a_u15["player_profile_id"] != b_u15["player_profile_id"]
    assert a_u15["player_name"] == b_u15["player_name"] == "John Smith"

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == 2
        assert await session.scalar(select(func.count(SchoolTeamPlayerMembership.id))) == 3


async def test_school_master_lifecycle_preserves_team_history_and_availability(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-roster-master-life@example.com")
    organization = create_school(school_client, owner, "Master Lifecycle School")
    team = _create_team(school_client, owner, organization["id"], "History XI")
    school_player = _create_school_player(
        school_client, owner, organization["id"], "Historical Student"
    )
    assigned = _assign_player(
        school_client, owner, organization["id"], team["id"], school_player["id"]
    )
    exact_url = f"{_team_players_url(organization['id'], team['id'])}/{assigned['id']}"

    deactivated = school_client.patch(
        f"{_school_players_url(organization['id'])}/{school_player['id']}",
        json={"status": "inactive"},
        headers=owner.headers,
    )
    assert deactivated.status_code == 200
    retained = school_client.get(exact_url, headers=owner.headers)
    assert retained.status_code == 200
    assert retained.json()["status"] == "active"
    assert retained.json()["school_player_status"] == "inactive"
    assert retained.json()["operationally_available"] is False

    duplicate = school_client.post(
        _team_players_url(organization["id"], team["id"]),
        json={"school_player_membership_id": school_player["id"]},
        headers=owner.headers,
    )
    assert duplicate.status_code == 409

    reactivated = school_client.patch(
        f"{_school_players_url(organization['id'])}/{school_player['id']}",
        json={"status": "active"},
        headers=owner.headers,
    )
    assert reactivated.status_code == 200
    available_again = school_client.get(exact_url, headers=owner.headers)
    assert available_again.status_code == 200
    assert available_again.json()["id"] == assigned["id"]
    assert available_again.json()["operationally_available"] is True

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert await session.get(PlayerProfile, school_player["player_profile_id"]) is not None
        assert (
            await session.scalar(
                select(func.count(SchoolTeamPlayerMembership.id)).where(
                    SchoolTeamPlayerMembership.id == assigned["id"]
                )
            )
            == 1
        )


def test_archived_team_history_is_readable_but_operationally_unavailable(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-roster-archive-history@example.com")
    organization = create_school(school_client, owner, "Archived History School")
    team = _create_team(school_client, owner, organization["id"], "Archive XI")
    player = _create_school_player(school_client, owner, organization["id"], "Archive Player")
    assigned = _assign_player(school_client, owner, organization["id"], team["id"], player["id"])
    school_client.delete(f"{_teams_url(organization['id'])}/{team['id']}", headers=owner.headers)

    exact = school_client.get(
        f"{_team_players_url(organization['id'], team['id'])}/{assigned['id']}",
        headers=owner.headers,
    )
    listed = school_client.get(
        _team_players_url(organization["id"], team["id"]), headers=owner.headers
    )
    assert exact.status_code == listed.status_code == 200
    assert exact.json()["team_status"] == "archived"
    assert exact.json()["operationally_available"] is False


def test_team_roster_request_body_cannot_spoof_identity_or_tenancy(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-roster-spoof@example.com")
    organization = create_school(school_client, owner, "Team Roster Spoof School")
    team = _create_team(school_client, owner, organization["id"], "Spoof XI")
    player = _create_school_player(school_client, owner, organization["id"], "Real Player")

    create = school_client.post(
        _team_players_url(organization["id"], team["id"]),
        json={
            "school_player_membership_id": player["id"],
            "organization_id": "spoofed",
            "team_id": "spoofed",
            "player_name": "Spoofed",
        },
        headers=owner.headers,
    )
    assert create.status_code == 422
    assigned = _assign_player(school_client, owner, organization["id"], team["id"], player["id"])
    update = school_client.patch(
        f"{_team_players_url(organization['id'], team['id'])}/{assigned['id']}",
        json={"status": "inactive", "team_id": "spoofed"},
        headers=owner.headers,
    )
    assert update.status_code == 422


async def test_postgres_concurrent_duplicate_assignment_is_controlled(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("Team roster concurrency contract requires real PostgreSQL")

    owner = register_user(school_client, "team-roster-concurrent@example.com")
    organization = create_school(school_client, owner, "Concurrent Team Roster School")
    team = _create_team(school_client, owner, organization["id"], "Concurrent XI")
    player = _create_school_player(school_client, owner, organization["id"], "Concurrent Player")
    ready = 0
    ready_lock = asyncio.Lock()
    start = asyncio.Event()

    async def assign_once() -> tuple[str, int | None]:
        nonlocal ready
        async with session_maker() as session:
            async with ready_lock:
                ready += 1
                if ready == 2:
                    start.set()
            await start.wait()
            try:
                await organization_team_roster_service.create_team_roster_player(
                    session,
                    organization_id=organization["id"],
                    team_id=team["id"],
                    payload=SchoolTeamRosterPlayerCreate(school_player_membership_id=player["id"]),
                    actor_user_id=owner.id,
                )
            except organization_team_roster_service.OrganizationTeamRosterServiceError as exc:
                assert await session.scalar(select(func.count(User.id))) == 1
                return "error", exc.status_code
            return "success", None

    results = await asyncio.gather(assign_once(), assign_once())
    assert sorted(results) == [("error", 409), ("success", None)]
    async with session_maker() as session:
        assert (
            await session.scalar(
                select(func.count(SchoolTeamPlayerMembership.id)).where(
                    SchoolTeamPlayerMembership.team_id == team["id"],
                    SchoolTeamPlayerMembership.school_player_membership_id == player["id"],
                )
            )
            == 1
        )


async def test_postgres_team_roster_schema_and_deletion_contracts(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("Team roster persistence contract requires real PostgreSQL")

    creator = register_user(school_client, "team-roster-retained-creator@example.com")
    administrator = register_user(school_client, "team-roster-retained-admin@example.com")
    organization = create_school(school_client, creator, "Retained Team Roster School")
    add_membership(school_client, creator, organization["id"], administrator.id, "admin")
    team = _create_team(school_client, creator, organization["id"], "Retained XI")
    player = _create_school_player(school_client, creator, organization["id"], "Retained Player")
    assigned = _assign_player(school_client, creator, organization["id"], team["id"], player["id"])

    async with session_maker() as session:
        constraints = {
            row.conname: row.definition
            for row in (
                await session.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) AS definition "
                        "FROM pg_constraint WHERE conrelid = "
                        "'school_team_player_memberships'::regclass"
                    )
                )
            ).all()
        }
        assert "ON DELETE CASCADE" in constraints["fk_school_team_players_organization"]
        assert "ON DELETE CASCADE" in constraints["fk_school_team_players_team"]
        assert "ON DELETE RESTRICT" in constraints["fk_school_team_players_school_player"]
        assert "ON DELETE SET NULL" in constraints["fk_school_team_players_creator"]
        assert "UNIQUE" in constraints["uq_school_team_player_memberships_team_player"]
        assert "active" in constraints["ck_school_team_player_memberships_status"]
        assert "inactive" in constraints["ck_school_team_player_memberships_status"]

        columns = {
            row.column_name: (row.is_nullable, row.column_default)
            for row in (
                await session.execute(
                    text(
                        "SELECT column_name, is_nullable, column_default "
                        "FROM information_schema.columns WHERE table_name = "
                        "'school_team_player_memberships'"
                    )
                )
            ).all()
        }
        assert columns["organization_id"][0] == "NO"
        assert columns["team_id"][0] == "NO"
        assert columns["school_player_membership_id"][0] == "NO"
        assert columns["created_by_user_id"][0] == "YES"
        assert "active" in columns["status"][1]
        indexes = set(
            (
                await session.execute(
                    text(
                        "SELECT indexname FROM pg_indexes WHERE tablename = "
                        "'school_team_player_memberships'"
                    )
                )
            ).scalars()
        )
        assert {
            "ix_school_team_player_memberships_organization_id",
            "ix_school_team_player_memberships_team_id",
            "ix_school_team_player_memberships_school_player_membership_id",
            "ix_school_team_player_memberships_organization_team_status",
        }.issubset(indexes)

        await session.execute(delete(User).where(User.id == creator.id))
        await session.commit()

    async with session_maker() as session:
        retained = await session.get(SchoolTeamPlayerMembership, assigned["id"])
        assert retained is not None
        assert retained.created_by_user_id is None
        assert await session.get(SchoolPlayerMembership, player["id"]) is not None
        assert await session.get(PlayerProfile, player["player_profile_id"]) is not None

        with pytest.raises(IntegrityError):
            await session.execute(
                delete(SchoolPlayerMembership).where(SchoolPlayerMembership.id == player["id"])
            )
            await session.commit()
        await session.rollback()
        assert await session.scalar(select(func.count(User.id))) == 1

        await session.execute(delete(Team).where(Team.id == team["id"]))
        await session.commit()

    async with session_maker() as session:
        assert await session.get(SchoolTeamPlayerMembership, assigned["id"]) is None
        assert await session.get(SchoolPlayerMembership, player["id"]) is not None
        assert await session.get(PlayerProfile, player["player_profile_id"]) is not None

    second_team = _create_team(
        school_client, administrator, organization["id"], "Organization Delete XI"
    )
    second_player = _create_school_player(
        school_client, administrator, organization["id"], "Organization Delete Player"
    )
    second_assignment = _assign_player(
        school_client,
        administrator,
        organization["id"],
        second_team["id"],
        second_player["id"],
    )
    async with session_maker() as session:
        await session.execute(delete(Organization).where(Organization.id == organization["id"]))
        await session.commit()

    async with session_maker() as session:
        assert await session.get(SchoolTeamPlayerMembership, second_assignment["id"]) is None
        assert await session.get(SchoolPlayerMembership, second_player["id"]) is None
        retained_team = await session.get(Team, second_team["id"])
        assert retained_team is not None
        assert retained_team.organization_id is None
        assert await session.get(PlayerProfile, second_player["player_profile_id"]) is not None
