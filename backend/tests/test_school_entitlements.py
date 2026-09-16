from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.api.schemas.organizations import OrganizationCreate
from backend.services import organization_service
from backend.services.entitlement_service import can_access_feature
from backend.services.organization_entitlement_service import (
    SCHOOL_FREE_CAPABILITIES,
    SCHOOL_FREE_EXCLUDED_CAPABILITIES,
    OrganizationCapabilityError,
    ensure_school_free_entitlement,
    organization_has_capability,
    provision_existing_school_free_entitlement,
    require_organization_capability,
)
from backend.sql_app.models import (
    Organization,
    OrganizationEntitlement,
    OrganizationMembership,
    RoleEnum,
    User,
)
from backend.tests.school_test_helpers import add_membership, create_school, register_user


def _entitlements_url(organization_id: str) -> str:
    return f"/api/organizations/{organization_id}/entitlements"


async def _entitlement_count(school_client: TestClient, organization_id: str) -> int:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        return int(
            await session.scalar(
                select(func.count(OrganizationEntitlement.id)).where(
                    OrganizationEntitlement.organization_id == organization_id,
                )
            )
            or 0
        )


async def test_new_school_receives_exactly_one_system_school_free_entitlement(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "entitlement-owner@example.com")
    organization = create_school(school_client, owner, "Entitlement School")

    response = school_client.get(_entitlements_url(organization["id"]), headers=owner.headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["organization_id"] == organization["id"]
    assert body["plan_key"] == "school_free"
    assert body["status"] == "active"
    assert body["source"] == "system"
    assert set(body["capabilities"]) == SCHOOL_FREE_CAPABILITIES
    assert set(body["excluded_capabilities"]) == SCHOOL_FREE_EXCLUDED_CAPABILITIES
    assert await _entitlement_count(school_client, organization["id"]) == 1


async def test_school_creation_rolls_back_if_entitlement_provisioning_fails(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = register_user(school_client, "entitlement-rollback@example.com")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]

    async def fail_provisioning(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("forced School Free provisioning failure")

    monkeypatch.setattr(organization_service, "ensure_school_free_entitlement", fail_provisioning)
    async with session_maker() as session:
        actor = await session.get(User, owner.id)
        assert actor is not None
        with pytest.raises(RuntimeError, match="forced School Free"):
            await organization_service.create_organization(
                session,
                payload=OrganizationCreate(name="Entitlement Rollback School"),
                actor=actor,
            )

    async with session_maker() as session:
        organization_count = await session.scalar(
            select(func.count(Organization.id)).where(
                Organization.name == "Entitlement Rollback School",
            )
        )
        membership_count = await session.scalar(
            select(func.count(OrganizationMembership.id)).where(
                OrganizationMembership.user_id == owner.id,
            )
        )
        entitlement_count = await session.scalar(select(func.count(OrganizationEntitlement.id)))
        assert organization_count == 0
        assert membership_count == 0
        assert entitlement_count == 0


async def test_existing_school_provisioning_is_exact_auditable_and_idempotent(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "legacy-school-owner@example.com")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        organization = Organization(
            name="Pre Phase 7C School",
            organization_type="school",
            status="active",
            created_by_user_id=owner.id,
        )
        membership = OrganizationMembership(
            organization=organization,
            user_id=owner.id,
            role="owner",
            status="active",
            created_by_user_id=owner.id,
        )
        session.add_all([organization, membership])
        await session.commit()
        organization_id = organization.id

    async with session_maker() as session:
        entitlement, created = await ensure_school_free_entitlement(
            session,
            organization_id=organization_id,
        )
        assert created is True
        assert entitlement.organization_id == organization_id
        assert entitlement.source == "system"
        repeated_pending, repeated_pending_created = await ensure_school_free_entitlement(
            session,
            organization_id=organization_id,
        )
        assert repeated_pending_created is False
        assert repeated_pending is entitlement
        await session.commit()
        await session.refresh(entitlement)
        entitlement_id = entitlement.id

    async with session_maker() as session:
        repeated, created = await provision_existing_school_free_entitlement(
            session,
            organization_id=organization_id,
        )
        assert created is False
        assert repeated.id == entitlement_id

    assert await _entitlement_count(school_client, organization_id) == 1


async def test_existing_school_provisioning_requires_an_exact_school_id(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        with pytest.raises(ValueError, match="School organization not found"):
            await provision_existing_school_free_entitlement(
                session,
                organization_id="missing-school-id",
            )


async def test_capabilities_are_organization_scoped_and_premium_capabilities_are_denied(
    school_client: TestClient,
) -> None:
    first_owner = register_user(school_client, "capabilities-first@example.com")
    second_owner = register_user(school_client, "capabilities-second@example.com")
    first_school = create_school(school_client, first_owner, "First Capability School")
    second_school = create_school(school_client, second_owner, "Second Capability School")
    add_membership(
        school_client,
        second_owner,
        second_school["id"],
        first_owner.id,
        "admin",
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]

    async with session_maker() as session:
        second_entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == second_school["id"],
            )
        )
        assert second_entitlement is not None
        second_entitlement.status = "disabled"
        await session.commit()

    async with session_maker() as session:
        for capability in SCHOOL_FREE_CAPABILITIES:
            assert await organization_has_capability(
                session,
                organization_id=first_school["id"],
                capability=capability,
            )
        for capability in SCHOOL_FREE_EXCLUDED_CAPABILITIES:
            assert not await organization_has_capability(
                session,
                organization_id=first_school["id"],
                capability=capability,
            )
        assert not await organization_has_capability(
            session,
            organization_id=second_school["id"],
            capability="school_matches_unlimited",
        )
        await require_organization_capability(
            session,
            organization_id=first_school["id"],
            actor_user_id=first_owner.id,
            capability="school_matches_unlimited",
        )
        with pytest.raises(OrganizationCapabilityError):
            await require_organization_capability(
                session,
                organization_id=second_school["id"],
                actor_user_id=first_owner.id,
                capability="school_matches_unlimited",
            )


async def test_capability_requirement_requires_membership_and_never_uses_global_role_bypass(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "capability-owner@example.com")
    outsider = register_user(school_client, "capability-outsider@example.com")
    organization = create_school(school_client, owner, "Capability Membership School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]

    async with session_maker() as session:
        stored_outsider = await session.get(User, outsider.id)
        assert stored_outsider is not None
        stored_outsider.role = RoleEnum.org_pro
        stored_outsider.is_superuser = True
        await session.commit()

    async with session_maker() as session:
        with pytest.raises(organization_service.OrganizationServiceError) as error:
            await require_organization_capability(
                session,
                organization_id=organization["id"],
                actor_user_id=outsider.id,
                capability="school_matches_unlimited",
            )
        assert error.value.status_code == 404

        with pytest.raises(OrganizationCapabilityError):
            await require_organization_capability(
                session,
                organization_id=organization["id"],
                actor_user_id=owner.id,
                capability="advanced_ai",
            )


def test_entitlement_reads_are_tenant_safe_and_owner_admin_only(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "entitlement-owner-a@example.com")
    admin_a = register_user(school_client, "entitlement-admin-a@example.com")
    viewer_a = register_user(school_client, "entitlement-viewer-a@example.com")
    owner_b = register_user(school_client, "entitlement-owner-b@example.com")
    school_a = create_school(school_client, owner_a, "Entitlement A")
    school_b = create_school(school_client, owner_b, "Entitlement B")
    add_membership(school_client, owner_a, school_a["id"], admin_a.id, "admin")
    add_membership(school_client, owner_a, school_a["id"], viewer_a.id, "viewer")

    owner_read = school_client.get(_entitlements_url(school_a["id"]), headers=owner_a.headers)
    admin_read = school_client.get(_entitlements_url(school_a["id"]), headers=admin_a.headers)
    viewer_read = school_client.get(_entitlements_url(school_a["id"]), headers=viewer_a.headers)
    cross_tenant = school_client.get(_entitlements_url(school_b["id"]), headers=admin_a.headers)

    assert owner_read.status_code == 200
    assert admin_read.status_code == 200
    assert viewer_read.status_code == 403
    assert viewer_read.json() == {"detail": "Insufficient organization role"}
    assert cross_tenant.status_code == 404
    assert cross_tenant.json() == {"detail": "Organization not found"}
    assert "entitlement b" not in cross_tenant.text.lower()


async def test_global_roles_do_not_bypass_organization_entitlement_reads(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "entitlement-global-owner@example.com")
    global_user = register_user(school_client, "entitlement-global-user@example.com")
    organization = create_school(school_client, owner, "Entitlement Global Boundary School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]

    async with session_maker() as session:
        stored_user = await session.get(User, global_user.id)
        assert stored_user is not None
        stored_user.role = RoleEnum.org_pro
        stored_user.is_superuser = True
        await session.commit()

    response = school_client.get(_entitlements_url(organization["id"]), headers=global_user.headers)

    assert response.status_code == 404
    assert response.json() == {"detail": "Organization not found"}
    assert "global boundary" not in response.text.lower()


async def test_disabled_membership_and_inactive_organization_cannot_read_entitlements(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "entitlement-inactive-owner@example.com")
    organization = create_school(school_client, owner, "Inactive Entitlement School")
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

    disabled_read = school_client.get(_entitlements_url(organization["id"]), headers=owner.headers)
    assert disabled_read.status_code == 404
    assert disabled_read.json() == {"detail": "Organization not found"}

    async with session_maker() as session:
        membership = await session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization["id"],
                OrganizationMembership.user_id == owner.id,
            )
        )
        stored_organization = await session.get(Organization, organization["id"])
        assert membership is not None
        assert stored_organization is not None
        membership.status = "active"
        stored_organization.status = "suspended"
        await session.commit()

    inactive_read = school_client.get(_entitlements_url(organization["id"]), headers=owner.headers)
    assert inactive_read.status_code == 404
    assert inactive_read.json() == {"detail": "Organization not found"}


async def test_school_entitlement_does_not_upgrade_personal_account_or_expose_mutation_api(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "entitlement-personal-owner@example.com")
    before = school_client.get("/auth/me", headers=owner.headers).json()
    organization = create_school(school_client, owner, "Personal Boundary School")
    after = school_client.get("/auth/me", headers=owner.headers).json()

    assert after["role"] == before["role"] == "free"
    assert after["subscription"] == before["subscription"]
    assert after["org_id"] == before["org_id"] is None

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        user = await session.get(User, owner.id)
        assert user is not None
        assert not await can_access_feature(session, user, "advanced_analytics")

    for method in ("post", "put", "patch", "delete"):
        response = getattr(school_client, method)(
            _entitlements_url(organization["id"]),
            headers=owner.headers,
        )
        assert response.status_code == 405
