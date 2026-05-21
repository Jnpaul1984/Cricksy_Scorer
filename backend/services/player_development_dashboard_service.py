from __future__ import annotations

import datetime as dt
from collections import Counter, defaultdict
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.sql_app import models, schemas

_MORE_EVIDENCE_CONFIDENCE_THRESHOLD = 0.6


async def get_team_development_overview(
    db: AsyncSession,
    current_user: models.User,
    *,
    include_archived: bool = False,
) -> schemas.PlayerDevelopmentTeamOverviewRead:
    scoped_profiles = await _list_scoped_player_profiles(db, current_user)
    if not scoped_profiles:
        return schemas.PlayerDevelopmentTeamOverviewRead()

    profile_by_id = {profile.player_id: profile for profile in scoped_profiles}
    scoped_player_ids = list(profile_by_id)
    visible_plans = await _list_visible_plans(
        db=db,
        current_user=current_user,
        player_ids=scoped_player_ids,
        include_archived=include_archived,
    )
    latest_plans = _latest_plan_by_player(visible_plans)

    players_without_plan_details = [
        schemas.PlayerDevelopmentDashboardPlayerSummary(
            player_profile_id=profile.player_id,
            player_name=profile.player_name,
        )
        for profile in scoped_profiles
        if profile.player_id not in latest_plans
    ]

    plan_status_counter: Counter[str] = Counter()
    theme_players: dict[tuple[str, str], set[str]] = defaultdict(set)
    drill_status_counter: Counter[str] = Counter()
    drill_category_counter: Counter[str] = Counter()
    review_required_players: list[schemas.PlayerDevelopmentDashboardPlayerPlanSummary] = []
    more_evidence_details: list[schemas.PlayerDevelopmentDashboardPlayerPlanSummary] = []
    checkpoints: list[schemas.PlayerDevelopmentDashboardCheckpointSummary] = []
    recent_activity: dt.datetime | None = None
    players_with_goals = 0
    players_with_drills = 0
    players_with_checkpoints = 0
    total_drill_assignments = 0

    for player_id, plan in latest_plans.items():
        profile = profile_by_id[player_id]
        plan_status_counter[_enum_value(plan.status)] += 1

        if plan.goals:
            players_with_goals += 1
        if plan.drill_assignments:
            players_with_drills += 1
        if plan.progress_checkpoints:
            players_with_checkpoints += 1

        if _plan_requires_review(plan):
            review_required_players.append(
                schemas.PlayerDevelopmentDashboardPlayerPlanSummary(
                    player_profile_id=player_id,
                    player_name=profile.player_name,
                    plan_id=plan.id,
                    plan_status=plan.status,
                    confidence_score=plan.confidence_score,
                    advisory_note="Coach review is still needed before this draft is treated as a working plan.",
                )
            )

        if _plan_needs_more_evidence(plan):
            more_evidence_details.append(
                schemas.PlayerDevelopmentDashboardPlayerPlanSummary(
                    player_profile_id=player_id,
                    player_name=profile.player_name,
                    plan_id=plan.id,
                    plan_status=plan.status,
                    confidence_score=plan.confidence_score,
                    advisory_note=_plan_evidence_note(plan),
                )
            )

        for weakness_tag in plan.weakness_tags:
            theme_players[(weakness_tag.category, weakness_tag.safe_display_label)].add(player_id)

        for drill in plan.drill_assignments:
            total_drill_assignments += 1
            drill_status_counter[_enum_value(drill.status)] += 1
            drill_category_counter[drill.drill_category] += 1
            recent_activity = _latest_datetime(recent_activity, drill.updated_at, drill.created_at)

        for checkpoint in plan.progress_checkpoints:
            checkpoints.append(
                schemas.PlayerDevelopmentDashboardCheckpointSummary(
                    checkpoint_id=checkpoint.id,
                    plan_id=plan.id,
                    player_profile_id=player_id,
                    player_name=profile.player_name,
                    checkpoint_date=checkpoint.checkpoint_date,
                    progress_status=checkpoint.progress_status,
                    advisory_label=_checkpoint_advisory_label(checkpoint.checkpoint_date),
                    is_overdue=checkpoint.checkpoint_date < dt.date.today(),
                    confidence_score=checkpoint.confidence_score,
                )
            )
            recent_activity = _latest_datetime(
                recent_activity,
                checkpoint.updated_at,
                checkpoint.created_at,
            )

        recent_activity = _latest_datetime(recent_activity, plan.updated_at, plan.created_at)
        for goal in plan.goals:
            recent_activity = _latest_datetime(recent_activity, goal.updated_at, goal.created_at)
        for weakness_tag in plan.weakness_tags:
            recent_activity = _latest_datetime(
                recent_activity,
                weakness_tag.updated_at,
                weakness_tag.created_at,
            )
        for strength_tag in plan.strength_tags:
            recent_activity = _latest_datetime(
                recent_activity,
                strength_tag.updated_at,
                strength_tag.created_at,
            )

    common_development_areas = [
        schemas.PlayerDevelopmentDashboardThemeSummary(
            category=category,
            safe_display_label=safe_display_label,
            player_count=len(player_ids),
        )
        for (category, safe_display_label), player_ids in sorted(
            theme_players.items(),
            key=lambda item: (-len(item[1]), item[0][0], item[0][1]),
        )
    ]

    return schemas.PlayerDevelopmentTeamOverviewRead(
        total_assigned_players=len(scoped_profiles),
        players_with_draft_plans=len(latest_plans),
        players_without_plans=len(players_without_plan_details),
        plans_requiring_review=len(review_required_players),
        players_with_goals=players_with_goals,
        players_with_drills=players_with_drills,
        players_with_checkpoints=players_with_checkpoints,
        plans_by_status=_status_count_list(plan_status_counter),
        players_without_plan_details=players_without_plan_details,
        review_required_players=sorted(review_required_players, key=lambda item: item.player_name),
        common_development_areas=common_development_areas,
        drill_assignment_summary=schemas.PlayerDevelopmentDashboardDrillSummary(
            total_assignments=total_drill_assignments,
            by_status=_status_count_list(drill_status_counter),
            by_category=[
                schemas.PlayerDevelopmentDashboardCategoryCount(category=category, count=count)
                for category, count in sorted(
                    drill_category_counter.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
        ),
        evidence_coverage_summary=schemas.PlayerDevelopmentDashboardEvidenceCoverageSummary(
            players_with_confident_recommendations=max(
                len(latest_plans) - len(more_evidence_details), 0
            ),
            players_needing_more_evidence=len(more_evidence_details),
            players_needing_more_evidence_details=sorted(
                more_evidence_details,
                key=lambda item: item.player_name,
            ),
        ),
        upcoming_checkpoints=sorted(
            checkpoints,
            key=lambda item: (
                not item.is_overdue,
                item.checkpoint_date,
                item.player_name,
            ),
        ),
        most_recent_development_activity_at=recent_activity,
    )


async def _list_scoped_player_profiles(
    db: AsyncSession,
    current_user: models.User,
) -> list[models.PlayerProfile]:
    assignment_stmt = select(models.CoachPlayerAssignment).where(
        models.CoachPlayerAssignment.is_active.is_(True)
    )
    role_value = _enum_value(current_user.role)

    if role_value in {"coach_pro", "coach_pro_plus"}:
        assignment_stmt = assignment_stmt.where(
            models.CoachPlayerAssignment.coach_user_id == current_user.id
        )
    elif role_value == "org_pro":
        if not current_user.org_id:
            return []
        assignment_stmt = assignment_stmt.join(
            models.User, models.User.id == models.CoachPlayerAssignment.coach_user_id
        ).where(models.User.org_id == current_user.org_id)
    else:
        return []

    assignments = list((await db.execute(assignment_stmt)).scalars().all())
    player_ids = sorted({assignment.player_profile_id for assignment in assignments})
    if not player_ids:
        return []

    result = await db.execute(
        select(models.PlayerProfile)
        .where(models.PlayerProfile.player_id.in_(player_ids))
        .order_by(models.PlayerProfile.player_name.asc())
    )
    return list(result.scalars().all())


async def _list_visible_plans(
    db: AsyncSession,
    current_user: models.User,
    *,
    player_ids: list[str],
    include_archived: bool,
) -> list[models.PlayerDevelopmentPlan]:
    if not player_ids:
        return []

    stmt = (
        select(models.PlayerDevelopmentPlan)
        .where(models.PlayerDevelopmentPlan.player_profile_id.in_(player_ids))
        .options(
            selectinload(models.PlayerDevelopmentPlan.goals),
            selectinload(models.PlayerDevelopmentPlan.weakness_tags),
            selectinload(models.PlayerDevelopmentPlan.strength_tags),
            selectinload(models.PlayerDevelopmentPlan.drill_assignments),
            selectinload(models.PlayerDevelopmentPlan.progress_checkpoints),
        )
        .order_by(
            models.PlayerDevelopmentPlan.created_at.desc(),
            models.PlayerDevelopmentPlan.id.desc(),
        )
    )

    role_value = _enum_value(current_user.role)
    if role_value in {"coach_pro", "coach_pro_plus"}:
        stmt = stmt.where(models.PlayerDevelopmentPlan.coach_user_id == current_user.id)
    elif role_value == "org_pro":
        if not current_user.org_id:
            return []
        stmt = stmt.where(models.PlayerDevelopmentPlan.org_id == current_user.org_id)
    else:
        return []

    if not include_archived:
        stmt = stmt.where(
            models.PlayerDevelopmentPlan.status != models.PlayerDevelopmentPlanStatus.archived
        )

    result = await db.execute(stmt)
    return list(result.scalars().all())


def _latest_plan_by_player(
    plans: list[models.PlayerDevelopmentPlan],
) -> dict[str, models.PlayerDevelopmentPlan]:
    latest: dict[str, models.PlayerDevelopmentPlan] = {}
    for plan in plans:
        latest.setdefault(plan.player_profile_id, plan)
    return latest


def _plan_requires_review(plan: models.PlayerDevelopmentPlan) -> bool:
    return bool(
        not plan.coach_approved
        or plan.approval_state
        in {
            models.PlayerDevelopmentApprovalState.pending_review,
            models.PlayerDevelopmentApprovalState.changes_requested,
        }
    )


def _plan_needs_more_evidence(plan: models.PlayerDevelopmentPlan) -> bool:
    if plan.confidence_score is None:
        return True
    return plan.confidence_score < _MORE_EVIDENCE_CONFIDENCE_THRESHOLD


def _plan_evidence_note(plan: models.PlayerDevelopmentPlan) -> str:
    limitations = plan.ai_metadata.get("limitations")
    if isinstance(limitations, list):
        for limitation in limitations:
            if isinstance(limitation, str) and limitation.strip():
                return limitation.strip()
    return "More evidence could strengthen future development recommendations for this player."


def _checkpoint_advisory_label(checkpoint_date: dt.date) -> str:
    today = dt.date.today()
    if checkpoint_date < today:
        return "Review overdue"
    if checkpoint_date == today:
        return "Review today"
    if checkpoint_date <= today + dt.timedelta(days=7):
        return "Upcoming review this week"
    return "Upcoming review"


def _status_count_list(
    counter: Counter[str],
) -> list[schemas.PlayerDevelopmentDashboardStatusCount]:
    return [
        schemas.PlayerDevelopmentDashboardStatusCount(
            status=models.PlayerDevelopmentPlanStatus(status),
            count=count,
        )
        for status, count in sorted(counter.items(), key=lambda item: item[0])
    ]


def _latest_datetime(
    current: dt.datetime | None,
    *candidates: dt.datetime | None,
) -> dt.datetime | None:
    resolved = current
    for candidate in candidates:
        if candidate is None:
            continue
        if resolved is None or candidate > resolved:
            resolved = candidate
    return resolved


def _enum_value(value: Any) -> str:
    return getattr(value, "value", value)
