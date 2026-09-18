from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.sql_app.models import (
    Fixture,
    Game,
    GameStatus,
    RoleEnum,
    Team,
    Tournament,
    TournamentTeam,
    User,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_school,
    register_user,
)


async def _team(client: TestClient, organization_id: str, owner_id: str, name: str) -> Team:
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


async def _game(
    client: TestClient,
    organization_id: str,
    owner_id: str,
    team_a: Team,
    team_b: Team,
    *,
    status: GameStatus = GameStatus.in_progress,
    result: str | None = None,
    publication_state: str | None = "private",
) -> Game:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        game = Game(
            id=str(uuid.uuid4()),
            team_a={
                "name": team_a.name,
                "players": [
                    {
                        "id": "profile-a",
                        "name": "Alice",
                        "student_identifier": "SECRET-A",
                        "school_player_membership_id": "membership-a",
                    }
                ],
                "school_source": {
                    "organization_id": organization_id,
                    "team_id": team_a.id,
                },
            },
            team_b={
                "name": team_b.name,
                "players": [{"id": "profile-b", "name": "Bob", "year_group": "9"}],
                "school_source": {
                    "organization_id": organization_id,
                    "team_id": team_b.id,
                },
            },
            match_type="limited",
            overs_limit=20,
            toss_winner_team=team_a.name,
            decision="bat",
            batting_team_name=team_a.name,
            bowling_team_name=team_b.name,
            status=status,
            total_runs=42,
            total_wickets=2,
            overs_completed=7,
            balls_this_over=3,
            current_inning=1,
            result=result,
            created_by_user_id=owner_id,
            publication_state=publication_state,
            batting_scorecard={
                "profile-a": {
                    "player_id": "profile-a",
                    "player_name": "Alice",
                    "runs": 30,
                    "balls_faced": 22,
                    "is_out": False,
                    "fours": 4,
                    "sixes": 1,
                    "how_out": "",
                    "student_identifier": "SECRET-A",
                }
            },
            bowling_scorecard={
                "profile-b": {
                    "player_id": "profile-b",
                    "player_name": "Bob",
                    "overs_bowled": 2.0,
                    "runs_conceded": 11,
                    "wickets_taken": 1,
                }
            },
        )
        session.add(game)
        await session.commit()
        await session.refresh(game)
        return game


def _competition(client: TestClient, owner: RegisteredUser, organization_id: str) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/competitions",
        json={"name": "Inter-House Cup", "tournament_type": "league"},
        headers=owner.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _competition_with_fixture(
    client: TestClient,
    owner: RegisteredUser,
    organization_id: str,
    team_a: Team,
    team_b: Team,
) -> tuple[dict, dict]:
    competition = _competition(client, owner, organization_id)
    for team in (team_a, team_b):
        response = client.post(
            f"/api/organizations/{organization_id}/competitions/{competition['id']}/teams",
            json={"team_id": team.id},
            headers=owner.headers,
        )
        assert response.status_code == 201, response.text
    response = client.post(
        f"/api/organizations/{organization_id}/competitions/{competition['id']}/fixtures",
        json={"team_a_id": team_a.id, "team_b_id": team_b.id, "match_number": 1},
        headers=owner.headers,
    )
    assert response.status_code == 201, response.text
    return competition, response.json()


async def test_school_competition_ownership_and_legacy_exclusion(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "competition-owner@example.com")
    organization = create_school(school_client, owner, "Competition School")
    competition = _competition(school_client, owner, organization["id"])
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        legacy = Tournament(name="Legacy Cup", organization_id=None)
        session.add(legacy)
        await session.commit()
    response = school_client.get(
        f"/api/organizations/{organization['id']}/competitions", headers=owner.headers
    )
    assert response.status_code == 200
    assert [row["id"] for row in response.json()] == [competition["id"]]
    assert competition["organization_id"] == organization["id"]


@pytest.mark.parametrize(
    ("role", "create_status"),
    [("owner", 201), ("admin", 201), ("coach", 201), ("scorer", 403), ("viewer", 403)],
)
async def test_contextual_competition_role_matrix(
    school_client: TestClient, role: str, create_status: int
) -> None:
    owner = register_user(school_client, f"matrix-{role}-owner@example.com")
    organization = create_school(school_client, owner, f"Matrix {role}")
    actor = owner
    if role != "owner":
        actor = register_user(school_client, f"matrix-{role}@example.com")
        add_membership(school_client, owner, organization["id"], actor.id, role)
    response = school_client.post(
        f"/api/organizations/{organization['id']}/competitions",
        json={"name": f"{role} Cup"},
        headers=actor.headers,
    )
    assert response.status_code == create_status, response.text
    listed = school_client.get(
        f"/api/organizations/{organization['id']}/competitions", headers=actor.headers
    )
    assert listed.status_code == 200


async def test_no_global_role_org_id_or_superuser_bypass_and_cross_tenant_404(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "tenant-owner@example.com")
    organization = create_school(school_client, owner, "Tenant A")
    competition = _competition(school_client, owner, organization["id"])
    outsider = register_user(school_client, "tenant-outsider@example.com")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        user = await session.get(User, outsider.id)
        assert user is not None
        user.role = RoleEnum.org_pro
        user.org_id = organization["id"]
        user.is_superuser = True
        await session.commit()
    response = school_client.get(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}",
        headers=outsider.headers,
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Organization not found"}


async def test_exact_team_references_duplicate_names_and_foreign_team_rejection(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "teams-owner@example.com")
    organization = create_school(school_client, owner, "Team Ref School")
    other_owner = register_user(school_client, "teams-other@example.com")
    other = create_school(school_client, other_owner, "Other School")
    same_a = await _team(school_client, organization["id"], owner.id, "Falcons")
    same_b = await _team(school_client, organization["id"], owner.id, "Falcons")
    foreign = await _team(school_client, other["id"], other_owner.id, "Falcons")
    competition, fixture = await _competition_with_fixture(
        school_client, owner, organization["id"], same_a, same_b
    )
    assert fixture["team_a_id"] == same_a.id
    assert fixture["team_b_id"] == same_b.id
    assert fixture["team_a_name"] == fixture["team_b_name"] == "Falcons"
    rejected = school_client.post(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}/teams",
        json={"team_id": foreign.id},
        headers=owner.headers,
    )
    assert rejected.status_code == 404


async def test_validated_game_linkage_rejects_foreign_wrong_and_duplicate_links(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "link-owner@example.com")
    organization = create_school(school_client, owner, "Link School")
    a = await _team(school_client, organization["id"], owner.id, "A")
    b = await _team(school_client, organization["id"], owner.id, "B")
    c = await _team(school_client, organization["id"], owner.id, "C")
    competition, fixture = await _competition_with_fixture(
        school_client, owner, organization["id"], a, b
    )
    wrong = await _game(school_client, organization["id"], owner.id, a, c)
    link_url = (
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/game"
    )
    rejected = school_client.put(link_url, json={"game_id": wrong.id}, headers=owner.headers)
    assert rejected.status_code == 404
    foreign_owner = register_user(school_client, "link-foreign-owner@example.com")
    foreign_org = create_school(school_client, foreign_owner, "Foreign Link School")
    foreign_a = await _team(school_client, foreign_org["id"], foreign_owner.id, "A")
    foreign_b = await _team(school_client, foreign_org["id"], foreign_owner.id, "B")
    foreign_game = await _game(
        school_client, foreign_org["id"], foreign_owner.id, foreign_a, foreign_b
    )
    foreign = school_client.put(link_url, json={"game_id": foreign_game.id}, headers=owner.headers)
    assert foreign.status_code == 404
    matching = await _game(school_client, organization["id"], owner.id, a, b)
    accepted = school_client.put(link_url, json={"game_id": matching.id}, headers=owner.headers)
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["game_id"] == matching.id


async def test_fixture_contextual_role_matrix(school_client: TestClient) -> None:
    owner = register_user(school_client, "fixture-matrix-owner@example.com")
    organization = create_school(school_client, owner, "Fixture Matrix School")
    a = await _team(school_client, organization["id"], owner.id, "A")
    b = await _team(school_client, organization["id"], owner.id, "B")
    competition, fixture = await _competition_with_fixture(
        school_client, owner, organization["id"], a, b
    )
    actors: dict[str, RegisteredUser] = {}
    for role in ("coach", "scorer", "viewer"):
        actor = register_user(school_client, f"fixture-matrix-{role}@example.com")
        add_membership(school_client, owner, organization["id"], actor.id, role)
        actors[role] = actor
    fixture_url = (
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}"
    )
    for actor in actors.values():
        assert school_client.get(fixture_url, headers=actor.headers).status_code == 200
    assert (
        school_client.patch(
            fixture_url, json={"venue": "School Oval"}, headers=actors["coach"].headers
        ).status_code
        == 200
    )
    assert (
        school_client.patch(
            fixture_url, json={"venue": "Denied"}, headers=actors["scorer"].headers
        ).status_code
        == 403
    )
    game = await _game(school_client, organization["id"], owner.id, a, b)
    assert (
        school_client.put(
            f"{fixture_url}/game", json={"game_id": game.id}, headers=actors["scorer"].headers
        ).status_code
        == 200
    )
    assert (
        school_client.put(
            f"{fixture_url}/game", json={"game_id": game.id}, headers=actors["viewer"].headers
        ).status_code
        == 403
    )
    assert school_client.delete(fixture_url, headers=actors["coach"].headers).status_code == 403
    assert school_client.delete(fixture_url, headers=owner.headers).status_code == 204


async def test_standings_are_rebuilt_from_completed_game_and_reflect_correction(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "standings-owner@example.com")
    organization = create_school(school_client, owner, "Standings School")
    a = await _team(school_client, organization["id"], owner.id, "Red")
    b = await _team(school_client, organization["id"], owner.id, "Blue")
    competition, fixture = await _competition_with_fixture(
        school_client, owner, organization["id"], a, b
    )
    game = await _game(
        school_client,
        organization["id"],
        owner.id,
        a,
        b,
        status=GameStatus.completed,
        result="Red won by 8 runs",
    )
    link_url = (
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/game"
    )
    assert (
        school_client.put(link_url, json={"game_id": game.id}, headers=owner.headers).status_code
        == 200
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        entrant = await session.scalar(select(TournamentTeam).where(TournamentTeam.team_id == b.id))
        assert entrant is not None
        entrant.points = 999
        entrant.matches_won = 999
        await session.commit()
    standings_url = (
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}/standings"
    )
    first = school_client.get(standings_url, headers=owner.headers)
    assert first.status_code == 200, first.text
    assert [(row["team_id"], row["points"]) for row in first.json()["entries"]] == [
        (a.id, 2),
        (b.id, 0),
    ]
    async with session_maker() as session:
        stored = await session.get(Game, game.id)
        assert stored is not None
        stored.result = "Blue won by 2 wickets"
        await session.commit()
    corrected = school_client.get(standings_url, headers=owner.headers)
    assert [(row["team_id"], row["points"]) for row in corrected.json()["entries"]] == [
        (b.id, 2),
        (a.id, 0),
    ]


async def test_private_guard_publication_roles_and_sanitized_projection(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "publish-owner@example.com")
    organization = create_school(school_client, owner, "Publish School")
    viewer = register_user(school_client, "publish-viewer@example.com")
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    a = await _team(school_client, organization["id"], owner.id, "First XI")
    b = await _team(school_client, organization["id"], owner.id, "Second XI")
    game = await _game(school_client, organization["id"], owner.id, a, b, publication_state=None)
    assert school_client.get(f"/games/{game.id}").status_code == 404
    assert school_client.get(f"/games/{game.id}/snapshot").status_code == 404
    assert school_client.get(f"/games/{game.id}", headers=owner.headers).status_code == 200
    public_url = f"/public/school-scorecards/{game.id}"
    assert school_client.get(public_url).status_code == 404
    publication_url = f"/api/organizations/{organization['id']}/matches/{game.id}/publication"
    denied = school_client.patch(
        publication_url,
        json={"publication_state": "published_live"},
        headers=viewer.headers,
    )
    assert denied.status_code == 403
    published = school_client.patch(
        publication_url,
        json={"publication_state": "published_live"},
        headers=owner.headers,
    )
    assert published.status_code == 200, published.text
    response = school_client.get(public_url)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["team_a"] == {"name": "First XI", "players": [{"name": "Alice"}]}
    serialized = str(body)
    for private_value in (
        "SECRET-A",
        "membership-a",
        "profile-a",
        "student_identifier",
        "year_group",
        "school_source",
    ):
        assert private_value not in serialized
    private = school_client.patch(
        publication_url,
        json={"publication_state": "private"},
        headers=owner.headers,
    )
    assert private.status_code == 200
    assert school_client.get(public_url).status_code == 404


async def test_publication_role_matrix_and_final_requires_completed_game(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "publish-matrix-owner@example.com")
    organization = create_school(school_client, owner, "Publication Matrix School")
    a = await _team(school_client, organization["id"], owner.id, "A")
    b = await _team(school_client, organization["id"], owner.id, "B")
    game = await _game(school_client, organization["id"], owner.id, a, b)
    url = f"/api/organizations/{organization['id']}/matches/{game.id}/publication"
    actors: dict[str, RegisteredUser] = {"owner": owner}
    for role in ("admin", "coach", "scorer", "viewer"):
        actor = register_user(school_client, f"publish-matrix-{role}@example.com")
        add_membership(school_client, owner, organization["id"], actor.id, role)
        actors[role] = actor
    for role in ("owner", "admin", "coach", "scorer"):
        response = school_client.patch(
            url,
            json={"publication_state": "published_live"},
            headers=actors[role].headers,
        )
        assert response.status_code == 200, (role, response.text)
    assert (
        school_client.patch(
            url,
            json={"publication_state": "published_live"},
            headers=actors["viewer"].headers,
        ).status_code
        == 403
    )
    not_final = school_client.patch(
        url,
        json={"publication_state": "published_final"},
        headers=owner.headers,
    )
    assert not_final.status_code == 409
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(Game, game.id)
        assert stored is not None
        stored.status = GameStatus.completed
        stored.result = "A won by 1 run"
        await session.commit()
    final = school_client.patch(
        url,
        json={"publication_state": "published_final"},
        headers=owner.headers,
    )
    assert final.status_code == 200
    assert final.json()["publication_state"] == "published_final"
    assert school_client.get(f"/public/school-scorecards/{game.id}").status_code == 200


async def test_legacy_non_school_game_remains_publicly_readable(
    school_client: TestClient,
) -> None:
    response = school_client.post(
        "/games",
        json={
            "team_a_name": "Legacy A",
            "team_b_name": "Legacy B",
            "players_a": ["A1", "A2"],
            "players_b": ["B1", "B2"],
            "match_type": "limited",
            "overs_limit": 20,
            "dls_enabled": False,
            "toss_winner_team": "Legacy A",
            "decision": "bat",
        },
    )
    assert response.status_code == 200, response.text
    game_id = response.json()["id"]
    assert school_client.get(f"/games/{game_id}").status_code == 200
    assert school_client.get(f"/games/{game_id}/snapshot").status_code == 200


async def test_one_game_cannot_back_two_authoritative_fixtures(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "duplicate-game-owner@example.com")
    organization = create_school(school_client, owner, "Duplicate Link School")
    a = await _team(school_client, organization["id"], owner.id, "A")
    b = await _team(school_client, organization["id"], owner.id, "B")
    competition, first = await _competition_with_fixture(
        school_client, owner, organization["id"], a, b
    )
    second_response = school_client.post(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}/fixtures",
        json={"team_a_id": a.id, "team_b_id": b.id, "match_number": 2},
        headers=owner.headers,
    )
    assert second_response.status_code == 201
    second = second_response.json()
    game = await _game(school_client, organization["id"], owner.id, a, b)
    base = f"/api/organizations/{organization['id']}/competitions/{competition['id']}/fixtures"
    assert (
        school_client.put(
            f"{base}/{first['id']}/game", json={"game_id": game.id}, headers=owner.headers
        ).status_code
        == 200
    )
    duplicate = school_client.put(
        f"{base}/{second['id']}/game", json={"game_id": game.id}, headers=owner.headers
    )
    assert duplicate.status_code == 409
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        assert (
            await session.scalar(select(func.count(Fixture.id)).where(Fixture.game_id == game.id))
            == 1
        )
