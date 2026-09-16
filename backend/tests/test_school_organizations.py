from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.api.schemas.organizations import OrganizationCreate
from backend.services.organization_service import create_organization
from backend.sql_app.models import Organization, User
from backend.tests.school_test_helpers import add_membership, create_school, register_user


def test_create_school_is_atomic_and_preserves_personal_identity(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "owner@example.com")
    before = school_client.get("/auth/me", headers=owner.headers).json()

    organization = create_school(school_client, owner, "  North   Secondary  ")

    assert organization["name"] == "North Secondary"
    assert organization["organization_type"] == "school"
    assert organization["status"] == "active"
    assert organization["membership_role"] == "owner"

    membership = school_client.get(
        f"/api/organizations/{organization['id']}/me",
        headers=owner.headers,
    )
    assert membership.status_code == 200, membership.text
    assert membership.json()["role"] == "owner"
    assert membership.json()["status"] == "active"

    after = school_client.get("/auth/me", headers=owner.headers).json()
    assert after["role"] == before["role"] == "free"
    assert after["subscription"] == before["subscription"]
    assert after["org_id"] == before["org_id"] is None


def test_user_can_belong_to_multiple_schools_with_different_roles(
    school_client: TestClient,
) -> None:
    first_owner = register_user(school_client, "first-owner@example.com")
    multi_member = register_user(school_client, "multi-member@example.com")
    first_school = create_school(school_client, first_owner, "First School")
    second_school = create_school(school_client, multi_member, "Second School")
    add_membership(
        school_client,
        first_owner,
        first_school["id"],
        multi_member.id,
        "coach",
    )

    response = school_client.get("/api/organizations", headers=multi_member.headers)

    assert response.status_code == 200, response.text
    memberships = {item["id"]: item["membership_role"] for item in response.json()}
    assert memberships == {
        first_school["id"]: "coach",
        second_school["id"]: "owner",
    }


@pytest.mark.parametrize("organization_status", ["suspended", "archived"])
async def test_inactive_organization_grants_no_normal_access(
    school_client: TestClient,
    organization_status: str,
) -> None:
    owner = register_user(school_client, "inactive-owner@example.com")
    organization = create_school(school_client, owner, "Inactive School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(Organization, organization["id"])
        assert stored is not None
        stored.status = organization_status
        await session.commit()

    read = school_client.get(
        f"/api/organizations/{organization['id']}",
        headers=owner.headers,
    )
    listed = school_client.get("/api/organizations", headers=owner.headers)

    assert read.status_code == 404
    assert read.json() == {"detail": "Organization not found"}
    assert listed.status_code == 200
    assert listed.json() == []


async def test_failed_owner_creation_rolls_back_organization(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = register_user(school_client, "rollback-owner@example.com")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        actor = await session.get(User, owner.id)
        assert actor is not None

        async def fail_commit() -> None:
            raise RuntimeError("forced owner-membership transaction failure")

        monkeypatch.setattr(session, "commit", fail_commit)
        with pytest.raises(RuntimeError, match="forced owner-membership"):
            await create_organization(
                session,
                payload=OrganizationCreate(name="Rolled Back School"),
                actor=actor,
            )

    async with session_maker() as verification_session:
        count_result = await verification_session.execute(
            select(func.count(Organization.id)).where(Organization.name == "Rolled Back School")
        )
        assert count_result.scalar_one() == 0


async def test_create_school_does_not_change_user_storage_fields(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "storage-owner@example.com")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        before = await session.get(User, owner.id)
        assert before is not None
        baseline: tuple[Any, Any, Any] = (before.role, before.subscription_plan, before.org_id)

    create_school(school_client, owner, "Storage Invariant School")

    async with session_maker() as session:
        after = await session.get(User, owner.id)
        assert after is not None
        assert (after.role, after.subscription_plan, after.org_id) == baseline
