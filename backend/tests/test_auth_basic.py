from __future__ import annotations

import asyncio
import contextlib
import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.main import fastapi_app
from backend.sql_app import models
from backend.sql_app.database import get_db


@pytest.fixture
def client() -> TestClient:
    """Provide a TestClient backed by a temporary SQLite DB."""
    fd, path = tempfile.mkstemp()
    os.close(fd)
    database_url = f"sqlite+aiosqlite:///{path}"
    engine = create_async_engine(database_url, connect_args={"check_same_thread": False})
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(models.User.__table__.create, checkfirst=True)

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    asyncio.run(init_models())
    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.pop(get_db, None)
    asyncio.run(engine.dispose())
    with contextlib.suppress(FileNotFoundError):
        os.remove(path)


def test_register_user(client: TestClient) -> None:
    resp = client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "secret123"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["email"] == "alice@example.com"
    assert data["is_active"] is True
    assert data["is_superuser"] is False
    assert "id" in data


def test_login_returns_token(client: TestClient) -> None:
    client.post("/auth/register", json={"email": "bob@example.com", "password": "hunter2"})
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
    client.post("/auth/register", json={"email": "dave@example.com", "password": "validpass"})
    login = client.post(
        "/auth/login",
        data={"username": "dave@example.com", "password": "validpass"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    token = login.json()["access_token"]

    me = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "dave@example.com"
