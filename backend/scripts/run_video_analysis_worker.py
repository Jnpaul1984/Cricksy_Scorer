"""
Video Analysis Worker - Async SQS Consumer

Long-polls SQS queue for video analysis jobs, downloads videos from S3,
runs analysis pipeline (pose extraction, metrics, findings, report),
and persists results to database.

Usage:
    python -m backend.scripts.run_video_analysis_worker

Environment Variables:
    SQS_VIDEO_ANALYSIS_QUEUE_URL - SQS queue URL
    S3_COACH_VIDEOS_BUCKET - S3 bucket for videos
    DATABASE_URL - Database connection string
    LOG_LEVEL - Logging level (default: INFO)
    WORKER_BATCH_SIZE - Messages to process per poll (default: 1)
    WORKER_LONG_POLL_TIMEOUT - SQS wait time in seconds (default: 20)
    WORKER_SLEEP_ON_ERROR - Sleep time after error before retry (default: 5)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.config import settings
from backend.services.pose_service import extract_pose_keypoints_from_video
from backend.services.pose_metrics import compute_pose_metrics
from backend.services.coach_findings import generate_findings
from backend.services.coach_report_service import generate_report_text
from backend.sql_app.models import VideoAnalysisJob, VideoAnalysisJobStatus

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Configuration
BATCH_SIZE = int(os.getenv("WORKER_BATCH_SIZE", "1"))
LONG_POLL_TIMEOUT = int(os.getenv("WORKER_LONG_POLL_TIMEOUT", "20"))
SLEEP_ON_ERROR = int(os.getenv("WORKER_SLEEP_ON_ERROR", "5"))

# AWS clients
s3_client = boto3.client("s3", region_name=settings.AWS_REGION)
sqs_client = boto3.client("sqs", region_name=settings.AWS_REGION)

# Database
engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# ============================================================================
# S3 Download
# ============================================================================


def download_video_from_s3(bucket: str, key: str, local_path: str) -> None:
    """
    Download video from S3 to local path.

    Args:
        bucket: S3 bucket name
        key: S3 object key
        local_path: Local file path to save to

    Raises:
        ClientError: If S3 download fails
    """
    try:
        logger.info(f"Downloading s3://{bucket}/{key} to {local_path}")
        s3_client.download_file(bucket, key, local_path)
        logger.info(f"Downloaded {Path(local_path).stat().st_size} bytes")
    except ClientError as e:
        raise RuntimeError(f"Failed to download video from S3: {str(e)}") from e
    except Exception as e:
        raise RuntimeError(f"Failed to download video: {str(e)}") from e


# ============================================================================
# Analysis Pipeline
# ============================================================================


def run_analysis_pipeline(video_path: str, sample_fps: int = 10) -> dict[str, Any]:
    """
    Run complete analysis pipeline on video.

    Pipeline:
    1. Extract pose keypoints from video
    2. Compute metrics from pose data
    3. Generate findings from metrics
    4. Generate report from findings

    Args:
        video_path: Path to video file
        sample_fps: Frames to sample per second

    Returns:
        dict with keys: pose_data, metrics, findings, report

    Raises:
        Exception: If any step in pipeline fails
    """
    logger.info(f"Starting analysis pipeline for {video_path}")

    try:
        # Step 1: Extract pose keypoints
        logger.info("Step 1/4: Extracting pose keypoints...")
        pose_data = extract_pose_keypoints_from_video(
            video_path=video_path,
            sample_fps=float(sample_fps),
        )
        logger.info(
            f"  Extracted {pose_data.get('pose_summary', {}).get('sampled_frame_count', 0)} frames"
        )

        # Step 2: Compute metrics
        logger.info("Step 2/4: Computing pose metrics...")
        metrics = compute_pose_metrics(pose_data)
        logger.info(f"  Computed {len(metrics.get('metrics', {}))} metrics")

        # Step 3: Generate findings
        logger.info("Step 3/4: Generating findings...")
        findings = generate_findings(metrics)
        logger.info(f"  Generated {len(findings.get('findings', []))} findings")

        # Step 4: Generate report
        logger.info("Step 4/4: Generating report...")
        report = generate_report_text(findings)
        logger.info(f"  Generated report with {len(report.get('top_issues', []))} issues")

        result = {
            "pose": pose_data,
            "metrics": metrics,
            "findings": findings,
            "report": report,
        }

        logger.info("Analysis pipeline complete")
        return result

    except Exception as e:
        logger.error(f"Analysis pipeline failed: {str(e)}", exc_info=True)
        raise


# ============================================================================
# Database Operations
# ============================================================================


async def load_job_from_db(job_id: str, db: AsyncSession) -> VideoAnalysisJob:
    """
    Load VideoAnalysisJob from database.

    Args:
        job_id: Job ID
        db: Database session

    Returns:
        VideoAnalysisJob object

    Raises:
        ValueError: If job not found
    """
    result = await db.execute(select(VideoAnalysisJob).where(VideoAnalysisJob.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise ValueError(f"Job not found in database: {job_id}")

    return job


async def update_job_results(
    job: VideoAnalysisJob,
    results_json: dict[str, Any],
    status: VideoAnalysisJobStatus = VideoAnalysisJobStatus.completed,
    error_message: str | None = None,
    db: AsyncSession | None = None,
) -> None:
    """
    Update job with results and status.

    Args:
        job: VideoAnalysisJob object to update
        results_json: Results from analysis pipeline
        status: Job status (completed or failed)
        error_message: Error message if failed
        db: Database session (required if updating DB)

    Raises:
        ValueError: If db not provided
    """
    if db is None:
        raise ValueError("Database session required to update job")

    job.status = status
    job.results = results_json
    job.completed_at = datetime.now(UTC)
    job.error_message = error_message

    await db.commit()
    logger.info(f"Updated job {job.id} with status {status.value}")


# ============================================================================
# Message Processing
# ============================================================================


async def process_message(
    message: dict[str, Any],
    receipt_handle: str,
    db: AsyncSession,
) -> bool:
    """
    Process a single SQS message.

    Message body format:
    {
        "job_id": "uuid",
        "session_id": "uuid",
        "sample_fps": 10,
        "include_frames": true
    }

    Args:
        message: Message body (dict)
        receipt_handle: SQS receipt handle
        db: Database session

    Returns:
        True if message should be deleted, False to retry
    """
    job_id = message.get("job_id")
    session_id = message.get("session_id")
    sample_fps = message.get("sample_fps", 10)

    logger.info(f"Processing message for job {job_id}, session {session_id}")

    try:
        # Load job from database
        job = await load_job_from_db(job_id, db)
        logger.info(f"Loaded job {job_id}, status: {job.status.value}")

        # Update status to processing
        job.status = VideoAnalysisJobStatus.processing
        job.started_at = datetime.now(UTC)
        await db.commit()

        # Check that we have s3_key (set during upload initiate)
        if not job.session or not job.session.s3_key:
            raise ValueError(f"Job {job_id} missing S3 key")

        s3_bucket = settings.S3_COACH_VIDEOS_BUCKET
        s3_key = job.session.s3_key

        # Download video to temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            video_path = Path(tmpdir) / "video.mp4"
            download_video_from_s3(s3_bucket, s3_key, str(video_path))

            # Run analysis pipeline
            results = run_analysis_pipeline(
                video_path=str(video_path),
                sample_fps=sample_fps,
            )

            # Persist results to database
            await update_job_results(
                job=job,
                results_json=results,
                status=VideoAnalysisJobStatus.completed,
                db=db,
            )

        logger.info(f"Successfully processed job {job_id}")
        return True

    except ValueError as e:
        # Job not found or missing data
        logger.error(f"Invalid job data: {str(e)}")
        try:
            job = await load_job_from_db(job_id, db)
            await update_job_results(
                job=job,
                results_json={},
                status=VideoAnalysisJobStatus.failed,
                error_message=f"Invalid job: {str(e)}",
                db=db,
            )
        except Exception:
            pass
        # Still delete message - no point retrying invalid jobs
        return True

    except Exception as e:
        # Processing error - update job status and don't delete message (will retry)
        logger.error(f"Failed to process job {job_id}: {str(e)}", exc_info=True)
        try:
            job = await load_job_from_db(job_id, db)
            await update_job_results(
                job=job,
                results_json={},
                status=VideoAnalysisJobStatus.failed,
                error_message=f"Processing failed: {str(e)}",
                db=db,
            )
        except Exception:
            pass
        # Don't delete - retry
        return False


# ============================================================================
# SQS Polling
# ============================================================================


async def receive_messages() -> list[dict[str, Any]]:
    """
    Long-poll SQS queue for messages.

    Returns:
        List of messages with keys: id, receipt_handle, body
    """
    try:
        response = sqs_client.receive_message(
            QueueUrl=settings.SQS_VIDEO_ANALYSIS_QUEUE_URL,
            MaxNumberOfMessages=BATCH_SIZE,
            WaitTimeSeconds=LONG_POLL_TIMEOUT,
        )

        messages = []
        for msg in response.get("Messages", []):
            try:
                body = json.loads(msg.get("Body", "{}"))
            except json.JSONDecodeError:
                body = msg.get("Body")

            messages.append({
                "id": msg.get("MessageId"),
                "receipt_handle": msg.get("ReceiptHandle"),
                "body": body,
            })

        if messages:
            logger.info(f"Received {len(messages)} message(s) from SQS")
        return messages

    except ClientError as e:
        logger.error(f"Failed to receive messages from SQS: {str(e)}")
        return []


def delete_message(receipt_handle: str) -> bool:
    """
    Delete message from SQS queue.

    Args:
        receipt_handle: Message receipt handle

    Returns:
        True if deleted, False if failed
    """
    try:
        sqs_client.delete_message(
            QueueUrl=settings.SQS_VIDEO_ANALYSIS_QUEUE_URL,
            ReceiptHandle=receipt_handle,
        )
        logger.info(f"Deleted message {receipt_handle[:20]}...")
        return True
    except ClientError as e:
        logger.error(f"Failed to delete message: {str(e)}")
        return False


# ============================================================================
# Main Worker Loop
# ============================================================================


async def worker_loop() -> None:
    """
    Main worker loop: long-poll SQS, process messages, update DB.
    """
    logger.info("Starting video analysis worker")
    logger.info(f"Queue URL: {settings.SQS_VIDEO_ANALYSIS_QUEUE_URL}")
    logger.info(f"S3 bucket: {settings.S3_COACH_VIDEOS_BUCKET}")
    logger.info(f"Batch size: {BATCH_SIZE}, Long poll timeout: {LONG_POLL_TIMEOUT}s")

    while True:
        try:
            # Receive messages from SQS
            messages = await receive_messages()

            if not messages:
                # No messages - continue polling
                continue

            # Process each message
            async with AsyncSessionLocal() as db:
                for msg in messages:
                    receipt_handle = msg.get("receipt_handle")
                    message_body = msg.get("body")

                    # Process message
                    success = await process_message(message_body, receipt_handle, db)

                    # Delete message if processing succeeded
                    if success:
                        delete_message(receipt_handle)
                    else:
                        logger.warning(f"Message {receipt_handle[:20]}... will be retried")

        except Exception as e:
            logger.error(f"Worker error: {str(e)}", exc_info=True)
            await asyncio.sleep(SLEEP_ON_ERROR)


def main() -> None:
    """Entry point."""
    try:
        # Verify configuration
        if not settings.SQS_VIDEO_ANALYSIS_QUEUE_URL:
            raise ValueError("SQS_VIDEO_ANALYSIS_QUEUE_URL not configured")
        if not settings.S3_COACH_VIDEOS_BUCKET:
            raise ValueError("S3_COACH_VIDEOS_BUCKET not configured")

        logger.info("Configuration valid, starting worker")

        # Run async worker loop
        asyncio.run(worker_loop())

    except KeyboardInterrupt:
        logger.info("Worker interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
