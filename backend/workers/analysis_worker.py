from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import signal
import tempfile
from datetime import UTC, datetime
from typing import Any, cast

import boto3
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.services.coach_plus_analysis import run_pose_metrics_findings_report
from backend.sql_app.database import get_engine, get_session_local
from backend.sql_app.models import VideoAnalysisJob, VideoAnalysisJobStatus, VideoSessionStatus

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    # Keep consistent with DB timezone-aware columns
    return datetime.now(UTC)


async def _download_from_s3(*, bucket: str, key: str, dst_path: str) -> None:
    s3 = cast(Any, boto3.client("s3", region_name=settings.AWS_REGION))  # pyright: ignore[reportUnknownMemberType]
    loop = asyncio.get_running_loop()

    def _dl() -> None:
        s3.download_file(bucket, key, dst_path)

    await loop.run_in_executor(None, _dl)


async def _upload_json_to_s3(*, bucket: str, key: str, payload: dict[str, Any]) -> None:
    s3 = cast(Any, boto3.client("s3", region_name=settings.AWS_REGION))  # pyright: ignore[reportUnknownMemberType]
    body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    loop = asyncio.get_running_loop()

    def _put() -> None:
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )

    await loop.run_in_executor(None, _put)


def _derive_output_key(input_key: str, leaf_name: str) -> str:
    # input_key ends with /original.mp4; keep same subtree
    base = input_key.rsplit("/", 1)[0]
    return f"{base}/analysis/{leaf_name}"


async def _process_job(job_id: str) -> None:
    session_local = get_session_local()

    async with session_local() as db:
        result = await db.execute(
            select(VideoAnalysisJob)
            .options(selectinload(VideoAnalysisJob.session))
            .where(VideoAnalysisJob.id == job_id)
        )
        job = result.scalar_one()
        video_session = job.session

        # Cache config values early: AsyncSession expires ORM attributes on commit()
        # which can trigger an implicit lazy refresh (and MissingGreenlet) on sync access.
        job_deep_enabled = True if job.deep_enabled is None else bool(job.deep_enabled)
        deep_enabled = bool(job_deep_enabled) and bool(settings.COACH_PLUS_DEEP_ANALYSIS_ENABLED)
        deep_fps = float(job.sample_fps or 10)
        include_frames = bool(job.include_frames)

        if not video_session.s3_bucket or not video_session.s3_key:
            job.status = VideoAnalysisJobStatus.failed
            job.stage = "FAILED"
            job.progress_pct = 0
            job.error_message = "Missing session.s3_bucket or session.s3_key"
            job.completed_at = _now_utc()
            await db.commit()
            return

        bucket = video_session.s3_bucket
        key = video_session.s3_key

        # Download to temp file
        with tempfile.TemporaryDirectory(prefix="coach_plus_video_") as tmpdir:
            local_video_path = os.path.join(tmpdir, "original.mp4")

            # Stage: QUICK
            job.status = VideoAnalysisJobStatus.quick_running
            job.stage = "QUICK"
            job.progress_pct = 0
            job.started_at = job.started_at or _now_utc()
            job.quick_started_at = _now_utc()
            video_session.status = VideoSessionStatus.processing
            await db.commit()

            await _download_from_s3(bucket=bucket, key=key, dst_path=local_video_path)

            # Best-effort progress bump
            job.progress_pct = 5
            await db.commit()

            quick_artifacts = run_pose_metrics_findings_report(
                video_path=local_video_path,
                sample_fps=5.0,
                include_frames=False,
                max_width=640,
                max_seconds=30.0,
                player_context=None,
            )

            quick_payload = quick_artifacts.results
            quick_out_key = _derive_output_key(key, "quick_results.json")
            await _upload_json_to_s3(bucket=bucket, key=quick_out_key, payload=quick_payload)
            quick_payload = {
                **quick_payload,
                "outputs": {"quick_results_s3_key": quick_out_key},
            }

            job.quick_results = quick_payload
            job.status = VideoAnalysisJobStatus.quick_done
            job.stage = "QUICK_DONE"
            job.progress_pct = 50
            job.quick_completed_at = _now_utc()
            await db.commit()

            if not deep_enabled:
                job.status = VideoAnalysisJobStatus.done
                job.stage = "DONE"
                job.progress_pct = 100
                job.completed_at = _now_utc()
                video_session.status = VideoSessionStatus.ready
                # Keep legacy results populated for older clients
                job.results = {"quick": quick_payload}
                await db.commit()
                return

            # Stage: DEEP
            job.status = VideoAnalysisJobStatus.deep_running
            job.stage = "DEEP"
            job.progress_pct = 50
            job.deep_started_at = _now_utc()
            await db.commit()

            # Deep pass uses job-configured FPS; keep a sane default
            deep_artifacts = run_pose_metrics_findings_report(
                video_path=local_video_path,
                sample_fps=deep_fps,
                include_frames=include_frames,
                max_width=640,
                max_seconds=None,
                player_context=None,
            )

            deep_payload = deep_artifacts.results
            deep_out_key = _derive_output_key(key, "deep_results.json")
            await _upload_json_to_s3(bucket=bucket, key=deep_out_key, payload=deep_payload)
            deep_payload = {
                **deep_payload,
                "outputs": {"deep_results_s3_key": deep_out_key},
            }

            # If frames were requested, upload them separately (can be large)
            if deep_artifacts.frames is not None:
                frames_key = _derive_output_key(key, "deep_frames.json")
                await _upload_json_to_s3(
                    bucket=bucket,
                    key=frames_key,
                    payload={"frames": deep_artifacts.frames},
                )
                deep_payload.setdefault("outputs", {})
                deep_payload["outputs"]["deep_frames_s3_key"] = frames_key

            job.deep_results = deep_payload
            job.status = VideoAnalysisJobStatus.done
            job.stage = "DONE"
            job.progress_pct = 100
            job.deep_completed_at = _now_utc()
            job.completed_at = _now_utc()
            video_session.status = VideoSessionStatus.ready

            # Keep legacy results populated for older clients
            job.results = {"quick": quick_payload, "deep": deep_payload}

            await db.commit()


async def _claim_one_job() -> str | None:
    session_local = get_session_local()

    async with session_local() as db, db.begin():
        stmt = (
            select(VideoAnalysisJob)
            .where(VideoAnalysisJob.status == VideoAnalysisJobStatus.queued)
            .order_by(VideoAnalysisJob.created_at)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        result = await db.execute(stmt)
        job = result.scalars().first()
        if job is None:
            return None

        # Claim by moving to QUICK_RUNNING (prevents other workers)
        job.status = VideoAnalysisJobStatus.quick_running
        job.stage = "QUICK"
        job.progress_pct = 0
        job.started_at = job.started_at or _now_utc()
        job.quick_started_at = _now_utc()

        return job.id


async def run_worker_loop(*, poll_seconds: float = 1.0) -> None:
    logger.info("analysis_worker starting")
    logger.info("ENV=%s", settings.ENV)

    stop_event = asyncio.Event()

    def _request_stop() -> None:
        logger.info("analysis_worker stopping (signal)")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            # Windows / some runtimes
            def _handler(_signum: int, _frame: object | None) -> None:
                _request_stop()

            signal.signal(sig, _handler)

    while not stop_event.is_set():
        try:
            job_id = await _claim_one_job()
            if job_id is None:
                await asyncio.sleep(poll_seconds)
                continue

            logger.info("Claimed job_id=%s", job_id)

            try:
                await _process_job(job_id)
                logger.info("Completed job_id=%s", job_id)
            except Exception as e:
                logger.exception("Job failed job_id=%s", job_id)
                # Best-effort mark failed
                session_local = get_session_local()
                async with session_local() as db:
                    result = await db.execute(
                        select(VideoAnalysisJob)
                        .options(selectinload(VideoAnalysisJob.session))
                        .where(VideoAnalysisJob.id == job_id)
                    )
                    job = result.scalar_one_or_none()
                    if job is not None:
                        job.status = VideoAnalysisJobStatus.failed
                        job.stage = "FAILED"
                        job.error_message = str(e)
                        job.progress_pct = min(int(job.progress_pct or 0), 99)
                        job.completed_at = _now_utc()
                        job.session.status = VideoSessionStatus.failed
                        await db.commit()

        except Exception:
            logger.exception("Worker loop error")
            await asyncio.sleep(poll_seconds)

    # Dispose engine
    with contextlib.suppress(Exception):
        await get_engine().dispose()


def main() -> None:
    logging.basicConfig(
        level=getattr(logging, (settings.LOG_LEVEL or "INFO").upper(), logging.INFO)
    )

    asyncio.run(run_worker_loop(poll_seconds=float(settings.COACH_PLUS_ANALYSIS_POLL_SECONDS)))


if __name__ == "__main__":
    main()
