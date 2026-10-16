"""Authorization for legacy Game routes outside the gameplay router.

Every user, organization, Game and player here is synthetic.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from backend.sql_app.models import (
    Game,
    GameContributor,
    GameContributorRoleEnum,
    GameStatus,
    OrganizationMembership,
    User,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_club,
    create_school,
    register_user,
)

OMIT = object()

OPEN_INTERRUPTION = {
    "id": "seeded-light",
    "kind": "light",
    "started_at": "2026-01-01T10:00:00+00:00",
    "ended_at": None,
    "note": "",
}


def _team(name: str, organization_id: str | None) -> dict[str, Any]:
    players = [{"id": str(uuid.uuid4()), "name": f"{name} Player {i}"} for i in range(1, 12)]
    team: dict[str, Any] = {
        "name": name,
        "players": players,
        "playing_xi": [player["id"] for player in players],
    }
    if organization_id is not None:
        team["school_source"] = {
            "organization_id": organization_id,
            "team_id": str(uuid.uuid4()),
        }
    return team


async def _insert_game(
    client: TestClient,
    *,
    organization_id: str | None,
    created_by_user_id: str | None = None,
    publication_state: str | None = None,
    match_purpose: str = "official",
    names: tuple[str, str] = ("Synthetic A", "Synthetic B"),
    with_result: bool = False,
    other_organization_id: str | None = None,
    raw_sources: tuple[Any, Any] | None = None,
) -> Game:
    team_a = _team(names[0], organization_id)
    team_b = _team(names[1], other_organization_id or organization_id)
    if raw_sources is not None:
        # Write each side's school_source verbatim; OMIT removes the key entirely.
        for team, source in zip((team_a, team_b), raw_sources, strict=True):
            team.pop("school_source", None)
            if source is not OMIT:
                team["school_source"] = source
    game_id = str(uuid.uuid4())
    result = None
    if with_result:
        result = json.dumps(
            {
                "match_id": game_id,
                "winner_team_name": names[0],
                "method": "by runs",
                "margin": 3,
                "result_text": f"{names[0]} won by 3 runs",
                "team_a_score": 120,
                "team_b_score": 117,
            }
        )
    game = Game(
        id=game_id,
        team_a=team_a,
        team_b=team_b,
        match_type="limited",
        match_purpose=match_purpose,
        overs_limit=20,
        interruptions=[dict(OPEN_INTERRUPTION)],
        toss_winner_team=team_a["name"],
        decision="bat",
        batting_team_name=team_a["name"],
        bowling_team_name=team_b["name"],
        status=GameStatus.completed if with_result else GameStatus.in_progress,
        current_inning=1,
        total_runs=42,
        total_wickets=2,
        result=result,
        publication_state=publication_state or ("private" if organization_id is not None else None),
        created_by_user_id=created_by_user_id,
    )
    async with client.session_maker() as session:  # type: ignore[attr-defined]
        session.add(game)
        await session.commit()
        await session.refresh(game)
    return game


async def _db_state(client: TestClient, game_id: str) -> dict[str, Any]:
    """Every persisted Game column plus row counts that a write could touch."""
    async with client.session_maker() as session:  # type: ignore[attr-defined]
        row = (
            (await session.execute(select(Game.__table__).where(Game.__table__.c.id == game_id)))
            .mappings()
            .one()
        )
        return {
            "game": dict(row),
            "games": await session.scalar(select(func.count()).select_from(Game)),
            "contributors": await session.scalar(select(func.count()).select_from(GameContributor)),
        }


async def _set_membership_status(
    client: TestClient, organization_id: str, user_id: str, status: str
) -> None:
    async with client.session_maker() as session:  # type: ignore[attr-defined]
        membership = await session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == user_id,
            )
        )
        assert membership is not None
        membership.status = status
        await session.commit()


async def _update_user(client: TestClient, user_id: str, **values: Any) -> None:
    async with client.session_maker() as session:  # type: ignore[attr-defined]
        user = await session.get(User, user_id)
        assert user is not None
        for key, value in values.items():
            setattr(user, key, value)
        await session.commit()


@pytest.fixture(autouse=True)
def real_sql_game_storage(school_client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Serve Games from the SQL session in SQLite runs too.

    In-memory mode replaces ``crud.get_game``/``update_game`` with a dictionary
    repository and makes the collection routes read that repository instead of SQL.
    Neither can see rows inserted through SQLAlchemy, so restore the original SQL
    implementations and disable the repository for these tests only. Depends on
    ``school_client`` so the app's own in-memory patch is applied first. PostgreSQL
    runs do not use the in-memory repository at all.
    """
    import importlib.util

    import backend.app as backend_app
    from backend.sql_app import crud

    spec = importlib.util.spec_from_file_location(
        "backend.sql_app._sql_crud_for_authz_tests", crud.__file__
    )
    assert spec is not None and spec.loader is not None
    sql_crud = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sql_crud)
    monkeypatch.setattr(crud, "get_game", sql_crud.get_game)
    monkeypatch.setattr(crud, "update_game", sql_crud.update_game)
    monkeypatch.setattr(backend_app, "_memory_repo", None)


@pytest.fixture
def broadcasts(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    """Record every broadcast the protected routes can emit."""
    from backend.main import fastapi_app

    calls: list[tuple[str, ...]] = []

    async def fake_emit_state_update(game_id: str, snapshot: dict[str, Any]) -> None:
        calls.append(("state:update", game_id))

    def fake_publish_game_update(game_id: str, payload: dict[str, Any]) -> None:
        calls.append(("game:update", game_id, str(payload.get("type"))))

    class FakeSio:
        async def emit(self, event: str, data: dict[str, Any], room: str | None = None) -> None:
            calls.append((event, str(room)))

    monkeypatch.setattr("backend.routes.game_admin.emit_state_update", fake_emit_state_update)
    monkeypatch.setattr("backend.routes.games_dls.publish_game_update", fake_publish_game_update)
    monkeypatch.setattr(fastapi_app.state, "sio", FakeSio(), raising=False)
    return calls


Body = Callable[[Game], dict[str, Any] | None]


def _xi(game: Game) -> dict[str, Any]:
    team_a = [player["id"] for player in game.team_a["players"]][:11]
    team_b = [player["id"] for player in game.team_b["players"]][:11]
    return {
        "team_a": list(reversed(team_a)),
        "team_b": team_b,
        "captain_a": team_a[1],
        "keeper_a": team_a[2],
        "captain_b": team_b[1],
        "keeper_b": team_b[2],
    }


@dataclass(frozen=True)
class Route:
    name: str
    method: str
    path: str
    body: Body
    success: int = 200
    # overs/reduce only broadcasts; it sets non-column attributes and persists nothing.
    persists: bool = True


WRITES: tuple[Route, ...] = (
    Route("overs-limit", "post", "/games/{game_id}/overs-limit", lambda g: {"overs_limit": 25}),
    Route(
        "team-roles",
        "post",
        "/games/{game_id}/team-roles",
        lambda g: {
            "side": "A",
            "captain_id": g.team_a["players"][3]["id"],
            "wicket_keeper_id": g.team_a["players"][4]["id"],
        },
    ),
    Route("playing-xi", "post", "/games/{game_id}/playing-xi", _xi),
    Route("playing_xi (alias)", "post", "/games/{game_id}/playing_xi", _xi),
    Route(
        "interruptions/start",
        "post",
        "/games/{game_id}/interruptions/start",
        lambda g: {"kind": "weather"},
    ),
    Route(
        "interruptions/stop",
        "post",
        "/games/{game_id}/interruptions/stop",
        lambda g: {"kind": "light"},
    ),
    Route(
        "interruptions (upsert)",
        "post",
        "/games/{game_id}/interruptions",
        lambda g: {"action": "start", "kind": "injury"},
    ),
    Route(
        "overs/reduce",
        "patch",
        "/games/{game_id}/overs/reduce",
        lambda g: {"innings": 2, "new_overs": 10},
        persists=False,
    ),
    Route(
        "results (POST)",
        "post",
        "/games/{game_id}/results",
        lambda g: {"match_id": g.id, "team_a_score": 99, "team_b_score": 1},
        success=201,
    ),
)
READS: tuple[Route, ...] = (
    Route("win-probability", "get", "/predictions/games/{game_id}/win-probability", lambda g: None),
    Route("interruptions (GET)", "get", "/games/{game_id}/interruptions", lambda g: None),
    Route("metrics", "get", "/games/{game_id}/metrics", lambda g: None),
    Route("results (GET)", "get", "/games/{game_id}/results", lambda g: None),
)


def _call(client: TestClient, route: Route, game: Game, actor: RegisteredUser | None):
    body = route.body(game)
    return client.request(
        route.method.upper(),
        route.path.format(game_id=game.id),
        headers=actor.headers if actor is not None else {},
        **({"json": body} if body is not None else {}),
    )


@dataclass
class OrganizationWorld:
    organization_id: str
    actors: dict[str, RegisteredUser | None]


# Explicit expected status per actor: (writes, reads). ``None`` means authorized.
EXPECTED: dict[str, tuple[int | None, int]] = {
    "anonymous": (401, 404),
    "unrelated tenant": (404, 404),
    "inactive member": (404, 404),
    "inactive user": (400, 404),
    "read-only member": (403, 200),
    "scorer": (None, 200),
    "coach": (None, 200),
    "admin": (None, 200),
    "owner": (None, 200),
}


async def _organization_world(client: TestClient, kind: str, prefix: str) -> OrganizationWorld:
    create = create_club if kind == "club" else create_school
    owner = register_user(client, f"{prefix}-owner@example.test")
    organization = create(client, owner, f"{prefix} Synthetic {kind}")
    members: dict[str, tuple[str, str]] = {
        "scorer": ("scorer", "scorer"),
        "coach": ("coach", "coach"),
        "admin": ("admin", "admin"),
        "read-only member": ("viewer", "viewer"),
        "inactive member": ("scorer", "inactive-member"),
        "inactive user": ("scorer", "inactive-user"),
    }
    actors: dict[str, RegisteredUser | None] = {"anonymous": None, "owner": owner}
    for label, (role, email) in members.items():
        user = register_user(client, f"{prefix}-{email}@example.test")
        add_membership(client, owner, organization["id"], user.id, role)
        actors[label] = user
    inactive_member = actors["inactive member"]
    inactive_user = actors["inactive user"]
    assert inactive_member is not None and inactive_user is not None
    await _set_membership_status(client, organization["id"], inactive_member.id, "disabled")
    await _update_user(client, inactive_user.id, is_active=False)
    outsider = register_user(client, f"{prefix}-outsider@example.test")
    create(client, outsider, f"{prefix} Unrelated {kind}")
    actors["unrelated tenant"] = outsider
    return OrganizationWorld(organization_id=organization["id"], actors=actors)


@pytest.mark.parametrize("kind", ["school", "club"])
@pytest.mark.parametrize("actor_label", list(EXPECTED))
async def test_route_by_actor_matrix(
    school_client: TestClient,
    broadcasts: list[tuple[str, ...]],
    kind: str,
    actor_label: str,
) -> None:
    world = await _organization_world(school_client, kind, f"{kind}-{actor_label.split()[0]}")
    actor = world.actors[actor_label]
    expected_write, expected_read = EXPECTED[actor_label]

    for route in WRITES:
        game = await _insert_game(school_client, organization_id=world.organization_id)
        before = await _db_state(school_client, game.id)
        broadcasts_before = len(broadcasts)
        response = _call(school_client, route, game, actor)
        if expected_write is None:
            assert response.status_code == route.success, (route.name, response.text)
            if route.persists:
                assert await _db_state(school_client, game.id) != before, route.name
            else:
                assert broadcasts[broadcasts_before:], route.name
        else:
            assert response.status_code == expected_write, (route.name, response.text)
            assert await _db_state(school_client, game.id) == before, route.name
            assert broadcasts[broadcasts_before:] == [], route.name

    game = await _insert_game(
        school_client, organization_id=world.organization_id, with_result=True
    )
    before = await _db_state(school_client, game.id)
    for route in READS:
        response = _call(school_client, route, game, actor)
        assert response.status_code == expected_read, (route.name, response.text)
        if expected_read == 404 and route.name == "results (GET)":
            assert response.json() == {"detail": "Results not found for the game"}
    assert await _db_state(school_client, game.id) == before

    if expected_write is not None:
        assert broadcasts == []


async def test_authorized_scorer_mutations_persist_and_broadcast(
    school_client: TestClient,
    broadcasts: list[tuple[str, ...]],
) -> None:
    world = await _organization_world(school_client, "school", "persist")
    scorer = world.actors["scorer"]
    game = await _insert_game(school_client, organization_id=world.organization_id)

    for route in WRITES:
        response = _call(school_client, route, game, scorer)
        assert response.status_code == route.success, (route.name, response.text)

    after = (await _db_state(school_client, game.id))["game"]
    assert after["overs_limit"] == 25
    assert after["team_a_captain_id"] == _xi(game)["captain_a"]
    assert set(after["team_a"]["playing_xi"]) == set(_xi(game)["team_a"])
    kinds = {(item.get("kind"), item.get("ended_at") is None) for item in after["interruptions"]}
    assert {("light", False), ("weather", True), ("injury", True)} <= kinds
    assert after["status"] in {GameStatus.completed, "completed"}
    assert json.loads(after["result"])["team_a_score"] == 99
    assert ("state:update", game.id) in broadcasts
    assert ("interruptions:update", game.id) in broadcasts
    assert ("game:update", game.id, "overs_reduced") in broadcasts


async def test_collections_hide_private_games_and_keep_published_scorecards(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "collections-owner@example.test")
    school = create_school(school_client, owner, "Collections Synthetic School")
    club_owner = register_user(school_client, "collections-club-owner@example.test")
    club = create_club(school_client, club_owner, "Collections Synthetic Club")

    legacy = await _insert_game(
        school_client,
        organization_id=None,
        names=("Legacy Lions", "Legacy Lynx"),
        with_result=True,
    )
    private_school = await _insert_game(
        school_client,
        organization_id=school["id"],
        names=("Private Hawks", "Private Herons"),
        with_result=True,
    )
    private_club = await _insert_game(
        school_client,
        organization_id=club["id"],
        names=("Private Cranes", "Private Crows"),
        with_result=True,
    )
    mixed_sources = await _insert_game(
        school_client,
        organization_id=school["id"],
        other_organization_id=club["id"],
        publication_state="published_final",
        names=("Mixed Martins", "Mixed Mynas"),
        with_result=True,
    )
    published = await _insert_game(
        school_client,
        organization_id=school["id"],
        publication_state="published_final",
        names=("Published Owls", "Published Ospreys"),
        with_result=True,
    )
    hidden = {private_school.id, private_club.id, mixed_sources.id}
    visible = {legacy.id, published.id}

    for headers in ({}, owner.headers, club_owner.headers):
        listed = school_client.get("/games/search", headers=headers)
        assert listed.status_code == 200, listed.text
        ids = {item["id"] for item in listed.json()}
        assert visible <= ids and not (hidden & ids), ids
        for term in ("Private", "Mixed"):
            filtered = school_client.get(f"/games/search?team_a={term}", headers=headers)
            assert filtered.json() == [], filtered.text

        results = school_client.get("/games/results", headers=headers)
        assert results.status_code == 200, results.text
        result_ids = {item["match_id"] for item in results.json()}
        assert visible <= result_ids and not (hidden & result_ids), result_ids
        assert "Private Hawks" not in results.text and "Private Cranes" not in results.text

    assert school_client.get(f"/public/school-scorecards/{published.id}").status_code == 200
    for game_id in hidden:
        assert school_client.get(f"/public/school-scorecards/{game_id}").status_code == 404
    assert school_client.get(f"/games/{legacy.id}/results").status_code == 200


async def test_legacy_owned_game_allows_creator_scorer_contributor_and_superuser(
    school_client: TestClient,
    broadcasts: list[tuple[str, ...]],
) -> None:
    creator = register_user(school_client, "legacy-creator@example.test")
    contributor = register_user(school_client, "legacy-contributor@example.test")
    commentator = register_user(school_client, "legacy-commentator@example.test")
    stranger = register_user(school_client, "legacy-stranger@example.test")
    superuser = register_user(school_client, "legacy-superuser@example.test")
    inactive_creator = register_user(school_client, "legacy-inactive@example.test")
    await _update_user(school_client, superuser.id, is_superuser=True)
    await _update_user(school_client, inactive_creator.id, is_active=False)
    game = await _insert_game(school_client, organization_id=None, created_by_user_id=creator.id)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        session.add_all(
            [
                GameContributor(
                    game_id=game.id, user_id=contributor.id, role=GameContributorRoleEnum.scorer
                ),
                GameContributor(
                    game_id=game.id,
                    user_id=commentator.id,
                    role=GameContributorRoleEnum.commentary,
                ),
            ]
        )
        await session.commit()

    before = await _db_state(school_client, game.id)
    for actor, expected in (
        (None, 401),
        (stranger, 403),
        (commentator, 403),
        (inactive_creator, 400),
    ):
        for route in WRITES:
            response = _call(school_client, route, game, actor)
            assert response.status_code == expected, (route.name, response.text)
    assert await _db_state(school_client, game.id) == before
    assert broadcasts == []

    for actor in (creator, contributor, superuser):
        for route in WRITES:
            fresh = await _insert_game(
                school_client, organization_id=None, created_by_user_id=creator.id
            )
            if actor is contributor:
                async with school_client.session_maker() as session:  # type: ignore[attr-defined]
                    session.add(
                        GameContributor(
                            game_id=fresh.id,
                            user_id=contributor.id,
                            role=GameContributorRoleEnum.scorer,
                        )
                    )
                    await session.commit()
            response = _call(school_client, route, fresh, actor)
            assert response.status_code == route.success, (route.name, response.text)


async def test_legacy_unowned_game_is_writable_only_by_superuser(
    school_client: TestClient,
    broadcasts: list[tuple[str, ...]],
) -> None:
    """Owner-approved policy: legacy Games with no recorded creator are superuser-only.

    Reads keep the legacy behaviour. No owner is backfilled or inferred.
    """
    any_user = register_user(school_client, "unowned-any-user@example.test")
    inactive = register_user(school_client, "unowned-inactive@example.test")
    superuser = register_user(school_client, "unowned-superuser@example.test")
    await _update_user(school_client, inactive.id, is_active=False)
    await _update_user(school_client, superuser.id, is_superuser=True)
    game = await _insert_game(school_client, organization_id=None, with_result=True)
    before = await _db_state(school_client, game.id)

    for actor, expected in ((None, 401), (any_user, 403), (inactive, 400)):
        for route in WRITES:
            response = _call(school_client, route, game, actor)
            assert response.status_code == expected, (route.name, response.text)
            if expected == 403:
                assert response.json() == {"detail": "Game has no recorded owner"}
    assert await _db_state(school_client, game.id) == before
    assert broadcasts == []

    for route in READS:
        response = _call(school_client, route, game, None)
        assert response.status_code == 200, (route.name, response.text)

    for route in WRITES:
        fresh = await _insert_game(school_client, organization_id=None)
        response = _call(school_client, route, fresh, superuser)
        assert response.status_code == route.success, (route.name, response.text)
        assert (await _db_state(school_client, fresh.id))["game"]["created_by_user_id"] is None


def _create_payload(**extra: Any) -> dict[str, Any]:
    return {
        "team_a_name": "Creator Alpha",
        "team_b_name": "Creator Beta",
        "players_a": [f"Alpha {i}" for i in range(1, 12)],
        "players_b": [f"Beta {i}" for i in range(1, 12)],
        "overs_limit": 20,
        **extra,
    }


async def test_generic_create_records_authenticated_creator_and_ignores_spoofing(
    school_client: TestClient,
    broadcasts: list[tuple[str, ...]],
) -> None:
    creator = register_user(school_client, "creator-real@example.test")
    victim = register_user(school_client, "creator-victim@example.test")
    stranger = register_user(school_client, "creator-stranger@example.test")
    inactive = register_user(school_client, "creator-inactive@example.test")
    await _update_user(school_client, inactive.id, is_active=False)
    spoof = {"created_by_user_id": victim.id, "creator_id": victim.id, "owner_id": victim.id}

    created = school_client.post("/games", json=_create_payload(**spoof), headers=creator.headers)
    assert created.status_code == 200, created.text
    owned_id = created.json()["id"]
    owned = (await _db_state(school_client, owned_id))["game"]
    assert owned["created_by_user_id"] == creator.id

    anonymous = school_client.post("/games", json=_create_payload(**spoof))
    assert anonymous.status_code == 200, anonymous.text
    assert (await _db_state(school_client, anonymous.json()["id"]))["game"][
        "created_by_user_id"
    ] is None

    bad_token = school_client.post(
        "/games",
        json=_create_payload(**spoof),
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert bad_token.status_code == 200, bad_token.text
    assert (await _db_state(school_client, bad_token.json()["id"]))["game"][
        "created_by_user_id"
    ] is None

    deactivated = school_client.post(
        "/games", json=_create_payload(**spoof), headers=inactive.headers
    )
    assert deactivated.status_code == 200, deactivated.text
    assert (await _db_state(school_client, deactivated.json()["id"]))["game"][
        "created_by_user_id"
    ] is None

    game = Game(id=owned_id, team_a=owned["team_a"], team_b=owned["team_b"])
    before = await _db_state(school_client, owned_id)
    for actor in (victim, stranger):
        for route in WRITES:
            response = _call(school_client, route, game, actor)
            assert response.status_code == 403, (route.name, response.text)
    assert await _db_state(school_client, owned_id) == before
    assert broadcasts == []

    limit = school_client.post(
        f"/games/{owned_id}/overs-limit", json={"overs_limit": 12}, headers=creator.headers
    )
    assert limit.status_code == 200, limit.text
    assert (await _db_state(school_client, owned_id))["game"]["overs_limit"] == 12


UNRESOLVED_SHAPES = {
    # name: callable(org_a, org_b) -> raw (team_a.school_source, team_b.school_source)
    "conflicting organizations": lambda a, b: (
        {"organization_id": a, "team_id": "t-a"},
        {"organization_id": b, "team_id": "t-b"},
    ),
    "one side missing organization_id": lambda a, b: (
        {"organization_id": a, "team_id": "t-a"},
        {"team_id": "t-b"},
    ),
    "one side non-string organization_id": lambda a, b: (
        {"organization_id": a, "team_id": "t-a"},
        {"organization_id": 12345, "team_id": "t-b"},
    ),
    "one side null source": lambda a, b: ({"organization_id": a, "team_id": "t-a"}, None),
    "only malformed source": lambda a, b: ({"organization_id": None}, OMIT),
}


@pytest.mark.parametrize("shape", list(UNRESOLVED_SHAPES))
async def test_unresolved_organization_ownership_is_denied_not_treated_as_legacy(
    school_client: TestClient,
    broadcasts: list[tuple[str, ...]],
    shape: str,
) -> None:
    owner_a = register_user(school_client, "unresolved-owner-a@example.test")
    school_a = create_school(school_client, owner_a, "Unresolved School A")
    owner_b = register_user(school_client, "unresolved-owner-b@example.test")
    club_b = create_club(school_client, owner_b, "Unresolved Club B")
    outsider = register_user(school_client, "unresolved-outsider@example.test")
    create_school(school_client, outsider, "Unresolved Unrelated School")
    superuser = register_user(school_client, "unresolved-superuser@example.test")
    await _update_user(school_client, superuser.id, is_superuser=True)

    game = await _insert_game(
        school_client,
        organization_id=None,
        with_result=True,
        publication_state="published_final",
        raw_sources=UNRESOLVED_SHAPES[shape](school_a["id"], club_b["id"]),
    )
    direct_reads = (
        *READS,
        Route("game (GET)", "get", "/games/{game_id}", lambda g: None),
        Route("snapshot (GET)", "get", "/games/{game_id}/snapshot", lambda g: None),
    )
    for actor in (None, outsider, owner_a, owner_b, superuser):
        for route in direct_reads:
            response = _call(school_client, route, game, actor)
            assert response.status_code == 404, (shape, route.name, response.text)

    before = await _db_state(school_client, game.id)
    for actor, expected in ((None, 401), (outsider, 404), (owner_a, 404), (owner_b, 404), (superuser, 404)):
        for route in WRITES:
            response = _call(school_client, route, game, actor)
            assert response.status_code == expected, (shape, route.name, response.text)
    assert await _db_state(school_client, game.id) == before
    assert broadcasts == []

    assert school_client.get(f"/public/school-scorecards/{game.id}").status_code == 404
    for path in ("/games/search", "/games/results"):
        assert game.id not in school_client.get(path).text, path


async def test_resolved_ownership_shapes_keep_legitimate_access(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "resolved-owner@example.test")
    school = create_school(school_client, owner, "Resolved Synthetic School")
    outsider = register_user(school_client, "resolved-outsider@example.test")
    create_school(school_client, outsider, "Resolved Unrelated School")
    source = {"organization_id": school["id"], "team_id": "t-a"}

    external_opponent = await _insert_game(
        school_client, organization_id=None, with_result=True, raw_sources=(source, OMIT)
    )
    both_sides = await _insert_game(school_client, organization_id=school["id"], with_result=True)
    legacy = await _insert_game(school_client, organization_id=None, with_result=True)
    published = await _insert_game(
        school_client,
        organization_id=school["id"],
        with_result=True,
        publication_state="published_live",
        raw_sources=(source, OMIT),
    )

    for game in (external_opponent, both_sides, published):
        for route in READS:
            assert _call(school_client, route, game, owner).status_code == 200, route.name
            assert _call(school_client, route, game, None).status_code == 404, route.name
            assert _call(school_client, route, game, outsider).status_code == 404, route.name
    for route in READS:
        assert _call(school_client, route, legacy, None).status_code == 200, route.name
    assert school_client.get(f"/public/school-scorecards/{published.id}").status_code == 200
    listed = school_client.get("/games/search").text
    assert published.id in listed and legacy.id in listed
    assert external_opponent.id not in listed and both_sides.id not in listed


async def test_generic_game_read_hides_practice_draft_from_every_actor(
    school_client: TestClient,
) -> None:
    """Practice IDs are never available through the generic Game API."""
    owner = register_user(school_client, "practice-read-owner@example.test")
    organization = create_school(school_client, owner, "Practice Read School")
    outsider = register_user(school_client, "practice-read-outsider@example.test")
    create_club(school_client, outsider, "Practice Read Other Club")
    practice = await _insert_game(
        school_client,
        organization_id=organization["id"],
        created_by_user_id=owner.id,
        match_purpose="practice",
    )
    official = await _insert_game(
        school_client,
        organization_id=organization["id"],
        created_by_user_id=owner.id,
    )

    for actor in (None, outsider, owner):
        response = _call(
            school_client,
            Route("game (GET)", "get", "/games/{game_id}", lambda _game: None),
            practice,
            actor,
        )
        assert response.status_code == 404, response.text

    assert school_client.get(f"/games/{official.id}", headers=owner.headers).status_code == 200


async def test_generic_gameplay_surface_hides_practice_from_authorized_owner(
    school_client: TestClient,
) -> None:
    """Every generic gameplay read/write must fail closed before mutation."""
    owner = register_user(school_client, "practice-gameplay-owner@example.test")
    organization = create_school(school_client, owner, "Practice Gameplay School")
    practice = await _insert_game(
        school_client,
        organization_id=organization["id"],
        created_by_user_id=owner.id,
        match_purpose="practice",
    )
    player_a = practice.team_a["players"][0]["id"]
    player_b = practice.team_b["players"][0]["id"]
    requests = (
        ("post", f"/games/{practice.id}/overs/start", {"bowler_id": player_b}),
        ("get", f"/games/{practice.id}/deliveries", None),
        ("post", f"/games/{practice.id}/overs/change_bowler", {"new_bowler_id": player_b}),
        ("post", f"/games/{practice.id}/innings/end", None),
        ("post", f"/games/{practice.id}/innings/start", {}),
        ("post", f"/games/{practice.id}/openers", {"striker_id": player_a, "non_striker_id": player_a}),
        ("post", f"/games/{practice.id}/batters/replace", {"new_batter_id": player_a}),
        ("post", f"/games/{practice.id}/next-batter", {"batter_id": player_a}),
        ("post", f"/games/{practice.id}/finalize", None),
        ("get", f"/games/{practice.id}/snapshot", None),
        ("get", f"/games/{practice.id}/recent_deliveries", None),
        (
            "post",
            f"/games/{practice.id}/deliveries",
            {
                "striker_id": player_a,
                "non_striker_id": practice.team_a["players"][1]["id"],
                "bowler_id": player_b,
                "runs_scored": 0,
            },
        ),
        ("post", f"/games/{practice.id}/undo-last", None),
        ("patch", f"/games/{practice.id}/deliveries/1", {}),
    )
    before = await _db_state(school_client, practice.id)
    for method, path, body in requests:
        response = school_client.request(method.upper(), path, headers=owner.headers, json=body)
        assert response.status_code == 404, f"{method} {path}: {response.text}"
    assert await _db_state(school_client, practice.id) == before
