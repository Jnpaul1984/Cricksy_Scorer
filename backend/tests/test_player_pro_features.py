from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import os
import tempfile
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.main import fastapi_app
from backend.sql_app import models
from backend.sql_app.database import get_db


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _run_async(coro):
    return asyncio.run(coro)


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
        existing = await session.get(models.PlayerProfile, player_id)
        if existing is None:
            profile = models.PlayerProfile(player_id=player_id, player_name=f"Player {player_id}")
            session.add(profile)
            await session.commit()


async def _ensure_player_summary(
    session_maker: async_sessionmaker,
    player_id: str,
    **overrides: Any,
) -> models.PlayerSummary:
    defaults = {
        "total_matches": 15,
        "total_runs": 600,
        "total_wickets": 24,
        "batting_average": 40.0,
        "bowling_average": 22.5,
        "strike_rate": 135.0,
    }
    defaults.update(overrides)
    async with session_maker() as session:
        result = await session.execute(
            select(models.PlayerSummary).where(models.PlayerSummary.player_id == player_id)
        )
        summary = result.scalar_one_or_none()
        if summary is None:
            summary = models.PlayerSummary(player_id=player_id, **defaults)
            session.add(summary)
        else:
            for key, value in defaults.items():
                setattr(summary, key, value)
        await session.commit()
        await session.refresh(summary)
        return summary


async def _create_player_form_entry(
    session_maker: async_sessionmaker,
    player_id: str,
    **overrides: Any,
) -> models.PlayerForm:
    today = dt.date.today()
    defaults = {
        "period_start": overrides.pop("period_start", today - dt.timedelta(days=30)),
        "period_end": overrides.pop("period_end", today),
        "matches_played": overrides.pop("matches_played", 5),
        "runs": overrides.pop("runs", 220),
        "wickets": overrides.pop("wickets", 8),
        "batting_average": overrides.pop("batting_average", 44.0),
        "strike_rate": overrides.pop("strike_rate", 132.0),
        "economy": overrides.pop("economy", 6.2),
        "form_score": overrides.pop("form_score", 85.0),
    }
    defaults.update(overrides)
    async with session_maker() as session:
        entry = models.PlayerForm(player_id=player_id, **defaults)
        session.add(entry)
        await session.commit()
        await session.refresh(entry)
        return entry


async def _create_coaching_note(
    session_maker: async_sessionmaker,
    player_id: str,
    coach_user_id: str,
    *,
    visibility: models.PlayerCoachingNoteVisibility,
    strengths: str,
    weaknesses: str,
    action_plan: str | None = None,
) -> models.PlayerCoachingNotes:
    async with session_maker() as session:
        note = models.PlayerCoachingNotes(
            player_id=player_id,
            coach_user_id=coach_user_id,
            strengths=strengths,
            weaknesses=weaknesses,
            action_plan=action_plan,
            visibility=visibility,
        )
        session.add(note)
        await session.commit()
        await session.refresh(note)
        return note


@pytest.fixture
def client() -> TestClient:
    fd, path = tempfile.mkstemp()
    os.close(fd)
    database_url = f"sqlite+aiosqlite:///{path}"
    engine = create_async_engine(database_url, connect_args={"check_same_thread": False})
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async def init_models() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

    async def override_get_db():
        async with session_maker() as session:
            yield session

    asyncio.run(init_models())
    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        test_client.session_maker = session_maker  # type: ignore[attr-defined]
        yield test_client

    fastapi_app.dependency_overrides.pop(get_db, None)
    asyncio.run(engine.dispose())
    with contextlib.suppress(FileNotFoundError):
        os.remove(path)


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


def set_role(client: TestClient, email: str, role: models.RoleEnum) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    _run_async(_set_user_role(session_maker, email, role))


def ensure_profile(client: TestClient, player_id: str) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    _run_async(_ensure_player_profile(session_maker, player_id))


def ensure_summary(client: TestClient, player_id: str) -> models.PlayerSummary:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    return _run_async(_ensure_player_summary(session_maker, player_id))


def create_form_entry(client: TestClient, player_id: str) -> models.PlayerForm:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    return _run_async(_create_player_form_entry(session_maker, player_id))


def create_coaching_note(
    client: TestClient,
    player_id: str,
    coach_user_id: str,
    *,
    visibility: models.PlayerCoachingNoteVisibility,
    strengths: str,
    weaknesses: str,
    action_plan: str | None = None,
) -> models.PlayerCoachingNotes:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    return _run_async(
        _create_coaching_note(
            session_maker,
            player_id,
            coach_user_id,
            visibility=visibility,
            strengths=strengths,
            weaknesses=weaknesses,
            action_plan=action_plan,
        )
    )


def test_free_role_blocked_from_player_pro_endpoints(client: TestClient) -> None:
    player_id = "player-free"
    ensure_profile(client, player_id)
    ensure_summary(client, player_id)

    register_user(client, "free@example.com")
    token = login_user(client, "free@example.com")

    resp_form = client.get(f"/api/players/{player_id}/form", headers=_auth_headers(token))
    assert resp_form.status_code == 403

    resp_notes = client.get(f"/api/players/{player_id}/notes", headers=_auth_headers(token))
    assert resp_notes.status_code == 403

    resp_summary = client.get(f"/api/players/{player_id}/summary", headers=_auth_headers(token))
    assert resp_summary.status_code == 403


def test_player_role_access_summary_only(client: TestClient) -> None:
    player_id = "player-pro"
    ensure_profile(client, player_id)
    summary = ensure_summary(client, player_id)

    register_user(client, "player@example.com")
    set_role(client, "player@example.com", models.RoleEnum.player_pro)
    token = login_user(client, "player@example.com")

    resp_form = client.get(f"/api/players/{player_id}/form", headers=_auth_headers(token))
    assert resp_form.status_code == 403

    resp_notes = client.get(f"/api/players/{player_id}/notes", headers=_auth_headers(token))
    assert resp_notes.status_code == 403

    resp_summary = client.get(f"/api/players/{player_id}/summary", headers=_auth_headers(token))
    assert resp_summary.status_code == 200
    data = resp_summary.json()
    assert data["player_id"] == summary.player_id
    assert data["total_matches"] == summary.total_matches


def test_coach_role_full_access_form_and_notes(client: TestClient) -> None:
    player_id = "player-coach"
    ensure_profile(client, player_id)
    ensure_summary(client, player_id)

    register_user(client, "coach@example.com")
    set_role(client, "coach@example.com", models.RoleEnum.coach_pro)
    token = login_user(client, "coach@example.com")

    form_payload = {
        "period_start": (dt.date.today() - dt.timedelta(days=30)).isoformat(),
        "period_end": dt.date.today().isoformat(),
        "matches_played": 7,
        "runs": 310,
        "wickets": 5,
        "batting_average": 51.5,
        "strike_rate": 140.0,
        "economy": 7.1,
        "form_score": 90.0,
    }
    resp_create_form = client.post(
        f"/api/players/{player_id}/form",
        headers=_auth_headers(token),
        json=form_payload,
    )
    assert resp_create_form.status_code == 200, resp_create_form.text
    form_id = resp_create_form.json()["id"]

    resp_list_form = client.get(f"/api/players/{player_id}/form", headers=_auth_headers(token))
    assert resp_list_form.status_code == 200
    form_entries = resp_list_form.json()
    assert len(form_entries) == 1
    assert form_entries[0]["id"] == form_id

    note_payload = {
        "strengths": "Aggressive batting",
        "weaknesses": "Chasing swing bowling early",
        "action_plan": "Extra drills in nets",
        "visibility": models.PlayerCoachingNoteVisibility.private_to_coach.value,
    }
    resp_create_note = client.post(
        f"/api/players/{player_id}/notes",
        headers=_auth_headers(token),
        json=note_payload,
    )
    assert resp_create_note.status_code == 200, resp_create_note.text
    note_id = resp_create_note.json()["id"]

    update_payload = {
        "strengths": "Aggressive batting and calm temperament",
        "weaknesses": "Chasing swing bowling early",
        "action_plan": "Add video analysis session",
        "visibility": models.PlayerCoachingNoteVisibility.private_to_coach.value,
    }
    resp_update_note = client.put(
        f"/api/players/{player_id}/notes/{note_id}",
        headers=_auth_headers(token),
        json=update_payload,
    )
    assert resp_update_note.status_code == 200, resp_update_note.text
    assert resp_update_note.json()["action_plan"] == "Add video analysis session"

    resp_list_notes = client.get(f"/api/players/{player_id}/notes", headers=_auth_headers(token))
    assert resp_list_notes.status_code == 200
    notes = resp_list_notes.json()
    assert len(notes) == 1
    assert notes[0]["id"] == note_id
    assert notes[0]["visibility"] == models.PlayerCoachingNoteVisibility.private_to_coach.value

    resp_summary = client.get(f"/api/players/{player_id}/summary", headers=_auth_headers(token))
    assert resp_summary.status_code == 200


def test_analyst_role_read_only_access(client: TestClient) -> None:
    player_id = "player-analyst"
    ensure_profile(client, player_id)
    ensure_summary(client, player_id)

    coach = register_user(client, "coach-prep@example.com")
    set_role(client, "coach-prep@example.com", models.RoleEnum.coach_pro)
    create_form_entry(client, player_id)
    create_coaching_note(
        client,
        player_id,
        coach_user_id=coach["id"],
        visibility=models.PlayerCoachingNoteVisibility.org_only,
        strengths="Footwork improved",
        weaknesses="Susceptible to yorkers",
        action_plan="Work on yorker defense",
    )
    private_note = create_coaching_note(
        client,
        player_id,
        coach_user_id=coach["id"],
        visibility=models.PlayerCoachingNoteVisibility.private_to_coach,
        strengths="Leadership quality",
        weaknesses="Overthinks plans",
        action_plan="Mindfulness sessions",
    )

    analyst = register_user(client, "analyst@example.com")
    set_role(client, "analyst@example.com", models.RoleEnum.analyst_pro)
    token = login_user(client, "analyst@example.com")

    resp_form = client.get(f"/api/players/{player_id}/form", headers=_auth_headers(token))
    assert resp_form.status_code == 200
    assert len(resp_form.json()) == 1

    resp_notes = client.get(f"/api/players/{player_id}/notes", headers=_auth_headers(token))
    assert resp_notes.status_code == 200
    note_entries = resp_notes.json()
    assert len(note_entries) == 1
    assert note_entries[0]["visibility"] == models.PlayerCoachingNoteVisibility.org_only.value

    resp_summary = client.get(f"/api/players/{player_id}/summary", headers=_auth_headers(token))
    assert resp_summary.status_code == 200

    resp_form_create = client.post(
        f"/api/players/{player_id}/form",
        headers=_auth_headers(token),
        json={
            "period_start": dt.date.today().isoformat(),
            "period_end": dt.date.today().isoformat(),
            "matches_played": 1,
            "runs": 50,
            "wickets": 1,
            "batting_average": 50.0,
            "strike_rate": 150.0,
            "economy": 6.0,
            "form_score": 70.0,
        },
    )
    assert resp_form_create.status_code == 403

    resp_note_create = client.post(
        f"/api/players/{player_id}/notes",
        headers=_auth_headers(token),
        json={
            "strengths": "Test",
            "weaknesses": "Test",
            "action_plan": None,
            "visibility": models.PlayerCoachingNoteVisibility.org_only.value,
        },
    )
    assert resp_note_create.status_code == 403

    resp_note_update = client.put(
        f"/api/players/{player_id}/notes/{private_note.id}",
        headers=_auth_headers(token),
        json={
            "strengths": "Updated",
            "weaknesses": "Updated",
            "action_plan": None,
            "visibility": models.PlayerCoachingNoteVisibility.org_only.value,
        },
    )
    assert resp_note_update.status_code == 403


def test_org_role_full_access(client: TestClient) -> None:
    player_id = "player-org"
    ensure_profile(client, player_id)
    ensure_summary(client, player_id)

    register_user(client, "org@example.com")
    set_role(client, "org@example.com", models.RoleEnum.org_pro)
    token = login_user(client, "org@example.com")

    form_payload = {
        "period_start": (dt.date.today() - dt.timedelta(days=14)).isoformat(),
        "period_end": dt.date.today().isoformat(),
        "matches_played": 4,
        "runs": 180,
        "wickets": 6,
        "batting_average": 45.0,
        "strike_rate": 128.0,
        "economy": 6.5,
        "form_score": 82.0,
    }
    resp_form = client.post(
        f"/api/players/{player_id}/form", headers=_auth_headers(token), json=form_payload
    )
    assert resp_form.status_code == 200, resp_form.text

    note_payload_private = {
        "strengths": "Calm finisher",
        "weaknesses": "Limited sweep range",
        "action_plan": "Drill sweep variations",
        "visibility": models.PlayerCoachingNoteVisibility.private_to_coach.value,
    }
    resp_note_private = client.post(
        f"/api/players/{player_id}/notes",
        headers=_auth_headers(token),
        json=note_payload_private,
    )
    assert resp_note_private.status_code == 200, resp_note_private.text

    note_payload_org = {
        "strengths": "Reads bowlers well",
        "weaknesses": "Slow starter",
        "action_plan": "Powerplay rotation practice",
        "visibility": models.PlayerCoachingNoteVisibility.org_only.value,
    }
    resp_note_org = client.post(
        f"/api/players/{player_id}/notes",
        headers=_auth_headers(token),
        json=note_payload_org,
    )
    assert resp_note_org.status_code == 200

    note_id = resp_note_org.json()["id"]
    resp_update_note = client.put(
        f"/api/players/{player_id}/notes/{note_id}",
        headers=_auth_headers(token),
        json={
            **note_payload_org,
            "action_plan": "Powerplay rotation + visualization",
        },
    )
    assert resp_update_note.status_code == 200
    assert resp_update_note.json()["action_plan"] == "Powerplay rotation + visualization"

    resp_notes = client.get(f"/api/players/{player_id}/notes", headers=_auth_headers(token))
    assert resp_notes.status_code == 200
    assert len(resp_notes.json()) == 2

    resp_summary = client.get(f"/api/players/{player_id}/summary", headers=_auth_headers(token))
    assert resp_summary.status_code == 200
