from __future__ import annotations

import datetime as dt
import asyncio
import os
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.sql_app import models
from backend.sql_app.models import OrganizationSponsorPlacement, OrganizationSponsorPlacementAudit, SponsorVisibilityAudit, User
from backend.routes import organization_sponsor_placements
from backend.tests.school_test_helpers import create_club, create_school, register_user


async def _make_platform_admin(client: TestClient, user_id: str) -> None:
    async with client.session_maker() as session:  # type: ignore[attr-defined]
        user = await session.get(User, user_id)
        assert user is not None
        user.is_superuser = True
        await session.commit()


def test_sponsor_retention_foreign_keys_match_migration() -> None:
    """Prevent ORM/migration drift that could erase governed placement history."""
    placement_fk = next(iter(OrganizationSponsorPlacement.__table__.c.organization_id.foreign_keys))
    audit_org_fk = next(iter(OrganizationSponsorPlacementAudit.__table__.c.organization_id.foreign_keys))
    audit_placement_fk = next(iter(OrganizationSponsorPlacementAudit.__table__.c.placement_id.foreign_keys))
    assert placement_fk.ondelete == "RESTRICT"
    assert audit_org_fk.ondelete == "RESTRICT"
    assert audit_placement_fk.ondelete == "RESTRICT"

    migration = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260930020000_add_org_sponsor_approval.py"
    ).read_text(encoding="utf-8")
    assert migration.count('ForeignKey("organizations.id", ondelete="RESTRICT")') == 2
    assert 'ForeignKey("organization_sponsor_placements.id", ondelete="RESTRICT")' in migration


@pytest.mark.parametrize("kind", ["school", "club"])
def test_school_and_club_proposal_independent_approval_and_immediate_takedown(
    school_client: TestClient, kind: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_PLACEMENTS_ENABLED", True)
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_ALLOWED_CATEGORIES", "sports-equipment")
    owner = register_user(school_client, f"{kind}-sponsor-owner@example.com")
    reviewer = register_user(school_client, f"{kind}-sponsor-reviewer@example.com")
    create = create_school if kind == "school" else create_club
    organization = create(school_client, owner, f"{kind} sponsor organization")
    settings = school_client.get(f"/api/organizations/{organization['id']}/public-settings", headers=owner.headers).json()

    proposed = school_client.post(
        f"/api/organizations/{organization['id']}/sponsor-placements",
        json={"sponsor_name": "Local Cricket Shop", "category": "sports-equipment", "sponsor_url": "https://example.org"},
        headers=owner.headers,
    )
    assert proposed.status_code == 201, proposed.text
    placement_id = proposed.json()["id"]
    assert school_client.get(f"/api/public/organizations/{settings['public_identifier']}/sponsor-placement").status_code == 404

    # An organization owner is not a platform reviewer.
    assert school_client.post(f"/api/platform/sponsor-placements/{placement_id}/approve", headers=owner.headers).status_code == 403
    import asyncio
    asyncio.run(_make_platform_admin(school_client, reviewer.id))
    review_queue = school_client.get("/api/platform/sponsor-placements", headers=reviewer.headers)
    assert review_queue.status_code == 200
    assert review_queue.json()["items"] == [{
        "id": placement_id, "organization_id": organization["id"], "organization_label": f"{kind} sponsor organization",
        "sponsor_name": "Local Cricket Shop", "category": "sports-equipment", "state": "proposed",
    }]
    assert review_queue.json()["page"] == {"page": 1, "page_size": 50, "total": 1, "pages": 1}
    approved = school_client.post(f"/api/platform/sponsor-placements/{placement_id}/approve", headers=reviewer.headers)
    assert approved.status_code == 200, approved.text

    # Approval and public organization publication are not enough: all three
    # persisted visibility gates must be deliberately enabled by Cricksy.
    assert school_client.get(f"/api/public/organizations/{settings['public_identifier']}/sponsor-placement").status_code == 404
    assert school_client.patch("/api/platform/sponsor-visibility/global", json={"enabled": True}, headers=owner.headers).status_code == 403
    assert school_client.patch("/api/platform/sponsor-visibility/global", json={"enabled": True}, headers=reviewer.headers).status_code == 200
    assert school_client.patch(f"/api/platform/sponsor-visibility/organizations/{organization['id']}", json={"enabled": True}, headers=reviewer.headers).status_code == 200
    snapshot = school_client.patch(f"/api/platform/sponsor-visibility/placements/{placement_id}", json={"enabled": True}, headers=reviewer.headers)
    assert snapshot.status_code == 200 and snapshot.json()["global_enabled"] is True
    assert school_client.put(f"/api/organizations/{organization['id']}/public-settings/publish", headers=owner.headers).status_code == 200
    public = school_client.get(f"/api/public/organizations/{settings['public_identifier']}/sponsor-placement")
    assert public.status_code == 200 and public.json()["sponsor_name"] == "Local Cricket Shop"
    assert public.headers["cache-control"] == "no-store, max-age=0"

    taken_down = school_client.post(f"/api/platform/sponsor-placements/{placement_id}/takedown", headers=reviewer.headers)
    assert taken_down.status_code == 200 and taken_down.json()["state"] == "taken_down"
    assert school_client.get(f"/api/public/organizations/{settings['public_identifier']}/sponsor-placement").status_code == 404
    # Re-enabling a gate never changes a takedown decision or resurrects a sponsor.
    assert school_client.patch(f"/api/platform/sponsor-visibility/placements/{placement_id}", json={"enabled": True}, headers=reviewer.headers).status_code == 200
    assert school_client.get(f"/api/public/organizations/{settings['public_identifier']}/sponsor-placement").status_code == 404

    async def audit_actions() -> list[str]:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            from sqlalchemy import select
            return list((await session.scalars(select(OrganizationSponsorPlacementAudit.action).where(OrganizationSponsorPlacementAudit.placement_id == placement_id).order_by(OrganizationSponsorPlacementAudit.id))).all())
    assert asyncio.run(audit_actions()) == ["proposed", "approved", "taken_down"]
    async def visibility_audits() -> int:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            from sqlalchemy import select
            return len(list((await session.scalars(select(SponsorVisibilityAudit).where(SponsorVisibilityAudit.placement_id == placement_id))).all()))
    assert asyncio.run(visibility_audits()) == 2


def test_replacement_cannot_resurface_after_newer_takedown(school_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_PLACEMENTS_ENABLED", True)
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_ALLOWED_CATEGORIES", "sports-equipment")
    owner = register_user(school_client, "replacement-owner@example.com")
    reviewer = register_user(school_client, "replacement-reviewer@example.com")
    org = create_school(school_client, owner, "Replacement School")
    import asyncio
    asyncio.run(_make_platform_admin(school_client, reviewer.id))
    ids = []
    for name in ("First", "Second"):
        proposed = school_client.post(f"/api/organizations/{org['id']}/sponsor-placements", json={"sponsor_name": name, "category": "sports-equipment"}, headers=owner.headers)
        ids.append(proposed.json()["id"])
        assert school_client.post(f"/api/platform/sponsor-placements/{ids[-1]}/approve", headers=reviewer.headers).status_code == 200
    settings = school_client.get(f"/api/organizations/{org['id']}/public-settings", headers=owner.headers).json()
    assert school_client.patch("/api/platform/sponsor-visibility/global", json={"enabled": True}, headers=reviewer.headers).status_code == 200
    assert school_client.patch(f"/api/platform/sponsor-visibility/organizations/{org['id']}", json={"enabled": True}, headers=reviewer.headers).status_code == 200
    assert school_client.patch(f"/api/platform/sponsor-visibility/placements/{ids[1]}", json={"enabled": True}, headers=reviewer.headers).status_code == 200
    assert school_client.put(f"/api/organizations/{org['id']}/public-settings/publish", headers=owner.headers).status_code == 200
    assert school_client.get(f"/api/public/organizations/{settings['public_identifier']}/sponsor-placement").json()["sponsor_name"] == "Second"
    assert school_client.post(f"/api/platform/sponsor-placements/{ids[1]}/takedown", headers=reviewer.headers).status_code == 200
    assert school_client.get(f"/api/public/organizations/{settings['public_identifier']}/sponsor-placement").status_code == 404


def test_cross_tenant_and_self_approval_are_denied(school_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_PLACEMENTS_ENABLED", True)
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_ALLOWED_CATEGORIES", "sports-equipment")
    proposer = register_user(school_client, "sponsor-proposer@example.com")
    other = register_user(school_client, "sponsor-other@example.com")
    first = create_school(school_client, proposer, "First School")
    second = create_club(school_client, other, "Second Club")
    assert school_client.post(f"/api/organizations/{second['id']}/sponsor-placements", json={"sponsor_name": "Nope", "category": "sports-equipment"}, headers=proposer.headers).status_code == 404
    proposal = school_client.post(f"/api/organizations/{first['id']}/sponsor-placements", json={"sponsor_name": "Approved only by Cricksy", "category": "sports-equipment"}, headers=proposer.headers)
    placement_id = proposal.json()["id"]
    import asyncio
    asyncio.run(_make_platform_admin(school_client, proposer.id))
    assert school_client.post(f"/api/platform/sponsor-placements/{placement_id}/approve", headers=proposer.headers).status_code == 403


def test_policy_gate_is_closed_by_default(school_client: TestClient) -> None:
    owner = register_user(school_client, "sponsor-policy-owner@example.com")
    organization = create_school(school_client, owner, "Policy-gated School")
    response = school_client.post(
        f"/api/organizations/{organization['id']}/sponsor-placements",
        json={"sponsor_name": "Not yet allowed", "category": "unreviewed"},
        headers=owner.headers,
    )
    assert response.status_code == 503


def test_category_gate_remains_closed_when_feature_is_enabled(school_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_PLACEMENTS_ENABLED", True)
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_ALLOWED_CATEGORIES", "")
    owner = register_user(school_client, "category-owner@example.com")
    organization = create_club(school_client, owner, "No categories Club")
    assert school_client.post(f"/api/organizations/{organization['id']}/sponsor-placements", json={"sponsor_name": "Not allowed", "category": "anything"}, headers=owner.headers).status_code == 503


def test_platform_visibility_and_review_lists_are_bounded_and_page_preserving(school_client: TestClient) -> None:
    owner = register_user(school_client, "sponsor-pagination-owner@example.com")
    import asyncio

    async def seed() -> None:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            now = dt.datetime.now(dt.UTC)
            for index in range(51):
                organization_id = f"pagination-org-{index:03d}"
                session.add(models.Organization(id=organization_id, name=f"Pagination {index:03d}", organization_type="school", status="active"))
                session.add(OrganizationSponsorPlacement(id=f"pagination-placement-{index:03d}", organization_id=organization_id, sponsor_name=f"Sponsor {index:03d}", category="sports-equipment", state="proposed", proposed_by_user_id=owner.id, created_at=now + dt.timedelta(seconds=index)))
            session.add(models.OrganizationSponsorPlacement(id="pagination-taken-down", organization_id="pagination-org-000", sponsor_name="Taken down", category="sports-equipment", state="taken_down", proposed_by_user_id=owner.id, created_at=now + dt.timedelta(seconds=99)))
            await session.commit()

    asyncio.run(seed())
    asyncio.run(_make_platform_admin(school_client, owner.id))
    queue = school_client.get("/api/platform/sponsor-placements?page=2&page_size=50", headers=owner.headers)
    assert queue.status_code == 200
    assert queue.json()["page"] == {"page": 2, "page_size": 50, "total": 51, "pages": 2}
    assert [item["id"] for item in queue.json()["items"]] == ["pagination-placement-050"]
    taken_down = school_client.get("/api/platform/sponsor-placements?states=taken_down", headers=owner.headers)
    assert taken_down.json()["page"]["total"] == 1 and taken_down.json()["items"][0]["id"] == "pagination-taken-down"
    snapshot = school_client.get("/api/platform/sponsor-visibility?organization_page=2&placement_page=2&page_size=50", headers=owner.headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["page"]["organizations"] == {"page": 2, "page_size": 50, "total": 51, "pages": 2}
    assert snapshot.json()["page"]["placements"] == {"page": 2, "page_size": 50, "total": 51, "pages": 2}
    preserved = school_client.patch("/api/platform/sponsor-visibility/placements/pagination-placement-000?organization_page=2&placement_page=2&page_size=50", json={"enabled": True}, headers=owner.headers)
    assert preserved.status_code == 200
    assert preserved.json()["page"]["placements"]["page"] == 2
    assert preserved.json()["placements"][0]["id"] == "pagination-placement-000"


@pytest.mark.parametrize(
    "category",
    ("sports-equipment", "education", "ordinary-food-businesses", "local-services"),
)
def test_owner_approved_categories_are_the_only_defaults(
    school_client: TestClient, monkeypatch: pytest.MonkeyPatch, category: str
) -> None:
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_PLACEMENTS_ENABLED", True)
    owner = register_user(school_client, f"{category}-owner@example.com")
    organization = create_school(school_client, owner, f"{category} School")
    allowed = school_client.post(
        f"/api/organizations/{organization['id']}/sponsor-placements",
        json={"sponsor_name": "Approved category", "category": category},
        headers=owner.headers,
    )
    assert allowed.status_code == 201, allowed.text
    denied = school_client.post(
        f"/api/organizations/{organization['id']}/sponsor-placements",
        json={"sponsor_name": "Unapproved category", "category": "regulated-financial-services"},
        headers=owner.headers,
    )
    assert denied.status_code == 503


def test_aggregate_reporting_is_tenant_scoped_deduplicated_and_stops_on_takedown(
    school_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_PLACEMENTS_ENABLED", True)
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_AGGREGATE_REPORTING_ENABLED", True)
    owner = register_user(school_client, "reporting-owner@example.com")
    outsider = register_user(school_client, "reporting-outsider@example.com")
    reviewer = register_user(school_client, "reporting-reviewer@example.com")
    organization = create_school(school_client, owner, "Reporting School")
    proposal = school_client.post(
        f"/api/organizations/{organization['id']}/sponsor-placements",
        json={"sponsor_name": "Local Cricket Shop", "category": "sports-equipment"}, headers=owner.headers,
    )
    placement_id = proposal.json()["id"]
    import asyncio
    asyncio.run(_make_platform_admin(school_client, reviewer.id))
    assert school_client.post(f"/api/platform/sponsor-placements/{placement_id}/approve", headers=reviewer.headers).status_code == 200
    assert school_client.patch("/api/platform/sponsor-visibility/global", json={"enabled": True}, headers=reviewer.headers).status_code == 200
    assert school_client.patch(f"/api/platform/sponsor-visibility/organizations/{organization['id']}", json={"enabled": True}, headers=reviewer.headers).status_code == 200
    assert school_client.patch(f"/api/platform/sponsor-visibility/placements/{placement_id}", json={"enabled": True}, headers=reviewer.headers).status_code == 200
    assert school_client.put(f"/api/organizations/{organization['id']}/public-settings/publish", headers=owner.headers).status_code == 200
    public_identifier = school_client.get(f"/api/organizations/{organization['id']}/public-settings", headers=owner.headers).json()["public_identifier"]
    reporting = school_client.get(f"/api/public/organizations/{public_identifier}/sponsor-placement").json()["reporting"]
    event = {"capability": reporting["display_capability"], "event_id": "123e4567-e89b-42d3-a456-426614174000"}
    assert school_client.post("/api/public/sponsor-placement-events", json=event).json() == {"accepted": True, "duplicate": False}
    assert school_client.post("/api/public/sponsor-placement-events", json=event).json() == {"accepted": True, "duplicate": True}
    assert school_client.post("/api/public/sponsor-placement-events", json={**event, "event_id": "123e4567-e89b-42d3-a456-426614174009"}).status_code == 404
    assert school_client.post("/api/public/sponsor-placement-events", json={"capability": reporting["click_capability"], "event_id": "123e4567-e89b-42d3-a456-426614174001"}).status_code == 202
    report = school_client.get(f"/api/organizations/{organization['id']}/sponsor-reporting", headers=owner.headers)
    assert report.status_code == 200 and report.json()["buckets"][0]["displays"] == 1 and report.json()["buckets"][0]["clicks"] == 1
    assert school_client.get(f"/api/organizations/{organization['id']}/sponsor-reporting", headers=outsider.headers).status_code == 404
    assert school_client.post(f"/api/platform/sponsor-placements/{placement_id}/takedown", headers=reviewer.headers).status_code == 200
    assert school_client.post("/api/public/sponsor-placement-events", json={**event, "event_id": "123e4567-e89b-42d3-a456-426614174002"}).status_code == 404
    retained = school_client.get(f"/api/organizations/{organization['id']}/sponsor-reporting", headers=owner.headers).json()["buckets"]
    assert retained[0]["displays"] == 1 and retained[0]["clicks"] == 1


def _live_reporting_placement(
    school_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> tuple[str, object]:
    """Create the minimum live public placement used by direct DB concurrency tests."""
    monkeypatch.setattr(organization_sponsor_placements.settings, "SPONSOR_PLACEMENTS_ENABLED", True)
    monkeypatch.setattr(
        organization_sponsor_placements.settings,
        "SPONSOR_AGGREGATE_REPORTING_ENABLED",
        True,
    )
    owner = register_user(school_client, "concurrent-reporting-owner@example.com")
    reviewer = register_user(school_client, "concurrent-reporting-reviewer@example.com")
    organization = create_school(school_client, owner, "Concurrent Reporting School")
    proposed = school_client.post(
        f"/api/organizations/{organization['id']}/sponsor-placements",
        json={"sponsor_name": "Concurrent Cricket Shop", "category": "sports-equipment"},
        headers=owner.headers,
    )
    assert proposed.status_code == 201, proposed.text
    placement_id = proposed.json()["id"]
    asyncio.run(_make_platform_admin(school_client, reviewer.id))
    assert school_client.post(
        f"/api/platform/sponsor-placements/{placement_id}/approve", headers=reviewer.headers
    ).status_code == 200
    assert school_client.patch(
        "/api/platform/sponsor-visibility/global", json={"enabled": True}, headers=reviewer.headers
    ).status_code == 200
    assert school_client.patch(
        f"/api/platform/sponsor-visibility/organizations/{organization['id']}",
        json={"enabled": True},
        headers=reviewer.headers,
    ).status_code == 200
    assert school_client.patch(
        f"/api/platform/sponsor-visibility/placements/{placement_id}",
        json={"enabled": True},
        headers=reviewer.headers,
    ).status_code == 200
    assert school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish", headers=owner.headers
    ).status_code == 200
    return placement_id, school_client.session_maker  # type: ignore[attr-defined]


async def _issue_reporting_nonces(session_maker: object, placement_id: str, count: int) -> list[str]:
    async with session_maker() as session:  # type: ignore[operator]
        nonces = [
            await organization_sponsor_placements._issue_reporting_capability(
                session, placement_id, "display"
            )
            for _ in range(count)
        ]
        await session.commit()
        return nonces


async def _record_reporting_nonce(session_maker: object, nonce: str, event_id: str) -> tuple[int, object]:
    async with session_maker() as session:  # type: ignore[operator]
        try:
            payload = organization_sponsor_placements.SponsorReportEventIn(
                capability=nonce, event_id=event_id
            )
            return 202, await organization_sponsor_placements.record_public_placement_event(payload, session)
        except HTTPException as exc:
            await session.rollback()
            return exc.status_code, exc.detail


def _require_migrated_postgres(school_client: TestClient) -> None:
    if os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1":
        pytest.skip("requires the isolated migrated PostgreSQL acceptance database")
    async def assert_postgres() -> None:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            assert session.bind is not None and session.bind.dialect.name == "postgresql"
    asyncio.run(assert_postgres())


def test_real_postgres_reporting_first_write_and_capability_consumption_are_atomic(
    school_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _require_migrated_postgres(school_client)
    placement_id, session_maker = _live_reporting_placement(school_client, monkeypatch)

    async def exercise() -> None:
        first, second = await _issue_reporting_nonces(session_maker, placement_id, 2)
        first_results = await asyncio.gather(
            _record_reporting_nonce(session_maker, first, str(uuid.uuid4())),
            _record_reporting_nonce(session_maker, second, str(uuid.uuid4())),
        )
        assert [status for status, _ in first_results] == [202, 202]
        async with session_maker() as session:  # type: ignore[operator]
            metric = await session.scalar(
                select(models.SponsorPlacementDailyMetric).where(
                    models.SponsorPlacementDailyMetric.placement_id == placement_id
                )
            )
            assert metric is not None and metric.display_count == 2 and metric.click_count == 0

        one_time = (await _issue_reporting_nonces(session_maker, placement_id, 1))[0]
        consumed = await asyncio.gather(
            _record_reporting_nonce(session_maker, one_time, str(uuid.uuid4())),
            _record_reporting_nonce(session_maker, one_time, str(uuid.uuid4())),
        )
        assert sorted(status for status, _ in consumed) == [202, 404]

    asyncio.run(exercise())


def test_real_postgres_reporting_rate_limit_replay_and_retention_boundary(
    school_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    _require_migrated_postgres(school_client)
    placement_id, session_maker = _live_reporting_placement(school_client, monkeypatch)

    async def exercise() -> None:
        nonces = await _issue_reporting_nonces(session_maker, placement_id, 61)
        event_ids = [str(uuid.uuid4()) for _ in nonces]
        results = await asyncio.gather(
            *(
                _record_reporting_nonce(session_maker, nonce, event_id)
                for nonce, event_id in zip(nonces, event_ids, strict=True)
            )
        )
        assert sum(status == 202 for status, _ in results) == 60
        assert sum(status == 429 for status, _ in results) == 1

        # A duplicate must remain idempotent after the shared bucket is full and
        # must not burn a newly-issued one-time capability.
        replay_nonce = (await _issue_reporting_nonces(session_maker, placement_id, 1))[0]
        replay_status, replay_body = await _record_reporting_nonce(session_maker, replay_nonce, event_ids[0])
        assert (replay_status, replay_body) == (202, {"accepted": True, "duplicate": True})

        now = dt.datetime.now(dt.UTC)
        stale_nonce = str(uuid.uuid4())
        retained_nonce = str(uuid.uuid4())
        async with session_maker() as session:  # type: ignore[operator]
            session.add_all(
                [
                    models.SponsorPlacementReportDedup(
                        event_id=stale_nonce,
                        placement_id=placement_id,
                        received_date=(now - dt.timedelta(hours=48, seconds=1)).date(),
                        received_at=now - dt.timedelta(hours=48, seconds=1),
                    ),
                    models.SponsorPlacementReportDedup(
                        event_id=retained_nonce,
                        placement_id=placement_id,
                        received_date=(now - dt.timedelta(hours=47, minutes=59)).date(),
                        received_at=now - dt.timedelta(hours=47, minutes=59),
                    ),
                    models.SponsorPlacementReportRateBucket(
                        placement_id=placement_id,
                        bucket_start=now - dt.timedelta(hours=48, seconds=1),
                        event_count=1,
                    ),
                ]
            )
            await session.commit()

        # This new event is intentionally rate-limited; the route's pre-rate
        # cleanup must still remove data older than 48 hours while retaining newer data.
        cleanup_nonce = (await _issue_reporting_nonces(session_maker, placement_id, 1))[0]
        assert (await _record_reporting_nonce(session_maker, cleanup_nonce, str(uuid.uuid4())))[0] == 429
        async with session_maker() as session:  # type: ignore[operator]
            retained = await session.get(models.SponsorPlacementReportDedup, retained_nonce)
            stale = await session.get(models.SponsorPlacementReportDedup, stale_nonce)
            old_bucket = await session.get(
                models.SponsorPlacementReportRateBucket,
                {"placement_id": placement_id, "bucket_start": now - dt.timedelta(hours=48, seconds=1)},
            )
            assert retained is not None and stale is None and old_bucket is None

    asyncio.run(exercise())
