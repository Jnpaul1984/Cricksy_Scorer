from __future__ import annotations

import datetime as dt
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.services.player_development_dashboard_service import (
    get_team_development_overview,
)
from backend.services.player_development_plan_service import (
    generate_draft_player_development_plan,
    get_draft_plan_by_id,
    list_player_draft_plans,
)
from backend.services.player_development_report_service import (
    get_player_development_report_by_plan,
    get_player_development_report_by_player,
    get_team_development_summary_report,
)
from backend.sql_app import models, schemas
from backend.sql_app.database import get_db

router = APIRouter(prefix="/api/player-development", tags=["player-development"])
UTC = getattr(dt, "UTC", dt.UTC)


async def _ensure_player_profile(
    db: AsyncSession,
    player_id: str,
) -> models.PlayerProfile:
    profile = await db.get(models.PlayerProfile, player_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Player profile not found")
    return profile


async def _get_active_assignment(
    db: AsyncSession,
    coach_user_id: str,
    player_id: str,
) -> models.CoachPlayerAssignment | None:
    result = await db.execute(
        select(models.CoachPlayerAssignment).where(
            models.CoachPlayerAssignment.coach_user_id == coach_user_id,
            models.CoachPlayerAssignment.player_profile_id == player_id,
            models.CoachPlayerAssignment.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def _ensure_generation_access(
    db: AsyncSession,
    current_user: models.User,
    player_id: str,
) -> models.PlayerProfile:
    profile = await _ensure_player_profile(db, player_id)
    role_value = getattr(current_user.role, "value", current_user.role)

    if role_value in {"coach_pro", "coach_pro_plus"}:
        assignment = await _get_active_assignment(db, current_user.id, player_id)
        if assignment is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Coach not assigned")
        return profile

    if role_value == "org_pro":
        if not current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization access is not configured for this user",
            )
        result = await db.execute(
            select(models.CoachPlayerAssignment)
            .join(models.User, models.User.id == models.CoachPlayerAssignment.coach_user_id)
            .where(
                models.CoachPlayerAssignment.player_profile_id == player_id,
                models.CoachPlayerAssignment.is_active.is_(True),
                models.User.org_id == current_user.org_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Player is not assigned within your organization",
            )
        return profile

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


async def _ensure_plan_access(
    db: AsyncSession,
    current_user: models.User,
    plan: models.PlayerDevelopmentPlan,
) -> None:
    role_value = getattr(current_user.role, "value", current_user.role)

    if role_value == "org_pro":
        if plan.org_id != current_user.org_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return

    if current_user.org_id and plan.org_id != current_user.org_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    assignment = await _get_active_assignment(db, current_user.id, plan.player_profile_id)
    if assignment is None and plan.coach_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


def _serialize_plan(
    plan: models.PlayerDevelopmentPlan,
) -> schemas.PlayerDevelopmentPlanDraftBundle:
    return schemas.PlayerDevelopmentPlanDraftBundle(
        plan=schemas.PlayerDevelopmentPlanRead.model_validate(plan),
        goals=[
            schemas.PlayerDevelopmentGoalRead.model_validate(goal)
            for goal in sorted(plan.goals, key=lambda item: item.created_at)
        ],
        weakness_tags=[
            schemas.PlayerWeaknessTagRead.model_validate(tag)
            for tag in sorted(plan.weakness_tags, key=lambda item: item.created_at)
        ],
        strength_tags=[
            schemas.PlayerStrengthTagRead.model_validate(tag)
            for tag in sorted(plan.strength_tags, key=lambda item: item.created_at)
        ],
        drill_assignments=[
            schemas.PlayerDrillAssignmentRead.model_validate(drill)
            for drill in sorted(plan.drill_assignments, key=lambda item: item.created_at)
        ],
        progress_checkpoints=[
            schemas.PlayerProgressCheckpointRead.model_validate(checkpoint)
            for checkpoint in sorted(plan.progress_checkpoints, key=lambda item: item.created_at)
        ],
    )


def _review_decision_to_state(
    decision: schemas.PlayerDevelopmentPlanReviewDecision,
) -> tuple[models.PlayerDevelopmentApprovalState, bool]:
    if decision == schemas.PlayerDevelopmentPlanReviewDecision.approved:
        return models.PlayerDevelopmentApprovalState.approved, True
    if decision == schemas.PlayerDevelopmentPlanReviewDecision.rejected:
        return models.PlayerDevelopmentApprovalState.rejected, False
    return models.PlayerDevelopmentApprovalState.changes_requested, False


@router.post(
    "/players/{player_id}/draft-plan",
    response_model=schemas.PlayerDevelopmentPlanDraftGenerationResponse,
)
async def create_player_development_draft_plan(
    player_id: str,
    current_user: Annotated[
        models.User,
        Depends(security.require_roles(["coach_pro", "coach_pro_plus", "org_pro"])),
    ],
    payload: schemas.PlayerDevelopmentPlanDraftGenerateRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> schemas.PlayerDevelopmentPlanDraftGenerationResponse:
    await _ensure_generation_access(db, current_user, player_id)

    try:
        result = await generate_draft_player_development_plan(
            db=db,
            player_profile_id=player_id,
            coach_user=current_user,
            additional_evidence_refs=(payload.additional_evidence_refs if payload else []),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None

    plan_bundle = None
    if result.plan_id is not None:
        plan = await get_draft_plan_by_id(db, result.plan_id)
        if plan is not None:
            plan_bundle = _serialize_plan(plan)

    return schemas.PlayerDevelopmentPlanDraftGenerationResponse(
        status=result.status,
        player_profile_id=result.player_profile_id,
        plan=plan_bundle,
        evidence_refs=result.evidence_refs,
        confidence_score=result.confidence_score,
        limitations=result.limitations,
        coach_review_required=True,
    )


@router.get(
    "/dashboard/team-overview",
    response_model=schemas.PlayerDevelopmentTeamOverviewRead,
)
async def get_player_development_team_dashboard(
    current_user: Annotated[
        models.User,
        Depends(security.require_roles(["coach_pro", "coach_pro_plus", "org_pro"])),
    ],
    include_archived: bool = False,
    db: AsyncSession = Depends(get_db),
) -> schemas.PlayerDevelopmentTeamOverviewRead:
    return await get_team_development_overview(
        db=db,
        current_user=current_user,
        include_archived=include_archived,
    )


@router.get(
    "/plans/{plan_id}",
    response_model=schemas.PlayerDevelopmentPlanDraftBundle,
)
async def get_player_development_plan(
    plan_id: str,
    current_user: Annotated[
        models.User,
        Depends(security.require_roles(["coach_pro", "coach_pro_plus", "org_pro"])),
    ],
    db: AsyncSession = Depends(get_db),
) -> schemas.PlayerDevelopmentPlanDraftBundle:
    plan = await get_draft_plan_by_id(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Player development plan not found")
    await _ensure_plan_access(db, current_user, plan)
    return _serialize_plan(plan)


@router.patch(
    "/plans/{plan_id}/review",
    response_model=schemas.PlayerDevelopmentPlanReviewResponse,
)
async def review_player_development_plan(
    plan_id: str,
    payload: schemas.PlayerDevelopmentPlanReviewRequest,
    current_user: Annotated[
        models.User,
        Depends(security.require_roles(["coach_pro_plus", "org_pro"])),
    ],
    db: AsyncSession = Depends(get_db),
) -> schemas.PlayerDevelopmentPlanReviewResponse:
    plan = await get_draft_plan_by_id(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Player development plan not found")
    await _ensure_plan_access(db, current_user, plan)

    if plan.status in {
        models.PlayerDevelopmentPlanStatus.archived,
        models.PlayerDevelopmentPlanStatus.completed,
    }:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Player development plan cannot be reviewed in its current status",
        )

    approval_state, coach_approved = _review_decision_to_state(payload.decision)
    plan.approval_state = approval_state
    plan.coach_approved = coach_approved
    await db.commit()

    return schemas.PlayerDevelopmentPlanReviewResponse(
        plan_id=plan.id,
        approval_state=plan.approval_state,
        coach_approved=plan.coach_approved,
        reviewer_notes=payload.reviewer_notes,
        reviewed_by_user_id=current_user.id,
        reviewed_at=dt.datetime.now(UTC),
    )


@router.get(
    "/players/{player_id}/plans",
    response_model=list[schemas.PlayerDevelopmentPlanDraftBundle],
)
async def list_player_development_plans(
    player_id: str,
    current_user: Annotated[
        models.User,
        Depends(security.require_roles(["coach_pro", "coach_pro_plus", "org_pro"])),
    ],
    db: AsyncSession = Depends(get_db),
) -> list[schemas.PlayerDevelopmentPlanDraftBundle]:
    await _ensure_generation_access(db, current_user, player_id)
    role_value = getattr(current_user.role, "value", current_user.role)
    if role_value in {"coach_pro", "coach_pro_plus"}:
        plans = await list_player_draft_plans(
            db=db,
            player_profile_id=player_id,
            coach_user_id=current_user.id,
        )
    else:
        if not current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization access is not configured for this user",
            )
        plans = await list_player_draft_plans(
            db=db,
            player_profile_id=player_id,
            org_id=current_user.org_id,
        )
    visible_plans: list[schemas.PlayerDevelopmentPlanDraftBundle] = []
    for plan in plans:
        await _ensure_plan_access(db, current_user, plan)
        visible_plans.append(_serialize_plan(plan))
    return visible_plans


@router.get(
    "/reports/players/{player_id}",
    response_model=schemas.PlayerDevelopmentPlayerReportRead,
)
async def get_player_development_player_report(
    player_id: str,
    current_user: Annotated[
        models.User,
        Depends(security.require_roles(["coach_pro", "coach_pro_plus", "org_pro"])),
    ],
    plan_id: str | None = None,
    include_archived: bool = False,
    audience: schemas.PlayerDevelopmentReportAudience = (
        schemas.PlayerDevelopmentReportAudience.coach
    ),
    db: AsyncSession = Depends(get_db),
) -> schemas.PlayerDevelopmentPlayerReportRead:
    await _ensure_generation_access(db, current_user, player_id)
    if plan_id is not None:
        plan = await get_draft_plan_by_id(db, plan_id)
        if plan is None:
            raise HTTPException(status_code=404, detail="Player development plan not found")
        await _ensure_plan_access(db, current_user, plan)
        if plan.player_profile_id != player_id:
            raise HTTPException(status_code=404, detail="Player development plan not found")
        if (
            not include_archived
            and plan.status == models.PlayerDevelopmentPlanStatus.archived
        ):
            raise HTTPException(status_code=404, detail="Player development plan not found")

    try:
        return await get_player_development_report_by_player(
            db=db,
            current_user=current_user,
            player_id=player_id,
            audience=audience,
            include_archived=include_archived,
            plan_id=plan_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get(
    "/reports/plans/{plan_id}",
    response_model=schemas.PlayerDevelopmentPlayerReportRead,
)
async def get_player_development_plan_report(
    plan_id: str,
    current_user: Annotated[
        models.User,
        Depends(security.require_roles(["coach_pro", "coach_pro_plus", "org_pro"])),
    ],
    audience: schemas.PlayerDevelopmentReportAudience = (
        schemas.PlayerDevelopmentReportAudience.coach
    ),
    db: AsyncSession = Depends(get_db),
) -> schemas.PlayerDevelopmentPlayerReportRead:
    plan = await get_draft_plan_by_id(db, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Player development plan not found")
    await _ensure_plan_access(db, current_user, plan)
    try:
        return await get_player_development_report_by_plan(
            db=db,
            plan=plan,
            audience=audience,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None


@router.get(
    "/reports/team-summary",
    response_model=schemas.PlayerDevelopmentTeamSummaryReportRead,
)
async def get_player_development_team_summary_report(
    current_user: Annotated[
        models.User,
        Depends(security.require_roles(["coach_pro", "coach_pro_plus", "org_pro"])),
    ],
    include_archived: bool = False,
    audience: schemas.PlayerDevelopmentReportAudience = (
        schemas.PlayerDevelopmentReportAudience.coach
    ),
    db: AsyncSession = Depends(get_db),
) -> schemas.PlayerDevelopmentTeamSummaryReportRead:
    return await get_team_development_summary_report(
        db=db,
        current_user=current_user,
        include_archived=include_archived,
        audience=audience,
    )
