from __future__ import annotations

import asyncio
import datetime as dt
import os
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


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _run_async(coro):
    return asyncio.run(coro)


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
    session_maker: async_sessionmaker, player_id: str, *, runs: int, wickets: int, offset_days: int
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


def set_role(client: TestClient, email: str, role: models.RoleEnum) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    _run_async(_set_user_role(session_maker, email, role))


def ensure_player_bundle(client: TestClient, player_id: str) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    _run_async(_ensure_player_bundle(session_maker, player_id))


def ensure_game(client: TestClient, game_id: str) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    _run_async(_ensure_game(session_maker, game_id))


def add_form_entry(
    client: TestClient, player_id: str, runs: int, wickets: int, offset: int
) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    _run_async(
        _add_form_entry(session_maker, player_id, runs=runs, wickets=wickets, offset_days=offset)
    )


def test_role_gating_for_analyst_endpoints(client: TestClient) -> None:
    ensure_player_bundle(client, "player-role")
    ensure_game(client, "game-role")

    restricted_roles = [
        ("free@example.com", None),
        ("player@example.com", models.RoleEnum.player_pro),
        ("coach@example.com", models.RoleEnum.coach_pro),
    ]

    for email, role in restricted_roles:
        register_user(client, email)
        if role is not None:
            set_role(client, email, role)
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


def test_analyst_exports_json_and_csv(client: TestClient) -> None:
    ensure_player_bundle(client, "player-export")
    analyst = register_user(client, "analyst@example.com")
    set_role(client, analyst["email"], models.RoleEnum.analyst_pro)
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


def test_match_and_form_exports(client: TestClient) -> None:
    ensure_player_bundle(client, "player-form")
    ensure_game(client, "game-form")
    org = register_user(client, "org@example.com")
    set_role(client, org["email"], models.RoleEnum.org_pro)
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


def test_analytics_query_form_summary(client: TestClient) -> None:
    player_id = "player-analytics"
    ensure_player_bundle(client, player_id)
    add_form_entry(client, player_id, runs=150, wickets=5, offset=10)
    add_form_entry(client, player_id, runs=90, wickets=2, offset=20)

    analyst = register_user(client, "analyst-query@example.com")
    set_role(client, analyst["email"], models.RoleEnum.analyst_pro)
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
