from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.main import fastapi_app
from backend.sql_app.database import get_db


@pytest.fixture
def client() -> TestClient:
    # Use the global SessionLocal and engine from backend.sql_app.database
    from backend.sql_app.database import SessionLocal

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.pop(get_db, None)


def test_register_user(client: TestClient) -> None:
    resp = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text

    # Login to verify user details
    login_resp = client.post(
        "/auth/login",
        data={"username": "alice@example.com", "password": "secret123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]

    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200, me_resp.text
    data = me_resp.json()

    assert data["email"] == "alice@example.com"
    assert data["is_active"] is True
    assert data["is_superuser"] is False
    assert "id" in data


def test_login_returns_token(client: TestClient) -> None:
    client.post(
        "/auth/register", json={"email": "bob@example.com", "password": "hunter2"}
    )
    resp = client.post(
        "/auth/login",
        data={"username": "bob@example.com", "password": "hunter2"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]


def test_login_wrong_password(client: TestClient) -> None:
    client.post(
        "/auth/register",
        json={"email": "carol@example.com", "password": "correcthorsebatterystaple"},
    )
    resp = client.post(
        "/auth/login",
        data={"username": "carol@example.com", "password": "wrongpassword"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 401


def test_me_endpoint_requires_valid_token(client: TestClient) -> None:
    client.post(
        "/auth/register", json={"email": "dave@example.com", "password": "validpass"}
    )
    login = client.post(
        "/auth/login",
        data={"username": "dave@example.com", "password": "validpass"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "dave@example.com"
