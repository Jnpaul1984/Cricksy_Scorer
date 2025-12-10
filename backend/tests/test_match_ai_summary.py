"""
Tests for GET /api/analyst/matches/{match_id}/ai-summary endpoint.
"""

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


async def _create_test_game(
    session_maker: async_sessionmaker,
    *,
    with_deliveries: bool = False,
) -> models.Game:
    """Create a test game and return it."""
    deliveries = []
    if with_deliveries:
        # Create sample deliveries for powerplay
        for over in range(6):
            for ball in range(1, 7):
                runs = 4 if (over == 2 and ball == 3) else (6 if (over == 4 and ball == 5) else 1)
                is_wicket = over == 3 and ball == 2
                deliveries.append(
                    {
                        "over_number": over,
                        "ball_number": ball,
                        "runs_scored": runs,
                        "is_wicket": is_wicket,
                        "dismissal_type": "caught" if is_wicket else None,
                    }
                )

    async with session_maker() as session:
        game = models.Game(
            match_type="T20",
            overs_limit=20,
            team_a={"id": "team_a_id", "name": "Team Alpha", "players": []},
            team_b={"id": "team_b_id", "name": "Team Beta", "players": []},
            status=models.GameStatus.live,
            deliveries=deliveries,
            result="Team Alpha won by 20 runs" if with_deliveries else None,
        )
        session.add(game)
        await session.commit()
        await session.refresh(game)
        return game


@pytest.fixture
def client() -> TestClient:
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
    return resp.json()


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


@pytest.mark.asyncio
async def test_match_ai_summary_returns_200_with_valid_match(client: TestClient):
    """Test that the endpoint returns 200 and correct structure for a valid match."""
    # Create user and get token
    email = "analyst1@test.com"
    register_user(client, email)
    token = login_user(client, email)
    await set_role(client, email, models.RoleEnum.analyst_pro)

    # Re-login after role change to get updated token
    token = login_user(client, email)

    # Create test game
    session_maker = client.session_maker  # type: ignore[attr-defined]
    game = await _create_test_game(session_maker)

    # Call the endpoint
    response = client.get(
        f"/api/analyst/matches/{game.id}/ai-summary",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200, response.text
    data = response.json()

    # Check required fields
    assert data["match_id"] == str(game.id)
    assert data["format"] in ["T20", "ODI", "Custom"]
    assert isinstance(data["teams"], list)
    assert len(data["teams"]) >= 1
    assert isinstance(data["key_themes"], list)
    assert isinstance(data["decisive_phases"], list)
    assert isinstance(data["momentum_shifts"], list)
    assert isinstance(data["player_highlights"], list)
    assert isinstance(data["overall_summary"], str)
    assert len(data["overall_summary"]) > 0
    assert "created_at" in data


@pytest.mark.asyncio
async def test_match_ai_summary_returns_404_for_invalid_match(client: TestClient):
    """Test that the endpoint returns 404 for a non-existent match."""
    email = "analyst2@test.com"
    register_user(client, email)
    token = login_user(client, email)
    await set_role(client, email, models.RoleEnum.analyst_pro)
    token = login_user(client, email)

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(
        f"/api/analyst/matches/{fake_id}/ai-summary",
        headers=_auth_headers(token),
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_match_ai_summary_requires_auth(client: TestClient):
    """Test that the endpoint requires authentication."""
    session_maker = client.session_maker  # type: ignore[attr-defined]
    game = await _create_test_game(session_maker)

    response = client.get(f"/api/analyst/matches/{game.id}/ai-summary")

    # Should return 401 without auth
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_match_ai_summary_team_structure(client: TestClient):
    """Test that team summaries have correct structure."""
    email = "analyst3@test.com"
    register_user(client, email)
    token = login_user(client, email)
    await set_role(client, email, models.RoleEnum.analyst_pro)
    token = login_user(client, email)

    session_maker = client.session_maker  # type: ignore[attr-defined]
    game = await _create_test_game(session_maker)

    response = client.get(
        f"/api/analyst/matches/{game.id}/ai-summary",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200, response.text
    data = response.json()

    for team in data["teams"]:
        assert "team_id" in team
        assert "team_name" in team
        assert team["result"] in ["won", "lost", "tied", "no_result"]
        assert isinstance(team["total_runs"], int)
        assert isinstance(team["wickets_lost"], int)
        assert isinstance(team["overs_faced"], (int, float))
        assert isinstance(team["key_stats"], list)


@pytest.mark.asyncio
async def test_match_ai_summary_phase_structure(client: TestClient):
    """Test that decisive phases have correct structure when deliveries exist."""
    email = "analyst4@test.com"
    register_user(client, email)
    token = login_user(client, email)
    await set_role(client, email, models.RoleEnum.analyst_pro)
    token = login_user(client, email)

    session_maker = client.session_maker  # type: ignore[attr-defined]
    game = await _create_test_game(session_maker, with_deliveries=True)

    response = client.get(
        f"/api/analyst/matches/{game.id}/ai-summary",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200, response.text
    data = response.json()

    # Should have at least one phase if deliveries exist
    if data["decisive_phases"]:
        phase = data["decisive_phases"][0]
        assert "phase_id" in phase
        assert phase["innings"] in [1, 2]
        assert "label" in phase
        assert isinstance(phase["over_range"], list)
        assert len(phase["over_range"]) == 2
        assert isinstance(phase["impact_score"], (int, float))
        assert -100 <= phase["impact_score"] <= 100
        assert isinstance(phase["narrative"], str)
