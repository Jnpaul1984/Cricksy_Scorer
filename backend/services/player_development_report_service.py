from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.services.player_development_dashboard_service import get_team_development_overview
from backend.sql_app import models, schemas

_ADVISORY_DISCLAIMER = (
    "Advisory development report only. This report does not change official match "
    "statistics, rankings, or selection decisions."
)
_CHECKPOINT_ADVISORY_LABEL = (
    "Advisory checkpoint review. Evidence-backed coaching notes only; unsupported improvement "
    "claims are not confirmed."
)
_UNSAFE_TERMS = (
    "weakest player",
    "poor performer",
    "liability",
    "selection-ready",
    "should be dropped",
    "should be selected",
)


async def get_player_development_report_by_player(
    db: AsyncSession,
    current_user: models.User,
    *,
    player_id: str,
    audience: schemas.PlayerDevelopmentReportAudience,
    include_archived: bool = False,
    plan_id: str | None = None,
) -> schemas.PlayerDevelopmentPlayerReportRead:
    profile = await db.get(models.PlayerProfile, player_id)
    if profile is None:
        raise ValueError("Player profile not found")

    plan = await _resolve_scoped_plan(
        db=db,
        current_user=current_user,
        player_id=player_id,
        plan_id=plan_id,
        include_archived=include_archived,
    )
    if plan is None:
        raise ValueError("Player development plan not found")

    return _build_player_report(
        profile=profile,
        plan=plan,
        audience=audience,
        include_archived=include_archived,
        report_type="player",
    )


async def get_player_development_report_by_plan(
    db: AsyncSession,
    *,
    plan: models.PlayerDevelopmentPlan,
    audience: schemas.PlayerDevelopmentReportAudience,
) -> schemas.PlayerDevelopmentPlayerReportRead:
    profile = await db.get(models.PlayerProfile, plan.player_profile_id)
    if profile is None:
        raise ValueError("Player profile not found")
    return _build_player_report(
        profile=profile,
        plan=plan,
        audience=audience,
        include_archived=plan.status == models.PlayerDevelopmentPlanStatus.archived,
        report_type="plan",
    )


async def get_team_development_summary_report(
    db: AsyncSession,
    current_user: models.User,
    *,
    audience: schemas.PlayerDevelopmentReportAudience,
    include_archived: bool = False,
) -> schemas.PlayerDevelopmentTeamSummaryReportRead:
    overview = await get_team_development_overview(
        db=db,
        current_user=current_user,
        include_archived=include_archived,
    )
    support_needs_language = [
        f"Development support needed: {item.player_name} — "
        f"{_safe_text(item.advisory_note, fallback='Coach review required.')}"
        for item in overview.evidence_coverage_summary.players_needing_more_evidence_details
    ]
    if not support_needs_language and overview.plans_requiring_review > 0:
        support_needs_language.append(
            "Coach review required before draft plans are treated as working plans."
        )

    next_coach_actions: list[str] = []
    if overview.plans_requiring_review > 0:
        next_coach_actions.append(
            f"Coach review required for {overview.plans_requiring_review} draft plan(s)."
        )
    if overview.evidence_coverage_summary.players_needing_more_evidence > 0:
        next_coach_actions.append(
            "Collect additional match, coaching session, or drill evidence where confidence is limited."
        )
    if not overview.upcoming_checkpoints:
        next_coach_actions.append(
            "Schedule planned review checkpoints so progress can be reviewed safely."
        )

    return schemas.PlayerDevelopmentTeamSummaryReportRead(
        report_title="Team Development Summary Report",
        report_scope=schemas.PlayerDevelopmentReportScope(
            report_type="team_summary",
            audience=audience,
            include_archived=include_archived,
            generated_at=dt.datetime.now(dt.UTC),
        ),
        total_assigned_players=overview.total_assigned_players,
        players_with_plans=overview.players_with_draft_plans,
        players_needing_coach_review=overview.plans_requiring_review,
        common_safe_development_themes=overview.common_development_areas,
        drill_overview=overview.drill_assignment_summary,
        upcoming_checkpoints=overview.upcoming_checkpoints,
        evidence_coverage=overview.evidence_coverage_summary,
        support_needs_language=support_needs_language,
        advisory_disclaimer=_ADVISORY_DISCLAIMER,
        next_coach_actions=next_coach_actions,
    )


async def _resolve_scoped_plan(
    db: AsyncSession,
    current_user: models.User,
    *,
    player_id: str,
    plan_id: str | None,
    include_archived: bool,
) -> models.PlayerDevelopmentPlan | None:
    role_value = getattr(current_user.role, "value", current_user.role)
    stmt = (
        select(models.PlayerDevelopmentPlan)
        .where(models.PlayerDevelopmentPlan.player_profile_id == player_id)
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
    if role_value in {"coach_pro", "coach_pro_plus"}:
        stmt = stmt.where(models.PlayerDevelopmentPlan.coach_user_id == current_user.id)
    elif role_value == "org_pro":
        stmt = stmt.where(models.PlayerDevelopmentPlan.org_id == current_user.org_id)
    else:
        return None

    if plan_id:
        stmt = stmt.where(models.PlayerDevelopmentPlan.id == plan_id)
    if not include_archived:
        stmt = stmt.where(
            models.PlayerDevelopmentPlan.status != models.PlayerDevelopmentPlanStatus.archived
        )

    result = await db.execute(stmt)
    return result.scalars().first()


def _build_player_report(
    *,
    profile: models.PlayerProfile,
    plan: models.PlayerDevelopmentPlan,
    audience: schemas.PlayerDevelopmentReportAudience,
    include_archived: bool,
    report_type: str,
) -> schemas.PlayerDevelopmentPlayerReportRead:
    strengths = [
        schemas.PlayerDevelopmentReportStrength(
            category=tag.category,
            label=_safe_text(tag.label, fallback="Evidence-backed coaching strength"),
            confidence_score=tag.confidence_score,
            evidence_refs=tag.evidence_refs,
        )
        for tag in sorted(plan.strength_tags, key=lambda item: item.created_at)
    ]
    safe_development_areas = [
        schemas.PlayerDevelopmentReportDevelopmentArea(
            category=tag.category,
            safe_display_label=_safe_text(
                tag.safe_display_label,
                fallback="Current growth focus",
            ),
            severity=tag.severity,
            confidence_score=tag.confidence_score,
            evidence_refs=tag.evidence_refs,
        )
        for tag in sorted(plan.weakness_tags, key=lambda item: item.created_at)
    ]
    goals = [
        schemas.PlayerDevelopmentReportGoal(
            title=_safe_text(goal.title, fallback="Development goal"),
            description=_safe_text(goal.description, fallback=None),
            target_metric=goal.target_metric,
            due_date=goal.due_date,
            status=goal.status,
            evidence_refs=goal.evidence_refs,
        )
        for goal in sorted(plan.goals, key=lambda item: item.created_at)
    ]
    drills = [
        schemas.PlayerDevelopmentReportDrill(
            drill_category=drill.drill_category,
            drill_name=_safe_text(drill.drill_name, fallback="Assigned development drill"),
            drill_description=_safe_text(drill.drill_description, fallback=None),
            frequency=drill.frequency,
            status=drill.status,
            due_date=drill.due_date,
            evidence_refs=drill.evidence_refs,
        )
        for drill in sorted(plan.drill_assignments, key=lambda item: item.created_at)
    ]
    checkpoint_review_summary = _build_checkpoint_review_summary(plan)
    limitations = _extract_limitations(plan)
    next_coach_actions = _next_coach_actions(
        plan=plan,
        limitations=limitations,
        has_checkpoints=bool(checkpoint_review_summary.checkpoints),
    )
    evidence_refs = _collect_plan_evidence_refs(plan)

    return schemas.PlayerDevelopmentPlayerReportRead(
        report_title=f"{profile.player_name} Development Report",
        player_profile_id=profile.player_id,
        player_name=profile.player_name,
        plan_id=plan.id,
        report_scope=schemas.PlayerDevelopmentReportScope(
            report_type=report_type,
            audience=audience,
            include_archived=include_archived,
            generated_at=dt.datetime.now(dt.UTC),
        ),
        plan_status=plan.status,
        coach_approved=plan.coach_approved,
        approval_state=plan.approval_state,
        confidence_score=plan.confidence_score,
        limitations=limitations,
        strengths=strengths,
        safe_development_areas=safe_development_areas,
        goals=goals,
        drills=drills,
        checkpoint_review_summary=checkpoint_review_summary,
        evidence_refs=evidence_refs,
        advisory_disclaimer=_ADVISORY_DISCLAIMER,
        next_coach_actions=next_coach_actions,
    )


def _build_checkpoint_review_summary(
    plan: models.PlayerDevelopmentPlan,
) -> schemas.PlayerDevelopmentCheckpointReviewSummaryRead:
    checkpoints = [
        _serialize_checkpoint(checkpoint)
        for checkpoint in sorted(plan.progress_checkpoints, key=lambda item: item.checkpoint_date)
    ]
    return schemas.PlayerDevelopmentCheckpointReviewSummaryRead(
        plan_id=plan.id,
        player_profile_id=plan.player_profile_id,
        advisory_label=_CHECKPOINT_ADVISORY_LABEL,
        checkpoints=checkpoints,
    )


def _serialize_checkpoint(
    checkpoint: models.PlayerProgressCheckpoint,
) -> schemas.PlayerDevelopmentReportCheckpoint:
    evidence_refs = checkpoint.evidence_refs
    status = checkpoint.progress_status
    progress_statement = "Evidence-backed coaching note."
    if _contains_improvement_claim(status) and not evidence_refs:
        status = "needs_evidence_review"
        progress_statement = (
            "Planned review checkpoint. More evidence would strengthen this recommendation "
            "before any improvement claim."
        )
    return schemas.PlayerDevelopmentReportCheckpoint(
        checkpoint_date=checkpoint.checkpoint_date,
        progress_status=status,
        progress_statement=progress_statement,
        confidence_score=checkpoint.confidence_score,
        evidence_refs=evidence_refs,
        coach_notes=_safe_text(checkpoint.coach_notes, fallback=None),
    )


def _contains_improvement_claim(value: str) -> bool:
    lowered = value.lower()
    return "improv" in lowered


def _extract_limitations(plan: models.PlayerDevelopmentPlan) -> list[str]:
    raw = plan.ai_metadata.get("limitations")
    if not isinstance(raw, list):
        return []
    limitations = [item.strip() for item in raw if isinstance(item, str) and item.strip()]
    cleaned: list[str] = []
    for item in limitations:
        safe_item = _safe_text(item, fallback="More evidence would strengthen this recommendation.")
        if safe_item is not None:
            cleaned.append(safe_item)
    return cleaned


def _next_coach_actions(
    *,
    plan: models.PlayerDevelopmentPlan,
    limitations: list[str],
    has_checkpoints: bool,
) -> list[str]:
    actions: list[str] = []
    if not plan.coach_approved or plan.approval_state in {
        models.PlayerDevelopmentApprovalState.pending_review,
        models.PlayerDevelopmentApprovalState.changes_requested,
    }:
        actions.append("Coach review required before this draft is treated as a working plan.")
    if limitations or (plan.confidence_score is not None and plan.confidence_score < 0.6):
        actions.append(
            "Collect additional evidence from matches, sessions, or drills to strengthen confidence."
        )
    if not has_checkpoints:
        actions.append("Schedule a planned review checkpoint for measurable progress follow-up.")
    return actions


def _collect_plan_evidence_refs(plan: models.PlayerDevelopmentPlan) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    refs.extend(plan.evidence_refs)
    for goal in plan.goals:
        refs.extend(goal.evidence_refs)
    for tag in plan.weakness_tags:
        refs.extend(tag.evidence_refs)
    for tag in plan.strength_tags:
        refs.extend(tag.evidence_refs)
    for drill in plan.drill_assignments:
        refs.extend(drill.evidence_refs)
    for checkpoint in plan.progress_checkpoints:
        refs.extend(checkpoint.evidence_refs)

    seen: set[tuple[str, str]] = set()
    deduped: list[dict[str, Any]] = []
    for ref in refs:
        ref_type = str(ref.get("type", "evidence"))
        ref_id = str(ref.get("id", ref.get("label", "unknown")))
        key = (ref_type, ref_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(
            {
                "type": ref_type,
                "id": ref_id,
                "label": str(ref.get("label", ref_id)),
            }
        )
    return deduped


def _safe_text(value: str | None, *, fallback: str | None) -> str | None:
    if value is None:
        return fallback
    cleaned = value.strip()
    if not cleaned:
        return fallback
    lowered = cleaned.lower()
    if any(term in lowered for term in _UNSAFE_TERMS):
        return fallback
    return cleaned
