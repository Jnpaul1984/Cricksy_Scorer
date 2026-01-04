"""
Video Moment Markers API

Endpoints for coaches to create timestamped markers in video sessions.
Used primarily for fielding/wicketkeeping analysis.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.sql_app.database import get_db
from backend.sql_app.models import (
    RoleEnum,
    User,
    VideoMomentMarker,
    VideoMomentType,
    VideoSession,
)

router = APIRouter(prefix="/api/coaches/markers", tags=["moment_markers"])


# Pydantic Schemas
class VideoMomentMarkerCreate(BaseModel):
    """Request schema for creating a video moment marker."""

    timestamp_ms: int = Field(..., ge=0, description="Timestamp in milliseconds from video start")
    moment_type: str = Field(
        ..., description="Type of moment: setup, catch, throw, dive, stumping, other"
    )
    description: str | None = Field(
        None, max_length=1000, description="Optional description of the moment"
    )


class VideoMomentMarkerUpdate(BaseModel):
    """Request schema for updating a video moment marker."""

    timestamp_ms: int | None = Field(None, ge=0)
    moment_type: str | None = None
    description: str | None = Field(None, max_length=1000)


class VideoMomentMarkerRead(BaseModel):
    """Response schema for a video moment marker."""

    id: str
    video_session_id: str
    timestamp_ms: int
    moment_type: str
    description: str | None = None
    created_by: str
    created_at: str


@router.post(
    "/sessions/{session_id}/markers",
    response_model=VideoMomentMarkerRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_moment_marker(
    session_id: str,
    marker_data: VideoMomentMarkerCreate,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoMomentMarkerRead:
    """
    Create a new moment marker in a video session.

    Only coach_pro_plus, org_pro, or superuser can create markers.
    User must own the video session.
    """
    # Verify user is a coach or admin
    allowed_roles = [RoleEnum.coach_pro_plus, RoleEnum.org_pro]
    if current_user.role not in allowed_roles and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus or Org Pro users can create moment markers",
            headers={"X-Error-Code": "403_UNAUTHORIZED"},
        )

    # Validate moment_type enum
    try:
        moment_type_enum = VideoMomentType(marker_data.moment_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid moment_type. Must be one of: {', '.join([e.value for e in VideoMomentType])}",
            headers={"X-Error-Code": "422_VALIDATION_ERROR"},
        )

    # Verify session exists and user has access
    session = await db.get(VideoSession, session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video session not found",
            headers={"X-Error-Code": "404_NOT_FOUND"},
        )

    # Check ownership
    is_owner = False
    if (
        session.owner_id == current_user.id
        or session.owner_type.value == "org"
        and session.owner_id == current_user.org_id
    ):
        is_owner = True

    if not is_owner and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this video session",
            headers={"X-Error-Code": "403_UNAUTHORIZED"},
        )

    # Create marker
    marker = VideoMomentMarker(
        id=str(uuid.uuid4()),
        video_session_id=session_id,
        timestamp_ms=marker_data.timestamp_ms,
        moment_type=moment_type_enum,
        description=marker_data.description,
        created_by=current_user.id,
        created_at=dt.datetime.now(dt.timezone.utc),
    )

    db.add(marker)
    await db.commit()
    await db.refresh(marker)

    return VideoMomentMarkerRead(
        id=marker.id,
        video_session_id=marker.video_session_id,
        timestamp_ms=marker.timestamp_ms,
        moment_type=marker.moment_type.value,
        description=marker.description,
        created_by=marker.created_by,
        created_at=marker.created_at.isoformat(),
    )


@router.get("/sessions/{session_id}/markers", response_model=list[VideoMomentMarkerRead])
async def list_session_markers(
    session_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    moment_type: str | None = Query(None, description="Filter by moment type"),
) -> list[VideoMomentMarkerRead]:
    """
    List all moment markers for a video session.

    Returns markers ordered by timestamp_ms ascending.
    """
    # Verify user is a coach or admin
    allowed_roles = [RoleEnum.coach_pro_plus, RoleEnum.org_pro]
    if current_user.role not in allowed_roles and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus or Org Pro users can view moment markers",
            headers={"X-Error-Code": "403_UNAUTHORIZED"},
        )

    # Verify session exists and user has access
    session = await db.get(VideoSession, session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Video session not found",
            headers={"X-Error-Code": "404_NOT_FOUND"},
        )

    # Check ownership
    is_owner = False
    if (
        session.owner_id == current_user.id
        or session.owner_type.value == "org"
        and session.owner_id == current_user.org_id
    ):
        is_owner = True

    if not is_owner and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this video session",
            headers={"X-Error-Code": "403_UNAUTHORIZED"},
        )

    # Build query
    query = select(VideoMomentMarker).where(VideoMomentMarker.video_session_id == session_id)

    # Filter by moment_type if provided
    if moment_type:
        try:
            moment_type_enum = VideoMomentType(moment_type)
            query = query.where(VideoMomentMarker.moment_type == moment_type_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid moment_type. Must be one of: {', '.join([e.value for e in VideoMomentType])}",
                headers={"X-Error-Code": "422_VALIDATION_ERROR"},
            )

    # Order by timestamp
    query = query.order_by(VideoMomentMarker.timestamp_ms.asc())

    result = await db.execute(query)
    markers = result.scalars().all()

    return [
        VideoMomentMarkerRead(
            id=marker.id,
            video_session_id=marker.video_session_id,
            timestamp_ms=marker.timestamp_ms,
            moment_type=marker.moment_type.value,
            description=marker.description,
            created_by=marker.created_by,
            created_at=marker.created_at.isoformat(),
        )
        for marker in markers
    ]


@router.patch("/markers/{marker_id}", response_model=VideoMomentMarkerRead)
async def update_moment_marker(
    marker_id: str,
    marker_data: VideoMomentMarkerUpdate,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoMomentMarkerRead:
    """
    Update an existing moment marker.

    Only the creator can update their own markers.
    """
    # Fetch marker
    marker = await db.get(VideoMomentMarker, marker_id)

    if not marker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moment marker not found",
            headers={"X-Error-Code": "404_NOT_FOUND"},
        )

    # Check ownership (must be creator)
    if marker.created_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own moment markers",
            headers={"X-Error-Code": "403_UNAUTHORIZED"},
        )

    # Update fields
    if marker_data.timestamp_ms is not None:
        marker.timestamp_ms = marker_data.timestamp_ms

    if marker_data.moment_type is not None:
        try:
            moment_type_enum = VideoMomentType(marker_data.moment_type)
            marker.moment_type = moment_type_enum
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid moment_type. Must be one of: {', '.join([e.value for e in VideoMomentType])}",
                headers={"X-Error-Code": "422_VALIDATION_ERROR"},
            )

    if marker_data.description is not None:
        marker.description = marker_data.description

    await db.commit()
    await db.refresh(marker)

    return VideoMomentMarkerRead(
        id=marker.id,
        video_session_id=marker.video_session_id,
        timestamp_ms=marker.timestamp_ms,
        moment_type=marker.moment_type.value,
        description=marker.description,
        created_by=marker.created_by,
        created_at=marker.created_at.isoformat(),
    )


@router.delete("/markers/{marker_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_moment_marker(
    marker_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete a moment marker.

    Only the creator or superuser can delete markers.
    """
    # Fetch marker
    marker = await db.get(VideoMomentMarker, marker_id)

    if not marker:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Moment marker not found",
            headers={"X-Error-Code": "404_NOT_FOUND"},
        )

    # Check ownership (must be creator or superuser)
    if marker.created_by != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own moment markers",
            headers={"X-Error-Code": "403_UNAUTHORIZED"},
        )

    await db.delete(marker)
    await db.commit()
