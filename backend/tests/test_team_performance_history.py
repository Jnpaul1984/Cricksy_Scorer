from __future__ import annotations

import asyncio
import datetime as dt

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.services.organization_team_performance_access import (
    TeamPerformanceAccessError,
    grant_organization_team_performance,
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
    RoleEnum,
    Team,
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
        stored.original_format_source = (
            "school_match_setup" if original_overs is not None else None
        )
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

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        retried = await update_game_performance_metadata(
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
        assert retried.team_performance_metadata_revision == 2

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
        practice, unfinished, multi_day, unsupported_rules, _, unknown_date, no_ledger, invalid = (
            [await session.get(Game, game.id) for game in games]
        )
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
