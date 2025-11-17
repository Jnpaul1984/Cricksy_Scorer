from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.sql_app.database import get_db
from backend.sql_app.models import (
    CoachPlayerAssignment,
    CoachingSession,
    PlayerProfile,
    RoleEnum,
    User,
)
from backend.sql_app.schemas import (
    CoachPlayerAssignmentCreate,
    CoachPlayerAssignmentRead,
    CoachingSessionCreate,
    CoachingSessionRead,
    CoachingSessionUpdate,
)

router = APIRouter(prefix="/api/coaches", tags=["coach_pro"])


async def _ensure_player_profile(db: AsyncSession, player_id: str) -> PlayerProfile:
    profile = await db.get(PlayerProfile, player_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Player profile not found")
    return profile


async def _get_active_assignment(
    db: AsyncSession, coach_user_id: str, player_id: str
) -> CoachPlayerAssignment | None:
    result = await db.execute(
        select(CoachPlayerAssignment).where(
            CoachPlayerAssignment.coach_user_id == coach_user_id,
            CoachPlayerAssignment.player_profile_id == player_id,
            CoachPlayerAssignment.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def _ensure_coach_user(db: AsyncSession, coach_user_id: str) -> User:
    coach = await db.get(User, coach_user_id)
    if coach is None or coach.role not in (RoleEnum.coach_pro, RoleEnum.org_pro):
        raise HTTPException(status_code=400, detail="Coach user not found or invalid role")
    return coach


@router.post("/assign-player", response_model=CoachPlayerAssignmentRead)
async def assign_player(
    assignment: CoachPlayerAssignmentCreate,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> CoachPlayerAssignment:
    if not (current_user.is_superuser or current_user.role == RoleEnum.org_pro):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    await _ensure_coach_user(db, assignment.coach_user_id)
    await _ensure_player_profile(db, assignment.player_profile_id)

    existing = await db.execute(
        select(CoachPlayerAssignment).where(
            CoachPlayerAssignment.coach_user_id == assignment.coach_user_id,
            CoachPlayerAssignment.player_profile_id == assignment.player_profile_id,
        )
    )
    assignment_row = existing.scalar_one_or_none()
    if assignment_row:
        assignment_row.is_active = True
        await db.commit()
        await db.refresh(assignment_row)
        return assignment_row

    assignment_model = CoachPlayerAssignment(
        coach_user_id=assignment.coach_user_id,
        player_profile_id=assignment.player_profile_id,
        is_active=True,
    )
    db.add(assignment_model)
    await db.commit()
    await db.refresh(assignment_model)
    return assignment_model


@router.get("/me/players", response_model=list[CoachPlayerAssignmentRead])
async def list_assigned_players(
    current_user: Annotated[User, Depends(security.require_roles(["coach_pro", "org_pro"]))],
    db: AsyncSession = Depends(get_db),
) -> list[CoachPlayerAssignment]:
    stmt = select(CoachPlayerAssignment).where(CoachPlayerAssignment.is_active.is_(True))
    if current_user.role == RoleEnum.coach_pro:
        stmt = stmt.where(CoachPlayerAssignment.coach_user_id == current_user.id)
    result = await db.execute(stmt.order_by(CoachPlayerAssignment.created_at.desc()))
    return result.scalars().all()


@router.get(
    "/players/{player_id}/sessions",
    response_model=list[CoachingSessionRead],
)
async def list_coaching_sessions(
    player_id: str,
    current_user: Annotated[User, Depends(security.require_roles(["coach_pro", "org_pro"]))],
    db: AsyncSession = Depends(get_db),
) -> list[CoachingSession]:
    await _ensure_player_profile(db, player_id)
    stmt = select(CoachingSession).where(CoachingSession.player_profile_id == player_id)
    if current_user.role == RoleEnum.coach_pro:
        assignment = await _get_active_assignment(db, current_user.id, player_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Coach not assigned")
        stmt = stmt.where(CoachingSession.coach_user_id == current_user.id)
    result = await db.execute(stmt.order_by(CoachingSession.scheduled_at.desc()))
    return result.scalars().all()


@router.post(
    "/players/{player_id}/sessions",
    response_model=CoachingSessionRead,
)
async def create_coaching_session(
    player_id: str,
    session_data: CoachingSessionCreate,
    current_user: Annotated[User, Depends(security.require_roles(["coach_pro", "org_pro"]))],
    db: AsyncSession = Depends(get_db),
) -> CoachingSession:
    await _ensure_player_profile(db, player_id)
    if current_user.role == RoleEnum.coach_pro:
        coach_user_id = current_user.id
        assignment = await _get_active_assignment(db, coach_user_id, player_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Coach not assigned")
    else:
        coach_user_id = session_data.coach_user_id or current_user.id
        await _ensure_coach_user(db, coach_user_id)
        assignment = await _get_active_assignment(db, coach_user_id, player_id)
        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Coach is not assigned to this player",
            )

    session = CoachingSession(
        coach_user_id=coach_user_id,
        player_profile_id=player_id,
        scheduled_at=session_data.scheduled_at,
        duration_minutes=session_data.duration_minutes,
        focus_area=session_data.focus_area,
        notes=session_data.notes,
        outcome=session_data.outcome,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.put(
    "/players/{player_id}/sessions/{session_id}",
    response_model=CoachingSessionRead,
)
async def update_coaching_session(
    player_id: str,
    session_id: str,
    session_data: CoachingSessionUpdate,
    current_user: Annotated[User, Depends(security.require_roles(["coach_pro", "org_pro"]))],
    db: AsyncSession = Depends(get_db),
) -> CoachingSession:
    session = await db.get(CoachingSession, session_id)
    if session is None or session.player_profile_id != player_id:
        raise HTTPException(status_code=404, detail="Coaching session not found")

    if current_user.role == RoleEnum.coach_pro:
        if session.coach_user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        assignment = await _get_active_assignment(db, current_user.id, player_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Coach not assigned")

    update_data = session_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)

    await db.commit()
    await db.refresh(session)
    return session
