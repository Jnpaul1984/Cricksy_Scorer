from __future__ import annotations

import asyncio
import datetime as dt
import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from structlog.testing import capture_logs

from backend.services import school_competition_service
from backend.sql_app.models import (
    Fixture,
    Game,
    GameStatus,
    Organization,
    OrganizationCompetitionPublication,
    OrganizationEntitlement,
    OrganizationPublicSettings,
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


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("owner", 200), ("admin", 200), ("coach", 403), ("scorer", 403), ("viewer", 403)],
)
async def test_youtube_video_edits_use_owner_admin_publication_authority(
    school_client: TestClient, role: str, expected_status: int
) -> None:
    owner = register_user(school_client, f"youtube-{role}-owner@example.com")
    organization = create_school(school_client, owner, f"YouTube {role} School")
    actor = owner
    if role != "owner":
        actor = register_user(school_client, f"youtube-{role}@example.com")
        add_membership(school_client, owner, organization["id"], actor.id, role)
    team_a = await _team(school_client, organization["id"], owner.id, "Synthetic Adult XI")
    team_b = await _team(school_client, organization["id"], owner.id, "Practice Adults")
    competition, fixture = await _competition_with_fixture(
        school_client, owner, organization["id"], team_a, team_b
    )
    game = await _game(school_client, organization["id"], owner.id, team_a, team_b)
    link = school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/game",
        json={"game_id": game.id},
        headers=owner.headers,
    )
    assert link.status_code == 200, link.text

    path = (
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/youtube-video"
    )
    attached = school_client.put(
        path,
        json={"youtube_url": "https://youtu.be/AbCdEf123_-?si=synthetic"},
        headers=actor.headers,
    )
    assert attached.status_code == expected_status
    if expected_status == 200:
        assert attached.json()["youtube_video_id"] == "AbCdEf123_-"
        assert attached.json()["updated_by_user_id"] == actor.id
        assert attached.json()["updated_at"]
        assert school_client.get(path, headers=actor.headers).json()["youtube_video_id"] == "AbCdEf123_-"
        assert school_client.put(
            path,
            json={"youtube_url": "<iframe src='https://youtube.com/embed/AbCdEf123_-'></iframe>"},
            headers=actor.headers,
        ).status_code == 422
        assert school_client.put(path, json={}, headers=actor.headers).status_code == 422
        assert school_client.get(path, headers=actor.headers).json()["youtube_video_id"] == "AbCdEf123_-"
    else:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            persisted = await session.get(Fixture, fixture["id"])
            assert persisted is not None and persisted.youtube_video_id is None


async def test_youtube_video_edit_fails_closed_for_nonmembers_wrong_tenant_and_removed_members(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "youtube-scope-owner@example.com")
    outsider = register_user(school_client, "youtube-scope-outsider@example.com")
    admin = register_user(school_client, "youtube-scope-admin@example.com")
    organization = create_school(school_client, owner, "YouTube Scope School")
    other_organization = create_school(school_client, owner, "Other YouTube Scope School")
    membership = add_membership(school_client, owner, organization["id"], admin.id, "admin")
    team_a = await _team(school_client, organization["id"], owner.id, "Scope A")
    team_b = await _team(school_client, organization["id"], owner.id, "Scope B")
    competition, fixture = await _competition_with_fixture(
        school_client, owner, organization["id"], team_a, team_b
    )
    game = await _game(school_client, organization["id"], owner.id, team_a, team_b)
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/game",
        json={"game_id": game.id},
        headers=owner.headers,
    ).status_code == 200
    path = (
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/youtube-video"
    )
    payload = {"youtube_url": "https://youtu.be/AbCdEf123_-"}
    assert school_client.put(path, json=payload, headers=outsider.headers).status_code == 404
    assert school_client.put(
        f"/api/organizations/{other_organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/youtube-video",
        json=payload,
        headers=owner.headers,
    ).status_code == 404

    disabled = school_client.patch(
        f"/api/organizations/{organization['id']}/memberships/{membership['id']}",
        json={"status": "disabled"},
        headers=owner.headers,
    )
    assert disabled.status_code == 200
    assert school_client.put(path, json=payload, headers=admin.headers).status_code == 404


@pytest.mark.parametrize("entitlement_state", ["expired", "missing"])
async def test_youtube_video_edit_requires_effective_scorecard_entitlement(
    school_client: TestClient, entitlement_state: str
) -> None:
    owner = register_user(school_client, f"youtube-entitlement-{entitlement_state}@example.com")
    organization = create_school(school_client, owner, f"YouTube {entitlement_state} School")
    team_a = await _team(school_client, organization["id"], owner.id, "Entitlement A")
    team_b = await _team(school_client, organization["id"], owner.id, "Entitlement B")
    competition, fixture = await _competition_with_fixture(
        school_client, owner, organization["id"], team_a, team_b
    )
    game = await _game(school_client, organization["id"], owner.id, team_a, team_b)
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/game",
        json={"game_id": game.id},
        headers=owner.headers,
    ).status_code == 200
    path = (
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/youtube-video"
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        if entitlement_state == "missing":
            assert entitlement is not None
            await session.delete(entitlement)
        else:
            assert entitlement is not None
            entitlement.effective_until = dt.datetime.now(dt.UTC) - dt.timedelta(days=1)
        await session.commit()
    response = school_client.put(
        path,
        json={"youtube_url": "https://youtu.be/AbCdEf123_-"},
        headers=owner.headers,
    )
    assert response.status_code == 403


async def test_youtube_video_requires_active_organization_and_exact_match_linkage(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "youtube-linkage-owner@example.com")
    organization = create_school(school_client, owner, "YouTube Linkage School")
    team_a = await _team(school_client, organization["id"], owner.id, "Linkage A")
    team_b = await _team(school_client, organization["id"], owner.id, "Linkage B")
    team_c = await _team(school_client, organization["id"], owner.id, "Linkage C")
    competition, fixture = await _competition_with_fixture(
        school_client, owner, organization["id"], team_a, team_b
    )
    game = await _game(school_client, organization["id"], owner.id, team_a, team_b)
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/game",
        json={"game_id": game.id},
        headers=owner.headers,
    ).status_code == 200
    path = (
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/youtube-video"
    )
    payload = {"youtube_url": "https://youtu.be/AbCdEf123_-"}
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        persisted_game = await session.get(Game, game.id)
        assert persisted_game is not None
        persisted_game.team_a = {
            **persisted_game.team_a,
            "school_source": {"organization_id": organization["id"], "team_id": team_c.id},
        }
        await session.commit()
    assert school_client.put(path, json=payload, headers=owner.headers).status_code == 404
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        organization_row = await session.get(Organization, organization["id"])
        assert organization_row is not None
        organization_row.status = "suspended"
        await session.commit()
    assert school_client.put(path, json=payload, headers=owner.headers).status_code == 404


async def test_youtube_video_is_only_projected_by_canonical_published_scorecard(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "youtube-public-owner@example.com")
    organization = create_school(school_client, owner, "YouTube Public School")
    team_a = await _team(school_client, organization["id"], owner.id, "Synthetic Adult XI")
    team_b = await _team(school_client, organization["id"], owner.id, "Practice Adults")
    competition, fixture = await _competition_with_fixture(
        school_client, owner, organization["id"], team_a, team_b
    )
    game = await _game(school_client, organization["id"], owner.id, team_a, team_b)
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/game",
        json={"game_id": game.id},
        headers=owner.headers,
    ).status_code == 200
    editor_path = (
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/youtube-video"
    )
    attached = school_client.put(
        editor_path,
        json={"youtube_url": "https://www.youtube.com/watch?v=AbCdEf123_-&list=synthetic"},
        headers=owner.headers,
    )
    assert attached.status_code == 200, attached.text
    assert attached.json()["youtube_video_id"] == "AbCdEf123_-"

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        before_game = await session.get(Game, game.id)
        public_settings = await session.get(OrganizationPublicSettings, organization["id"])
        competition_settings = await session.get(
            OrganizationCompetitionPublication, competition["id"]
        )
        assert before_game is not None and before_game.publication_state == "private"
        assert before_game.total_runs == 42
        assert public_settings is not None and public_settings.publication_state == "unpublished"
        assert competition_settings is not None and competition_settings.publication_state == "unpublished"
    org_publication = school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish",
        headers=owner.headers,
    )
    competition_publication = school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        "/community-publication/publish",
        headers=owner.headers,
    )
    assert org_publication.status_code == competition_publication.status_code == 200
    scorecard_publication = school_client.patch(
        f"/api/organizations/{organization['id']}/matches/{game.id}/publication",
        json={"publication_state": "published_live"},
        headers=owner.headers,
    )
    assert scorecard_publication.status_code == 200, scorecard_publication.text

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        public_settings = await session.get(OrganizationPublicSettings, organization["id"])
        competition_settings = await session.get(OrganizationCompetitionPublication, competition["id"])
        fixture_row = await session.get(Fixture, fixture["id"])
        assert public_settings is not None and competition_settings is not None and fixture_row is not None
        public_identifier = public_settings.public_identifier
        competition_key = competition_settings.public_key
        fixture_public_identifier = fixture_row.public_identifier
    canonical_path = (
        f"/api/public/organizations/{public_identifier}/competitions/{competition_key}"
        f"/scorecards/{game.public_scorecard_identifier}"
    )
    public_scorecard = school_client.get(canonical_path)
    assert public_scorecard.status_code == 200, public_scorecard.text
    assert public_scorecard.json()["youtube_video_id"] == "AbCdEf123_-"
    assert game.id not in public_scorecard.text

    public_fixture = school_client.get(
        f"/api/public/organizations/{public_identifier}/competitions/{competition_key}"
        f"/fixtures/{fixture_public_identifier}"
    )
    assert public_fixture.status_code == 200
    assert "youtube_video_id" not in public_fixture.json()
    legacy_scorecard = school_client.get(f"/public/school-scorecards/{game.id}")
    assert legacy_scorecard.status_code == 200
    assert "youtube_video_id" not in legacy_scorecard.json()

    replaced = school_client.put(
        editor_path,
        json={"youtube_url": "https://youtube.com/live/ZyXwVu987_-"},
        headers=owner.headers,
    )
    assert replaced.status_code == 200
    assert school_client.get(canonical_path).json()["youtube_video_id"] == "ZyXwVu987_-"
    removed = school_client.put(editor_path, json={"youtube_url": None}, headers=owner.headers)
    assert removed.status_code == 200
    assert removed.json()["youtube_video_id"] is None
    assert school_client.get(canonical_path).json()["youtube_video_id"] is None

    attached = school_client.put(
        editor_path,
        json={"youtube_url": "https://youtu.be/AbCdEf123_-"},
        headers=owner.headers,
    )
    assert attached.status_code == 200
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        "/community-publication/unpublish",
        headers=owner.headers,
    ).status_code == 200
    assert school_client.get(canonical_path).status_code == 404
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        "/community-publication/publish",
        headers=owner.headers,
    ).status_code == 200
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        "/community-publication/publish",
        headers=owner.headers,
    ).status_code == 200
    assert school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/unpublish",
        headers=owner.headers,
    ).status_code == 200
    assert school_client.get(canonical_path).status_code == 404
    assert school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish",
        headers=owner.headers,
    ).status_code == 200
    assert school_client.patch(
        f"/api/organizations/{organization['id']}/matches/{game.id}/publication",
        json={"publication_state": "private"},
        headers=owner.headers,
    ).status_code == 200
    assert school_client.get(canonical_path).status_code == 404
    assert school_client.patch(
        f"/api/organizations/{organization['id']}/matches/{game.id}/publication",
        json={"publication_state": "published_live"},
        headers=owner.headers,
    ).status_code == 200
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        assert entitlement is not None
        entitlement.status = "disabled"
        await session.commit()
    assert school_client.get(canonical_path).status_code == 404


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
    # The repository's CRICKSY_IN_MEMORY_DB mode monkey-patches legacy game CRUD
    # with a separate in-memory store, so DB-seeded Games are intentionally absent
    # from generic routes in that mode. PostgreSQL exercises the real persistence path.
    if os.getenv("CRICKSY_IN_MEMORY_DB") != "1":
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


async def test_publication_changes_and_role_denials_emit_safe_operational_events(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "publish-audit-owner@example.com")
    organization = create_school(school_client, owner, "Publication Audit School")
    viewer = register_user(school_client, "publish-audit-viewer@example.com")
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    team_a = await _team(school_client, organization["id"], owner.id, "Audit A")
    team_b = await _team(school_client, organization["id"], owner.id, "Audit B")
    game = await _game(school_client, organization["id"], owner.id, team_a, team_b)
    url = f"/api/organizations/{organization['id']}/matches/{game.id}/publication"

    with capture_logs() as logs:
        denied = school_client.patch(
            url,
            json={"publication_state": "published_live"},
            headers=viewer.headers,
        )
        changed = school_client.patch(
            url,
            json={"publication_state": "published_live"},
            headers=owner.headers,
        )

    assert denied.status_code == 403
    assert changed.status_code == 200
    assert {
        "event": "organization.school_competition_authorization_denied",
        "organization_id": organization["id"],
        "actor_user_id": viewer.id,
        "membership_role": "viewer",
        "capability": "school_live_scorecards",
        "log_level": "warning",
    } in logs
    assert {
        "event": "organization.school_match_publication_changed",
        "organization_id": organization["id"],
        "game_id": game.id,
        "actor_user_id": owner.id,
        "previous_state": "private",
        "publication_state": "published_live",
        "log_level": "info",
    } in logs


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


async def test_concurrent_fixture_game_links_have_one_controlled_loser_on_postgresql(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("Fixture linkage concurrency requires real PostgreSQL")

    owner = register_user(school_client, "concurrent-link-owner@example.com")
    organization = create_school(school_client, owner, "Concurrent Link School")
    a = await _team(school_client, organization["id"], owner.id, "Concurrent A")
    b = await _team(school_client, organization["id"], owner.id, "Concurrent B")
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

    async def link(fixture_id: str) -> Fixture | Exception:
        async with session_maker() as session:
            try:
                return await school_competition_service.link_fixture_game(
                    session,
                    organization_id=organization["id"],
                    actor_user_id=owner.id,
                    competition_id=competition["id"],
                    fixture_id=fixture_id,
                    game_id=game.id,
                )
            except Exception as exc:
                return exc

    outcomes = await asyncio.gather(link(first["id"]), link(second["id"]))
    winners = [outcome for outcome in outcomes if isinstance(outcome, Fixture)]
    losers = [
        outcome
        for outcome in outcomes
        if isinstance(outcome, school_competition_service.SchoolCompetitionServiceError)
    ]
    assert len(winners) == 1
    assert len(losers) == 1
    assert losers[0].status_code == 409
    assert losers[0].detail == "Game is already linked to a fixture"

    async with session_maker() as session:
        assert (
            await session.scalar(select(func.count(Fixture.id)).where(Fixture.game_id == game.id))
            == 1
        )
