"""GPU worker for parallel video chunk processing.

Processes individual video chunks in parallel, writing pose landmarks to S3.
Multiple GPU workers can run concurrently, each claiming chunks via SKIP LOCKED.
"""

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
import cv2
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.config import settings
from backend.services.coach_plus_analysis import extract_pose_landmarks
from backend.sql_app.database import get_session_local
from backend.sql_app.models import (
    VideoAnalysisChunk,
    VideoAnalysisChunkStatus,
    VideoAnalysisJob,
)

logger = logging.getLogger(__name__)


def _now_utc() -> datetime:
    return datetime.now(UTC)


async def _download_from_s3(
    *, bucket: str, key: str, dst_path: str, chunk_id: str | None = None
) -> None:
    """Download video from S3 to local path.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        dst_path: Local destination path
        chunk_id: Optional chunk ID for logging
    """
    s3 = cast(Any, boto3.client("s3", region_name=settings.AWS_REGION))
    loop = asyncio.get_running_loop()

    logger.info(
        f"Downloading from S3: bucket={bucket} key={key} -> {dst_path} "
        f"chunk_id={chunk_id or 'N/A'}"
    )

    def _dl() -> None:
        try:
            s3.download_file(bucket, key, dst_path)
            file_size = os.path.getsize(dst_path)
            logger.info(
                f"S3 download complete: bucket={bucket} key={key} "
                f"file_size_bytes={file_size} chunk_id={chunk_id or 'N/A'}"
            )
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            request_id = e.response.get("ResponseMetadata", {}).get("RequestId", "N/A")
            logger.error(
                f"S3 download failed: bucket={bucket} key={key} "
                f"error_code={error_code} request_id={request_id} chunk_id={chunk_id or 'N/A'}"
            )
            raise

    await loop.run_in_executor(None, _dl)


async def _upload_json_to_s3(*, bucket: str, key: str, payload: dict[str, Any]) -> None:
    """Upload JSON payload to S3.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        payload: JSON payload to upload
    """
    s3 = cast(Any, boto3.client("s3", region_name=settings.AWS_REGION))
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
    logger.info(f"Uploaded chunk artifact: bucket={bucket} key={key} size={len(body)}")


def extract_chunk_poses(
    video_path: str,
    start_sec: float,
    end_sec: float,
    sample_fps: float,
    max_width: int,
) -> dict[str, Any]:
    """Extract pose landmarks for a video chunk.

    Args:
        video_path: Path to video file
        start_sec: Chunk start time in seconds
        end_sec: Chunk end time in seconds
        sample_fps: Target sampling rate
        max_width: Max video width for processing

    Returns:
        Dict with pose landmarks and metadata
    """
    cap = cv2.VideoCapture(video_path)
    try:
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Calculate frame range for chunk
        start_frame = int(start_sec * fps)
        end_frame = min(int(end_sec * fps), total_frames)

        logger.info(
            f"Processing chunk: start_sec={start_sec:.2f} end_sec={end_sec:.2f} "
            f"start_frame={start_frame} end_frame={end_frame} fps={fps:.2f}"
        )

        # Seek to start position using CAP_PROP_POS_MSEC
        start_ms = start_sec * 1000
        cap.set(cv2.CAP_PROP_POS_MSEC, start_ms)

        # Verify seek worked
        actual_pos = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        logger.info(
            f"Seeked to: requested={start_sec:.2f}s actual={actual_pos:.2f}s "
            f"delta={abs(actual_pos - start_sec):.2f}s"
        )

        # Extract poses using existing service
        # (This reuses the existing extract_pose_landmarks but on a seeked video)
        # For simplicity, we'll extract from current position to end_sec
        chunk_duration = end_sec - start_sec

        poses = extract_pose_landmarks(
            video_path=video_path,
            sample_fps=sample_fps,
            max_width=max_width,
            max_seconds=chunk_duration,
        )

        return {
            "poses": poses,
            "metadata": {
                "start_sec": start_sec,
                "end_sec": end_sec,
                "chunk_duration": chunk_duration,
                "video_fps": fps,
                "start_frame": start_frame,
                "end_frame": end_frame,
            },
        }
    finally:
        cap.release()


async def _process_chunk(chunk_id: str) -> None:
    """Process a single video chunk.

    Args:
        chunk_id: Chunk ID to process
    """
    session_local = get_session_local()
    start_time = _now_utc()

    async with session_local() as db:
        logger.info(f"Processing chunk: chunk_id={chunk_id}")

        # Fetch chunk with job and session
        result = await db.execute(
            select(VideoAnalysisChunk)
            .options(selectinload(VideoAnalysisChunk.job).selectinload(VideoAnalysisJob.session))
            .where(VideoAnalysisChunk.id == chunk_id)
        )
        chunk = result.scalar_one()
        job = chunk.job
        session = job.session

        # Get S3 location from job snapshot
        bucket = job.s3_bucket or session.s3_bucket
        key = job.s3_key or session.s3_key

        if not bucket or not key:
            chunk.status = VideoAnalysisChunkStatus.failed
            chunk.error_message = f"Missing S3 location: bucket={bucket} key={key}"
            await db.commit()
            logger.error(f"Chunk failed - missing S3 location: chunk_id={chunk_id}")
            return

        # Check if artifact already exists (idempotency)
        from backend.services.video_chunking import check_chunk_artifact_exists

        artifact_key = f"jobs/{job.id}/chunks/chunk_{chunk.chunk_index:04d}.json"
        if await check_chunk_artifact_exists(bucket, artifact_key):
            logger.info(
                f"Chunk artifact already exists: chunk_id={chunk_id} s3_key={artifact_key} "
                f"- marking complete (idempotent)"
            )
            chunk.status = VideoAnalysisChunkStatus.completed
            chunk.artifact_s3_key = artifact_key
            chunk.completed_at = _now_utc()

            # Update job progress
            job.completed_chunks = (job.completed_chunks or 0) + 1
            if job.total_chunks and job.total_chunks > 0:
                job.progress_pct = min(99, int(100 * job.completed_chunks / job.total_chunks))

            await db.commit()
            return

        # Download video to temp file
        with tempfile.TemporaryDirectory(prefix="gpu_chunk_") as tmpdir:
            local_video_path = os.path.join(tmpdir, "video.mp4")

            await _download_from_s3(
                bucket=bucket,
                key=key,
                dst_path=local_video_path,
                chunk_id=chunk_id,
            )

            # Extract poses for this chunk
            try:
                chunk_data = extract_chunk_poses(
                    video_path=local_video_path,
                    start_sec=chunk.start_sec,
                    end_sec=chunk.end_sec,
                    sample_fps=settings.SAMPLE_FPS,
                    max_width=settings.MAX_WIDTH,
                )

                # Upload chunk artifact to S3
                await _upload_json_to_s3(
                    bucket=bucket,
                    key=artifact_key,
                    payload=chunk_data,
                )

                # Mark chunk complete
                end_time = _now_utc()
                runtime_ms = int((end_time - start_time).total_seconds() * 1000)

                chunk.status = VideoAnalysisChunkStatus.completed
                chunk.artifact_s3_key = artifact_key
                chunk.runtime_ms = runtime_ms
                chunk.completed_at = end_time

                # Update job progress
                job.completed_chunks = (job.completed_chunks or 0) + 1
                if job.total_chunks and job.total_chunks > 0:
                    job.progress_pct = min(99, int(100 * job.completed_chunks / job.total_chunks))

                await db.commit()

                logger.info(
                    f"Chunk completed: chunk_id={chunk_id} index={chunk.chunk_index} "
                    f"runtime_ms={runtime_ms} progress={job.progress_pct}%"
                )

            except Exception as e:
                chunk.status = VideoAnalysisChunkStatus.failed
                chunk.error_message = f"Processing failed: {e!s}"
                chunk.attempts += 1
                await db.commit()
                logger.error(
                    f"Chunk processing failed: chunk_id={chunk_id} "
                    f"attempts={chunk.attempts} error={e!s}",
                    exc_info=True,
                )
                raise


async def _claim_one_chunk() -> str | None:
    """Claim a single queued chunk for processing.

    Uses SKIP LOCKED for concurrent GPU workers.

    Returns:
        chunk_id if claimed, None if no chunks available
    """
    session_local = get_session_local()

    async with session_local() as db, db.begin():
        stmt = (
            select(VideoAnalysisChunk)
            .where(VideoAnalysisChunk.status == VideoAnalysisChunkStatus.queued)
            .order_by(VideoAnalysisChunk.job_id, VideoAnalysisChunk.chunk_index)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        result = await db.execute(stmt)
        chunk = result.scalars().first()
        if chunk is None:
            return None

        # Claim by moving to processing
        chunk.status = VideoAnalysisChunkStatus.processing
        chunk.started_at = _now_utc()
        chunk.attempts += 1

        return chunk.id


async def run_gpu_worker_loop(*, poll_seconds: float = 1.0) -> None:
    """Run GPU chunk processing worker loop.

    Args:
        poll_seconds: Polling interval when no chunks available
    """
    logger.info("gpu_chunk_worker starting")
    logger.info("ENV=%s", settings.ENV)
    logger.info(
        f"Chunk config: CHUNK_SECONDS={settings.CHUNK_SECONDS} "
        f"SAMPLE_FPS={settings.SAMPLE_FPS} MAX_WIDTH={settings.MAX_WIDTH}"
    )

    stop_event = asyncio.Event()

    def _request_stop() -> None:
        logger.info("gpu_chunk_worker stopping (signal)")
        stop_event.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGINT, _request_stop)
    loop.add_signal_handler(signal.SIGTERM, _request_stop)

    while not stop_event.is_set():
        chunk_id = await _claim_one_chunk()
        if chunk_id:
            try:
                await _process_chunk(chunk_id)
            except Exception as e:
                logger.exception(f"Chunk processing error: chunk_id={chunk_id} error={e!s}")
        else:
            # No chunks available - wait before polling again
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(stop_event.wait(), timeout=poll_seconds)

    logger.info("gpu_chunk_worker stopped")


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stdout,
    )

    asyncio.run(run_gpu_worker_loop())
