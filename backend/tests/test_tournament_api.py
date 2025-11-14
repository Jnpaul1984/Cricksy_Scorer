"""Integration tests for tournament API endpoints"""

from __future__ import annotations

import datetime as dt

import pytest
from fastapi.testclient import TestClient

from backend.main import _fastapi as app

UTC = getattr(dt, "UTC", dt.UTC)


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as client:
        yield client


def test_create_tournament(client: TestClient):
    """Test POST /tournaments"""
    response = client.post(
        "/tournaments/",
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


def test_list_tournaments(client: TestClient):
    """Test GET /tournaments"""
    # First create a tournament
    create_resp = client.post(
        "/tournaments/",
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    assert create_resp.status_code == 201

    # List tournaments
    response = client.get("/tournaments/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_get_tournament(client: TestClient):
    """Test GET /tournaments/{id}"""
    # Create a tournament
    create_response = client.post(
        "/tournaments/",
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    # Get the tournament
    response = client.get(f"/tournaments/{tournament_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == tournament_id
    assert data["name"] == "Test League"


def test_update_tournament(client: TestClient):
    """Test PATCH /tournaments/{id}"""
    create_response = client.post(
        "/tournaments/",
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    # Update the tournament
    response = client.patch(
        f"/tournaments/{tournament_id}",
        json={
            "name": "Updated Test League",
            "status": "ongoing",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Test League"
    assert data["status"] == "ongoing"


def test_add_team_to_tournament(client: TestClient):
    """Test POST /tournaments/{id}/teams"""
    create_response = client.post(
        "/tournaments/",
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    # Add a team
    response = client.post(
        f"/tournaments/{tournament_id}/teams",
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


def test_get_teams(client: TestClient):
    """Test GET /tournaments/{id}/teams"""
    create_response = client.post(
        "/tournaments/",
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    client.post(
        f"/tournaments/{tournament_id}/teams",
        json={"team_name": "Team A", "team_data": {}},
    )
    client.post(
        f"/tournaments/{tournament_id}/teams",
        json={"team_name": "Team B", "team_data": {}},
    )

    response = client.get(f"/tournaments/{tournament_id}/teams")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


def test_create_fixture(client: TestClient):
    """Test POST /tournaments/fixtures"""
    create_response = client.post(
        "/tournaments/",
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    response = client.post(
        "/tournaments/fixtures",
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


def test_get_fixtures(client: TestClient):
    """Test GET /tournaments/{id}/fixtures"""
    create_response = client.post(
        "/tournaments/",
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    client.post(
        "/tournaments/fixtures",
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


def test_get_points_table(client: TestClient):
    """Test GET /tournaments/{id}/points-table"""
    create_response = client.post(
        "/tournaments/",
        json={
            "name": "Test League",
            "tournament_type": "league",
        },
    )
    tournament_id = create_response.json()["id"]

    client.post(
        f"/tournaments/{tournament_id}/teams",
        json={"team_name": "Team A", "team_data": {}},
    )

    response = client.get(f"/tournaments/{tournament_id}/points-table")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["team_name"] == "Team A"
    assert data[0]["points"] == 0
