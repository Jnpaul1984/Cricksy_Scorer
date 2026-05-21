from __future__ import annotations

import os
import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.main import fastapi_app
from backend.sql_app import models
from backend.sql_app.database import SessionLocal, get_db


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register_and_login(
    client: TestClient, email: str, password: str = "secret123"
) -> dict[str, str]:
    register_response = client.post("/auth/register", json={"email": email, "password": password})
    assert register_response.status_code == 201, register_response.text

    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200, login_response.text
    return {"email": email, "token": login_response.json()["access_token"]}


def _login_only(client: TestClient, email: str, password: str = "secret123") -> str:
    login_response = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200, login_response.text
    return login_response.json()["access_token"]


async def _set_user_role(email: str, role: models.RoleEnum) -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(models.User).where(models.User.email == email))
        user = result.scalar_one()
        user.role = role
        await session.commit()


async def _ensure_player_profile(player_id: str) -> None:
    async with SessionLocal() as session:
        profile = await session.get(models.PlayerProfile, player_id)
        if profile is None:
            session.add(
                models.PlayerProfile(player_id=player_id, player_name=f"Player {player_id}")
            )
            await session.commit()


@pytest.fixture
def client(reset_db) -> TestClient:
    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.pop(get_db, None)


async def _coach_token(client: TestClient) -> str:
    email = f"coach-{uuid.uuid4().hex[:8]}@example.com"
    _register_and_login(client, email)
    await _set_user_role(email, models.RoleEnum.coach_pro)
    return _login_only(client, email)


def _flatten_questions(template_payload: dict[str, Any]) -> dict[str, list[int]]:
    return {
        category["category"]: [q["id"] for q in category["questions"]]
        for category in template_payload["categories"]
    }


@pytest.mark.asyncio
async def test_template_retrieval_returns_all_mvp_categories(client: TestClient) -> None:
    token = await _coach_token(client)
    response = client.get("/api/mental-questionnaires/template", headers=_auth_headers(token))
    assert response.status_code == 200, response.text

    payload = response.json()
    categories = {item["category"] for item in payload["categories"]}
    assert categories == {
        "Mental Toughness",
        "Pressure Handling",
        "Game Awareness / Cricket IQ",
        "Training Habits & Discipline",
    }
    assert all(len(item["questions"]) >= 1 for item in payload["categories"])


@pytest.mark.asyncio
async def test_submission_scoring_latest_profile_and_history(client: TestClient) -> None:
    token = await _coach_token(client)
    player_id = "mental-player-001"
    await _ensure_player_profile(player_id)

    template_response = client.get(
        "/api/mental-questionnaires/template", headers=_auth_headers(token)
    )
    assert template_response.status_code == 200, template_response.text
    questions_by_category = _flatten_questions(template_response.json())

    first_payload = {
        "answers": [
            {"question_id": questions_by_category["Mental Toughness"][0], "score": 5},
            {"question_id": questions_by_category["Mental Toughness"][1], "score": 4},
            {"question_id": questions_by_category["Pressure Handling"][0], "score": 2},
            {"question_id": questions_by_category["Pressure Handling"][1], "score": 3},
            {"question_id": questions_by_category["Game Awareness / Cricket IQ"][0], "score": 4},
            {"question_id": questions_by_category["Game Awareness / Cricket IQ"][1], "score": 4},
            {"question_id": questions_by_category["Training Habits & Discipline"][0], "score": 3},
            {"question_id": questions_by_category["Training Habits & Discipline"][1], "score": 5},
        ]
    }
    first_submit = client.post(
        f"/api/mental-questionnaires/players/{player_id}/responses",
        headers=_auth_headers(token),
        json=first_payload,
    )
    assert first_submit.status_code == 200, first_submit.text
    summary = first_submit.json()

    category_scores = {
        item["category"]: item["average_score"] for item in summary["category_scores"]
    }
    assert category_scores["Mental Toughness"] == 4.5
    assert category_scores["Pressure Handling"] == 2.5
    assert category_scores["Game Awareness / Cricket IQ"] == 4.0
    assert category_scores["Training Habits & Discipline"] == 4.0
    assert summary["overall_average_score"] == 3.75

    language_blob = " ".join(
        [summary["overall_summary"], *summary["strengths"], *summary["development_areas"]]
    ).lower()
    assert "strength" in language_blob
    assert "development area" in language_blob
    for forbidden in (
        "weak mentally",
        "poor mindset",
        "bad attitude",
        "mentally fragile",
        "failure-prone",
    ):
        assert forbidden not in language_blob

    latest = client.get(
        f"/api/mental-questionnaires/players/{player_id}/profile/latest",
        headers=_auth_headers(token),
    )
    assert latest.status_code == 200
    assert latest.json()["session_id"] == summary["session_id"]

    second_payload = {
        "answers": [
            {"question_id": item["question_id"], "score": 4} for item in first_payload["answers"]
        ]
    }
    second_submit = client.post(
        f"/api/mental-questionnaires/players/{player_id}/responses",
        headers=_auth_headers(token),
        json=second_payload,
    )
    assert second_submit.status_code == 200

    history = client.get(
        f"/api/mental-questionnaires/players/{player_id}/responses",
        headers=_auth_headers(token),
    )
    assert history.status_code == 200
    entries = history.json()
    assert len(entries) == 2
    assert entries[0]["session_id"] == second_submit.json()["session_id"]
    assert entries[1]["session_id"] == summary["session_id"]


@pytest.mark.asyncio
async def test_invalid_score_outside_likert_range_rejected(client: TestClient) -> None:
    token = await _coach_token(client)
    template_response = client.get(
        "/api/mental-questionnaires/template", headers=_auth_headers(token)
    )
    question_id = template_response.json()["categories"][0]["questions"][0]["id"]

    response = client.post(
        "/api/mental-questionnaires/players/mental-player-002/responses",
        headers=_auth_headers(token),
        json={"answers": [{"question_id": question_id, "score": 6}]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_permission_enforced_for_non_coach_roles(client: TestClient) -> None:
    user = _register_and_login(client, f"free-{uuid.uuid4().hex[:8]}@example.com")
    token = user["token"]

    template_response = client.get(
        "/api/mental-questionnaires/template", headers=_auth_headers(token)
    )
    assert template_response.status_code == 403
    submit_response = client.post(
        "/api/mental-questionnaires/players/player-free/responses",
        headers=_auth_headers(token),
        json={"answers": [{"question_id": 1, "score": 3}]},
    )
    assert submit_response.status_code == 403
