from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text

from backend.sql_app.models import (
    Organization,
    OrganizationEntitlement,
    OrganizationMembership,
    RoleEnum,
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


def _create_team(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    name: str = "U15",
) -> dict:
    response = client.post(
        _teams_url(organization_id),
        json={"name": name, "home_ground": "School Oval", "season": "2026"},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("role", ["owner", "admin"])
async def test_owner_and_admin_can_create_read_update_and_archive_school_teams(
    school_client: TestClient,
    role: str,
) -> None:
    owner = register_user(school_client, f"{role}-flow-owner@example.com")
    actor = owner
    organization = create_school(school_client, owner, f"{role.title()} Flow School")
    if role == "admin":
        actor = register_user(school_client, "admin-flow-actor@example.com")
        add_membership(school_client, owner, organization["id"], actor.id, "admin")

    team = _create_team(school_client, actor, organization["id"])
    assert team["organization_id"] == organization["id"]
    assert team["status"] == "active"
    assert team["owner_user_id"] == actor.id

    read = school_client.get(
        f"{_teams_url(organization['id'])}/{team['id']}", headers=actor.headers
    )
    assert read.status_code == 200
    assert read.json()["name"] == "U15"

    updated = school_client.patch(
        f"{_teams_url(organization['id'])}/{team['id']}",
        json={"name": "  First   XI  ", "home_ground": None},
        headers=actor.headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "First XI"
    assert updated.json()["home_ground"] is None

    archived = school_client.delete(
        f"{_teams_url(organization['id'])}/{team['id']}", headers=actor.headers
    )
    assert archived.status_code == 204
    listed = school_client.get(_teams_url(organization["id"]), headers=actor.headers)
    assert listed.status_code == 200
    assert listed.json() == []

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.scalar(
            select(Team).where(
                Team.id == team["id"],
                Team.organization_id == organization["id"],
            )
        )
        assert stored is not None
        assert stored.status == "archived"


async def test_coach_can_create_read_update_but_cannot_archive(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "coach-owner@example.com")
    coach = register_user(school_client, "coach-member@example.com")
    organization = create_school(school_client, owner, "Coach Team School")
    add_membership(school_client, owner, organization["id"], coach.id, "coach")

    team = _create_team(school_client, coach, organization["id"])
    read = school_client.get(
        f"{_teams_url(organization['id'])}/{team['id']}", headers=coach.headers
    )
    updated = school_client.patch(
        f"{_teams_url(organization['id'])}/{team['id']}",
        json={"name": "Girls U15"},
        headers=coach.headers,
    )
    archived = school_client.delete(
        f"{_teams_url(organization['id'])}/{team['id']}", headers=coach.headers
    )

    assert read.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["name"] == "Girls U15"
    assert archived.status_code == 403
    assert archived.json() == {"detail": "Insufficient organization role"}


@pytest.mark.parametrize("role", ["scorer", "viewer"])
def test_scorer_and_viewer_are_read_only(
    school_client: TestClient,
    role: str,
) -> None:
    owner = register_user(school_client, f"{role}-owner@example.com")
    reader = register_user(school_client, f"{role}-reader@example.com")
    organization = create_school(school_client, owner, f"{role.title()} Team School")
    add_membership(school_client, owner, organization["id"], reader.id, role)
    team = _create_team(school_client, owner, organization["id"])

    listed = school_client.get(_teams_url(organization["id"]), headers=reader.headers)
    read = school_client.get(
        f"{_teams_url(organization['id'])}/{team['id']}", headers=reader.headers
    )
    create = school_client.post(
        _teams_url(organization["id"]), json={"name": "Denied"}, headers=reader.headers
    )
    update = school_client.patch(
        f"{_teams_url(organization['id'])}/{team['id']}",
        json={"name": "Denied"},
        headers=reader.headers,
    )
    archive = school_client.delete(
        f"{_teams_url(organization['id'])}/{team['id']}", headers=reader.headers
    )

    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [team["id"]]
    assert read.status_code == 200
    assert create.status_code == update.status_code == archive.status_code == 403


def test_non_member_is_denied_without_team_metadata_leakage(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "nonmember-owner@example.com")
    outsider = register_user(school_client, "nonmember-outsider@example.com")
    organization = create_school(school_client, owner, "Private Team School")
    team = _create_team(school_client, owner, organization["id"], "Secret First XI")

    listed = school_client.get(_teams_url(organization["id"]), headers=outsider.headers)
    exact = school_client.get(
        f"{_teams_url(organization['id'])}/{team['id']}", headers=outsider.headers
    )

    assert listed.status_code == exact.status_code == 404
    assert listed.json() == exact.json() == {"detail": "Organization not found"}
    assert "secret" not in exact.text.lower()


def test_exact_team_id_is_tenant_scoped_and_leaks_no_metadata(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "cross-team-owner-a@example.com")
    owner_b = register_user(school_client, "cross-team-owner-b@example.com")
    school_a = create_school(school_client, owner_a, "Tenant A School")
    school_b = create_school(school_client, owner_b, "Tenant B School")
    add_membership(school_client, owner_b, school_b["id"], owner_a.id, "admin")
    team_a = _create_team(school_client, owner_a, school_a["id"], "Tenant A Secret")

    for method, kwargs in (
        ("get", {}),
        ("patch", {"json": {"name": "Spoofed"}}),
        ("delete", {}),
    ):
        response = getattr(school_client, method)(
            f"{_teams_url(school_b['id'])}/{team_a['id']}",
            headers=owner_a.headers,
            **kwargs,
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Team not found"}
        assert "tenant a" not in response.text.lower()


async def test_disabled_membership_and_inactive_organization_are_denied(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "inactive-team-owner@example.com")
    organization = create_school(school_client, owner, "Inactive Team School")
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
    disabled = school_client.get(_teams_url(organization["id"]), headers=owner.headers)
    assert disabled.status_code == 404

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
    inactive = school_client.get(_teams_url(organization["id"]), headers=owner.headers)
    assert inactive.status_code == 404


@pytest.mark.parametrize("entitlement_state", ["disabled", "missing"])
async def test_disabled_or_missing_school_entitlement_denies_team_operations(
    school_client: TestClient,
    entitlement_state: str,
) -> None:
    owner = register_user(school_client, f"{entitlement_state}-team-owner@example.com")
    organization = create_school(
        school_client, owner, f"{entitlement_state.title()} Entitlement Team School"
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"],
            )
        )
        assert entitlement is not None
        if entitlement_state == "disabled":
            entitlement.status = "disabled"
        else:
            await session.delete(entitlement)
        await session.commit()

    response = school_client.post(
        _teams_url(organization["id"]),
        json={"name": "Denied Team"},
        headers=owner.headers,
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "Organization capability not enabled: school_persistent_teams"
    }


@pytest.mark.parametrize("global_authority", ["org_pro", "superuser"])
async def test_global_authority_without_membership_does_not_bypass_school_team_access(
    school_client: TestClient,
    global_authority: str,
) -> None:
    owner = register_user(school_client, f"global-{global_authority}-owner@example.com")
    outsider = register_user(school_client, f"global-{global_authority}-outsider@example.com")
    organization = create_school(school_client, owner, "No Global Bypass School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(User, outsider.id)
        assert stored is not None
        if global_authority == "org_pro":
            stored.role = RoleEnum.org_pro
        else:
            stored.is_superuser = True
        await session.commit()

    response = school_client.get(_teams_url(organization["id"]), headers=outsider.headers)
    assert response.status_code == 404
    assert response.json() == {"detail": "Organization not found"}


async def test_route_organization_is_authoritative_and_body_spoof_is_rejected(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "spoof-team-owner@example.com")
    school_a = create_school(school_client, owner, "Spoof A School")
    school_b = create_school(school_client, owner, "Spoof B School")

    response = school_client.post(
        _teams_url(school_a["id"]),
        json={"name": "Spoof Attempt", "organization_id": school_b["id"]},
        headers=owner.headers,
    )
    assert response.status_code == 422

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert (
            await session.scalar(select(func.count(Team.id)).where(Team.name == "Spoof Attempt"))
            == 0
        )


async def test_user_org_id_is_never_interpreted_as_school_membership(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "legacy-org-owner@example.com")
    outsider = register_user(school_client, "legacy-org-outsider@example.com")
    organization = create_school(school_client, owner, "Legacy Org ID School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(User, outsider.id)
        assert stored is not None
        stored.org_id = organization["id"]
        await session.commit()

    response = school_client.get(_teams_url(organization["id"]), headers=outsider.headers)
    assert response.status_code == 404


async def test_legacy_null_organization_team_remains_on_legacy_path_only(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "legacy-team-owner@example.com")
    organization = create_school(school_client, owner, "Legacy Compatibility School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored_user = await session.get(User, owner.id)
        assert stored_user is not None
        stored_user.role = RoleEnum.coach_pro
        await session.commit()

    created = school_client.post(
        "/api/teams",
        json={"name": "Legacy Personal XI", "players": [], "competitions": []},
        headers=owner.headers,
    )
    assert created.status_code == 201, created.text
    legacy_team = created.json()

    legacy_read = school_client.get(f"/api/teams/{legacy_team['id']}", headers=owner.headers)
    school_list = school_client.get(_teams_url(organization["id"]), headers=owner.headers)
    assert legacy_read.status_code == 200
    assert legacy_read.json()["name"] == "Legacy Personal XI"
    assert school_list.status_code == 200
    assert school_list.json() == []

    async with session_maker() as session:
        stored_team = await session.get(Team, legacy_team["id"])
        assert stored_team is not None
        assert stored_team.organization_id is None
        assert stored_team.status == "active"


async def test_postgres_school_team_survives_creator_deletion(
    school_client: TestClient,
) -> None:
    """The database retains an organization-owned Team when its creator is deleted."""
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("School Team creator-retention contract requires real PostgreSQL")

    creator = register_user(school_client, "retained-team-creator@example.com")
    administrator = register_user(school_client, "retained-team-admin@example.com")
    organization = create_school(school_client, creator, "Retained Team School")
    add_membership(
        school_client,
        creator,
        organization["id"],
        administrator.id,
        "admin",
    )
    team = _create_team(
        school_client,
        creator,
        organization["id"],
        "Historical First XI",
    )

    async with session_maker() as session:
        constraints = {
            row.conname: row.definition
            for row in (
                await session.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) AS definition "
                        "FROM pg_constraint WHERE conrelid = 'teams'::regclass "
                        "AND conname IN "
                        "('fk_teams_owner_user_id_users', "
                        "'fk_teams_organization_id_organizations')"
                    )
                )
            ).all()
        }
        assert "ON DELETE SET NULL" in constraints["fk_teams_owner_user_id_users"]
        assert "ON DELETE SET NULL" in constraints["fk_teams_organization_id_organizations"]
        owner_nullable = await session.scalar(
            text(
                "SELECT is_nullable FROM information_schema.columns "
                "WHERE table_name = 'teams' AND column_name = 'owner_user_id'"
            )
        )
        assert owner_nullable == "YES"

        await session.execute(delete(User).where(User.id == creator.id))
        await session.commit()

    async with session_maker() as session:
        retained_team = await session.get(Team, team["id"])
        assert retained_team is not None
        assert retained_team.organization_id == organization["id"]
        assert retained_team.owner_user_id is None
        assert retained_team.name == "Historical First XI"
        assert retained_team.home_ground == "School Oval"
        assert retained_team.season == "2026"
        assert retained_team.status == "active"
        assert retained_team.players == []
        assert retained_team.competitions == []

    authorized_read = school_client.get(
        f"{_teams_url(organization['id'])}/{team['id']}",
        headers=administrator.headers,
    )
    assert authorized_read.status_code == 200, authorized_read.text
    assert authorized_read.json()["owner_user_id"] is None
    assert authorized_read.json()["organization_id"] == organization["id"]


async def test_postgres_legacy_team_survives_owner_deletion_as_orphaned_data(
    school_client: TestClient,
) -> None:
    """Legacy personal Teams favor retention when their former owner is deleted."""
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("Legacy Team owner-retention contract requires real PostgreSQL")

    owner = register_user(school_client, "retained-legacy-owner@example.com")
    coach = register_user(school_client, "retained-legacy-coach@example.com")
    async with session_maker() as session:
        stored_owner = await session.get(User, owner.id)
        stored_coach = await session.get(User, coach.id)
        assert stored_owner is not None and stored_coach is not None
        stored_owner.role = RoleEnum.coach_pro
        stored_coach.role = RoleEnum.coach_pro
        await session.commit()

    created = school_client.post(
        "/api/teams",
        json={
            "name": "Retained Legacy XI",
            "home_ground": "Legacy Oval",
            "season": "2024",
            "coach_id": coach.id,
            "players": [],
            "competitions": [],
        },
        headers=owner.headers,
    )
    assert created.status_code == 201, created.text
    team = created.json()

    async with session_maker() as session:
        await session.execute(delete(User).where(User.id == owner.id))
        await session.commit()

    async with session_maker() as session:
        retained_team = await session.get(Team, team["id"])
        assert retained_team is not None
        assert retained_team.organization_id is None
        assert retained_team.owner_user_id is None
        assert retained_team.name == "Retained Legacy XI"
        assert retained_team.home_ground == "Legacy Oval"
        assert retained_team.season == "2024"

    legacy_read = school_client.get(f"/api/teams/{team['id']}", headers=coach.headers)
    assert legacy_read.status_code == 200, legacy_read.text
    assert legacy_read.json()["owner_user_id"] is None


def test_school_team_names_are_not_globally_or_tenant_unique(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "duplicate-team-owner@example.com")
    organization = create_school(school_client, owner, "Multi Team School")

    first = _create_team(school_client, owner, organization["id"], "U15")
    duplicate = _create_team(school_client, owner, organization["id"], "U15")
    third = _create_team(school_client, owner, organization["id"], "First XI")
    listed = school_client.get(_teams_url(organization["id"]), headers=owner.headers)

    assert listed.status_code == 200
    assert {item["id"] for item in listed.json()} == {
        first["id"],
        duplicate["id"],
        third["id"],
    }


def test_school_team_contract_does_not_accept_roster_or_lifecycle_mutations(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "contract-team-owner@example.com")
    organization = create_school(school_client, owner, "Contract Boundary School")

    for forbidden_field, value in (
        ("players", [{"id": "p1", "name": "Student"}]),
        ("competitions", [{"id": "c1", "name": "League"}]),
        ("status", "archived"),
        ("owner_user_id", "spoof-owner"),
    ):
        response = school_client.post(
            _teams_url(organization["id"]),
            json={"name": "Forbidden Mutation", forbidden_field: value},
            headers=owner.headers,
        )
        assert response.status_code == 422


async def test_phase7d_postgres_schema_and_organization_delete_contract(
    school_client: TestClient,
) -> None:
    """Real-Postgres proof for migration columns, indexes, checks, and SET NULL."""
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("Phase 7D migration contract requires real PostgreSQL")

    owner = register_user(school_client, "postgres-schema-team-owner@example.com")
    organization = create_school(school_client, owner, "Postgres Schema School")
    team = _create_team(school_client, owner, organization["id"], "Postgres XI")

    async with session_maker() as session:
        columns = {
            row.column_name: (row.is_nullable, row.column_default)
            for row in (
                await session.execute(
                    text(
                        "SELECT column_name, is_nullable, column_default "
                        "FROM information_schema.columns "
                        "WHERE table_name = 'teams' "
                        "AND column_name IN ('organization_id', 'status')"
                    )
                )
            ).all()
        }
        assert columns["organization_id"] == ("YES", None)
        assert columns["status"][0] == "NO"
        assert "active" in columns["status"][1]

        constraints = {
            row.conname: row.definition
            for row in (
                await session.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) AS definition "
                        "FROM pg_constraint WHERE conrelid = 'teams'::regclass "
                        "AND conname IN "
                        "('fk_teams_organization_id_organizations', 'ck_teams_status')"
                    )
                )
            ).all()
        }
        assert "ON DELETE SET NULL" in constraints["fk_teams_organization_id_organizations"]
        assert "active" in constraints["ck_teams_status"]
        assert "archived" in constraints["ck_teams_status"]

        indexes = set(
            (
                await session.execute(
                    text(
                        "SELECT indexname FROM pg_indexes WHERE tablename = 'teams' "
                        "AND indexname LIKE 'ix_teams_organization%'"
                    )
                )
            ).scalars()
        )
        assert indexes == {
            "ix_teams_organization_id",
            "ix_teams_organization_status",
        }

        stored_organization = await session.get(Organization, organization["id"])
        assert stored_organization is not None
        await session.delete(stored_organization)
        await session.commit()

    async with session_maker() as session:
        retained_team = await session.get(Team, team["id"])
        assert retained_team is not None
        assert retained_team.organization_id is None
