from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.services import organization_entitlement_service
from backend.sql_app.models import (
    Game,
    GameStatus,
    OrganizationEntitlement,
    PlayerProfile,
    RoleEnum,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
    User,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_school,
    register_user,
)


@dataclass(frozen=True)
class SeededTeam:
    id: str
    membership_ids: tuple[str, ...]
    profile_ids: tuple[str, ...]


async def _seed_team(
    client: TestClient,
    *,
    organization_id: str,
    owner_user_id: str,
    name: str,
    shared_player: tuple[str, str] | None = None,
) -> SeededTeam:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        team = Team(
            id=str(uuid.uuid4()),
            name=name,
            organization_id=organization_id,
            status="active",
            owner_user_id=owner_user_id,
            players=[{"id": "legacy-only", "name": "Legacy JSON must remain untouched"}],
            competitions=[],
        )
        session.add(team)
        await session.flush()
        memberships: list[str] = []
        profiles: list[str] = []
        team_memberships: list[SchoolTeamPlayerMembership] = []
        for index in range(11):
            if index == 0 and shared_player is not None:
                profile_id, school_membership_id = shared_player
            else:
                profile_id = str(uuid.uuid4())
                school_membership_id = str(uuid.uuid4())
                session.add(
                    PlayerProfile(player_id=profile_id, player_name=f"{name} Player {index + 1}")
                )
                session.add(
                    SchoolPlayerMembership(
                        id=school_membership_id,
                        organization_id=organization_id,
                        player_profile_id=profile_id,
                        status="active",
                        created_by_user_id=owner_user_id,
                    )
                )
            team_membership_id = str(uuid.uuid4())
            team_memberships.append(
                SchoolTeamPlayerMembership(
                    id=team_membership_id,
                    organization_id=organization_id,
                    team_id=team.id,
                    school_player_membership_id=school_membership_id,
                    status="active",
                    created_by_user_id=owner_user_id,
                )
            )
            memberships.append(team_membership_id)
            profiles.append(profile_id)
        await session.flush()
        session.add_all(team_memberships)
        await session.commit()
        return SeededTeam(team.id, tuple(memberships), tuple(profiles))


def _side(team: SeededTeam) -> dict:
    return {
        "team_id": team.id,
        "playing_xi_membership_ids": list(team.membership_ids),
        "captain_membership_id": team.membership_ids[0],
        "wicketkeeper_membership_id": team.membership_ids[1],
    }


def _payload(team_a: SeededTeam, team_b: SeededTeam) -> dict:
    return {
        "team_a": _side(team_a),
        "team_b": _side(team_b),
        "match_type": "limited",
        "overs_limit": 20,
        "days_limit": None,
        "overs_per_day": None,
        "dls_enabled": False,
        "toss_winner_side": "team_a",
        "decision": "bat",
    }


def _external_payload(
    school_team: SeededTeam, *, school_side: str = "team_a", team_name: str = "Westhaven First XI"
) -> dict:
    payload = {
        "mode": "school_vs_external",
        "school_side": school_side,
        "team_a": _side(school_team) if school_side == "team_a" else None,
        "team_b": _side(school_team) if school_side == "team_b" else None,
        "external_opponent": {
            "team_name": team_name,
            "player_names": [f"Westhaven Player {index}" for index in range(1, 12)],
            "captain_index": 0,
            "wicketkeeper_index": 1,
        },
        "match_type": "limited",
        "overs_limit": 20,
        "days_limit": None,
        "overs_per_day": None,
        "dls_enabled": False,
        "toss_winner_side": "team_a",
        "decision": "bat",
    }
    return payload


async def _match_environment(
    client: TestClient,
    *,
    suffix: str,
    role: str = "owner",
) -> tuple[RegisteredUser, RegisteredUser, dict, SeededTeam, SeededTeam]:
    owner = register_user(client, f"school-match-{suffix}-owner@example.com")
    actor = owner
    organization = create_school(client, owner, f"School Match {suffix}")
    if role != "owner":
        actor = register_user(client, f"school-match-{suffix}-{role}@example.com")
        add_membership(client, owner, organization["id"], actor.id, role)
    team_a = await _seed_team(
        client,
        organization_id=organization["id"],
        owner_user_id=owner.id,
        name=f"{suffix} First XI",
    )
    team_b = await _seed_team(
        client,
        organization_id=organization["id"],
        owner_user_id=owner.id,
        name=f"{suffix} U15",
    )
    return owner, actor, organization, team_a, team_b


@pytest.mark.parametrize("role", ["owner", "admin", "coach", "scorer"])
async def test_contextual_school_roles_create_match_from_explicit_eligible_xi(
    school_client: TestClient,
    role: str,
) -> None:
    _, actor, organization, team_a, team_b = await _match_environment(
        school_client,
        suffix=f"role-{role}",
        role=role,
    )

    response = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_payload(team_a, team_b),
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["organization_id"] == organization["id"]
    assert body["team_a_player_profile_ids"] == list(team_a.profile_ids)
    assert body["team_b_player_profile_ids"] == list(team_b.profile_ids)

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        game = await session.get(Game, body["game_id"])
        assert game is not None
        assert game.publication_state == "private"
        assert game.created_by_user_id == actor.id
        assert game.team_a["school_source"] == {
            "organization_id": organization["id"],
            "team_id": team_a.id,
        }
        assert game.team_a["playing_xi"] == list(team_a.profile_ids)
        assert game.team_a_captain_id == team_a.profile_ids[0]
        assert game.team_a_keeper_id == team_a.profile_ids[1]
        stored_team = await session.get(Team, team_a.id)
        assert stored_team is not None
        assert stored_team.players == [
            {"id": "legacy-only", "name": "Legacy JSON must remain untouched"}
        ]


async def test_viewer_and_global_role_or_org_id_cannot_bypass_school_authority(
    school_client: TestClient,
) -> None:
    owner, viewer, organization, team_a, team_b = await _match_environment(
        school_client,
        suffix="viewer-denial",
        role="viewer",
    )
    denied = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_payload(team_a, team_b),
        headers=viewer.headers,
    )
    assert denied.status_code == 403
    assert denied.json() == {"detail": "Insufficient organization role"}

    outsider = register_user(school_client, "school-match-global-bypass@example.com")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(User, outsider.id)
        assert stored is not None
        stored.role = RoleEnum.org_pro
        stored.org_id = organization["id"]
        stored.is_superuser = True
        await session.commit()
    bypass = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_payload(team_a, team_b),
        headers=outsider.headers,
    )
    assert bypass.status_code == 404
    assert bypass.json() == {"detail": "Organization not found"}
    assert organization["name"].lower() not in bypass.text.lower()
    assert owner.email not in bypass.text


async def test_school_match_capabilities_are_all_required(school_client: TestClient) -> None:
    _, actor, organization, team_a, team_b = await _match_environment(
        school_client,
        suffix="capability",
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        assert entitlement is not None
        entitlement.status = "disabled"
        await session.commit()

    response = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_payload(team_a, team_b),
        headers=actor.headers,
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": "Organization capability not enabled: school_match_playing_xi"
    }


@pytest.mark.parametrize(
    "missing_capability",
    ["school_match_playing_xi", "school_persistent_teams", "school_team_rosters"],
)
async def test_each_saved_team_match_capability_is_enforced(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    missing_capability: str,
) -> None:
    _, actor, organization, team_a, team_b = await _match_environment(
        school_client,
        suffix=f"missing-{missing_capability}",
    )
    approved = organization_entitlement_service.SCHOOL_FREE_CAPABILITIES - {missing_capability}
    monkeypatch.setitem(
        organization_entitlement_service.PLAN_CAPABILITIES,
        organization_entitlement_service.SCHOOL_FREE_PLAN_KEY,
        frozenset(approved),
    )

    response = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_payload(team_a, team_b),
        headers=actor.headers,
    )
    assert response.status_code == 403
    assert response.json() == {
        "detail": f"Organization capability not enabled: {missing_capability}"
    }


async def test_server_rejects_stale_duplicate_inactive_and_tampered_xi_ids(
    school_client: TestClient,
) -> None:
    _, actor, organization, team_a, team_b = await _match_environment(
        school_client,
        suffix="eligibility",
    )
    url = f"/api/organizations/{organization['id']}/matches"

    duplicate = _payload(team_a, team_b)
    duplicate["team_a"]["playing_xi_membership_ids"][-1] = team_a.membership_ids[0]
    assert school_client.post(url, json=duplicate, headers=actor.headers).status_code == 422

    captain_outside = _payload(team_a, team_b)
    captain_outside["team_a"]["captain_membership_id"] = str(uuid.uuid4())
    assert school_client.post(url, json=captain_outside, headers=actor.headers).status_code == 422

    keeper_outside = _payload(team_a, team_b)
    keeper_outside["team_b"]["wicketkeeper_membership_id"] = str(uuid.uuid4())
    assert school_client.post(url, json=keeper_outside, headers=actor.headers).status_code == 422

    tampered = _payload(team_a, team_b)
    tampered["team_a"]["playing_xi_membership_ids"][2] = str(uuid.uuid4())
    tampered_response = school_client.post(url, json=tampered, headers=actor.headers)
    assert tampered_response.status_code == 422
    assert "not eligible" in tampered_response.text

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        inactive_team_member = await session.get(
            SchoolTeamPlayerMembership, team_a.membership_ids[0]
        )
        assert inactive_team_member is not None
        inactive_team_member.status = "inactive"
        await session.commit()
    inactive_team_response = school_client.post(
        url, json=_payload(team_a, team_b), headers=actor.headers
    )
    assert inactive_team_response.status_code == 422

    async with session_maker() as session:
        team_member = await session.get(SchoolTeamPlayerMembership, team_a.membership_ids[0])
        assert team_member is not None
        team_member.status = "active"
        school_member = await session.get(
            SchoolPlayerMembership, team_member.school_player_membership_id
        )
        assert school_member is not None
        school_member.status = "inactive"
        await session.commit()
    inactive_school_response = school_client.post(
        url, json=_payload(team_a, team_b), headers=actor.headers
    )
    assert inactive_school_response.status_code == 422

    async with session_maker() as session:
        team_member = await session.get(SchoolTeamPlayerMembership, team_a.membership_ids[0])
        assert team_member is not None
        school_member = await session.get(
            SchoolPlayerMembership, team_member.school_player_membership_id
        )
        assert school_member is not None
        school_member.status = "active"
        archived = await session.get(Team, team_b.id)
        assert archived is not None
        archived.status = "archived"
        await session.commit()
    archived_response = school_client.post(
        url, json=_payload(team_a, team_b), headers=actor.headers
    )
    assert archived_response.status_code == 409


async def test_foreign_team_and_membership_ids_are_tenant_safe(school_client: TestClient) -> None:
    _, actor_a, school_a, team_a1, team_a2 = await _match_environment(
        school_client,
        suffix="tenant-a",
    )
    owner_b, _, school_b, team_b1, _ = await _match_environment(
        school_client,
        suffix="tenant-b",
    )
    url = f"/api/organizations/{school_a['id']}/matches"

    foreign_team = _payload(team_a1, team_b1)
    response = school_client.post(url, json=foreign_team, headers=actor_a.headers)
    assert response.status_code == 404
    assert response.json() == {"detail": "Team not found"}
    assert school_b["name"].lower() not in response.text.lower()

    wrong_team_membership = _payload(team_a1, team_a2)
    wrong_team_membership["team_a"]["playing_xi_membership_ids"][2] = team_a2.membership_ids[0]
    response = school_client.post(url, json=wrong_team_membership, headers=actor_a.headers)
    assert response.status_code == 422
    assert response.json() == {
        "detail": "One or more selected players are not eligible for this Team"
    }

    foreign_membership = _payload(team_a1, team_a2)
    foreign_membership["team_a"]["playing_xi_membership_ids"][2] = team_b1.membership_ids[0]
    response = school_client.post(url, json=foreign_membership, headers=actor_a.headers)
    assert response.status_code == 422
    assert response.json() == {
        "detail": "One or more selected players are not eligible for this Team"
    }
    assert school_b["name"].lower() not in response.text.lower()
    assert owner_b.email not in response.text


async def test_match_snapshot_and_canonical_identity_survive_roster_lifecycle_changes(
    school_client: TestClient,
) -> None:
    _, actor, organization, team_a, team_b = await _match_environment(
        school_client,
        suffix="snapshot",
    )
    before_profiles = 22
    first = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_payload(team_a, team_b),
        headers=actor.headers,
    )
    second = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_payload(team_a, team_b),
        headers=actor.headers,
    )
    assert first.status_code == second.status_code == 201
    first_id = first.json()["game_id"]
    second_id = second.json()["game_id"]
    assert first.json()["team_a_player_profile_ids"] == second.json()["team_a_player_profile_ids"]

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    is_postgres = False
    async with session_maker() as session:
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == before_profiles
        game = await session.get(Game, first_id)
        assert game is not None
        is_postgres = session.bind is not None and session.bind.dialect.name == "postgresql"
        frozen_team_a = game.team_a.copy()

    if is_postgres:
        scored = school_client.post(
            f"/games/{first_id}/deliveries",
            json={
                "striker_id": team_a.profile_ids[0],
                "non_striker_id": team_a.profile_ids[1],
                "bowler_id": team_b.profile_ids[0],
                "runs_scored": 4,
                "runs_off_bat": 0,
                "is_wicket": False,
            },
            headers=actor.headers,
        )
        assert scored.status_code == 200, scored.text
        assert scored.json()["score"]["runs"] == 4

    async with session_maker() as session:
        roster_member = await session.get(SchoolTeamPlayerMembership, team_a.membership_ids[0])
        assert roster_member is not None
        roster_member.status = "inactive"
        school_member = await session.get(
            SchoolPlayerMembership, roster_member.school_player_membership_id
        )
        assert school_member is not None
        school_member.status = "inactive"
        current_team = await session.get(Team, team_a.id)
        assert current_team is not None
        current_team.status = "archived"
        await session.commit()

    async with session_maker() as session:
        frozen_game = await session.get(Game, first_id)
        assert frozen_game is not None
        assert frozen_game.team_a == frozen_team_a
        assert frozen_game.team_a["playing_xi"] == list(team_a.profile_ids)

    # The repository's SQLite test mode intentionally monkey-patches legacy game
    # CRUD with an in-memory store. PostgreSQL exercises the actual persistence
    # path used in production, including resume, scoring snapshot, and results.
    if not is_postgres:
        return

    resumed = school_client.get(f"/games/{first_id}", headers=actor.headers)
    snapshot = school_client.get(f"/games/{first_id}/snapshot", headers=actor.headers)
    assert resumed.status_code == snapshot.status_code == 200
    assert [player["id"] for player in resumed.json()["team_a"]["players"]] == list(
        team_a.profile_ids
    )
    assert [player["id"] for player in snapshot.json()["players"]["batting"]] == list(
        team_a.profile_ids
    )

    result = school_client.post(
        f"/games/{first_id}/results",
        json={
            "match_id": first_id,
            "winner": frozen_team_a["name"],
            "team_a_score": 120,
            "team_b_score": 100,
        },
    )
    assert result.status_code == 201, result.text
    persisted_result = school_client.get(f"/games/{first_id}/results")
    assert persisted_result.status_code == 200
    assert persisted_result.json()["winner_team_name"] == frozen_team_a["name"]

    async with session_maker() as session:
        game = await session.get(Game, first_id)
        other_game = await session.get(Game, second_id)
        assert game is not None and other_game is not None
        assert game.team_a == frozen_team_a
        assert other_game.team_a["playing_xi"] == list(team_a.profile_ids)


async def test_same_canonical_player_can_be_reused_across_different_saved_teams(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "school-match-shared-owner@example.com")
    organization = create_school(school_client, owner, "Shared Player School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    profile_id = str(uuid.uuid4())
    school_membership_id = str(uuid.uuid4())
    async with session_maker() as session:
        session.add(PlayerProfile(player_id=profile_id, player_name="Shared Player"))
        session.add(
            SchoolPlayerMembership(
                id=school_membership_id,
                organization_id=organization["id"],
                player_profile_id=profile_id,
                status="active",
                created_by_user_id=owner.id,
            )
        )
        await session.commit()
    shared = (profile_id, school_membership_id)
    team_one = await _seed_team(
        school_client,
        organization_id=organization["id"],
        owner_user_id=owner.id,
        name="U15",
        shared_player=shared,
    )
    team_two = await _seed_team(
        school_client,
        organization_id=organization["id"],
        owner_user_id=owner.id,
        name="First XI",
        shared_player=shared,
    )
    opponent_one = await _seed_team(
        school_client,
        organization_id=organization["id"],
        owner_user_id=owner.id,
        name="Opponent One",
    )
    opponent_two = await _seed_team(
        school_client,
        organization_id=organization["id"],
        owner_user_id=owner.id,
        name="Opponent Two",
    )
    url = f"/api/organizations/{organization['id']}/matches"
    same_match = school_client.post(url, json=_payload(team_one, team_two), headers=owner.headers)
    assert same_match.status_code == 422
    assert same_match.json() == {
        "detail": "A canonical player cannot appear for both sides in one match"
    }
    first = school_client.post(url, json=_payload(team_one, opponent_one), headers=owner.headers)
    second = school_client.post(url, json=_payload(team_two, opponent_two), headers=owner.headers)
    assert first.status_code == second.status_code == 201
    assert first.json()["team_a_player_profile_ids"][0] == profile_id
    assert second.json()["team_a_player_profile_ids"][0] == profile_id
    async with session_maker() as session:
        assert (
            await session.scalar(
                select(func.count(PlayerProfile.player_id)).where(
                    PlayerProfile.player_id == profile_id
                )
            )
            == 1
        )


def test_generic_match_creation_contract_remains_available(school_client: TestClient) -> None:
    response = school_client.post(
        "/games",
        json={
            "team_a_name": "Generic A",
            "team_b_name": "Generic B",
            "players_a": ["A1", "A2"],
            "players_b": ["B1", "B2"],
            "match_type": "limited",
            "overs_limit": 20,
            "dls_enabled": False,
            "interruptions": [],
            "toss_winner_team": "Generic A",
            "decision": "bat",
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["team_a"]["name"] == "Generic A"
    assert len(response.json()["team_a"]["players"]) == 2


@pytest.mark.parametrize("role", ["owner", "admin", "coach", "scorer"])
@pytest.mark.parametrize("school_side", ["team_a", "team_b"])
async def test_authorized_roles_create_external_match_with_school_on_either_side(
    school_client: TestClient,
    role: str,
    school_side: str,
) -> None:
    _, actor, organization, school_team, _ = await _match_environment(
        school_client,
        suffix=f"external-{role}-{school_side}",
        role=role,
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        before = {
            "teams": await session.scalar(select(func.count(Team.id))),
            "profiles": await session.scalar(select(func.count(PlayerProfile.player_id))),
            "school_memberships": await session.scalar(
                select(func.count(SchoolPlayerMembership.id))
            ),
            "team_memberships": await session.scalar(
                select(func.count(SchoolTeamPlayerMembership.id))
            ),
        }

    response = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_external_payload(school_team, school_side=school_side),
        headers=actor.headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    school_key = school_side
    external_key = "team_b" if school_side == "team_a" else "team_a"
    assert body[f"{school_key}_id"] == school_team.id
    assert body[f"{external_key}_id"] is None
    assert body[f"{school_key}_player_profile_ids"] == list(school_team.profile_ids)
    assert body[f"{external_key}_player_profile_ids"] == []

    async with session_maker() as session:
        game = await session.get(Game, body["game_id"])
        assert game is not None
        school_snapshot = getattr(game, school_key)
        external_snapshot = getattr(game, external_key)
        assert school_snapshot["school_source"] == {
            "organization_id": organization["id"],
            "team_id": school_team.id,
        }
        assert school_snapshot["playing_xi"] == list(school_team.profile_ids)
        assert "school_source" not in external_snapshot
        assert len(external_snapshot["players"]) == 11
        external_ids = [player["id"] for player in external_snapshot["players"]]
        assert len(set(external_ids)) == 11
        assert all(player_id.startswith("external:") for player_id in external_ids)
        assert all("player_profile_id" not in player for player in external_snapshot["players"])
        assert set(external_snapshot["playing_xi"]) == set(external_ids)
        assert game.publication_state == "private"
        assert game.created_by_user_id == actor.id
        assert before == {
            "teams": await session.scalar(select(func.count(Team.id))),
            "profiles": await session.scalar(select(func.count(PlayerProfile.player_id))),
            "school_memberships": await session.scalar(
                select(func.count(SchoolPlayerMembership.id))
            ),
            "team_memberships": await session.scalar(
                select(func.count(SchoolTeamPlayerMembership.id))
            ),
        }


async def test_external_match_preserves_contextual_authorization_and_tenant_safety(
    school_client: TestClient,
) -> None:
    owner, viewer, organization, school_team, _ = await _match_environment(
        school_client,
        suffix="external-auth",
        role="viewer",
    )
    url = f"/api/organizations/{organization['id']}/matches"
    denied = school_client.post(
        url,
        json=_external_payload(school_team),
        headers=viewer.headers,
    )
    assert denied.status_code == 403

    outsider = register_user(school_client, "external-match-outsider@example.com")
    hidden = school_client.post(
        url,
        json=_external_payload(school_team),
        headers=outsider.headers,
    )
    assert hidden.status_code == 404
    assert organization["name"].lower() not in hidden.text.lower()

    _, actor_b, school_b, foreign_team, _ = await _match_environment(
        school_client,
        suffix="external-foreign",
    )
    foreign = school_client.post(
        url,
        json=_external_payload(foreign_team),
        headers=owner.headers,
    )
    assert foreign.status_code == 404
    assert foreign.json() == {"detail": "Team not found"}
    assert school_b["name"].lower() not in foreign.text.lower()
    assert actor_b.email not in foreign.text


async def test_external_match_reuses_school_eligibility_and_validates_manual_xi(
    school_client: TestClient,
) -> None:
    _, actor, organization, school_team, _ = await _match_environment(
        school_client,
        suffix="external-validation",
    )
    url = f"/api/organizations/{organization['id']}/matches"

    too_few = _external_payload(school_team)
    too_few["external_opponent"]["player_names"].pop()
    assert school_client.post(url, json=too_few, headers=actor.headers).status_code == 422

    too_few_school = _external_payload(school_team)
    too_few_school["team_a"]["playing_xi_membership_ids"].pop()
    assert school_client.post(url, json=too_few_school, headers=actor.headers).status_code == 422

    duplicate_school = _external_payload(school_team)
    duplicate_school["team_a"]["playing_xi_membership_ids"][-1] = school_team.membership_ids[0]
    assert school_client.post(url, json=duplicate_school, headers=actor.headers).status_code == 422

    duplicate = _external_payload(school_team)
    duplicate["external_opponent"]["player_names"][-1] = "WESTHAVEN PLAYER 1"
    assert school_client.post(url, json=duplicate, headers=actor.headers).status_code == 422

    injected = _external_payload(school_team)
    injected["external_opponent"]["player_names"][0] = {
        "id": school_team.profile_ids[0],
        "name": "Injected canonical player",
    }
    assert school_client.post(url, json=injected, headers=actor.headers).status_code == 422

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        team_membership = await session.get(
            SchoolTeamPlayerMembership, school_team.membership_ids[0]
        )
        assert team_membership is not None
        team_membership.status = "inactive"
        await session.commit()
    ineligible = school_client.post(
        url,
        json=_external_payload(school_team),
        headers=actor.headers,
    )
    assert ineligible.status_code == 422

    async with session_maker() as session:
        team_membership = await session.get(
            SchoolTeamPlayerMembership, school_team.membership_ids[0]
        )
        assert team_membership is not None
        team_membership.status = "active"
        school_membership = await session.get(
            SchoolPlayerMembership, team_membership.school_player_membership_id
        )
        assert school_membership is not None
        school_membership.status = "inactive"
        await session.commit()
    inactive_school = school_client.post(
        url,
        json=_external_payload(school_team),
        headers=actor.headers,
    )
    assert inactive_school.status_code == 422

    async with session_maker() as session:
        team_membership = await session.get(
            SchoolTeamPlayerMembership, school_team.membership_ids[0]
        )
        assert team_membership is not None
        school_membership = await session.get(
            SchoolPlayerMembership, team_membership.school_player_membership_id
        )
        assert school_membership is not None
        school_membership.status = "active"
        team = await session.get(Team, school_team.id)
        assert team is not None
        team.status = "archived"
        await session.commit()
    archived = school_client.post(
        url,
        json=_external_payload(school_team),
        headers=actor.headers,
    )
    assert archived.status_code == 409


@pytest.mark.parametrize("school_side", ["team_a", "team_b"])
async def test_mixed_match_statistics_publication_and_snapshot_are_school_attributed_only(
    school_client: TestClient,
    school_side: str,
) -> None:
    _, owner, organization, school_team, _ = await _match_environment(
        school_client,
        suffix="external-attribution",
    )
    create = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_external_payload(school_team, school_side=school_side),
        headers=owner.headers,
    )
    assert create.status_code == 201, create.text
    game_id = create.json()["game_id"]
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        game = await session.get(Game, game_id)
        assert game is not None
        is_postgres = session.bind is not None and session.bind.dialect.name == "postgresql"
        school_snapshot = game.team_a if school_side == "team_a" else game.team_b
        external_snapshot = game.team_b if school_side == "team_a" else game.team_a
        frozen_team_a = copy.deepcopy(game.team_a)
        frozen_team_b = copy.deepcopy(game.team_b)
        external_ids = external_snapshot["playing_xi"]
        batting_snapshot = (
            game.team_a if game.batting_team_name == game.team_a["name"] else game.team_b
        )
        bowling_snapshot = (
            game.team_a if game.bowling_team_name == game.team_a["name"] else game.team_b
        )

    if is_postgres:
        scored = school_client.post(
            f"/games/{game_id}/deliveries",
            json={
                "striker_id": batting_snapshot["playing_xi"][0],
                "non_striker_id": batting_snapshot["playing_xi"][1],
                "bowler_id": bowling_snapshot["playing_xi"][0],
                "runs_scored": 1,
                "runs_off_bat": 0,
                "is_wicket": False,
            },
            headers=owner.headers,
        )
        assert scored.status_code == 200, scored.text

    async with session_maker() as session:
        game = await session.get(Game, game_id)
        assert game is not None
        game.deliveries = [
            {
                "over_number": 1,
                "ball_number": 1,
                "inning": 1,
                "striker_id": school_team.profile_ids[0],
                "non_striker_id": school_team.profile_ids[1],
                "bowler_id": external_ids[0],
                "runs_off_bat": 4,
                "runs_scored": 4,
                "is_extra": False,
                "is_wicket": False,
            },
            {
                "over_number": 1,
                "ball_number": 1,
                "inning": 2,
                "striker_id": external_ids[0],
                "non_striker_id": external_ids[1],
                "bowler_id": school_team.profile_ids[1],
                "runs_off_bat": 2,
                "runs_scored": 2,
                "is_extra": False,
                "is_wicket": False,
            },
        ]
        game.status = GameStatus.completed
        game.result = f"{school_snapshot['name']} won by 2 runs"
        current_team = await session.get(Team, school_team.id)
        assert current_team is not None
        current_team.name = "Renamed after match"
        await session.commit()

    players = school_client.get(
        f"/api/organizations/{organization['id']}/statistics/players",
        headers=owner.headers,
    )
    teams = school_client.get(
        f"/api/organizations/{organization['id']}/statistics/teams",
        headers=owner.headers,
    )
    results = school_client.get(
        f"/api/organizations/{organization['id']}/results",
        headers=owner.headers,
    )
    assert players.status_code == teams.status_code == results.status_code == 200
    player_rows = {row["player_profile_id"]: row for row in players.json()}
    assert player_rows[school_team.profile_ids[0]]["runs"] == 4
    assert player_rows[school_team.profile_ids[0]]["matches"] == 1
    assert player_rows[school_team.profile_ids[1]]["runs_conceded"] == 2
    team_row = next(row for row in teams.json() if row["team_id"] == school_team.id)
    assert team_row["matches"] == 1
    assert team_row["wins"] == 1
    assert team_row["runs_scored"] == 4
    assert team_row["runs_conceded"] == 2
    assert all(row["team_name"] != "Westhaven First XI" for row in teams.json())
    mixed_result = next(row for row in results.json() if row["game_id"] == game_id)
    expected_a_id = school_team.id if school_side == "team_a" else None
    expected_b_id = school_team.id if school_side == "team_b" else None
    assert mixed_result["team_a_id"] == expected_a_id
    assert mixed_result["team_b_id"] == expected_b_id
    external_name_key = "team_b_name" if school_side == "team_a" else "team_a_name"
    assert mixed_result[external_name_key] == "Westhaven First XI"

    publication_url = f"/api/organizations/{organization['id']}/matches/{game_id}/publication"
    published_live = school_client.patch(
        publication_url,
        json={"publication_state": "published_live"},
        headers=owner.headers,
    )
    assert published_live.status_code == 200, published_live.text
    assert school_client.get(f"/public/school-scorecards/{game_id}").status_code == 200
    published = school_client.patch(
        publication_url,
        json={"publication_state": "published_final"},
        headers=owner.headers,
    )
    assert published.status_code == 200, published.text
    public = school_client.get(f"/public/school-scorecards/{game_id}")
    assert public.status_code == 200, public.text
    assert public.json()["team_a"]["name"] == frozen_team_a["name"]
    assert public.json()["team_b"]["name"] == frozen_team_b["name"]
    serialized = public.text
    assert "school_source" not in serialized
    assert school_team.id not in serialized
    assert all(player_id not in serialized for player_id in external_ids)
    private = school_client.patch(
        publication_url,
        json={"publication_state": "private"},
        headers=owner.headers,
    )
    assert private.status_code == 200
    assert school_client.get(f"/public/school-scorecards/{game_id}").status_code == 404

    if is_postgres:
        resumed = school_client.get(f"/games/{game_id}", headers=owner.headers)
        assert resumed.status_code == 200, resumed.text
        resumed_school = resumed.json()[school_side]
        frozen_school_name = (
            frozen_team_a["name"] if school_side == "team_a" else frozen_team_b["name"]
        )
        assert resumed_school["name"] == frozen_school_name
        assert [player["id"] for player in resumed_school["players"]] == list(
            school_team.profile_ids
        )

    async with session_maker() as session:
        game = await session.get(Game, game_id)
        assert game is not None
        assert game.team_a == frozen_team_a
        assert game.team_b == frozen_team_b


async def _opening_player_ids(client: TestClient, game_id: str) -> tuple[str, str, str]:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        game = await session.get(Game, game_id)
        assert game is not None
        batting = game.team_a if game.batting_team_name == game.team_a["name"] else game.team_b
        bowling = game.team_b if game.bowling_team_name == game.team_b["name"] else game.team_a
        return (
            str(batting["players"][0]["id"]),
            str(batting["players"][1]["id"]),
            str(bowling["players"][0]["id"]),
        )


async def _require_postgres_game_routes(client: TestClient) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        is_postgres = session.bind is not None and session.bind.dialect.name == "postgresql"
    if not is_postgres:
        pytest.skip("School gameplay routes require the real PostgreSQL persistence gate")


async def _start_first_innings(
    client: TestClient,
    *,
    game_id: str,
    headers: dict[str, str],
) -> tuple[tuple[str, str, str], dict]:
    striker_id, non_striker_id, bowler_id = await _opening_player_ids(client, game_id)
    openers = client.post(
        f"/games/{game_id}/openers",
        json={"striker_id": striker_id, "non_striker_id": non_striker_id},
        headers=headers,
    )
    assert openers.status_code == 200, openers.text
    started = client.post(
        f"/games/{game_id}/innings/start",
        json={
            "striker_id": striker_id,
            "non_striker_id": non_striker_id,
            "opening_bowler_id": bowler_id,
        },
        headers=headers,
    )
    assert started.status_code == 200, started.text
    return (striker_id, non_striker_id, bowler_id), started.json()


@pytest.mark.parametrize("role", ["owner", "admin", "coach", "scorer"])
async def test_school_contextual_scorers_start_first_innings_without_personal_upgrade(
    school_client: TestClient,
    role: str,
) -> None:
    await _require_postgres_game_routes(school_client)
    _, actor, organization, team_a, team_b = await _match_environment(
        school_client,
        suffix=f"first-innings-{role}",
        role=role,
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored_actor = await session.get(User, actor.id)
        assert stored_actor is not None
        assert stored_actor.role == RoleEnum.free
    created = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_payload(team_a, team_b),
        headers=actor.headers,
    )
    assert created.status_code == 201, created.text
    game_id = created.json()["game_id"]

    snapshot = school_client.get(f"/games/{game_id}/snapshot", headers=actor.headers)
    assert snapshot.status_code == 200, snapshot.text
    assert snapshot.json()["school_organization_id"] == organization["id"]
    assert snapshot.json()["can_score"] is True

    opening_ids, started = await _start_first_innings(
        school_client,
        game_id=game_id,
        headers=actor.headers,
    )
    assert started["status"] == "IN_PROGRESS"
    assert started["current_inning"] == 1
    assert started["score"] == {"runs": 0, "wickets": 0, "overs": 0}
    assert started.get("deliveries", []) == []
    assert started["current_striker_id"] == opening_ids[0]
    assert started["current_non_striker_id"] == opening_ids[1]
    assert started["current_bowler_id"] == opening_ids[2]

    duplicate = school_client.post(
        f"/games/{game_id}/innings/start",
        json={
            "striker_id": opening_ids[0],
            "non_striker_id": opening_ids[1],
            "opening_bowler_id": opening_ids[2],
        },
        headers=actor.headers,
    )
    assert duplicate.status_code == 400
    assert duplicate.json() == {"detail": "No new innings to start"}


async def test_school_viewer_and_cross_tenant_users_cannot_mutate_scoring(
    school_client: TestClient,
) -> None:
    await _require_postgres_game_routes(school_client)
    owner, viewer, organization, team_a, team_b = await _match_environment(
        school_client,
        suffix="scoring-denial",
        role="viewer",
    )
    created = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_payload(team_a, team_b),
        headers=owner.headers,
    )
    assert created.status_code == 201, created.text
    game_id = created.json()["game_id"]
    striker_id, non_striker_id, bowler_id = await _opening_player_ids(school_client, game_id)

    viewer_snapshot = school_client.get(f"/games/{game_id}/snapshot", headers=viewer.headers)
    assert viewer_snapshot.status_code == 200
    assert viewer_snapshot.json()["can_score"] is False

    mutations = (
        ("openers", {"striker_id": striker_id, "non_striker_id": non_striker_id}),
        (
            "innings/start",
            {
                "striker_id": striker_id,
                "non_striker_id": non_striker_id,
                "opening_bowler_id": bowler_id,
            },
        ),
        (
            "deliveries",
            {
                "striker_id": striker_id,
                "non_striker_id": non_striker_id,
                "bowler_id": bowler_id,
                "runs_scored": 1,
                "runs_off_bat": 0,
                "is_wicket": False,
            },
        ),
    )
    for endpoint, payload in mutations:
        denied = school_client.post(
            f"/games/{game_id}/{endpoint}", json=payload, headers=viewer.headers
        )
        assert denied.status_code == 403
        assert denied.json() == {"detail": "Insufficient organization role"}

    outsider = register_user(school_client, "school-scoring-outsider@example.com")
    create_school(school_client, outsider, "Unrelated Scoring School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(User, outsider.id)
        assert stored is not None
        stored.role = RoleEnum.org_pro
        stored.org_id = organization["id"]
        stored.is_superuser = True
        await session.commit()

    hidden_snapshot = school_client.get(f"/games/{game_id}/snapshot", headers=outsider.headers)
    assert hidden_snapshot.status_code == 404
    assert hidden_snapshot.json() == {"detail": "Game not found"}
    hidden_start = school_client.post(
        f"/games/{game_id}/innings/start",
        json={
            "striker_id": striker_id,
            "non_striker_id": non_striker_id,
            "opening_bowler_id": bowler_id,
        },
        headers=outsider.headers,
    )
    assert hidden_start.status_code == 404
    assert hidden_start.json() == {"detail": "Game not found"}
    assert organization["name"].lower() not in hidden_start.text.lower()


async def test_school_scoring_requires_the_active_organization_entitlement(
    school_client: TestClient,
) -> None:
    await _require_postgres_game_routes(school_client)
    _, owner, organization, team_a, team_b = await _match_environment(
        school_client,
        suffix="scoring-entitlement",
    )
    created = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_payload(team_a, team_b),
        headers=owner.headers,
    )
    assert created.status_code == 201, created.text
    game_id = created.json()["game_id"]
    striker_id, non_striker_id, bowler_id = await _opening_player_ids(school_client, game_id)

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        assert entitlement is not None
        entitlement.status = "disabled"
        await session.commit()

    snapshot = school_client.get(f"/games/{game_id}/snapshot", headers=owner.headers)
    assert snapshot.status_code == 200
    assert snapshot.json()["can_score"] is False
    denied = school_client.post(
        f"/games/{game_id}/innings/start",
        json={
            "striker_id": striker_id,
            "non_striker_id": non_striker_id,
            "opening_bowler_id": bowler_id,
        },
        headers=owner.headers,
    )
    assert denied.status_code == 403
    assert denied.json() == {"detail": "Insufficient organization role"}


@pytest.mark.parametrize("school_side", ["team_a", "team_b"])
async def test_school_vs_external_first_innings_uses_same_contextual_scoring_contract(
    school_client: TestClient,
    school_side: str,
) -> None:
    await _require_postgres_game_routes(school_client)
    _, scorer, organization, school_team, _ = await _match_environment(
        school_client,
        suffix=f"external-first-{school_side}",
        role="scorer",
    )
    created = school_client.post(
        f"/api/organizations/{organization['id']}/matches",
        json=_external_payload(school_team, school_side=school_side),
        headers=scorer.headers,
    )
    assert created.status_code == 201, created.text
    game_id = created.json()["game_id"]

    opening_ids, started = await _start_first_innings(
        school_client,
        game_id=game_id,
        headers=scorer.headers,
    )
    assert started["current_inning"] == 1
    assert started["score"]["runs"] == 0
    assert started.get("deliveries", []) == []

    scored = school_client.post(
        f"/games/{game_id}/deliveries",
        json={
            "striker_id": opening_ids[0],
            "non_striker_id": opening_ids[1],
            "bowler_id": opening_ids[2],
            "runs_scored": 1,
            "runs_off_bat": 0,
            "is_wicket": False,
        },
        headers=scorer.headers,
    )
    assert scored.status_code == 200, scored.text
    assert scored.json()["score"]["runs"] == 1


async def test_generic_match_scoring_contract_does_not_require_school_context(
    school_client: TestClient,
) -> None:
    created = school_client.post(
        "/games",
        json={
            "team_a_name": "Generic Start A",
            "team_b_name": "Generic Start B",
            "players_a": ["A1", "A2"],
            "players_b": ["B1", "B2"],
            "match_type": "limited",
            "overs_limit": 20,
            "dls_enabled": False,
            "interruptions": [],
            "toss_winner_team": "Generic Start A",
            "decision": "bat",
        },
    )
    assert created.status_code == 200, created.text
    game_id = created.json()["id"]
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        game = await session.get(Game, game_id)
        assert game is not None
        game.status = GameStatus.innings_break
        game.current_inning = 0
        await session.commit()

    opening_ids, started = await _start_first_innings(
        school_client,
        game_id=game_id,
        headers={},
    )
    assert started["current_inning"] == 1
    assert started["current_striker_id"] == opening_ids[0]
