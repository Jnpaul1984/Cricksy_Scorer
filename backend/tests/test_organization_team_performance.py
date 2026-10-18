from __future__ import annotations

import asyncio
import datetime as dt

import pytest
from sqlalchemy import select

from backend.services.organization_team_performance_access import (
    TeamPerformanceAccessError,
    grant_organization_team_performance,
    require_team_performance_access,
    revoke_organization_team_performance,
)
from backend.sql_app.models import (
    Game,
    Organization,
    OrganizationMembership,
    OrganizationTeamPerformanceGrant,
    RoleEnum,
    User,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_club,
    create_school,
    register_user,
)
from backend.tests.test_school_team_analytics import _hand_calculated_deliveries, _seed_team_game


async def _grant_async(client, organization_id: str, operator: RegisteredUser, **kwargs):
    async with client.session_maker() as session:  # type: ignore[attr-defined]
        grant, created = await grant_organization_team_performance(
            session,
            organization_id=organization_id,
            operator_user_id=operator.id,
            reason="Owner-approved bounded staff pilot",
            **kwargs,
        )
        await session.commit()
        await session.refresh(grant)
        return grant, created


def _grant(client, organization_id: str, operator: RegisteredUser, **kwargs):
    return asyncio.run(_grant_async(client, organization_id, operator, **kwargs))


@pytest.mark.parametrize("organization_type", ["school", "club"])
def test_team_performance_is_default_off_and_returns_only_safe_aggregates(
    school_client, organization_type: str
) -> None:
    owner = register_user(school_client, f"pilot-{organization_type}@example.com")
    create_organization = create_school if organization_type == "school" else create_club
    organization = create_organization(school_client, owner, f"Pilot {organization_type}")
    organization_id = organization["id"]
    team, game, target, opponent = asyncio.run(
        _seed_team_game(
            school_client,
            organization_id,
            owner.id,
            deliveries=None,
        )
    )
    path = f"/api/organizations/{organization_id}/team-performance/teams/{team.id}?overs_limit=20"

    denied = school_client.get(path, headers=owner.headers)
    assert denied.status_code == 403

    _grant(
        school_client,
        organization_id,
        owner,
    )
    response = school_client.get(path, headers=owner.headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["organization_id"] == organization_id
    assert payload["team_id"] == team.id
    assert payload["coverage"]["status"] == "no_usable_ledger"
    assert payload["coverage"]["eligible_games"] == 1
    assert payload["coverage"]["no_ledger_games"] == 1
    assert "source_game_ids" not in payload
    assert "innings_attribution" not in payload
    assert "exclusions" not in payload
    assert game.id not in response.text
    assert all(player.player_name not in response.text for player in [*target, *opponent])


@pytest.mark.asyncio
async def test_team_performance_returns_weighted_safe_ledger_metrics(school_client) -> None:
    owner = register_user(school_client, "pilot-ledger@example.com")
    organization = create_school(school_client, owner, "Recorded pilot")
    team, game, target, opponent = await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=None,
    )

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        stored_game = await session.get(Game, game.id)
        assert stored_game is not None
        stored_game.deliveries = _hand_calculated_deliveries(target, opponent)
        await session.commit()

    await _grant_async(school_client, organization["id"], owner)
    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20",
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["batting"]["team_runs"] == 19
    assert payload["batting"]["legal_balls"] == 6
    assert payload["batting"]["run_rate"] == 19.0
    assert payload["bowling"]["opposition_team_runs"] == 13
    assert payload["bowling"]["bowler_charged_runs"] == 9
    assert payload["bowling"]["team_concession_rate"] == 13.0
    assert payload["bowling"]["bowling_economy"] == 9.0
    assert payload["coverage"]["usable_batting_innings"] == 1
    assert payload["coverage"]["usable_bowling_innings"] == 1


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [
        ("owner", 200),
        ("admin", 200),
        ("coach", 200),
        ("scorer", 403),
        ("viewer", 403),
    ],
)
def test_team_performance_contextual_role_matrix(
    school_client, role: str, expected_status: int
) -> None:
    owner = register_user(school_client, f"role-owner-{role}@example.com")
    staff = owner if role == "owner" else register_user(school_client, f"role-{role}@example.com")
    organization = create_school(school_client, owner, "Role matrix pilot")
    if role != "owner":
        add_membership(school_client, owner, organization["id"], staff.id, role)
    team, _, _, _ = asyncio.run(
        _seed_team_game(
            school_client,
            organization["id"],
            owner.id,
            deliveries=None,
        )
    )
    _grant(school_client, organization["id"], owner)

    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20",
        headers=staff.headers,
    )
    assert response.status_code == expected_status, response.text


def test_team_performance_hides_foreign_team_and_denies_user_org_id_bypass(school_client) -> None:
    owner_a = register_user(school_client, "tenant-a-owner@example.com")
    owner_b = register_user(school_client, "tenant-b-owner@example.com")
    outsider = register_user(school_client, "tenant-outsider@example.com")
    org_a = create_school(school_client, owner_a, "Tenant A")
    org_b = create_school(school_client, owner_b, "Tenant B")
    team_a, _, _, _ = asyncio.run(
        _seed_team_game(school_client, org_a["id"], owner_a.id, deliveries=None)
    )
    team_b, _, _, _ = asyncio.run(
        _seed_team_game(school_client, org_b["id"], owner_b.id, deliveries=None)
    )
    _grant(school_client, org_a["id"], owner_a)

    foreign_team_response = school_client.get(
        f"/api/organizations/{org_a['id']}/team-performance/teams/{team_b.id}?overs_limit=20",
        headers=owner_a.headers,
    )
    assert foreign_team_response.status_code == 404
    assert foreign_team_response.json()["detail"] == "Team not found"
    assert team_b.id not in foreign_team_response.text

    async def make_legacy_bypass_look_authorized() -> None:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            user = await session.get(User, outsider.id)
            assert user is not None
            user.org_id = org_a["id"]
            user.is_superuser = True
            user.role = RoleEnum.coach_pro_plus
            user.subscription_plan = RoleEnum.coach_pro_plus
            await session.commit()

    asyncio.run(make_legacy_bypass_look_authorized())
    outsider_response = school_client.get(
        f"/api/organizations/{org_a['id']}/team-performance/teams/{team_a.id}?overs_limit=20",
        headers=outsider.headers,
    )
    assert outsider_response.status_code == 404
    assert outsider_response.json()["detail"] == "Organization not found"


def test_team_performance_denies_removed_membership_inactive_org_and_grant_expiry(
    school_client,
) -> None:
    owner = register_user(school_client, "revocation-owner@example.com")
    staff = register_user(school_client, "revocation-coach@example.com")
    organization = create_school(school_client, owner, "Revocation pilot")
    add_membership(school_client, owner, organization["id"], staff.id, "coach")
    team, _, _, _ = asyncio.run(
        _seed_team_game(school_client, organization["id"], owner.id, deliveries=None)
    )
    grant, _ = _grant(school_client, organization["id"], owner)
    endpoint = (
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20"
    )

    async def disable_membership() -> None:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            membership = await session.scalar(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == organization["id"],
                    OrganizationMembership.user_id == staff.id,
                )
            )
            assert membership is not None
            membership.status = "disabled"
            await session.commit()

    asyncio.run(disable_membership())
    assert school_client.get(endpoint, headers=staff.headers).status_code == 404

    async def update_grant(*, effective_from, effective_until, organization_status=None) -> None:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            grant_row = await session.get(OrganizationTeamPerformanceGrant, grant.id)
            org_row = await session.get(Organization, organization["id"])
            assert grant_row is not None and org_row is not None
            grant_row.effective_from = effective_from
            grant_row.effective_until = effective_until
            if organization_status is not None:
                org_row.status = organization_status
            await session.commit()

    asyncio.run(
        update_grant(
            effective_from=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
            effective_until=None,
        )
    )
    assert school_client.get(endpoint, headers=owner.headers).status_code == 403
    asyncio.run(
        update_grant(
            effective_from=dt.datetime.now(dt.UTC) - dt.timedelta(days=2),
            effective_until=dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
        )
    )
    assert school_client.get(endpoint, headers=owner.headers).status_code == 403
    asyncio.run(
        update_grant(
            effective_from=dt.datetime.now(dt.UTC) - dt.timedelta(days=2),
            effective_until=dt.datetime.now(dt.UTC) - dt.timedelta(days=1),
            organization_status="suspended",
        )
    )
    assert school_client.get(endpoint, headers=owner.headers).status_code == 404


def test_team_performance_keeps_invalid_warnings_separate_from_usable_innings(
    school_client,
) -> None:
    owner = register_user(school_client, "warning-owner@example.com")
    organization = create_school(school_client, owner, "Warning pilot")
    team, game, target, opponent = asyncio.run(
        _seed_team_game(school_client, organization["id"], owner.id, deliveries=None)
    )
    deliveries = _hand_calculated_deliveries(target, opponent)
    deliveries[0]["runs_scored"] = -1

    async def store_ledger() -> None:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            stored_game = await session.get(Game, game.id)
            assert stored_game is not None
            stored_game.deliveries = deliveries
            await session.commit()

    asyncio.run(store_ledger())
    _grant(school_client, organization["id"], owner)

    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20",
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["coverage"]["status"] == "usable_with_exclusions"
    assert payload["coverage"]["usable_batting_innings"] == 0
    assert payload["coverage"]["usable_bowling_innings"] == 1
    assert payload["coverage"]["cohort_exclusion_counts"] == {}
    assert payload["coverage"]["warning_counts"] == {"invalid_numeric_field": 1}
    assert game.id not in response.text
    assert all(player.player_id not in response.text for player in [*target, *opponent])


def test_team_performance_rejects_oversized_scope_without_truncating(
    school_client, monkeypatch
) -> None:
    import backend.services.school_team_analytics_service as analytics_service

    owner = register_user(school_client, "large-scope-owner@example.com")
    organization = create_school(school_client, owner, "Large scope pilot")
    team, game, _, _ = asyncio.run(
        _seed_team_game(school_client, organization["id"], owner.id, deliveries=None)
    )
    _grant(school_client, organization["id"], owner)
    monkeypatch.setattr(analytics_service, "MAX_CANDIDATE_GAMES", 0)

    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20",
        headers=owner.headers,
    )
    assert response.status_code == 413
    assert "too large" in response.json()["detail"]

    async def store_empty_ledger() -> None:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            stored_game = await session.get(Game, game.id)
            assert stored_game is not None
            stored_game.deliveries = []
            await session.commit()

    asyncio.run(store_empty_ledger())
    monkeypatch.setattr(analytics_service, "MAX_CANDIDATE_GAMES", 250)
    monkeypatch.setattr(analytics_service, "MAX_DELIVERY_PAYLOAD_BYTES", 0)
    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20",
        headers=owner.headers,
    )
    assert response.status_code == 413
    assert "too large" in response.json()["detail"]


@pytest.mark.asyncio
async def test_grant_revoke_operations_are_audited_and_idempotent(school_client) -> None:
    operator = register_user(school_client, "grant-operator@example.com")
    organization = create_school(school_client, operator, "Audit pilot")
    team, _, _, _ = await _seed_team_game(
        school_client,
        organization["id"],
        operator.id,
        deliveries=None,
    )
    start = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1)
    until = dt.datetime.now(dt.UTC) + dt.timedelta(days=1)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        first, created = await grant_organization_team_performance(
            session,
            organization_id=organization["id"],
            operator_user_id=operator.id,
            reason="Approved staff pilot",
            effective_from=start,
            effective_until=until,
        )
        assert created
        await session.commit()
        grant_id = first.id

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        duplicate, created = await grant_organization_team_performance(
            session,
            organization_id=organization["id"],
            operator_user_id=operator.id,
            reason="Approved staff pilot",
            effective_from=start,
            effective_until=until,
        )
        assert not created
        assert duplicate.id == grant_id
        revoked, did_revoke = await revoke_organization_team_performance(
            session,
            organization_id=organization["id"],
            operator_user_id=operator.id,
            reason="Pilot closed",
        )
        assert did_revoke
        assert revoked.revoked_by_user_id == operator.id
        assert revoked.revocation_reason == "Pilot closed"
        await session.commit()

    denied_after_revoke = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20",
        headers=operator.headers,
    )
    assert denied_after_revoke.status_code == 403

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        duplicate_revoke, did_revoke = await revoke_organization_team_performance(
            session,
            organization_id=organization["id"],
            operator_user_id=operator.id,
            reason="Pilot closed",
        )
        assert not did_revoke
        assert duplicate_revoke.id == grant_id
        with pytest.raises(TeamPerformanceAccessError):
            await require_team_performance_access(
                session,
                organization_id=organization["id"],
                team_id="missing",
                actor_user_id=operator.id,
            )
