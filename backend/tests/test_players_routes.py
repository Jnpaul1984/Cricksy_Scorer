from __future__ import annotations

import os

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_app.db")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "0")

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.main import fastapi_app
from backend.sql_app import models
from backend.sql_app.database import SessionLocal, engine


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _init_models() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)


async def _set_user_role(email: str, role: models.RoleEnum) -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(models.User).where(models.User.email == email))
        user = result.scalar_one()
        user.role = role
        await session.commit()


async def test_award_achievement_and_profile_flow():
    await _init_models()

    payload = {
        "game_id": None,
        "achievement_type": "century",
        "title": "Century Master",
        "description": "Scored 150 runs in a match",
        "badge_icon": "Y'",
        "metadata": {"runs": 150, "balls": 120},
    }

    with TestClient(fastapi_app) as client:
        email = "coach@example.com"
        password = "secret123"
        register_resp = client.post("/auth/register", json={"email": email, "password": password})
        assert register_resp.status_code == 201
        await _set_user_role(email, models.RoleEnum.org_pro)
        login_resp = client.post(
            "/auth/login",
            data={"username": email, "password": password},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        token = login_resp.json()["access_token"]
        headers = _auth_headers(token)

        # Awarding an achievement without an existing profile should 404
        resp = client.post(
            "/api/players/player-test-001/achievements", json=payload, headers=headers
        )
        assert resp.status_code == 404

        # Requesting achievements should return a list (empty when no data)
        resp2 = client.get("/api/players/player-test-001/achievements")
        assert resp2.status_code == 200
        assert isinstance(resp2.json(), list)

        # Leaderboard endpoint should be wired and return a valid shape
        resp3 = client.get("/api/players/leaderboard", headers=headers)
        assert resp3.status_code == 200
        data3 = resp3.json()
        assert "metric" in data3 and "entries" in data3
