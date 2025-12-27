from __future__ import annotations

from typing import Any

import pytest


@pytest.mark.asyncio
async def test_upload_initiate_persists_session_s3_key(
    db_session, monkeypatch: pytest.MonkeyPatch
) -> None:
    from httpx import ASGITransport, AsyncClient

    from backend.app import create_app
    import backend.security as security
    from backend.config import settings
    from backend.sql_app.models import OwnerTypeEnum, User, VideoSession, VideoSessionStatus

    class _FakeS3Service:
        def generate_presigned_put_url(
            self, bucket: str, key: str, expires_in: int | None = None
        ) -> str:
            return f"https://example.invalid/upload?bucket={bucket}&key={key}"

    class _FakeSQSService:
        def send_message(
            self, queue_url: str, message_body: dict[str, Any], message_attributes=None
        ) -> str:
            return "test-message-id"

    # Patch lazy services to avoid real AWS clients
    import backend.services.s3_service as s3_service_mod
    import backend.services.sqs_service as sqs_service_mod

    monkeypatch.setattr(s3_service_mod, "_get_s3_service", lambda: _FakeS3Service())
    monkeypatch.setattr(sqs_service_mod, "_get_sqs_service", lambda: _FakeSQSService())

    # Ensure queue url is non-empty for the endpoint path
    monkeypatch.setattr(settings, "SQS_VIDEO_ANALYSIS_QUEUE_URL", "https://example.invalid/sqs")

    # Create a Coach Pro Plus user
    user = User(
        id="coach-pro-plus-test-user-id",
        email="coachplus@test.com",
        hashed_password=security.get_password_hash("testpass"),
        role="coach_pro_plus",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Add to in-memory auth cache
    security.add_in_memory_user(user)

    token = security.create_access_token({"sub": user.id, "email": user.email, "role": user.role})

    # Create a video session directly (endpoint response validation can be flaky in SQLite)
    session = VideoSession(
        owner_type=OwnerTypeEnum.coach,
        owner_id=user.id,
        title="Test Session",
        player_ids=[],
        notes=None,
        status=VideoSessionStatus.pending,
        s3_bucket=None,
        s3_key=None,
    )
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    session_id = session.id

    # Build a FastAPI app that uses the real SQLAlchemy DB dependency.
    # The default Settings instance is created at import time with CRICKSY_IN_MEMORY_DB=1,
    # so we must pass a settings override to disable the fake-session in-memory wiring.
    import os

    from backend.config import Settings

    monkeypatch.setenv("CRICKSY_IN_MEMORY_DB", "0")
    settings_override = Settings(
        DATABASE_URL=os.environ["DATABASE_URL"],
        APP_SECRET_KEY=os.environ["APP_SECRET_KEY"],
        IN_MEMORY_DB=False,
    )
    _, fastapi_app = create_app(settings_override=settings_override)
    client = AsyncClient(transport=ASGITransport(app=fastapi_app), base_url="http://test")
    try:
        # Initiate upload
        initiate = await client.post(
            "/api/coaches/plus/videos/upload/initiate",
            json={"session_id": session_id, "sample_fps": 10, "include_frames": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert initiate.status_code == 200
        body = initiate.json()

        assert body["s3_bucket"] == settings.S3_COACH_VIDEOS_BUCKET
        assert body["s3_key"]

        # Verify session record has persisted s3 info for worker to read.
        # Refresh because the endpoint used a separate DB session.
        await db_session.refresh(session)
        assert session.s3_bucket == settings.S3_COACH_VIDEOS_BUCKET
        assert session.s3_key == body["s3_key"]

        # Complete upload should enqueue without failing key validation
        complete = await client.post(
            "/api/coaches/plus/videos/upload/complete",
            json={"job_id": body["job_id"]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert complete.status_code == 200
    finally:
        await client.aclose()
