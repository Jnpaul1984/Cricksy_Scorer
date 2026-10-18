from __future__ import annotations

import asyncio
import datetime as dt
import json
from copy import deepcopy
from uuid import uuid4

import pytest
from sqlalchemy import String, cast, select, text

from backend.services.organization_entitlement_service import SCHOOL_FREE_CAPABILITIES
from backend.services.organization_team_performance_access import (
    TeamPerformanceAccessError,
    grant_organization_team_performance,
    require_team_performance_access,
    revoke_organization_team_performance,
)
from backend.sql_app.models import (
    Game,
    Organization,
    OrganizationEntitlement,
    OrganizationMembership,
    OrganizationTeamPerformanceGrant,
    RoleEnum,
    Team,
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
    reason = kwargs.pop("reason", "Owner-approved bounded staff pilot")
    async with client.session_maker() as session:  # type: ignore[attr-defined]
        grant, created = await grant_organization_team_performance(
            session,
            organization_id=organization_id,
            operator_user_id=operator.id,
            reason=reason,
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
    assert payload["coverage"]["warning_counts"] == {}
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
            user.role = RoleEnum.org_pro
            user.subscription_plan = RoleEnum.org_pro
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


def test_team_performance_payload_limit_counts_utf8_bytes_at_boundaries(school_client) -> None:
    import backend.services.school_team_analytics_service as analytics_service

    owner = register_user(school_client, "payload-boundary-owner@example.com")
    organization = create_school(school_client, owner, "Payload boundary pilot")
    team, game, target, opponent = asyncio.run(
        _seed_team_game(school_client, organization["id"], owner.id, deliveries=None)
    )
    _grant(school_client, organization["id"], owner)
    endpoint = (
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20"
    )

    async def store_payload_and_get_utf8_size(payload: list[dict]) -> int:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            dialect_name = session.get_bind().dialect.name
            update_statement = (
                text("UPDATE games SET deliveries = CAST(:payload AS JSONB) WHERE id = :game_id")
                if dialect_name == "postgresql"
                else text("UPDATE games SET deliveries = :payload WHERE id = :game_id")
            )
            await session.execute(
                update_statement,
                {
                    "payload": json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    "game_id": game.id,
                },
            )
            await session.commit()
            serialized_payload = await session.scalar(
                select(cast(Game.deliveries, String)).where(Game.id == game.id)
            )
            assert isinstance(serialized_payload, str)
            return len(serialized_payload.encode("utf-8"))

    async def exercise_boundaries() -> None:
        for character in ("a", "é"):
            deliveries = _hand_calculated_deliveries(target, opponent)
            deliveries[0]["padding"] = ""
            base_size = await store_payload_and_get_utf8_size(deliveries)

            for offset, expected_status in ((-1, 200), (0, 200), (1, 413)):
                remaining_bytes = analytics_service.MAX_DELIVERY_PAYLOAD_BYTES + offset - base_size
                encoded_width = len(character.encode("utf-8"))
                repeated, remainder = divmod(remaining_bytes, encoded_width)
                deliveries[0]["padding"] = character * repeated + "x" * remainder
                actual_size = await store_payload_and_get_utf8_size(deliveries)
                assert actual_size == analytics_service.MAX_DELIVERY_PAYLOAD_BYTES + offset

                response = school_client.get(endpoint, headers=owner.headers)
                assert response.status_code == expected_status, response.text
                if expected_status == 413:
                    assert "too large" in response.json()["detail"]

    asyncio.run(exercise_boundaries())


@pytest.mark.parametrize(
    ("ordinary_exclusion", "invalid_ledger", "expected_status", "expected_warnings"),
    [
        (False, False, "usable_recorded_data", {}),
        (True, False, "usable_with_exclusions", {}),
        (False, True, "no_usable_ledger", {"invalid_numeric_field": 2}),
    ],
)
def test_team_performance_api_coverage_status_distinguishes_cohort_and_ledger_exclusions(
    school_client,
    ordinary_exclusion: bool,
    invalid_ledger: bool,
    expected_status: str,
    expected_warnings: dict[str, int],
) -> None:
    owner = register_user(
        school_client,
        f"coverage-status-{ordinary_exclusion}-{invalid_ledger}@example.com",
    )
    organization = create_school(school_client, owner, "Coverage status pilot")
    team, game, target, opponent = asyncio.run(
        _seed_team_game(school_client, organization["id"], owner.id, deliveries=None)
    )
    deliveries = _hand_calculated_deliveries(target, opponent)
    if invalid_ledger:
        for delivery in deliveries:
            delivery["runs_scored"] = -1
    if ordinary_exclusion:
        asyncio.run(
            _seed_team_game(
                school_client,
                organization["id"],
                owner.id,
                deliveries=[],
                purpose="practice",
                reuse_team=team,
            )
        )

    async def store_games() -> None:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            stored_game = await session.get(Game, game.id)
            assert stored_game is not None
            stored_game.deliveries = deliveries
            await session.commit()

    asyncio.run(store_games())
    _grant(school_client, organization["id"], owner)
    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20",
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    coverage = response.json()["coverage"]
    assert coverage["status"] == expected_status
    assert coverage["warning_counts"] == expected_warnings
    assert coverage["cohort_excluded_games"] == int(ordinary_exclusion)
    assert coverage["cohort_exclusion_counts"] == (
        {"non_official_match": 1} if ordinary_exclusion else {}
    )


@pytest.mark.asyncio
async def test_workload_limit_counts_selected_games_not_unrelated_history(
    school_client, monkeypatch
) -> None:
    import backend.services.school_team_analytics_service as analytics_service

    owner = register_user(school_client, "cohort-bound-owner@example.com")
    organization = create_school(school_client, owner, "Cohort bound pilot")
    team, seed_game, _, _ = await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=[],
    )
    await _grant_async(school_client, organization["id"], owner)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        session.add_all(
            [
                Game(
                    id=str(uuid4()),
                    team_a=deepcopy(seed_game.team_a),
                    team_b=deepcopy(seed_game.team_b),
                    status=seed_game.status,
                    match_purpose="practice",
                    match_type=seed_game.match_type,
                    overs_limit=seed_game.overs_limit,
                    days_limit=None,
                    match_rules=None,
                    deliveries=[],
                )
                for _ in range(260)
            ]
        )
        await session.commit()
    monkeypatch.setattr(analytics_service, "MAX_CANDIDATE_GAMES", 1)
    endpoint = (
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20"
    )
    response = school_client.get(endpoint, headers=owner.headers)
    assert response.status_code == 200, response.text
    assert response.json()["coverage"]["eligible_games"] == 1
    assert response.json()["coverage"]["cohort_excluded_games"] == 260
    assert response.json()["coverage"]["cohort_exclusion_counts"] == {"non_official_match": 260}

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        session.add(
            Game(
                id=str(uuid4()),
                team_a=deepcopy(seed_game.team_a),
                team_b=deepcopy(seed_game.team_b),
                status=seed_game.status,
                match_purpose="official",
                match_type=seed_game.match_type,
                overs_limit=seed_game.overs_limit,
                days_limit=None,
                match_rules=None,
                deliveries=[],
            )
        )
        await session.commit()
    oversized = school_client.get(endpoint, headers=owner.headers)
    assert oversized.status_code == 413


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
            grant_id=grant_id,
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
            grant_id=grant_id,
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

    replacement, replacement_created = await _grant_async(
        school_client,
        organization["id"],
        operator,
        reason="Approved renewal",
    )
    assert replacement_created
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        retried_old_revoke, did_revoke = await revoke_organization_team_performance(
            session,
            organization_id=organization["id"],
            grant_id=grant_id,
            operator_user_id=operator.id,
            reason="Pilot closed",
        )
        assert not did_revoke
        assert retried_old_revoke.id == grant_id
        active_grant = await session.scalar(
            select(OrganizationTeamPerformanceGrant).where(
                OrganizationTeamPerformanceGrant.organization_id == organization["id"],
                OrganizationTeamPerformanceGrant.status == "active",
            )
        )
        assert active_grant is not None
        assert active_grant.id == replacement.id
        await session.commit()


@pytest.mark.asyncio
async def test_team_performance_revalidates_role_user_and_team_on_every_request(
    school_client,
) -> None:
    owner = register_user(school_client, "request-recheck-owner@example.com")
    coach = register_user(school_client, "request-recheck-coach@example.com")
    organization = create_school(school_client, owner, "Request recheck pilot")
    membership = add_membership(school_client, owner, organization["id"], coach.id, "coach")
    team, _, _, _ = await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=None,
    )
    await _grant_async(school_client, organization["id"], owner)
    endpoint = (
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20"
    )
    assert school_client.get(endpoint, headers=coach.headers).status_code == 200

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        row = await session.get(OrganizationMembership, membership["id"])
        assert row is not None
        row.role = "scorer"
        await session.commit()
    downgraded = school_client.get(endpoint, headers=coach.headers)
    assert downgraded.status_code == 403
    assert team.id not in downgraded.text

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        row = await session.get(OrganizationMembership, membership["id"])
        assert row is not None
        await session.delete(row)
        await session.commit()
    removed = school_client.get(endpoint, headers=coach.headers)
    assert removed.status_code == 404
    assert organization["id"] not in removed.text

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        user = await session.get(User, owner.id)
        assert user is not None
        user.is_active = False
        await session.commit()
    inactive = school_client.get(endpoint, headers=owner.headers)
    assert inactive.status_code == 400
    assert inactive.json()["detail"] == "Inactive user"

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        user = await session.get(User, owner.id)
        team_row = await session.get(Team, team.id)
        assert user is not None and team_row is not None
        user.is_active = True
        await session.delete(team_row)
        await session.commit()
    missing_team = school_client.get(endpoint, headers=owner.headers)
    assert missing_team.status_code == 404
    assert missing_team.json()["detail"] == "Team not found"
    assert team.id not in missing_team.text


@pytest.mark.asyncio
async def test_healthy_free_capabilities_and_personal_account_survive_pilot_lifecycle(
    school_client,
) -> None:
    owner = register_user(school_client, "pilot-healthy-free@example.com")
    organization = create_school(school_client, owner, "Healthy Free invariance")
    team, _, _, _ = await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=None,
    )
    organization_id = organization["id"]
    performance_endpoint = (
        f"/api/organizations/{organization_id}/team-performance/teams/{team.id}?overs_limit=20"
    )

    def read_free_state() -> dict[str, object]:
        entitlement = school_client.get(
            f"/api/organizations/{organization_id}/entitlements",
            headers=owner.headers,
        )
        team_statistics = school_client.get(
            f"/api/organizations/{organization_id}/statistics/teams",
            headers=owner.headers,
        )
        player_statistics = school_client.get(
            f"/api/organizations/{organization_id}/statistics/players",
            headers=owner.headers,
        )
        personal_account = school_client.get("/auth/me", headers=owner.headers)
        assert entitlement.status_code == 200, entitlement.text
        assert team_statistics.status_code == 200, team_statistics.text
        assert player_statistics.status_code == 200, player_statistics.text
        assert personal_account.status_code == 200, personal_account.text
        entitlement_body = entitlement.json()
        assert entitlement_body["status"] == "active"
        assert set(entitlement_body["capabilities"]) == SCHOOL_FREE_CAPABILITIES
        return {
            "entitlement": entitlement_body,
            "team_statistics": team_statistics.json(),
            "player_statistics": player_statistics.json(),
            "personal_account": personal_account.json(),
        }

    baseline = read_free_state()
    assert school_client.get(performance_endpoint, headers=owner.headers).status_code == 403

    grant, _ = await _grant_async(school_client, organization_id, owner)
    granted = school_client.get(performance_endpoint, headers=owner.headers)
    assert granted.status_code == 200, granted.text
    assert read_free_state() == baseline

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        _, changed = await revoke_organization_team_performance(
            session,
            organization_id=organization_id,
            grant_id=grant.id,
            operator_user_id=owner.id,
            reason="Pilot closed",
        )
        assert changed
        await session.commit()
    assert school_client.get(performance_endpoint, headers=owner.headers).status_code == 403
    assert read_free_state() == baseline

    expiring, _ = await _grant_async(
        school_client,
        organization_id,
        owner,
        reason="Short pilot renewal",
        effective_until=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
    )
    renewed = school_client.get(performance_endpoint, headers=owner.headers)
    assert renewed.status_code == 200, renewed.text
    assert read_free_state() == baseline

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        current = await session.get(OrganizationTeamPerformanceGrant, expiring.id)
        assert current is not None
        current.effective_from = dt.datetime.now(dt.UTC) - dt.timedelta(days=2)
        current.effective_until = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
        await session.commit()
    assert school_client.get(performance_endpoint, headers=owner.headers).status_code == 403
    assert read_free_state() == baseline


@pytest.mark.asyncio
async def test_free_entitlement_and_personal_account_are_unchanged_by_pilot_lifecycle(
    school_client,
) -> None:
    owner = register_user(school_client, "pilot-free-invariance@example.com")
    organization = create_school(school_client, owner, "Free invariance pilot")
    team, _, _, _ = await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=None,
    )
    endpoint = (
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}?overs_limit=20"
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        user = await session.get(User, owner.id)
        assert entitlement is not None and user is not None
        entitlement_snapshot = (entitlement.plan_key, entitlement.status, entitlement.source)
        account_snapshot = (user.role, user.subscription_plan, user.org_id)
        entitlement.status = "disabled"
        await session.commit()

    grant, _ = await _grant_async(school_client, organization["id"], owner)
    denied_without_free_capability = school_client.get(endpoint, headers=owner.headers)
    assert denied_without_free_capability.status_code == 403
    assert denied_without_free_capability.json()["detail"] == "Team Performance is unavailable"

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        assert entitlement is not None
        assert (entitlement.plan_key, entitlement.status, entitlement.source) == (
            entitlement_snapshot[0],
            "disabled",
            entitlement_snapshot[2],
        )
        await session.delete(entitlement)
        await session.commit()
    denied_without_free_entitlement = school_client.get(endpoint, headers=owner.headers)
    assert denied_without_free_entitlement.status_code == 403
    assert denied_without_free_entitlement.json()["detail"] == "Team Performance is unavailable"

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        _, changed = await revoke_organization_team_performance(
            session,
            organization_id=organization["id"],
            grant_id=grant.id,
            operator_user_id=owner.id,
            reason="Pilot closed",
        )
        assert changed
        await session.commit()
    assert school_client.get(endpoint, headers=owner.headers).status_code == 403

    expiring, _ = await _grant_async(
        school_client,
        organization["id"],
        owner,
        reason="Short pilot renewal",
        effective_until=dt.datetime.now(dt.UTC) + dt.timedelta(days=1),
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        current = await session.get(OrganizationTeamPerformanceGrant, expiring.id)
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        user = await session.get(User, owner.id)
        assert current is not None and entitlement is None and user is not None
        current.effective_from = dt.datetime.now(dt.UTC) - dt.timedelta(days=2)
        current.effective_until = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
        assert (user.role, user.subscription_plan, user.org_id) == account_snapshot
        await session.commit()
    expired_denial = school_client.get(endpoint, headers=owner.headers)
    assert expired_denial.status_code == 403
    assert expired_denial.json()["detail"] == "Team Performance is unavailable"
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        user = await session.get(User, owner.id)
        assert entitlement is None
        assert user is not None
        assert (user.role, user.subscription_plan, user.org_id) == account_snapshot


@pytest.mark.asyncio
async def test_grant_validity_and_renewal_constraints(school_client) -> None:
    operator = register_user(school_client, "grant-constraints@example.com")
    organization = create_school(school_client, operator, "Grant constraints")
    start = dt.datetime.now(dt.UTC)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        for reason, effective_from, effective_until in (
            (" ", None, None),
            ("x" * 2001, None, None),
            ("naive timestamp", start.replace(tzinfo=None), None),
            ("invalid range", start, start),
        ):
            with pytest.raises(ValueError):
                await grant_organization_team_performance(
                    session,
                    organization_id=organization["id"],
                    operator_user_id=operator.id,
                    reason=reason,
                    effective_from=effective_from,
                    effective_until=effective_until,
                )

    first, _ = await _grant_async(
        school_client,
        organization["id"],
        operator,
        effective_from=start,
        effective_until=start + dt.timedelta(days=1),
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(ValueError, match="already exists"):
            await grant_organization_team_performance(
                session,
                organization_id=organization["id"],
                operator_user_id=operator.id,
                reason="Different active grant",
            )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        expired = await session.get(OrganizationTeamPerformanceGrant, first.id)
        assert expired is not None
        expired.effective_from = dt.datetime.now(dt.UTC) - dt.timedelta(days=2)
        expired.effective_until = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
        await session.commit()
    renewed, created = await _grant_async(
        school_client,
        organization["id"],
        operator,
        reason="Renewal after expiry",
    )
    assert created and renewed.id != first.id


@pytest.mark.asyncio
async def test_concurrent_grant_and_revoke_retries_are_serialized(school_client) -> None:
    if school_client.session_maker.kw["bind"].dialect.name != "postgresql":  # type: ignore[attr-defined]
        pytest.skip("Concurrent row-lock behavior is verified by the PostgreSQL gate")
    operator = register_user(school_client, "concurrent-grant@example.com")
    organization = create_school(school_client, operator, "Concurrent grant pilot")

    async def grant_once():
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            grant, created = await grant_organization_team_performance(
                session,
                organization_id=organization["id"],
                operator_user_id=operator.id,
                reason="Concurrent approved request",
            )
            await session.commit()
            return grant.id, created

    grant_results = await asyncio.gather(grant_once(), grant_once())
    assert len({grant_id for grant_id, _ in grant_results}) == 1
    assert sorted(created for _, created in grant_results) == [False, True]
    grant_id = grant_results[0][0]

    async def revoke_once():
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            grant, changed = await revoke_organization_team_performance(
                session,
                organization_id=organization["id"],
                grant_id=grant_id,
                operator_user_id=operator.id,
                reason="Concurrent close",
            )
            await session.commit()
            return grant.id, changed

    revoke_results = await asyncio.gather(revoke_once(), revoke_once())
    assert {grant_id for grant_id, _ in revoke_results} == {grant_id}
    assert sorted(changed for _, changed in revoke_results) == [False, True]
