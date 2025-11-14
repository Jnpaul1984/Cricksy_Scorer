"""Integration tests for tournament API endpoints"""
from __future__ import annotations

import datetime as dt

import pytest
from httpx import AsyncClient

from backend.main import app

UTC = getattr(dt, "UTC", dt.UTC)


@pytest.mark.asyncio
async def test_create_tournament():
    """Test POST /tournaments"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
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
        return data["id"]


@pytest.mark.asyncio
async def test_list_tournaments():
    """Test GET /tournaments"""
    # First create a tournament
    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post(
            "/tournaments/",
            json={
                "name": "Test League",
                "tournament_type": "league",
            },
        )

        # List tournaments
        response = await client.get("/tournaments/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0


@pytest.mark.asyncio
async def test_get_tournament():
    """Test GET /tournaments/{id}"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a tournament
        create_response = await client.post(
            "/tournaments/",
            json={
                "name": "Test League",
                "tournament_type": "league",
            },
        )
        tournament_id = create_response.json()["id"]

        # Get the tournament
        response = await client.get(f"/tournaments/{tournament_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tournament_id
        assert data["name"] == "Test League"


@pytest.mark.asyncio
async def test_update_tournament():
    """Test PATCH /tournaments/{id}"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a tournament
        create_response = await client.post(
            "/tournaments/",
            json={
                "name": "Test League",
                "tournament_type": "league",
            },
        )
        tournament_id = create_response.json()["id"]

        # Update the tournament
        response = await client.patch(
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


@pytest.mark.asyncio
async def test_add_team_to_tournament():
    """Test POST /tournaments/{id}/teams"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a tournament
        create_response = await client.post(
            "/tournaments/",
            json={
                "name": "Test League",
                "tournament_type": "league",
            },
        )
        tournament_id = create_response.json()["id"]

        # Add a team
        response = await client.post(
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


@pytest.mark.asyncio
async def test_get_teams():
    """Test GET /tournaments/{id}/teams"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a tournament and add teams
        create_response = await client.post(
            "/tournaments/",
            json={
                "name": "Test League",
                "tournament_type": "league",
            },
        )
        tournament_id = create_response.json()["id"]

        await client.post(
            f"/tournaments/{tournament_id}/teams",
            json={"team_name": "Team A", "team_data": {}},
        )
        await client.post(
            f"/tournaments/{tournament_id}/teams",
            json={"team_name": "Team B", "team_data": {}},
        )

        # Get teams
        response = await client.get(f"/tournaments/{tournament_id}/teams")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2


@pytest.mark.asyncio
async def test_create_fixture():
    """Test POST /tournaments/fixtures"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a tournament
        create_response = await client.post(
            "/tournaments/",
            json={
                "name": "Test League",
                "tournament_type": "league",
            },
        )
        tournament_id = create_response.json()["id"]

        # Create a fixture
        response = await client.post(
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


@pytest.mark.asyncio
async def test_get_fixtures():
    """Test GET /tournaments/{id}/fixtures"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a tournament
        create_response = await client.post(
            "/tournaments/",
            json={
                "name": "Test League",
                "tournament_type": "league",
            },
        )
        tournament_id = create_response.json()["id"]

        # Create fixtures
        await client.post(
            "/tournaments/fixtures",
            json={
                "tournament_id": tournament_id,
                "match_number": 1,
                "team_a_name": "Team A",
                "team_b_name": "Team B",
            },
        )

        # Get fixtures
        response = await client.get(f"/tournaments/{tournament_id}/fixtures")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1


@pytest.mark.asyncio
async def test_get_points_table():
    """Test GET /tournaments/{id}/points-table"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Create a tournament and add teams
        create_response = await client.post(
            "/tournaments/",
            json={
                "name": "Test League",
                "tournament_type": "league",
            },
        )
        tournament_id = create_response.json()["id"]

        await client.post(
            f"/tournaments/{tournament_id}/teams",
            json={"team_name": "Team A", "team_data": {}},
        )

        # Get points table
        response = await client.get(f"/tournaments/{tournament_id}/points-table")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["team_name"] == "Team A"
        assert data[0]["points"] == 0
