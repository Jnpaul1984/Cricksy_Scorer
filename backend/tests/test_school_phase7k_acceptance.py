"""Phase 7K production-like acceptance and rollout-gate regressions."""

from __future__ import annotations

import io
import json
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import func, select

from backend.services import organization_entitlement_service
from backend.sql_app.models import (
    Game,
    GameStatus,
    OrganizationEntitlement,
    PlayerProfile,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
    User,
)
from backend.tests.school_test_helpers import create_school, register_user


def _create_team(
    client: TestClient, organization_id: str, headers: dict[str, str], name: str
) -> dict:
    response = client.post(
        f"/api/organizations/{organization_id}/teams",
        json={"name": name},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _xlsx(rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    output = io.BytesIO()
    workbook.save(output)
    workbook.close()
    return output.getvalue()


def _match_payload(team_a: dict, roster_a: list[dict], team_b: dict, roster_b: list[dict]) -> dict:
    def side(team: dict, roster: list[dict]) -> dict:
        membership_ids = [row["id"] for row in roster]
        assert len(membership_ids) == 11
        return {
            "team_id": team["id"],
            "playing_xi_membership_ids": membership_ids,
            "captain_membership_id": membership_ids[0],
            "wicketkeeper_membership_id": membership_ids[1],
        }

    return {
        "team_a": side(team_a, roster_a),
        "team_b": side(team_b, roster_b),
        "match_type": "limited",
        "overs_limit": 1,
        "days_limit": None,
        "overs_per_day": None,
        "dls_enabled": False,
        "toss_winner_side": "team_a",
        "decision": "bat",
    }


def _start_innings(
    client: TestClient,
    game_id: str,
    batting: list[dict],
    bowling: list[dict],
    headers: dict[str, str],
) -> None:
    response = client.post(
        f"/games/{game_id}/innings/start",
        json={
            "striker_id": batting[0]["player_profile_id"],
            "non_striker_id": batting[1]["player_profile_id"],
            "opening_bowler_id": bowling[0]["player_profile_id"],
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text


def _delivery(
    client: TestClient,
    game_id: str,
    batting: list[dict],
    bowling: list[dict],
    runs: int,
    headers: dict[str, str],
) -> dict:
    response = client.post(
        f"/games/{game_id}/deliveries",
        json={
            "striker_id": batting[0]["player_profile_id"],
            "non_striker_id": batting[1]["player_profile_id"],
            "bowler_id": bowling[0]["player_profile_id"],
            "runs_scored": runs,
            "runs_off_bat": 0,
            "is_wicket": False,
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    return response.json()


async def test_phase7k_complete_school_free_acceptance_journey(
    school_client: TestClient,
) -> None:
    """Exercise the governed School Free path against the migrated PostgreSQL schema."""
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("Phase 7K production acceptance requires real PostgreSQL")

    owner = register_user(school_client, "phase7k-owner@example.com")
    organization = create_school(school_client, owner, "Phase 7K School")
    organization_id = organization["id"]

    entitlement_response = school_client.get(
        f"/api/organizations/{organization_id}/entitlements", headers=owner.headers
    )
    assert entitlement_response.status_code == 200, entitlement_response.text
    entitlement = entitlement_response.json()
    assert entitlement["plan_key"] == "school_free"
    assert set(entitlement["capabilities"]) == set(
        organization_entitlement_service.SCHOOL_FREE_CAPABILITIES
    )
    assert set(entitlement["excluded_capabilities"]) == set(
        organization_entitlement_service.SCHOOL_FREE_EXCLUDED_CAPABILITIES
    )

    existing_response = school_client.post(
        f"/api/organizations/{organization_id}/players",
        json={
            "player_name": "Retained Student",
            "student_identifier": "RET-1",
            "year_group": "Year 10",
        },
        headers=owner.headers,
    )
    assert existing_response.status_code == 201, existing_response.text
    existing = existing_response.json()
    deactivated = school_client.patch(
        f"/api/organizations/{organization_id}/players/{existing['id']}",
        json={"status": "inactive"},
        headers=owner.headers,
    )
    assert deactivated.status_code == 200

    rows: list[list[object]] = [
        ["Student Name", "ID Number", "Year"],
        ["Retained Student", "RET-1", "Year 10"],
    ]
    rows.extend([f"First Player {index}", f"A-{index}", "Year 10"] for index in range(2, 12))
    rows.extend([f"Second Player {index}", f"B-{index}", "Year 9"] for index in range(1, 12))
    upload = _xlsx(rows)

    async with session_maker() as session:
        before = {
            "profiles": await session.scalar(select(func.count(PlayerProfile.player_id))),
            "school_memberships": await session.scalar(
                select(func.count(SchoolPlayerMembership.id))
            ),
            "team_memberships": await session.scalar(
                select(func.count(SchoolTeamPlayerMembership.id))
            ),
            "users": await session.scalar(select(func.count(User.id))),
        }

    preview_response = school_client.post(
        f"/api/organizations/{organization_id}/player-imports/preview",
        files={
            "file": (
                "phase7k-roster.xlsx",
                upload,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={
            "column_mapping": json.dumps(
                {
                    "Student Name": "player_name",
                    "ID Number": "student_identifier",
                    "Year": "year_group",
                }
            )
        },
        headers=owner.headers,
    )
    assert preview_response.status_code == 201, preview_response.text
    preview = preview_response.json()
    assert preview["file_type"] == "xlsx"
    assert preview["row_count"] == 22
    duplicate = preview["rows"][0]
    assert duplicate["classification"] == "ambiguous_needs_review"
    assert duplicate["resolution_required"] is True
    assert duplicate["resolved_school_player_membership_id"] == existing["id"]

    async with session_maker() as session:
        after_preview = {
            "profiles": await session.scalar(select(func.count(PlayerProfile.player_id))),
            "school_memberships": await session.scalar(
                select(func.count(SchoolPlayerMembership.id))
            ),
            "team_memberships": await session.scalar(
                select(func.count(SchoolTeamPlayerMembership.id))
            ),
            "users": await session.scalar(select(func.count(User.id))),
        }
    assert after_preview == before

    apply_response = school_client.post(
        f"/api/organizations/{organization_id}/player-imports/{preview['import_id']}/apply",
        json={
            "resolutions": [
                {
                    "source_row_number": 2,
                    "action": "reactivate_existing",
                    "school_player_membership_id": existing["id"],
                }
            ]
        },
        headers=owner.headers,
    )
    assert apply_response.status_code == 200, apply_response.text
    applied = apply_response.json()
    assert applied["summary"]["created_players"] == 21
    assert applied["summary"]["reactivated_memberships"] == 1
    assert applied["summary"]["team_assignments_created"] == 0
    assert applied["summary"]["failed_rows"] == 0

    consumed = school_client.post(
        f"/api/organizations/{organization_id}/player-imports/{preview['import_id']}/apply",
        json={"resolutions": []},
        headers=owner.headers,
    )
    assert consumed.status_code == 409
    assert consumed.json() == {"detail": "Player import has already been applied"}

    master_roster = school_client.get(
        f"/api/organizations/{organization_id}/players", headers=owner.headers
    )
    assert master_roster.status_code == 200
    master_players = master_roster.json()
    assert len(master_players) == 22
    assert next(row for row in master_players if row["id"] == existing["id"])["status"] == "active"

    first_xi = _create_team(school_client, organization_id, owner.headers, "First XI")
    second_xi = _create_team(school_client, organization_id, owner.headers, "Second XI")
    development_xi = _create_team(school_client, organization_id, owner.headers, "Development XI")
    first_memberships = [
        row
        for row in master_players
        if row["student_identifier"] == "RET-1" or row["student_identifier"].startswith("A-")
    ]
    second_memberships = [
        row for row in master_players if row["student_identifier"].startswith("B-")
    ]
    assert len(first_memberships) == len(second_memberships) == 11
    for team, memberships in (
        (first_xi, first_memberships),
        (second_xi, second_memberships),
    ):
        for membership in memberships:
            assigned = school_client.post(
                f"/api/organizations/{organization_id}/teams/{team['id']}/players",
                json={"school_player_membership_id": membership["id"]},
                headers=owner.headers,
            )
            assert assigned.status_code == 201, assigned.text

    roster_a = school_client.get(
        f"/api/organizations/{organization_id}/teams/{first_xi['id']}/players",
        headers=owner.headers,
    ).json()
    roster_b = school_client.get(
        f"/api/organizations/{organization_id}/teams/{second_xi['id']}/players",
        headers=owner.headers,
    ).json()
    assert len(roster_a) == len(roster_b) == 11

    shared = school_client.post(
        f"/api/organizations/{organization_id}/teams/{development_xi['id']}/players",
        json={"school_player_membership_id": existing["id"]},
        headers=owner.headers,
    )
    assert shared.status_code == 201, shared.text
    assert shared.json()["player_profile_id"] == existing["player_profile_id"]
    async with session_maker() as session:
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == 22
        assert await session.scalar(select(func.count(SchoolPlayerMembership.id))) == 22
        assert await session.scalar(select(func.count(SchoolTeamPlayerMembership.id))) == 23
        assert await session.scalar(select(func.count(User.id))) == 1

    match_response = school_client.post(
        f"/api/organizations/{organization_id}/matches",
        json=_match_payload(first_xi, roster_a, second_xi, roster_b),
        headers=owner.headers,
    )
    assert match_response.status_code == 201, match_response.text
    game_id = match_response.json()["game_id"]
    outsider = register_user(school_client, "phase7k-outsider@example.com")
    assert school_client.get(f"/games/{game_id}", headers=outsider.headers).status_code == 404
    assert (
        school_client.get(f"/games/{game_id}/snapshot", headers=outsider.headers).status_code == 404
    )
    assert school_client.get(f"/public/school-scorecards/{game_id}").status_code == 404

    _start_innings(school_client, game_id, roster_a, roster_b, owner.headers)
    for _ in range(6):
        first_innings = _delivery(school_client, game_id, roster_a, roster_b, 1, owner.headers)
    assert first_innings["needs_new_innings"] is True
    _start_innings(school_client, game_id, roster_b, roster_a, owner.headers)
    _delivery(school_client, game_id, roster_b, roster_a, 4, owner.headers)
    completed = _delivery(school_client, game_id, roster_b, roster_a, 3, owner.headers)
    assert completed["is_game_over"] is True

    game_response = school_client.get(f"/games/{game_id}", headers=owner.headers)
    assert game_response.status_code == 200, game_response.text
    game_body = game_response.json()
    assert game_body["status"] == "COMPLETED"
    assert game_body["result"]["result_text"] == "Second XI won by 10 wickets"
    official_result = game_body["result"]["result_text"]
    async with session_maker() as session:
        scored_game = await session.get(Game, game_id)
        assert scored_game is not None
        frozen_team_a = dict(scored_game.team_a)
        frozen_team_b = dict(scored_game.team_b)

    result_response = school_client.get(
        f"/api/organizations/{organization_id}/results", headers=owner.headers
    )
    assert result_response.status_code == 200
    assert result_response.json()[0]["game_id"] == game_id
    assert result_response.json()[0]["result"] == official_result
    player_stats = school_client.get(
        f"/api/organizations/{organization_id}/statistics/players", headers=owner.headers
    )
    team_stats = school_client.get(
        f"/api/organizations/{organization_id}/statistics/teams", headers=owner.headers
    )
    assert player_stats.status_code == team_stats.status_code == 200
    assert {row["player_profile_id"] for row in player_stats.json()} >= {
        roster_a[0]["player_profile_id"],
        roster_b[0]["player_profile_id"],
    }
    assert {row["team_id"] for row in team_stats.json()} >= {first_xi["id"], second_xi["id"]}
    team_stats_by_id = {row["team_id"]: row for row in team_stats.json()}
    assert team_stats_by_id[first_xi["id"]]["losses"] == 1
    assert team_stats_by_id[second_xi["id"]]["wins"] == 1

    competition_response = school_client.post(
        f"/api/organizations/{organization_id}/competitions",
        json={"name": "Phase 7K Cup", "tournament_type": "league"},
        headers=owner.headers,
    )
    assert competition_response.status_code == 201, competition_response.text
    competition = competition_response.json()
    for team in (first_xi, second_xi):
        entrant = school_client.post(
            f"/api/organizations/{organization_id}/competitions/{competition['id']}/teams",
            json={"team_id": team["id"]},
            headers=owner.headers,
        )
        assert entrant.status_code == 201, entrant.text
    fixture_response = school_client.post(
        f"/api/organizations/{organization_id}/competitions/{competition['id']}/fixtures",
        json={
            "team_a_id": first_xi["id"],
            "team_b_id": second_xi["id"],
            "match_number": 1,
        },
        headers=owner.headers,
    )
    assert fixture_response.status_code == 201, fixture_response.text
    fixture = fixture_response.json()
    linked = school_client.put(
        f"/api/organizations/{organization_id}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/game",
        json={"game_id": game_id},
        headers=owner.headers,
    )
    assert linked.status_code == 200, linked.text
    standings = school_client.get(
        f"/api/organizations/{organization_id}/competitions/{competition['id']}/standings",
        headers=owner.headers,
    )
    assert standings.status_code == 200
    assert standings.json()["entries"][0]["team_id"] == second_xi["id"]
    assert standings.json()["entries"][0]["points"] == 2

    publication_url = f"/api/organizations/{organization_id}/matches/{game_id}/publication"
    published = school_client.patch(
        publication_url,
        json={"publication_state": "published_final"},
        headers=owner.headers,
    )
    assert published.status_code == 200, published.text
    public = school_client.get(f"/public/school-scorecards/{game_id}")
    assert public.status_code == 200, public.text
    assert public.json()["result"] == official_result
    serialized_public = json.dumps(public.json())
    assert "school_source" not in serialized_public
    assert "student_identifier" not in serialized_public
    assert existing["id"] not in serialized_public
    made_private = school_client.patch(
        publication_url,
        json={"publication_state": "private"},
        headers=owner.headers,
    )
    assert made_private.status_code == 200
    assert school_client.get(f"/public/school-scorecards/{game_id}").status_code == 404

    reused = school_client.post(
        f"/api/organizations/{organization_id}/matches",
        json=_match_payload(first_xi, roster_a, second_xi, roster_b),
        headers=owner.headers,
    )
    assert reused.status_code == 201, reused.text
    reused_game_id = reused.json()["game_id"]
    assert reused.json()["team_a_player_profile_ids"] == [
        row["player_profile_id"] for row in roster_a
    ]

    assert (
        school_client.patch(
            f"/api/organizations/{organization_id}/teams/{first_xi['id']}/players/{roster_a[0]['id']}",
            json={"status": "inactive"},
            headers=owner.headers,
        ).status_code
        == 200
    )
    assert (
        school_client.patch(
            f"/api/organizations/{organization_id}/players/{roster_a[0]['school_player_membership_id']}",
            json={"status": "inactive"},
            headers=owner.headers,
        ).status_code
        == 200
    )
    assert (
        school_client.delete(
            f"/api/organizations/{organization_id}/teams/{first_xi['id']}",
            headers=owner.headers,
        ).status_code
        == 204
    )

    async with session_maker() as session:
        original = await session.get(Game, game_id)
        reused_game = await session.get(Game, reused_game_id)
        stored_first_xi = await session.get(Team, first_xi["id"])
        assert original is not None and reused_game is not None and stored_first_xi is not None
        assert original.team_a == frozen_team_a
        assert original.team_b == frozen_team_b
        assert reused_game.team_a == frozen_team_a
        assert reused_game.team_b == frozen_team_b
        assert stored_first_xi.status == "archived"
        assert stored_first_xi.players == []


async def test_phase7k_exact_foreign_ids_remain_tenant_safe_across_school_resources(
    school_client: TestClient,
) -> None:
    owner_a = register_user(school_client, "phase7k-tenant-a@example.com")
    owner_b = register_user(school_client, "phase7k-tenant-b@example.com")
    school_a = create_school(school_client, owner_a, "Phase 7K Tenant A")
    school_b = create_school(school_client, owner_b, "Phase 7K Tenant B Secret")
    team_a = _create_team(school_client, school_a["id"], owner_a.headers, "Tenant A XI")
    team_b1 = _create_team(school_client, school_b["id"], owner_b.headers, "Secret First XI")
    team_b2 = _create_team(school_client, school_b["id"], owner_b.headers, "Secret Second XI")
    player_response = school_client.post(
        f"/api/organizations/{school_b['id']}/players",
        json={"player_name": "Secret Student", "student_identifier": "SECRET-1"},
        headers=owner_b.headers,
    )
    assert player_response.status_code == 201
    player_b = player_response.json()
    team_member_response = school_client.post(
        f"/api/organizations/{school_b['id']}/teams/{team_b1['id']}/players",
        json={"school_player_membership_id": player_b["id"]},
        headers=owner_b.headers,
    )
    assert team_member_response.status_code == 201
    team_member_b = team_member_response.json()
    import_response = school_client.post(
        f"/api/organizations/{school_b['id']}/player-imports/preview",
        files={"file": ("secret.csv", b"player_name\nSecret Import Player\n", "text/csv")},
        headers=owner_b.headers,
    )
    assert import_response.status_code == 201
    import_b = import_response.json()

    competition_response = school_client.post(
        f"/api/organizations/{school_b['id']}/competitions",
        json={"name": "Secret Competition", "tournament_type": "league"},
        headers=owner_b.headers,
    )
    assert competition_response.status_code == 201
    competition_b = competition_response.json()
    for team in (team_b1, team_b2):
        assert (
            school_client.post(
                f"/api/organizations/{school_b['id']}/competitions/{competition_b['id']}/teams",
                json={"team_id": team["id"]},
                headers=owner_b.headers,
            ).status_code
            == 201
        )
    fixture_response = school_client.post(
        f"/api/organizations/{school_b['id']}/competitions/{competition_b['id']}/fixtures",
        json={"team_a_id": team_b1["id"], "team_b_id": team_b2["id"]},
        headers=owner_b.headers,
    )
    assert fixture_response.status_code == 201
    fixture_b = fixture_response.json()

    game_id = str(uuid.uuid4())
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        session.add(
            Game(
                id=game_id,
                team_a={
                    "name": "Secret First XI",
                    "players": [],
                    "playing_xi": [],
                    "school_source": {
                        "organization_id": school_b["id"],
                        "team_id": team_b1["id"],
                    },
                },
                team_b={
                    "name": "Secret Second XI",
                    "players": [],
                    "playing_xi": [],
                    "school_source": {
                        "organization_id": school_b["id"],
                        "team_id": team_b2["id"],
                    },
                },
                status=GameStatus.in_progress,
                publication_state="private",
                created_by_user_id=owner_b.id,
            )
        )
        await session.commit()

    foreign_requests = [
        school_client.get(f"/api/organizations/{school_b['id']}", headers=owner_a.headers),
        school_client.get(
            f"/api/organizations/{school_b['id']}/entitlements", headers=owner_a.headers
        ),
        school_client.get(
            f"/api/organizations/{school_b['id']}/memberships", headers=owner_a.headers
        ),
        school_client.get(
            f"/api/organizations/{school_a['id']}/teams/{team_b1['id']}",
            headers=owner_a.headers,
        ),
        school_client.get(
            f"/api/organizations/{school_a['id']}/players/{player_b['id']}",
            headers=owner_a.headers,
        ),
        school_client.get(
            f"/api/organizations/{school_a['id']}/teams/{team_b1['id']}"
            f"/players/{team_member_b['id']}",
            headers=owner_a.headers,
        ),
        school_client.post(
            f"/api/organizations/{school_a['id']}/player-imports/{import_b['import_id']}/apply",
            json={"resolutions": []},
            headers=owner_a.headers,
        ),
        school_client.get(
            f"/api/organizations/{school_a['id']}/statistics/players/{player_b['player_profile_id']}",
            headers=owner_a.headers,
        ),
        school_client.get(
            f"/api/organizations/{school_a['id']}/statistics/teams/{team_b1['id']}",
            headers=owner_a.headers,
        ),
        school_client.get(
            f"/api/organizations/{school_a['id']}/competitions/{competition_b['id']}",
            headers=owner_a.headers,
        ),
        school_client.get(
            f"/api/organizations/{school_a['id']}/competitions/{competition_b['id']}"
            f"/fixtures/{fixture_b['id']}",
            headers=owner_a.headers,
        ),
        school_client.get(
            f"/api/organizations/{school_a['id']}/matches/{game_id}/publication",
            headers=owner_a.headers,
        ),
        school_client.get(f"/games/{game_id}", headers=owner_a.headers),
        school_client.get(f"/games/{game_id}/snapshot", headers=owner_a.headers),
    ]
    for response in foreign_requests:
        assert response.status_code == 404, response.text
        serialized = response.text.lower()
        assert "secret student" not in serialized
        assert "secret first xi" not in serialized
        assert "secret competition" not in serialized
        assert "phase 7k tenant b secret" not in serialized

    selection_a = [str(uuid.uuid4()) for _ in range(11)]
    selection_b = [str(uuid.uuid4()) for _ in range(11)]
    foreign_match = school_client.post(
        f"/api/organizations/{school_a['id']}/matches",
        json={
            "team_a": {
                "team_id": team_b1["id"],
                "playing_xi_membership_ids": selection_a,
                "captain_membership_id": selection_a[0],
                "wicketkeeper_membership_id": selection_a[1],
            },
            "team_b": {
                "team_id": team_a["id"],
                "playing_xi_membership_ids": selection_b,
                "captain_membership_id": selection_b[0],
                "wicketkeeper_membership_id": selection_b[1],
            },
            "match_type": "limited",
            "overs_limit": 20,
            "dls_enabled": False,
            "toss_winner_side": "team_a",
            "decision": "bat",
        },
        headers=owner_a.headers,
    )
    assert foreign_match.status_code == 404
    assert "secret" not in foreign_match.text.lower()


async def test_phase7k_maximum_allowed_csv_import_and_roster_loading_are_bounded(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("Phase 7K import performance baseline requires real PostgreSQL")

    owner = register_user(school_client, "phase7k-performance@example.com")
    organization = create_school(school_client, owner, "Phase 7K Performance School")
    content = "player_name,student_identifier,year_group\n" + "\n".join(
        f"Performance Player {index},PERF-{index},Year 10" for index in range(1, 1001)
    )

    preview_started = time.perf_counter()
    preview_response = school_client.post(
        f"/api/organizations/{organization['id']}/player-imports/preview",
        files={"file": ("maximum-roster.csv", content.encode(), "text/csv")},
        headers=owner.headers,
    )
    preview_seconds = time.perf_counter() - preview_started
    assert preview_response.status_code == 201, preview_response.text
    preview = preview_response.json()
    assert preview["row_count"] == 1000
    assert preview_seconds < 60

    async with session_maker() as session:
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == 0
        assert await session.scalar(select(func.count(SchoolPlayerMembership.id))) == 0

    apply_started = time.perf_counter()
    apply_response = school_client.post(
        f"/api/organizations/{organization['id']}/player-imports/{preview['import_id']}/apply",
        json={"resolutions": []},
        headers=owner.headers,
    )
    apply_seconds = time.perf_counter() - apply_started
    assert apply_response.status_code == 200, apply_response.text
    assert apply_response.json()["summary"]["created_players"] == 1000
    assert apply_response.json()["summary"]["failed_rows"] == 0
    assert apply_seconds < 120

    roster_started = time.perf_counter()
    roster_response = school_client.get(
        f"/api/organizations/{organization['id']}/players", headers=owner.headers
    )
    roster_seconds = time.perf_counter() - roster_started
    assert roster_response.status_code == 200
    assert len(roster_response.json()) == 1000
    assert roster_seconds < 30
    async with session_maker() as session:
        assert await session.scalar(select(func.count(PlayerProfile.player_id))) == 1000
        assert await session.scalar(select(func.count(SchoolPlayerMembership.id))) == 1000
        assert await session.scalar(select(func.count(User.id))) == 1


async def test_phase7k_entitlement_rollback_fails_closed_without_deleting_school_data(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("Phase 7K rollback rehearsal requires real PostgreSQL")

    owner = register_user(school_client, "phase7k-rollback@example.com")
    organization = create_school(school_client, owner, "Phase 7K Rollback School")
    organization_id = organization["id"]
    team = _create_team(school_client, organization_id, owner.headers, "Retained XI")
    player_response = school_client.post(
        f"/api/organizations/{organization_id}/players",
        json={"player_name": "Retained Player", "student_identifier": "ROLL-1"},
        headers=owner.headers,
    )
    assert player_response.status_code == 201
    player = player_response.json()
    game_id = str(uuid.uuid4())
    async with session_maker() as session:
        session.add(
            Game(
                id=game_id,
                team_a={
                    "name": "Retained XI",
                    "players": [],
                    "school_source": {
                        "organization_id": organization_id,
                        "team_id": team["id"],
                    },
                },
                team_b={
                    "name": "Visitors",
                    "players": [],
                    "school_source": {
                        "organization_id": organization_id,
                        "team_id": team["id"],
                    },
                },
                status=GameStatus.completed,
                result="Retained XI won by 1 run",
                publication_state="published_final",
                created_by_user_id=owner.id,
            )
        )
        await session.commit()
    public_url = f"/public/school-scorecards/{game_id}"
    assert school_client.get(public_url).status_code == 200

    async with session_maker() as session:
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization_id
            )
        )
        assert entitlement is not None
        entitlement.status = "disabled"
        await session.commit()

    blocked_team = school_client.post(
        f"/api/organizations/{organization_id}/teams",
        json={"name": "Blocked XI"},
        headers=owner.headers,
    )
    assert blocked_team.status_code == 403
    assert "school_persistent_teams" in blocked_team.text
    assert (
        school_client.get(
            f"/api/organizations/{organization_id}/players", headers=owner.headers
        ).status_code
        == 403
    )
    assert school_client.get(public_url).status_code == 404

    async with session_maker() as session:
        assert await session.get(Team, team["id"]) is not None
        retained_membership = await session.get(SchoolPlayerMembership, player["id"])
        assert retained_membership is not None
        assert retained_membership.player_profile_id == player["player_profile_id"]
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization_id
            )
        )
        assert entitlement is not None
        entitlement.status = "active"
        await session.commit()

    restored_roster = school_client.get(
        f"/api/organizations/{organization_id}/players", headers=owner.headers
    )
    assert restored_roster.status_code == 200
    assert [row["id"] for row in restored_roster.json()] == [player["id"]]
    assert school_client.get(public_url).status_code == 200
    assert (
        school_client.get(
            f"/api/organizations/{organization_id}/teams/{team['id']}",
            headers=owner.headers,
        ).status_code
        == 200
    )
