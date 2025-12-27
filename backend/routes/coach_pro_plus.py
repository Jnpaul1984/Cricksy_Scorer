"""
Coach Pro Plus Routes - Video Sessions Scaffolding

Provides placeholder endpoints for video session management.
Real video upload/streaming will be implemented in future phases.
Feature-gated by role (coach_pro_plus, org_pro).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Annotated
from uuid import uuid4

from backend import security
from backend.services.coach_findings import generate_findings
from backend.services.coach_report_service import generate_report_text
from backend.services.pose_metrics import compute_pose_metrics
from backend.sql_app.database import get_db
from backend.sql_app.models import (
    RoleEnum,
    User,
    VideoSession,
    VideoAnalysisJob,
    VideoSessionStatus,
    VideoAnalysisJobStatus,
    OwnerTypeEnum,
)
from backend.config import settings
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/api/coaches/plus", tags=["coach_pro_plus"])


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


class VideoSessionRead(BaseModel):
    """Response schema for a video session"""

    id: str
    owner_type: str  # "coach" or "org"
    owner_id: str
    title: str
    player_ids: list[str]
    status: str  # "pending", "uploaded", "processing", "ready", "failed"
    notes: str | None = None
    s3_bucket: str | None = None
    s3_key: str | None = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoAnalysisJobRead(BaseModel):
    """Response schema for a video analysis job"""

    id: str
    session_id: str
    sample_fps: int
    include_frames: bool
    status: str  # "queued", "processing", "completed", "failed"
    error_message: str | None = None
    sqs_message_id: str | None = None
    results: dict | None = None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    updated_at: datetime

    class Config:
        from_attributes = True


class VideoUploadInitiateRequest(BaseModel):
    """Request schema for initiating a video upload"""

    session_id: str
    sample_fps: int = Field(default=10, ge=1, le=30)
    include_frames: bool = Field(default=False)


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
) -> list[VideoSessionRead]:
    """
    List video sessions for the current user (Coach Pro Plus feature).

    Feature-gated: Requires coach_pro_plus role.
    Returns sessions owned by the user or their organization.
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
    if current_user.role == RoleEnum.org_pro:
        # Org users see all sessions for their org
        query = select(VideoSession).where(
            (VideoSession.owner_type == OwnerTypeEnum.org)
            & (VideoSession.owner_id == current_user.org_id)
        )
    else:
        # Coach users see only their own sessions
        query = select(VideoSession).where(VideoSession.owner_id == current_user.id)

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
) -> VideoAnalysisJobRead:
    """
    Create a video analysis job for a session.

    The job is queued and sent to SQS for async processing.
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

    return [VideoAnalysisJobRead.model_validate(job) for job in jobs]


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

    # Fetch job
    result = await db.execute(select(VideoAnalysisJob).where(VideoAnalysisJob.id == job_id))
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

    return VideoAnalysisJobRead.model_validate(job)


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

    # Create analysis job
    job_id = str(uuid4())
    job = VideoAnalysisJob(
        id=job_id,
        session_id=request.session_id,
        sample_fps=request.sample_fps,
        include_frames=request.include_frames,
        status=VideoAnalysisJobStatus.queued,
    )

    db.add(job)
    await db.flush()

    try:
        # Generate S3 presigned URL (lazy import)
        from backend.services.s3_service import s3_service

        # Key format: coach_plus/{owner_type}/{owner_id}/{session_id}/{video_id}/original.mp4
        video_id = str(uuid4())
        s3_key = f"coach_plus/{owner_type_value}/{owner_id_value}/{request.session_id}/{video_id}/original.mp4"

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
    Complete a video upload by updating job status and enqueuing to SQS.

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

    # Update job status to "uploaded"
    job.status = VideoAnalysisJobStatus.processing

    job_id_value = job.id
    status_value = job.status.value

    # Prepare SQS message
    message_body = {
        "job_id": job.id,
        "session_id": job.session_id,
        "sample_fps": job.sample_fps,
        "include_frames": job.include_frames,
    }

    # Send to SQS queue (lazy import)
    try:
        from backend.services.sqs_service import sqs_service

        message_id = sqs_service.send_message(  # type: ignore[union-attr]
            queue_url=settings.SQS_VIDEO_ANALYSIS_QUEUE_URL,
            message_body=message_body,
        )
        job.sqs_message_id = message_id
    except RuntimeError as e:
        job.status = VideoAnalysisJobStatus.failed
        job.error_message = f"Failed to enqueue job: {e!s}"
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue video for processing: {e!s}",
        ) from e

    # Commit changes
    await db.commit()

    return VideoUploadCompleteResponse(
        job_id=job_id_value,
        status=status_value,
        sqs_message_id=message_id,
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

        logger = log_module.getLogger(__name__)
        logger.exception(f"KeyError in video analysis pipeline: {e}")
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
