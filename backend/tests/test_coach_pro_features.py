from __future__ import annotations

import datetime as dt
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

UTC = getattr(dt, "UTC", dt.UTC)


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


async def _ensure_player_profile(session_maker: async_sessionmaker, player_id: str) -> None:
    async with session_maker() as session:
        profile = await session.get(models.PlayerProfile, player_id)
        if profile is None:
            session.add(
                models.PlayerProfile(player_id=player_id, player_name=f"Player {player_id}")
            )
            await session.commit()


@pytest.fixture
def client(reset_db) -> TestClient:
    # Use the global SessionLocal and engine from backend.sql_app.database
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

    # Login to get full user details (ID, role, etc.)
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


async def set_role(client: TestClient, email: str, role: models.RoleEnum) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _set_user_role(session_maker, email, role)


async def ensure_profile(client: TestClient, player_id: str) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _ensure_player_profile(session_maker, player_id)


async def test_non_privileged_roles_blocked(client: TestClient) -> None:
    player_id = "player-rbac"
    await ensure_profile(client, player_id)

    free_user = register_user(client, "free@example.com")
    player_user = register_user(client, "player@example.com")
    analyst_user = register_user(client, "analyst@example.com")
    await set_role(client, player_user["email"], models.RoleEnum.player_pro)
    await set_role(client, analyst_user["email"], models.RoleEnum.analyst_pro)

    payload = {
        "scheduled_at": (dt.datetime.now(UTC) + dt.timedelta(days=1)).isoformat(),
        "duration_minutes": 60,
        "focus_area": "Technique",
        "notes": None,
        "outcome": None,
    }

    for email in (free_user["email"], player_user["email"], analyst_user["email"]):
        token = login_user(client, email)
        resp_list = client.get("/api/coaches/me/players", headers=_auth_headers(token))
        assert resp_list.status_code == 403

        resp_session = client.post(
            f"/api/coaches/players/{player_id}/sessions",
            headers=_auth_headers(token),
            json=payload,
        )
        assert resp_session.status_code == 403


async def test_org_assigns_coach_and_views_assignments(client: TestClient) -> None:
    player_id = "player-assign"
    await ensure_profile(client, player_id)

    coach = register_user(client, "coach@example.com")
    await set_role(client, coach["email"], models.RoleEnum.coach_pro)

    org = register_user(client, "org@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    resp_assign = client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": coach["id"], "player_profile_id": player_id},
    )
    assert resp_assign.status_code == 200, resp_assign.text

    resp_list = client.get("/api/coaches/me/players", headers=_auth_headers(org_token))
    assert resp_list.status_code == 200
    assignments = resp_list.json()
    assert any(a["player_profile_id"] == player_id for a in assignments)


async def test_coach_manages_sessions_for_assigned_player(client: TestClient) -> None:
    player_id = "player-coach"
    await ensure_profile(client, player_id)

    coach = register_user(client, "coach-session@example.com")
    await set_role(client, coach["email"], models.RoleEnum.coach_pro)
    coach_token = login_user(client, coach["email"])

    org = register_user(client, "org-session@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    assign_resp = client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": coach["id"], "player_profile_id": player_id},
    )
    assert assign_resp.status_code == 200, assign_resp.text

    resp_players = client.get("/api/coaches/me/players", headers=_auth_headers(coach_token))
    assert resp_players.status_code == 200
    assert len(resp_players.json()) == 1

    session_payload = {
        "scheduled_at": (dt.datetime.now(UTC) + dt.timedelta(days=2)).isoformat(),
        "duration_minutes": 75,
        "focus_area": "Power hitting",
        "notes": "Track bat swing path",
        "outcome": None,
    }
    create_resp = client.post(
        f"/api/coaches/players/{player_id}/sessions",
        headers=_auth_headers(coach_token),
        json=session_payload,
    )
    assert create_resp.status_code == 200, create_resp.text
    session_id = create_resp.json()["id"]

    list_resp = client.get(
        f"/api/coaches/players/{player_id}/sessions", headers=_auth_headers(coach_token)
    )
    assert list_resp.status_code == 200
    sessions = list_resp.json()
    assert len(sessions) == 1

    update_resp = client.put(
        f"/api/coaches/players/{player_id}/sessions/{session_id}",
        headers=_auth_headers(coach_token),
        json={"outcome": "Improved bat speed"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["outcome"] == "Improved bat speed"


async def test_org_creates_sessions_for_any_assigned_coach(client: TestClient) -> None:
    player_id = "player-org-session"
    await ensure_profile(client, player_id)

    coach = register_user(client, "coach-assigned@example.com")
    await set_role(client, coach["email"], models.RoleEnum.coach_pro)
    coach_id = coach["id"]

    org = register_user(client, "org-controller@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": coach_id, "player_profile_id": player_id},
    )

    payload = {
        "coach_user_id": coach_id,
        "scheduled_at": (dt.datetime.now(UTC) + dt.timedelta(days=3)).isoformat(),
        "duration_minutes": 45,
        "focus_area": "Bowling yorkers",
        "notes": None,
        "outcome": None,
    }
    create_resp = client.post(
        f"/api/coaches/players/{player_id}/sessions",
        headers=_auth_headers(org_token),
        json=payload,
    )
    assert create_resp.status_code == 200, create_resp.text
    session_id = create_resp.json()["id"]

    list_resp = client.get(
        f"/api/coaches/players/{player_id}/sessions",
        headers=_auth_headers(org_token),
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    update_resp = client.put(
        f"/api/coaches/players/{player_id}/sessions/{session_id}",
        headers=_auth_headers(org_token),
        json={"notes": "Focus on release point"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["notes"] == "Focus on release point"


async def test_coach_cannot_manage_unassigned_player(client: TestClient) -> None:
    player_one = "player-one"
    player_two = "player-two"
    await ensure_profile(client, player_one)
    await ensure_profile(client, player_two)

    coach = register_user(client, "coach-guard@example.com")
    await set_role(client, coach["email"], models.RoleEnum.coach_pro)
    coach_token = login_user(client, coach["email"])

    org = register_user(client, "org-guard@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": coach["id"], "player_profile_id": player_one},
    )

    payload = {
        "scheduled_at": (dt.datetime.now(UTC) + dt.timedelta(days=4)).isoformat(),
        "duration_minutes": 30,
        "focus_area": "Running between wickets",
        "notes": None,
        "outcome": None,
    }
    resp_unassigned = client.post(
        f"/api/coaches/players/{player_two}/sessions",
        headers=_auth_headers(coach_token),
        json=payload,
    )
    assert resp_unassigned.status_code == 403

    # Org creates a session for player one, coach should be able to update.
    create_resp = client.post(
        f"/api/coaches/players/{player_one}/sessions",
        headers=_auth_headers(org_token),
        json={
            **payload,
            "coach_user_id": coach["id"],
            "focus_area": "Shot selection",
        },
    )
    assert create_resp.status_code == 200
    session_id = create_resp.json()["id"]

    # Another coach should not be able to update this session (create second coach)
    coach_two = register_user(client, "coach-two@example.com")
    await set_role(client, coach_two["email"], models.RoleEnum.coach_pro)
    coach_two_token = login_user(client, coach_two["email"])

    resp_update = client.put(
        f"/api/coaches/players/{player_one}/sessions/{session_id}",
        headers=_auth_headers(coach_two_token),
        json={"outcome": "Should not work"},
    )
    assert resp_update.status_code == 403


@pytest.mark.asyncio
async def test_analysis_history_endpoint(client: TestClient):
    """Test GET /video-sessions/{session_id}/analysis-history endpoint."""
    # Register and upgrade user to coach_pro_plus
    user = register_user(client, "coach-video@example.com")
    await set_role(client, user["email"], models.RoleEnum.coach_pro_plus)
    token = login_user(client, user["email"])
    headers = _auth_headers(token)

    # Create a video session
    session_resp = client.post(
        "/api/coaches/plus/sessions",
        headers=headers,
        json={"title": "Test Session", "player_ids": [], "notes": "Test notes"},
    )
    assert session_resp.status_code == 200, session_resp.text
    session_id = session_resp.json()["id"]

    # Initially, history should be empty
    history_resp = client.get(
        f"/api/coaches/plus/video-sessions/{session_id}/analysis-history",
        headers=headers,
    )
    assert history_resp.status_code == 200, history_resp.text
    history = history_resp.json()
    assert isinstance(history, list)
    assert len(history) == 0

    # Create an analysis job manually for testing
    from datetime import datetime, timezone

    from backend.sql_app.database import SessionLocal

    async with SessionLocal() as db:
        job = models.VideoAnalysisJob(
            session_id=session_id,
            sample_fps=10,
            include_frames=False,
            status=models.VideoAnalysisJobStatus.completed,
            quick_results={"pose_summary": {"detection_rate_percent": 95}},
            quick_findings={"key_issues": ["balance", "follow_through"]},
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        job1_id = job.id

    # Now history should have 1 job
    history_resp = client.get(
        f"/api/coaches/plus/video-sessions/{session_id}/analysis-history",
        headers=headers,
    )
    assert history_resp.status_code == 200, history_resp.text
    history = history_resp.json()
    assert len(history) == 1
    assert history[0]["session_id"] == session_id
    assert history[0]["status"] == "completed"
    assert "quick_results" in history[0]
    assert "quick_findings" in history[0]

    # Verify ordered by created_at desc (newest first)
    async with SessionLocal() as db:
        # Fetch the first job and modify its created_at to be older
        result = await db.execute(
            select(models.VideoAnalysisJob).where(models.VideoAnalysisJob.id == job1_id)
        )
        job1 = result.scalar_one()
        job1.created_at = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

        # Create second job with newer timestamp
        job2 = models.VideoAnalysisJob(
            session_id=session_id,
            sample_fps=10,
            include_frames=False,
            status=models.VideoAnalysisJobStatus.done,
        )
        job2.created_at = datetime(2024, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
        db.add(job2)
        await db.commit()
        await db.refresh(job2)
        job2_id = job2.id

    history_resp = client.get(
        f"/api/coaches/plus/video-sessions/{session_id}/analysis-history",
        headers=headers,
    )
    assert history_resp.status_code == 200, history_resp.text
    history = history_resp.json()
    assert len(history) == 2
    # Newest (job2) should be first
    assert history[0]["id"] == job2_id
    assert history[1]["id"] == job1_id


@pytest.mark.asyncio
async def test_repetition_and_phase_retrieval_endpoints_are_authorized_and_legacy_safe(
    client: TestClient,
) -> None:
    coach = register_user(client, "coach-repetitions@example.com")
    intruder = register_user(client, "coach-repetitions-intruder@example.com")
    await set_role(client, coach["email"], models.RoleEnum.coach_pro_plus)
    await set_role(client, intruder["email"], models.RoleEnum.coach_pro_plus)
    coach_token = login_user(client, coach["email"])
    intruder_token = login_user(client, intruder["email"])

    session_resp = client.post(
        "/api/coaches/plus/sessions",
        headers=_auth_headers(coach_token),
        json={"title": "Repetition Session", "analysis_context": "bowling", "camera_view": "side"},
    )
    assert session_resp.status_code == 200, session_resp.text
    session_id = session_resp.json()["id"]

    session_maker = client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as db:
        segmented_job = models.VideoAnalysisJob(
            session_id=session_id,
            sample_fps=10,
            include_frames=False,
            status=models.VideoAnalysisJobStatus.done,
            deep_results={
                "meta": {
                    "repetition_segmentation": {
                        "enabled": True,
                        "discipline": "bowling",
                        "segmentation_method": "pose_motion_ball_hybrid_v1",
                        "validity_state": "VALID",
                        "segmentation_confidence": 0.84,
                        "repetitions_count": 1,
                        "insufficient_reason": None,
                    },
                    "phase_recognition": {
                        "enabled": True,
                        "discipline": "pace_bowling",
                        "detection_method": "repetition_relative_heuristic_v1",
                        "validity_state": "LOW_CONFIDENCE",
                        "phases_count": 1,
                        "recognized_repetitions": 1,
                        "insufficient_reason": None,
                    },
                },
                "v2": {
                    "repetitions": [
                        {
                            "schema_version": "coach_analysis_v2.contract.v1",
                            "repetition_id": "rep-1",
                            "session_id": session_id,
                            "job_id": "placeholder",
                            "discipline": "bowling",
                            "action_type": "bowling_delivery",
                            "start_ts": 0.6,
                            "end_ts": 1.5,
                            "start_frame": 18,
                            "end_frame": 45,
                            "segmentation_method": "pose_motion_ball_hybrid_v1",
                            "segmentation_confidence": 0.84,
                            "manual_override": False,
                            "validity_state": "VALID",
                            "insufficient_reason": None,
                            "evidence_refs": [
                                {"ref_type": "ball_tracking", "label": "release_to_bounce"}
                            ],
                            "metric_refs": ["head_stability_score"],
                        }
                    ],
                    "phases": [
                        {
                            "schema_version": "coach_analysis_v2.contract.v1",
                            "phase_id": "rep-1:phase:1",
                            "repetition_id": "rep-1",
                            "phase_name": "approach",
                            "start_ts": 0.6,
                            "end_ts": 0.8,
                            "start_frame": 18,
                            "end_frame": 24,
                            "detection_method": "repetition_relative_heuristic_v1",
                            "confidence": 0.76,
                            "requires_object_evidence": False,
                            "camera_view_compatibility": ["side", "front", "behind"],
                            "manual_correction_supported": False,
                            "validity_state": "VALID",
                            "evidence_refs": [{"ref_type": "repetition_window", "ref_id": "rep-1"}],
                            "limitations": [],
                        }
                    ],
                },
            },
        )
        legacy_job = models.VideoAnalysisJob(
            session_id=session_id,
            sample_fps=10,
            include_frames=False,
            status=models.VideoAnalysisJobStatus.done,
            deep_results={"report": {"summary": "legacy-only"}},
        )
        db.add(segmented_job)
        db.add(legacy_job)
        await db.commit()
        await db.refresh(segmented_job)
        await db.refresh(legacy_job)
        segmented_job.deep_results = {
            **(segmented_job.deep_results or {}),
            "v2": {
                **((segmented_job.deep_results or {}).get("v2", {})),
                "repetitions": [
                    {
                        **(
                            (segmented_job.deep_results or {})
                            .get("v2", {})
                            .get("repetitions", [{}])[0]
                        ),
                        "job_id": segmented_job.id,
                    }
                ],
            },
        }
        await db.commit()
        segmented_job_id = segmented_job.id
        legacy_job_id = legacy_job.id

    job_resp = client.get(
        f"/api/coaches/plus/analysis-jobs/{segmented_job_id}/repetitions",
        headers=_auth_headers(coach_token),
    )
    assert job_resp.status_code == 200, job_resp.text
    job_payload = job_resp.json()
    assert job_payload["job_id"] == segmented_job_id
    assert job_payload["source"] == "deep_results"
    assert len(job_payload["repetitions"]) == 1
    assert job_payload["repetitions"][0]["action_type"] == "bowling_delivery"

    legacy_resp = client.get(
        f"/api/coaches/plus/analysis-jobs/{legacy_job_id}/repetitions",
        headers=_auth_headers(coach_token),
    )
    assert legacy_resp.status_code == 200, legacy_resp.text
    legacy_payload = legacy_resp.json()
    assert legacy_payload["source"] == "none"
    assert legacy_payload["repetitions"] == []
    assert legacy_payload["summary"] is None

    phase_job_resp = client.get(
        f"/api/coaches/plus/analysis-jobs/{segmented_job_id}/phases",
        headers=_auth_headers(coach_token),
    )
    assert phase_job_resp.status_code == 200, phase_job_resp.text
    phase_job_payload = phase_job_resp.json()
    assert phase_job_payload["job_id"] == segmented_job_id
    assert phase_job_payload["source"] == "deep_results"
    assert len(phase_job_payload["phases"]) == 1
    assert phase_job_payload["phases"][0]["phase_name"] == "approach"

    legacy_phase_resp = client.get(
        f"/api/coaches/plus/analysis-jobs/{legacy_job_id}/phases",
        headers=_auth_headers(coach_token),
    )
    assert legacy_phase_resp.status_code == 200, legacy_phase_resp.text
    legacy_phase_payload = legacy_phase_resp.json()
    assert legacy_phase_payload["source"] == "none"
    assert legacy_phase_payload["phases"] == []
    assert legacy_phase_payload["summary"] is None

    session_repetitions_resp = client.get(
        f"/api/coaches/plus/sessions/{session_id}/repetitions",
        headers=_auth_headers(coach_token),
    )
    assert session_repetitions_resp.status_code == 200, session_repetitions_resp.text
    session_payload = session_repetitions_resp.json()
    assert session_payload["session_id"] == session_id
    assert len(session_payload["jobs"]) == 2
    assert {job["job_id"] for job in session_payload["jobs"]} == {segmented_job_id, legacy_job_id}

    session_phases_resp = client.get(
        f"/api/coaches/plus/sessions/{session_id}/phases",
        headers=_auth_headers(coach_token),
    )
    assert session_phases_resp.status_code == 200, session_phases_resp.text
    session_phase_payload = session_phases_resp.json()
    assert session_phase_payload["session_id"] == session_id
    assert len(session_phase_payload["jobs"]) == 2

    forbidden_resp = client.get(
        f"/api/coaches/plus/analysis-jobs/{segmented_job_id}/repetitions",
        headers=_auth_headers(intruder_token),
    )
    assert forbidden_resp.status_code == 403

    forbidden_phase_resp = client.get(
        f"/api/coaches/plus/analysis-jobs/{segmented_job_id}/phases",
        headers=_auth_headers(intruder_token),
    )
    assert forbidden_phase_resp.status_code == 403


@pytest.mark.asyncio
async def test_coach_pro_plus_can_list_assigned_players(client: TestClient) -> None:
    player_id = "player-coach-plus-assigned"
    await ensure_profile(client, player_id)

    coach_plus = register_user(client, "coach-plus-players@example.com")
    await set_role(client, coach_plus["email"], models.RoleEnum.coach_pro_plus)
    coach_plus_token = login_user(client, coach_plus["email"])

    org = register_user(client, "org-plus-players@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    assign_resp = client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": coach_plus["id"], "player_profile_id": player_id},
    )
    assert assign_resp.status_code == 200, assign_resp.text

    resp = client.get("/api/coaches/me/players", headers=_auth_headers(coach_plus_token))
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert any(item["player_profile_id"] == player_id for item in payload)


@pytest.mark.asyncio
async def test_player_centered_session_requires_assigned_primary_player(client: TestClient) -> None:
    assigned_player_id = "player-v2-assigned"
    unassigned_player_id = "player-v2-unassigned"
    await ensure_profile(client, assigned_player_id)
    await ensure_profile(client, unassigned_player_id)

    coach_plus = register_user(client, "coach-plus-v2@example.com")
    await set_role(client, coach_plus["email"], models.RoleEnum.coach_pro_plus)
    coach_plus_token = login_user(client, coach_plus["email"])

    org = register_user(client, "org-v2@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    assign_resp = client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": coach_plus["id"], "player_profile_id": assigned_player_id},
    )
    assert assign_resp.status_code == 200, assign_resp.text

    create_resp = client.post(
        "/api/coaches/plus/sessions",
        headers=_auth_headers(coach_plus_token),
        json={
            "title": "V2 Pace Session",
            "primary_player_id": assigned_player_id,
            "player_ids": [assigned_player_id],
            "discipline": "pace_bowling",
            "coaching_focus": "release consistency",
            "camera_view": "side",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    created_payload = create_resp.json()
    assert created_payload["primary_player_id"] == assigned_player_id
    assert created_payload["player_ids"] == [assigned_player_id]
    assert created_payload["discipline"] == "pace_bowling"
    assert created_payload["analysis_context"] == "bowling"
    assert created_payload["coaching_focus"] == "release consistency"
    assert created_payload["camera_view"] == "side"

    nonexistent_resp = client.post(
        "/api/coaches/plus/sessions",
        headers=_auth_headers(coach_plus_token),
        json={
            "title": "Missing Player",
            "primary_player_id": "missing-player-id",
            "discipline": "batting",
            "camera_view": "front",
        },
    )
    assert nonexistent_resp.status_code == 404
    assert "not found" in nonexistent_resp.json()["detail"].lower()

    unauthorized_resp = client.post(
        "/api/coaches/plus/sessions",
        headers=_auth_headers(coach_plus_token),
        json={
            "title": "Unauthorized Player",
            "primary_player_id": unassigned_player_id,
            "discipline": "batting",
            "camera_view": "front",
        },
    )
    assert unauthorized_resp.status_code == 403
    assert "not assigned" in unauthorized_resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_player_centered_session_validation_and_legacy_compatibility(
    client: TestClient,
) -> None:
    player_id = "player-v2-validation"
    await ensure_profile(client, player_id)

    coach_plus = register_user(client, "coach-plus-validation@example.com")
    await set_role(client, coach_plus["email"], models.RoleEnum.coach_pro_plus)
    coach_plus_token = login_user(client, coach_plus["email"])

    org = register_user(client, "org-validation@example.com")
    await set_role(client, org["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org["email"])

    assign_resp = client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": coach_plus["id"], "player_profile_id": player_id},
    )
    assert assign_resp.status_code == 200, assign_resp.text

    invalid_discipline_resp = client.post(
        "/api/coaches/plus/sessions",
        headers=_auth_headers(coach_plus_token),
        json={
            "title": "Invalid discipline",
            "primary_player_id": player_id,
            "discipline": "mixed",
            "camera_view": "side",
        },
    )
    assert invalid_discipline_resp.status_code == 422

    invalid_context_resp = client.post(
        "/api/coaches/plus/sessions",
        headers=_auth_headers(coach_plus_token),
        json={
            "title": "Mismatched context",
            "primary_player_id": player_id,
            "discipline": "spin_bowling",
            "analysis_context": "batting",
            "camera_view": "side",
        },
    )
    assert invalid_context_resp.status_code == 422

    invalid_camera_resp = client.post(
        "/api/coaches/plus/sessions",
        headers=_auth_headers(coach_plus_token),
        json={
            "title": "Invalid camera",
            "primary_player_id": player_id,
            "discipline": "batting",
            "camera_view": "skycam",
        },
    )
    assert invalid_camera_resp.status_code == 422

    legacy_resp = client.post(
        "/api/coaches/plus/sessions",
        headers=_auth_headers(coach_plus_token),
        json={
            "title": "Legacy Session",
            "player_ids": [],
            "analysis_context": "mixed",
        },
    )
    assert legacy_resp.status_code == 200, legacy_resp.text
    legacy_payload = legacy_resp.json()
    assert legacy_payload["primary_player_id"] is None
    assert legacy_payload["player_ids"] == []
    assert legacy_payload["analysis_context"] == "mixed"


@pytest.mark.asyncio
async def test_player_centered_session_rbac_for_org_and_superuser(client: TestClient) -> None:
    org_player_id = "player-v2-org"
    super_player_id = "player-v2-super"
    await ensure_profile(client, org_player_id)
    await ensure_profile(client, super_player_id)

    org_user = register_user(client, "org-v2-rbac@example.com")
    await set_role(client, org_user["email"], models.RoleEnum.org_pro)
    org_token = login_user(client, org_user["email"])

    assign_resp = client.post(
        "/api/coaches/assign-player",
        headers=_auth_headers(org_token),
        json={"coach_user_id": org_user["id"], "player_profile_id": org_player_id},
    )
    assert assign_resp.status_code == 200, assign_resp.text

    org_create_resp = client.post(
        "/api/coaches/plus/sessions",
        headers=_auth_headers(org_token),
        json={
            "title": "Org V2 Session",
            "primary_player_id": org_player_id,
            "discipline": "fielding",
            "camera_view": "front",
        },
    )
    assert org_create_resp.status_code == 200, org_create_resp.text

    super_user = register_user(client, "super-v2-rbac@example.com")
    await set_role(client, super_user["email"], models.RoleEnum.coach_pro_plus)
    session_maker = client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        result = await session.execute(
            select(models.User).where(models.User.email == super_user["email"])
        )
        super_row = result.scalar_one()
        super_row.is_superuser = True
        await session.commit()
    super_token = login_user(client, super_user["email"])

    super_create_resp = client.post(
        "/api/coaches/plus/sessions",
        headers=_auth_headers(super_token),
        json={
            "title": "Superuser V2 Session",
            "primary_player_id": super_player_id,
            "discipline": "spin_bowling",
            "camera_view": "behind",
        },
    )
    assert super_create_resp.status_code == 200, super_create_resp.text
    assert super_create_resp.json()["analysis_context"] == "bowling"
