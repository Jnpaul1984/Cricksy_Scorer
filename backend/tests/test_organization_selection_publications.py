from __future__ import annotations

import asyncio
import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.api.schemas.organization_selection_plans import OrganizationSelectionRevisionRequest
from backend.services.organization_selection_plan_service import publish_selection_plan
from backend.sql_app.database import get_session_local
from backend.sql_app.models import (
    Game,
    OrganizationSelectionPlan,
    OrganizationSelectionPublication,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
)
from backend.tests.school_test_helpers import (
    add_membership,
    create_club,
    create_school,
    register_user,
)
from backend.tests.test_organization_selection_plans import (
    _assign,
    _create_plan,
    _fixture,
    _player,
    _team,
    _update_plan,
)


def _prepared_plan(client: TestClient, organization_type: str = "school") -> tuple:
    owner = register_user(client, f"publication-{organization_type}@example.com")
    organization = (
        create_school(client, owner, "Publication School")
        if organization_type == "school"
        else create_club(client, owner, "Publication Club")
    )
    team = _team(client, owner, organization["id"], "Publication XI")
    opponent = _team(client, owner, organization["id"], "Publication Opponent")
    players = [
        _player(client, owner, organization["id"], f"Published Player {index:02d}")
        for index in range(1, 13)
    ]
    assignments = [
        _assign(client, owner, organization["id"], team["id"], player["id"]) for player in players
    ]
    fixture = _fixture(client, owner, organization["id"], team["id"], opponent["id"])
    plan = _create_plan(client, owner, organization["id"], team["id"], fixture["id"]).json()
    update = _update_plan(
        client,
        owner,
        organization["id"],
        plan["id"],
        {
            "expected_revision": 1,
            "xi_roster_membership_ids": [player["id"] for player in players[:11]],
            "reserve_roster_membership_ids": [players[11]["id"]],
            "captain_roster_membership_id": players[0]["id"],
            "wicketkeeper_roster_membership_id": players[1]["id"],
            "batting_order_roster_membership_ids": [player["id"] for player in players[:11]],
            "bowling_plan": [
                {"roster_membership_id": players[2]["id"], "role": "primary"},
                {"roster_membership_id": players[3]["id"], "role": "secondary"},
            ],
        },
    )
    assert update.status_code == 200, update.text
    return owner, organization, team, fixture, players, assignments, update.json()


def _publish(client: TestClient, actor, organization_id: str, plan: dict):
    return client.post(
        f"/api/organizations/{organization_id}/selection-plans/{plan['id']}/publish",
        json={"expected_revision": plan["revision"]},
        headers=actor.headers,
    )


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_match_preparation_publish_version_history_and_no_match_truth_side_effects(
    school_client: TestClient,
    organization_type: str,
) -> None:
    owner, organization, _, _, players, _, plan = _prepared_plan(school_client, organization_type)
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        games_before = await session.scalar(select(func.count(Game.id)))

    first = _publish(school_client, owner, organization["id"], plan)
    assert first.status_code == 201, first.text
    version_one = first.json()
    assert version_one["publication_version"] == 1
    assert version_one["plan_revision"] == plan["revision"]
    assert version_one["published_by_user_id"] == owner.id
    assert version_one["published_at"]
    assert [
        player["roster_membership_id"]
        for player in sorted(
            (item for item in version_one["players"] if item["batting_position"] is not None),
            key=lambda item: item["batting_position"],
        )
    ] == [player["id"] for player in players[:11]]

    repeated = _publish(school_client, owner, organization["id"], plan)
    assert repeated.status_code == 201, repeated.text
    assert repeated.json()["id"] == version_one["id"]

    begin = school_client.post(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}/draft",
        json={"expected_revision": plan["revision"]},
        headers=owner.headers,
    )
    assert begin.status_code == 200, begin.text
    assert begin.json()["status"] == "draft"
    assert begin.json()["revision"] == plan["revision"] + 1
    changed = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {
            "expected_revision": begin.json()["revision"],
            "batting_order_roster_membership_ids": [player["id"] for player in players[10::-1]],
        },
    )
    assert changed.status_code == 200, changed.text
    second = _publish(school_client, owner, organization["id"], changed.json())
    assert second.status_code == 201, second.text
    assert second.json()["publication_version"] == 2

    history = school_client.get(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}/publications",
        headers=owner.headers,
    )
    assert history.status_code == 200, history.text
    assert [item["publication_version"] for item in history.json()] == [2, 1]
    retained_one = school_client.get(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}" "/publications/1",
        headers=owner.headers,
    )
    assert retained_one.status_code == 200
    assert retained_one.json() == version_one

    async with session_maker() as session:
        assert await session.scalar(select(func.count(Game.id))) == games_before


async def test_publish_validation_roles_advisory_availability_and_retained_identity(
    school_client: TestClient,
) -> None:
    owner, organization, team, fixture, players, assignments, plan = _prepared_plan(school_client)
    scorer = register_user(school_client, "publication-scorer@example.com")
    viewer = register_user(school_client, "publication-viewer@example.com")
    add_membership(school_client, owner, organization["id"], scorer.id, "scorer")
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    for player, state in zip(players[:3], ("unavailable", "maybe", "available"), strict=True):
        response = school_client.put(
            f"/api/organizations/{organization['id']}/availability/fixture/{fixture['id']}"
            f"/players/{player['id']}",
            json={"state": state},
            headers=owner.headers,
        )
        assert response.status_code == 200, response.text
    for actor in (scorer, viewer):
        denied = _publish(school_client, actor, organization["id"], plan)
        assert denied.status_code == 403
    published = _publish(school_client, owner, organization["id"], plan)
    assert published.status_code == 201, published.text
    for actor in (scorer, viewer):
        history = school_client.get(
            f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}/publications",
            headers=actor.headers,
        )
        assert history.status_code == 200

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        membership = await session.get(SchoolPlayerMembership, players[0]["id"])
        assert membership is not None
        membership.status = "inactive"
        team_membership = await session.get(SchoolTeamPlayerMembership, assignments[1]["id"])
        assert team_membership is not None
        team_membership.status = "inactive"
        await session.commit()
    retained = school_client.get(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}/publications/1",
        headers=viewer.headers,
    )
    assert retained.status_code == 200
    assert {item["player_name"] for item in retained.json()["players"]} >= {
        "Published Player 01",
        "Published Player 02",
    }


async def test_publish_revalidates_inactive_player_and_requires_complete_contract(
    school_client: TestClient,
) -> None:
    owner, organization, _, _, players, assignments, plan = _prepared_plan(school_client)
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        membership = await session.get(SchoolTeamPlayerMembership, assignments[0]["id"])
        assert membership is not None
        membership.status = "inactive"
        await session.commit()
    rejected = _publish(school_client, owner, organization["id"], plan)
    assert rejected.status_code == 422

    async with session_maker() as session:
        membership = await session.get(SchoolTeamPlayerMembership, assignments[0]["id"])
        assert membership is not None
        membership.status = "active"
        await session.commit()
    begin = _update_plan(
        school_client,
        owner,
        organization["id"],
        plan["id"],
        {
            "expected_revision": plan["revision"],
            "xi_roster_membership_ids": [p["id"] for p in players[:10]],
            "batting_order_roster_membership_ids": [p["id"] for p in players[:10]],
        },
    )
    assert begin.status_code == 200
    exact_eleven = _publish(school_client, owner, organization["id"], begin.json())
    assert exact_eleven.status_code == 422


async def test_published_history_blocks_fixture_and_competition_deletion(
    school_client: TestClient,
) -> None:
    owner, organization, _, fixture, _, _, plan = _prepared_plan(school_client)
    assert _publish(school_client, owner, organization["id"], plan).status_code == 201
    fixture_url = (
        f"/api/organizations/{organization['id']}/competitions/{fixture['tournament_id']}"
        f"/fixtures/{fixture['id']}"
    )
    fixture_delete = school_client.delete(fixture_url, headers=owner.headers)
    assert fixture_delete.status_code == 409
    competition_delete = school_client.delete(
        f"/api/organizations/{organization['id']}/competitions/{fixture['tournament_id']}",
        headers=owner.headers,
    )
    assert competition_delete.status_code == 409
    history = school_client.get(
        f"/api/organizations/{organization['id']}/selection-plans/{plan['id']}/publications/1",
        headers=owner.headers,
    )
    assert history.status_code == 200


@pytest.mark.skipif(
    os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="Publication concurrency requires real PostgreSQL",
)
async def test_postgres_concurrent_publish_is_one_idempotent_version(
    school_client: TestClient,
) -> None:
    owner, organization, _, _, _, _, plan = _prepared_plan(school_client)
    session_maker = get_session_local()
    start = asyncio.Event()

    async def publish_once():
        async with session_maker() as session:
            await start.wait()
            return await publish_selection_plan(
                session,
                organization_id=organization["id"],
                plan_id=plan["id"],
                actor_user_id=owner.id,
                payload=OrganizationSelectionRevisionRequest(expected_revision=plan["revision"]),
            )

    tasks = [asyncio.create_task(publish_once()) for _ in range(2)]
    start.set()
    results = await asyncio.gather(*tasks)
    assert results[0].id == results[1].id
    assert results[0].publication_version == results[1].publication_version == 1
    async with session_maker() as session:
        assert (
            await session.scalar(
                select(func.count(OrganizationSelectionPublication.id)).where(
                    OrganizationSelectionPublication.selection_plan_id == plan["id"]
                )
            )
            == 1
        )
        root = await session.get(OrganizationSelectionPlan, plan["id"])
        assert root is not None and root.status == "published"
