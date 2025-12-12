"""Tests for admin beta user creation endpoint."""

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


async def _set_superuser(
    session_maker: async_sessionmaker,
    email: str,
) -> None:
    async with session_maker() as session:
        result = await session.execute(select(models.User).where(models.User.email == email))
        user = result.scalar_one()
        user.is_superuser = True
        await session.commit()


def register_user(client: TestClient, email: str, password: str = "secret123") -> dict[str, Any]:
    resp = client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text

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
def client(reset_db) -> TestClient:
    from backend.sql_app.database import SessionLocal

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        test_client.session_maker = SessionLocal  # type: ignore[attr-defined]
        yield test_client

    fastapi_app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_superadmin_can_create_beta_user(client: TestClient) -> None:
    """Super admin can create a beta user account."""
    # Register and promote to superadmin
    register_user(client, "admin@example.com")
    await _set_superuser(client.session_maker, "admin@example.com")  # type: ignore[attr-defined]
    token = login_user(client, "admin@example.com")

    # Create a beta user
    resp = client.post(
        "/api/admin/users",
        json={
            "email": "beta@example.com",
            "role": "player_pro",
            "plan": "player_pro",
            "org_id": "test-org-123",
            "beta_tag": "beta_phase1",
        },
        headers=_auth_headers(token),
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["email"] == "beta@example.com"
    assert data["role"] == "player_pro"
    assert data["plan"] == "player_pro"
    assert data["org_id"] == "test-org-123"
    assert data["beta_tag"] == "beta_phase1"
    assert "temp_password" in data
    assert len(data["temp_password"]) >= 12

    # Verify the created user can log in with the temp password
    login_resp = client.post(
        "/auth/login",
        data={"username": "beta@example.com", "password": data["temp_password"]},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200, login_resp.text


@pytest.mark.asyncio
async def test_superadmin_can_create_beta_user_with_custom_password(client: TestClient) -> None:
    """Super admin can create a beta user with a specific password."""
    register_user(client, "admin2@example.com")
    await _set_superuser(client.session_maker, "admin2@example.com")  # type: ignore[attr-defined]
    token = login_user(client, "admin2@example.com")

    resp = client.post(
        "/api/admin/users",
        json={
            "email": "beta2@example.com",
            "role": "coach_pro",
            "plan": "coach_pro",
            "password": "MyCustomPassword123!",
        },
        headers=_auth_headers(token),
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["temp_password"] == "MyCustomPassword123!"


@pytest.mark.asyncio
async def test_non_admin_cannot_create_beta_user(client: TestClient) -> None:
    """Non-admin users cannot access the create beta user endpoint."""
    register_user(client, "regular@example.com")
    token = login_user(client, "regular@example.com")

    resp = client.post(
        "/api/admin/users",
        json={
            "email": "should-fail@example.com",
            "role": "player_pro",
            "plan": "player_pro",
        },
        headers=_auth_headers(token),
    )

    assert resp.status_code == 403, resp.text
    assert "Super admin access required" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_cannot_create_duplicate_email(client: TestClient) -> None:
    """Cannot create a beta user with an email that already exists."""
    # Create admin and existing user
    register_user(client, "admin3@example.com")
    register_user(client, "existing@example.com")
    await _set_superuser(client.session_maker, "admin3@example.com")  # type: ignore[attr-defined]
    token = login_user(client, "admin3@example.com")

    # Try to create a beta user with the same email
    resp = client.post(
        "/api/admin/users",
        json={
            "email": "existing@example.com",
            "role": "player_pro",
            "plan": "player_pro",
        },
        headers=_auth_headers(token),
    )

    assert resp.status_code == 400, resp.text
    assert "already exists" in resp.json()["detail"]


def test_unauthenticated_cannot_create_beta_user(client: TestClient) -> None:
    """Unauthenticated requests cannot access the endpoint."""
    resp = client.post(
        "/api/admin/users",
        json={
            "email": "nope@example.com",
            "role": "player_pro",
            "plan": "player_pro",
        },
    )

    assert resp.status_code == 401, resp.text
