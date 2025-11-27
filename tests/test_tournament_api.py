"""Legacy tournament API tests updated for auth + RBAC."""

from __future__ import annotations

import os
import uuid
from contextlib import contextmanager

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")

# Only force in-memory DB if no DATABASE_URL is present (e.g. local run without Postgres)
if "DATABASE_URL" not in os.environ:
    os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

import pytest
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


def _register_org_user(client: TestClient) -> tuple[str, dict[str, str]]:
    email = f"org-{uuid.uuid4().hex}@example.com"
    password = "secret123"
    resp = client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text

    # Login to get the token and then the user ID
    login = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    # Get user details to find the ID
    me_resp = client.get("/auth/me", headers=_auth_headers(token))
    assert me_resp.status_code == 200, me_resp.text
    user_id = me_resp.json()["id"]

    with _superuser_override():
        promote = client.post(
            f"/users/{user_id}/role",
            json={"role": models.RoleEnum.org_pro.value},
            headers=_auth_headers("fake"),
        )
        assert promote.status_code == 200, promote.text

    return user_id, _auth_headers(token)


@pytest.fixture
def org_client():
    with TestClient(fastapi_app) as client:
        _, headers = _register_org_user(client)
        yield client, headers


def test_create_tournament(org_client):
    client, headers = org_client
    response = client.post(
        "/tournaments/",
        headers=headers,
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


def test_list_tournaments(org_client):
    client, headers = org_client
    client.post(
        "/tournaments/",
        headers=headers,
        json={
            "name": "List League",
            "tournament_type": "league",
        },
    )
    response = client.get("/tournaments/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_get_tournament(org_client):
    client, headers = org_client
    create = client.post(
        "/tournaments/",
        headers=headers,
        json={
            "name": "Get League",
            "tournament_type": "league",
        },
    )
    tournament_id = create.json()["id"]

    response = client.get(f"/tournaments/{tournament_id}")
    assert response.status_code == 200
    assert response.json()["id"] == tournament_id


def test_update_tournament(org_client):
    client, headers = org_client
    create = client.post(
        "/tournaments/",
        headers=headers,
        json={
            "name": "Update League",
            "tournament_type": "league",
        },
    )
    tournament_id = create.json()["id"]

    response = client.patch(
        f"/tournaments/{tournament_id}",
        headers=headers,
        json={"name": "Updated League", "status": "ongoing"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated League"
    assert data["status"] == "ongoing"


def test_add_team_to_tournament(org_client):
    client, headers = org_client
    create = client.post(
        "/tournaments/",
        headers=headers,
        json={
            "name": "Team League",
            "tournament_type": "league",
        },
    )
    tournament_id = create.json()["id"]

    response = client.post(
        f"/tournaments/{tournament_id}/teams",
        headers=headers,
        json={"team_name": "Mumbai Indians", "team_data": {"players": []}},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["team_name"] == "Mumbai Indians"
    assert data["tournament_id"] == tournament_id
    assert data["matches_played"] == 0
    assert data["points"] == 0


def test_get_teams(org_client):
    client, headers = org_client
    create = client.post(
        "/tournaments/",
        headers=headers,
        json={
            "name": "Teams League",
            "tournament_type": "league",
        },
    )
    tournament_id = create.json()["id"]

    client.post(
        f"/tournaments/{tournament_id}/teams",
        headers=headers,
        json={"team_name": "Team A", "team_data": {}},
    )
    client.post(
        f"/tournaments/{tournament_id}/teams",
        headers=headers,
        json={"team_name": "Team B", "team_data": {}},
    )

    response = client.get(f"/tournaments/{tournament_id}/teams")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_create_fixture(org_client):
    client, headers = org_client
    create = client.post(
        "/tournaments/",
        headers=headers,
        json={
            "name": "Fixture League",
            "tournament_type": "league",
        },
    )
    tournament_id = create.json()["id"]

    response = client.post(
        "/tournaments/fixtures",
        headers=headers,
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


def test_get_fixtures(org_client):
    client, headers = org_client
    create = client.post(
        "/tournaments/",
        headers=headers,
        json={
            "name": "Fixtures League",
            "tournament_type": "league",
        },
    )
    tournament_id = create.json()["id"]

    client.post(
        "/tournaments/fixtures",
        headers=headers,
        json={
            "tournament_id": tournament_id,
            "match_number": 1,
            "team_a_name": "Team A",
            "team_b_name": "Team B",
        },
    )

    response = client.get(f"/tournaments/{tournament_id}/fixtures")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_points_table(org_client):
    client, headers = org_client
    create = client.post(
        "/tournaments/",
        headers=headers,
        json={
            "name": "Points League",
            "tournament_type": "league",
        },
    )
    tournament_id = create.json()["id"]

    client.post(
        f"/tournaments/{tournament_id}/teams",
        headers=headers,
        json={"team_name": "Team A", "team_data": {}},
    )

    response = client.get(f"/tournaments/{tournament_id}/points-table")
    assert response.status_code == 200
    table = response.json()
    assert len(table) == 1
    assert table[0]["team_name"] == "Team A"
    assert table[0]["points"] == 0
