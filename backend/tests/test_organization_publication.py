from __future__ import annotations

import asyncio
import importlib

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from backend.api.schemas.organizations import OrganizationMembershipUpdate
from backend.services import organization_publication_service
from backend.services.organization_publication_service import (
    PUBLIC_IDENTIFIER_PATTERN,
    public_identifier_candidate,
)
from backend.services.organization_service import OrganizationServiceError, update_membership
from backend.sql_app.models import (
    Organization,
    OrganizationMembership,
    OrganizationPublicSettings,
)
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


async def _require_postgres(session_maker: object) -> None:
    async with session_maker() as session:  # type: ignore[operator]
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("PostgreSQL concurrency proof")


async def test_concurrent_missing_settings_recovery_creates_one_identity(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "concurrent-recovery-owner@example.com")
    organization = create_school(school_client, owner, "Concurrent Recovery School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _require_postgres(session_maker)
    async with session_maker() as session:
        await session.execute(
            delete(OrganizationPublicSettings).where(
                OrganizationPublicSettings.organization_id == organization["id"]
            )
        )
        await session.commit()

    async def publish() -> tuple[str, str, int]:
        async with session_maker() as session:
            settings = await organization_publication_service.set_publication_state(
                session,
                organization_id=organization["id"],
                actor_user_id=owner.id,
                publish=True,
            )
            return (
                settings.public_identifier,
                settings.publication_state,
                settings.publication_version,
            )

    outcomes = await asyncio.gather(publish(), publish())
    assert outcomes[0] == outcomes[1]
    assert outcomes[0][1:] == ("published", 2)
    async with session_maker() as session:
        records = (
            await session.scalars(
                select(OrganizationPublicSettings).where(
                    OrganizationPublicSettings.organization_id == organization["id"]
                )
            )
        ).all()
        assert len(records) == 1
        assert records[0].public_identifier == outcomes[0][0]


async def test_concurrent_publish_unpublish_has_one_coherent_durable_state(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "transition-race-owner@example.com")
    publisher = register_user(school_client, "transition-race-publisher@example.com")
    unpublisher = register_user(school_client, "transition-race-unpublisher@example.com")
    organization = create_club(school_client, owner, "Transition Race Club")
    add_membership(school_client, owner, organization["id"], publisher.id, "admin")
    add_membership(school_client, owner, organization["id"], unpublisher.id, "admin")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _require_postgres(session_maker)

    async def transition(*, actor_user_id: str, publish: bool) -> None:
        async with session_maker() as session:
            await organization_publication_service.set_publication_state(
                session,
                organization_id=organization["id"],
                actor_user_id=actor_user_id,
                publish=publish,
            )

    await asyncio.gather(
        transition(actor_user_id=publisher.id, publish=True),
        transition(actor_user_id=unpublisher.id, publish=False),
    )
    async with session_maker() as session:
        settings = await session.get(OrganizationPublicSettings, organization["id"])
        assert settings is not None
        assert settings.published_at is not None
        assert settings.published_by_user_id == publisher.id
        if settings.publication_state == "published":
            assert settings.publication_version == 2
            assert settings.updated_by_user_id == publisher.id
            assert settings.unpublished_at is None
            assert settings.unpublished_by_user_id is None
        else:
            assert settings.publication_state == "unpublished"
            assert settings.publication_version == 3
            assert settings.updated_by_user_id == unpublisher.id
            assert settings.unpublished_at is not None
            assert settings.unpublished_by_user_id == unpublisher.id


async def test_membership_revocation_winning_race_prevents_publication(
    school_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = register_user(school_client, "revocation-race-owner@example.com")
    admin = register_user(school_client, "revocation-race-admin@example.com")
    organization = create_school(school_client, owner, "Revocation Race School")
    membership = add_membership(school_client, owner, organization["id"], admin.id, "admin")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _require_postgres(session_maker)
    publication_lock_attempted = asyncio.Event()
    original_lock = organization_publication_service._lock_active_organization

    async def observed_publication_lock(*args: object, **kwargs: object) -> Organization:
        publication_lock_attempted.set()
        return await original_lock(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        organization_publication_service,
        "_lock_active_organization",
        observed_publication_lock,
    )
    async with session_maker() as revocation_session:
        locked = await revocation_session.scalar(
            select(Organization).where(Organization.id == organization["id"]).with_for_update()
        )
        assert locked is not None

        async def publish() -> None:
            async with session_maker() as publication_session:
                await organization_publication_service.set_publication_state(
                    publication_session,
                    organization_id=organization["id"],
                    actor_user_id=admin.id,
                    publish=True,
                )

        publication_task = asyncio.create_task(publish())
        await asyncio.wait_for(publication_lock_attempted.wait(), timeout=5)
        await update_membership(
            revocation_session,
            organization_id=organization["id"],
            membership_id=membership["id"],
            payload=OrganizationMembershipUpdate(status="disabled"),
            actor_user_id=owner.id,
        )
        with pytest.raises(OrganizationServiceError) as exc_info:
            await publication_task
        assert exc_info.value.status_code == 404

    async with session_maker() as session:
        settings = await session.get(OrganizationPublicSettings, organization["id"])
        target = await session.get(OrganizationMembership, membership["id"])
        assert settings is not None and settings.publication_state == "unpublished"
        assert target is not None and target.status == "disabled"


async def test_concurrent_identifier_collision_uses_database_retry_and_fallback(
    school_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = register_user(school_client, "collision-race-owner@example.com")
    first = create_school(school_client, owner, "Collision School")
    second = create_club(school_client, owner, "Collision Club")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _require_postgres(session_maker)
    async with session_maker() as session:
        await session.execute(
            delete(OrganizationPublicSettings).where(
                OrganizationPublicSettings.organization_id.in_([first["id"], second["id"]])
            )
        )
        await session.commit()

    forced_candidate = "org_ffffffffffffffffffffffff"
    original_candidate = public_identifier_candidate

    def colliding_candidate(organization_id: str, collision_attempt: int = 0) -> str:
        if collision_attempt == 0:
            return forced_candidate
        return original_candidate(organization_id, collision_attempt)

    monkeypatch.setattr(
        organization_publication_service,
        "public_identifier_candidate",
        colliding_candidate,
    )

    async def publish(organization_id: str) -> None:
        async with session_maker() as session:
            await organization_publication_service.set_publication_state(
                session,
                organization_id=organization_id,
                actor_user_id=owner.id,
                publish=True,
            )

    await asyncio.gather(publish(first["id"]), publish(second["id"]))
    async with session_maker() as session:
        records = (
            await session.scalars(
                select(OrganizationPublicSettings).where(
                    OrganizationPublicSettings.organization_id.in_([first["id"], second["id"]])
                )
            )
        ).all()
        identifiers = {record.public_identifier for record in records}
        assert len(records) == len(identifiers) == 2
        assert {record.publication_state for record in records} == {"published"}
        assert forced_candidate in identifiers
        assert all(PUBLIC_IDENTIFIER_PATTERN.fullmatch(identifier) for identifier in identifiers)


async def test_migration_backfill_assigns_unique_identifiers_to_existing_organizations(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "backfill-owner@example.com")
    organizations = [
        create_school(school_client, owner, "Backfill School"),
        create_club(school_client, owner, "Backfill Club One"),
        create_club(school_client, owner, "Backfill Club Two"),
    ]
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _require_postgres(session_maker)
    migration = importlib.import_module(
        "backend.alembic.versions.20260929030000_add_organization_public_settings"
    )
    organization_ids = [organization["id"] for organization in organizations]
    async with session_maker() as session:
        await session.execute(
            delete(OrganizationPublicSettings).where(
                OrganizationPublicSettings.organization_id.in_(organization_ids)
            )
        )
        await session.execute(text(migration.ORGANIZATION_PUBLIC_SETTINGS_BACKFILL_SQL))
        await session.commit()
        rows = (
            await session.execute(
                select(
                    func.count(OrganizationPublicSettings.organization_id),
                    func.count(func.distinct(OrganizationPublicSettings.public_identifier)),
                ).where(OrganizationPublicSettings.organization_id.in_(organization_ids))
            )
        ).one()
        assert rows == (3, 3)
        identifiers = (
            await session.scalars(
                select(OrganizationPublicSettings.public_identifier).where(
                    OrganizationPublicSettings.organization_id.in_(organization_ids)
                )
            )
        ).all()
        assert all(PUBLIC_IDENTIFIER_PATTERN.fullmatch(identifier) for identifier in identifiers)
