from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.asyncio
async def test_video_stream_url_endpoint_and_job_embed(db_session, monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensures stream URL is returned via the new endpoint and embedded on the single-job response.

    This is mocked (no AWS clients) by patching the lazy S3 service getter.
    """

    from httpx import ASGITransport, AsyncClient

    from backend.app import create_app
    import backend.security as security
    from backend.config import Settings, settings
    from backend.sql_app.models import (
        OwnerTypeEnum,
        User,
        VideoAnalysisJob,
        VideoAnalysisJobStatus,
        VideoSession,
        VideoSessionStatus,
    )

    class _FakeS3Service:
        def generate_presigned_get_url(
            self, bucket: str, key: str, expires_in: int | None = None
        ) -> str:
            return f"https://example.invalid/stream?bucket={bucket}&key={key}&exp={expires_in}"

    # Patch lazy S3 service to avoid real boto3 client creation
    import backend.services.s3_service as s3_service_mod

    monkeypatch.setattr(s3_service_mod, "_get_s3_service", lambda: _FakeS3Service())

    # Use a deterministic expiry for assertions
    monkeypatch.setattr(settings, "S3_STREAM_URL_EXPIRES_SECONDS", 123)

    # Create a Coach Pro Plus user
    user = User(
        id="coach-pro-plus-stream-test-user-id",
        email="coachplus-stream@test.com",
        hashed_password=security.get_password_hash("testpass"),
        role="coach_pro_plus",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    security.add_in_memory_user(user)
    token = security.create_access_token({"sub": user.id, "email": user.email, "role": user.role})

    # Create a session that already has an uploaded S3 location
    session = VideoSession(
        owner_type=OwnerTypeEnum.coach,
        owner_id=user.id,
        title="Test Session",
        player_ids=[],
        notes=None,
        status=VideoSessionStatus.uploaded,
        s3_bucket="test-bucket",
        s3_key="coach_plus/coach/123/original.mp4",
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)

    # Create a job linked to that session
    job = VideoAnalysisJob(
        session_id=session.id,
        sample_fps=10,
        include_frames=False,
        status=VideoAnalysisJobStatus.completed,
        results=None,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    # Build a FastAPI app that uses the real SQLAlchemy DB dependency.
    import os

    monkeypatch.setenv("CRICKSY_IN_MEMORY_DB", "0")
    settings_override = Settings(
        DATABASE_URL=os.environ["DATABASE_URL"],
        APP_SECRET_KEY=os.environ["APP_SECRET_KEY"],
        IN_MEMORY_DB=False,
    )
    _, fastapi_app = create_app(settings_override=settings_override)

    client = AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test")
    try:
        # New endpoint
        resp = await client.get(
            f"/api/coaches/plus/videos/{session.id}/stream-url",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["bucket"] == "test-bucket"
        assert body["key"] == "coach_plus/coach/123/original.mp4"
        assert body["expires_in"] == 123
        assert "https://example.invalid/stream" in body["video_url"]

        # Single-job poll response includes embedded stream info
        job_resp = await client.get(
            f"/api/coaches/plus/analysis-jobs/{job.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert job_resp.status_code == 200
        job_body = job_resp.json()
        assert job_body.get("video_stream")
        assert job_body["video_stream"]["expires_in"] == 123
        assert job_body["video_stream"]["bucket"] == "test-bucket"
        assert job_body["video_stream"]["key"] == "coach_plus/coach/123/original.mp4"
        assert "https://example.invalid/stream" in job_body["video_stream"]["video_url"]
    finally:
        await client.aclose()
