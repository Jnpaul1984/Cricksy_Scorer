from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.services.organization_publication_service import public_identifier_candidate
from backend.sql_app.models import Organization, OrganizationPublicSettings
from backend.tests.school_test_helpers import (
    add_membership,
    create_club,
    create_school,
    register_user,
)


@pytest.mark.parametrize("organization_kind", ["school", "club"])
def test_school_and_club_default_private_and_owner_controls_publication(
    school_client: TestClient, organization_kind: str
) -> None:
    owner = register_user(school_client, f"{organization_kind}-publication-owner@example.com")
    create = create_school if organization_kind == "school" else create_club
    organization = create(school_client, owner, f"North {organization_kind.title()}")

    settings = school_client.get(
        f"/api/organizations/{organization['id']}/public-settings", headers=owner.headers
    )
    assert settings.status_code == 200
    assert settings.json()["publication_state"] == "unpublished"
    identifier = settings.json()["public_identifier"]
    assert school_client.get(f"/api/public/organizations/{identifier}").status_code == 404

    published = school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish",
        headers=owner.headers,
    )
    repeated = school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish",
        headers=owner.headers,
    )
    assert published.status_code == repeated.status_code == 200
    assert repeated.json() == published.json()

    public = school_client.get(f"/api/public/organizations/{identifier}")
    assert public.status_code == 200
    assert public.json() == {
        "public_identifier": identifier,
        "display_name": f"North {organization_kind.title()}",
        "organization_type": organization_kind,
    }

    unpublished = school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/unpublish",
        headers=owner.headers,
    )
    repeated_unpublish = school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/unpublish",
        headers=owner.headers,
    )
    assert unpublished.status_code == repeated_unpublish.status_code == 200
    assert repeated_unpublish.json() == unpublished.json()
    assert school_client.get(f"/api/public/organizations/{identifier}").status_code == 404


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("admin", 200), ("coach", 403), ("scorer", 403), ("viewer", 403)],
)
def test_only_current_owner_or_admin_may_publish(
    school_client: TestClient, role: str, expected_status: int
) -> None:
    owner = register_user(school_client, f"authority-owner-{role}@example.com")
    member = register_user(school_client, f"authority-member-{role}@example.com")
    organization = create_school(school_client, owner, "Authority School")
    add_membership(school_client, owner, organization["id"], member.id, role)

    response = school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish",
        headers=member.headers,
    )
    assert response.status_code == expected_status


def test_nonmember_cross_tenant_and_disabled_membership_fail_closed(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "publication-owner@example.com")
    outsider = register_user(school_client, "publication-outsider@example.com")
    admin = register_user(school_client, "publication-disabled@example.com")
    organization = create_club(school_client, owner, "Private Club")
    membership = add_membership(school_client, owner, organization["id"], admin.id, "admin")

    for suffix in ("public-settings", "public-settings/publish"):
        method = school_client.get if suffix == "public-settings" else school_client.put
        response = method(
            f"/api/organizations/{organization['id']}/{suffix}", headers=outsider.headers
        )
        assert response.status_code == 404

    disabled = school_client.patch(
        f"/api/organizations/{organization['id']}/memberships/{membership['id']}",
        json={"status": "disabled"},
        headers=owner.headers,
    )
    assert disabled.status_code == 200
    denied = school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish",
        headers=admin.headers,
    )
    assert denied.status_code == 404


async def test_public_identifier_is_stable_unique_and_db_enforced(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "identifier-owner@example.com")
    first = create_school(school_client, owner, "Rename-safe School")
    second = create_club(school_client, owner, "Other Club")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        first_settings = await session.get(OrganizationPublicSettings, first["id"])
        second_settings = await session.get(OrganizationPublicSettings, second["id"])
        assert first_settings is not None and second_settings is not None
        assert first_settings.public_identifier != second_settings.public_identifier
        identifier = first_settings.public_identifier
        organization = await session.get(Organization, first["id"])
        assert organization is not None
        organization.name = "Renamed School"
        await session.commit()
        await session.refresh(first_settings)
        assert first_settings.public_identifier == identifier

        second_settings.public_identifier = identifier
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


def test_identifier_collision_candidates_are_deterministic_and_distinct() -> None:
    organization_id = "tenant-id"
    assert public_identifier_candidate(organization_id) == public_identifier_candidate(
        organization_id
    )
    assert public_identifier_candidate(organization_id, 1) != public_identifier_candidate(
        organization_id, 0
    )


def test_malformed_and_missing_public_identifiers_share_safe_not_found(
    school_client: TestClient,
) -> None:
    malformed = school_client.get("/api/public/organizations/not-a-valid-identifier")
    missing = school_client.get("/api/public/organizations/org_000000000000000000000000")
    assert malformed.status_code == missing.status_code == 404
    assert malformed.json() == missing.json() == {"detail": "Public page not found"}


async def test_one_settings_record_per_organization(school_client: TestClient) -> None:
    owner = register_user(school_client, "one-contract-owner@example.com")
    organization = create_school(school_client, owner, "One Contract School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        records = (
            await session.scalars(
                select(OrganizationPublicSettings).where(
                    OrganizationPublicSettings.organization_id == organization["id"]
                )
            )
        ).all()
        assert len(records) == 1
