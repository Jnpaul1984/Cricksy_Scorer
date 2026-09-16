from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.api.schemas.organizations import (
    OrganizationMembershipCreate,
    OrganizationMembershipUpdate,
)
from backend.services.organization_service import (
    OrganizationServiceError,
)
from backend.services.organization_service import (
    add_membership as add_membership_service,
)
from backend.services.organization_service import (
    update_membership as update_membership_service,
)
from backend.sql_app.database import get_engine, get_session_local
from backend.sql_app.models import OrganizationMembership
from backend.tests.school_test_helpers import add_membership, create_school, register_user


@pytest.mark.parametrize("role", ["viewer", "scorer", "coach"])
def test_non_manager_roles_cannot_manage_memberships(
    school_client: TestClient,
    role: str,
) -> None:
    owner = register_user(school_client, f"{role}-owner@example.com")
    member = register_user(school_client, f"{role}@example.com")
    target = register_user(school_client, f"{role}-target@example.com")
    organization = create_school(school_client, owner, f"{role.title()} School")
    add_membership(school_client, owner, organization["id"], member.id, role)

    listed = school_client.get(
        f"/api/organizations/{organization['id']}/memberships",
        headers=member.headers,
    )
    created = school_client.post(
        f"/api/organizations/{organization['id']}/memberships",
        json={"user_id": target.id, "role": "viewer"},
        headers=member.headers,
    )

    assert listed.status_code == 403
    assert created.status_code == 403
    assert listed.json() == {"detail": "Insufficient organization role"}
    assert created.json() == {"detail": "Insufficient organization role"}


def test_admin_manages_non_owner_roles_but_not_owner_authority(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "admin-boundary-owner@example.com")
    admin = register_user(school_client, "admin-boundary@example.com")
    member = register_user(school_client, "admin-target@example.com")
    organization = create_school(school_client, owner, "Admin Boundary School")
    admin_membership = add_membership(
        school_client,
        owner,
        organization["id"],
        admin.id,
        "admin",
    )

    member_membership = add_membership(
        school_client,
        admin,
        organization["id"],
        member.id,
        "viewer",
    )
    promoted = school_client.patch(
        f"/api/organizations/{organization['id']}/memberships/{member_membership['id']}",
        json={"role": "coach"},
        headers=admin.headers,
    )
    assert promoted.status_code == 200, promoted.text
    assert promoted.json()["role"] == "coach"

    grant_owner = school_client.patch(
        f"/api/organizations/{organization['id']}/memberships/{member_membership['id']}",
        json={"role": "owner"},
        headers=admin.headers,
    )
    alter_owner = school_client.patch(
        f"/api/organizations/{organization['id']}/memberships/{organization_owner_id(school_client, owner, organization['id'])}",
        json={"role": "viewer"},
        headers=admin.headers,
    )
    disable_admin = school_client.delete(
        f"/api/organizations/{organization['id']}/memberships/{admin_membership['id']}",
        headers=owner.headers,
    )

    assert grant_owner.status_code == 403
    assert alter_owner.status_code == 403
    assert disable_admin.status_code == 200
    assert disable_admin.json()["status"] == "disabled"


def organization_owner_id(
    client: TestClient,
    owner,
    organization_id: str,
) -> str:
    response = client.get(
        f"/api/organizations/{organization_id}/me",
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["id"]


def test_final_active_owner_cannot_be_demoted_disabled_or_self_removed(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "last-owner@example.com")
    organization = create_school(school_client, owner, "Last Owner School")
    membership_id = organization_owner_id(school_client, owner, organization["id"])

    demote = school_client.patch(
        f"/api/organizations/{organization['id']}/memberships/{membership_id}",
        json={"role": "admin"},
        headers=owner.headers,
    )
    disable = school_client.patch(
        f"/api/organizations/{organization['id']}/memberships/{membership_id}",
        json={"status": "disabled"},
        headers=owner.headers,
    )
    remove = school_client.delete(
        f"/api/organizations/{organization['id']}/memberships/{membership_id}",
        headers=owner.headers,
    )

    for response in (demote, disable, remove):
        assert response.status_code == 409
        assert response.json() == {"detail": "Organization must retain an active owner"}


def test_owner_can_transfer_authority_before_disabling_self(
    school_client: TestClient,
) -> None:
    first_owner = register_user(school_client, "transfer-first@example.com")
    successor = register_user(school_client, "transfer-successor@example.com")
    organization = create_school(school_client, first_owner, "Transfer School")
    successor_membership = add_membership(
        school_client,
        first_owner,
        organization["id"],
        successor.id,
        "admin",
    )
    promote = school_client.patch(
        f"/api/organizations/{organization['id']}/memberships/{successor_membership['id']}",
        json={"role": "owner"},
        headers=first_owner.headers,
    )
    assert promote.status_code == 200, promote.text
    assert promote.json()["role"] == "owner"

    first_membership_id = organization_owner_id(
        school_client,
        first_owner,
        organization["id"],
    )
    disable = school_client.delete(
        f"/api/organizations/{organization['id']}/memberships/{first_membership_id}",
        headers=first_owner.headers,
    )
    assert disable.status_code == 200, disable.text
    assert disable.json()["status"] == "disabled"

    denied = school_client.get(
        f"/api/organizations/{organization['id']}",
        headers=first_owner.headers,
    )
    successor_access = school_client.get(
        f"/api/organizations/{organization['id']}",
        headers=successor.headers,
    )
    assert denied.status_code == 404
    assert successor_access.status_code == 200


@pytest.mark.skipif(
    get_engine().dialect.name != "postgresql",
    reason="Owner mutation serialization requires real PostgreSQL",
)
async def test_concurrent_owner_demotions_retain_an_active_owner(
    school_client: TestClient,
) -> None:
    first_owner = register_user(school_client, "race-first-owner@example.com")
    second_owner = register_user(school_client, "race-second-owner@example.com")
    organization = create_school(school_client, first_owner, "Owner Race School")
    first_membership_id = organization_owner_id(
        school_client,
        first_owner,
        organization["id"],
    )
    second_membership = add_membership(
        school_client,
        first_owner,
        organization["id"],
        second_owner.id,
        "admin",
    )
    promoted = school_client.patch(
        f"/api/organizations/{organization['id']}/memberships/{second_membership['id']}",
        json={"role": "owner"},
        headers=first_owner.headers,
    )
    assert promoted.status_code == 200, promoted.text

    session_maker = get_session_local()
    start = asyncio.Event()
    ready = 0
    ready_lock = asyncio.Lock()

    async def demote_self(membership_id: str, actor_user_id: str) -> object:
        nonlocal ready
        async with session_maker() as session:
            async with ready_lock:
                ready += 1
                if ready == 2:
                    start.set()
            await start.wait()
            try:
                return await update_membership_service(
                    session,
                    organization_id=organization["id"],
                    membership_id=membership_id,
                    payload=OrganizationMembershipUpdate(role="admin"),
                    actor_user_id=actor_user_id,
                )
            except OrganizationServiceError as exc:
                return exc

    outcomes = await asyncio.wait_for(
        asyncio.gather(
            demote_self(first_membership_id, first_owner.id),
            demote_self(second_membership["id"], second_owner.id),
        ),
        timeout=10,
    )
    successes = [item for item in outcomes if isinstance(item, OrganizationMembership)]
    conflicts = [
        item
        for item in outcomes
        if isinstance(item, OrganizationServiceError)
        and item.status_code == 409
        and item.detail == "Organization must retain an active owner"
    ]
    assert len(successes) == 1
    assert len(conflicts) == 1

    async with session_maker() as session:
        active_owner_count = await session.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.organization_id == organization["id"],
                OrganizationMembership.role == "owner",
                OrganizationMembership.status == "active",
            )
        )
        assert active_owner_count == 1


def test_exact_user_membership_creation_has_no_directory_behavior(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "exact-owner@example.com")
    organization = create_school(school_client, owner, "Exact User School")

    response = school_client.post(
        f"/api/organizations/{organization['id']}/memberships",
        json={"user_id": "does-not-exist", "role": "viewer"},
        headers=owner.headers,
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "User not found"}
    assert "email" not in response.text.lower()
    assert "users" not in response.text.lower()


def test_membership_listing_is_paginated(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "pagination-owner@example.com")
    organization = create_school(school_client, owner, "Pagination School")
    for number in range(3):
        member = register_user(school_client, f"pagination-{number}@example.com")
        add_membership(
            school_client,
            owner,
            organization["id"],
            member.id,
            "viewer",
        )

    response = school_client.get(
        f"/api/organizations/{organization['id']}/memberships?limit=2&offset=1",
        headers=owner.headers,
    )

    assert response.status_code == 200, response.text
    assert response.json()["limit"] == 2
    assert response.json()["offset"] == 1
    assert response.json()["total"] == 4
    assert len(response.json()["items"]) == 2


@pytest.mark.skipif(
    get_engine().dialect.name != "postgresql",
    reason="Concurrent uniqueness validation requires real PostgreSQL",
)
async def test_concurrent_duplicate_membership_is_one_row_and_one_controlled_conflict(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "concurrent-owner@example.com")
    target = register_user(school_client, "concurrent-target@example.com")
    organization = create_school(school_client, owner, "Concurrent School")
    session_maker = get_session_local()

    async def attempt() -> object:
        async with session_maker() as session:
            try:
                return await add_membership_service(
                    session,
                    organization_id=organization["id"],
                    payload=OrganizationMembershipCreate(user_id=target.id, role="viewer"),
                    actor_user_id=owner.id,
                )
            except OrganizationServiceError as exc:
                return exc

    outcomes = await asyncio.gather(attempt(), attempt())
    successes = [item for item in outcomes if isinstance(item, OrganizationMembership)]
    conflicts = [
        item
        for item in outcomes
        if isinstance(item, OrganizationServiceError) and item.status_code == 409
    ]
    assert len(successes) == 1
    assert len(conflicts) == 1

    async with session_maker() as session:
        count_result = await session.execute(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.organization_id == organization["id"],
                OrganizationMembership.user_id == target.id,
            )
        )
        assert count_result.scalar_one() == 1
