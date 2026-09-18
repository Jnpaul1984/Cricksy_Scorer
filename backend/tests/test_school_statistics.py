from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.sql_app.models import (
    Fixture,
    Game,
    GameStatus,
    OrganizationEntitlement,
    PlayerProfile,
    RoleEnum,
    SchoolPlayerMembership,
    Team,
    Tournament,
    User,
)
from backend.tests.school_test_helpers import add_membership, create_school, register_user


@dataclass(frozen=True)
class SchoolStatsSeed:
    team_a: Team
    team_b: Team
    team_c: Team
    profile_a: PlayerProfile
    profile_same_name: PlayerProfile
    profile_bowler: PlayerProfile
    membership_a: SchoolPlayerMembership
    first_game: Game
    second_game: Game


def _snapshot(
    organization_id: str,
    team: Team,
    profiles: list[PlayerProfile],
) -> dict:
    return {
        "name": team.name,
        "players": [
            {
                "id": profile.player_id,
                "name": profile.player_name,
                "player_profile_id": profile.player_id,
                "school_player_membership_id": f"membership-{profile.player_id}",
                "school_team_player_membership_id": f"team-membership-{profile.player_id}",
            }
            for profile in profiles
        ],
        "playing_xi": [profile.player_id for profile in profiles],
        "school_source": {"organization_id": organization_id, "team_id": team.id},
    }


def _delivery(
    *,
    inning: int,
    striker: str,
    bowler: str,
    off_bat: int = 0,
    extra_type: str | None = None,
    extra_runs: int = 0,
    wicket: bool = False,
    dismissal_type: str | None = None,
    dismissed_player_id: str | None = None,
) -> dict:
    team_runs = off_bat
    if extra_type == "nb":
        team_runs += 1
        extra_runs = 1
    elif extra_type in {"wd", "b", "lb"}:
        team_runs = extra_runs
    return {
        "inning": inning,
        "striker_id": striker,
        "non_striker_id": striker,
        "bowler_id": bowler,
        "runs_off_bat": off_bat,
        "extra_type": extra_type,
        "extra_runs": extra_runs,
        "runs_scored": team_runs,
        "is_wicket": wicket,
        "dismissal_type": dismissal_type,
        "dismissed_player_id": dismissed_player_id,
    }


async def _seed(
    client: TestClient,
    organization_id: str,
    owner_id: str,
) -> SchoolStatsSeed:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        team_a = Team(
            id=str(uuid.uuid4()),
            name="First XI",
            organization_id=organization_id,
            owner_user_id=owner_id,
            status="active",
            players=[],
            competitions=[],
        )
        team_b = Team(
            id=str(uuid.uuid4()),
            name="Second XI",
            organization_id=organization_id,
            owner_user_id=owner_id,
            status="active",
            players=[],
            competitions=[],
        )
        team_c = Team(
            id=str(uuid.uuid4()),
            name="Development XI",
            organization_id=organization_id,
            owner_user_id=owner_id,
            status="archived",
            players=[],
            competitions=[],
        )
        profile_a = PlayerProfile(player_id=str(uuid.uuid4()), player_name="Alex Lee")
        profile_same_name = PlayerProfile(player_id=str(uuid.uuid4()), player_name="Alex Lee")
        profile_bowler = PlayerProfile(player_id=str(uuid.uuid4()), player_name="Jordan Moss")
        session.add_all([team_a, team_b, team_c, profile_a, profile_same_name, profile_bowler])
        await session.flush()
        memberships = [
            SchoolPlayerMembership(
                id=str(uuid.uuid4()),
                organization_id=organization_id,
                player_profile_id=profile.player_id,
                status="active",
                created_by_user_id=owner_id,
            )
            for profile in (profile_a, profile_same_name, profile_bowler)
        ]
        session.add_all(memberships)

        first_game = Game(
            id=str(uuid.uuid4()),
            team_a=_snapshot(organization_id, team_a, [profile_a, profile_bowler]),
            team_b=_snapshot(organization_id, team_b, [profile_same_name]),
            status=GameStatus.completed,
            current_inning=2,
            batting_team_name=team_b.name,
            bowling_team_name=team_a.name,
            result=f"{team_a.name} won by 5 runs",
            publication_state="private",
            created_by_user_id=owner_id,
            deliveries=[
                _delivery(
                    inning=1,
                    striker=profile_a.player_id,
                    bowler=profile_same_name.player_id,
                    off_bat=4,
                ),
                _delivery(
                    inning=1,
                    striker=profile_a.player_id,
                    bowler=profile_same_name.player_id,
                    off_bat=6,
                ),
                _delivery(
                    inning=1,
                    striker=profile_a.player_id,
                    bowler=profile_same_name.player_id,
                    wicket=True,
                    dismissal_type="bowled",
                    dismissed_player_id=profile_a.player_id,
                ),
                _delivery(
                    inning=2,
                    striker=profile_same_name.player_id,
                    bowler=profile_bowler.player_id,
                    off_bat=2,
                ),
                _delivery(
                    inning=2,
                    striker=profile_same_name.player_id,
                    bowler=profile_bowler.player_id,
                    extra_type="wd",
                    extra_runs=2,
                ),
                _delivery(
                    inning=2,
                    striker=profile_same_name.player_id,
                    bowler=profile_bowler.player_id,
                    off_bat=4,
                    extra_type="nb",
                ),
                _delivery(
                    inning=2,
                    striker=profile_same_name.player_id,
                    bowler=profile_bowler.player_id,
                    extra_type="b",
                    extra_runs=3,
                ),
                _delivery(
                    inning=2,
                    striker=profile_same_name.player_id,
                    bowler=profile_bowler.player_id,
                    wicket=True,
                    dismissal_type="run_out",
                    dismissed_player_id=profile_same_name.player_id,
                ),
            ],
        )
        second_game = Game(
            id=str(uuid.uuid4()),
            team_a=_snapshot(organization_id, team_c, [profile_a]),
            team_b=_snapshot(organization_id, team_b, [profile_same_name]),
            status=GameStatus.completed,
            current_inning=2,
            batting_team_name=team_b.name,
            bowling_team_name=team_c.name,
            result="Match tied",
            publication_state="published_final",
            created_by_user_id=owner_id,
            deliveries=[
                _delivery(
                    inning=1,
                    striker=profile_a.player_id,
                    bowler=profile_same_name.player_id,
                    off_bat=6,
                ),
                _delivery(
                    inning=1,
                    striker=profile_a.player_id,
                    bowler=profile_same_name.player_id,
                    off_bat=6,
                ),
                _delivery(
                    inning=1,
                    striker=profile_a.player_id,
                    bowler=profile_same_name.player_id,
                    off_bat=4,
                ),
                _delivery(
                    inning=1,
                    striker=profile_a.player_id,
                    bowler=profile_same_name.player_id,
                    off_bat=4,
                ),
            ],
        )
        legacy = Game(
            id=str(uuid.uuid4()),
            team_a={"name": "Legacy", "players": [{"id": "legacy-a", "name": "Alex Lee"}]},
            team_b={"name": "Legacy B", "players": []},
            status=GameStatus.completed,
            result="Legacy won by 10 runs",
            deliveries=[
                _delivery(
                    inning=1,
                    striker="legacy-a",
                    bowler="legacy-b",
                    off_bat=100,
                )
            ],
        )
        session.add_all([first_game, second_game, legacy])
        memberships[0].status = "inactive"
        await session.commit()
        return SchoolStatsSeed(
            team_a=team_a,
            team_b=team_b,
            team_c=team_c,
            profile_a=profile_a,
            profile_same_name=profile_same_name,
            profile_bowler=profile_bowler,
            membership_a=memberships[0],
            first_game=first_game,
            second_game=second_game,
        )


async def test_player_statistics_use_canonical_snapshots_and_delivery_truth(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "stats-owner@example.com")
    organization = create_school(school_client, owner, "Statistics School")
    seeded = await _seed(school_client, organization["id"], owner.id)

    response = school_client.get(
        f"/api/organizations/{organization['id']}/statistics/players",
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    rows = {row["player_profile_id"]: row for row in response.json()}
    alex = rows[seeded.profile_a.player_id]
    same_name = rows[seeded.profile_same_name.player_id]

    assert len(rows) == 3
    assert alex["player_name"] == same_name["player_name"] == "Alex Lee"
    assert alex["roster_status"] == "inactive"
    assert alex["matches"] == 2
    assert alex["innings"] == 2
    assert alex["runs"] == 30
    assert alex["highest_score"] == 20
    assert alex["batting_average"] == 30.0
    assert alex["balls_faced"] == 7
    assert alex["strike_rate"] == 428.57
    assert alex["fours"] == 3
    assert alex["sixes"] == 3
    assert same_name["runs"] == 6
    assert same_name["balls_faced"] == 3
    assert same_name["bowling_innings"] == 2
    assert same_name["balls_bowled"] == 7
    assert same_name["overs"] == "1.1"
    assert same_name["wickets"] == 1
    assert same_name["best_bowling"] == "1/10"


async def test_player_statistics_reflect_corrections_without_rewriting_history(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "correction-owner@example.com")
    organization = create_school(school_client, owner, "Correction School")
    seeded = await _seed(school_client, organization["id"], owner.id)
    url = f"/api/organizations/{organization['id']}/statistics/players/{seeded.profile_a.player_id}"
    before = school_client.get(url, headers=owner.headers)
    assert before.status_code == 200
    assert before.json()["runs"] == 30

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        game = await session.get(Game, seeded.second_game.id)
        assert game is not None
        deliveries = list(game.deliveries)
        deliveries[0] = {**deliveries[0], "runs_off_bat": 1, "runs_scored": 1}
        game.deliveries = deliveries
        await session.commit()

    corrected = school_client.get(url, headers=owner.headers)
    assert corrected.status_code == 200
    assert corrected.json()["runs"] == 25
    assert corrected.json()["highest_score"] == 15

    async with session_maker() as session:
        membership = await session.get(SchoolPlayerMembership, seeded.membership_a.id)
        assert membership is not None
        membership.status = "active"
        await session.commit()

    lifecycle_changed = school_client.get(url, headers=owner.headers)
    assert lifecycle_changed.status_code == 200
    assert lifecycle_changed.json()["roster_status"] == "active"
    assert lifecycle_changed.json()["runs"] == 25
    assert lifecycle_changed.json()["matches"] == 2


async def test_team_statistics_preserve_archived_team_and_frozen_attribution(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-stats-owner@example.com")
    organization = create_school(school_client, owner, "Team Statistics School")
    seeded = await _seed(school_client, organization["id"], owner.id)
    response = school_client.get(
        f"/api/organizations/{organization['id']}/statistics/teams", headers=owner.headers
    )
    assert response.status_code == 200, response.text
    rows = {row["team_id"]: row for row in response.json()}
    assert rows[seeded.team_a.id] == {
        "team_id": seeded.team_a.id,
        "team_name": "First XI",
        "team_status": "active",
        "matches": 1,
        "wins": 1,
        "losses": 0,
        "ties": 0,
        "draws": 0,
        "no_results": 0,
        "runs_scored": 10,
        "runs_conceded": 12,
        "wickets_taken": 1,
        "wickets_lost": 1,
    }
    assert rows[seeded.team_c.id]["team_status"] == "archived"
    assert rows[seeded.team_c.id]["matches"] == 1
    assert rows[seeded.team_c.id]["ties"] == 1
    assert rows[seeded.team_c.id]["runs_scored"] == 20


async def test_statistics_exact_ids_are_tenant_safe_and_capability_gated(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "tenant-stats-a@example.com")
    owner_b = register_user(school_client, "tenant-stats-b@example.com")
    school_a = create_school(school_client, owner_a, "Stats Tenant A")
    school_b = create_school(school_client, owner_b, "Stats Tenant B")
    seed_a = await _seed(school_client, school_a["id"], owner_a.id)
    seed_b = await _seed(school_client, school_b["id"], owner_b.id)
    add_membership(school_client, owner_b, school_b["id"], owner_a.id, "viewer")

    foreign_player = school_client.get(
        f"/api/organizations/{school_a['id']}/statistics/players/{seed_b.profile_a.player_id}",
        headers=owner_a.headers,
    )
    foreign_team = school_client.get(
        f"/api/organizations/{school_a['id']}/statistics/teams/{seed_b.team_a.id}",
        headers=owner_a.headers,
    )
    assert foreign_player.status_code == foreign_team.status_code == 404
    assert seed_b.profile_a.player_name not in foreign_player.text
    assert seed_b.team_a.name not in foreign_team.text

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == school_a["id"]
            )
        )
        assert entitlement is not None
        entitlement.status = "disabled"
        user = await session.get(User, owner_a.id)
        assert user is not None
        user.role = RoleEnum.org_pro
        user.is_superuser = True
        user.org_id = school_a["id"]
        await session.commit()
    denied = school_client.get(
        f"/api/organizations/{school_a['id']}/statistics/players",
        headers=owner_a.headers,
    )
    assert denied.status_code == 403
    assert denied.json() == {
        "detail": "Organization capability not enabled: school_basic_statistics"
    }
    assert seed_a.profile_a.player_id not in denied.text


async def test_results_and_fixture_summaries_use_official_linked_truth(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "results-owner@example.com")
    viewer = register_user(school_client, "results-viewer@example.com")
    organization = create_school(school_client, owner, "Results School")
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    seeded = await _seed(school_client, organization["id"], owner.id)
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        competition = Tournament(
            id=str(uuid.uuid4()),
            name="School Cup",
            organization_id=organization["id"],
            status="ongoing",
        )
        fixture = Fixture(
            id=str(uuid.uuid4()),
            tournament_id=competition.id,
            team_a_id=seeded.team_a.id,
            team_b_id=seeded.team_b.id,
            team_a_name=seeded.team_a.name,
            team_b_name=seeded.team_b.name,
            game_id=seeded.first_game.id,
            status="completed",
        )
        session.add_all([competition, fixture])
        live_game = Game(
            id=str(uuid.uuid4()),
            team_a=_snapshot(organization["id"], seeded.team_a, [seeded.profile_a]),
            team_b=_snapshot(organization["id"], seeded.team_b, [seeded.profile_same_name]),
            status=GameStatus.in_progress,
            current_inning=1,
            batting_team_name=seeded.team_a.name,
            bowling_team_name=seeded.team_b.name,
            publication_state="published_live",
            created_by_user_id=owner.id,
            deliveries=[],
        )
        live_game_id = live_game.id
        session.add(live_game)
        await session.commit()

    results = school_client.get(
        f"/api/organizations/{organization['id']}/results", headers=viewer.headers
    )
    fixtures = school_client.get(
        f"/api/organizations/{organization['id']}/fixtures", headers=viewer.headers
    )
    assert results.status_code == fixtures.status_code == 200
    result_by_id = {row["game_id"]: row for row in results.json()}
    first = result_by_id[seeded.first_game.id]
    assert first["result"] == "First XI won by 5 runs"
    assert first["team_a_runs"] == 10
    assert first["team_b_runs"] == 12
    assert first["publication_state"] == "private"
    assert first["public_scorecard_available"] is False
    live = result_by_id[live_game_id]
    assert live["status"] == "in_progress"
    assert live["result"] is None
    assert live["publication_state"] == "published_live"
    assert live["public_scorecard_available"] is True
    assert fixtures.json() == [
        {
            "fixture_id": fixture.id,
            "competition_id": competition.id,
            "competition_name": "School Cup",
            "team_a_id": seeded.team_a.id,
            "team_a_name": "First XI",
            "team_b_id": seeded.team_b.id,
            "team_b_name": "Second XI",
            "match_number": None,
            "venue": None,
            "scheduled_date": None,
            "fixture_status": "completed",
            "game_id": seeded.first_game.id,
            "game_status": "completed",
            "result": "First XI won by 5 runs",
            "publication_state": "private",
            "public_scorecard_available": False,
        }
    ]


async def test_results_are_tenant_isolated_without_role_or_user_bypass(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "results-tenant-a@example.com")
    owner_b = register_user(school_client, "results-tenant-b@example.com")
    school_a = create_school(school_client, owner_a, "Results Tenant A")
    school_b = create_school(school_client, owner_b, "Results Tenant B")
    await _seed(school_client, school_a["id"], owner_a.id)

    hidden = school_client.get(
        f"/api/organizations/{school_a['id']}/results", headers=owner_b.headers
    )
    assert hidden.status_code == 404
    assert "First XI" not in hidden.text

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        user = await session.get(User, owner_b.id)
        assert user is not None
        user.role = RoleEnum.org_pro
        user.is_superuser = True
        user.org_id = school_a["id"]
        await session.commit()

    still_hidden = school_client.get(
        f"/api/organizations/{school_a['id']}/results", headers=owner_b.headers
    )
    assert still_hidden.status_code == 404
    assert school_b["id"] not in still_hidden.text
