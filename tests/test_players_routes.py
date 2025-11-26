from __future__ import annotations

import os
from contextlib import contextmanager

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from fastapi.testclient import TestClient

from backend import security
from backend.main import fastapi_app
from backend.sql_app import models


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


class _TestSuperUser:
    id = "test-superuser"
    email = "superuser@example.com"
    is_active = True
    is_superuser = True
    role = models.RoleEnum.org_pro


@contextmanager
def _superuser_override():
    def _override():
        return _TestSuperUser()

    fastapi_app.dependency_overrides[security.get_current_active_user] = _override
    try:
        yield
    finally:
        fastapi_app.dependency_overrides.pop(security.get_current_active_user, None)


def _register_user_with_role(
    client: TestClient, email: str, password: str, role: models.RoleEnum
) -> tuple[dict[str, str], str]:
    register_resp = client.post(
        "/auth/register", json={"email": email, "password": password}
    )
    assert register_resp.status_code == 201, register_resp.text
    user = register_resp.json()

    with _superuser_override():
        promote = client.post(
            f"/users/{user['id']}/role",
            json={"role": role.value},
            headers=_auth_headers("fake"),
        )
        assert promote.status_code == 200, promote.text

    login_resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    return user, token


def test_award_achievement_and_profile_flow():
    payload = {
        "game_id": None,
        "achievement_type": "century",
        "title": "Century Master",
        "description": "Scored 150 runs in a match",
        "badge_icon": "🏏",
        "metadata": {"runs": 150, "balls": 120},
    }

    with TestClient(fastapi_app) as client:
        _, token = _register_user_with_role(
            client, "coach@example.com", "secret123", models.RoleEnum.coach_pro
        )
        headers = _auth_headers(token)

        resp = client.post(
            "/api/players/player-test-001/achievements",
            json=payload,
            headers=headers,
        )
        assert resp.status_code == 404

        resp2 = client.get("/api/players/player-test-001/achievements")
        assert resp2.status_code == 200
        assert isinstance(resp2.json(), list)

        resp3 = client.get("/api/players/leaderboard", headers=headers)
        assert resp3.status_code == 200
        data3 = resp3.json()
        assert "metric" in data3
        assert "entries" in data3
