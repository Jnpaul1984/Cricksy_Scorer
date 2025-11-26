"""Integration tests for tournament API endpoints"""

from __future__ import annotations

import datetime as dt
import os
import uuid

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_app.db")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "0")

from collections.abc import AsyncGenerator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.main import _fastapi as app
from backend.sql_app import models
from backend.sql_app.database import SessionLocal, engine

UTC = getattr(dt, "UTC", dt.UTC)


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


async def _register_and_login_org_user(client: TestClient) -> str:
    email = f"org-{uuid.uuid4().hex}@example.com"
    password = "secret123"
    await _init_models()
    resp = client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    await _set_user_role(email, models.RoleEnum.org_pro)
    login_resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200, login_resp.text
    return login_resp.json()["access_token"]


@pytest.fixture
async def org_client() -> AsyncGenerator[tuple[TestClient, str], None]:
    with TestClient(app) as client:
        token = await _register_and_login_org_user(client)
        yield client, token


async def test_create_tournament(org_client: tuple[TestClient, str]):
    client, token = org_client
    response = client.post(
        "/tournaments/",
        headers=_auth_headers(token),
        json={
            "name": "Test League 2024",
            "description": "A test cricket league",
            "tournament_type": "league",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test League 2024"
    assert data["tournament_type"] == "league"
    assert data["status"] == "upcoming"
    assert "id" in data


async def test_list_tournaments(org_client: tuple[TestClient, str]):
    client, token = org_client
    create_resp = client.post(
        "/tournaments/",
        headers=_auth_headers(token),
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    assert create_resp.status_code == 201

    response = client.get("/tournaments/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


async def test_get_tournament(org_client: tuple[TestClient, str]):
    client, token = org_client
    create_response = client.post(
        "/tournaments/",
        headers=_auth_headers(token),
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    response = client.get(f"/tournaments/{tournament_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tournament_id
    assert data["name"] == "Test League"


async def test_update_tournament(org_client: tuple[TestClient, str]):
    client, token = org_client
    create_response = client.post(
        "/tournaments/",
        headers=_auth_headers(token),
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    response = client.patch(
        f"/tournaments/{tournament_id}",
        headers=_auth_headers(token),
        json={
            "name": "Updated Test League",
            "status": "ongoing",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Test League"
    assert data["status"] == "ongoing"


async def test_add_team_to_tournament(org_client: tuple[TestClient, str]):
    client, token = org_client
    create_response = client.post(
        "/tournaments/",
        headers=_auth_headers(token),
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    response = client.post(
        f"/tournaments/{tournament_id}/teams",
        headers=_auth_headers(token),
        json={
            "team_name": "Mumbai Indians",
            "team_data": {"players": []},
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["team_name"] == "Mumbai Indians"
    assert data["tournament_id"] == tournament_id
    assert data["matches_played"] == 0
    assert data["points"] == 0


async def test_get_teams(org_client: tuple[TestClient, str]):
    client, token = org_client
    create_response = client.post(
        "/tournaments/",
        headers=_auth_headers(token),
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    client.post(
        f"/tournaments/{tournament_id}/teams",
        headers=_auth_headers(token),
        json={"team_name": "Team A", "team_data": {}},
    )
    client.post(
        f"/tournaments/{tournament_id}/teams",
        headers=_auth_headers(token),
        json={"team_name": "Team B", "team_data": {}},
    )

    response = client.get(f"/tournaments/{tournament_id}/teams")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


async def test_create_fixture(org_client: tuple[TestClient, str]):
    client, token = org_client
    create_response = client.post(
        "/tournaments/",
        headers=_auth_headers(token),
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    response = client.post(
        "/tournaments/fixtures",
        headers=_auth_headers(token),
        json={
            "tournament_id": tournament_id,
            "match_number": 1,
            "team_a_name": "Team A",
            "team_b_name": "Team B",
            "venue": "Test Stadium",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["match_number"] == 1
    assert data["team_a_name"] == "Team A"
    assert data["status"] == "scheduled"


async def test_get_fixtures(org_client: tuple[TestClient, str]):
    client, token = org_client
    create_response = client.post(
        "/tournaments/",
        headers=_auth_headers(token),
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    client.post(
        "/tournaments/fixtures",
        headers=_auth_headers(token),
        json={
            "tournament_id": tournament_id,
            "match_number": 1,
            "team_a_name": "Team A",
            "team_b_name": "Team B",
        },
    )

    response = client.get(f"/tournaments/{tournament_id}/fixtures")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


async def test_get_points_table(org_client: tuple[TestClient, str]):
    client, token = org_client
    create_response = client.post(
        "/tournaments/",
        headers=_auth_headers(token),
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    client.post(
        f"/tournaments/{tournament_id}/teams",
        headers=_auth_headers(token),
        json={"team_name": "Team A", "team_data": {}},
    )

    response = client.get(f"/tournaments/{tournament_id}/points-table")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["team_name"] == "Team A"
    assert data[0]["points"] == 0
