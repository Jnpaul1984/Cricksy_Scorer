"""
Coach Pro Plus Routes - Video Sessions Scaffolding

Provides placeholder endpoints for video session management.
Real video upload/streaming will be implemented in future phases.
Feature-gated by role (coach_pro_plus, org_pro).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.sql_app.database import get_db
from backend.sql_app.models import RoleEnum, User

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
    coach_id: str
    title: str
    player_ids: list[str]
    status: str  # "pending", "uploaded", "processing", "ready"
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


# ============================================================================
# In-Memory Store (Placeholder)
# ============================================================================
# In production, this will be backed by a VideoSession SQLAlchemy model
# For now, we use a simple in-memory dict for scaffolding

_video_sessions: dict[str, dict] = {}


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
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_upload_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_upload_enabled",
        )

    # Verify user is coach_pro_plus or org_pro
    if current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can create video sessions",
        )

    session_id = str(uuid4())
    now = datetime.now(UTC)

    session = {
        "id": session_id,
        "coach_id": current_user.id,
        "title": session_data.title,
        "player_ids": session_data.player_ids,
        "status": "pending",
        "notes": session_data.notes,
        "created_at": now,
        "updated_at": now,
    }

    _video_sessions[session_id] = session

    return VideoSessionRead(**session)


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
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # Verify user is coach_pro_plus or org_pro
    if current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can view video sessions",
        )

    # Filter sessions by coach_id
    user_sessions = [
        session for session in _video_sessions.values() if session["coach_id"] == current_user.id
    ]

    # Apply pagination
    paginated = user_sessions[offset : offset + limit]

    return [VideoSessionRead(**session) for session in paginated]


@router.get("/sessions/{session_id}", response_model=VideoSessionRead)
async def get_video_session(
    session_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoSessionRead:
    """
    Get a specific video session (Coach Pro Plus feature).

    Feature-gated: Requires coach_pro_plus role.
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_sessions_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_sessions_enabled",
        )

    # Verify user is coach_pro_plus or org_pro
    if current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can access video sessions",
        )

    session = _video_sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    # Verify ownership
    if session["coach_id"] != current_user.id and current_user.role != RoleEnum.org_pro:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="You don't have access to this session"
        )

    return VideoSessionRead(**session)


# ============================================================================
# TODO: Future Endpoints (Video Upload/Streaming)
# ============================================================================
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
