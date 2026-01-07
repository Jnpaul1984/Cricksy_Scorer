"""Chunk aggregation utilities for CPU worker.

Aggregates completed GPU chunk artifacts into final analysis report.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, cast

import boto3
from backend.config import settings
from backend.services.coach_findings import generate_findings
from backend.services.coach_report_service import generate_report_text
from backend.services.pose_metrics import build_pose_metric_evidence, compute_pose_metrics
from backend.sql_app.models import VideoAnalysisChunk, VideoAnalysisJob
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def _download_json_from_s3(bucket: str, key: str) -> dict[str, Any]:
    """Download JSON artifact from S3.

    Args:
        bucket: S3 bucket name
        key: S3 object key

    Returns:
        Parsed JSON payload
    """
    s3 = cast(Any, boto3.client("s3", region_name=settings.AWS_REGION))
    loop = asyncio.get_running_loop()

    def _get() -> dict[str, Any]:
        response = s3.get_object(Bucket=bucket, Key=key)
        body = response["Body"].read()
        return json.loads(body)

    return await loop.run_in_executor(None, _get)


async def _upload_json_to_s3(*, bucket: str, key: str, payload: dict[str, Any]) -> None:
    """Upload JSON payload to S3."""
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


def _merge_chunk_poses(chunks_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge pose landmarks from all chunks into single timeline.

    Args:
        chunks_data: List of chunk payloads (sorted by chunk_index)

    Returns:
        Combined list of pose frames
    """
    all_frames = []

    for chunk in chunks_data:
        poses = chunk.get("poses", [])
        if isinstance(poses, list):
            all_frames.extend(poses)

    logger.info(f"Merged {len(chunks_data)} chunks into {len(all_frames)} total pose frames")
    return all_frames


def _compute_aggregated_metrics(
    all_frames: list[dict[str, Any]], video_duration: float
) -> dict[str, Any]:
    """Compute metrics from aggregated pose data.

    Args:
        all_frames: Combined pose frames from all chunks
        video_duration: Total video duration in seconds

    Returns:
        Metrics dict compatible with compute_pose_metrics
    """
    frames_with_pose = sum(1 for f in all_frames if f.get("landmarks"))
    total_frames = len(all_frames)
    detection_rate = (frames_with_pose / total_frames * 100) if total_frames > 0 else 0

    # Build pose payload compatible with metrics service
    pose_payload = {
        "frames": all_frames,
        "total_frames": total_frames,
        "sampled_frames": total_frames,
        "frames_with_pose": frames_with_pose,
        "detection_rate_percent": detection_rate,
        "video_fps": 30.0,  # Approximate - not critical for metrics
        "model": "MediaPipe Pose Landmarker Full",
        "summary": {
            "total_frames": total_frames,
            "sampled_frames": total_frames,
            "frames_with_pose": frames_with_pose,
            "detection_rate_percent": detection_rate,
            "video_fps": 30.0,
            "model": "MediaPipe Pose Landmarker Full",
        },
    }

    metrics_result = compute_pose_metrics(pose_payload)

    # Add evidence markers
    try:
        evidence = build_pose_metric_evidence(pose_payload, metrics_result)
        metrics_result.setdefault("evidence", evidence)
    except Exception:
        logger.exception("Failed to compute evidence markers")

    return metrics_result


async def aggregate_chunks_and_finalize(db: AsyncSession, job: VideoAnalysisJob) -> None:
    """Aggregate completed chunks and finalize job.

    Args:
        db: Database session
        job: Job with all chunks completed
    """
    logger.info(
        f"Aggregating chunks for job: job_id={job.id} "
        f"total_chunks={job.total_chunks} completed={job.completed_chunks}"
    )

    # Fetch all chunks (ordered by index)
    result = await db.execute(
        select(VideoAnalysisChunk)
        .where(VideoAnalysisChunk.job_id == job.id)
        .order_by(VideoAnalysisChunk.chunk_index)
    )
    chunks = result.scalars().all()

    # Get S3 location
    session = await db.get(type(job.session), job.session.id)
    bucket = job.s3_bucket or session.s3_bucket

    if not bucket:
        raise ValueError(f"Missing S3 bucket for job {job.id}")

    # Download all chunk artifacts
    chunks_data = []
    for chunk in chunks:
        if not chunk.artifact_s3_key:
            raise ValueError(
                f"Chunk {chunk.id} missing artifact_s3_key (status={chunk.status.value})"
            )

        chunk_payload = await _download_json_from_s3(bucket, chunk.artifact_s3_key)
        chunks_data.append(chunk_payload)

    # Merge poses from all chunks
    all_frames = _merge_chunk_poses(chunks_data)

    # Compute aggregated metrics
    metrics_result = _compute_aggregated_metrics(all_frames, job.video_duration_seconds or 0)

    # Generate findings and report
    findings_result = generate_findings(metrics_result)
    report_result = cast(dict[str, Any], generate_report_text(findings_result, None))

    # Build final results payload
    final_results = {
        "pose_summary": {
            "total_frames": len(all_frames),
            "sampled_frames": len(all_frames),
            "frames_with_pose": sum(1 for f in all_frames if f.get("landmarks")),
            "detection_rate_percent": metrics_result.get("detection_rate_percent", 0),
            "video_fps": 30.0,
            "model": "MediaPipe Pose Landmarker Full",
        },
        "metrics": metrics_result,
        "findings": findings_result,
        "report": report_result,
        "meta": {
            "processing_mode": "gpu_chunked",
            "total_chunks": job.total_chunks,
            "video_duration_seconds": job.video_duration_seconds,
        },
    }

    # Upload final report to S3
    final_key = f"jobs/{job.id}/final_results.json"
    await _upload_json_to_s3(bucket=bucket, key=final_key, payload=final_results)

    # Update job with final results
    job.deep_results = {
        **final_results,
        "outputs": {"deep_results_s3_key": final_key},
    }
    job.results = {"deep": job.deep_results}  # Legacy compat

    logger.info(
        f"Chunk aggregation complete: job_id={job.id} "
        f"total_frames={len(all_frames)} s3_key={final_key}"
    )
