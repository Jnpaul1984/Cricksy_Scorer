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
from botocore.exceptions import ClientError
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


async def _download_from_s3(*, bucket: str, key: str, dst_path: str, job_id: str | None = None) -> None:
    """Download video from S3 to local path with comprehensive logging.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
        dst_path: Local destination path
        job_id: Optional job ID for context logging
    
    Raises:
        ClientError: S3 operation failed (re-raised after logging)
    """
    s3 = cast(Any, boto3.client("s3", region_name=settings.AWS_REGION))  # pyright: ignore[reportUnknownMemberType]
    loop = asyncio.get_running_loop()
    
    logger.info(
        f"Downloading from S3: bucket={bucket} key={key} -> {dst_path} "
        f"job_id={job_id or 'N/A'}"
    )

    def _dl() -> None:
        try:
            s3.download_file(bucket, key, dst_path)
            # Log file size after successful download
            try:
                import os
                file_size = os.path.getsize(dst_path)
                logger.info(
                    f"S3 download complete: bucket={bucket} key={key} "
                    f"file_size_bytes={file_size} job_id={job_id or 'N/A'}"
                )
            except Exception as size_err:
                logger.warning(f"Could not determine file size: {size_err}")
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            request_id = e.response.get("ResponseMetadata", {}).get("RequestId", "N/A")
            logger.error(
                f"S3 download failed: bucket={bucket} key={key} "
                f"error_code={error_code} request_id={request_id} job_id={job_id or 'N/A'}"
            )
            raise

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
        logger.info(f"Processing analysis job: job_id={job_id}")
        
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

        # Prefer job-level S3 snapshot (immutable), fallback to session (mutable)
        # Job-level snapshot prevents 404s from session mutations during retries
        bucket = job.s3_bucket or video_session.s3_bucket
        key = job.s3_key or video_session.s3_key
        
        # Log if fallback occurred (indicates old job or missing snapshot)
        if not job.s3_bucket or not job.s3_key:
            logger.warning(
                f"Job S3 snapshot missing, using session values: job_id={job_id} "
                f"job.s3_bucket={job.s3_bucket} job.s3_key={job.s3_key} "
                f"session.s3_bucket={video_session.s3_bucket} session.s3_key={video_session.s3_key}"
            )
        
        # Log if job and session values differ (session was mutated)
        if job.s3_bucket and job.s3_key and (
            job.s3_bucket != video_session.s3_bucket or job.s3_key != video_session.s3_key
        ):
            logger.warning(
                f"Job/session S3 location mismatch (session was mutated): job_id={job_id} "
                f"job: bucket={job.s3_bucket} key={job.s3_key} | "
                f"session: bucket={video_session.s3_bucket} key={video_session.s3_key}"
            )

        if not bucket or not key:
            job.status = VideoAnalysisJobStatus.failed
            job.stage = "FAILED"
            job.progress_pct = 0
            job.error_message = (
                f"Missing S3 location: job.s3_bucket={job.s3_bucket} job.s3_key={job.s3_key} "
                f"session.s3_bucket={video_session.s3_bucket} session.s3_key={video_session.s3_key}"
            )
            job.completed_at = _now_utc()
            await db.commit()
            logger.error(f"Job failed - missing S3 location: job_id={job_id} {job.error_message}")
            return
        
        logger.info(
            f"Job S3 location: job_id={job_id} bucket={bucket} key={key} "
            f"session_id={video_session.id} using_snapshot={'yes' if job.s3_bucket else 'no'}"
        )

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

            await _download_from_s3(bucket=bucket, key=key, dst_path=local_video_path, job_id=job_id)

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
    
    # Log AWS configuration for debugging
    logger.info(
        f"AWS Configuration: region={settings.AWS_REGION} "
        f"S3_COACH_VIDEOS_BUCKET={settings.S3_COACH_VIDEOS_BUCKET or '<not set>'}"
    )
    
    # Log AWS identity (account/role) for verification
    try:
        import boto3
        sts = boto3.client("sts", region_name=settings.AWS_REGION)
        identity = sts.get_caller_identity()
        account_id = identity.get("Account", "Unknown")
        arn = identity.get("Arn", "Unknown")
        logger.info(f"AWS Identity: account={account_id} arn={arn}")
    except Exception as e:
        logger.warning(f"Could not retrieve AWS identity: {e}")

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
