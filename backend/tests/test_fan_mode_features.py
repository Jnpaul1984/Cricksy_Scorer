from __future__ import annotations

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


async def _ensure_player_profile(session_maker: async_sessionmaker, player_id: str) -> None:
    async with session_maker() as session:
        profile = await session.get(models.PlayerProfile, player_id)
        if profile is None:
            session.add(
                models.PlayerProfile(player_id=player_id, player_name=f"Player {player_id}")
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


async def ensure_player_profile(client: TestClient, player_id: str) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _ensure_player_profile(session_maker, player_id)


async def test_auth_required_for_fan_routes(client: TestClient) -> None:
    payload = {
        "home_team_name": "Home",
        "away_team_name": "Away",
        "match_type": "T20",
        "overs_limit": 20,
    }
    resp = client.post("/api/fan/matches", json=payload)
    assert resp.status_code == 401
    resp_get = client.get("/api/fan/matches")
    assert resp_get.status_code == 401
    resp_fav = client.post(
        "/api/fan/favorites", json={"favorite_type": "team", "team_id": "Team X"}
    )
    assert resp_fav.status_code == 401


async def test_fan_matches_are_user_scoped(client: TestClient) -> None:
    user_a = register_user(client, "fan-a@example.com")
    token_a = login_user(client, user_a["email"])

    match_payload = {
        "home_team_name": "Aces",
        "away_team_name": "Blazers",
        "match_type": "T20",
        "overs_limit": 15,
    }
    create_resp = client.post(
        "/api/fan/matches", headers=_auth_headers(token_a), json=match_payload
    )
    assert create_resp.status_code == 200, create_resp.text
    match_id = create_resp.json()["id"]

    list_resp = client.get("/api/fan/matches", headers=_auth_headers(token_a))
    assert list_resp.status_code == 200
    matches = list_resp.json()
    assert len(matches) == 1
    assert matches[0]["id"] == match_id

    detail_resp = client.get(f"/api/fan/matches/{match_id}", headers=_auth_headers(token_a))
    assert detail_resp.status_code == 200
    assert detail_resp.json()["home_team_name"] == "Aces"

    user_b = register_user(client, "fan-b@example.com")
    token_b = login_user(client, user_b["email"])

    list_b = client.get("/api/fan/matches", headers=_auth_headers(token_b))
    assert list_b.status_code == 200
    assert list_b.json() == []

    detail_b = client.get(f"/api/fan/matches/{match_id}", headers=_auth_headers(token_b))
    assert detail_b.status_code == 404


async def test_favorites_lifecycle_and_isolation(client: TestClient) -> None:
    await ensure_player_profile(client, "player-1")
    user = register_user(client, "fan@example.com")
    token = login_user(client, user["email"])

    fav_player = {
        "favorite_type": "player",
        "player_profile_id": "player-1",
    }
    fav_team = {
        "favorite_type": "team",
        "team_id": "Dreamers",
    }
    resp_player = client.post("/api/fan/favorites", headers=_auth_headers(token), json=fav_player)
    assert resp_player.status_code == 200, resp_player.text

    resp_team = client.post("/api/fan/favorites", headers=_auth_headers(token), json=fav_team)
    assert resp_team.status_code == 200, resp_team.text

    list_resp = client.get("/api/fan/favorites", headers=_auth_headers(token))
    assert list_resp.status_code == 200
    favorites = list_resp.json()
    assert len(favorites) == 2
    player_fav_id = next(f["id"] for f in favorites if f["favorite_type"] == "player")

    delete_resp = client.delete(f"/api/fan/favorites/{player_fav_id}", headers=_auth_headers(token))
    assert delete_resp.status_code == 204

    list_after = client.get("/api/fan/favorites", headers=_auth_headers(token))
    assert len(list_after.json()) == 1

    user_b = register_user(client, "fan2@example.com")
    token_b = login_user(client, user_b["email"])

    list_b = client.get("/api/fan/favorites", headers=_auth_headers(token_b))
    assert list_b.status_code == 200
    assert list_b.json() == []

    delete_other = client.delete(
        f"/api/fan/favorites/{player_fav_id}", headers=_auth_headers(token_b)
    )
    assert delete_other.status_code == 404
