from __future__ import annotations

import asyncio
import importlib
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from backend.api.schemas.organizations import OrganizationMembershipUpdate
from backend.services import organization_publication_service, organization_team_service
from backend.services.organization_publication_service import (
    PUBLIC_IDENTIFIER_PATTERN,
    public_competition_key_candidate,
    public_identifier_candidate,
    team_public_identifier_candidate,
)
from backend.services.organization_service import OrganizationServiceError, update_membership
from backend.sql_app.models import (
    Fixture,
    Game,
    GameStatus,
    Organization,
    OrganizationEntitlement,
    OrganizationMembership,
    OrganizationPublicSettings,
    OrganizationTeamPublication,
    OrganizationTeamPublicationAudit,
    Team,
    Tournament,
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


@pytest.mark.parametrize("organization_kind", ["school", "club"])
def test_team_publication_is_owner_admin_only_tenant_bound_and_revocable(
    school_client: TestClient, organization_kind: str
) -> None:
    owner = register_user(school_client, f"team-public-owner-{organization_kind}@example.com")
    admin = register_user(school_client, f"team-public-admin-{organization_kind}@example.com")
    coach = register_user(school_client, f"team-public-coach-{organization_kind}@example.com")
    outsider = register_user(school_client, f"team-public-outsider-{organization_kind}@example.com")
    create = create_school if organization_kind == "school" else create_club
    organization = create(school_client, owner, f"{organization_kind} Team Public")
    add_membership(school_client, owner, organization["id"], admin.id, "admin")
    add_membership(school_client, owner, organization["id"], coach.id, "coach")
    team_response = school_client.post(
        f"/api/organizations/{organization['id']}/teams", json={"name": "Private XI"}, headers=owner.headers
    )
    assert team_response.status_code == 201, team_response.text
    team = team_response.json()
    team_identifier = team_public_identifier_candidate(team["id"])
    public_path = f"/api/public/organizations/{public_identifier_candidate(organization['id'])}/teams/{team_identifier}"
    assert school_client.get(public_path).status_code == 404

    for actor in (coach, outsider):
        denied = school_client.put(
            f"/api/organizations/{organization['id']}/teams/{team['id']}/public-publication/publish",
            headers=actor.headers,
        )
        assert denied.status_code in {403, 404}

    other = create(school_client, owner, f"Other {organization_kind} Tenant")
    foreign = school_client.post(
        f"/api/organizations/{other['id']}/teams", json={"name": "Foreign XI"}, headers=owner.headers
    ).json()
    cross_tenant = school_client.put(
        f"/api/organizations/{organization['id']}/teams/{foreign['id']}/public-publication/publish",
        headers=owner.headers,
    )
    assert cross_tenant.status_code == 404

    published = school_client.put(
        f"/api/organizations/{organization['id']}/teams/{team['id']}/public-publication/publish",
        headers=admin.headers,
    )
    assert published.status_code == 200
    assert published.json()["public_identifier"] == team_identifier
    # The parent organization is an independent, fail-closed publication gate.
    assert school_client.get(public_path).status_code == 404
    assert school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish", headers=owner.headers
    ).status_code == 200
    public = school_client.get(public_path)
    assert public.status_code == 200
    assert public.json() == {
        "public_identifier": team_identifier,
        "display_name": "Private XI",
        "aggregate_stats": {"published_games": 0},
    }
    assert "player" not in public.text.lower() and "roster" not in public.text.lower()
    assert school_client.put(
        f"/api/organizations/{organization['id']}/teams/{team['id']}/public-publication/unpublish",
        headers=owner.headers,
    ).status_code == 200
    assert school_client.get(public_path).status_code == 404
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async def audit_rows() -> list[OrganizationTeamPublicationAudit]:
        async with session_maker() as session:
            return (await session.scalars(select(OrganizationTeamPublicationAudit).where(OrganizationTeamPublicationAudit.team_id == team["id"]).order_by(OrganizationTeamPublicationAudit.id))).all()
    history = asyncio.run(audit_rows())
    assert [(row.action, row.actor_user_id, row.publication_version) for row in history] == [
        ("published", admin.id, 2), ("unpublished", owner.id, 3)
    ]


@pytest.mark.parametrize("organization_kind", ["school", "club"])
def test_archiving_team_revokes_publication_and_cannot_be_republished(
    school_client: TestClient, organization_kind: str
) -> None:
    owner = register_user(school_client, f"team-archive-owner-{organization_kind}@example.com")
    create = create_school if organization_kind == "school" else create_club
    organization = create(school_client, owner, f"{organization_kind} Archive Public")
    other_organization = create(school_client, owner, f"Other {organization_kind} Archive")
    team = school_client.post(
        f"/api/organizations/{organization['id']}/teams",
        json={"name": "Archive XI"},
        headers=owner.headers,
    ).json()
    other_team = school_client.post(
        f"/api/organizations/{other_organization['id']}/teams",
        json={"name": "Other Archive XI"},
        headers=owner.headers,
    ).json()
    public_path = (
        f"/api/public/organizations/{public_identifier_candidate(organization['id'])}"
        f"/teams/{team_public_identifier_candidate(team['id'])}"
    )
    other_public_path = (
        f"/api/public/organizations/{public_identifier_candidate(other_organization['id'])}"
        f"/teams/{team_public_identifier_candidate(other_team['id'])}"
    )
    for organization_item, team_item in ((organization, team), (other_organization, other_team)):
        assert school_client.put(
            f"/api/organizations/{organization_item['id']}/public-settings/publish",
            headers=owner.headers,
        ).status_code == 200
        assert school_client.put(
            f"/api/organizations/{organization_item['id']}/teams/{team_item['id']}"
            "/public-publication/publish",
            headers=owner.headers,
        ).status_code == 200
    assert school_client.get(public_path).status_code == 200
    assert school_client.get(other_public_path).status_code == 200

    # Tenant binding is checked before archival side effects.
    assert school_client.delete(
        f"/api/organizations/{organization['id']}/teams/{other_team['id']}",
        headers=owner.headers,
    ).status_code == 404
    assert school_client.get(other_public_path).status_code == 200

    assert school_client.delete(
        f"/api/organizations/{organization['id']}/teams/{team['id']}", headers=owner.headers
    ).status_code == 204
    assert school_client.get(public_path).status_code == 404
    assert school_client.put(
        f"/api/organizations/{organization['id']}/teams/{team['id']}/public-publication/publish",
        headers=owner.headers,
    ).status_code == 409

    session_maker = school_client.session_maker  # type: ignore[attr-defined]

    async def audit_rows() -> list[OrganizationTeamPublicationAudit]:
        async with session_maker() as session:
            return (
                await session.scalars(
                    select(OrganizationTeamPublicationAudit)
                    .where(OrganizationTeamPublicationAudit.team_id == team["id"])
                    .order_by(OrganizationTeamPublicationAudit.id)
                )
            ).all()

    history = asyncio.run(audit_rows())
    assert [(row.action, row.actor_user_id, row.publication_version) for row in history] == [
        ("published", owner.id, 2),
        ("archived", owner.id, 3),
    ]


@pytest.mark.skipif(
    os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="requires migrated PostgreSQL row-lock semantics",
)
def test_postgres_archive_publish_race_never_leaves_archived_team_published(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-archive-race-owner@example.com")
    organization = create_school(school_client, owner, "Archive Race School")
    team = school_client.post(
        f"/api/organizations/{organization['id']}/teams",
        json={"name": "Race XI"},
        headers=owner.headers,
    ).json()
    assert school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish",
        headers=owner.headers,
    ).status_code == 200
    session_maker = school_client.session_maker  # type: ignore[attr-defined]

    async def race() -> tuple[object | None, object | None]:
        gate = asyncio.Event()

        async def publish() -> object | None:
            async with session_maker() as session:
                await gate.wait()
                try:
                    return await organization_publication_service.set_team_publication_state(
                        session,
                        organization_id=organization["id"],
                        team_id=team["id"],
                        actor_user_id=owner.id,
                        publish=True,
                    )
                except OrganizationServiceError as exc:
                    return exc

        async def archive() -> object | None:
            async with session_maker() as session:
                await gate.wait()
                try:
                    await organization_team_service.archive_team(
                        session,
                        organization_id=organization["id"],
                        team_id=team["id"],
                        actor_user_id=owner.id,
                    )
                    return None
                except organization_team_service.OrganizationTeamServiceError as exc:
                    return exc

        gate.set()
        return tuple(await asyncio.gather(publish(), archive()))

    publish_result, archive_result = asyncio.run(race())
    assert archive_result is None
    assert isinstance(publish_result, OrganizationTeamPublication) or (
        isinstance(publish_result, OrganizationServiceError)
        and publish_result.status_code == 409
    )

    async def final_state() -> tuple[Team, OrganizationTeamPublication | None, list[str]]:
        async with session_maker() as session:
            persisted_team = await session.get(Team, team["id"])
            publication = await session.get(OrganizationTeamPublication, team["id"])
            actions = list(
                await session.scalars(
                    select(OrganizationTeamPublicationAudit.action)
                    .where(OrganizationTeamPublicationAudit.team_id == team["id"])
                    .order_by(OrganizationTeamPublicationAudit.id)
                )
            )
            assert persisted_team is not None
            return persisted_team, publication, actions

    persisted_team, publication, actions = asyncio.run(final_state())
    assert persisted_team.status == "archived"
    assert publication is None or publication.publication_state == "unpublished"
    assert actions in ([], ["published", "archived"])
    assert school_client.get(
        f"/api/public/organizations/{public_identifier_candidate(organization['id'])}"
        f"/teams/{team_public_identifier_candidate(team['id'])}"
    ).status_code == 404


async def test_public_team_aggregate_counts_only_published_final_games(school_client: TestClient) -> None:
    owner = register_user(school_client, "team-aggregate-owner@example.com")
    organization = create_school(school_client, owner, "Aggregate School")
    team = school_client.post(
        f"/api/organizations/{organization['id']}/teams", json={"name": "Aggregate XI"}, headers=owner.headers
    ).json()
    assert school_client.put(f"/api/organizations/{organization['id']}/public-settings/publish", headers=owner.headers).status_code == 200
    assert school_client.put(f"/api/organizations/{organization['id']}/teams/{team['id']}/public-publication/publish", headers=owner.headers).status_code == 200
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    other_organization = create_school(school_client, owner, "Foreign Aggregate School")
    async with session_maker() as session:
        tournament = Tournament(name="Aggregate Competition", organization_id=organization["id"])
        unpublished_tournament = Tournament(name="Private Competition", organization_id=organization["id"])
        foreign_tournament = Tournament(name="Foreign Competition", organization_id=other_organization["id"])
        published_game = Game(status=GameStatus.completed, publication_state="published_final")
        private_game = Game(status=GameStatus.completed, publication_state="private")
        unpublished_competition_game = Game(status=GameStatus.completed, publication_state="published_final")
        foreign_competition_game = Game(status=GameStatus.completed, publication_state="published_final")
        session.add_all([tournament, unpublished_tournament, foreign_tournament, published_game, private_game, unpublished_competition_game, foreign_competition_game])
        await session.flush()
        session.add_all([
            Fixture(tournament_id=tournament.id, team_a_name="Aggregate XI", team_b_name="Opposition", team_a_id=team["id"], game_id=published_game.id, status="completed"),
            Fixture(tournament_id=tournament.id, team_a_name="Aggregate XI", team_b_name="Private Opposition", team_a_id=team["id"], game_id=private_game.id, status="completed"),
            Fixture(tournament_id=unpublished_tournament.id, team_a_name="Aggregate XI", team_b_name="Unpublished", team_a_id=team["id"], game_id=unpublished_competition_game.id, status="completed"),
            Fixture(tournament_id=foreign_tournament.id, team_a_name="Aggregate XI", team_b_name="Foreign", team_a_id=team["id"], game_id=foreign_competition_game.id, status="completed"),
        ])
        await session.commit()
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{tournament.id}/community-publication/publish",
        headers=owner.headers,
    ).status_code == 200
    public = school_client.get(
        f"/api/public/organizations/{public_identifier_candidate(organization['id'])}/teams/{team_public_identifier_candidate(team['id'])}"
    )
    assert public.status_code == 200
    assert public.json()["aggregate_stats"] == {"published_games": 1}
    async with session_maker() as session:
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        assert entitlement is not None
        entitlement.status = "disabled"
        await session.commit()
    disabled = school_client.get(
        f"/api/public/organizations/{public_identifier_candidate(organization['id'])}/teams/{team_public_identifier_candidate(team['id'])}"
    )
    assert disabled.status_code == 200
    assert disabled.json()["aggregate_stats"] == {"published_games": 0}


async def test_opaque_entity_share_routes_fail_closed_after_parent_revocation(
    school_client: TestClient,
) -> None:
    """Public entity links never accept/return tenant, fixture, or game identifiers."""
    owner = register_user(school_client, "opaque-share-owner@example.com")
    organization = create_school(school_client, owner, "Opaque Share School")
    other = create_school(school_client, owner, "Other Opaque Share School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        competition = Tournament(name="Opaque Cup", organization_id=organization["id"])
        game = Game(
            status=GameStatus.completed,
            publication_state="published_final",
            result="Home won by 1 run",
            team_a={"name": "Home", "players": [], "school_source": {"organization_id": organization["id"]}},
            team_b={"name": "Away", "players": [], "school_source": {"organization_id": organization["id"]}},
        )
        session.add_all([competition, game])
        await session.flush()
        fixture = Fixture(
            tournament_id=competition.id,
            team_a_name="Home",
            team_b_name="Away",
            game_id=game.id,
            status="completed",
            result="Private result must not be used",
        )
        session.add(fixture)
        await session.commit()
        await session.refresh(fixture)
        await session.refresh(game)

    published_org = school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish", headers=owner.headers
    ).json()
    public_org = published_org["public_identifier"]
    published_competition = school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition.id}/community-publication/publish",
        headers=owner.headers,
    )
    assert published_competition.status_code == 200
    community = school_client.get(f"/api/public/organizations/{public_org}/community")
    assert community.status_code == 200
    public_competition = community.json()["competitions"][0]
    fixture_projection = public_competition["fixtures"][0]
    assert public_competition["public_key"].startswith("cmp_")
    assert fixture_projection["public_identifier"].startswith("fix_")
    assert fixture_projection["canonical_scorecard_path"].endswith(game.public_scorecard_identifier)

    base = f"/api/public/organizations/{public_org}/competitions/{public_competition['public_key']}"
    for suffix in ("", f"/fixtures/{fixture_projection['public_identifier']}", f"/results/{fixture_projection['public_identifier']}"):
        response = school_client.get(f"{base}{suffix}")
        assert response.status_code == 200, response.text
        serialized = response.text
        for private_identifier in (organization["id"], competition.id, fixture.id, game.id):
            assert private_identifier not in serialized
    scorecard = school_client.get(f"{base}/scorecards/{game.public_scorecard_identifier}")
    assert scorecard.status_code == 200, scorecard.text
    assert scorecard.json()["public_identifier"] == game.public_scorecard_identifier
    assert game.id not in scorecard.text
    # Preserve the earlier endpoint's deliberately separate contract while the
    # nested canonical endpoint remains opaque-only.
    legacy_scorecard = school_client.get(f"/public/school-scorecards/{game.id}")
    assert legacy_scorecard.status_code == 200
    assert legacy_scorecard.json()["game_id"] == game.id
    assert "public_identifier" not in legacy_scorecard.json()

    # Opaque keys cannot be replayed under another tenant and are immediately
    # invalid when either publication gate is withdrawn.
    other_public = school_client.put(
        f"/api/organizations/{other['id']}/public-settings/publish", headers=owner.headers
    ).json()["public_identifier"]
    assert school_client.get(
        f"/api/public/organizations/{other_public}/competitions/{public_competition['public_key']}"
    ).status_code == 404
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition.id}/community-publication/unpublish",
        headers=owner.headers,
    ).status_code == 200
    assert school_client.get(base).status_code == 404
    assert school_client.get(f"{base}/scorecards/{game.public_scorecard_identifier}").status_code == 404
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition.id}/community-publication/publish",
        headers=owner.headers,
    ).status_code == 200
    async with session_maker() as session:
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        assert entitlement is not None
        entitlement.status = "disabled"
        await session.commit()
    assert school_client.get(f"{base}/scorecards/{game.public_scorecard_identifier}").status_code == 404
    async with session_maker() as session:
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        assert entitlement is not None
        entitlement.status = "active"
        await session.commit()
    assert school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/unpublish", headers=owner.headers
    ).status_code == 200
    assert school_client.get(f"{base}/fixtures/{fixture_projection['public_identifier']}").status_code == 404
async def test_direct_opaque_entity_links_bypass_community_collection_caps(school_client: TestClient) -> None:
    owner = register_user(school_client, "opaque-boundary-owner@example.com")
    organization = create_school(school_client, owner, "Opaque Boundary School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        competitions = [Tournament(name=f"Boundary Competition {number:02d}", organization_id=organization["id"]) for number in range(1, 10)]
        session.add_all(competitions)
        await session.flush()
        ninth = competitions[-1]
        fixtures = [Fixture(tournament_id=ninth.id, team_a_name=f"Home {number}", team_b_name=f"Away {number}", match_number=number, status="scheduled") for number in range(1, 14)]
        session.add_all(fixtures)
        await session.commit()
        await session.refresh(fixtures[-1])
    published = school_client.put(f"/api/organizations/{organization['id']}/public-settings/publish", headers=owner.headers)
    assert published.status_code == 200
    public_identifier = published.json()["public_identifier"]
    for competition in competitions:
        response = school_client.put(f"/api/organizations/{organization['id']}/competitions/{competition.id}/community-publication/publish", headers=owner.headers)
        assert response.status_code == 200, response.text
    ninth_key = public_competition_key_candidate(ninth.id)
    base = f"/api/public/organizations/{public_identifier}/competitions/{ninth_key}"
    community = school_client.get(f"/api/public/organizations/{public_identifier}/community")
    assert community.status_code == 200
    assert len(community.json()["competitions"]) == 8
    assert all(item["public_key"] != ninth_key for item in community.json()["competitions"])
    assert school_client.get(base).status_code == 200
    fixture_url = f"{base}/fixtures/{fixtures[-1].public_identifier}"
    assert school_client.get(fixture_url).status_code == 200
    assert school_client.put(f"/api/organizations/{organization['id']}/competitions/{ninth.id}/community-publication/unpublish", headers=owner.headers).status_code == 200
    assert school_client.get(base).status_code == 404
    assert school_client.get(fixture_url).status_code == 404
