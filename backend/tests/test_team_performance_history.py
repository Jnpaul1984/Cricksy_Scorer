from __future__ import annotations

import asyncio
import datetime as dt
import json
import threading

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.exc import IntegrityError

from backend.services.organization_team_performance_access import (
    TeamPerformanceAccessError,
    grant_organization_team_performance,
    revoke_organization_team_performance,
)
from backend.services.game_performance_metadata_service import (
    GamePerformanceMetadataError,
    update_game_performance_metadata,
)
from backend.services.school_team_readiness_service import (
    TeamReadinessRequest,
    evaluate_team_match_readiness,
)
from backend.sql_app.models import (
    Game,
    GamePerformanceMetadataAudit,
    GameStatus,
    Fixture,
    Organization,
    OrganizationMembership,
    OrganizationTeamPerformanceGrant,
    RoleEnum,
    Team,
    Tournament,
    User,
)
from backend.tests.school_test_helpers import (
    add_membership,
    create_club,
    create_school,
    register_user,
)
from backend.tests.test_school_team_analytics import (
    _hand_calculated_deliveries,
    _seed_team_game,
)


async def _grant(client: TestClient, organization_id: str, owner_id: str) -> None:
    async with client.session_maker() as session:  # type: ignore[attr-defined]
        await grant_organization_team_performance(
            session,
            organization_id=organization_id,
            operator_user_id=owner_id,
            reason="Approved readiness test",
        )
        await session.commit()


async def _add_history_game(
    client: TestClient,
    *,
    organization_id: str,
    owner_id: str,
    played_date: dt.date,
    reuse_team=None,
    current_overs: int = 20,
    original_overs: int | None = 25,
    deliveries=None,
) -> tuple[Team, Game]:
    team, game, target, opponent = await _seed_team_game(
        client,
        organization_id,
        owner_id,
        deliveries=deliveries,
        reuse_team=reuse_team,
        overs_limit=current_overs,
    )
    if deliveries is None:
        ledger = _hand_calculated_deliveries(target, opponent)
    else:
        ledger = deliveries
    async with client.session_maker() as session:  # type: ignore[attr-defined]
        stored = await session.get(Game, game.id)
        assert stored is not None
        stored.deliveries = ledger
        stored.actual_played_date = played_date
        stored.played_date_trust_state = "confirmed"
        stored.played_date_source = "staff_confirmed"
        stored.original_overs_limit = original_overs
        stored.original_format_trust_state = (
            "setup_capture" if original_overs is not None else "unknown"
        )
        stored.original_format_source = "school_match_setup" if original_overs is not None else None
        await session.commit()
    return team, game


@pytest.mark.asyncio
async def test_metadata_update_is_audited_atomic_revision_safe_and_preserves_original_format(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = register_user(school_client, "history-metadata-owner@example.com")
    organization = create_school(school_client, owner, "History Metadata")
    team, game = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 2, 2),
        original_overs=None,
    )

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await update_game_performance_metadata(
            session,
            game_id=game.id,
            actor_user_id=owner.id,
            expected_revision=1,
            reason="Confirm match record",
            played_date_supplied=True,
            played_date=dt.date(2026, 2, 1),
            original_overs_supplied=True,
            original_overs_limit=25,
        )
        assert saved.team_performance_metadata_revision == 2
        assert saved.original_overs_limit == 25
        assert saved.original_format_trust_state == "staff_corrected"
        assert saved.actual_played_date == dt.date(2026, 2, 1)
        audits = list(
            (
                await session.scalars(
                    select(GamePerformanceMetadataAudit)
                    .where(GamePerformanceMetadataAudit.game_id == game.id)
                    .order_by(GamePerformanceMetadataAudit.field_name)
                )
            ).all()
        )
        assert len(audits) == 2
        assert {audit.actor_user_id for audit in audits} == {owner.id}
        assert {audit.reason for audit in audits} == {"Confirm match record"}
        assert {audit.metadata_revision for audit in audits} == {2}
        audit_by_field = {audit.field_name: audit for audit in audits}
        assert audit_by_field["actual_played_date"].old_value == "2026-02-02"
        assert audit_by_field["actual_played_date"].new_value == "2026-02-01"
        assert audit_by_field["original_overs_limit"].old_value is None
        assert audit_by_field["original_overs_limit"].new_value == 25

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        retried = await update_game_performance_metadata(
            session,
            game_id=game.id,
            actor_user_id=owner.id,
            expected_revision=2,
            reason="Confirm match record",
            played_date_supplied=True,
            played_date=dt.date(2026, 2, 1),
            original_overs_supplied=True,
            original_overs_limit=25,
        )
        assert retried.team_performance_metadata_revision == 2
        audits_after_retry = list(
            (
                await session.scalars(
                    select(GamePerformanceMetadataAudit).where(
                        GamePerformanceMetadataAudit.game_id == game.id
                    )
                )
            ).all()
        )
        assert len(audits_after_retry) == 2

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(GamePerformanceMetadataError, match="stale"):
            await update_game_performance_metadata(
                session,
                game_id=game.id,
                actor_user_id=owner.id,
                expected_revision=1,
                reason="Conflicting correction",
                played_date_supplied=True,
                played_date=dt.date(2026, 2, 3),
                original_overs_supplied=False,
                original_overs_limit=None,
            )

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(GamePerformanceMetadataError, match="stale"):
            await update_game_performance_metadata(
                session,
                game_id=game.id,
                actor_user_id=owner.id,
                expected_revision=1,
                reason="Stale no-op",
                played_date_supplied=True,
                played_date=dt.date(2026, 2, 1),
                original_overs_supplied=False,
                original_overs_limit=None,
            )

    from backend.routes import game_admin

    async def get_game(db, *, game_id: str):
        return await db.get(Game, game_id)

    async def update_game(db, *, game_model: Game):
        await db.commit()
        await db.refresh(game_model)
        return game_model

    monkeypatch.setattr(game_admin.crud, "get_game", get_game)
    monkeypatch.setattr(game_admin.crud, "update_game", update_game)
    changed_limit = school_client.post(
        f"/games/{game.id}/overs-limit",
        json={"overs_limit": 18},
        headers=owner.headers,
    )
    assert changed_limit.status_code == 200, changed_limit.text
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, game.id)
        assert saved is not None
        assert saved.overs_limit == 18
        assert saved.original_overs_limit == 25
        assert saved.actual_played_date == dt.date(2026, 2, 1)
        assert saved.team_performance_metadata_revision == 2


@pytest.mark.asyncio
async def test_new_game_history_metadata_defaults_to_unknown_not_fixture_schedule(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "history-unknown-defaults@example.com")
    organization = create_school(school_client, owner, "History Unknown Defaults")
    _, game, _, _ = await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=None,
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        stored = await session.get(Game, game.id)
        assert stored is not None
        assert stored.actual_played_date is None
        assert stored.played_date_trust_state == "unknown"
        assert stored.played_date_source is None
        assert stored.original_overs_limit is None
        assert stored.original_format_trust_state == "unknown"
        assert stored.original_format_source is None
        assert stored.team_performance_metadata_revision == 1


@pytest.mark.asyncio
async def test_fixture_schedule_is_not_played_date_and_date_can_be_confirmed(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "history-fixture-date@example.com")
    organization = create_school(school_client, owner, "History Fixture Date")
    team, game, _, _ = await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=None,
    )
    scheduled_at = dt.datetime(2026, 8, 1, 14, tzinfo=dt.UTC)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        tournament = Tournament(
            name="History fixture tournament",
            organization_id=organization["id"],
        )
        session.add(tournament)
        await session.flush()
        fixture = Fixture(
            tournament_id=tournament.id,
            team_a_name="Saved Team",
            team_b_name="Opponent",
            team_a_id=team.id,
            scheduled_date=scheduled_at,
            game_id=game.id,
            status="completed",
        )
        session.add(fixture)
        await session.commit()

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        linked = await session.get(Game, game.id)
        assert linked is not None
        assert linked.actual_played_date is None
        await update_game_performance_metadata(
            session,
            game_id=game.id,
            actor_user_id=owner.id,
            expected_revision=1,
            reason="Confirm venue-local played date",
            played_date_supplied=True,
            played_date=dt.date(2026, 8, 2),
            original_overs_supplied=False,
            original_overs_limit=None,
        )
        saved_fixture = await session.get(Fixture, fixture.id)
        assert saved_fixture is not None
        assert saved_fixture.scheduled_date is not None
        assert saved_fixture.scheduled_date.date() == scheduled_at.date()


@pytest.mark.asyncio
async def test_metadata_route_rejects_unauthorized_actor_and_returns_no_audit_identity(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "history-route-owner@example.com")
    scorer = register_user(school_client, "history-route-scorer@example.com")
    viewer = register_user(school_client, "history-route-viewer@example.com")
    outsider = register_user(school_client, "history-route-outsider@example.com")
    organization = create_school(school_client, owner, "History Route")
    add_membership(school_client, owner, organization["id"], scorer.id, "scorer")
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    _, game = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 3, 1),
        original_overs=None,
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        global_user = await session.get(User, outsider.id)
        assert global_user is not None
        global_user.role = RoleEnum.org_pro
        global_user.org_id = organization["id"]
        global_user.is_superuser = True
        await session.commit()

    metadata = school_client.get(
        f"/games/{game.id}/team-performance-metadata",
        headers=owner.headers,
    )
    assert metadata.status_code == 200, metadata.text
    assert metadata.json()["metadata_revision"] == 1
    assert owner.id not in metadata.text

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(HTTPException) as denied_directly:
            await update_game_performance_metadata(
                session,
                game_id=game.id,
                actor_user_id=outsider.id,
                expected_revision=1,
                reason="Global role is not membership authority",
                played_date_supplied=True,
                played_date=dt.date(2026, 3, 1),
                original_overs_supplied=False,
                original_overs_limit=None,
            )
        assert denied_directly.value.status_code == 404

    invalid_date = school_client.patch(
        f"/games/{game.id}/team-performance-metadata",
        json={
            "expected_revision": 1,
            "reason": "Date must not contain a time",
            "actual_played_date": "2026-03-01T12:00:00+02:00",
        },
        headers=owner.headers,
    )
    assert invalid_date.status_code == 422

    denied = school_client.patch(
        f"/games/{game.id}/team-performance-metadata",
        json={
            "expected_revision": 1,
            "reason": "Viewer should not have mutation authority",
            "actual_played_date": "2026-03-02",
        },
        headers=viewer.headers,
    )
    assert denied.status_code == 403

    response = school_client.patch(
        f"/games/{game.id}/team-performance-metadata",
        json={
            "expected_revision": 1,
            "reason": "Scorer confirms date",
            "actual_played_date": "2026-03-02",
        },
        headers=scorer.headers,
    )
    assert response.status_code == 200, response.text
    assert response.json() == {
        "actual_played_date": "2026-03-02",
        "played_date_trust_state": "confirmed",
        "original_overs_limit": None,
        "original_format_trust_state": "unknown",
        "metadata_revision": 2,
    }
    assert owner.id not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("match_count", "expected_state"),
    [(0, "not_ready"), (4, "not_ready"), (5, "ready"), (6, "ready")],
)
async def test_readiness_five_match_threshold_latest_five_and_safe_response(
    school_client: TestClient,
    match_count: int,
    expected_state: str,
) -> None:
    owner = register_user(school_client, f"history-count-{match_count}@example.com")
    organization = create_school(school_client, owner, f"History Count {match_count}")
    team = None
    games: list[Game] = []
    if match_count == 0:
        team, game = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 4, 1),
        )
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            saved = await session.get(Game, game.id)
            assert saved is not None
            saved.match_purpose = "practice"
            await session.commit()
    for index in range(match_count):
        team, game = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 4, index + 1),
            reuse_team=team,
        )
        games.append(game)
    assert team is not None
    await _grant(school_client, organization["id"], owner.id)

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await evaluate_team_match_readiness(
            session,
            TeamReadinessRequest(
                actor_user_id=owner.id,
                organization_id=organization["id"],
                team_id=team.id if team is not None else "not-used",
                as_of_date=dt.date(2026, 5, 1),
            ),
        )

    assert result is not None
    assert result.required_history == 5
    assert result.usable_prior_match_count == match_count
    assert result.remaining_match_count == max(5 - match_count, 0)
    assert result.state == expected_state
    assert result.usable_batting_match_count == match_count
    assert result.usable_bowling_match_count == match_count
    assert len(result.selected_sources) == min(5, match_count)
    assert [source.played_date for source in result.selected_sources] == sorted(
        [dt.date(2026, 4, index + 1) for index in range(match_count)],
        reverse=True,
    )[:5]
    assert [source.game_id for source in result.selected_sources] == [
        game.id for game in reversed(games[-5:])
    ]

    if match_count == 6:
        response = school_client.get(
            f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}/readiness",
            params={"as_of_date": "2026-05-01"},
            headers=owner.headers,
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["required_history"] == 5
        assert payload["usable_prior_match_count"] == 6
        assert payload["state"] == "ready"
        assert "selected_sources" not in payload
        assert all(game.id not in response.text for game in games)
        assert owner.id not in response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_readiness_parity_and_original_format_not_current_limit(
    school_client: TestClient,
    organization_type: str,
) -> None:
    owner = register_user(school_client, f"history-parity-{organization_type}@example.com")
    create_organization = create_school if organization_type == "school" else create_club
    organization = create_organization(school_client, owner, "History Parity")
    team = None
    for index, (current_limit, original_limit) in enumerate(((25, 50), (18, 25))):
        team, _ = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 6, index + 1),
            reuse_team=team,
            current_overs=current_limit,
            original_overs=original_limit,
        )
    assert team is not None
    await _grant(school_client, organization["id"], owner.id)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await evaluate_team_match_readiness(
            session,
            TeamReadinessRequest(
                actor_user_id=owner.id,
                organization_id=organization["id"],
                team_id=team.id,
                as_of_date=dt.date(2026, 7, 1),
            ),
        )
    assert result.usable_prior_match_count == 1
    assert result.exclusion_counts["wrong_original_format"] == 1
    assert result.state == "not_ready"


@pytest.mark.asyncio
async def test_readiness_keeps_ordinary_and_evidence_exclusion_reasons_distinct(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "history-exclusions-owner@example.com")
    organization = create_school(school_client, owner, "History Exclusions")
    team = None
    games: list[Game] = []
    for index in range(8):
        team, game = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 8, index + 1),
            reuse_team=team,
            original_overs=None if index == 4 else 25,
        )
        games.append(game)

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        practice, unfinished, multi_day, unsupported_rules, _, unknown_date, no_ledger, invalid = [
            await session.get(Game, game.id) for game in games
        ]
        assert all(
            game is not None
            for game in (
                practice,
                unfinished,
                multi_day,
                unsupported_rules,
                unknown_date,
                no_ledger,
                invalid,
            )
        )
        practice.match_purpose = "practice"
        unfinished.status = GameStatus.started
        multi_day.match_type = "multi_day"
        multi_day.days_limit = 2
        unsupported_rules.match_rules = {"version": 1}
        unknown_date.actual_played_date = None
        unknown_date.played_date_trust_state = "unknown"
        unknown_date.played_date_source = None
        no_ledger.deliveries = []
        invalid.deliveries = [*invalid.deliveries, {"inning": 3}]
        await session.commit()

    assert team is not None
    await _grant(school_client, organization["id"], owner.id)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await evaluate_team_match_readiness(
            session,
            TeamReadinessRequest(
                actor_user_id=owner.id,
                organization_id=organization["id"],
                team_id=team.id,
                as_of_date=dt.date(2026, 9, 1),
            ),
        )
    assert result.usable_prior_match_count == 0
    assert result.state == "not_ready"
    for reason in (
        "non_official_match",
        "not_completed",
        "multi_day_match",
        "unsupported_match_rules",
        "unknown_original_format",
        "unknown_played_date",
        "missing_ledger",
        "unsupported_innings",
    ):
        assert result.exclusion_counts[reason] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("source_change", "candidate_expected"),
    [
        (None, True),
        ("malformed-source", True),
        ({"organization_id": "same-org"}, True),
        ({"organization_id": "same-org", "team_id": "missing-team"}, True),
        ("cross-organization", False),
        ("duplicate-target", True),
    ],
)
async def test_readiness_fails_closed_for_opponent_source_ownership(
    school_client: TestClient,
    source_change,
    candidate_expected: bool,
) -> None:
    owner = register_user(school_client, f"history-source-{str(source_change)[:8]}@example.com")
    organization = create_school(school_client, owner, "History Source Boundary")
    team, game = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )
    foreign_team_id = None
    if source_change == "cross-organization":
        foreign_owner = register_user(school_client, "history-foreign-owner@example.com")
        foreign_organization = create_school(
            school_client, foreign_owner, "History Foreign Opponent"
        )
        foreign_team, _ = await _add_history_game(
            school_client,
            organization_id=foreign_organization["id"],
            owner_id=foreign_owner.id,
            played_date=dt.date(2026, 8, 1),
        )
        foreign_team_id = foreign_team.id
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        stored = await session.get(Game, game.id)
        assert stored is not None
        side = dict(stored.team_b)
        if source_change is None:
            side["school_source"] = None
        elif source_change == "malformed-source":
            side["school_source"] = "malformed"
        elif source_change == "duplicate-target":
            side["school_source"] = {
                "organization_id": organization["id"],
                "team_id": team.id,
            }
        elif source_change == "cross-organization":
            side["school_source"] = {
                "organization_id": foreign_organization["id"],
                "team_id": foreign_team.id,
            }
        elif source_change["organization_id"] == "same-org":
            side["school_source"] = {
                "organization_id": organization["id"],
                "team_id": source_change.get("team_id"),
            }
        else:
            side["school_source"] = source_change
        stored.team_b = side
        await session.commit()
    await _grant(school_client, organization["id"], owner.id)

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await evaluate_team_match_readiness(
            session,
            TeamReadinessRequest(
                actor_user_id=owner.id,
                organization_id=organization["id"],
                team_id=team.id,
                as_of_date=dt.date(2026, 9, 1),
            ),
        )
    assert result.usable_prior_match_count == 0
    if candidate_expected:
        assert result.exclusion_counts["ambiguous_team_attribution"] == 1

    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}/readiness",
        params={"as_of_date": "2026-09-01"},
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["usable_prior_match_count"] == 0
    assert "missing-team" not in response.text
    assert "foreign-team" not in response.text
    if foreign_team_id is not None:
        assert foreign_team_id not in response.text


@pytest.mark.asyncio
async def test_readiness_accepts_genuinely_external_opponent(school_client: TestClient) -> None:
    owner = register_user(school_client, "history-external-owner@example.com")
    organization = create_school(school_client, owner, "History External Opponent")
    team, game = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        stored = await session.get(Game, game.id)
        assert stored is not None
        external_side = dict(stored.team_b)
        external_side.pop("school_source")
        stored.team_b = external_side
        await session.commit()
    await _grant(school_client, organization["id"], owner.id)

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await evaluate_team_match_readiness(
            session,
            TeamReadinessRequest(
                actor_user_id=owner.id,
                organization_id=organization["id"],
                team_id=team.id,
                as_of_date=dt.date(2026, 9, 1),
            ),
        )
    assert result.usable_prior_match_count == 1
    assert result.state == "not_ready"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("bad_evidence", "reason"),
    [
        ({"inning": 99}, "unsupported_innings"),
        (
            {
                "inning": 1,
                "is_wicket": True,
                "dismissal_type": "not-a-dismissal",
            },
            "invalid_ledger",
        ),
    ],
)
async def test_readiness_rejects_unsupported_or_invalid_evidence_with_other_valid_innings(
    school_client: TestClient,
    bad_evidence: dict[str, object],
    reason: str,
) -> None:
    owner = register_user(school_client, f"history-bad-evidence-{reason}@example.com")
    organization = create_school(school_client, owner, "History Bad Evidence")
    team, game = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        stored = await session.get(Game, game.id)
        assert stored is not None
        if bad_evidence["inning"] == 99:
            stored.deliveries = [*stored.deliveries, bad_evidence]
        else:
            invalid = dict(stored.deliveries[0])
            invalid.update(
                is_wicket=True,
                dismissal_type="not-a-dismissal",
                dismissed_player_id=invalid["striker_id"],
            )
            stored.deliveries = [invalid, *stored.deliveries[1:]]
        await session.commit()
    await _grant(school_client, organization["id"], owner.id)

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await evaluate_team_match_readiness(
            session,
            TeamReadinessRequest(
                actor_user_id=owner.id,
                organization_id=organization["id"],
                team_id=team.id,
                as_of_date=dt.date(2026, 9, 1),
            ),
        )
    assert result.usable_prior_match_count == 0
    assert result.exclusion_counts[reason] == 1


@pytest.mark.asyncio
async def test_readiness_payload_byte_overflow_is_unavailable(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = register_user(school_client, "history-payload-owner@example.com")
    organization = create_school(school_client, owner, "History Payload Bound")
    team, _ = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )
    await _grant(school_client, organization["id"], owner.id)
    import backend.services.school_team_readiness_service as readiness_service

    monkeypatch.setattr(readiness_service, "MAX_DELIVERY_PAYLOAD_BYTES", 0)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await evaluate_team_match_readiness(
            session,
            TeamReadinessRequest(
                actor_user_id=owner.id,
                organization_id=organization["id"],
                team_id=team.id,
                as_of_date=dt.date(2026, 9, 1),
            ),
        )
    assert result.state == "data_unavailable"
    assert result.exclusion_counts["scope_too_large"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("fields", "expected_error"),
    [
        (
            {"played_date_source": None},
            "ck_games_played_date_provenance",
        ),
        (
            {"original_overs_limit": None},
            "ck_games_original_format_provenance",
        ),
        (
            {"original_format_source": None},
            "ck_games_original_format_provenance",
        ),
        (
            {
                "original_format_trust_state": "staff_corrected",
                "original_format_source": None,
            },
            "ck_games_original_format_provenance",
        ),
        (
            {
                "original_format_trust_state": "staff_corrected",
                "original_overs_limit": None,
                "original_format_source": "staff_correction",
            },
            "ck_games_original_format_provenance",
        ),
    ],
)
async def test_provenance_constraints_reject_null_trusted_fields(
    school_client: TestClient,
    fields: dict[str, object],
    expected_error: str,
) -> None:
    owner = register_user(school_client, f"history-check-{str(fields)[:8]}@example.com")
    organization = create_school(school_client, owner, "History Provenance Constraints")
    _, game = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(IntegrityError, match=expected_error):
            await session.execute(
                Game.__table__.update().where(Game.id == game.id).values(**fields)
            )
        await session.rollback()


@pytest.mark.asyncio
async def test_metadata_audit_failure_rolls_back_game_update(school_client: TestClient) -> None:
    owner = register_user(school_client, "history-audit-failure@example.com")
    organization = create_school(school_client, owner, "History Audit Failure")
    _, game = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]

        def reject_audit_flush(sync_session, flush_context, instances) -> None:
            if any(isinstance(row, GamePerformanceMetadataAudit) for row in sync_session.new):
                raise RuntimeError("injected audit write failure")

        event.listen(session.sync_session, "before_flush", reject_audit_flush)
        try:
            with pytest.raises(RuntimeError, match="injected audit write failure"):
                await update_game_performance_metadata(
                    session,
                    game_id=game.id,
                    actor_user_id=owner.id,
                    expected_revision=1,
                    reason="Test atomic audit write",
                    played_date_supplied=True,
                    played_date=dt.date(2026, 8, 2),
                    original_overs_supplied=False,
                    original_overs_limit=None,
                )
        finally:
            event.remove(session.sync_session, "before_flush", reject_audit_flush)

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, game.id)
        audits = list(
            (
                await session.scalars(
                    select(GamePerformanceMetadataAudit).where(
                        GamePerformanceMetadataAudit.game_id == game.id
                    )
                )
            ).all()
        )
        assert saved is not None
        assert saved.actual_played_date == dt.date(2026, 8, 1)
        assert saved.team_performance_metadata_revision == 1
        assert audits == []


@pytest.mark.asyncio
async def test_conflicting_postgres_metadata_writers_cannot_both_commit(
    school_client: TestClient,
) -> None:
    async with school_client.session_maker() as probe:  # type: ignore[attr-defined]
        if probe.get_bind().dialect.name != "postgresql":
            pytest.skip("row-lock concurrency is exercised in the migrated PostgreSQL CI gate")

    owner = register_user(school_client, "history-concurrent-owner@example.com")
    organization = create_school(school_client, owner, "History Concurrent Writers")
    _, game = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )
    barrier = asyncio.Barrier(2)

    async def update_date(value: dt.date):
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            await barrier.wait()
            try:
                await update_game_performance_metadata(
                    session,
                    game_id=game.id,
                    actor_user_id=owner.id,
                    expected_revision=1,
                    reason="Concurrent correction",
                    played_date_supplied=True,
                    played_date=value,
                    original_overs_supplied=False,
                    original_overs_limit=None,
                )
                return "committed"
            except GamePerformanceMetadataError as error:
                return error.status_code

    outcomes = await asyncio.gather(
        update_date(dt.date(2026, 8, 2)),
        update_date(dt.date(2026, 8, 3)),
    )
    assert outcomes.count("committed") == 1
    assert outcomes.count(409) == 1
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, game.id)
        audits = list(
            (
                await session.scalars(
                    select(GamePerformanceMetadataAudit).where(
                        GamePerformanceMetadataAudit.game_id == game.id
                    )
                )
            ).all()
        )
        assert saved is not None
        assert saved.team_performance_metadata_revision == 2
        assert saved.actual_played_date in {dt.date(2026, 8, 2), dt.date(2026, 8, 3)}
        assert len(audits) == 1
        assert audits[0].metadata_revision == 2


@pytest.mark.asyncio
async def test_same_value_postgres_metadata_writers_still_conflict_on_stale_revision(
    school_client: TestClient,
) -> None:
    async with school_client.session_maker() as probe:  # type: ignore[attr-defined]
        if probe.get_bind().dialect.name != "postgresql":
            pytest.skip("row-lock concurrency is exercised in the migrated PostgreSQL CI gate")

    owner = register_user(school_client, "history-concurrent-same-value@example.com")
    organization = create_school(school_client, owner, "History Concurrent Same Value")
    _, game = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )
    barrier = asyncio.Barrier(2)

    async def update_same_date():
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            await barrier.wait()
            try:
                await update_game_performance_metadata(
                    session,
                    game_id=game.id,
                    actor_user_id=owner.id,
                    expected_revision=1,
                    reason="Concurrent same-value correction",
                    played_date_supplied=True,
                    played_date=dt.date(2026, 8, 2),
                    original_overs_supplied=False,
                    original_overs_limit=None,
                )
                return "committed"
            except GamePerformanceMetadataError as error:
                return error.status_code

    outcomes = await asyncio.gather(update_same_date(), update_same_date())
    assert outcomes.count("committed") == 1
    assert outcomes.count(409) == 1
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, game.id)
        audits = list(
            (
                await session.scalars(
                    select(GamePerformanceMetadataAudit)
                    .where(GamePerformanceMetadataAudit.game_id == game.id)
                    .order_by(GamePerformanceMetadataAudit.metadata_revision)
                )
            ).all()
        )
        assert saved is not None
        assert saved.actual_played_date == dt.date(2026, 8, 2)
        assert saved.team_performance_metadata_revision == 2
        assert len(audits) == 1
        assert (
            audits[0].metadata_revision,
            audits[0].old_value,
            audits[0].new_value,
        ) == (2, "2026-08-01", "2026-08-02")


@pytest.mark.asyncio
async def test_metadata_update_refreshes_strongly_retained_game_before_auditing(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "history-retained-game-owner@example.com")
    organization = create_school(school_client, owner, "History Retained Game")
    _, game = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )
    async with school_client.session_maker() as retained_session:  # type: ignore[attr-defined]
        retained = await retained_session.get(Game, game.id)
        assert retained is not None
        assert retained.actual_played_date == dt.date(2026, 8, 1)

        async with school_client.session_maker() as correcting_session:  # type: ignore[attr-defined]
            corrected = await update_game_performance_metadata(
                correcting_session,
                game_id=game.id,
                actor_user_id=owner.id,
                expected_revision=1,
                reason="First correction",
                played_date_supplied=True,
                played_date=dt.date(2026, 8, 2),
                original_overs_supplied=False,
                original_overs_limit=None,
            )
            assert corrected.actual_played_date == dt.date(2026, 8, 2)

        saved = await update_game_performance_metadata(
            retained_session,
            game_id=game.id,
            actor_user_id=owner.id,
            expected_revision=2,
            reason="Second correction",
            played_date_supplied=True,
            played_date=dt.date(2026, 8, 3),
            original_overs_supplied=False,
            original_overs_limit=None,
        )
        assert saved is retained
        assert retained.actual_played_date == dt.date(2026, 8, 3)
        assert retained.team_performance_metadata_revision == 3
        audits = list(
            (
                await retained_session.scalars(
                    select(GamePerformanceMetadataAudit)
                    .where(GamePerformanceMetadataAudit.game_id == game.id)
                    .order_by(GamePerformanceMetadataAudit.metadata_revision)
                )
            ).all()
        )
        assert [
            (audit.metadata_revision, audit.old_value, audit.new_value) for audit in audits
        ] == [
            (2, "2026-08-01", "2026-08-02"),
            (3, "2026-08-02", "2026-08-03"),
        ]


@pytest.mark.asyncio
async def test_readiness_refreshes_corrected_date_in_reused_session(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "history-fresh-date-owner@example.com")
    organization = create_school(school_client, owner, "History Fresh Date")
    team = None
    games: list[Game] = []
    for day in range(1, 6):
        team, game = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 8, day),
            reuse_team=team,
        )
        games.append(game)
    assert team is not None
    await _grant(school_client, organization["id"], owner.id)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        request = TeamReadinessRequest(
            actor_user_id=owner.id,
            organization_id=organization["id"],
            team_id=team.id,
            as_of_date=dt.date(2026, 8, 10),
        )
        first = await evaluate_team_match_readiness(session, request)
        assert first.usable_prior_match_count == 5

        async with school_client.session_maker() as correction_session:  # type: ignore[attr-defined]
            await update_game_performance_metadata(
                correction_session,
                game_id=games[0].id,
                actor_user_id=owner.id,
                expected_revision=1,
                reason="Correct date to after the boundary",
                played_date_supplied=True,
                played_date=dt.date(2026, 8, 12),
                original_overs_supplied=False,
                original_overs_limit=None,
            )

        corrected = await evaluate_team_match_readiness(session, request)
        assert corrected.usable_prior_match_count == 4
        assert corrected.state == "not_ready"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case_name", "game_count", "bytes_per_game", "candidate_limit"),
    [
        ("single", 1, 5 * 1024 * 1024 + 1024, None),
        ("cumulative", 2, 3 * 1024 * 1024, None),
        ("candidate_count", 2, 2 * 1024 * 1024, 1),
    ],
)
async def test_readiness_oversize_query_does_not_hydrate_delivery_payloads(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    case_name: str,
    game_count: int,
    bytes_per_game: int,
    candidate_limit: int | None,
) -> None:
    owner = register_user(school_client, f"history-bounded-{case_name}@example.com")
    organization = create_school(school_client, owner, f"History Bounded {case_name}")
    team = None
    games: list[Game] = []
    for index in range(game_count):
        team, game = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 8, index + 1),
            reuse_team=team,
        )
        games.append(game)
    assert team is not None
    padding = "x" * bytes_per_game
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        for game in games:
            stored = await session.get(Game, game.id)
            assert stored is not None
            stored.deliveries = [{"payload_padding": padding}]
        await session.commit()
    await _grant(school_client, organization["id"], owner.id)

    import backend.services.school_team_readiness_service as readiness_service

    if candidate_limit is not None:
        monkeypatch.setattr(readiness_service, "MAX_CANDIDATE_GAMES", candidate_limit)
    request = TeamReadinessRequest(
        actor_user_id=owner.id,
        organization_id=organization["id"],
        team_id=team.id,
        as_of_date=dt.date(2026, 9, 1),
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        tracked = [await session.get(Game, game.id) for game in games]
        assert all(game is not None for game in tracked)
        for game in tracked:
            session.expire(game, ["deliveries"])
        rows = (
            await session.execute(
                readiness_service._readiness_candidates_stmt(
                    request,
                    session.get_bind().dialect.name,
                )
            )
        ).all()
        assert len(rows) == game_count
        assert all(row[1] is None for row in rows)
        assert all("deliveries" in inspect(row[0]).unloaded for row in rows)
        assert rows[0][2] == game_count
        if candidate_limit is not None:
            assert rows[0][2] > candidate_limit
            assert rows[0][3] < readiness_service.MAX_DELIVERY_PAYLOAD_BYTES
        else:
            assert rows[0][3] > readiness_service.MAX_DELIVERY_PAYLOAD_BYTES

        result = await evaluate_team_match_readiness(session, request)
        assert result.state == "data_unavailable"
        assert result.exclusion_counts["scope_too_large"] == 1
        assert all("deliveries" in inspect(game).unloaded for game in tracked)


@pytest.mark.asyncio
async def test_readiness_payload_growth_before_candidate_snapshot_is_rejected(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "history-concurrent-payload-owner@example.com")
    organization = create_school(school_client, owner, "History Concurrent Payload Growth")
    team, game = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )
    await _grant(school_client, organization["id"], owner.id)
    writer_started = threading.Event()
    writer_finished = threading.Event()
    update_errors: list[BaseException] = []
    large_ledger = [{"payload_padding": "x" * (5 * 1024 * 1024 + 1024)}]

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("Concurrent payload snapshot is covered in migrated PostgreSQL tests")
        sync_url = session.get_bind().url.set(drivername="postgresql+psycopg2")

        def update_ledger() -> None:
            try:
                writer_started.wait(timeout=10)
                writer_engine = create_engine(sync_url)
                with writer_engine.begin() as connection:
                    connection.exec_driver_sql(
                        "UPDATE games SET deliveries = CAST(%s AS JSONB) WHERE id = %s",
                        (
                            json.dumps(large_ledger),
                            game.id,
                        ),
                    )
                writer_engine.dispose()
            except BaseException as error:
                update_errors.append(error)
            finally:
                writer_finished.set()

        writer = threading.Thread(target=update_ledger, daemon=True)
        writer.start()
        candidate_queries = 0

        def grow_before_snapshot(conn, cursor, statement, parameters, context, executemany):
            nonlocal candidate_queries
            if "readiness_candidate_metrics" in statement:
                candidate_queries += 1
                writer_started.set()
                assert writer_finished.wait(timeout=15)

        event.listen(session.sync_session.bind, "before_cursor_execute", grow_before_snapshot)
        try:
            result = await evaluate_team_match_readiness(
                session,
                TeamReadinessRequest(
                    actor_user_id=owner.id,
                    organization_id=organization["id"],
                    team_id=team.id,
                    as_of_date=dt.date(2026, 9, 1),
                ),
            )
        finally:
            event.remove(session.sync_session.bind, "before_cursor_execute", grow_before_snapshot)
            writer.join(timeout=10)
        assert not update_errors
        assert candidate_queries == 1
        assert result.state == "data_unavailable"
        assert result.exclusion_counts["scope_too_large"] == 1


@pytest.mark.asyncio
async def test_readiness_excludes_same_day_groups_future_reference_and_invalid_games(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "history-chronology-owner@example.com")
    organization = create_school(school_client, owner, "History Chronology")
    team = None
    same_day: Game | None = None
    for day in (1, 2, 2, 3, 4, 5, 6, 8, 9):
        team, game = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 7, day),
            reuse_team=team,
        )
        if day == 5:
            async with school_client.session_maker() as session:  # type: ignore[attr-defined]
                stored = await session.get(Game, game.id)
                assert stored is not None
                stored.deliveries = [*stored.deliveries, {"inning": 3}]
                await session.commit()
        if day == 8:
            same_day = game
    assert team is not None and same_day is not None
    await _grant(school_client, organization["id"], owner.id)

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await evaluate_team_match_readiness(
            session,
            TeamReadinessRequest(
                actor_user_id=owner.id,
                organization_id=organization["id"],
                team_id=team.id,
                as_of_date=dt.date(2026, 7, 8),
                reference_game_id=same_day.id,
            ),
        )
    assert result.usable_prior_match_count == 4
    assert result.exclusion_counts["reference_game"] == 1
    assert result.exclusion_counts["not_prior_to_boundary"] == 1
    assert result.exclusion_counts["same_date_ambiguous"] == 2
    assert result.exclusion_counts["unsupported_innings"] == 1
    assert result.state == "not_ready"


@pytest.mark.asyncio
@pytest.mark.parametrize("external_opponent", [False, True])
async def test_readiness_reference_uses_validated_scope_without_history_ledger_requirements(
    school_client: TestClient,
    external_opponent: bool,
) -> None:
    owner = register_user(school_client, f"history-reference-valid-{external_opponent}@example.com")
    organization = create_school(school_client, owner, "History Valid Reference")
    team: Team | None = None
    for day in range(1, 6):
        team, _ = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 8, day),
            reuse_team=team,
        )
    assert team is not None
    _, reference = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 6),
        reuse_team=team,
        current_overs=18,
        deliveries=[{"invalid": "history ledger must not be inspected"}],
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        stored = await session.get(Game, reference.id)
        assert stored is not None
        stored.status = GameStatus.in_progress
        if external_opponent:
            side = dict(stored.team_b)
            side.pop("school_source")
            stored.team_b = side
        await session.commit()
    await _grant(school_client, organization["id"], owner.id)
    request = TeamReadinessRequest(
        actor_user_id=owner.id,
        organization_id=organization["id"],
        team_id=team.id,
        as_of_date=dt.date(2026, 8, 6),
        reference_game_id=reference.id,
    )

    from backend.services.school_team_readiness_service import _readiness_candidates_stmt

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        candidate_rows = (
            await session.execute(
                _readiness_candidates_stmt(request, session.get_bind().dialect.name)
            )
        ).all()
        reference_row = next(row for row in candidate_rows if row[0].id == reference.id)
        assert reference_row[1] is None
        assert "deliveries" in inspect(reference_row[0]).unloaded
        result = await evaluate_team_match_readiness(session, request)

    assert result.state == "ready"
    assert result.usable_prior_match_count == 5
    assert result.exclusion_counts["reference_game"] == 1

    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}/readiness",
        params={"as_of_date": "2026-08-06", "reference_game_id": reference.id},
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "ready"
    assert response.json()["usable_prior_match_count"] == 5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "invalid_reference",
    [
        "null-source",
        "malformed-source",
        "nonexistent-opponent",
        "duplicate-target",
        "unknown-format",
        "wrong-format",
        "unsupported-match-type",
    ],
)
async def test_readiness_reference_rejects_unresolved_team_scope_and_format(
    school_client: TestClient,
    invalid_reference: str,
) -> None:
    owner = register_user(
        school_client, f"history-reference-invalid-{invalid_reference}@example.com"
    )
    organization = create_school(school_client, owner, "History Invalid Reference")
    team, reference = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 6),
        current_overs=18,
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        stored = await session.get(Game, reference.id)
        assert stored is not None
        if invalid_reference in {
            "null-source",
            "malformed-source",
            "nonexistent-opponent",
            "duplicate-target",
        }:
            side = dict(stored.team_b)
            if invalid_reference == "null-source":
                side["school_source"] = None
            elif invalid_reference == "malformed-source":
                side["school_source"] = "not-a-source"
            elif invalid_reference == "nonexistent-opponent":
                side["school_source"] = {
                    "organization_id": organization["id"],
                    "team_id": "missing-opponent-team",
                }
            else:
                side["school_source"] = {
                    "organization_id": organization["id"],
                    "team_id": team.id,
                }
            stored.team_b = side
        elif invalid_reference == "unknown-format":
            stored.original_overs_limit = None
            stored.original_format_trust_state = "unknown"
            stored.original_format_source = None
        elif invalid_reference == "wrong-format":
            stored.original_overs_limit = 18
        else:
            stored.match_type = "multi_day"
        await session.commit()
    await _grant(school_client, organization["id"], owner.id)
    request = TeamReadinessRequest(
        actor_user_id=owner.id,
        organization_id=organization["id"],
        team_id=team.id,
        as_of_date=dt.date(2026, 8, 6),
        reference_game_id=reference.id,
    )

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await evaluate_team_match_readiness(session, request)
    assert result.state == "data_unavailable"
    assert result.usable_prior_match_count == 0
    assert result.exclusion_counts["reference_date_unavailable"] == 1

    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}/readiness",
        params={"as_of_date": "2026-08-06", "reference_game_id": reference.id},
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "data_unavailable"
    assert response.json()["usable_prior_match_count"] == 0
    assert "missing-opponent-team" not in response.text


@pytest.mark.asyncio
async def test_readiness_reference_rejects_cross_organization_opponent_without_leakage(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "history-reference-foreign-owner@example.com")
    organization = create_school(school_client, owner, "History Reference Foreign")
    team, reference = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 6),
    )
    foreign_owner = register_user(school_client, "history-reference-foreign-team-owner@example.com")
    foreign_organization = create_school(school_client, foreign_owner, "History Foreign Reference")
    foreign_team, _ = await _add_history_game(
        school_client,
        organization_id=foreign_organization["id"],
        owner_id=foreign_owner.id,
        played_date=dt.date(2026, 8, 6),
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        stored = await session.get(Game, reference.id)
        assert stored is not None
        side = dict(stored.team_b)
        side["school_source"] = {
            "organization_id": foreign_organization["id"],
            "team_id": foreign_team.id,
        }
        stored.team_b = side
        await session.commit()
    await _grant(school_client, organization["id"], owner.id)
    request = TeamReadinessRequest(
        actor_user_id=owner.id,
        organization_id=organization["id"],
        team_id=team.id,
        as_of_date=dt.date(2026, 8, 6),
        reference_game_id=reference.id,
    )

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(TeamPerformanceAccessError) as error:
            await evaluate_team_match_readiness(session, request)
    assert error.value.status_code == 404

    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}/readiness",
        params={"as_of_date": "2026-08-06", "reference_game_id": reference.id},
        headers=owner.headers,
    )
    assert response.status_code == 404
    assert foreign_team.id not in response.text
    assert "usable_prior_match_count" not in response.text


@pytest.mark.asyncio
async def test_readiness_is_unavailable_when_a_same_day_tie_can_change_the_latest_five(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "history-cutoff-tie-owner@example.com")
    organization = create_school(school_client, owner, "History Cutoff Tie")
    team = None
    for day in (1, 2, 3, 4, 5, 7, 7):
        team, _ = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 7, day),
            reuse_team=team,
        )
    assert team is not None
    await _grant(school_client, organization["id"], owner.id)

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await evaluate_team_match_readiness(
            session,
            TeamReadinessRequest(
                actor_user_id=owner.id,
                organization_id=organization["id"],
                team_id=team.id,
                as_of_date=dt.date(2026, 7, 8),
            ),
        )
    assert result.usable_prior_match_count == 5
    assert result.exclusion_counts["same_date_ambiguous"] == 2
    assert result.state == "data_unavailable"
    assert result.selected_sources == ()


@pytest.mark.asyncio
async def test_readiness_denies_direct_scorer_calls_and_reports_scope_overflow(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = register_user(school_client, "history-denied-owner@example.com")
    scorer = register_user(school_client, "history-denied-scorer@example.com")
    organization = create_school(school_client, owner, "History Denial")
    add_membership(school_client, owner, organization["id"], scorer.id, "scorer")
    team, _ = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )
    await _grant(school_client, organization["id"], owner.id)

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(TeamPerformanceAccessError):
            await evaluate_team_match_readiness(
                session,
                TeamReadinessRequest(
                    actor_user_id=scorer.id,
                    organization_id=organization["id"],
                    team_id=team.id,
                    as_of_date=dt.date(2026, 9, 1),
                ),
            )

    import backend.services.school_team_readiness_service as readiness_service

    monkeypatch.setattr(readiness_service, "MAX_CANDIDATE_GAMES", 0)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await evaluate_team_match_readiness(
            session,
            TeamReadinessRequest(
                actor_user_id=owner.id,
                organization_id=organization["id"],
                team_id=team.id,
                as_of_date=dt.date(2026, 9, 1),
            ),
        )
    assert result.state == "data_unavailable"
    assert result.usable_prior_match_count == 0
    assert result.exclusion_counts["scope_too_large"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "access_loss",
    [
        "inactive_user",
        "inactive_organization",
        "removed_membership",
        "revoked_grant",
        "expired_grant",
    ],
)
async def test_readiness_revalidates_direct_service_access_loss(
    school_client: TestClient,
    access_loss: str,
) -> None:
    owner = register_user(school_client, f"history-access-loss-{access_loss}@example.com")
    organization = create_school(school_client, owner, f"History Access Loss {access_loss}")
    team, _ = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 8, 1),
    )
    if access_loss == "expired_grant":
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            now = dt.datetime.now(dt.UTC)
            await grant_organization_team_performance(
                session,
                organization_id=organization["id"],
                operator_user_id=owner.id,
                reason="Expired access test",
                effective_from=now - dt.timedelta(days=2),
                effective_until=now - dt.timedelta(days=1),
            )
            await session.commit()
    else:
        await _grant(school_client, organization["id"], owner.id)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        if access_loss == "inactive_user":
            actor = await session.get(User, owner.id)
            assert actor is not None
            actor.is_active = False
        elif access_loss == "inactive_organization":
            org = await session.get(Organization, organization["id"])
            assert org is not None
            org.status = "suspended"
        elif access_loss == "removed_membership":
            membership = await session.scalar(
                select(OrganizationMembership).where(
                    OrganizationMembership.organization_id == organization["id"],
                    OrganizationMembership.user_id == owner.id,
                )
            )
            assert membership is not None
            await session.delete(membership)
        elif access_loss == "revoked_grant":
            grant = await session.scalar(
                select(OrganizationTeamPerformanceGrant).where(
                    OrganizationTeamPerformanceGrant.organization_id == organization["id"]
                )
            )
            assert grant is not None
            await revoke_organization_team_performance(
                session,
                organization_id=organization["id"],
                grant_id=grant.id,
                operator_user_id=owner.id,
                reason="Revoke access test",
            )
        await session.commit()

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(TeamPerformanceAccessError):
            await evaluate_team_match_readiness(
                session,
                TeamReadinessRequest(
                    actor_user_id=owner.id,
                    organization_id=organization["id"],
                    team_id=team.id,
                    as_of_date=dt.date(2026, 9, 1),
                ),
            )


def test_metadata_update_service_rejects_missing_game(school_client: TestClient) -> None:
    async def update() -> None:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            with pytest.raises(GamePerformanceMetadataError):
                await update_game_performance_metadata(
                    session,
                    game_id="missing-game",
                    actor_user_id="missing-user",
                    expected_revision=1,
                    reason="Must not exist",
                    played_date_supplied=True,
                    played_date=dt.date(2026, 9, 1),
                    original_overs_supplied=False,
                    original_overs_limit=None,
                )

    asyncio.run(update())
