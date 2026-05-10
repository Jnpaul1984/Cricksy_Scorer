from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from backend.services.video_job_recovery import mark_stale_video_analysis_jobs
from backend.sql_app.models import (
    VideoAnalysisJob,
    VideoAnalysisJobStatus,
    VideoSessionStatus,
)


@pytest.mark.asyncio
async def test_mark_stale_video_analysis_jobs_detects_only_old_running_jobs(
    db_session, test_video_session
) -> None:
    now = datetime.now(UTC)
    test_video_session.s3_bucket = "test-bucket"
    test_video_session.s3_key = "coach_plus/coach/test/session/original.mp4"
    test_video_session.status = VideoSessionStatus.processing

    stale_job = VideoAnalysisJob(
        session_id=test_video_session.id,
        status=VideoAnalysisJobStatus.quick_running,
        stage="QUICK",
        progress_pct=31,
        started_at=now - timedelta(hours=3),
        s3_bucket=test_video_session.s3_bucket,
        s3_key=test_video_session.s3_key,
    )
    fresh_job = VideoAnalysisJob(
        session_id=test_video_session.id,
        status=VideoAnalysisJobStatus.quick_running,
        stage="QUICK",
        progress_pct=12,
        started_at=now - timedelta(minutes=5),
        s3_bucket=test_video_session.s3_bucket,
        s3_key=test_video_session.s3_key,
    )
    db_session.add_all([stale_job, fresh_job])
    await db_session.commit()
    await db_session.refresh(stale_job)
    await db_session.refresh(fresh_job)

    stale_jobs = await mark_stale_video_analysis_jobs(
        db_session,
        now=now,
        stale_after_seconds=1800,
        session_id=test_video_session.id,
    )

    assert [job.id for job in stale_jobs] == [stale_job.id]
    await db_session.refresh(stale_job)
    await db_session.refresh(fresh_job)
    assert stale_job.status == VideoAnalysisJobStatus.failed
    assert stale_job.stage == "STALE_ORPHANED"
    assert "Marked stale/orphaned after 1800s" in (stale_job.error_message or "")
    assert fresh_job.status == VideoAnalysisJobStatus.quick_running


@pytest.mark.asyncio
async def test_get_job_marks_stale_and_exposes_retryable(
    async_client, db_session, auth_headers, test_video_session
) -> None:
    old_time = datetime.now(UTC) - timedelta(hours=2)
    test_video_session.s3_bucket = "test-bucket"
    test_video_session.s3_key = "coach_plus/coach/test/session/original.mp4"
    test_video_session.status = VideoSessionStatus.processing
    job = VideoAnalysisJob(
        session_id=test_video_session.id,
        status=VideoAnalysisJobStatus.deep_running,
        stage="DEEP",
        progress_pct=66,
        started_at=old_time,
        deep_started_at=old_time,
        s3_bucket=test_video_session.s3_bucket,
        s3_key=test_video_session.s3_key,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await async_client.get(f"/api/coaches/plus/analysis-jobs/{job.id}", headers=auth_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "failed"
    assert body["stage"] == "STALE_ORPHANED"
    assert body["retryable"] is True
    assert "Marked stale/orphaned" in (body["error_message"] or "")


@pytest.mark.asyncio
async def test_retry_endpoint_requeues_failed_job(
    async_client, db_session, auth_headers, test_video_session
) -> None:
    test_video_session.s3_bucket = "test-bucket"
    test_video_session.s3_key = "coach_plus/coach/test/session/original.mp4"
    test_video_session.status = VideoSessionStatus.failed
    job = VideoAnalysisJob(
        session_id=test_video_session.id,
        status=VideoAnalysisJobStatus.failed,
        stage="FAILED",
        progress_pct=75,
        error_message="worker crash",
        started_at=datetime.now(UTC) - timedelta(minutes=20),
        completed_at=datetime.now(UTC) - timedelta(minutes=10),
        s3_bucket=test_video_session.s3_bucket,
        s3_key=test_video_session.s3_key,
        quick_results={"meta": {"analysis_mode_used": "batting"}},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await async_client.post(
        f"/api/coaches/plus/analysis-jobs/{job.id}/retry",
        headers=auth_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "queued"
    assert body["stage"] == "QUEUED"
    assert body["progress_pct"] == 0
    assert body["error_message"] is None
    assert body["retryable"] is False

    await db_session.refresh(job)
    assert job.quick_results == {"meta": {"analysis_mode_used": "batting"}}
    assert job.started_at is None
    assert job.completed_at is None


@pytest.mark.asyncio
async def test_retry_endpoint_blocks_completed_jobs(
    async_client, db_session, auth_headers, test_video_session
) -> None:
    test_video_session.s3_bucket = "test-bucket"
    test_video_session.s3_key = "coach_plus/coach/test/session/original.mp4"
    job = VideoAnalysisJob(
        session_id=test_video_session.id,
        status=VideoAnalysisJobStatus.done,
        stage="DONE",
        progress_pct=100,
        s3_bucket=test_video_session.s3_bucket,
        s3_key=test_video_session.s3_key,
        deep_results={"meta": {"analysis_mode_used": "batting"}},
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await async_client.post(
        f"/api/coaches/plus/analysis-jobs/{job.id}/retry",
        headers=auth_headers,
    )
    assert resp.status_code == 409
    assert "Cannot retry successfully completed job" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_retry_endpoint_blocks_unauthorized_user(
    async_client, db_session, other_auth_headers, test_video_session
) -> None:
    test_video_session.s3_bucket = "test-bucket"
    test_video_session.s3_key = "coach_plus/coach/test/session/original.mp4"
    job = VideoAnalysisJob(
        session_id=test_video_session.id,
        status=VideoAnalysisJobStatus.failed,
        stage="FAILED",
        error_message="worker crash",
        s3_bucket=test_video_session.s3_bucket,
        s3_key=test_video_session.s3_key,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    resp = await async_client.post(
        f"/api/coaches/plus/analysis-jobs/{job.id}/retry",
        headers=other_auth_headers,
    )
    assert resp.status_code == 403
