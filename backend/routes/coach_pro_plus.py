"""
Coach Pro Plus Routes - Video Sessions Scaffolding

Provides placeholder endpoints for video session management.
Real video upload/streaming will be implemented in future phases.
Feature-gated by role (coach_pro_plus, org_pro).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

import boto3
from backend import security
from backend.config import settings
from backend.services.coach_findings import generate_findings
from backend.services.coach_report_service import generate_report_text
from backend.services.pose_metrics import build_pose_metric_evidence, compute_pose_metrics
from backend.services.s3_service import s3_service
from backend.services.video_chunking import (
    create_chunk_specs,
    get_video_duration_from_s3,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import (
    OwnerTypeEnum,
    RoleEnum,
    TargetZone,
    User,
    VideoAnalysisChunk,
    VideoAnalysisChunkStatus,
    VideoAnalysisJob,
    VideoAnalysisJobStatus,
    VideoSession,
    VideoSessionStatus,
)
from botocore.exceptions import ClientError
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/api/coaches/plus", tags=["coach_pro_plus"])

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


async def _check_feature_access(user: User, feature: str) -> bool:
    """Check if user has access to a specific feature."""
    # coach_pro_plus and org_pro have video features
    if user.role in (RoleEnum.coach_pro_plus, RoleEnum.org_pro):
        return True
    # Superuser always has access
    return bool(user.is_superuser)


# ============================================================================
# Schemas (Pydantic Models)
# ============================================================================


class VideoSessionCreate(BaseModel):
    """Request schema for creating a video session"""

    title: str
    player_ids: list[str] = []
    notes: str | None = None
    analysis_context: str | None = None  # batting, bowling, wicketkeeping, fielding, mixed
    camera_view: str | None = None  # side, front, behind, other


class VideoSessionRead(BaseModel):
    """Response schema for a video session"""

    id: str
    owner_type: str  # "coach" or "org"
    owner_id: str
    title: str
    player_ids: list[str]
    status: str  # "pending", "uploaded", "processing", "ready", "failed"
    notes: str | None = None
    analysis_context: str | None = None  # batting, bowling, wicketkeeping, fielding, mixed
    camera_view: str | None = None  # side, front, behind, other
    s3_bucket: str | None = None
    s3_key: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoStreamUrlRead(BaseModel):
    """Response schema for a short-lived presigned GET URL."""

    video_url: str
    expires_in: int
    bucket: str
    key: str


class VideoAnalysisJobRead(BaseModel):
    """Response schema for a video analysis job"""

    id: str
    session_id: str
    sample_fps: int
    include_frames: bool
    status: str  # "queued", "processing", "completed", "failed"
    stage: str | None = None
    progress_pct: int = 0
    error_message: str | None = None
    sqs_message_id: str | None = None

    # Session context (denormalized for frontend convenience)
    analysis_context: str | None = None
    camera_view: str | None = None

    # Legacy combined results (kept for backward compatibility)
    results: dict | None = None

    # New staged results
    quick_results: dict | None = None
    deep_results: dict | None = None

    # Extracted artifacts for frontend consumption
    quick_findings: dict | None = None
    quick_report: dict | None = None
    deep_findings: dict | None = None
    deep_report: dict | None = None

    # S3 keys for downloading full results
    quick_results_s3_key: str | None = None
    deep_results_s3_key: str | None = None

    # PDF export
    pdf_s3_key: str | None = None
    pdf_generated_at: datetime | None = None

    # Presigned URLs for downloading results (computed per-request, short-lived)
    quick_results_url: str | None = None
    deep_results_url: str | None = None

    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime

    # Optional short-lived streaming URL (computed per-request; never persisted)
    video_stream: VideoStreamUrlRead | None = None

    class Config:
        from_attributes = True


class VideoUploadInitiateRequest(BaseModel):
    """Request schema for initiating a video upload"""

    session_id: str
    sample_fps: int = Field(default=10, ge=1, le=30)
    include_frames: bool = Field(default=False)
    analysis_mode: str | None = Field(
        default=None,
        pattern="^(batting|bowling|wicketkeeping|fielding|mixed)$",
        description="Analysis mode for the video job",
    )


class VideoUploadInitiateResponse(BaseModel):
    """Response schema for upload initiate with presigned URL"""

    job_id: str
    session_id: str
    presigned_url: str
    expires_in: int
    s3_bucket: str
    s3_key: str


class VideoUploadCompleteRequest(BaseModel):
    """Request schema for completing a video upload"""

    job_id: str


class VideoUploadCompleteResponse(BaseModel):
    """Response schema for upload completion"""

    job_id: str
    status: str
    sqs_message_id: str | None = None
    message: str


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/sessions", response_model=VideoSessionRead)
async def create_video_session(
    session_data: VideoSessionCreate,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoSessionRead:
    """
    Create a new video session (Coach Pro Plus feature).

    Feature-gated: Requires coach_pro_plus role.
    Stores in database with S3 bucket/key placeholders and pending status.
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_upload_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_upload_enabled",
        )

    # Verify user is coach_pro_plus, org_pro, or superuser
    if (
        current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro)
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can create video sessions",
        )

    # Determine ownership type and ID
    # If user is org_pro and has org_id, use org ownership; otherwise use coach ownership
    if current_user.role == RoleEnum.org_pro and current_user.org_id:
        owner_type = OwnerTypeEnum.org
        owner_id = current_user.org_id
    else:
        # coach_pro_plus, coach_pro, or superuser - use personal ownership
        # Also fallback to personal if org_pro but no org_id
        owner_type = OwnerTypeEnum.coach
        owner_id = current_user.id

    # Create database record
    session = VideoSession(
        owner_type=owner_type,
        owner_id=owner_id,
        title=session_data.title,
        player_ids=session_data.player_ids,
        notes=session_data.notes,
        analysis_context=session_data.analysis_context,
        camera_view=session_data.camera_view,
        status=VideoSessionStatus.pending,
        s3_bucket=None,  # Will be populated after upload
        s3_key=None,  # Will be populated after upload
    )

    db.add(session)
    await db.commit()
    await db.refresh(session)

    return VideoSessionRead.model_validate(session)


@router.get("/sessions", response_model=list[VideoSessionRead])
async def list_video_sessions(
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(
        None,
        description="Filter by status: pending, uploaded, processing, ready, failed",
    ),
    exclude_failed: bool = Query(
        False,
        description="Exclude failed sessions to improve performance",
    ),
) -> list[VideoSessionRead]:
    """
    List video sessions for the current user (Coach Pro Plus feature).

    Feature-gated: Requires coach_pro_plus role.
    Returns sessions owned by the user or their organization.

    Performance tip: Use exclude_failed=true to hide old failed sessions.
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # Verify user is coach_pro_plus, org_pro, or superuser
    if (
        current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro)
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can view video sessions",
        )

    # Build query based on user role
    if current_user.is_superuser:
        # Superusers see all sessions
        query = select(VideoSession)
    elif current_user.role == RoleEnum.org_pro:
        # Org users see all sessions for their org
        query = select(VideoSession).where(
            (VideoSession.owner_type == OwnerTypeEnum.org)
            & (VideoSession.owner_id == current_user.org_id)
        )
    else:
        # Coach users see only their own sessions
        query = select(VideoSession).where(VideoSession.owner_id == current_user.id)

    # Apply status filters (performance optimization)
    if exclude_failed:
        query = query.where(VideoSession.status != VideoSessionStatus.failed)

    if status_filter:
        try:
            status_enum = VideoSessionStatus(status_filter)
            query = query.where(VideoSession.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status_filter}. Valid values: {', '.join(s.value for s in VideoSessionStatus)}",
            )

    # Apply pagination
    query = query.offset(offset).limit(limit).order_by(VideoSession.created_at.desc())

    result = await db.execute(query)
    sessions = result.scalars().all()

    return [VideoSessionRead.model_validate(session) for session in sessions]


@router.get("/sessions/{session_id}", response_model=VideoSessionRead)
async def get_video_session(
    session_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoSessionRead:
    """
    Get a specific video session (Coach Pro Plus feature).

    Feature-gated: Requires coach_pro_plus role.
    Checks ownership before returning session details.
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # Verify user is coach_pro_plus, org_pro, or superuser
    if (
        current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro)
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can access video sessions",
        )

    # Fetch session from database
    result = await db.execute(select(VideoSession).where(VideoSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    # Verify ownership
    if current_user.role == RoleEnum.coach_pro_plus:
        # Coach must own the session
        if session.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )
    else:
        # Org users see org sessions
        if session.owner_type == OwnerTypeEnum.org and session.owner_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )

    return VideoSessionRead.model_validate(session)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_video_session(
    session_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Delete a video session and all its associated data (Coach Pro Plus feature).

    This will:
    - Delete the VideoSession record
    - Cascade delete all VideoAnalysisJobs
    - Cascade delete all VideoAnalysisChunks
    - Optionally delete the S3 video file (if present)
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # Verify user is coach_pro_plus, org_pro, or superuser
    if (
        current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro)
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can delete video sessions",
        )

    # Fetch session from database
    result = await db.execute(select(VideoSession).where(VideoSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    # Verify ownership (same logic as get_video_session)
    if current_user.role == RoleEnum.coach_pro_plus:
        if session.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )
    elif not current_user.is_superuser:  # org_pro users
        if session.owner_type == OwnerTypeEnum.org and session.owner_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )

    # Delete S3 video file if present (best effort - don't fail if S3 delete fails)
    if session.s3_bucket and session.s3_key:
        try:
            s3_service.delete_object(session.s3_bucket, session.s3_key)
            logger.info(
                f"Deleted S3 object: s3://{session.s3_bucket}/{session.s3_key} for session {session_id}"
            )
        except Exception as e:
            logger.warning(
                f"Failed to delete S3 object for session {session_id}: {e} (continuing with DB delete)"
            )

    # Delete from database (cascade will handle analysis_jobs and chunks)
    await db.delete(session)
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/sessions/bulk", status_code=status.HTTP_200_OK)
async def bulk_delete_sessions(
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(
        None,
        description="Only delete sessions with this status (failed, pending, etc.)",
    ),
    older_than_days: int | None = Query(
        None,
        ge=1,
        description="Only delete sessions older than N days",
    ),
) -> dict[str, Any]:
    """
    Bulk delete old/failed video sessions to free up storage and improve performance.

    Safety features:
    - Only deletes YOUR sessions (or your org's)
    - Supports filtering by status (e.g., failed, pending)
    - Supports filtering by age (e.g., older than 30 days)
    - Returns count of deleted sessions
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # Build query based on ownership
    if current_user.is_superuser:
        query = select(VideoSession)
    elif current_user.role == RoleEnum.org_pro:
        query = select(VideoSession).where(
            (VideoSession.owner_type == OwnerTypeEnum.org)
            & (VideoSession.owner_id == current_user.org_id)
        )
    else:
        query = select(VideoSession).where(VideoSession.owner_id == current_user.id)

    # Apply filters
    if status_filter:
        # Validate status
        try:
            status_enum = VideoSessionStatus(status_filter)
            query = query.where(VideoSession.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status_filter}. Must be one of: {', '.join(s.value for s in VideoSessionStatus)}",
            )

    if older_than_days:
        from datetime import datetime, timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=older_than_days)
        query = query.where(VideoSession.created_at < cutoff_date)

    # Fetch sessions to delete
    result = await db.execute(query)
    sessions_to_delete = result.scalars().all()

    deleted_count = 0
    s3_deleted_count = 0

    for session in sessions_to_delete:
        # Delete S3 file if present (best effort)
        if session.s3_bucket and session.s3_key:
            try:
                s3_service.delete_object(session.s3_bucket, session.s3_key)
                s3_deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete S3 object for session {session.id}: {e}")

        await db.delete(session)
        deleted_count += 1

    await db.commit()

    return {
        "deleted_count": deleted_count,
        "s3_files_deleted": s3_deleted_count,
        "filters_applied": {
            "status": status_filter,
            "older_than_days": older_than_days,
        },
    }


# ============================================================================
# Video Analysis Jobs (Database-backed)
# ============================================================================


@router.post("/sessions/{session_id}/analysis-jobs", response_model=VideoAnalysisJobRead)
async def create_analysis_job(
    session_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    sample_fps: int = Query(10, ge=1, le=30),
    include_frames: bool = Query(False),
    analysis_mode: str | None = Query(None, pattern="^(batting|bowling|wicketkeeping)$"),
) -> VideoAnalysisJobRead:
    """
    Create a video analysis job for a session.

    The job is queued in the database for background processing.

    Args:
        analysis_mode: Optional analysis mode (batting, bowling, or wicketkeeping).
                      Determines which findings/drills are generated.
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_analysis_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_analysis_enabled",
        )

    # Verify user can access this session
    result = await db.execute(select(VideoSession).where(VideoSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    # Check ownership
    if current_user.role == RoleEnum.coach_pro_plus and session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this session",
        )

    # Create analysis job
    job = VideoAnalysisJob(
        session_id=session_id,
        sample_fps=sample_fps,
        include_frames=include_frames,
        status=VideoAnalysisJobStatus.queued,
        stage="QUEUED",
        progress_pct=0,
        deep_enabled=bool(settings.COACH_PLUS_DEEP_ANALYSIS_ENABLED),
        analysis_mode=analysis_mode,  # Store analysis mode
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    return VideoAnalysisJobRead.model_validate(job)


@router.get("/sessions/{session_id}/analysis-jobs", response_model=list[VideoAnalysisJobRead])
async def list_analysis_jobs(
    session_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> list[VideoAnalysisJobRead]:
    """
    List analysis jobs for a session.
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_analysis_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_analysis_enabled",
        )

    # Verify user can access this session
    result = await db.execute(select(VideoSession).where(VideoSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    # Check ownership
    if current_user.role == RoleEnum.coach_pro_plus and session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this session",
        )

    # List jobs for this session
    result = await db.execute(
        select(VideoAnalysisJob)
        .options(selectinload(VideoAnalysisJob.session))
        .where(VideoAnalysisJob.session_id == session_id)
        .order_by(VideoAnalysisJob.created_at.desc())
    )
    jobs = result.scalars().all()

    # Add session context to each job response
    job_reads = []
    for job in jobs:
        job_read = VideoAnalysisJobRead.model_validate(job)
        job_read = job_read.model_copy(
            update={
                "analysis_context": session.analysis_context,
                "camera_view": session.camera_view,
            }
        )
        job_reads.append(job_read)

    return job_reads


@router.get(
    "/video-sessions/{session_id}/analysis-history", response_model=list[VideoAnalysisJobRead]
)
async def get_analysis_history(
    session_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> list[VideoAnalysisJobRead]:
    """
    Get analysis history for a video session (alias for list_analysis_jobs).
    Returns jobs ordered by created_at descending (newest first).
    """
    return await list_analysis_jobs(session_id, current_user, db)


@router.get("/analysis-jobs/{job_id}", response_model=VideoAnalysisJobRead)
async def get_analysis_job(
    job_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoAnalysisJobRead:
    """
    Get a specific analysis job with results.
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_analysis_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_analysis_enabled",
        )

    # Fetch job (eager-load session to avoid async lazy-load / MissingGreenlet)
    result = await db.execute(
        select(VideoAnalysisJob)
        .options(selectinload(VideoAnalysisJob.session))
        .where(VideoAnalysisJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    # Check ownership via session
    session = job.session
    if current_user.role == RoleEnum.coach_pro_plus and session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job",
        )

    job_read = VideoAnalysisJobRead.model_validate(job)

    # Best-effort: attach presigned URLs for results and video
    try:
        # Generate presigned URLs for S3 results if available
        updates = {}

        # Add session context to job response
        updates["analysis_context"] = session.analysis_context
        updates["camera_view"] = session.camera_view

        if job.quick_results_s3_key:
            quick_url = s3_service.generate_presigned_get_url(
                bucket=settings.S3_COACH_VIDEOS_BUCKET,
                key=job.quick_results_s3_key,
                expires_in=settings.S3_STREAM_URL_EXPIRES_SECONDS,
            )
            updates["quick_results_url"] = quick_url

        if job.deep_results_s3_key:
            deep_url = s3_service.generate_presigned_get_url(
                bucket=settings.S3_COACH_VIDEOS_BUCKET,
                key=job.deep_results_s3_key,
                expires_in=settings.S3_STREAM_URL_EXPIRES_SECONDS,
            )
            updates["deep_results_url"] = deep_url

        # Attach video streaming URL for this single job
        if session.s3_bucket and session.s3_key:
            expires_in = settings.S3_STREAM_URL_EXPIRES_SECONDS
            url = s3_service.generate_presigned_get_url(
                bucket=session.s3_bucket,
                key=session.s3_key,
                expires_in=expires_in,
            )
            updates["video_stream"] = VideoStreamUrlRead(
                video_url=url,
                expires_in=expires_in,
                bucket=session.s3_bucket,
                key=session.s3_key,
            )

        # Apply all updates at once if any
        if updates:
            job_read = job_read.model_copy(update=updates)

    except Exception:
        # Graceful degradation: preserve existing response shape without URLs
        pass

    return job_read


class PdfExportResponse(BaseModel):
    """Response schema for PDF export"""

    job_id: str
    pdf_url: str
    expires_in: int
    pdf_s3_key: str
    pdf_size_bytes: int


@router.post("/analysis-jobs/{job_id}/export-pdf", response_model=PdfExportResponse)
async def export_analysis_pdf(
    job_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> PdfExportResponse:
    """
    Generate and export a PDF report for a video analysis job.

    Creates a PDF from available analysis data (results JSON + findings),
    uploads it to S3, and returns a presigned download URL.
    """
    from backend.services.pdf_export_service import generate_analysis_pdf

    # Verify feature access
    if not await _check_feature_access(current_user, "video_analysis_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_analysis_enabled",
        )

    # Fetch job with session
    result = await db.execute(
        select(VideoAnalysisJob)
        .options(selectinload(VideoAnalysisJob.session))
        .where(VideoAnalysisJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    # Check ownership via session
    session = job.session
    if current_user.role == RoleEnum.coach_pro_plus and session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job",
        )

    # Block export if job is not completed
    terminal_success_states = {
        VideoAnalysisJobStatus.completed,
        VideoAnalysisJobStatus.done,
    }
    if job.status not in terminal_success_states:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot export PDF: job status is {job.status.value}, must be completed",
        )

    # Generate PDF from available data
    try:
        pdf_bytes = generate_analysis_pdf(
            job_id=job.id,
            session_title=session.title,
            status=job.status.value,
            quick_findings=job.quick_findings,
            deep_findings=job.deep_findings,
            quick_results=job.quick_results,
            deep_results=job.deep_results,
            created_at=job.created_at,
            completed_at=job.completed_at,
            analysis_mode=job.analysis_mode,
            coach_goals=job.coach_goals,
            outcomes=job.outcomes,
        )

        pdf_size_bytes = len(pdf_bytes)
        logger.info(
            f"Generated PDF for job {job_id}: {pdf_size_bytes} bytes ({pdf_size_bytes / 1024:.2f} KB)"
        )

    except Exception as e:
        logger.error(f"Failed to generate PDF for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF: {e!s}",
        )

    # Upload PDF to S3
    pdf_s3_key = f"jobs/{job_id}/exports/report.pdf"
    try:
        s3_service.upload_file_obj(
            file_obj=pdf_bytes,
            bucket=settings.S3_COACH_VIDEOS_BUCKET,
            key=pdf_s3_key,
            content_type="application/pdf",
        )
        logger.info(
            f"Uploaded PDF to S3: bucket={settings.S3_COACH_VIDEOS_BUCKET}, key={pdf_s3_key}"
        )

    except Exception as e:
        logger.error(f"Failed to upload PDF to S3 for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload PDF: {e!s}",
        )

    # Update job with PDF metadata
    job.pdf_s3_key = pdf_s3_key
    job.pdf_generated_at = (
        datetime.now(datetime.UTC) if hasattr(datetime, "UTC") else datetime.utcnow()
    )
    await db.commit()

    # Generate presigned download URL
    expires_in = settings.S3_STREAM_URL_EXPIRES_SECONDS
    pdf_url = s3_service.generate_presigned_get_url(
        bucket=settings.S3_COACH_VIDEOS_BUCKET,
        key=pdf_s3_key,
        expires_in=expires_in,
    )

    return PdfExportResponse(
        job_id=job_id,
        pdf_url=pdf_url,
        expires_in=expires_in,
        pdf_s3_key=pdf_s3_key,
        pdf_size_bytes=pdf_size_bytes,
    )


# ============================================================================
# Phase 2: Coach Goals and Outcomes Endpoints
# ============================================================================


class SetGoalsRequest(BaseModel):
    """Request schema for setting coach goals on a job."""

    zones: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Zone goals: [{zone_id, target_accuracy}, ...]",
    )
    metrics: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Metric goals: [{code, target_score}, ...]",
    )


class OutcomesResponse(BaseModel):
    """Response schema for outcomes."""

    zones: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    overall_compliance_pct: float


class CompareJobsRequest(BaseModel):
    """Request schema for comparing multiple jobs."""

    job_ids: list[str] = Field(description="List of job IDs to compare")


class CompareJobsResponse(BaseModel):
    """Response schema for job comparison."""

    timeline: list[dict[str, Any]]
    deltas: list[dict[str, Any]]
    persistent_issues: list[dict[str, Any]]


@router.post("/analysis-jobs/{job_id}/set-goals")
async def set_job_goals(
    job_id: str,
    request: SetGoalsRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Set coach-defined goals for an analysis job.

    Goals can be set before or after analysis completion.
    Includes zone accuracy targets and metric performance thresholds.
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_analysis_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_analysis_enabled",
        )

    # Fetch job with session
    result = await db.execute(
        select(VideoAnalysisJob)
        .options(selectinload(VideoAnalysisJob.session))
        .where(VideoAnalysisJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    # Check ownership via session
    session = job.session
    if current_user.role == RoleEnum.coach_pro_plus and session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job",
        )

    # Save goals
    coach_goals = {
        "zones": request.zones,
        "metrics": request.metrics,
    }
    job.coach_goals = coach_goals
    await db.commit()
    await db.refresh(job)

    logger.info(
        f"Set goals for job {job_id}: {len(request.zones)} zones, {len(request.metrics)} metrics"
    )

    return {
        "job_id": job_id,
        "coach_goals": job.coach_goals,
        "message": "Goals saved successfully",
    }


@router.post("/analysis-jobs/{job_id}/calculate-compliance", response_model=OutcomesResponse)
async def calculate_job_compliance(
    job_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> OutcomesResponse:
    """Calculate compliance of analysis results against coach-defined goals.

    Compares actual zone accuracy and metric scores to target thresholds.
    Saves outcomes to job for future retrieval.
    """
    from backend.services.goal_compliance import calculate_compliance

    # Verify feature access
    if not await _check_feature_access(current_user, "video_analysis_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_analysis_enabled",
        )

    # Fetch job with session
    result = await db.execute(
        select(VideoAnalysisJob)
        .options(selectinload(VideoAnalysisJob.session))
        .where(VideoAnalysisJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    # Check ownership via session
    session = job.session
    if current_user.role == RoleEnum.coach_pro_plus and session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job",
        )

    # Validate goals exist
    if not job.coach_goals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No goals set for this job. Use /set-goals endpoint first.",
        )

    # Fetch target zones needed for compliance calculation
    zone_ids = [zg["zone_id"] for zg in job.coach_goals.get("zones", [])]
    zones_lookup = {}

    if zone_ids:
        zones_result = await db.execute(select(TargetZone).where(TargetZone.id.in_(zone_ids)))
        zones = zones_result.scalars().all()
        zones_lookup = {
            z.id: {
                "id": z.id,
                "name": z.name,
                "shape": z.shape,
                "definition_json": z.definition_json,
            }
            for z in zones
        }

    # Calculate compliance
    try:
        outcomes = calculate_compliance(job, zones_lookup)
    except Exception as e:
        logger.error(f"Failed to calculate compliance for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate compliance: {e!s}",
        )

    # Save outcomes
    job.outcomes = outcomes
    job.goal_compliance_pct = outcomes["overall_compliance_pct"]
    await db.commit()
    await db.refresh(job)

    logger.info(
        f"Calculated compliance for job {job_id}: {outcomes['overall_compliance_pct']}% compliant"
    )

    return OutcomesResponse(**outcomes)


@router.get("/analysis-jobs/{job_id}/outcomes", response_model=OutcomesResponse)
async def get_job_outcomes(
    job_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> OutcomesResponse:
    """Get calculated outcomes for a job with goals."""
    # Verify feature access
    if not await _check_feature_access(current_user, "video_analysis_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_analysis_enabled",
        )

    # Fetch job with session
    result = await db.execute(
        select(VideoAnalysisJob)
        .options(selectinload(VideoAnalysisJob.session))
        .where(VideoAnalysisJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    # Check ownership via session
    session = job.session
    if current_user.role == RoleEnum.coach_pro_plus and session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job",
        )

    # Return outcomes if available
    if not job.outcomes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No outcomes calculated yet. Use /calculate-compliance endpoint first.",
        )

    return OutcomesResponse(**job.outcomes)


@router.post("/sessions/{session_id}/compare-jobs", response_model=CompareJobsResponse)
async def compare_session_jobs(
    session_id: str,
    request: CompareJobsRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> CompareJobsResponse:
    """Compare multiple analysis jobs within a session.

    Shows timeline of metric scores, improvements/regressions between jobs,
    and persistent issues across multiple sessions.
    """
    from backend.services.session_comparison import compare_jobs

    # Verify feature access
    if not await _check_feature_access(current_user, "video_analysis_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_analysis_enabled",
        )

    # Fetch session
    result = await db.execute(select(VideoSession).where(VideoSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check ownership
    if current_user.role == RoleEnum.coach_pro_plus and session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this session",
        )

    # Fetch jobs
    jobs_result = await db.execute(
        select(VideoAnalysisJob)
        .where(
            VideoAnalysisJob.id.in_(request.job_ids),
            VideoAnalysisJob.session_id == session_id,
        )
        .order_by(VideoAnalysisJob.completed_at.asc(), VideoAnalysisJob.created_at.asc())
    )
    jobs = jobs_result.scalars().all()

    if not jobs:
        raise HTTPException(status_code=404, detail="No matching jobs found for this session")

    if len(jobs) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 jobs required for comparison",
        )

    # Perform comparison
    try:
        comparison = compare_jobs(list(jobs))
    except Exception as e:
        logger.error(f"Failed to compare jobs for session {session_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compare jobs: {e!s}",
        )

    logger.info(f"Compared {len(jobs)} jobs for session {session_id}")

    return CompareJobsResponse(**comparison)


@router.get("/videos/{session_id}/stream-url", response_model=VideoStreamUrlRead)
async def get_video_stream_url(
    session_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoStreamUrlRead:
    """
    Get a short-lived presigned GET URL for the uploaded video of a session.

    This is computed per-request and is not persisted.
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_upload_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_upload_enabled",
        )

    # Fetch session from database
    result = await db.execute(select(VideoSession).where(VideoSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    # Verify ownership
    if current_user.role == RoleEnum.coach_pro_plus:
        if session.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )
    else:
        if session.owner_type == OwnerTypeEnum.org and session.owner_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )

    if not session.s3_bucket or not session.s3_key:
        raise HTTPException(status_code=404, detail="Video not available for this session")

    expires_in = settings.S3_STREAM_URL_EXPIRES_SECONDS
    video_url = s3_service.generate_presigned_get_url(
        bucket=session.s3_bucket,
        key=session.s3_key,
        expires_in=expires_in,
    )
    return VideoStreamUrlRead(
        video_url=video_url,
        expires_in=expires_in,
        bucket=session.s3_bucket,
        key=session.s3_key,
    )


# ============================================================================
# Video Upload Endpoints
# ============================================================================


@router.post("/videos/upload/initiate", response_model=VideoUploadInitiateResponse)
async def initiate_video_upload(
    request: VideoUploadInitiateRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoUploadInitiateResponse:
    """
    Initiate a video upload by creating an analysis job and generating a presigned PUT URL.

    Flow:
    1. Validate session exists and user owns it
    2. Create VideoAnalysisJob with status "queued"
    3. Generate S3 presigned PUT URL
    4. Return URL + job details for client to upload to

    Key: coach_plus/{owner_type}/{owner_id}/{session_id}/{video_id}/original.mp4
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_upload_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_upload_enabled",
        )

    # Verify user is coach_pro_plus, org_pro, or superuser
    if (
        current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro)
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can upload videos",
        )

    # Validate session exists and user owns it
    result = await db.execute(select(VideoSession).where(VideoSession.id == request.session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    # Check ownership
    if current_user.role == RoleEnum.coach_pro_plus:
        if session.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )
    else:
        # Org users see org sessions
        if session.owner_type == OwnerTypeEnum.org and session.owner_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )

    owner_type_value = session.owner_type.value
    owner_id_value = session.owner_id

    if not settings.S3_COACH_VIDEOS_BUCKET or not settings.S3_COACH_VIDEOS_BUCKET.strip():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="S3 video storage is not configured (S3_COACH_VIDEOS_BUCKET is empty).",
        )

    # Create analysis job with awaiting_upload status (not claimable yet)
    job_id = str(uuid4())
    job = VideoAnalysisJob(
        id=job_id,
        session_id=request.session_id,
        sample_fps=request.sample_fps,
        include_frames=request.include_frames,
        status=VideoAnalysisJobStatus.awaiting_upload,  # NOT queued yet
        stage="AWAITING_UPLOAD",
        progress_pct=0,
        deep_enabled=bool(settings.COACH_PLUS_DEEP_ANALYSIS_ENABLED),
        analysis_mode=request.analysis_mode,  # NEW: Store analysis mode from request
        # S3 location will be set after key generation
        s3_bucket=None,
        s3_key=None,
    )

    db.add(job)
    await db.flush()

    try:
        # Generate S3 presigned URL (lazy import)
        import logging

        import boto3
        from backend.services.s3_service import s3_service

        try:
            sts = boto3.client("sts")
            identity = sts.get_caller_identity()
            logging.warning(f"AWS IDENTITY IN CONTAINER: {identity}")
        except Exception as e:
            logging.warning(f"AWS IDENTITY IN CONTAINER: <unavailable: {e!s}>")

        # Key format: {prefix}/{owner_type}/{owner_id}/{session_id}/{video_id}/original.mp4
        video_id = str(uuid4())
        prefix = (settings.COACH_PLUS_S3_PREFIX or "coach_plus").strip().strip("/")
        s3_key = (
            f"{prefix}/{owner_type_value}/{owner_id_value}/"
            f"{request.session_id}/{video_id}/original.mp4"
        )

        # Persist upload location onto the session so the worker can retrieve it later.
        # The worker currently expects `job.session.s3_key`.
        session.s3_bucket = settings.S3_COACH_VIDEOS_BUCKET
        session.s3_key = s3_key

        # CRITICAL: Snapshot S3 location in job to prevent 404s from session mutations
        job.s3_bucket = settings.S3_COACH_VIDEOS_BUCKET
        job.s3_key = s3_key

        # Set session status to uploading (awaiting client upload)
        session.status = VideoSessionStatus.pending  # or could use a custom "uploading" status

        presigned_url = s3_service.generate_presigned_put_url(  # type: ignore[union-attr]
            bucket=settings.S3_COACH_VIDEOS_BUCKET,
            key=s3_key,
            expires_in=settings.S3_UPLOAD_URL_EXPIRES_SECONDS,
        )
    except RuntimeError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {e!s}",
        ) from e

    await db.commit()

    return VideoUploadInitiateResponse(
        job_id=job_id,
        session_id=request.session_id,
        presigned_url=presigned_url,
        expires_in=settings.S3_UPLOAD_URL_EXPIRES_SECONDS,
        s3_bucket=settings.S3_COACH_VIDEOS_BUCKET,
        s3_key=s3_key,
    )


@router.post("/videos/upload/complete", response_model=VideoUploadCompleteResponse)
async def complete_video_upload(
    request: VideoUploadCompleteRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoUploadCompleteResponse:
    """
    Complete a video upload by updating job status and leaving it queued in DB.

    Flow:
    1. Validate job exists and user owns session
    2. Update job status to "uploaded"
    3. Send message to SQS queue for async processing
    4. Return confirmation with SQS message ID

    After this, the video analysis worker will:
    - Receive message from SQS
    - Extract frames from video
    - Compute pose metrics
    - Update job status to "completed"
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_upload_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_upload_enabled",
        )

    # Verify user is coach_pro_plus, org_pro, or superuser
    if (
        current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro)
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can upload videos",
        )

    # Fetch job
    result = await db.execute(
        select(VideoAnalysisJob)
        .options(selectinload(VideoAnalysisJob.session))
        .where(VideoAnalysisJob.id == request.job_id)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    # Check ownership via session
    session = job.session
    if current_user.role == RoleEnum.coach_pro_plus and session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job",
        )

    # Idempotency: If already queued, processing, or completed, return success
    if job.status in (
        VideoAnalysisJobStatus.queued,
        VideoAnalysisJobStatus.quick_running,
        VideoAnalysisJobStatus.quick_done,
        VideoAnalysisJobStatus.deep_running,
        VideoAnalysisJobStatus.done,
        VideoAnalysisJobStatus.completed,
    ):
        logger.info(
            f"Upload complete called on already-processed job: job_id={job.id} "
            f"status={job.status.value} - returning success (idempotent)"
        )
        return VideoUploadCompleteResponse(
            job_id=job.id,
            status=job.status.value,
            sqs_message_id=job.sqs_message_id,
            message=f"Job already {job.status.value} - no action taken",
        )

    # If job is failed, allow retry by proceeding with validation
    if job.status == VideoAnalysisJobStatus.failed:
        logger.info(
            f"Upload complete called on failed job: job_id={job.id} - will retry validation"
        )

    # Only proceed if job is awaiting_upload or failed
    if job.status not in (VideoAnalysisJobStatus.awaiting_upload, VideoAnalysisJobStatus.failed):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete upload for job in status: {job.status.value}",
        )

    # Validate we have stored upload location (worker requires this)
    if not session.s3_key:
        job.status = VideoAnalysisJobStatus.failed
        job.error_message = "Upload location missing (session.s3_key is null). Re-initiate upload."
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload location missing for this session. Please re-initiate upload.",
        )

    # Preflight check: verify S3 object exists before queuing analysis
    bucket = session.s3_bucket
    key = session.s3_key

    logger.info(
        f"Upload complete request: job_id={job.id} session_id={session.id} "
        f"bucket={bucket} key={key} user_id={current_user.id}"
    )

    try:
        s3 = boto3.client("s3", region_name=settings.AWS_REGION)
        s3.head_object(Bucket=bucket, Key=key)
        logger.info(f"S3 preflight check PASSED: job_id={job.id} bucket={bucket} key={key}")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        request_id = e.response.get("ResponseMetadata", {}).get("RequestId", "N/A")

        error_detail = (
            f"Upload not found in S3. bucket={bucket} key={key} "
            f"error_code={error_code} request_id={request_id}"
        )

        if error_code in ("404", "NoSuchKey"):
            logger.warning(f"S3 preflight check FAILED (not found): job_id={job.id} {error_detail}")
        else:
            logger.error(f"S3 preflight check ERROR: job_id={job.id} {error_detail}")

        job.status = VideoAnalysisJobStatus.failed
        job.stage = "FAILED"
        job.error_message = f"Upload verification failed: {error_detail}"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload not found in S3. Please retry upload. Details: {error_detail}",
        ) from None
    except Exception as e:
        error_detail = f"S3 preflight check failed: bucket={bucket} key={key} error={e!s}"
        logger.error(f"S3 preflight check EXCEPTION: job_id={job.id} {error_detail}")
        job.status = VideoAnalysisJobStatus.failed
        job.stage = "FAILED"
        job.error_message = error_detail
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify upload. Error: {e!s}",
        ) from e

    logger.info(f"S3 object verified: job_id={job.id} proceeding to queue analysis")

    # Determine processing mode: GPU (chunked) or CPU (monolithic)
    deep_mode = job.deep_mode or "cpu"

    if deep_mode == "gpu":
        # GPU mode: compute duration and create chunks
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            # Download video to compute duration
            duration = await get_video_duration_from_s3(bucket, key, tmp_path)
            job.video_duration_seconds = duration

            # Create chunk specifications
            chunk_specs = create_chunk_specs(
                duration_seconds=duration,
                chunk_seconds=settings.CHUNK_SECONDS,
            )

            # Create chunk records
            chunks = []
            for spec in chunk_specs:
                chunk = VideoAnalysisChunk(
                    job_id=job.id,
                    chunk_index=spec["index"],
                    start_sec=spec["start_sec"],
                    end_sec=spec["end_sec"],
                    status=VideoAnalysisChunkStatus.queued,
                )
                chunks.append(chunk)

            db.add_all(chunks)

            # Update job with chunk tracking
            job.total_chunks = len(chunks)
            job.completed_chunks = 0
            job.status = VideoAnalysisJobStatus.queued
            job.stage = "DEEP_QUEUED"
            job.progress_pct = 0

            logger.info(
                f"GPU mode: created {len(chunks)} chunks for job_id={job.id} "
                f"duration={duration:.2f}s chunk_size={settings.CHUNK_SECONDS}s"
            )
        except Exception as e:
            logger.error(f"Failed to create chunks: job_id={job.id} error={e!s}")
            job.status = VideoAnalysisJobStatus.failed
            job.stage = "FAILED"
            job.error_message = f"Chunk creation failed: {e!s}"
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to prepare video for processing: {e!s}",
            ) from e
        finally:
            import contextlib
            import os

            with contextlib.suppress(Exception):
                os.unlink(tmp_path)
    else:
        # CPU mode: simple queue transition (existing behavior)
        job.status = VideoAnalysisJobStatus.queued
        job.stage = "QUEUED"
        job.progress_pct = 0

    # Common cleanup
    job.error_message = None
    job.sqs_message_id = None
    session.status = VideoSessionStatus.uploaded

    await db.commit()

    return VideoUploadCompleteResponse(
        job_id=job.id,
        status=job.status.value,
        sqs_message_id=None,
        message="Video uploaded and queued for analysis",
    )


# ============================================================================
# Video Analysis (MVP - Internal Testing)
# ============================================================================


class VideoAnalysisRequest(BaseModel):
    """Request for video analysis."""

    video_path: str = Field(
        ..., description="Path to video file on disk (assumed to already exist)"
    )
    sample_fps: int = Field(default=10, ge=1, le=30, description="Frames to sample per second")
    player_id: str | None = Field(default=None, description="Optional player ID for context")
    session_id: str | None = Field(default=None, description="Optional session ID for tracking")
    include_frames: bool = Field(
        default=False, description="Include per-frame pose data in response"
    )


class PoseSummary(BaseModel):
    """Summary of pose extraction results."""

    total_frames: int
    sampled_frames: int
    frames_with_pose: int
    detection_rate_percent: float
    model: str
    video_fps: float


class VideoAnalysisResponse(BaseModel):
    """Full pipeline response: pose → metrics → findings → report."""

    pose_summary: PoseSummary
    metrics: dict
    findings: dict
    report: dict
    frames: list[dict[str, Any]] | None = None


@router.post(
    "/videos/analyze", response_model=VideoAnalysisResponse, response_model_exclude_none=True
)
async def analyze_video(
    request: VideoAnalysisRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoAnalysisResponse:
    """
    Analyze a video and generate coaching report.

    Pipeline: Pose Extraction → Metrics → Findings → Report

    **MVP Testing Only** - Assumes video exists on disk. No large uploads accepted.

    Feature-gated: Requires coach_pro_plus or org_pro role.

    **Request:**
    - `video_path`: Path to video file (local disk or mounted storage)
    - `sample_fps`: Sampling rate (1-30 frames per second)
    - `player_id`: Optional player identifier
    - `session_id`: Optional session identifier

    **Response:**
    - `pose_summary`: Extraction stats
    - `metrics`: 5 computed biomechanical metrics
    - `findings`: Rule-based coaching findings
    - `report`: Narrative coaching report with drills and plan

    Errors:
    - 403: Insufficient role/feature access
    - 400: Invalid video path or video not found
    - 422: Invalid request parameters
    """
    # Check role access (coach_pro_plus, org_pro, or superuser)
    if (
        current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro)
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can analyze videos",
        )

    # Check feature access
    if not await _check_feature_access(current_user, "video_analysis_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_analysis_enabled",
        )

    # Validate video path exists
    from pathlib import Path

    video_file = Path(request.video_path)
    if not video_file.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video file not found: {request.video_path}",
        )

    if not video_file.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not a file: {request.video_path}",
        )

    # Check file extension
    valid_extensions = {".mp4", ".avi", ".mov", ".mkv", ".flv"}
    if video_file.suffix.lower() not in valid_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported video format: {video_file.suffix}. "
            f"Supported: {', '.join(valid_extensions)}",
        )

    try:
        # Step 1: Extract pose keypoints (lazy import)
        from backend.services.pose_service import extract_pose_keypoints_from_video

        pose_data = extract_pose_keypoints_from_video(
            video_path=request.video_path,
            sample_fps=request.sample_fps,
            max_width=640,
        )

        # Normalize pose_data schema - supports multiple response formats
        def _normalize_pose_data(data: dict) -> dict:
            """Extract fields from pose_data supporting multiple schema versions."""
            # total_frames: try direct alias, then pose_summary, then metrics
            total_frames = (
                data.get("total_frames")
                or data.get("pose_summary", {}).get("frame_count")
                or data.get("metrics", {}).get("frame_count")
            )
            if total_frames is None:
                raise ValueError("Could not find total_frames in pose data")

            # sampled_frames: try direct alias, then pose_summary, then metrics
            sampled_frames = (
                data.get("sampled_frames")
                or data.get("pose_summary", {}).get("sampled_frame_count")
                or data.get("metrics", {}).get("sampled_frame_count")
            )
            if sampled_frames is None:
                raise ValueError("Could not find sampled_frames in pose data")

            # frames_with_pose: try direct alias (detected_frames), then metrics
            frames_with_pose = data.get("frames_with_pose") or data.get("detected_frames")
            if frames_with_pose is None:
                raise ValueError("Could not find frames_with_pose/detected_frames in pose data")

            # detection_rate_percent: try direct, then pose_summary, then metrics, else compute
            detection_rate_percent = (
                data.get("detection_rate_percent")
                or data.get("pose_summary", {}).get("detection_rate")
                or data.get("metrics", {}).get("detection_rate")
            )
            if detection_rate_percent is None:
                # Compute if not available
                detection_rate_percent = (
                    (frames_with_pose / sampled_frames * 100) if sampled_frames > 0 else 0
                )

            # video_fps: try direct alias, then top-level fps
            video_fps = data.get("video_fps") or data.get("fps") or 30.0

            # model: default to MediaPipe Pose Landmarker if not provided
            model = data.get("model") or "MediaPipe Pose Landmarker Full"

            return {
                "total_frames": int(total_frames),
                "sampled_frames": int(sampled_frames),
                "frames_with_pose": int(frames_with_pose),
                "detection_rate_percent": float(detection_rate_percent),
                "video_fps": float(video_fps),
                "model": str(model),
            }

        normalized = _normalize_pose_data(pose_data)

        pose_summary = PoseSummary(
            total_frames=normalized["total_frames"],
            sampled_frames=normalized["sampled_frames"],
            frames_with_pose=normalized["frames_with_pose"],
            detection_rate_percent=normalized["detection_rate_percent"],
            model=normalized["model"],
            video_fps=normalized["video_fps"],
        )

        # Create adapter payload for metrics layer with normalized summary
        pose_payload_for_metrics = {
            **pose_data,
            # Add normalized values at top level for downstream functions
            "total_frames": normalized["total_frames"],
            "sampled_frames": normalized["sampled_frames"],
            "frames_with_pose": normalized["frames_with_pose"],
            "detection_rate_percent": normalized["detection_rate_percent"],
            "video_fps": normalized["video_fps"],
            "model": normalized["model"],
            # Also provide under summary key for functions expecting it there
            "summary": {
                "total_frames": normalized["total_frames"],
                "sampled_frames": normalized["sampled_frames"],
                "frames_with_pose": normalized["frames_with_pose"],
                "detection_rate_percent": normalized["detection_rate_percent"],
                "video_fps": normalized["video_fps"],
                "model": normalized["model"],
            },
        }

        # Step 2: Compute metrics from pose
        metrics_result = compute_pose_metrics(pose_payload_for_metrics)

        # Evidence markers (extend-only; safe fallback on errors)
        try:
            evidence = build_pose_metric_evidence(pose_payload_for_metrics, metrics_result)
            if isinstance(metrics_result, dict):
                metrics_result.setdefault("evidence", evidence)
        except Exception:
            logger.exception("Failed to compute evidence markers")

        # Ensure metrics_result has normalized summary keys for downstream functions
        if isinstance(metrics_result, dict):
            metrics_result.setdefault("total_frames", normalized["total_frames"])
            metrics_result.setdefault("sampled_frames", normalized["sampled_frames"])
            metrics_result.setdefault("frames_with_pose", normalized["frames_with_pose"])
            metrics_result.setdefault(
                "detection_rate_percent", normalized["detection_rate_percent"]
            )
            metrics_result.setdefault("video_fps", normalized["video_fps"])
            metrics_result.setdefault("model", normalized["model"])

        # Step 3: Generate findings
        findings_result = generate_findings(metrics_result)

        # Step 4: Generate coaching report
        player_context = None
        if request.player_id:
            player_context = {
                "player_id": request.player_id,
                "session_id": request.session_id or "unknown",
            }

        report_result = generate_report_text(findings_result, player_context)

        frames_out: list[dict[str, Any]] | None = None
        if request.include_frames:
            # Support multiple schema versions coming from pose_service
            frames_out = (
                pose_data.get("frames")
                or pose_data.get("frames_data")
                or pose_data.get("pose_frames")
            )
            # Ensure it's a list (avoid returning dict/None)
            if not isinstance(frames_out, list):
                frames_out = None

        return VideoAnalysisResponse(
            pose_summary=pose_summary,
            metrics=metrics_result,
            findings=findings_result,
            report=report_result,
            frames=frames_out,
        )

    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File error: {e!s}",
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video error: {e!s}",
        ) from e
    except KeyError as e:
        # Detailed error for debugging KeyError issues
        import logging as log_module

        local_logger = log_module.getLogger(__name__)
        local_logger.exception(f"KeyError in video analysis pipeline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: Missing required field {e!s}. Check logs for details.",
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {e!s}",
        ) from e


# @router.post("/sessions/{session_id}/upload")
# - Receive video file chunks
# - Store on S3
# - Trigger video processing (transcoding, etc.)
#
# @router.get("/sessions/{session_id}/stream")
# - Stream video to client
# - Return presigned S3 URL
#
# @router.post("/sessions/{session_id}/process-ai")
# - Trigger AI analysis on uploaded video
# - Queue for processing
#
# @router.get("/sessions/{session_id}/ai-report")
# - Return AI-generated insights from video analysis


# ============================================================================
# Ball Tracking Endpoints
# ============================================================================


class BallTrackingRequest(BaseModel):
    """Request for ball tracking analysis."""

    video_path: str = Field(..., description="Path to video file")
    ball_color: str = Field(default="red", description="Ball color: red, white, or pink")
    sample_fps: float = Field(default=30.0, ge=1, le=60, description="Frames per second to sample")
    min_radius: int = Field(default=5, ge=1, le=50, description="Minimum ball radius in pixels")
    max_radius: int = Field(default=50, ge=5, le=200, description="Maximum ball radius in pixels")


class BallPositionResponse(BaseModel):
    """Ball position in a frame."""

    frame_num: int
    timestamp: float
    x: float
    y: float
    confidence: float
    radius: float
    velocity_x: float = 0.0
    velocity_y: float = 0.0


class BallTrajectoryResponse(BaseModel):
    """Ball trajectory analysis response."""

    positions: list[BallPositionResponse]
    total_frames: int
    detected_frames: int
    detection_rate: float
    release_point: BallPositionResponse | None = None
    bounce_point: BallPositionResponse | None = None
    impact_point: BallPositionResponse | None = None
    avg_velocity: float
    max_velocity: float
    trajectory_length: float


class BallMetricsResponse(BaseModel):
    """Ball tracking metrics for coaching."""

    release_height: float | None = None
    release_position_x: float | None = None
    swing_deviation: float = 0.0
    flight_time: float = 0.0
    ball_speed_estimate: float = 0.0
    bounce_distance: float | None = None
    bounce_angle: float | None = None
    trajectory_curve: str = "straight"
    spin_detected: bool = False
    release_consistency: float = 100.0


class BallTrackingResponse(BaseModel):
    """Complete ball tracking analysis response."""

    trajectory: BallTrajectoryResponse
    metrics: BallMetricsResponse


@router.post(
    "/videos/track-ball",
    response_model=BallTrackingResponse,
    response_model_exclude_none=True,
)
async def track_ball_in_video(
    request: BallTrackingRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> BallTrackingResponse:
    """
    Track cricket ball trajectory in video.

    Uses computer vision (color-based detection) to track ball position
    across frames and compute trajectory metrics.

    Feature-gated: Requires coach_pro_plus or org_pro role.

    **Request:**
    - `video_path`: Path to video file
    - `ball_color`: red/white/pink (default: red)
    - `sample_fps`: Sampling rate (1-60 fps, default: 30)
    - `min_radius`/`max_radius`: Ball size constraints in pixels

    **Response:**
    - `trajectory`: Frame-by-frame ball positions with velocities
    - `metrics`: Coaching metrics (release point, swing, bounce, speed)

    **Use Cases:**
    - Bowling analysis: release point consistency, swing detection
    - Batting analysis: impact point tracking, shot trajectories
    - Combined with pose analysis for timing feedback

    Errors:
    - 403: Insufficient role/feature access
    - 400: Invalid video path or unsupported ball color
    """
    # Check role access
    if (
        current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro)
        and not current_user.is_superuser
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can track ball in videos",
        )

    # Check feature access
    if not await _check_feature_access(current_user, "video_analysis_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_analysis_enabled",
        )

    # Validate video path
    from pathlib import Path

    video_file = Path(request.video_path)
    if not video_file.exists():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video file not found: {request.video_path}",
        )

    try:
        # Import ball tracking service
        from backend.services.ball_tracking_service import (
            BallTracker,
            analyze_ball_trajectory,
        )

        # Track ball
        tracker = BallTracker(
            ball_color=request.ball_color,
            min_radius=request.min_radius,
            max_radius=request.max_radius,
        )

        trajectory = tracker.track_ball_in_video(
            video_path=request.video_path,
            sample_fps=request.sample_fps,
        )

        # Analyze trajectory
        metrics = analyze_ball_trajectory(trajectory)

        # Convert to response models
        def _pos_to_response(pos):
            if pos is None:
                return None
            return BallPositionResponse(
                frame_num=pos.frame_num,
                timestamp=pos.timestamp,
                x=pos.x,
                y=pos.y,
                confidence=pos.confidence,
                radius=pos.radius,
                velocity_x=pos.velocity_x,
                velocity_y=pos.velocity_y,
            )

        trajectory_response = BallTrajectoryResponse(
            positions=[_pos_to_response(p) for p in trajectory.positions],
            total_frames=trajectory.total_frames,
            detected_frames=trajectory.detected_frames,
            detection_rate=trajectory.detection_rate,
            release_point=_pos_to_response(trajectory.release_point),
            bounce_point=_pos_to_response(trajectory.bounce_point),
            impact_point=_pos_to_response(trajectory.impact_point),
            avg_velocity=trajectory.avg_velocity,
            max_velocity=trajectory.max_velocity,
            trajectory_length=trajectory.trajectory_length,
        )

        metrics_response = BallMetricsResponse(
            release_height=metrics.release_height,
            release_position_x=metrics.release_position_x,
            swing_deviation=metrics.swing_deviation,
            flight_time=metrics.flight_time,
            ball_speed_estimate=metrics.ball_speed_estimate,
            bounce_distance=metrics.bounce_distance,
            bounce_angle=metrics.bounce_angle,
            trajectory_curve=metrics.trajectory_curve,
            spin_detected=metrics.spin_detected,
            release_consistency=metrics.release_consistency,
        )

        return BallTrackingResponse(
            trajectory=trajectory_response,
            metrics=metrics_response,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Ball tracking failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ball tracking failed: {e!s}",
        )


# ============================================================================
# Pitch Calibration Endpoints
# ============================================================================


class PitchCornerPoint(BaseModel):
    """Single corner point for pitch calibration."""

    x: float = Field(..., description="X coordinate in pixels")
    y: float = Field(..., description="Y coordinate in pixels")


class PitchCalibrationRequest(BaseModel):
    """Request schema for pitch calibration."""

    corners: list[PitchCornerPoint] = Field(
        ...,
        min_length=4,
        max_length=4,
        description="4 corner points: [top_left, top_right, bottom_left, bottom_right]",
    )


class PitchCalibrationResponse(BaseModel):
    """Response schema for pitch calibration."""

    session_id: str
    corners: list[PitchCornerPoint]
    message: str


class CalibrationFrameResponse(BaseModel):
    """Response schema for calibration frame."""

    session_id: str
    frame_url: str | None = None
    message: str


@router.get("/sessions/{session_id}/calibration-frame", response_model=CalibrationFrameResponse)
async def get_calibration_frame(
    session_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> CalibrationFrameResponse:
    """
    Get a calibration frame from the video for pitch corner selection.

    Returns a presigned S3 GET URL for a JPEG frame extracted from ~1 second into the video.
    """
    # Verify access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # Fetch session
    result = await db.execute(select(VideoSession).where(VideoSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    # Verify ownership
    if session.owner_id != current_user.id and not current_user.is_superuser:
        if session.owner_type != OwnerTypeEnum.org or session.owner_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )

    # Check if video is uploaded
    if not session.s3_key or not session.s3_bucket:
        raise HTTPException(
            status_code=400, detail="Video not uploaded yet. Upload video before calibration."
        )

    # Generate frame key (frames stored alongside video)
    # Format: coach_videos/{owner_id}/sessions/{session_id}/calibration_frame.jpg
    frame_key = session.s3_key.replace("/video.mp4", "/calibration_frame.jpg")

    # Check if frame already exists, otherwise generate it
    # For now, assume frame extraction happens in worker (TODO: implement)
    # Return presigned URL for frame
    try:
        frame_url = s3_service.generate_presigned_get_url(
            bucket=session.s3_bucket,
            key=frame_key,
            expiration=3600,  # 1 hour
        )
        return CalibrationFrameResponse(
            session_id=session_id, frame_url=frame_url, message="Calibration frame available"
        )
    except Exception as e:
        logger.warning(f"Calibration frame not found: {e}")
        return CalibrationFrameResponse(
            session_id=session_id,
            frame_url=None,
            message="Calibration frame not yet generated. Please process video first.",
        )


@router.post("/sessions/{session_id}/pitch-calibration", response_model=PitchCalibrationResponse)
async def save_pitch_calibration(
    session_id: str,
    request: PitchCalibrationRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> PitchCalibrationResponse:
    """
    Save pitch corner calibration for homography transform.

    Corners should be provided in order: [top_left, top_right, bottom_left, bottom_right]
    where top = bowler's end, bottom = batsman's end.
    """
    # Verify access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # Fetch session
    result = await db.execute(select(VideoSession).where(VideoSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    # Verify ownership
    if session.owner_id != current_user.id and not current_user.is_superuser:
        if session.owner_type != OwnerTypeEnum.org or session.owner_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )

    # Validate corners
    if len(request.corners) != 4:
        raise HTTPException(
            status_code=400, detail=f"Expected exactly 4 corners, got {len(request.corners)}"
        )

    # Save corners to session
    corners_data = [{"x": c.x, "y": c.y} for c in request.corners]
    session.pitch_corners = {"corners": corners_data}
    await db.commit()

    logger.info(f"Pitch calibration saved for session {session_id}")

    return PitchCalibrationResponse(
        session_id=session_id,
        corners=request.corners,
        message="Pitch calibration saved successfully",
    )


class PitchMapPoint(BaseModel):
    """Single point on the pitch map."""

    x_coordinate: float = Field(..., description="Normalized X (0-100): 0=leg, 100=off")
    y_coordinate: float = Field(..., description="Normalized Y (0-100): 0=bowler, 100=batsman")
    value: float = Field(default=1.0, description="Intensity value (used for heatmap)")
    timestamp: float | None = Field(None, description="Timestamp in video (seconds)")
    confidence: float | None = Field(None, description="Detection confidence (0-1)")
    length: str | None = Field(None, description="Length classification (yorker/full/good/short)")
    line: str | None = Field(None, description="Line classification (leg/middle/off)")


class PitchMapResponse(BaseModel):
    """Response schema for pitch map data."""

    session_id: str
    total_points: int
    points: list[PitchMapPoint]
    calibrated: bool
    message: str


@router.get("/sessions/{session_id}/pitch-map", response_model=PitchMapResponse)
async def get_pitch_map(
    session_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> PitchMapResponse:
    """
    Get pitch map data for visualization.

    Returns normalized bounce point coordinates from ball tracking analysis.
    """
    # Verify access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # Fetch session
    result = await db.execute(select(VideoSession).where(VideoSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    # Verify ownership
    if session.owner_id != current_user.id and not current_user.is_superuser:
        if session.owner_type != OwnerTypeEnum.org or session.owner_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )

    # Get latest analysis job
    job_result = await db.execute(
        select(VideoAnalysisJob)
        .where(VideoAnalysisJob.session_id == session_id)
        .order_by(VideoAnalysisJob.created_at.desc())
    )
    job = job_result.scalar_one_or_none()

    if not job:
        return PitchMapResponse(
            session_id=session_id,
            total_points=0,
            points=[],
            calibrated=False,
            message="No analysis job found for this session",
        )

    # Check if analysis is complete
    if job.status not in (VideoAnalysisJobStatus.done, VideoAnalysisJobStatus.completed):
        return PitchMapResponse(
            session_id=session_id,
            total_points=0,
            points=[],
            calibrated=bool(session.pitch_corners),
            message=f"Analysis not complete. Current status: {job.status}",
        )

    # Extract pitch map data from deep_results
    deep_results = job.deep_results or {}
    pitch_map_data = deep_results.get("pitch_map", [])

    # Check if calibration was used
    calibrated = bool(session.pitch_corners)

    if not pitch_map_data:
        return PitchMapResponse(
            session_id=session_id,
            total_points=0,
            points=[],
            calibrated=calibrated,
            message="No pitch map data available. Ensure video contains bowling deliveries.",
        )

    # Convert to response format
    points = [
        PitchMapPoint(
            x_coordinate=p.get("x", 0),
            y_coordinate=p.get("y", 0),
            value=p.get("value", 1.0),
            timestamp=p.get("timestamp"),
            confidence=p.get("confidence"),
            length=p.get("length"),
            line=p.get("line"),
        )
        for p in pitch_map_data
    ]

    return PitchMapResponse(
        session_id=session_id,
        total_points=len(points),
        points=points,
        calibrated=calibrated,
        message="Pitch map data retrieved successfully",
    )


# ============================================================================
# Target Zone Endpoints
# ============================================================================


class TargetZoneCreate(BaseModel):
    """Request schema for creating a target zone."""

    session_id: str | None = Field(None, description="Optional session ID to link zone")
    name: str = Field(..., min_length=1, max_length=100, description="Zone name")
    shape: str = Field(default="rect", description="Shape type: rect, circle, polygon")
    definition_json: dict[str, Any] = Field(
        ..., description="Shape definition: {x, y, width, height} for rect"
    )


class TargetZoneRead(BaseModel):
    """Response schema for target zone."""

    id: str
    owner_id: str
    session_id: str | None
    name: str
    shape: str
    definition_json: dict[str, Any]
    created_at: datetime

    class Config:
        from_attributes = True


class ZoneReportRequest(BaseModel):
    """Request schema for zone accuracy report."""

    zone_id: str
    tolerance: float = Field(default=0.0, ge=0.0, description="Tolerance margin (0-100 scale)")


class ZoneReportResponse(BaseModel):
    """Response schema for zone accuracy report."""

    zone_id: str
    zone_name: str
    total_deliveries: int
    hits: int
    misses: int
    hit_rate: float
    miss_breakdown: dict[str, int]
    nearest_miss_distance: float | None
    avg_miss_distance: float | None


@router.post("/target-zones", response_model=TargetZoneRead)
async def create_target_zone(
    zone_data: TargetZoneCreate,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> TargetZoneRead:
    """
    Create a new target zone for pitch mapping analysis.
    """
    # Verify access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # If session_id provided, verify it exists and user has access
    if zone_data.session_id:
        session_result = await db.execute(
            select(VideoSession).where(VideoSession.id == zone_data.session_id)
        )
        session = session_result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.owner_id != current_user.id and not current_user.is_superuser:
            if session.owner_type != OwnerTypeEnum.org or session.owner_id != current_user.org_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have access to this session",
                )

    # Create zone
    zone = TargetZone(
        owner_id=current_user.id,
        session_id=zone_data.session_id,
        name=zone_data.name,
        shape=zone_data.shape,
        definition_json=zone_data.definition_json,
    )

    db.add(zone)
    await db.commit()
    await db.refresh(zone)

    logger.info(f"Target zone created: {zone.id} by user {current_user.id}")

    return TargetZoneRead.model_validate(zone)


@router.get("/target-zones", response_model=list[TargetZoneRead])
async def list_target_zones(
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    session_id: str | None = Query(None, description="Filter by session ID"),
    db: AsyncSession = Depends(get_db),
) -> list[TargetZoneRead]:
    """
    List target zones for the current user.
    """
    # Verify access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # Build query
    query = select(TargetZone).where(TargetZone.owner_id == current_user.id)

    if session_id:
        query = query.where(TargetZone.session_id == session_id)

    query = query.order_by(TargetZone.created_at.desc())

    result = await db.execute(query)
    zones = result.scalars().all()

    return [TargetZoneRead.model_validate(z) for z in zones]


@router.post("/sessions/{session_id}/zone-report", response_model=ZoneReportResponse)
async def get_zone_accuracy_report(
    session_id: str,
    request: ZoneReportRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> ZoneReportResponse:
    """
    Calculate accuracy report for a target zone.

    Analyzes how many deliveries landed within the zone vs. outside.
    """
    # Verify access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # Fetch zone
    zone_result = await db.execute(select(TargetZone).where(TargetZone.id == request.zone_id))
    zone = zone_result.scalar_one_or_none()

    if not zone:
        raise HTTPException(status_code=404, detail="Target zone not found")

    # Verify ownership
    if zone.owner_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this zone",
        )

    # Fetch session
    session_result = await db.execute(select(VideoSession).where(VideoSession.id == session_id))
    session = session_result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get pitch map data
    job_result = await db.execute(
        select(VideoAnalysisJob)
        .where(VideoAnalysisJob.session_id == session_id)
        .order_by(VideoAnalysisJob.created_at.desc())
    )
    job = job_result.scalar_one_or_none()

    if not job or not job.deep_results:
        raise HTTPException(status_code=400, detail="No analysis data available for this session")

    pitch_map_data = job.deep_results.get("pitch_map", [])

    if not pitch_map_data:
        return ZoneReportResponse(
            zone_id=zone.id,
            zone_name=zone.name,
            total_deliveries=0,
            hits=0,
            misses=0,
            hit_rate=0.0,
            miss_breakdown={},
            nearest_miss_distance=None,
            avg_miss_distance=None,
        )

    # Analyze hits vs misses
    hits = 0
    misses = 0
    miss_distances = []
    miss_breakdown = {
        "above": 0,
        "below": 0,
        "left": 0,
        "right": 0,
    }

    # Extract zone definition (assuming rectangular zone)
    zone_def = zone.definition_json
    x_min = zone_def.get("x", 0)
    y_min = zone_def.get("y", 0)
    width = zone_def.get("width", 10)
    height = zone_def.get("height", 10)
    x_max = x_min + width
    y_max = y_min + height

    # Apply tolerance
    x_min -= request.tolerance
    y_min -= request.tolerance
    x_max += request.tolerance
    y_max += request.tolerance

    for point in pitch_map_data:
        px = point.get("x", 0)
        py = point.get("y", 0)

        # Check if point is inside zone (with tolerance)
        if x_min <= px <= x_max and y_min <= py <= y_max:
            hits += 1
        else:
            misses += 1

            # Calculate miss distance (simplified: distance to zone center)
            zone_center_x = (x_min + x_max) / 2
            zone_center_y = (y_min + y_max) / 2
            distance = ((px - zone_center_x) ** 2 + (py - zone_center_y) ** 2) ** 0.5
            miss_distances.append(distance)

            # Classify miss direction
            if py < y_min:
                miss_breakdown["above"] += 1
            elif py > y_max:
                miss_breakdown["below"] += 1

            if px < x_min:
                miss_breakdown["left"] += 1
            elif px > x_max:
                miss_breakdown["right"] += 1

    total = hits + misses
    hit_rate = (hits / total * 100) if total > 0 else 0.0

    nearest_miss = min(miss_distances) if miss_distances else None
    avg_miss = sum(miss_distances) / len(miss_distances) if miss_distances else None

    return ZoneReportResponse(
        zone_id=zone.id,
        zone_name=zone.name,
        total_deliveries=total,
        hits=hits,
        misses=misses,
        hit_rate=hit_rate,
        miss_breakdown=miss_breakdown,
        nearest_miss_distance=nearest_miss,
        avg_miss_distance=avg_miss,
    )
