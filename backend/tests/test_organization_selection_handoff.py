from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.api.schemas.school_matches import SchoolMatchCreate
from backend.services import organization_selection_plan_service, school_match_service
from backend.sql_app.database import get_session_local
from backend.sql_app.models import (
    Fixture,
    Game,
    GameStatus,
    OrganizationSelectionPublication,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
)
from backend.tests.school_test_helpers import add_membership, register_user
from backend.tests.test_organization_selection_plans import _assign, _player
from backend.tests.test_organization_selection_publications import _prepared_plan, _publish


def _handoff_url(organization_id: str, plan_id: str, version: int = 1) -> str:
    return (
        f"/api/organizations/{organization_id}/selection-plans/{plan_id}"
        f"/publications/{version}/handoff"
    )


def _opponent_selection(
    client: TestClient,
    owner,
    organization_id: str,
    team_id: str,
    suffix: str,
) -> dict:
    roster_players = [
        _player(client, owner, organization_id, f"Handoff Opponent {suffix} {index:02d}")
        for index in range(1, 12)
    ]
    assignments = [
        _assign(client, owner, organization_id, team_id, player["id"]) for player in roster_players
    ]
    return {
        "team_id": team_id,
        "playing_xi_membership_ids": [assignment["id"] for assignment in assignments],
        "captain_membership_id": assignments[0]["id"],
        "wicketkeeper_membership_id": assignments[1]["id"],
    }


def _match_payload(handoff: dict, opponent: dict) -> dict:
    selected = handoff["selected_team"]
    return {
        "mode": "school_vs_school",
        "school_side": None,
        "team_a": selected if handoff["selected_side"] == "team_a" else opponent,
        "team_b": opponent if handoff["selected_side"] == "team_a" else selected,
        "external_opponent": None,
        "selection_handoff": {
            "selection_plan_id": handoff["selection_plan_id"],
            "publication_version": handoff["publication_version"],
            "fixture_id": handoff["fixture_id"],
        },
        "match_type": "limited",
        "overs_limit": 40,
        "days_limit": None,
        "overs_per_day": None,
        "dls_enabled": False,
        "toss_winner_side": "team_b",
        "decision": "bowl",
    }


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_published_selection_handoff_revalidates_and_prefills_existing_match_contract(
    school_client: TestClient,
    organization_type: str,
) -> None:
    owner, organization, team, fixture, _, assignments, plan = _prepared_plan(
        school_client, organization_type
    )
    publication = _publish(school_client, owner, organization["id"], plan)
    assert publication.status_code == 201, publication.text

    prepared = school_client.post(
        _handoff_url(organization["id"], plan["id"]), headers=owner.headers
    )
    assert prepared.status_code == 200, prepared.text
    body = prepared.json()
    assert body["publication_version"] == 1
    assert body["fixture_id"] == fixture["id"]
    assert body["selected_side"] == "team_a"
    assert body["selected_team"]["team_id"] == team["id"]
    assert set(body["selected_team"]["playing_xi_membership_ids"]) == {
        assignment["id"] for assignment in assignments[:11]
    }
    assert body["selected_team"]["captain_membership_id"] == assignments[0]["id"]
    assert body["selected_team"]["wicketkeeper_membership_id"] == assignments[1]["id"]
    assert len(body["planned_batting_order_membership_ids"]) == 11


async def test_draft_roles_tenant_scope_and_exact_publication_version(
    school_client: TestClient,
) -> None:
    owner, organization, _, _, _, _, plan = _prepared_plan(school_client)
    scorer = register_user(school_client, "handoff-scorer@example.com")
    viewer = register_user(school_client, "handoff-viewer@example.com")
    admin = register_user(school_client, "handoff-admin@example.com")
    coach = register_user(school_client, "handoff-coach@example.com")
    add_membership(school_client, owner, organization["id"], scorer.id, "scorer")
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    add_membership(school_client, owner, organization["id"], admin.id, "admin")
    add_membership(school_client, owner, organization["id"], coach.id, "coach")

    missing = school_client.post(
        _handoff_url(organization["id"], plan["id"]), headers=owner.headers
    )
    assert missing.status_code == 404
    assert _publish(school_client, owner, organization["id"], plan).status_code == 201
    for actor in (owner, admin, coach):
        allowed = school_client.post(
            _handoff_url(organization["id"], plan["id"]), headers=actor.headers
        )
        assert allowed.status_code == 200, allowed.text
        assert allowed.json()["publication_version"] == 1
    for actor in (scorer, viewer):
        denied = school_client.post(
            _handoff_url(organization["id"], plan["id"]), headers=actor.headers
        )
        assert denied.status_code == 403

    absent_version = school_client.post(
        _handoff_url(organization["id"], plan["id"], 2), headers=owner.headers
    )
    assert absent_version.status_code == 404
    outsider = register_user(school_client, "handoff-outsider@example.com")
    hidden = school_client.post(
        _handoff_url(organization["id"], plan["id"]), headers=outsider.headers
    )
    assert hidden.status_code == 404


@pytest.mark.parametrize("inactive_layer", ["master", "team"])
async def test_handoff_rejects_currently_inactive_published_player_without_mutating_history(
    school_client: TestClient,
    inactive_layer: str,
) -> None:
    owner, organization, _, _, players, assignments, plan = _prepared_plan(school_client)
    publication = _publish(school_client, owner, organization["id"], plan)
    assert publication.status_code == 201
    retained = publication.json()
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if inactive_layer == "master":
            membership = await session.get(SchoolPlayerMembership, players[0]["id"])
        else:
            membership = await session.get(SchoolTeamPlayerMembership, assignments[0]["id"])
        assert membership is not None
        membership.status = "inactive"
        await session.commit()

    rejected = school_client.post(
        _handoff_url(organization["id"], plan["id"]), headers=owner.headers
    )
    assert rejected.status_code == 422
    unchanged = school_client.get(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}" "/publications/1",
        headers=owner.headers,
    )
    assert unchanged.status_code == 200
    assert unchanged.json() == retained


async def test_stale_and_linked_fixture_return_controlled_conflicts(
    school_client: TestClient,
) -> None:
    owner, organization, _, fixture, _, _, plan = _prepared_plan(school_client)
    assert _publish(school_client, owner, organization["id"], plan).status_code == 201
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        row = await session.get(Fixture, fixture["id"])
        assert row is not None
        row.status = "cancelled"
        await session.commit()
    stale = school_client.post(_handoff_url(organization["id"], plan["id"]), headers=owner.headers)
    assert stale.status_code == 409

    async with session_maker() as session:
        row = await session.get(Fixture, fixture["id"])
        assert row is not None
        row.status = "scheduled"
        row.game_id = await session.scalar(select(Game.id).limit(1))
        if row.game_id is None:
            game = Game(id="handoff-existing-game", team_a={}, team_b={})
            session.add(game)
            await session.flush()
            row.game_id = game.id
        await session.commit()
    linked = school_client.post(_handoff_url(organization["id"], plan["id"]), headers=owner.headers)
    assert linked.status_code == 409
    assert "already has a linked Game" in linked.json()["detail"]


@pytest.mark.parametrize(
    "game_status",
    [GameStatus.started, GameStatus.in_progress, GameStatus.completed],
)
async def test_handoff_never_rewrites_started_in_progress_or_completed_game(
    school_client: TestClient,
    game_status: GameStatus,
) -> None:
    owner, organization, _, fixture, _, _, plan = _prepared_plan(school_client)
    assert _publish(school_client, owner, organization["id"], plan).status_code == 201
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        game = Game(
            id=f"retained-{game_status.value}",
            team_a={"playing_xi": ["historical-player"]},
            team_b={"playing_xi": []},
            status=game_status,
        )
        session.add(game)
        await session.flush()
        row = await session.get(Fixture, fixture["id"])
        assert row is not None
        row.game_id = game.id
        await session.commit()

    rejected = school_client.post(
        _handoff_url(organization["id"], plan["id"]), headers=owner.headers
    )
    assert rejected.status_code == 409
    async with session_maker() as session:
        game = await session.get(Game, f"retained-{game_status.value}")
        assert game is not None
        assert game.status == game_status
        assert game.team_a["playing_xi"] == ["historical-player"]


async def test_final_match_creation_links_fixture_once_and_preserves_match_truth_boundaries(
    school_client: TestClient,
) -> None:
    owner, organization, _, fixture, _, _, plan = _prepared_plan(school_client)
    publication = _publish(school_client, owner, organization["id"], plan)
    assert publication.status_code == 201
    retained = publication.json()
    prepared = school_client.post(
        _handoff_url(organization["id"], plan["id"]), headers=owner.headers
    ).json()
    opponent = _opponent_selection(
        school_client,
        owner,
        organization["id"],
        prepared["fixture_team_b_id"],
        "final",
    )
    payload = _match_payload(prepared, opponent)
    created = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=payload,
        headers=owner.headers,
    )
    assert created.status_code == 201, created.text
    game_id = created.json()["game_id"]

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        linked = await session.get(Fixture, fixture["id"])
        game = await session.get(Game, game_id)
        assert linked is not None and linked.game_id == game_id
        assert game is not None
        assert game.status == GameStatus.innings_break
        assert game.current_inning == 0
        assert game.deliveries == []
        assert game.dls_enabled is False
        original_xi = list(game.team_a["playing_xi"])

    retry = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=payload,
        headers=owner.headers,
    )
    assert retry.status_code == 409
    async with session_maker() as session:
        assert await session.scalar(select(func.count(Game.id))) == 1
        game = await session.get(Game, game_id)
        assert game is not None and game.team_a["playing_xi"] == original_xi
    history = school_client.get(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}" "/publications/1",
        headers=owner.headers,
    )
    assert history.json() == retained


async def test_handoff_payload_cannot_change_published_xi_or_fixture(
    school_client: TestClient,
) -> None:
    owner, organization, _, _, _, _, plan = _prepared_plan(school_client)
    assert _publish(school_client, owner, organization["id"], plan).status_code == 201
    prepared = school_client.post(
        _handoff_url(organization["id"], plan["id"]), headers=owner.headers
    ).json()
    opponent = _opponent_selection(
        school_client,
        owner,
        organization["id"],
        prepared["fixture_team_b_id"],
        "tamper",
    )
    payload = _match_payload(prepared, opponent)
    payload["team_a"]["captain_membership_id"] = payload["team_a"]["wicketkeeper_membership_id"]
    rejected = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=payload,
        headers=owner.headers,
    )
    assert rejected.status_code == 422
    payload = _match_payload(prepared, opponent)
    payload["selection_handoff"]["fixture_id"] = "foreign-fixture"
    rejected_fixture = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=payload,
        headers=owner.headers,
    )
    assert rejected_fixture.status_code == 422


def test_external_opponent_contract_rejects_selection_binding_without_creating_fake_identity() -> (
    None
):
    with pytest.raises(ValueError):
        SchoolMatchCreate.model_validate(
            {
                "mode": "school_vs_external",
                "school_side": "team_a",
                "team_a": {
                    "team_id": "school-team",
                    "playing_xi_membership_ids": [f"member-{index}" for index in range(11)],
                    "captain_membership_id": "member-0",
                    "wicketkeeper_membership_id": "member-1",
                },
                "team_b": None,
                "external_opponent": {
                    "team_name": "External XI",
                    "player_names": [f"External {index}" for index in range(11)],
                    "captain_index": 0,
                    "wicketkeeper_index": 1,
                },
                "selection_handoff": {
                    "selection_plan_id": "plan",
                    "publication_version": 1,
                    "fixture_id": "fixture",
                },
                "toss_winner_side": "team_a",
                "decision": "bat",
            }
        )


@pytest.mark.skipif(
    os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="Handoff concurrency requires real PostgreSQL",
)
async def test_postgres_concurrent_handoff_creates_and_links_only_one_game(
    school_client: TestClient,
) -> None:
    owner, organization, _, fixture, _, _, plan = _prepared_plan(school_client)
    assert _publish(school_client, owner, organization["id"], plan).status_code == 201
    prepared = school_client.post(
        _handoff_url(organization["id"], plan["id"]), headers=owner.headers
    ).json()
    opponent = _opponent_selection(
        school_client,
        owner,
        organization["id"],
        prepared["fixture_team_b_id"],
        "concurrent",
    )
    payload = SchoolMatchCreate.model_validate(_match_payload(prepared, opponent))
    session_maker = get_session_local()
    start = asyncio.Event()

    async def create_once():
        async with session_maker() as session:
            await start.wait()
            try:
                game = await school_match_service.create_school_match(
                    session,
                    organization_id=organization["id"],
                    payload=payload,
                    actor_user_id=owner.id,
                )
                return ("created", game.id, await session.scalar(select(func.count(Game.id))))
            except organization_selection_plan_service.OrganizationSelectionPlanServiceError as exc:
                return (
                    "conflict",
                    exc.status_code,
                    await session.scalar(select(func.count(Game.id))),
                )

    tasks = [asyncio.create_task(create_once()) for _ in range(2)]
    start.set()
    results = await asyncio.gather(*tasks)
    assert sorted(result[0] for result in results) == ["conflict", "created"]
    assert next(result for result in results if result[0] == "conflict")[1] == 409
    async with session_maker() as session:
        linked = await session.get(Fixture, fixture["id"])
        assert linked is not None and linked.game_id is not None
        assert await session.scalar(select(func.count(Game.id))) == 1
        assert await session.scalar(select(func.count(OrganizationSelectionPublication.id))) == 1
