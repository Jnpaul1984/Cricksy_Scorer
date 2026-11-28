"""Private Team coach report composition and response boundaries."""

from __future__ import annotations

import datetime as dt
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from backend.services.school_team_readiness_service import (
    TeamPhaseBand,
    TeamPhaseResult,
    TeamReadinessRequest,
    calculate_team_recent_form,
)
from backend.services.school_team_report_service import _observations, compose_team_coach_report
from backend.services.organization_team_performance_access import (
    revoke_organization_team_performance,
)
from backend.sql_app.models import Game, OrganizationTeamPerformanceGrant
from sqlalchemy import select
from backend.tests.school_test_helpers import (
    add_membership,
    create_club,
    create_school,
    register_user,
)
from backend.tests.test_team_performance_history import _add_history_game, _grant


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["school", "club"])
async def test_report_exact_five_and_safe_response(school_client: TestClient, kind: str) -> None:
    owner = register_user(school_client, f"report-{kind}@example.com")
    organization = (create_school if kind == "school" else create_club)(
        school_client, owner, f"Report {kind}"
    )
    team = None
    games = []
    for day in range(1, 7):
        team, game = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 4, day),
            reuse_team=team,
        )
        games.append(game)
    assert team is not None
    route = f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}/coach-report"
    params = {"as_of_date": "2026-05-01"}
    assert school_client.get(route, params=params, headers=owner.headers).status_code == 403
    await _grant(school_client, organization["id"], owner.id)
    scorer = register_user(school_client, f"report-scorer-{kind}@example.com")
    add_membership(school_client, owner, organization["id"], scorer.id, "scorer")
    assert school_client.get(route, params=params, headers=scorer.headers).status_code == 403
    foreign_organization = (create_school if kind == "school" else create_club)(
        school_client, owner, f"Foreign report {kind}"
    )
    foreign_route = f"/api/organizations/{foreign_organization['id']}/team-performance/teams/{team.id}/coach-report"
    await _grant(school_client, foreign_organization["id"], owner.id)
    assert school_client.get(foreign_route, params=params, headers=owner.headers).status_code == 404
    response = school_client.get(route, params=params, headers=owner.headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["readiness"]["state"] == "ready"
    assert body["sample_size"] == 5
    assert [match["played_date"] for match in body["matches"]] == [
        f"2026-04-0{day}" for day in range(2, 7)
    ]
    assert body["phase_unavailable_matches"] == 5
    assert body["observations"] == []
    assert body["batting"] is not None and body["bowling"] is not None
    assert all(game.id not in response.text for game in games)
    assert owner.id not in response.text
    for forbidden in ("striker_id", "deliveries", "ledger_digest", "metadata_revision"):
        assert forbidden not in response.text
    not_ready = school_client.get(route, params={"as_of_date": "2026-04-05"}, headers=owner.headers)
    assert not_ready.json()["readiness"]["state"] == "not_ready"
    assert not_ready.json()["matches"] == []


@pytest.mark.asyncio
async def test_report_rejects_concurrent_evidence_mismatch(
    school_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import backend.services.school_team_report_service as service

    owner = register_user(school_client, "report-mismatch@example.com")
    organization = create_school(school_client, owner, "Report mismatch")
    team = None
    for day in range(1, 6):
        team, _ = await _add_history_game(
            school_client,
            organization_id=organization["id"],
            owner_id=owner.id,
            played_date=dt.date(2026, 4, day),
            reuse_team=team,
        )
    assert team is not None
    await _grant(school_client, organization["id"], owner.id)
    request = TeamReadinessRequest(owner.id, organization["id"], team.id, dt.date(2026, 5, 1))
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        form = await calculate_team_recent_form(session, request)
        assert form.readiness.state == "ready"

    async def inconsistent_phase(*_args: object, **_kwargs: object) -> TeamPhaseResult:
        changed = replace(
            form.readiness,
            selected_sources=(replace(form.readiness.selected_sources[0], metadata_revision=999),)
            + form.readiness.selected_sources[1:],
        )
        return TeamPhaseResult(changed, 5, (), 0)

    monkeypatch.setattr(service, "calculate_team_phase_analysis", inconsistent_phase)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await compose_team_coach_report(session, request)
    assert result.readiness.state == "data_unavailable"
    assert result.form is None and result.phases is None and result.observations == ()


def test_observations_require_comparable_coverage_and_nonzero_denominators() -> None:
    from backend.services.school_team_readiness_service import TeamReadinessResult

    readiness = TeamReadinessResult(
        "org", "team", dt.date(2026, 5, 1), 5, 5, 0, "ready", 5, 5, {}, ()
    )

    def band(name: str, runs: int, balls: int, games: int, first: int = 0) -> TeamPhaseBand:
        batting = {"team_runs": runs, "legal_balls": balls}
        bowling = {"opposition_team_runs": runs, "legal_balls": balls}
        sources = frozenset(str(index) for index in range(first, first + games))
        return TeamPhaseBand(
            name,
            1,
            5,
            games,
            games,
            5 - games,
            5 - games,
            batting,
            bowling,
            games,
            games,
            sources,
            sources,
        )  # type: ignore[arg-type]

    phases = TeamPhaseResult(
        readiness,
        5,
        (band("opening", 0, 30, 5), band("middle", 12, 30, 5), band("closing", 0, 0, 5)),
        0,
    )
    observations = _observations(phases)
    assert len(observations) == 2
    assert observations[0].earlier_rate == 0
    assert observations[0].later_rate == 2.4
    assert observations[0].earlier_legal_balls == 30
    assert observations[0].observed_matches == 5
    tied = TeamPhaseResult(readiness, 5, (band("opening", 6, 12, 5), band("middle", 12, 24, 5)), 0)
    assert _observations(tied) == ()
    incomplete = TeamPhaseResult(
        readiness, 5, (band("opening", 6, 12, 4), band("middle", 12, 24, 5)), 1
    )
    assert _observations(incomplete) == ()
    different_matches = TeamPhaseResult(
        readiness, 5, (band("opening", 6, 12, 4), band("middle", 18, 24, 4, first=1)), 1
    )
    assert _observations(different_matches) == ()
    rounded_tie = TeamPhaseResult(
        readiness, 5, (band("opening", 100, 10000, 5), band("middle", 101, 10000, 5)), 0
    )
    assert _observations(rounded_tie) == ()


@pytest.mark.asyncio
async def test_report_correction_undo_and_revoked_access(school_client: TestClient) -> None:
    owner = register_user(school_client, "report-correction@example.com")
    organization = create_school(school_client, owner, "Report correction")
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
    route = f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}/coach-report"
    params = {"as_of_date": "2026-05-01"}
    original = school_client.get(route, params=params, headers=owner.headers)
    assert original.status_code == 200
    assert original.json()["readiness"]["state"] == "ready"
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        game = await session.get(Game, games[-1].id)
        assert game is not None
        original_rows = list(game.deliveries)
        game.deliveries = []
        await session.commit()
    corrected = school_client.get(route, params=params, headers=owner.headers)
    assert corrected.status_code == 200
    assert corrected.json()["readiness"]["state"] == "not_ready"
    assert corrected.json()["matches"] == []
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        game = await session.get(Game, games[-1].id)
        assert game is not None
        game.deliveries = original_rows
        await session.commit()
    undone = school_client.get(route, params=params, headers=owner.headers)
    assert undone.json()["readiness"]["state"] == "ready"
    assert undone.json()["batting"] == original.json()["batting"]
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
            reason="Report access test",
        )
        await session.commit()
    assert school_client.get(route, params=params, headers=owner.headers).status_code == 403


@pytest.mark.asyncio
async def test_report_workload_overflow_has_no_evidence(
    school_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    import backend.services.school_team_readiness_service as readiness_service

    owner = register_user(school_client, "report-overflow@example.com")
    organization = create_school(school_client, owner, "Report overflow")
    team, _ = await _add_history_game(
        school_client,
        organization_id=organization["id"],
        owner_id=owner.id,
        played_date=dt.date(2026, 4, 1),
    )
    await _grant(school_client, organization["id"], owner.id)
    monkeypatch.setattr(readiness_service, "MAX_CANDIDATE_GAMES", 0)
    response = school_client.get(
        f"/api/organizations/{organization['id']}/team-performance/teams/{team.id}/coach-report",
        params={"as_of_date": "2026-05-01"},
        headers=owner.headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["readiness"]["state"] == "data_unavailable"
    assert body["readiness"]["exclusion_counts"]["scope_too_large"] == 1
    assert body["matches"] == body["phases"] == body["observations"] == []
