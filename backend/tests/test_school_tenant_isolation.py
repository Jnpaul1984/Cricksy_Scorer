from __future__ import annotations

from fastapi.testclient import TestClient

from backend.sql_app.models import RoleEnum, User
from backend.tests.school_test_helpers import add_membership, create_school, register_user


def test_non_member_cannot_read_school_and_denial_leaks_no_metadata(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "private-owner@example.com")
    outsider = register_user(school_client, "private-outsider@example.com")
    organization = create_school(school_client, owner, "Confidential Academy")

    response = school_client.get(
        f"/api/organizations/{organization['id']}",
        headers=outsider.headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Organization not found"}
    body = response.text.lower()
    assert "confidential" not in body
    assert "academy" not in body
    assert "owner" not in body
    assert "member" not in body


def test_school_a_admin_cannot_read_or_mutate_school_b(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "isolation-owner-a@example.com")
    admin_a = register_user(school_client, "isolation-admin-a@example.com")
    owner_b = register_user(school_client, "isolation-owner-b@example.com")
    member_b = register_user(school_client, "isolation-member-b@example.com")
    school_a = create_school(school_client, owner_a, "School A")
    school_b = create_school(school_client, owner_b, "School B Secret")
    add_membership(school_client, owner_a, school_a["id"], admin_a.id, "admin")
    membership_b = add_membership(
        school_client,
        owner_b,
        school_b["id"],
        member_b.id,
        "viewer",
    )

    listed = school_client.get(
        f"/api/organizations/{school_b['id']}/memberships",
        headers=admin_a.headers,
    )
    mutated = school_client.patch(
        f"/api/organizations/{school_b['id']}/memberships/{membership_b['id']}",
        json={"role": "coach"},
        headers=admin_a.headers,
    )

    for response in (listed, mutated):
        assert response.status_code == 404
        assert response.json() == {"detail": "Organization not found"}
        assert "school b" not in response.text.lower()
        assert member_b.id not in response.text
        assert membership_b["id"] not in response.text


def test_membership_id_from_other_school_is_not_resolved_outside_scope(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "scoped-owner-a@example.com")
    owner_b = register_user(school_client, "scoped-owner-b@example.com")
    target_b = register_user(school_client, "scoped-target-b@example.com")
    school_a = create_school(school_client, owner_a, "Scoped A")
    school_b = create_school(school_client, owner_b, "Scoped B")
    membership_b = add_membership(
        school_client,
        owner_b,
        school_b["id"],
        target_b.id,
        "viewer",
    )

    response = school_client.patch(
        f"/api/organizations/{school_a['id']}/memberships/{membership_b['id']}",
        json={"role": "coach"},
        headers=owner_a.headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Membership not found"}
    assert target_b.id not in response.text
    assert school_b["id"] not in response.text


def test_same_user_has_independent_authority_in_each_school(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "role-scope-owner-a@example.com")
    owner_b = register_user(school_client, "role-scope-owner-b@example.com")
    shared_user = register_user(school_client, "role-scope-shared@example.com")
    target_a = register_user(school_client, "role-scope-target-a@example.com")
    target_b = register_user(school_client, "role-scope-target-b@example.com")
    school_a = create_school(school_client, owner_a, "Role Scope A")
    school_b = create_school(school_client, owner_b, "Role Scope B")
    add_membership(school_client, owner_a, school_a["id"], shared_user.id, "admin")
    add_membership(school_client, owner_b, school_b["id"], shared_user.id, "viewer")

    allowed = school_client.post(
        f"/api/organizations/{school_a['id']}/memberships",
        json={"user_id": target_a.id, "role": "viewer"},
        headers=shared_user.headers,
    )
    denied = school_client.post(
        f"/api/organizations/{school_b['id']}/memberships",
        json={"user_id": target_b.id, "role": "viewer"},
        headers=shared_user.headers,
    )

    assert allowed.status_code == 201, allowed.text
    assert denied.status_code == 403
    assert denied.json() == {"detail": "Insufficient organization role"}


async def test_global_org_pro_role_is_not_an_organization_bypass(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "org-pro-owner@example.com")
    global_org_user = register_user(school_client, "global-org-pro@example.com")
    organization = create_school(school_client, owner, "Membership Only School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored_user = await session.get(User, global_org_user.id)
        assert stored_user is not None
        stored_user.role = RoleEnum.org_pro
        await session.commit()

    response = school_client.get(
        f"/api/organizations/{organization['id']}",
        headers=global_org_user.headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Organization not found"}
