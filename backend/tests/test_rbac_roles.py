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


async def _set_user_flags(
    session_maker: async_sessionmaker,
    email: str,
    *,
    is_superuser: bool | None = None,
    role: models.RoleEnum | None = None,
) -> None:
    async with session_maker() as session:
        result = await session.execute(
            select(models.User).where(models.User.email == email)
        )
        user = result.scalar_one()
        if is_superuser is not None:
            user.is_superuser = is_superuser
        if role is not None:
            user.role = role
        await session.commit()


async def _ensure_player_profile(
    session_maker: async_sessionmaker, player_id: str
) -> None:
    async with session_maker() as session:
        existing = await session.get(models.PlayerProfile, player_id)
        if existing is None:
            profile = models.PlayerProfile(
                player_id=player_id, player_name="Test Player"
            )
            session.add(profile)
            await session.commit()


def register_user(
    client: TestClient, email: str, password: str = "secret123"
) -> dict[str, Any]:
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


@pytest.fixture
def client() -> TestClient:
    # Use the global SessionLocal and engine from backend.sql_app.database
    # This ensures we share the same in-memory DB that reset_db cleans up.
    from backend.sql_app.database import SessionLocal

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        test_client.session_maker = SessionLocal  # type: ignore[attr-defined]
        yield test_client

    fastapi_app.dependency_overrides.pop(get_db, None)


async def promote_to_superuser(client: TestClient, email: str) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _set_user_flags(session_maker, email, is_superuser=True)


async def set_role(client: TestClient, email: str, role: models.RoleEnum) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _set_user_flags(session_maker, email, role=role)


async def ensure_profile(client: TestClient, player_id: str) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _ensure_player_profile(session_maker, player_id)


def test_new_users_start_as_free(client: TestClient) -> None:
    data = register_user(client, "free@example.com")
    assert data["role"] == models.RoleEnum.free.value


async def test_superuser_can_update_roles(client: TestClient) -> None:
    admin = register_user(client, "admin@example.com")
    target = register_user(client, "member@example.com")
    await promote_to_superuser(client, "admin@example.com")
    admin_token = login_user(client, "admin@example.com")

    resp = client.post(
        f"/users/{target['id']}/role",
        json={"role": models.RoleEnum.coach_pro.value},
        headers=_auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == models.RoleEnum.coach_pro.value


def test_non_superuser_cannot_update_roles(client: TestClient) -> None:
    user = register_user(client, "user@example.com")
    target = register_user(client, "other@example.com")
    token = login_user(client, user["email"])
    resp = client.post(
        f"/users/{target['id']}/role",
        json={"role": models.RoleEnum.coach_pro.value},
        headers=_auth_headers(token),
    )
    assert resp.status_code == 403


def test_free_user_blocked_from_coach_endpoint(client: TestClient) -> None:
    register_user(client, "free-coach@example.com")
    token = login_user(client, "free-coach@example.com")

    resp = client.post(
        "/api/players/player-1/achievements",
        headers=_auth_headers(token),
        json={
            "achievement_type": "century",
            "title": "Century",
            "description": "Test",
        },
    )
    assert resp.status_code == 403


def test_free_user_blocked_from_org_endpoint(client: TestClient) -> None:
    register_user(client, "free-org@example.com")
    token = login_user(client, "free-org@example.com")
    resp = client.post(
        "/tournaments/",
        headers=_auth_headers(token),
        json={"name": "Org Cup"},
    )
    assert resp.status_code == 403


async def test_coach_user_can_award_achievement(client: TestClient) -> None:
    register_user(client, "coach@example.com")
    await set_role(client, "coach@example.com", models.RoleEnum.coach_pro)
    token = login_user(client, "coach@example.com")
    await ensure_profile(client, "player-coach")

    resp = client.post(
        "/api/players/player-coach/achievements",
        headers=_auth_headers(token),
        json={
            "achievement_type": "century",
            "title": "Century",
            "description": "Coach added",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["player_id"] == "player-coach"


async def test_org_user_can_access_coach_and_analyst_endpoints(
    client: TestClient,
) -> None:
    register_user(client, "org@example.com")
    await set_role(client, "org@example.com", models.RoleEnum.org_pro)
    token = login_user(client, "org@example.com")
    await ensure_profile(client, "player-org")

    resp_coach = client.post(
        "/api/players/player-org/achievements",
        headers=_auth_headers(token),
        json={
            "achievement_type": "century",
            "title": "Org Century",
            "description": "By org admin",
        },
    )
    assert resp_coach.status_code == 200, resp_coach.text

    resp_analyst = client.get("/api/players/leaderboard", headers=_auth_headers(token))
    assert resp_analyst.status_code == 200, resp_analyst.text
