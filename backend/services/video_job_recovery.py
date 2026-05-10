from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.config import settings
from backend.sql_app.models import (
    VideoAnalysisChunkStatus,
    VideoAnalysisJob,
    VideoAnalysisJobStatus,
    VideoSessionStatus,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

STALE_CANDIDATE_STATUSES = {
    VideoAnalysisJobStatus.processing,
    VideoAnalysisJobStatus.quick_running,
    VideoAnalysisJobStatus.quick_done,
    VideoAnalysisJobStatus.deep_running,
}

# Stale/orphaned jobs are normalized to `failed` with stage=STALE_ORPHANED,
# so allowing retries from `failed` covers both explicit failures and stale recoveries.
RETRYABLE_STATUSES = {VideoAnalysisJobStatus.failed}
SUCCESS_TERMINAL_STATUSES = {VideoAnalysisJobStatus.done, VideoAnalysisJobStatus.completed}
MAX_STALE_PROGRESS_PCT = 99
MIN_STALE_THRESHOLD_SECONDS = 60


def _now_utc() -> datetime:
    return datetime.now(UTC)


def get_stale_threshold_seconds() -> int:
    # Guardrail against accidental too-low values that would mark active jobs stale too quickly.
    return max(int(settings.COACH_PLUS_STALE_JOB_THRESHOLD_SECONDS), MIN_STALE_THRESHOLD_SECONDS)


def is_retryable_video_job(job: VideoAnalysisJob) -> bool:
    if job.status not in RETRYABLE_STATUSES:
        return False
    session = job.session
    bucket = job.s3_bucket or (session.s3_bucket if session else None)
    key = job.s3_key or (session.s3_key if session else None)
    return bool(bucket and key)


def _job_reference_time(job: VideoAnalysisJob) -> datetime:
    ts = (
        job.deep_started_at
        or job.quick_started_at
        or job.started_at
        or job.updated_at
        or job.created_at
    )
    if ts is None:
        return _now_utc()
    if ts.tzinfo is None:
        return ts.replace(tzinfo=UTC)
    return ts


def _should_mark_stale(job: VideoAnalysisJob, *, now: datetime, stale_after: timedelta) -> bool:
    if job.status not in STALE_CANDIDATE_STATUSES:
        return False
    return now - _job_reference_time(job) >= stale_after


def _mark_stale(job: VideoAnalysisJob, *, now: datetime, threshold_seconds: int) -> None:
    previous_status = job.status.value
    reference_time = _job_reference_time(job).isoformat()
    job.status = VideoAnalysisJobStatus.failed
    job.stage = "STALE_ORPHANED"
    job.progress_pct = min(int(job.progress_pct or 0), MAX_STALE_PROGRESS_PCT)
    job.completed_at = now
    job.error_message = (
        f"Marked stale/orphaned after {threshold_seconds}s in status={previous_status} "
        f"(reference_time={reference_time})"
    )
    if job.session and job.session.status == VideoSessionStatus.processing:
        job.session.status = VideoSessionStatus.failed


async def mark_stale_video_analysis_jobs(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    stale_after_seconds: int | None = None,
    job_id: str | None = None,
    session_id: str | None = None,
) -> list[VideoAnalysisJob]:
    current_time = now or _now_utc()
    threshold_seconds = stale_after_seconds or get_stale_threshold_seconds()
    stale_after = timedelta(seconds=threshold_seconds)

    stmt = (
        select(VideoAnalysisJob)
        .options(selectinload(VideoAnalysisJob.session))
        .where(VideoAnalysisJob.status.in_(STALE_CANDIDATE_STATUSES))
    )
    if job_id:
        stmt = stmt.where(VideoAnalysisJob.id == job_id)
    if session_id:
        stmt = stmt.where(VideoAnalysisJob.session_id == session_id)

    result = await db.execute(stmt)
    candidates = result.scalars().all()

    stale_jobs: list[VideoAnalysisJob] = []
    for job in candidates:
        if _should_mark_stale(job, now=current_time, stale_after=stale_after):
            _mark_stale(job, now=current_time, threshold_seconds=threshold_seconds)
            stale_jobs.append(job)

    if stale_jobs:
        await db.commit()
        for job in stale_jobs:
            await db.refresh(job)

    return stale_jobs


async def retry_video_analysis_job(
    db: AsyncSession, job: VideoAnalysisJob, *, now: datetime | None = None
) -> VideoAnalysisJob:
    current_time = now or _now_utc()

    if job.status in SUCCESS_TERMINAL_STATUSES:
        raise ValueError(f"Cannot retry successfully completed job in status={job.status.value}")
    if job.status not in RETRYABLE_STATUSES:
        raise ValueError(f"Job status {job.status.value} is not retryable")
    if not is_retryable_video_job(job):
        raise ValueError("Job is retryable only when a persisted S3 upload location exists")

    job.status = VideoAnalysisJobStatus.queued
    job.stage = "QUEUED"
    job.progress_pct = 0
    job.error_message = None
    job.sqs_message_id = None
    job.started_at = None
    job.completed_at = None
    job.quick_started_at = None
    job.quick_completed_at = None
    job.deep_started_at = None
    job.deep_completed_at = None
    job.updated_at = current_time

    if job.session and job.session.status == VideoSessionStatus.failed:
        job.session.status = VideoSessionStatus.uploaded

    if job.deep_mode == "gpu":
        job.completed_chunks = 0
        for chunk in job.chunks:
            chunk.status = VideoAnalysisChunkStatus.queued
            chunk.error_message = None
            chunk.started_at = None
            chunk.completed_at = None
            chunk.runtime_ms = None

    await db.commit()
    await db.refresh(job)
    return job
