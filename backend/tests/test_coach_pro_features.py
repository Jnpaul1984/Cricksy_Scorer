from __future__ import annotations

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
def client(reset_db) -> TestClient:
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


async def ensure_profile(client: TestClient, player_id: str) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _ensure_player_profile(session_maker, player_id)


async def test_non_privileged_roles_blocked(client: TestClient) -> None:
    player_id = "player-rbac"
    await ensure_profile(client, player_id)

    free_user = register_user(client, "free@example.com")
    player_user = register_user(client, "player@example.com")
    analyst_user = register_user(client, "analyst@example.com")
    await set_role(client, player_user["email"], models.RoleEnum.player_pro)
    await set_role(client, analyst_user["email"], models.RoleEnum.analyst_pro)

    payload = {
        "scheduled_at": (dt.datetime.now(UTC) + dt.timedelta(days=1)).isoformat(),
        "duration_minutes": 60,
        "focus_area": "Technique",
        "notes": None,
        "outcome": None,
    }

    for email in (free_user["email"], player_user["email"], analyst_user["email"]):
        token = login_user(client, email)
        resp_list = client.get("/api/coaches/me/players", headers=_auth_headers(token))
        assert resp_list.status_code == 403

        resp_session = client.post(
            f"/api/coaches/players/{player_id}/sessions",
            headers=_auth_headers(token),
            json=payload,
        )
        assert resp_session.status_code == 403


async def test_org_assigns_coach_and_views_assignments(client: TestClient) -> None:
    player_id = "player-assign"
    await ensure_profile(client, player_id)

    coach = register_user(client, "coach@example.com")
    await set_role(client, coach["email"], models.RoleEnum.coach_pro)

    org = register_user(client, "org@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    resp_assign = client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": coach["id"], "player_profile_id": player_id},
    )
    assert resp_assign.status_code == 200, resp_assign.text

    resp_list = client.get("/api/coaches/me/players", headers=_auth_headers(org_token))
    assert resp_list.status_code == 200
    assignments = resp_list.json()
    assert any(a["player_profile_id"] == player_id for a in assignments)


async def test_coach_manages_sessions_for_assigned_player(client: TestClient) -> None:
    player_id = "player-coach"
    await ensure_profile(client, player_id)

    coach = register_user(client, "coach-session@example.com")
    await set_role(client, coach["email"], models.RoleEnum.coach_pro)
    coach_token = login_user(client, coach["email"])

    org = register_user(client, "org-session@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    assign_resp = client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": coach["id"], "player_profile_id": player_id},
    )
    assert assign_resp.status_code == 200, assign_resp.text

    resp_players = client.get("/api/coaches/me/players", headers=_auth_headers(coach_token))
    assert resp_players.status_code == 200
    assert len(resp_players.json()) == 1

    session_payload = {
        "scheduled_at": (dt.datetime.now(UTC) + dt.timedelta(days=2)).isoformat(),
        "duration_minutes": 75,
        "focus_area": "Power hitting",
        "notes": "Track bat swing path",
        "outcome": None,
    }
    create_resp = client.post(
        f"/api/coaches/players/{player_id}/sessions",
        headers=_auth_headers(coach_token),
        json=session_payload,
    )
    assert create_resp.status_code == 200, create_resp.text
    session_id = create_resp.json()["id"]

    list_resp = client.get(
        f"/api/coaches/players/{player_id}/sessions", headers=_auth_headers(coach_token)
    )
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert len(sessions) == 1

    update_resp = client.put(
        f"/api/coaches/players/{player_id}/sessions/{session_id}",
        headers=_auth_headers(coach_token),
        json={"outcome": "Improved bat speed"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["outcome"] == "Improved bat speed"


async def test_org_creates_sessions_for_any_assigned_coach(client: TestClient) -> None:
    player_id = "player-org-session"
    await ensure_profile(client, player_id)

    coach = register_user(client, "coach-assigned@example.com")
    await set_role(client, coach["email"], models.RoleEnum.coach_pro)
    coach_id = coach["id"]

    org = register_user(client, "org-controller@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": coach_id, "player_profile_id": player_id},
    )

    payload = {
        "coach_user_id": coach_id,
        "scheduled_at": (dt.datetime.now(UTC) + dt.timedelta(days=3)).isoformat(),
        "duration_minutes": 45,
        "focus_area": "Bowling yorkers",
        "notes": None,
        "outcome": None,
    }
    create_resp = client.post(
        f"/api/coaches/players/{player_id}/sessions",
        headers=_auth_headers(org_token),
        json=payload,
    )
    assert create_resp.status_code == 200, create_resp.text
    session_id = create_resp.json()["id"]

    list_resp = client.get(
        f"/api/coaches/players/{player_id}/sessions",
        headers=_auth_headers(org_token),
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    update_resp = client.put(
        f"/api/coaches/players/{player_id}/sessions/{session_id}",
        headers=_auth_headers(org_token),
        json={"notes": "Focus on release point"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["notes"] == "Focus on release point"


async def test_coach_cannot_manage_unassigned_player(client: TestClient) -> None:
    player_one = "player-one"
    player_two = "player-two"
    await ensure_profile(client, player_one)
    await ensure_profile(client, player_two)

    coach = register_user(client, "coach-guard@example.com")
    await set_role(client, coach["email"], models.RoleEnum.coach_pro)
    coach_token = login_user(client, coach["email"])

    org = register_user(client, "org-guard@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": coach["id"], "player_profile_id": player_one},
    )

    payload = {
        "scheduled_at": (dt.datetime.now(UTC) + dt.timedelta(days=4)).isoformat(),
        "duration_minutes": 30,
        "focus_area": "Running between wickets",
        "notes": None,
        "outcome": None,
    }
    resp_unassigned = client.post(
        f"/api/coaches/players/{player_two}/sessions",
        headers=_auth_headers(coach_token),
        json=payload,
    )
    assert resp_unassigned.status_code == 403

    # Org creates a session for player one, coach should be able to update.
    create_resp = client.post(
        f"/api/coaches/players/{player_one}/sessions",
        headers=_auth_headers(org_token),
        json={
            **payload,
            "coach_user_id": coach["id"],
            "focus_area": "Shot selection",
        },
    )
    assert create_resp.status_code == 200
    session_id = create_resp.json()["id"]

    # Another coach should not be able to update this session (create second coach)
    coach_two = register_user(client, "coach-two@example.com")
    await set_role(client, coach_two["email"], models.RoleEnum.coach_pro)
    coach_two_token = login_user(client, coach_two["email"])

    resp_update = client.put(
        f"/api/coaches/players/{player_one}/sessions/{session_id}",
        headers=_auth_headers(coach_two_token),
        json={"outcome": "Should not work"},
    )
    assert resp_update.status_code == 403
