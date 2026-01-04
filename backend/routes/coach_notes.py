"""
Coach Notes API

Endpoints for coaches to create and manage notes on players,
including linking notes to video sessions and AI corrective guidance.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.services.corrective_guidance_service import get_corrective_guidance
from backend.sql_app.database import get_db
from backend.sql_app.models import (
    CoachNote,
    CoachNoteSeverity,
    Player,
    RoleEnum,
    User,
    VideoSession,
)

router = APIRouter(prefix="/api/coaches", tags=["coach_notes"])


# Pydantic Schemas
class CoachNoteCreate(BaseModel):
    """Request schema for creating a coach note."""

    player_id: int
    note_text: str
    video_session_id: str | None = None
    moment_marker_id: str | None = None
    tags: list[str] | None = None
    severity: str = "info"  # "info", "improvement", "critical"


class CoachNoteUpdate(BaseModel):
    """Request schema for updating a coach note."""

    note_text: str | None = None
    tags: list[str] | None = None
    severity: str | None = None


class CoachNoteRead(BaseModel):
    """Response schema for a coach note."""

    id: str
    coach_id: str
    player_id: int
    player_name: str | None = None
    video_session_id: str | None = None
    video_session_title: str | None = None
    moment_marker_id: str | None = None
    note_text: str
    tags: list[str] | None = None
    severity: str
    created_at: str
    updated_at: str


@router.post(
    "/players/{player_id}/notes", response_model=CoachNoteRead, status_code=status.HTTP_201_CREATED
)
async def create_coach_note(
    player_id: int,
    note_data: CoachNoteCreate,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> CoachNoteRead:
    """
    Create a new coach note for a player.

    Only coach_pro, coach_pro_plus, org_pro, or superuser can create notes.
    """
    # Verify user is a coach or admin
    allowed_roles = [RoleEnum.coach_pro, RoleEnum.coach_pro_plus, RoleEnum.org_pro]
    if current_user.role not in allowed_roles and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coaches can create notes on players",
        )

    # Verify player exists
    player = await db.get(Player, player_id)
    if not player:
        raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

    # Validate severity
    try:
        severity_enum = CoachNoteSeverity(note_data.severity)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid severity. Must be one of: info, improvement, critical",
        )

    # If video_session_id provided, verify it exists
    video_session = None
    if note_data.video_session_id:
        video_session = await db.get(VideoSession, note_data.video_session_id)
        if not video_session:
            raise HTTPException(status_code=404, detail="Video session not found")

    # Create note
    now = dt.datetime.now(dt.timezone.utc)
    note = CoachNote(
        id=str(uuid.uuid4()),
        coach_id=current_user.id,
        player_id=player_id,
        video_session_id=note_data.video_session_id,
        moment_marker_id=note_data.moment_marker_id,
        note_text=note_data.note_text,
        tags=note_data.tags,
        severity=severity_enum,
        created_at=now,
        updated_at=now,
    )

    db.add(note)
    await db.commit()
    await db.refresh(note)

    return CoachNoteRead(
        id=note.id,
        coach_id=note.coach_id,
        player_id=note.player_id,
        player_name=player.name,
        video_session_id=note.video_session_id,
        video_session_title=video_session.title if video_session else None,
        moment_marker_id=note.moment_marker_id,
        note_text=note.note_text,
        tags=note.tags,
        severity=note.severity.value,
        created_at=note.created_at.isoformat(),
        updated_at=note.updated_at.isoformat(),
    )


@router.get("/players/{player_id}/notes", response_model=list[CoachNoteRead])
async def list_player_notes(
    player_id: int,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    severity: str | None = Query(
        None, description="Filter by severity: info, improvement, critical"
    ),
    video_session_id: str | None = Query(None, description="Filter by video session ID"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[CoachNoteRead]:
    """
    Get all coach notes for a specific player.

    Accessible by coaches and admins.
    """
    # Verify user is a coach or admin
    allowed_roles = [RoleEnum.coach_pro, RoleEnum.coach_pro_plus, RoleEnum.org_pro]
    if current_user.role not in allowed_roles and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coaches can view player notes",
        )

    # Build query
    query = select(CoachNote).where(CoachNote.player_id == player_id)

    if severity:
        try:
            severity_enum = CoachNoteSeverity(severity)
            query = query.where(CoachNote.severity == severity_enum)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid severity. Must be one of: info, improvement, critical",
            )

    if video_session_id:
        query = query.where(CoachNote.video_session_id == video_session_id)

    query = query.order_by(CoachNote.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    notes = result.scalars().all()

    # Fetch player name
    player = await db.get(Player, player_id)
    player_name = player.name if player else None

    # Fetch video session titles if needed
    session_ids = [note.video_session_id for note in notes if note.video_session_id]
    sessions_dict = {}
    if session_ids:
        sessions_result = await db.execute(
            select(VideoSession).where(VideoSession.id.in_(session_ids))
        )
        sessions_dict = {s.id: s.title for s in sessions_result.scalars().all()}

    return [
        CoachNoteRead(
            id=note.id,
            coach_id=note.coach_id,
            player_id=note.player_id,
            player_name=player_name,
            video_session_id=note.video_session_id,
            video_session_title=sessions_dict.get(note.video_session_id)
            if note.video_session_id
            else None,
            moment_marker_id=note.moment_marker_id,
            note_text=note.note_text,
            tags=note.tags,
            severity=note.severity.value,
            created_at=note.created_at.isoformat(),
            updated_at=note.updated_at.isoformat(),
        )
        for note in notes
    ]


@router.get("/notes/{note_id}", response_model=CoachNoteRead)
async def get_coach_note(
    note_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> CoachNoteRead:
    """Get a specific coach note by ID."""
    # Verify user is a coach or admin
    allowed_roles = [RoleEnum.coach_pro, RoleEnum.coach_pro_plus, RoleEnum.org_pro]
    if current_user.role not in allowed_roles and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coaches can view notes",
        )

    note = await db.get(CoachNote, note_id)

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Fetch player name
    player = await db.get(Player, note.player_id)

    # Fetch video session if linked
    video_session = None
    if note.video_session_id:
        video_session = await db.get(VideoSession, note.video_session_id)

    return CoachNoteRead(
        id=note.id,
        coach_id=note.coach_id,
        player_id=note.player_id,
        player_name=player.name if player else None,
        video_session_id=note.video_session_id,
        video_session_title=video_session.title if video_session else None,
        moment_marker_id=note.moment_marker_id,
        note_text=note.note_text,
        tags=note.tags,
        severity=note.severity.value,
        created_at=note.created_at.isoformat(),
        updated_at=note.updated_at.isoformat(),
    )


@router.patch("/notes/{note_id}", response_model=CoachNoteRead)
async def update_coach_note(
    note_id: str,
    update_data: CoachNoteUpdate,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> CoachNoteRead:
    """
    Update a coach note.

    Only the coach who created the note or a superuser can update it.
    """
    note = await db.get(CoachNote, note_id)

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Verify ownership
    if note.coach_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only update your own notes",
        )

    # Update fields
    if update_data.note_text is not None:
        note.note_text = update_data.note_text

    if update_data.tags is not None:
        note.tags = update_data.tags

    if update_data.severity is not None:
        try:
            note.severity = CoachNoteSeverity(update_data.severity)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid severity. Must be one of: info, improvement, critical",
            )

    # Update timestamp for in-memory mode
    note.updated_at = dt.datetime.now(dt.timezone.utc)

    await db.commit()
    await db.refresh(note)

    # Fetch player and video session for response
    player = await db.get(Player, note.player_id)

    video_session = None
    if note.video_session_id:
        video_session = await db.get(VideoSession, note.video_session_id)

    return CoachNoteRead(
        id=note.id,
        coach_id=note.coach_id,
        player_id=note.player_id,
        player_name=player.name if player else None,
        video_session_id=note.video_session_id,
        video_session_title=video_session.title if video_session else None,
        moment_marker_id=note.moment_marker_id,
        note_text=note.note_text,
        tags=note.tags,
        severity=note.severity.value,
        created_at=note.created_at.isoformat(),
        updated_at=note.updated_at.isoformat(),
    )


@router.delete("/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_coach_note(
    note_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a coach note.

    Only the coach who created the note or a superuser can delete it.
    """
    note = await db.get(CoachNote, note_id)

    if not note:
        raise HTTPException(status_code=404, detail="Note not found")

    # Verify ownership
    if note.coach_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only delete your own notes",
        )

    await db.delete(note)
    await db.commit()


# ============================
# AI Corrective Guidance
# ============================


class CorrectiveGuidanceRequest(BaseModel):
    """Request schema for corrective guidance."""

    role: str  # "batting", "bowling", "fielding", "wicketkeeping"
    skill_focus: str  # e.g., "footwork", "timing", "catching"
    note_text: str | None = None


class CheckpointResponse(BaseModel):
    """A single corrective checkpoint."""

    title: str
    description: str
    priority: str


class DrillResponse(BaseModel):
    """A practice drill recommendation."""

    name: str
    description: str
    duration_minutes: int
    equipment: list[str]


class CorrectiveGuidanceResponse(BaseModel):
    """Response schema for corrective guidance."""

    checkpoints: list[CheckpointResponse]
    drills: list[DrillResponse]
    reference_media: list[str]


@router.post("/corrective-guidance", response_model=CorrectiveGuidanceResponse)
async def get_ai_corrective_guidance(
    request: CorrectiveGuidanceRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
) -> CorrectiveGuidanceResponse:
    """
    Get AI-powered corrective guidance for coaching.

    Provides 3-5 corrective checkpoints, drill suggestions, and reference media
    based on the player's role and skill focus.

    **Permissions**: Coach Pro, Coach Pro Plus, Org Pro
    """
    # Verify user is a coach or admin
    allowed_roles = [RoleEnum.coach_pro, RoleEnum.coach_pro_plus, RoleEnum.org_pro]
    if current_user.role not in allowed_roles and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only coaches can access corrective guidance",
        )

    # Validate role
    valid_roles = ["batting", "bowling", "fielding", "wicketkeeping"]
    if request.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
        )

    # Generate guidance
    guidance = get_corrective_guidance(
        role=request.role,
        skill_focus=request.skill_focus,
        note_text=request.note_text,
    )

    return CorrectiveGuidanceResponse(**guidance)
