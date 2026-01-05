"""Test video upload lifecycle and job queueing.

Tests the fix for S3 HeadObject 404 errors by ensuring:
1. Jobs are created with awaiting_upload status (not claimable)
2. Jobs become queued only after upload-complete succeeds
3. Worker only claims queued jobs
4. Upload-complete is idempotent
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock, patch

import pytest
from botocore.exceptions import ClientError
from fastapi.testclient import TestClient
from sqlalchemy import select

if TYPE_CHECKING:
    pass

from backend.main import fastapi_app
from backend.sql_app import models
from backend.sql_app.database import get_db


@pytest.fixture
def client(reset_db: Any) -> TestClient:  # type: ignore[misc]
    """Test client with database override."""
    from backend.sql_app.database import SessionLocal

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        test_client.session_maker = SessionLocal  # type: ignore[attr-defined]
        yield test_client

    fastapi_app.dependency_overrides.pop(get_db, None)


def register_and_login(client: TestClient, email: str) -> str:
    """Register user and return access token."""
    client.post("/auth/register", json={"email": email, "password": "secret123"})
    resp = client.post(
        "/auth/login",
        data={"username": email, "password": "secret123"},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    return resp.json()["access_token"]


async def set_role(session_maker: Any, email: str, role: models.RoleEnum) -> None:
    """Set user role in database."""
    async with session_maker() as session:
        result = await session.execute(select(models.User).where(models.User.email == email))
        user = result.scalar_one()
        user.role = role
        await session.commit()


async def get_job_status(session_maker: Any, job_id: str) -> str | None:
    """Get current job status from database."""
    async with session_maker() as session:
        job = await session.get(models.VideoAnalysisJob, job_id)
        return job.status.value if job else None


@pytest.mark.asyncio
async def test_upload_lifecycle_prevents_premature_claiming(client: TestClient):
    """Test that jobs are not claimable until upload completes."""
    token = register_and_login(client, "coach@example.com")
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await set_role(session_maker, "coach@example.com", models.RoleEnum.coach_pro_plus)

    # Step 1: Create video session
    resp = client.post(
        "/api/coaches/plus/sessions",
        json={"title": "Test Session", "player_ids": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    session_id = resp.json()["id"]

    # Step 2: Initiate upload (mocking S3)
    with patch("backend.routes.coach_pro_plus.s3_service") as mock_s3:
        mock_s3.generate_presigned_put_url.return_value = "https://fake-presigned-url"

        resp = client.post(
            "/api/coaches/plus/videos/upload/initiate",
            json={"session_id": session_id, "sample_fps": 10, "include_frames": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        job_id = data["job_id"]

    # Step 3: Verify job is awaiting_upload (NOT queued)
    status = await get_job_status(session_maker, job_id)
    assert status == "awaiting_upload", f"Expected awaiting_upload, got {status}"

    # Step 4: Verify worker cannot claim job yet
    from backend.workers.analysis_worker import _claim_one_job

    claimed_id = await _claim_one_job()
    assert claimed_id is None, "Worker should not claim awaiting_upload jobs"

    # Step 5: Complete upload successfully (mocking S3 head_object)
    with patch("boto3.client") as mock_boto:
        mock_s3_client = MagicMock()
        mock_boto.return_value = mock_s3_client
        mock_s3_client.head_object.return_value = {"ContentLength": 1024}

        resp = client.post(
            "/api/coaches/plus/videos/upload/complete",
            json={"job_id": job_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "queued"

    # Step 6: Verify job is now queued (claimable)
    status = await get_job_status(session_maker, job_id)
    assert status == "queued", f"Expected queued, got {status}"

    # Step 7: Verify worker CAN now claim job
    claimed_id = await _claim_one_job()
    assert claimed_id == job_id, "Worker should claim queued job"


@pytest.mark.asyncio
async def test_upload_complete_idempotency(client: TestClient):
    """Test that calling upload-complete twice doesn't break anything."""
    token = register_and_login(client, "coach2@example.com")
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await set_role(session_maker, "coach2@example.com", models.RoleEnum.coach_pro_plus)

    # Create session and initiate upload
    resp = client.post(
        "/api/coaches/plus/sessions",
        json={"title": "Test Session 2", "player_ids": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    session_id = resp.json()["id"]

    with patch("backend.routes.coach_pro_plus.s3_service") as mock_s3:
        mock_s3.generate_presigned_put_url.return_value = "https://fake-url"
        resp = client.post(
            "/api/coaches/plus/videos/upload/initiate",
            json={"session_id": session_id, "sample_fps": 10, "include_frames": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        job_id = resp.json()["job_id"]

    # Complete upload first time
    with patch("boto3.client") as mock_boto:
        mock_s3_client = MagicMock()
        mock_boto.return_value = mock_s3_client
        mock_s3_client.head_object.return_value = {"ContentLength": 1024}

        resp1 = client.post(
            "/api/coaches/plus/videos/upload/complete",
            json={"job_id": job_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp1.status_code == 200
        assert resp1.json()["status"] == "queued"

        # Call complete again (idempotent)
        resp2 = client.post(
            "/api/coaches/plus/videos/upload/complete",
            json={"job_id": job_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200
        # Should return success without changes
        assert "already" in resp2.json()["message"].lower() or resp2.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_upload_complete_fails_on_missing_s3_object(client: TestClient):
    """Test that upload-complete fails if S3 object doesn't exist."""
    token = register_and_login(client, "coach3@example.com")
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await set_role(session_maker, "coach3@example.com", models.RoleEnum.coach_pro_plus)

    # Create session and initiate upload
    resp = client.post(
        "/api/coaches/plus/sessions",
        json={"title": "Test Session 3", "player_ids": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    session_id = resp.json()["id"]

    with patch("backend.routes.coach_pro_plus.s3_service") as mock_s3:
        mock_s3.generate_presigned_put_url.return_value = "https://fake-url"
        resp = client.post(
            "/api/coaches/plus/videos/upload/initiate",
            json={"session_id": session_id, "sample_fps": 10, "include_frames": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        job_id = resp.json()["job_id"]

    # Complete upload with missing S3 object (404)
    with patch("boto3.client") as mock_boto:
        mock_s3_client = MagicMock()
        mock_boto.return_value = mock_s3_client
        error_response = {"Error": {"Code": "404"}}
        mock_s3_client.head_object.side_effect = ClientError(error_response, "HeadObject")

        resp = client.post(
            "/api/coaches/plus/videos/upload/complete",
            json={"job_id": job_id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400, resp.text
        assert "not found" in resp.json()["detail"].lower()

    # Verify job is marked failed
    status = await get_job_status(session_maker, job_id)
    assert status == "failed", f"Expected failed, got {status}"
