from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import IntegrityError

from backend.sql_app.models import (
    Fixture,
    Organization,
    RoleEnum,
    Team,
    Tournament,
    TournamentTeam,
    User,
)
from backend.tests.school_test_helpers import RegisteredUser, create_school, register_user


async def _set_global_role(client: TestClient, user_id: str, role: RoleEnum) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        user = await session.get(User, user_id)
        assert user is not None
        user.role = role
        await session.commit()


async def _school_team(client: TestClient, organization_id: str, owner_id: str, name: str) -> Team:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        team = Team(
            id=str(uuid.uuid4()),
            name=name,
            organization_id=organization_id,
            owner_user_id=owner_id,
            status="active",
            players=[],
            competitions=[],
        )
        session.add(team)
        await session.commit()
        await session.refresh(team)
        return team


async def _school_competition_with_fixture(
    client: TestClient,
) -> tuple[dict, dict, dict, RegisteredUser]:
    owner = register_user(client, f"legacy-boundary-{uuid.uuid4().hex}@example.com")
    organization = create_school(client, owner, f"Boundary School {uuid.uuid4().hex}")
    team_a = await _school_team(client, organization["id"], owner.id, "School A")
    team_b = await _school_team(client, organization["id"], owner.id, "School B")
    competition_response = client.post(
        f"/api/organizations/{organization['id']}/competitions",
        json={"name": "Private School Cup", "tournament_type": "league"},
        headers=owner.headers,
    )
    assert competition_response.status_code == 201, competition_response.text
    competition = competition_response.json()
    for team in (team_a, team_b):
        response = client.post(
            f"/api/organizations/{organization['id']}/competitions/{competition['id']}/teams",
            json={"team_id": team.id},
            headers=owner.headers,
        )
        assert response.status_code == 201, response.text
    fixture_response = client.post(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}/fixtures",
        json={
            "team_a_id": team_a.id,
            "team_b_id": team_b.id,
            "match_number": 1,
            "venue": "School Oval",
        },
        headers=owner.headers,
    )
    assert fixture_response.status_code == 201, fixture_response.text
    return organization, competition, fixture_response.json(), owner


async def test_legacy_routes_cannot_reach_school_competition_or_fixture(
    school_client: TestClient,
) -> None:
    organization, competition, fixture, owner = await _school_competition_with_fixture(
        school_client
    )
    competition_id = competition["id"]
    fixture_id = fixture["id"]

    legacy_list = school_client.get("/tournaments/")
    assert legacy_list.status_code == 200
    assert competition_id not in {row["id"] for row in legacy_list.json()}

    assert school_client.get(f"/tournaments/{competition_id}").status_code == 404
    assert (
        school_client.patch(
            f"/tournaments/{competition_id}", json={"name": "Leaked mutation"}
        ).status_code
        == 404
    )
    assert (
        school_client.post(
            f"/tournaments/{competition_id}/teams",
            json={"team_name": "Injected", "team_data": {"private": True}},
        ).status_code
        == 404
    )
    assert school_client.get(f"/tournaments/{competition_id}/teams").status_code == 404
    assert school_client.get(f"/tournaments/{competition_id}/points-table").status_code == 404
    assert school_client.get(f"/tournaments/{competition_id}/leaderboards").status_code == 404
    assert school_client.get(f"/tournaments/{competition_id}/fixtures").status_code == 404

    assert school_client.get(f"/tournaments/fixtures/{fixture_id}").status_code == 404
    assert (
        school_client.patch(
            f"/tournaments/fixtures/{fixture_id}", json={"venue": "Leaked venue"}
        ).status_code
        == 404
    )
    assert school_client.delete(f"/tournaments/fixtures/{fixture_id}").status_code == 404

    await _set_global_role(school_client, owner.id, RoleEnum.org_pro)
    fixture_create = school_client.post(
        "/tournaments/fixtures",
        headers=owner.headers,
        json={
            "tournament_id": competition_id,
            "team_a_name": "Injected A",
            "team_b_name": "Injected B",
        },
    )
    assert fixture_create.status_code == 404
    assert school_client.delete(f"/tournaments/{competition_id}").status_code == 404

    school_competition_url = (
        f"/api/organizations/{organization['id']}/competitions/{competition_id}"
    )
    school_fixture_url = f"{school_competition_url}/fixtures/{fixture_id}"
    school_competition = school_client.get(school_competition_url, headers=owner.headers)
    assert school_competition.status_code == 200, school_competition.text
    assert school_competition.json()["name"] == "Private School Cup"
    school_fixture = school_client.get(school_fixture_url, headers=owner.headers)
    assert school_fixture.status_code == 200, school_fixture.text
    assert school_fixture.json()["venue"] == "School Oval"

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert (
            await session.scalar(
                select(func.count(TournamentTeam.id)).where(
                    TournamentTeam.tournament_id == competition_id
                )
            )
            == 2
        )
        assert (
            await session.scalar(
                select(func.count(Fixture.id)).where(Fixture.tournament_id == competition_id)
            )
            == 1
        )


async def test_null_org_legacy_tournament_operations_remain_compatible(
    school_client: TestClient,
) -> None:
    actor = register_user(school_client, f"legacy-actor-{uuid.uuid4().hex}@example.com")
    await _set_global_role(school_client, actor.id, RoleEnum.org_pro)
    created = school_client.post(
        "/tournaments/",
        headers=actor.headers,
        json={"name": "Legacy Cup", "tournament_type": "league"},
    )
    assert created.status_code == 201, created.text
    tournament_id = created.json()["id"]

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(Tournament, tournament_id)
        assert stored is not None
        assert stored.organization_id is None

    assert tournament_id in {row["id"] for row in school_client.get("/tournaments/").json()}
    assert school_client.get(f"/tournaments/{tournament_id}").status_code == 200
    updated = school_client.patch(
        f"/tournaments/{tournament_id}", json={"name": "Legacy Cup Updated"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Legacy Cup Updated"

    added = school_client.post(
        f"/tournaments/{tournament_id}/teams",
        json={"team_name": "Legacy XI", "team_data": {"players": []}},
    )
    assert added.status_code == 201, added.text
    assert [
        row["team_name"] for row in school_client.get(f"/tournaments/{tournament_id}/teams").json()
    ] == ["Legacy XI"]
    points = school_client.get(f"/tournaments/{tournament_id}/points-table")
    assert points.status_code == 200
    assert points.json()[0]["team_name"] == "Legacy XI"
    leaderboard = school_client.get(f"/tournaments/{tournament_id}/leaderboards")
    assert leaderboard.status_code == 200
    assert leaderboard.json() == {"batting": [], "bowling": []}

    fixture_created = school_client.post(
        "/tournaments/fixtures",
        headers=actor.headers,
        json={
            "tournament_id": tournament_id,
            "match_number": 1,
            "team_a_name": "Legacy XI",
            "team_b_name": "Legacy Opponent",
            "venue": "Legacy Ground",
        },
    )
    assert fixture_created.status_code == 201, fixture_created.text
    fixture_id = fixture_created.json()["id"]
    assert school_client.get(f"/tournaments/fixtures/{fixture_id}").status_code == 200
    fixture_list = school_client.get(f"/tournaments/{tournament_id}/fixtures")
    assert fixture_list.status_code == 200
    assert [row["id"] for row in fixture_list.json()] == [fixture_id]
    fixture_updated = school_client.patch(
        f"/tournaments/fixtures/{fixture_id}", json={"venue": "Updated Legacy Ground"}
    )
    assert fixture_updated.status_code == 200
    assert fixture_updated.json()["venue"] == "Updated Legacy Ground"
    assert school_client.delete(f"/tournaments/fixtures/{fixture_id}").status_code == 200
    assert school_client.delete(f"/tournaments/{tournament_id}").status_code == 200


async def test_organization_delete_cannot_convert_school_competition_to_legacy(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("PostgreSQL foreign-key enforcement assertion")

    organization, competition, _fixture, owner = await _school_competition_with_fixture(
        school_client
    )

    async with session_maker() as session:
        with pytest.raises(IntegrityError):
            await session.execute(delete(Organization).where(Organization.id == organization["id"]))
            await session.commit()
        await session.rollback()

    async with session_maker() as session:
        retained = await session.get(Tournament, competition["id"])
        assert retained is not None
        assert retained.organization_id == organization["id"]
        assert await session.get(Organization, organization["id"]) is not None

    assert school_client.get(f"/tournaments/{competition['id']}").status_code == 404
    school_read = school_client.get(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}",
        headers=owner.headers,
    )
    assert school_read.status_code == 200, school_read.text


async def test_postgres_tournament_organization_fk_is_restrict(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("PostgreSQL catalog assertion")
        row = (
            (
                await session.execute(
                    text(
                        "SELECT confdeltype::text AS confdeltype, "
                        "pg_get_constraintdef(oid) AS definition "
                        "FROM pg_constraint "
                        "WHERE conname = 'fk_tournaments_organization'"
                    )
                )
            )
            .mappings()
            .one()
        )
    assert row["confdeltype"] == "r"
    assert "ON DELETE RESTRICT" in row["definition"]
