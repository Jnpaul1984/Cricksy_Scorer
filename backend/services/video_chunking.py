"""Video chunking utilities for parallel GPU processing."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import boto3
import cv2
from botocore.exceptions import ClientError

from backend.config import settings

logger = logging.getLogger(__name__)


def get_video_duration(video_path: str) -> float:
    """Extract video duration in seconds using OpenCV.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds

    Raises:
        ValueError: If video cannot be opened or duration cannot be determined
    """
    cap = cv2.VideoCapture(video_path)
    try:
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if fps <= 0 or frame_count <= 0:
            raise ValueError(
                f"Invalid video metadata: fps={fps} frame_count={frame_count} path={video_path}"
            )

        duration = frame_count / fps
        logger.info(
            f"Video duration extracted: path={video_path} "
            f"duration={duration:.2f}s fps={fps} frames={frame_count}"
        )
        return duration
    finally:
        cap.release()


async def get_video_duration_from_s3(bucket: str, key: str, local_path: str) -> float:
    """Download video from S3 and extract duration.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        local_path: Local path to download video to

    Returns:
        Duration in seconds

    Raises:
        ClientError: S3 download failed
        ValueError: Duration extraction failed
    """
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    loop = asyncio.get_running_loop()

    logger.info(f"Downloading video for duration check: bucket={bucket} key={key}")

    def _download() -> None:
        s3.download_file(bucket, key, local_path)

    await loop.run_in_executor(None, _download)

    return get_video_duration(local_path)


def create_chunk_specs(
    duration_seconds: float, chunk_seconds: int = 30
) -> list[dict[str, Any]]:
    """Create chunk specifications for video processing.

    Args:
        duration_seconds: Total video duration
        chunk_seconds: Target chunk duration (default 30s)

    Returns:
        List of chunk specs: [{"index": 0, "start_sec": 0.0, "end_sec": 30.0}, ...]
    """
    if duration_seconds <= 0:
        raise ValueError(f"Invalid duration: {duration_seconds}")

    if chunk_seconds <= 0:
        raise ValueError(f"Invalid chunk_seconds: {chunk_seconds}")

    chunks = []
    current = 0.0
    index = 0

    while current < duration_seconds:
        end = min(current + chunk_seconds, duration_seconds)
        chunks.append({
            "index": index,
            "start_sec": current,
            "end_sec": end,
        })
        current = end
        index += 1

    logger.info(
        f"Created {len(chunks)} chunks: duration={duration_seconds:.2f}s "
        f"chunk_size={chunk_seconds}s"
    )
    return chunks


async def check_chunk_artifact_exists(bucket: str, key: str) -> bool:
    """Check if chunk artifact exists in S3 (for idempotency).

    Args:
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        True if artifact exists, False otherwise
    """
    s3 = boto3.client("s3", region_name=settings.AWS_REGION)
    loop = asyncio.get_running_loop()

    def _check() -> bool:
        try:
            s3.head_object(Bucket=bucket, Key=key)
            return True
        except ClientError as e:
            if e.response.get("Error", {}).get("Code") == "404":
                return False
            raise

    return await loop.run_in_executor(None, _check)
