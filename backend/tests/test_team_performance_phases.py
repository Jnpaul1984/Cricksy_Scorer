"""Focused phase attribution for the private five-match Team pilot."""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.services.organization_team_performance_access import (
    TeamPerformanceAccessError,
    revoke_organization_team_performance,
)
from backend.services.school_team_readiness_service import (
    TeamReadinessRequest,
    _ordered_phase_rows,
    calculate_team_phase_analysis,
)
from backend.sql_app.models import Game, OrganizationTeamPerformanceGrant
from backend.tests.school_test_helpers import (
    add_membership,
    create_club,
    create_school,
    register_user,
)
from backend.tests.test_team_performance_history import _add_history_game, _grant


def _positioned_innings(
    first: dict, *, legal_count: int = 121, with_extras: bool = True
) -> list[dict]:
    rows: list[dict] = []
    for legal in range(legal_count):
        over, ball = divmod(legal, 6)
        position = {"over_number": over, "ball_number": ball + 1}
        if with_extras and legal == 30:
            rows.append(
                dict(
                    first, **position, extra_type="wd", extra_runs=2, runs_off_bat=0, runs_scored=2
                )
            )
            rows.append(
                dict(
                    first, **position, extra_type="nb", extra_runs=1, runs_off_bat=0, runs_scored=1
                )
            )
        runs = 4 if legal == 30 else 6 if legal == 120 else 0
        rows.append(dict(first, **position, runs_off_bat=runs, runs_scored=runs))
    return rows


def test_phase_position_validation_rejects_missing_gaps_and_import_convention() -> None:
    row = {"inning": 1, "extra_type": None, "over_number": 0, "ball_number": 1}
    assert _ordered_phase_rows([row]) == [(row, 1)]
    assert _ordered_phase_rows([dict(row, ball_number=2)]) is None
    assert _ordered_phase_rows([dict(row, over_number=1)]) is None
    assert _ordered_phase_rows([dict(row, _source="historical")]) is None
    assert _ordered_phase_rows([dict(row, over_number=True)]) is None


@pytest.mark.asyncio
@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_phase_edges_extras_aggregate_and_safe_route(
    school_client: TestClient, organization_type: str
) -> None:
    owner = register_user(school_client, f"phases-{organization_type}@example.com")
    create = create_school if organization_type == "school" else create_club
    organization = create(school_client, owner, f"Phase {organization_type}")
    team = None
    games = []
    for day in range(1, 7):
        team, game = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 4, day),
            reuse_team=team,
            current_overs=18 if day == 6 else 25,
        )
        games.append(game)
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            stored = await session.get(Game, game.id)
            assert stored is not None
            batting = stored.deliveries[0]
            bowling = stored.deliveries[9]
            if day == 5:
                stored.team_a, stored.team_b = stored.team_b, stored.team_a
            if day == 6:
                stored.dls_enabled = True
            stored.deliveries = [
                *_positioned_innings(batting, legal_count=108 if day == 6 else 121),
                *_positioned_innings(bowling, legal_count=108 if day == 6 else 121),
            ]
            await session.commit()
    assert team is not None
    await _grant(school_client, organization["id"], owner.id)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await calculate_team_phase_analysis(
            session,
            TeamReadinessRequest(owner.id, organization["id"], team.id, dt.date(2026, 5, 1)),
        )
    assert result.readiness.state == "ready", result.readiness.exclusion_counts
    assert result.sample_size == 5
    assert result.phase_unavailable_matches == 0
    opening, middle, closing = result.phases
    assert (opening.start_over, opening.end_over) == (1, 5)
    assert (middle.start_over, middle.end_over) == (6, 20)
    assert (closing.start_over, closing.end_over) == (21, 25)
    assert opening.batting and opening.batting["team_runs"] == 0
    assert opening.batting["legal_balls"] == 150
    assert middle.batting and middle.batting["team_runs"] == 5 * 4 + 5 * 3
    assert middle.batting["legal_balls"] == 4 * 90 + 78
    assert middle.batting["run_rate"] == round(
        middle.batting["team_runs"] * 6 / middle.batting["legal_balls"], 2
    )
    assert closing.batting and closing.batting["team_runs"] == 24
    assert closing.batting_observed_matches == 4
    assert closing.batting_unavailable_matches == 1
    assert closing.bowling and closing.bowling["bowling_economy"] is not None
    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}/phases",
        params={"as_of_date": "2026-05-01"},
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["sample_size"] == 5
    assert len(response.json()["phases"]) == 3
    assert all(game.id not in response.text for game in games)
    assert owner.id not in response.text


@pytest.mark.asyncio
async def test_phase_missing_positions_and_zero_denominators(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "phases-missing@example.com")
    organization = create_school(school_client, owner, "Phase missing")
    team = None
    games = []
    for day in range(1, 6):
        team, game = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 4, day),
            reuse_team=team,
        )
        games.append(game)
    assert team is not None
    await _grant(school_client, organization["id"], owner.id)
    request = TeamReadinessRequest(owner.id, organization["id"], team.id, dt.date(2026, 5, 1))
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        missing = await calculate_team_phase_analysis(session, request)
    assert missing.readiness.state == "ready"
    assert missing.phase_unavailable_matches == 5
    assert all(phase.batting is None and phase.bowling is None for phase in missing.phases)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        for game in games:
            stored = await session.get(Game, game.id)
            assert stored is not None
            wide_batting = stored.deliveries[3]
            wide_bowling = stored.deliveries[12]
            stored.deliveries = [
                dict(wide_batting, over_number=0, ball_number=1),
                dict(wide_bowling, over_number=0, ball_number=1),
            ]
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        corrected = await calculate_team_phase_analysis(session, request)
    assert corrected.phase_unavailable_matches == 0
    opening = corrected.phases[0]
    assert opening.batting and opening.batting["legal_balls"] == 0
    assert opening.batting["run_rate"] is None
    assert opening.bowling and opening.bowling["bowling_economy"] is None
    assert corrected.phases[1].batting is None
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        stored = await session.get(Game, games[-1].id)
        assert stored is not None
        rows = list(stored.deliveries)
        legal = dict(rows[0], extra_type=None, extra_runs=0, runs_scored=0)
        stored.deliveries = [rows[0], legal, rows[1]]
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        revised = await calculate_team_phase_analysis(session, request)
    assert revised.phases[0].batting and revised.phases[0].batting["legal_balls"] == 1
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        stored = await session.get(Game, games[-1].id)
        assert stored is not None
        stored.deliveries = [stored.deliveries[0], stored.deliveries[2]]
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        undone = await calculate_team_phase_analysis(session, request)
    assert undone.phases[0].batting and undone.phases[0].batting["run_rate"] is None


@pytest.mark.asyncio
async def test_phase_route_and_service_recheck_grant_role_and_team(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "phase-access-owner@example.com")
    scorer = register_user(school_client, "phase-access-scorer@example.com")
    organization = create_school(school_client, owner, "Phase access")
    foreign = create_school(school_client, owner, "Foreign phase access")
    add_membership(school_client, owner, organization["id"], scorer.id, "scorer")
    team, _ = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 4, 1),
    )
    route = f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}/phases"
    params = {"as_of_date": "2026-05-01"}
    assert school_client.get(route, params=params, headers=owner.headers).status_code == 403
    await _grant(school_client, organization["id"], owner.id)
    assert school_client.get(route, params=params, headers=scorer.headers).status_code == 403
    await _grant(school_client, foreign["id"], owner.id)
    assert (
        school_client.get(
            f"/api/organizations/{foreign['id']}/team-performance/teams/{team.id}/phases",
            params=params,
            headers=owner.headers,
        ).status_code
        == 404
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
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
            reason="Phase access test",
        )
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(TeamPerformanceAccessError):
            await calculate_team_phase_analysis(
                session,
                TeamReadinessRequest(owner.id, organization["id"], team.id, dt.date(2026, 5, 1)),
            )


@pytest.mark.asyncio
async def test_phase_workload_overflow_never_returns_a_phase(
    school_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import backend.services.school_team_readiness_service as readiness_service

    owner = register_user(school_client, "phase-overflow@example.com")
    organization = create_school(school_client, owner, "Phase overflow")
    team, _ = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 4, 1),
    )
    await _grant(school_client, organization["id"], owner.id)
    monkeypatch.setattr(readiness_service, "MAX_CANDIDATE_GAMES", 0)
    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}/phases",
        params={"as_of_date": "2026-05-01"},
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    assert response.json()["readiness"]["state"] == "data_unavailable"
    assert response.json()["readiness"]["exclusion_counts"]["scope_too_large"] == 1
    assert response.json()["phases"] == []
