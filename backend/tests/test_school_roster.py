from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text

from backend.api.schemas.organizations import SchoolRosterPlayerCreate, SchoolRosterPlayerLink
from backend.services import organization_roster_service
from backend.sql_app.models import (
    Organization,
    OrganizationEntitlement,
    OrganizationMembership,
    PlayerProfile,
    RoleEnum,
    SchoolPlayerMembership,
    User,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_school,
    register_user,
)


def _players_url(organization_id: str) -> str:
    return f"/api/organizations/{organization_id}/players"


def _create_player(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    *,
    name: str = "Student Player",
    student_identifier: str | None = "STU-001",
    year_group: str | None = "Year 9",
) -> dict:
    response = client.post(
        _players_url(organization_id),
        json={
            "player_name": name,
            "student_identifier": student_identifier,
            "year_group": year_group,
        },
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _link_player(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    player_profile_id: str,
) -> dict:
    response = client.post(
        f"{_players_url(organization_id)}/link",
        json={"player_profile_id": player_profile_id},
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _add_profile(session_maker, player_id: str, name: str) -> None:
    async with session_maker() as session:
        session.add(PlayerProfile(player_id=player_id, player_name=name))
        await session.commit()


@pytest.mark.parametrize("role", ["owner", "admin"])
async def test_owner_and_admin_have_full_school_roster_lifecycle(
    school_client: TestClient,
    role: str,
) -> None:
    owner = register_user(school_client, f"roster-{role}-owner@example.com")
    actor = owner
    organization = create_school(school_client, owner, f"{role.title()} Roster School")
    if role == "admin":
        actor = register_user(school_client, "roster-admin-actor@example.com")
        add_membership(school_client, owner, organization["id"], actor.id, "admin")

    created = _create_player(
        school_client,
        actor,
        organization["id"],
        name="  Maya   Singh  ",
    )
    assert created["organization_id"] == organization["id"]
    assert created["player_name"] == "Maya Singh"
    assert created["status"] == "active"
    assert created["created_by_user_id"] == actor.id

    exact = school_client.get(
        f"{_players_url(organization['id'])}/{created['id']}", headers=actor.headers
    )
    listed = school_client.get(_players_url(organization["id"]), headers=actor.headers)
    updated = school_client.patch(
        f"{_players_url(organization['id'])}/{created['id']}",
        json={"student_identifier": " STU-002 ", "year_group": None},
        headers=actor.headers,
    )
    assert exact.status_code == listed.status_code == updated.status_code == 200
    assert [item["id"] for item in listed.json()] == [created["id"]]
    assert updated.json()["student_identifier"] == "STU-002"
    assert updated.json()["year_group"] is None

    deactivated = school_client.patch(
        f"{_players_url(organization['id'])}/{created['id']}",
        json={"status": "inactive"},
        headers=actor.headers,
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "inactive"
    assert school_client.get(_players_url(organization["id"]), headers=actor.headers).json() == []

    discovered = school_client.get(
        _players_url(organization["id"]),
        params={"status": "inactive"},
        headers=actor.headers,
    )
    assert discovered.status_code == 200
    assert [item["id"] for item in discovered.json()] == [created["id"]]
    assert discovered.json()[0]["player_profile_id"] == created["player_profile_id"]

    reactivated = school_client.patch(
        f"{_players_url(organization['id'])}/{discovered.json()[0]['id']}",
        json={"status": "active"},
        headers=actor.headers,
    )
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["id"] == created["id"]
    assert reactivated.json()["player_profile_id"] == created["player_profile_id"]
    assert reactivated.json()["student_identifier"] == "STU-002"
    assert reactivated.json()["year_group"] is None
    active_list = school_client.get(_players_url(organization["id"]), headers=actor.headers)
    assert active_list.status_code == 200
    assert [item["id"] for item in active_list.json()] == [created["id"]]

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        profile = await session.get(PlayerProfile, created["player_profile_id"])
        membership = await session.get(SchoolPlayerMembership, created["id"])
        assert profile is not None and membership is not None
        assert profile.player_name == "Maya Singh"
        assert profile.total_matches == 0
        assert membership.status == "active"
        assert membership.student_identifier == "STU-002"
        assert (
            await session.scalar(
                select(func.count(SchoolPlayerMembership.id)).where(
                    SchoolPlayerMembership.organization_id == organization["id"],
                    SchoolPlayerMembership.player_profile_id == created["player_profile_id"],
                )
            )
            == 1
        )
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == 1
        assert await session.scalar(select(func.count(User.id))) == (1 if role == "owner" else 2)


def test_roster_status_filter_defaults_active_and_rejects_invalid_values(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "roster-status-filter-owner@example.com")
    organization = create_school(school_client, owner, "Roster Status Filter School")
    active = _create_player(school_client, owner, organization["id"], name="Active Student")
    inactive = _create_player(school_client, owner, organization["id"], name="Inactive Student")
    deactivated = school_client.delete(
        f"{_players_url(organization['id'])}/{inactive['id']}", headers=owner.headers
    )
    assert deactivated.status_code == 204

    default_list = school_client.get(_players_url(organization["id"]), headers=owner.headers)
    explicit_active = school_client.get(
        _players_url(organization["id"]),
        params={"status": "active"},
        headers=owner.headers,
    )
    inactive_list = school_client.get(
        _players_url(organization["id"]),
        params={"status": "inactive"},
        headers=owner.headers,
    )
    all_list = school_client.get(
        _players_url(organization["id"]),
        params={"status": "all"},
        headers=owner.headers,
    )
    invalid = school_client.get(
        _players_url(organization["id"]),
        params={"status": "deleted"},
        headers=owner.headers,
    )

    assert [item["id"] for item in default_list.json()] == [active["id"]]
    assert explicit_active.json() == default_list.json()
    assert [item["id"] for item in inactive_list.json()] == [inactive["id"]]
    assert {item["id"] for item in all_list.json()} == {active["id"], inactive["id"]}
    assert invalid.status_code == 422


async def test_coach_can_create_link_read_and_update_but_not_deactivate(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "roster-coach-owner@example.com")
    coach = register_user(school_client, "roster-coach@example.com")
    organization = create_school(school_client, owner, "Coach Roster School")
    add_membership(school_client, owner, organization["id"], coach.id, "coach")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _add_profile(session_maker, "existing-coach-player", "Existing Player")

    created = _create_player(school_client, coach, organization["id"])
    linked = _link_player(school_client, coach, organization["id"], "existing-coach-player")
    assert linked["player_name"] == "Existing Player"
    assert (
        school_client.get(
            f"{_players_url(organization['id'])}/{created['id']}", headers=coach.headers
        ).status_code
        == 200
    )
    metadata_update = school_client.patch(
        f"{_players_url(organization['id'])}/{created['id']}",
        json={"student_identifier": "COACH-002", "year_group": "Year 10"},
        headers=coach.headers,
    )
    assert metadata_update.status_code == 200
    assert metadata_update.json()["student_identifier"] == "COACH-002"
    assert metadata_update.json()["year_group"] == "Year 10"

    denied_deactivation = school_client.patch(
        f"{_players_url(organization['id'])}/{created['id']}",
        json={"status": "inactive"},
        headers=coach.headers,
    )
    assert denied_deactivation.status_code == 403
    assert denied_deactivation.json() == {"detail": "Insufficient organization role"}

    owner_deactivation = school_client.delete(
        f"{_players_url(organization['id'])}/{created['id']}", headers=owner.headers
    )
    assert owner_deactivation.status_code == 204
    inactive_read = school_client.get(
        _players_url(organization["id"]),
        params={"status": "inactive"},
        headers=coach.headers,
    )
    assert inactive_read.status_code == 200
    assert [item["id"] for item in inactive_read.json()] == [created["id"]]
    denied_reactivation = school_client.patch(
        f"{_players_url(organization['id'])}/{created['id']}",
        json={"status": "active"},
        headers=coach.headers,
    )
    assert denied_reactivation.status_code == 403
    assert denied_reactivation.json() == {"detail": "Insufficient organization role"}

    denied_delete = school_client.delete(
        f"{_players_url(organization['id'])}/{created['id']}", headers=coach.headers
    )
    assert denied_delete.status_code == 403
    assert denied_delete.json() == {"detail": "Insufficient organization role"}


@pytest.mark.parametrize("role", ["scorer", "viewer"])
def test_scorer_and_viewer_have_read_only_school_roster_access(
    school_client: TestClient,
    role: str,
) -> None:
    owner = register_user(school_client, f"roster-{role}-owner@example.com")
    reader = register_user(school_client, f"roster-{role}@example.com")
    organization = create_school(school_client, owner, f"{role.title()} Roster School")
    add_membership(school_client, owner, organization["id"], reader.id, role)
    player = _create_player(school_client, owner, organization["id"])

    assert (
        school_client.get(_players_url(organization["id"]), headers=reader.headers).status_code
        == 200
    )
    assert (
        school_client.get(
            f"{_players_url(organization['id'])}/{player['id']}", headers=reader.headers
        ).status_code
        == 200
    )
    create = school_client.post(
        _players_url(organization["id"]),
        json={"player_name": "Denied"},
        headers=reader.headers,
    )
    link = school_client.post(
        f"{_players_url(organization['id'])}/link",
        json={"player_profile_id": player["player_profile_id"]},
        headers=reader.headers,
    )
    metadata_update = school_client.patch(
        f"{_players_url(organization['id'])}/{player['id']}",
        json={"year_group": "Denied"},
        headers=reader.headers,
    )
    status_update = school_client.patch(
        f"{_players_url(organization['id'])}/{player['id']}",
        json={"status": "inactive"},
        headers=reader.headers,
    )
    remove = school_client.delete(
        f"{_players_url(organization['id'])}/{player['id']}", headers=reader.headers
    )
    assert create.status_code == link.status_code == metadata_update.status_code == 403
    assert status_update.status_code == 403
    assert remove.status_code == 403

    owner_deactivation = school_client.delete(
        f"{_players_url(organization['id'])}/{player['id']}", headers=owner.headers
    )
    assert owner_deactivation.status_code == 204
    inactive_read = school_client.get(
        _players_url(organization["id"]),
        params={"status": "inactive"},
        headers=reader.headers,
    )
    assert inactive_read.status_code == 200
    assert [item["id"] for item in inactive_read.json()] == [player["id"]]
    denied_reactivation = school_client.patch(
        f"{_players_url(organization['id'])}/{player['id']}",
        json={"status": "active"},
        headers=reader.headers,
    )
    assert denied_reactivation.status_code == 403


def test_nonmember_and_cross_tenant_exact_ids_leak_no_roster_metadata(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "roster-tenant-a@example.com")
    owner_b = register_user(school_client, "roster-tenant-b@example.com")
    outsider = register_user(school_client, "roster-outsider@example.com")
    school_a = create_school(school_client, owner_a, "Roster Tenant A")
    school_b = create_school(school_client, owner_b, "Roster Tenant B")
    add_membership(school_client, owner_b, school_b["id"], owner_a.id, "admin")
    player_a = _create_player(school_client, owner_a, school_a["id"], name="Secret Student")
    school_client.delete(
        f"{_players_url(school_a['id'])}/{player_a['id']}", headers=owner_a.headers
    )

    for status_filter in ("inactive", "all"):
        nonmember = school_client.get(
            _players_url(school_a["id"]),
            params={"status": status_filter},
            headers=outsider.headers,
        )
        assert nonmember.status_code == 404
        assert nonmember.json() == {"detail": "Organization not found"}

        cross_tenant_list = school_client.get(
            _players_url(school_b["id"]),
            params={"status": status_filter},
            headers=owner_a.headers,
        )
        assert cross_tenant_list.status_code == 200
        assert cross_tenant_list.json() == []
        assert "secret" not in cross_tenant_list.text.lower()

    for method, kwargs in (
        ("get", {}),
        ("patch", {"json": {"status": "inactive"}}),
        ("delete", {}),
    ):
        response = getattr(school_client, method)(
            f"{_players_url(school_b['id'])}/{player_a['id']}",
            headers=owner_a.headers,
            **kwargs,
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Roster player not found"}
        assert "secret" not in response.text.lower()


async def test_disabled_membership_is_denied(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "roster-gates-owner@example.com")
    organization = create_school(school_client, owner, "Roster Gates School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]

    async with session_maker() as session:
        owner_membership = await session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization["id"],
                OrganizationMembership.user_id == owner.id,
            )
        )
        assert owner_membership is not None
        owner_membership.status = "disabled"
        await session.commit()
    assert (
        school_client.get(_players_url(organization["id"]), headers=owner.headers).status_code
        == 404
    )


async def test_inactive_organization_is_denied(school_client: TestClient) -> None:
    owner = register_user(school_client, "roster-inactive-org-owner@example.com")
    organization = create_school(school_client, owner, "Inactive Roster School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored_organization = await session.get(Organization, organization["id"])
        assert stored_organization is not None
        stored_organization.status = "suspended"
        await session.commit()
    denied = school_client.get(_players_url(organization["id"]), headers=owner.headers)
    assert denied.status_code == 404


@pytest.mark.parametrize("entitlement_state", ["disabled", "missing"])
async def test_disabled_or_missing_entitlement_is_denied(
    school_client: TestClient,
    entitlement_state: str,
) -> None:
    owner = register_user(
        school_client, f"roster-{entitlement_state}-entitlement-owner@example.com"
    )
    organization = create_school(
        school_client, owner, f"{entitlement_state.title()} Roster Entitlement School"
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        assert entitlement is not None
        if entitlement_state == "disabled":
            entitlement.status = "disabled"
        else:
            await session.delete(entitlement)
        await session.commit()
    capability_denied = school_client.get(_players_url(organization["id"]), headers=owner.headers)
    assert capability_denied.status_code == 403
    assert capability_denied.json() == {
        "detail": "Organization capability not enabled: school_master_roster"
    }


@pytest.mark.parametrize("global_authority", ["org_pro", "superuser", "user_org_id"])
async def test_global_or_legacy_authority_does_not_grant_roster_access(
    school_client: TestClient,
    global_authority: str,
) -> None:
    owner = register_user(school_client, f"roster-{global_authority}-owner@example.com")
    outsider = register_user(school_client, f"roster-{global_authority}-outsider@example.com")
    organization = create_school(
        school_client, owner, f"No {global_authority} Roster Bypass School"
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored_outsider = await session.get(User, outsider.id)
        assert stored_outsider is not None
        if global_authority == "org_pro":
            stored_outsider.role = RoleEnum.org_pro
        elif global_authority == "superuser":
            stored_outsider.is_superuser = True
        else:
            stored_outsider.org_id = organization["id"]
        await session.commit()

    denied = school_client.get(_players_url(organization["id"]), headers=outsider.headers)
    assert denied.status_code == 404
    assert denied.json() == {"detail": "Organization not found"}


async def test_exact_link_duplicate_same_name_and_request_spoof_contracts(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "roster-link-owner@example.com")
    organization = create_school(school_client, owner, "Roster Link School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _add_profile(session_maker, "exact-profile", "Same Name")

    linked = _link_player(school_client, owner, organization["id"], "exact-profile")
    duplicate = school_client.post(
        f"{_players_url(organization['id'])}/link",
        json={"player_profile_id": "exact-profile"},
        headers=owner.headers,
    )
    missing = school_client.post(
        f"{_players_url(organization['id'])}/link",
        json={"player_profile_id": "missing-profile"},
        headers=owner.headers,
    )
    same_name = _create_player(school_client, owner, organization["id"], name="Same Name")
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "Player is already on this school roster"}
    assert missing.status_code == 404
    assert same_name["player_profile_id"] != linked["player_profile_id"]

    deactivated = school_client.patch(
        f"{_players_url(organization['id'])}/{linked['id']}",
        json={"status": "inactive"},
        headers=owner.headers,
    )
    assert deactivated.status_code == 200
    inactive_duplicate = school_client.post(
        f"{_players_url(organization['id'])}/link",
        json={"player_profile_id": "exact-profile"},
        headers=owner.headers,
    )
    assert inactive_duplicate.status_code == 409
    assert inactive_duplicate.json() == {"detail": "Player is already on this school roster"}
    reactivated = school_client.patch(
        f"{_players_url(organization['id'])}/{linked['id']}",
        json={"status": "active"},
        headers=owner.headers,
    )
    assert reactivated.status_code == 200

    spoof_create = school_client.post(
        _players_url(organization["id"]),
        json={"player_name": "Spoof", "organization_id": "other"},
        headers=owner.headers,
    )
    spoof_update = school_client.patch(
        f"{_players_url(organization['id'])}/{linked['id']}",
        json={"player_profile_id": same_name["player_profile_id"]},
        headers=owner.headers,
    )
    assert spoof_create.status_code == spoof_update.status_code == 422

    usable = school_client.get(_players_url(organization["id"]), headers=owner.headers)
    assert usable.status_code == 200
    assert len(usable.json()) == 2


async def test_new_profile_and_roster_membership_are_atomic_on_conflict(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = register_user(school_client, "roster-atomic-owner@example.com")
    organization = create_school(school_client, owner, "Roster Atomic School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _add_profile(session_maker, "existing-atomic-profile", "Existing Atomic")
    async with session_maker() as session:
        session.add(
            SchoolPlayerMembership(
                id="forced-membership-conflict",
                organization_id=organization["id"],
                player_profile_id="existing-atomic-profile",
                created_by_user_id=owner.id,
            )
        )
        await session.commit()

    generated_ids = iter(["rolled-back-new-profile", "forced-membership-conflict"])
    monkeypatch.setattr(organization_roster_service, "_new_id", lambda: next(generated_ids))
    async with session_maker() as session:
        with pytest.raises(organization_roster_service.OrganizationRosterServiceError) as exc:
            await organization_roster_service.create_roster_player(
                session,
                organization_id=organization["id"],
                payload=SchoolRosterPlayerCreate(player_name="Must Roll Back"),
                actor_user_id=owner.id,
            )
        assert exc.value.status_code == 409
        assert await session.get(PlayerProfile, "rolled-back-new-profile") is None
        assert await session.scalar(select(func.count(User.id))) == 1


async def test_same_canonical_player_can_belong_to_multiple_school_rosters(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "roster-multi-owner@example.com")
    school_a = create_school(school_client, owner, "Roster Multi A")
    school_b = create_school(school_client, owner, "Roster Multi B")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _add_profile(session_maker, "shared-canonical-player", "Shared Student")
    membership_a = _link_player(school_client, owner, school_a["id"], "shared-canonical-player")
    membership_b = _link_player(school_client, owner, school_b["id"], "shared-canonical-player")
    school_client.delete(
        f"{_players_url(school_a['id'])}/{membership_a['id']}", headers=owner.headers
    )
    retained = school_client.get(
        f"{_players_url(school_b['id'])}/{membership_b['id']}", headers=owner.headers
    )
    assert retained.status_code == 200
    assert retained.json()["player_profile_id"] == "shared-canonical-player"


async def test_postgres_duplicate_link_concurrency_returns_controlled_conflict(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("School roster concurrency contract requires real PostgreSQL")

    owner = register_user(school_client, "roster-concurrent-owner@example.com")
    organization = create_school(school_client, owner, "Concurrent Roster School")
    await _add_profile(session_maker, "concurrent-profile", "Concurrent Player")
    ready = 0
    ready_lock = asyncio.Lock()
    start = asyncio.Event()

    async def link_once() -> tuple[str, int | None]:
        nonlocal ready
        async with session_maker() as session:
            async with ready_lock:
                ready += 1
                if ready == 2:
                    start.set()
            await start.wait()
            try:
                await organization_roster_service.link_roster_player(
                    session,
                    organization_id=organization["id"],
                    payload=SchoolRosterPlayerLink(player_profile_id="concurrent-profile"),
                    actor_user_id=owner.id,
                )
            except organization_roster_service.OrganizationRosterServiceError as exc:
                assert await session.scalar(select(func.count(User.id))) == 1
                return "error", exc.status_code
            return "success", None

    results = await asyncio.gather(link_once(), link_once())
    assert sorted(results) == [("error", 409), ("success", None)]
    async with session_maker() as session:
        count = await session.scalar(
            select(func.count(SchoolPlayerMembership.id)).where(
                SchoolPlayerMembership.organization_id == organization["id"],
                SchoolPlayerMembership.player_profile_id == "concurrent-profile",
            )
        )
        assert count == 1


async def test_postgres_schema_creator_delete_and_organization_delete_contract(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("School roster persistence contract requires real PostgreSQL")

    creator = register_user(school_client, "roster-retained-creator@example.com")
    administrator = register_user(school_client, "roster-retained-admin@example.com")
    organization = create_school(school_client, creator, "Retained Roster School")
    add_membership(school_client, creator, organization["id"], administrator.id, "admin")
    player = _create_player(
        school_client,
        creator,
        organization["id"],
        name="Historical Student",
        student_identifier="HIST-01",
        year_group="2026",
    )

    async with session_maker() as session:
        constraints = {
            row.conname: row.definition
            for row in (
                await session.execute(
                    text(
                        "SELECT conname, pg_get_constraintdef(oid) AS definition "
                        "FROM pg_constraint "
                        "WHERE conrelid = 'school_player_memberships'::regclass"
                    )
                )
            ).all()
        }
        assert (
            "ON DELETE CASCADE"
            in constraints["fk_school_player_memberships_organization_id_organizations"]
        )
        assert (
            "ON DELETE RESTRICT"
            in constraints["fk_school_player_memberships_player_profile_id_player_profiles"]
        )
        assert (
            "ON DELETE SET NULL"
            in constraints["fk_school_player_memberships_created_by_user_id_users"]
        )
        assert "UNIQUE" in constraints["uq_school_player_memberships_organization_player"]
        columns = {
            row.column_name: (row.is_nullable, row.column_default)
            for row in (
                await session.execute(
                    text(
                        "SELECT column_name, is_nullable, column_default "
                        "FROM information_schema.columns "
                        "WHERE table_name = 'school_player_memberships'"
                    )
                )
            ).all()
        }
        assert columns["organization_id"][0] == "NO"
        assert columns["player_profile_id"][0] == "NO"
        assert columns["created_by_user_id"][0] == "YES"
        assert columns["student_identifier"][0] == "YES"
        assert columns["year_group"][0] == "YES"
        assert "active" in columns["status"][1]
        indexes = set(
            (
                await session.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE tablename = 'school_player_memberships'"
                    )
                )
            ).scalars()
        )
        assert {
            "ix_school_player_memberships_organization_id",
            "ix_school_player_memberships_player_profile_id",
            "ix_school_player_memberships_organization_status",
        }.issubset(indexes)

        await session.execute(delete(User).where(User.id == creator.id))
        await session.commit()

    async with session_maker() as session:
        retained = await session.get(SchoolPlayerMembership, player["id"])
        profile = await session.get(PlayerProfile, player["player_profile_id"])
        assert retained is not None and profile is not None
        assert retained.organization_id == organization["id"]
        assert retained.created_by_user_id is None
        assert retained.student_identifier == "HIST-01"
        assert profile.player_name == "Historical Student"

    authorized = school_client.get(
        f"{_players_url(organization['id'])}/{player['id']}",
        headers=administrator.headers,
    )
    assert authorized.status_code == 200
    assert authorized.json()["created_by_user_id"] is None

    async with session_maker() as session:
        stored_organization = await session.get(Organization, organization["id"])
        assert stored_organization is not None
        await session.delete(stored_organization)
        await session.commit()
    async with session_maker() as session:
        assert await session.get(SchoolPlayerMembership, player["id"]) is None
        assert await session.get(PlayerProfile, player["player_profile_id"]) is not None
