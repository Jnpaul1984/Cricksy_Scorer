from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.main import fastapi_app
from backend.sql_app import models
from backend.sql_app.database import get_db

UTC = getattr(dt, "UTC", dt.UTC)
HISTORICAL_FIXTURE_PATH = Path(__file__).resolve().parent / "simulated_t20_match.json"


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _set_user_role(
    session_maker: async_sessionmaker,
    email: str,
    role: models.RoleEnum,
) -> None:
    async with session_maker() as session:
        result = await session.execute(select(models.User).where(models.User.email == email))
        user = result.scalar_one()
        user.role = role
        await session.commit()


async def _set_user_org_id(
    session_maker: async_sessionmaker,
    email: str,
    org_id: str | None,
) -> None:
    async with session_maker() as session:
        result = await session.execute(select(models.User).where(models.User.email == email))
        user = result.scalar_one()
        user.org_id = org_id
        await session.commit()


async def _ensure_player_bundle(session_maker: async_sessionmaker, player_id: str) -> None:
    async with session_maker() as session:
        profile = await session.get(models.PlayerProfile, player_id)
        if profile is None:
            profile = models.PlayerProfile(player_id=player_id, player_name=f"Player {player_id}")
            session.add(profile)
        summary = await session.execute(
            select(models.PlayerSummary).where(models.PlayerSummary.player_id == player_id)
        )
        summary_row = summary.scalar_one_or_none()
        if summary_row is None:
            session.add(
                models.PlayerSummary(
                    player_id=player_id,
                    total_matches=12,
                    total_runs=480,
                    total_wickets=18,
                    batting_average=40.0,
                    bowling_average=25.0,
                    strike_rate=125.0,
                )
            )
        today = dt.date.today()
        session.add(
            models.PlayerForm(
                player_id=player_id,
                period_start=today - dt.timedelta(days=30),
                period_end=today,
                matches_played=6,
                runs=220,
                wickets=7,
                batting_average=44.0,
                strike_rate=135.0,
                economy=6.5,
                form_score=82.5,
            )
        )
        await session.commit()


async def _add_form_entry(
    session_maker: async_sessionmaker,
    player_id: str,
    *,
    runs: int,
    wickets: int,
    offset_days: int,
) -> None:
    today = dt.date.today()
    async with session_maker() as session:
        session.add(
            models.PlayerForm(
                player_id=player_id,
                period_start=today - dt.timedelta(days=offset_days + 7),
                period_end=today - dt.timedelta(days=offset_days),
                matches_played=3,
                runs=runs,
                wickets=wickets,
                batting_average=runs / 3,
                strike_rate=120.0,
                economy=6.8,
                form_score=75.0,
            )
        )
        await session.commit()


async def _ensure_game(session_maker: async_sessionmaker, game_id: str) -> None:
    async with session_maker() as session:
        game = await session.get(models.Game, game_id)
        if game is None:
            session.add(
                models.Game(
                    id=game_id,
                    team_a={"name": "Team A", "players": []},
                    team_b={"name": "Team B", "players": []},
                    match_type="T20",
                )
            )
            await session.commit()


async def _create_game(
    session_maker: async_sessionmaker,
    *,
    game_id: str,
    created_by_user_id: str | None,
    status: models.GameStatus,
    deliveries: list[dict[str, Any]] | None = None,
) -> None:
    async with session_maker() as session:
        game = await session.get(models.Game, game_id)
        if game is None:
            game = models.Game(
                id=game_id,
                team_a={"name": f"{game_id} Team A", "players": []},
                team_b={"name": f"{game_id} Team B", "players": []},
                match_type="T20",
            )
            session.add(game)
        game.created_by_user_id = created_by_user_id
        game.status = status
        game.deliveries = deliveries or []
        game.result = f"{game_id} result"
        await session.commit()


@pytest.fixture
def client() -> TestClient:
    # Use the global SessionLocal and engine from backend.sql_app.database
    from backend.sql_app.database import SessionLocal

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        test_client.session_maker = SessionLocal  # type: ignore[attr-defined]
        yield test_client

    fastapi_app.dependency_overrides.pop(get_db, None)


def register_user(client: TestClient, email: str, password: str = "secret123") -> dict[str, Any]:
    resp = client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text

    # Login to get full user details (ID, role, etc.)
    login_resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]

    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200, me_resp.text
    return me_resp.json()


def login_user(client: TestClient, email: str, password: str = "secret123") -> str:
    resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def set_role(client: TestClient, email: str, role: models.RoleEnum) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _set_user_role(session_maker, email, role)


async def set_user_org_id(client: TestClient, email: str, org_id: str | None) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _set_user_org_id(session_maker, email, org_id)


async def ensure_player_bundle(client: TestClient, player_id: str) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _ensure_player_bundle(session_maker, player_id)


async def ensure_game(client: TestClient, game_id: str) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _ensure_game(session_maker, game_id)


async def add_form_entry(
    client: TestClient, player_id: str, runs: int, wickets: int, offset: int
) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _add_form_entry(session_maker, player_id, runs=runs, wickets=wickets, offset_days=offset)


async def create_game(
    client: TestClient,
    *,
    game_id: str,
    created_by_user_id: str | None,
    status: models.GameStatus,
    deliveries: list[dict[str, Any]] | None = None,
) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _create_game(
        session_maker,
        game_id=game_id,
        created_by_user_id=created_by_user_id,
        status=status,
        deliveries=deliveries,
    )


async def test_role_gating_for_analyst_endpoints(client: TestClient) -> None:
    await ensure_player_bundle(client, "player-role")
    await ensure_game(client, "game-role")

    restricted_roles = [
        ("free@example.com", None),
        ("player@example.com", models.RoleEnum.player_pro),
        ("coach@example.com", models.RoleEnum.coach_pro),
    ]

    for email, role in restricted_roles:
        register_user(client, email)
        if role is not None:
            await set_role(client, email, role)
        token = login_user(client, email)
        endpoints = [
            ("GET", "/api/analyst/players/export"),
            ("GET", "/api/analyst/matches/export"),
            ("GET", "/api/analyst/player-form/export"),
            ("POST", "/api/analyst/query"),
        ]
        for method, path in endpoints:
            if method == "GET":
                resp = client.get(path, headers=_auth_headers(token))
            else:
                resp = client.post(
                    path,
                    headers=_auth_headers(token),
                    json={"entity": "players"},
                )
            assert resp.status_code == 403, f"{method} {path} should be forbidden for {email}"


async def test_analyst_exports_json_and_csv(client: TestClient) -> None:
    await ensure_player_bundle(client, "player-export")
    analyst = register_user(client, "analyst@example.com")
    await set_role(client, analyst["email"], models.RoleEnum.analyst_pro)
    analyst_token = login_user(client, analyst["email"])

    resp_json = client.get(
        "/api/analyst/players/export?format=json", headers=_auth_headers(analyst_token)
    )
    assert resp_json.status_code == 200
    data = resp_json.json()
    assert isinstance(data, list) and len(data) >= 1

    resp_csv = client.get(
        "/api/analyst/players/export?format=csv", headers=_auth_headers(analyst_token)
    )
    assert resp_csv.status_code == 200
    assert resp_csv.headers["content-type"].startswith("text/csv")
    assert "player_id" in resp_csv.text


async def test_match_and_form_exports(client: TestClient) -> None:
    await ensure_player_bundle(client, "player-form")
    await ensure_game(client, "game-form")
    org = register_user(client, "org@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    resp_matches = client.get("/api/analyst/matches/export", headers=_auth_headers(org_token))
    assert resp_matches.status_code == 200
    matches = resp_matches.json()
    assert len(matches) >= 1
    assert matches[0]["game_id"] == "game-form"

    resp_form = client.get("/api/analyst/player-form/export", headers=_auth_headers(org_token))
    assert resp_form.status_code == 200
    form_entries = resp_form.json()
    assert len(form_entries) >= 1
    assert form_entries[0]["player_id"] == "player-form"


async def test_analytics_query_form_summary(client: TestClient) -> None:
    player_id = "player-analytics"
    await ensure_player_bundle(client, player_id)
    await add_form_entry(client, player_id, runs=150, wickets=5, offset=10)
    await add_form_entry(client, player_id, runs=90, wickets=2, offset=20)

    analyst = register_user(client, "analyst-query@example.com")
    await set_role(client, analyst["email"], models.RoleEnum.analyst_pro)
    token = login_user(client, analyst["email"])

    payload = {
        "entity": "form",
        "player_id": player_id,
        "from_date": (dt.date.today() - dt.timedelta(days=40)).isoformat(),
        "to_date": dt.date.today().isoformat(),
    }
    resp = client.post("/api/analyst/query", headers=_auth_headers(token), json=payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["summary_stats"]["form_entries"] >= 3
    assert data["summary_stats"]["total_runs"] >= 220
    assert len(data["sample_rows"]) >= 1


async def test_analytics_matches_list_is_completed_and_org_scoped(client: TestClient) -> None:
    analyst_org = register_user(client, "analyst-org@example.com")
    await set_role(client, analyst_org["email"], models.RoleEnum.analyst_pro)
    await set_user_org_id(client, analyst_org["email"], "org-alpha")
    token = login_user(client, analyst_org["email"])

    analyst_other_org = register_user(client, "analyst-other@example.com")
    await set_role(client, analyst_other_org["email"], models.RoleEnum.analyst_pro)
    await set_user_org_id(client, analyst_other_org["email"], "org-beta")

    await create_game(
        client,
        game_id="completed-alpha",
        created_by_user_id=analyst_org["id"],
        status=models.GameStatus.completed,
    )
    await create_game(
        client,
        game_id="inprogress-alpha",
        created_by_user_id=analyst_org["id"],
        status=models.GameStatus.in_progress,
    )
    await create_game(
        client,
        game_id="completed-beta",
        created_by_user_id=analyst_other_org["id"],
        status=models.GameStatus.completed,
    )

    resp = client.get("/analytics/matches", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    ids = [item["id"] for item in payload["items"]]
    assert "completed-alpha" in ids
    assert "inprogress-alpha" not in ids
    assert "completed-beta" not in ids


async def test_historical_imported_match_visible_in_analyst_workspace(client: TestClient) -> None:
    analyst = register_user(client, "analyst-historical@example.com")
    await set_role(client, analyst["email"], models.RoleEnum.analyst_pro)
    token = login_user(client, analyst["email"])

    fixture_payload = json.loads(HISTORICAL_FIXTURE_PATH.read_text(encoding="utf-8"))

    dry_run_resp = client.post(
        "/api/historical-import/json/dry-run",
        headers=_auth_headers(token),
        params={"record_preview": "true"},
        json=fixture_payload,
    )
    assert dry_run_resp.status_code == 200, dry_run_resp.text
    batch_id = dry_run_resp.json()["record_id"]
    assert batch_id

    apply_resp = client.post(
        f"/api/historical-import/json/batches/{batch_id}/apply",
        headers=_auth_headers(token),
        json={"confirm": True},
    )
    assert apply_resp.status_code == 200, apply_resp.text
    game_id = apply_resp.json()["applied_game_id"]

    apply_deliveries_resp = client.post(
        f"/api/historical-import/json/batches/{batch_id}/apply-deliveries",
        headers={**_auth_headers(token), "content-type": "application/json"},
        params={"confirm": "true"},
        content=HISTORICAL_FIXTURE_PATH.read_bytes(),
    )
    assert apply_deliveries_resp.status_code == 200, apply_deliveries_resp.text

    list_resp = client.get("/analytics/matches", headers=_auth_headers(token))
    assert list_resp.status_code == 200, list_resp.text
    matches = list_resp.json()["items"]
    imported = next((item for item in matches if item["id"] == game_id), None)
    assert imported is not None, "Imported historical match must be listed in Analyst Workspace"
    assert imported["is_historical"] is True
    assert imported["source"] == "historical_import"
    assert imported["venue"] == fixture_payload.get("venue")
    # date may fall back to epoch when fixture has no explicit date field
    assert isinstance(imported["date"], str) and imported["date"] != ""

    case_study_resp = client.get(
        f"/analytics/matches/{game_id}/case-study",
        headers=_auth_headers(token),
    )
    assert case_study_resp.status_code == 200, case_study_resp.text
    detail = case_study_resp.json()
    assert detail["match"]["id"] == game_id
    assert len(detail["match"]["innings"]) >= 2
    assert len(detail["phases"]) > 0
    assert len(detail["key_players"]) > 0


async def test_analyst_export_data_real_rows_or_empty_never_fake(client: TestClient) -> None:
    analyst = register_user(client, "analyst-export-real@example.com")
    await set_role(client, analyst["email"], models.RoleEnum.analyst_pro)
    token = login_user(client, analyst["email"])

    await create_game(
        client,
        game_id="export-real",
        created_by_user_id=analyst["id"],
        status=models.GameStatus.completed,
        deliveries=[
            {
                "inning_no": 1,
                "over_number": 2,
                "ball_number": 1,
                "striker_id": "p-1",
                "bowler_id": "b-1",
                "runs_scored": 4,
                "extra_runs": 0,
                "extra_type": None,
                "is_wicket": False,
            }
        ],
    )

    resp_rows = client.get(
        "/api/analyst/export-data?match_id=export-real",
        headers=_auth_headers(token),
    )
    assert resp_rows.status_code == 200, resp_rows.text
    payload_rows = resp_rows.json()
    assert payload_rows["meta"]["row_count"] == 1
    assert payload_rows["rows"][0]["player"] == "p-1"
    text_dump = str(payload_rows)
    assert "Player A" not in text_dump and "Player B" not in text_dump and "Player C" not in text_dump

    resp_empty = client.get(
        "/api/analyst/export-data?match_id=export-real&phase=death",
        headers=_auth_headers(token),
    )
    assert resp_empty.status_code == 200
    payload_empty = resp_empty.json()
    assert payload_empty["rows"] == []
    assert payload_empty["meta"]["row_count"] == 0
    assert payload_empty["meta"]["empty_reason"] == "no_rows_for_match_or_filters"


async def test_analyst_match_detail_and_export_cross_org_blocked(client: TestClient) -> None:
    analyst_owner = register_user(client, "analyst-owner@example.com")
    await set_role(client, analyst_owner["email"], models.RoleEnum.analyst_pro)
    await set_user_org_id(client, analyst_owner["email"], "org-owner")
    owner_token = login_user(client, analyst_owner["email"])

    analyst_other = register_user(client, "analyst-other-org@example.com")
    await set_role(client, analyst_other["email"], models.RoleEnum.analyst_pro)
    await set_user_org_id(client, analyst_other["email"], "org-other")
    other_token = login_user(client, analyst_other["email"])

    await create_game(
        client,
        game_id="org-owner-match",
        created_by_user_id=analyst_owner["id"],
        status=models.GameStatus.completed,
    )

    ok_detail = client.get(
        "/api/analyst/matches/org-owner-match",
        headers=_auth_headers(owner_token),
    )
    assert ok_detail.status_code == 200
    assert ok_detail.json()["match_id"] == "org-owner-match"

    blocked_detail = client.get(
        "/api/analyst/matches/org-owner-match",
        headers=_auth_headers(other_token),
    )
    assert blocked_detail.status_code == 404

    blocked_export = client.get(
        "/api/analyst/export-data?match_id=org-owner-match",
        headers=_auth_headers(other_token),
    )
    assert blocked_export.status_code == 404
