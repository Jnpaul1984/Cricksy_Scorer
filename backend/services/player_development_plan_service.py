from __future__ import annotations

import datetime as dt
import re
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.domain.ai_boundary import (
    AiOutputMetadata,
    AiOutputType,
    AiSourceReference,
    validate_no_official_truth_mutation,
)
from backend.services.ai_player_insights import build_player_ai_insights
from backend.services.player_improvement_tracker import ImprovementMetrics, MonthlyStats
from backend.services.player_improvement_tracker import PlayerImprovementTracker
from backend.services.training_drill_generator import TrainingDrillGenerator
from backend.sql_app import models

UTC = getattr(dt, "UTC", dt.UTC)

_GENERIC_AI_STRENGTHS = {
    "Solid foundation to build on with more game time.",
}
_GENERIC_AI_WEAKNESSES = {
    "No major weaknesses detected from available data.",
}
_NEGATIVE_TERMS = ("liability", "weak link", "hopeless", "poor player", "problem player")


@dataclass(slots=True)
class DraftPlanGenerationResult:
    status: str
    player_profile_id: str
    plan_id: str | None
    limitations: list[str]
    evidence_refs: list[dict[str, Any]]
    confidence_score: float | None


async def generate_draft_player_development_plan(
    db: AsyncSession,
    player_profile_id: str,
    coach_user: models.User,
    additional_evidence_refs: list[dict[str, Any]] | None = None,
) -> DraftPlanGenerationResult:
    profile = await _load_player_profile(db, player_profile_id)
    video_sessions = await _load_video_sessions(db, player_profile_id, coach_user)
    evidence_refs = _dedupe_refs(
        [
            *_base_profile_refs(profile),
            *_form_refs(profile.form_entries),
            *_coaching_note_refs(profile.coaching_notes),
            *_coaching_session_refs(profile.coaching_sessions),
            *_video_session_refs(video_sessions),
            *(additional_evidence_refs or []),
        ]
    )

    if not _has_sufficient_evidence(profile, video_sessions):
        limitations = [
            "Insufficient player-development evidence is available to draft a reliable plan.",
            "Add tracked form, coaching notes, sessions, or Coach Pro Plus video evidence before generating recommendations.",
        ]
        return DraftPlanGenerationResult(
            status="insufficient_data",
            player_profile_id=player_profile_id,
            plan_id=None,
            limitations=limitations,
            evidence_refs=evidence_refs,
            confidence_score=0.0,
        )

    insights = await build_player_ai_insights(db, player_profile_id)
    filtered_strengths = _filter_ai_items(insights.strengths, _GENERIC_AI_STRENGTHS)
    filtered_weaknesses = _filter_ai_items(insights.weaknesses, _GENERIC_AI_WEAKNESSES)
    advisory_payload = {
        "summary": insights.summary,
        "strengths": filtered_strengths,
        "development_areas": filtered_weaknesses,
        "recommendations": insights.recommendations,
        "limitations": [],
        "confidence_score": None,
    }
    validate_no_official_truth_mutation(advisory_payload, "player_development_plan_service")

    monthly_stats = _build_monthly_stats(profile.form_entries)
    improvement_metrics = _build_improvement_metrics(monthly_stats)
    limitations = _build_limitations(profile, monthly_stats, video_sessions)
    confidence_score = _calculate_confidence(profile, monthly_stats, video_sessions)
    ai_metadata = _build_ai_metadata(
        confidence_score=confidence_score,
        limitations=limitations,
        evidence_refs=evidence_refs,
        player_name=profile.player_name,
    )

    plan = models.PlayerDevelopmentPlan(
        id=str(uuid.uuid4()),
        player_profile_id=profile.player_id,
        coach_user_id=coach_user.id,
        org_id=coach_user.org_id or "unscoped-org",
        title=f"{profile.player_name} draft development plan",
        summary=_build_plan_summary(profile.player_name, filtered_strengths, filtered_weaknesses),
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        confidence_score=confidence_score,
        evidence_refs=evidence_refs,
        ai_metadata=ai_metadata,
    )

    strength_tags = _build_strength_tags(
        profile=profile,
        plan=plan,
        strengths=filtered_strengths,
        confidence_score=confidence_score,
        evidence_refs=evidence_refs,
        ai_metadata=ai_metadata,
    )
    weakness_tags = _build_weakness_tags(
        profile=profile,
        plan=plan,
        weaknesses=filtered_weaknesses,
        confidence_score=confidence_score,
        evidence_refs=evidence_refs,
        ai_metadata=ai_metadata,
    )
    goals = _build_goals(plan, improvement_metrics, profile.form_entries)
    drill_assignments = _build_drill_assignments(
        profile=profile,
        plan=plan,
        coach_user=coach_user,
        weakness_tags=weakness_tags,
        evidence_refs=evidence_refs,
    )
    progress_checkpoints = _build_progress_checkpoints(
        profile=profile,
        plan=plan,
        coach_user=coach_user,
        improvement_metrics=improvement_metrics,
        evidence_refs=evidence_refs,
        ai_metadata=ai_metadata,
    )

    plan.strength_tags.extend(strength_tags)
    plan.weakness_tags.extend(weakness_tags)
    plan.goals.extend(goals)
    plan.drill_assignments.extend(drill_assignments)
    plan.progress_checkpoints.extend(progress_checkpoints)

    db.add(plan)
    await db.commit()

    return DraftPlanGenerationResult(
        status="draft_created",
        player_profile_id=player_profile_id,
        plan_id=plan.id,
        limitations=limitations,
        evidence_refs=evidence_refs,
        confidence_score=confidence_score,
    )


async def get_draft_plan_by_id(
    db: AsyncSession,
    plan_id: str,
) -> models.PlayerDevelopmentPlan | None:
    result = await db.execute(
        select(models.PlayerDevelopmentPlan)
        .where(models.PlayerDevelopmentPlan.id == plan_id)
        .options(
            selectinload(models.PlayerDevelopmentPlan.goals),
            selectinload(models.PlayerDevelopmentPlan.weakness_tags),
            selectinload(models.PlayerDevelopmentPlan.strength_tags),
            selectinload(models.PlayerDevelopmentPlan.drill_assignments),
            selectinload(models.PlayerDevelopmentPlan.progress_checkpoints),
        )
    )
    return result.scalar_one_or_none()


async def list_player_draft_plans(
    db: AsyncSession,
    player_profile_id: str,
    coach_user_id: str | None = None,
    org_id: str | None = None,
) -> list[models.PlayerDevelopmentPlan]:
    filters = [models.PlayerDevelopmentPlan.player_profile_id == player_profile_id]
    if coach_user_id is not None:
        filters.append(models.PlayerDevelopmentPlan.coach_user_id == coach_user_id)
    if org_id is not None:
        filters.append(models.PlayerDevelopmentPlan.org_id == org_id)

    result = await db.execute(
        select(models.PlayerDevelopmentPlan)
        .where(*filters)
        .order_by(models.PlayerDevelopmentPlan.created_at.desc())
        .options(
            selectinload(models.PlayerDevelopmentPlan.goals),
            selectinload(models.PlayerDevelopmentPlan.weakness_tags),
            selectinload(models.PlayerDevelopmentPlan.strength_tags),
            selectinload(models.PlayerDevelopmentPlan.drill_assignments),
            selectinload(models.PlayerDevelopmentPlan.progress_checkpoints),
        )
    )
    return list(result.scalars().all())


async def _load_player_profile(
    db: AsyncSession,
    player_profile_id: str,
) -> models.PlayerProfile:
    result = await db.execute(
        select(models.PlayerProfile)
        .where(models.PlayerProfile.player_id == player_profile_id)
        .options(
            selectinload(models.PlayerProfile.form_entries),
            selectinload(models.PlayerProfile.coaching_notes),
            selectinload(models.PlayerProfile.coaching_sessions),
        )
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise ValueError(f"Player profile {player_profile_id} not found")
    return profile


async def _load_video_sessions(
    db: AsyncSession,
    player_profile_id: str,
    coach_user: models.User,
) -> list[models.VideoSession]:
    owner_filters = [
        and_(
            models.VideoSession.owner_type == models.OwnerTypeEnum.coach,
            models.VideoSession.owner_id == coach_user.id,
        )
    ]
    if coach_user.org_id:
        owner_filters.append(
            and_(
                models.VideoSession.owner_type == models.OwnerTypeEnum.org,
                models.VideoSession.owner_id == coach_user.org_id,
            )
        )

    result = await db.execute(
        select(models.VideoSession)
        .where(or_(*owner_filters))
        .order_by(models.VideoSession.created_at.desc())
    )
    sessions = list(result.scalars().all())
    return [session for session in sessions if player_profile_id in session.player_ids]


def _has_sufficient_evidence(
    profile: models.PlayerProfile,
    video_sessions: list[models.VideoSession],
) -> bool:
    return any(
        (
            profile.total_matches > 0,
            profile.total_innings_batted > 0,
            profile.total_innings_bowled > 0,
            bool(profile.form_entries),
            bool(profile.coaching_notes),
            bool(profile.coaching_sessions),
            bool(video_sessions),
        )
    )


def _build_limitations(
    profile: models.PlayerProfile,
    monthly_stats: list[MonthlyStats],
    video_sessions: list[models.VideoSession],
) -> list[str]:
    limitations: list[str] = []
    if len(monthly_stats) < 2:
        limitations.append(
            "Limited month-over-month form data is available for measurable progress goals."
        )
    if not profile.coaching_notes:
        limitations.append("No coach notes were found, so coach-observed evidence is limited.")
    if not video_sessions:
        limitations.append("No Coach Pro Plus video references were available for this draft.")
    return limitations


def _calculate_confidence(
    profile: models.PlayerProfile,
    monthly_stats: list[MonthlyStats],
    video_sessions: list[models.VideoSession],
) -> float:
    confidence = 0.35
    if profile.total_matches > 0:
        confidence += 0.15
    if profile.coaching_notes:
        confidence += 0.15
    if profile.coaching_sessions:
        confidence += 0.1
    if monthly_stats:
        confidence += 0.15
    if len(monthly_stats) >= 2:
        confidence += 0.05
    if video_sessions:
        confidence += 0.05
    return round(min(1.0, confidence), 2)


def _build_ai_metadata(
    *,
    confidence_score: float,
    limitations: list[str],
    evidence_refs: list[dict[str, Any]],
    player_name: str,
) -> dict[str, Any]:
    source_refs = [
        AiSourceReference(
            type=str(ref.get("type", "evidence")),
            id=str(_ref_identifier(ref)),
            label=str(ref.get("label", ref.get("type", "evidence"))),
        )
        for ref in evidence_refs
        if _ref_identifier(ref)
    ]
    metadata = AiOutputMetadata(
        output_type=AiOutputType.DRAFT,
        is_official_truth=False,
        requires_review=True,
        grounded_in_data=True,
        confidence_score=confidence_score,
        limitations=limitations,
        source_refs=source_refs,
        grounding_summary=f"Draft development plan assembled from stored player evidence for {player_name}.",
    )
    return metadata.model_dump(mode="json")


def _build_plan_summary(
    player_name: str,
    strengths: list[str],
    weaknesses: list[str],
) -> str:
    build_on = strengths[0] if strengths else "existing strengths"
    focus_area = (
        _safe_development_phrase(weaknesses[0]) if weaknesses else "current coaching priorities"
    )
    return (
        f"Draft plan for {player_name} built from recorded player evidence. "
        f"Build on {build_on.lower()} while focusing on {focus_area.lower()}."
    )


def _build_strength_tags(
    *,
    profile: models.PlayerProfile,
    plan: models.PlayerDevelopmentPlan,
    strengths: list[str],
    confidence_score: float,
    evidence_refs: list[dict[str, Any]],
    ai_metadata: dict[str, Any],
) -> list[models.PlayerStrengthTag]:
    tags: list[models.PlayerStrengthTag] = []
    for strength in strengths[:3]:
        tags.append(
            models.PlayerStrengthTag(
                plan_id=plan.id,
                player_profile_id=profile.player_id,
                category=_strength_category(strength),
                label=strength,
                confidence_score=confidence_score,
                source_type=models.PlayerDevelopmentSourceType.ai_insight,
                evidence_refs=evidence_refs,
                ai_metadata=ai_metadata,
            )
        )
    for note in profile.coaching_notes[:2]:
        for item in _split_text_items(note.strengths)[:1]:
            tags.append(
                models.PlayerStrengthTag(
                    plan_id=plan.id,
                    player_profile_id=profile.player_id,
                    category=_strength_category(item),
                    label=item,
                    confidence_score=None,
                    source_type=models.PlayerDevelopmentSourceType.coach_note,
                    evidence_refs=_dedupe_refs(
                        [{"type": "coach_note", "id": note.id, "label": "Coach note evidence"}]
                    ),
                    ai_metadata={},
                )
            )
    return _dedupe_strength_tags(tags)


def _build_weakness_tags(
    *,
    profile: models.PlayerProfile,
    plan: models.PlayerDevelopmentPlan,
    weaknesses: list[str],
    confidence_score: float,
    evidence_refs: list[dict[str, Any]],
    ai_metadata: dict[str, Any],
) -> list[models.PlayerWeaknessTag]:
    tags: list[models.PlayerWeaknessTag] = []
    for weakness in weaknesses[:4]:
        category, label, safe_display_label, severity = _classify_development_area(weakness)
        tags.append(
            models.PlayerWeaknessTag(
                plan_id=plan.id,
                player_profile_id=profile.player_id,
                category=category,
                label=label,
                safe_display_label=safe_display_label,
                severity=severity,
                confidence_score=confidence_score,
                source_type=models.PlayerDevelopmentSourceType.ai_insight,
                evidence_refs=evidence_refs,
                ai_metadata=ai_metadata,
            )
        )
    for note in profile.coaching_notes[:2]:
        for item in _split_text_items(note.weaknesses)[:2]:
            category, label, safe_display_label, severity = _classify_development_area(item)
            tags.append(
                models.PlayerWeaknessTag(
                    plan_id=plan.id,
                    player_profile_id=profile.player_id,
                    category=category,
                    label=label,
                    safe_display_label=safe_display_label,
                    severity=severity,
                    confidence_score=None,
                    source_type=models.PlayerDevelopmentSourceType.coach_note,
                    evidence_refs=_dedupe_refs(
                        [{"type": "coach_note", "id": note.id, "label": "Coach note evidence"}]
                    ),
                    ai_metadata={},
                )
            )
    return _dedupe_weakness_tags(tags)


def _build_goals(
    plan: models.PlayerDevelopmentPlan,
    improvement_metrics: dict[str, ImprovementMetrics],
    form_entries: list[models.PlayerForm],
) -> list[models.PlayerDevelopmentGoal]:
    if len(form_entries) < 2:
        return []

    due_date = max(form.period_end for form in form_entries) + dt.timedelta(days=30)
    evidence_refs = _dedupe_refs(_form_refs(form_entries[-2:]))
    goals: list[models.PlayerDevelopmentGoal] = []
    for metric_name in ("strike_rate", "batting_average", "consistency", "dismissal_rate"):
        metric = improvement_metrics.get(metric_name)
        if metric is None:
            continue
        goal = _goal_from_metric(plan.id, metric_name, metric, due_date, evidence_refs)
        if goal is not None:
            goals.append(goal)
        if len(goals) >= 2:
            break
    return goals


def _goal_from_metric(
    plan_id: str,
    metric_name: str,
    metric: ImprovementMetrics,
    due_date: dt.date,
    evidence_refs: list[dict[str, Any]],
) -> models.PlayerDevelopmentGoal | None:
    if metric_name == "strike_rate" and (metric.trend == "declining" or metric.current_value < 110):
        target_value = round(max(metric.previous_value, metric.current_value * 1.08), 2)
        if target_value <= metric.current_value:
            return None
        return models.PlayerDevelopmentGoal(
            plan_id=plan_id,
            title="Improve strike rotation",
            description="Use tracked form evidence to lift strike rate without forcing unsupported outcomes.",
            target_metric=metric_name,
            baseline_value=metric.previous_value,
            current_value=metric.current_value,
            target_value=target_value,
            unit="runs per 100 balls",
            due_date=due_date,
            evidence_refs=evidence_refs,
        )
    if metric_name == "batting_average" and (
        metric.trend == "declining" or metric.current_value < 30
    ):
        target_value = round(max(metric.previous_value, metric.current_value + 3), 2)
        if target_value <= metric.current_value:
            return None
        return models.PlayerDevelopmentGoal(
            plan_id=plan_id,
            title="Build longer batting stays",
            description="Track whether improved decision-making produces more durable innings.",
            target_metric=metric_name,
            baseline_value=metric.previous_value,
            current_value=metric.current_value,
            target_value=target_value,
            unit="runs per dismissal",
            due_date=due_date,
            evidence_refs=evidence_refs,
        )
    if metric_name == "consistency" and (metric.trend == "declining" or metric.current_value < 60):
        target_value = round(max(metric.previous_value, metric.current_value + 5), 2)
        if target_value <= metric.current_value:
            return None
        return models.PlayerDevelopmentGoal(
            plan_id=plan_id,
            title="Improve consistency across innings",
            description="Use repeated form tracking to confirm whether performance variance is reducing.",
            target_metric=metric_name,
            baseline_value=metric.previous_value,
            current_value=metric.current_value,
            target_value=target_value,
            unit="consistency score",
            due_date=due_date,
            evidence_refs=evidence_refs,
        )
    if (
        metric_name == "dismissal_rate"
        and metric.current_value > 0
        and (metric.trend == "declining" or metric.current_value > metric.previous_value)
    ):
        target_value = round(
            min(metric.previous_value or metric.current_value, metric.current_value * 0.9), 2
        )
        if target_value >= metric.current_value:
            return None
        return models.PlayerDevelopmentGoal(
            plan_id=plan_id,
            title="Reduce dismissal frequency",
            description="Review tracked innings evidence before claiming improvement in staying power.",
            target_metric=metric_name,
            baseline_value=metric.previous_value,
            current_value=metric.current_value,
            target_value=target_value,
            unit="dismissals per innings",
            due_date=due_date,
            evidence_refs=evidence_refs,
        )
    return None


def _build_drill_assignments(
    *,
    profile: models.PlayerProfile,
    plan: models.PlayerDevelopmentPlan,
    coach_user: models.User,
    weakness_tags: list[models.PlayerWeaknessTag],
    evidence_refs: list[dict[str, Any]],
) -> list[models.PlayerDrillAssignment]:
    weakness_scores = _weakness_scores_from_tags(weakness_tags)
    if max(weakness_scores.values(), default=0) < 50:
        return []

    drill_plan = TrainingDrillGenerator.generate_drills_for_player(
        player_id=profile.player_id,
        player_name=profile.player_name,
        player_profile={
            "player_id": profile.player_id,
            "player_name": profile.player_name,
            **weakness_scores,
        },
        recent_dismissals=[],
    )
    due_date = dt.date.today() + dt.timedelta(days=21)
    assignments: list[models.PlayerDrillAssignment] = []
    for drill in drill_plan.drills[:3]:
        assignments.append(
            models.PlayerDrillAssignment(
                plan_id=plan.id,
                player_profile_id=profile.player_id,
                coach_user_id=coach_user.id,
                drill_category=drill.category.value,
                drill_name=drill.name,
                drill_description=drill.description,
                frequency=drill.recommended_frequency,
                status=models.PlayerDevelopmentPlanStatus.draft,
                due_date=due_date,
                evidence_refs=evidence_refs,
            )
        )
    return assignments


def _build_progress_checkpoints(
    *,
    profile: models.PlayerProfile,
    plan: models.PlayerDevelopmentPlan,
    coach_user: models.User,
    improvement_metrics: dict[str, ImprovementMetrics],
    evidence_refs: list[dict[str, Any]],
    ai_metadata: dict[str, Any],
) -> list[models.PlayerProgressCheckpoint]:
    checkpoint_date: dt.date | None = None
    if profile.form_entries:
        checkpoint_date = max(form.period_end for form in profile.form_entries) + dt.timedelta(
            days=30
        )
    elif profile.coaching_sessions:
        checkpoint_date = max(session.scheduled_at for session in profile.coaching_sessions).date()

    if checkpoint_date is None or not evidence_refs:
        return []

    tracked_metrics = [metric.metric_name for metric in improvement_metrics.values()][:2]
    metrics_phrase = (
        ", ".join(tracked_metrics) if tracked_metrics else "tracked development evidence"
    )
    checkpoint = models.PlayerProgressCheckpoint(
        plan_id=plan.id,
        player_profile_id=profile.player_id,
        coach_user_id=coach_user.id,
        checkpoint_date=checkpoint_date,
        summary=f"Planned review checkpoint for {metrics_phrase}; coach confirmation is still required before any progress claim.",
        progress_status="planned_review",
        confidence_score=plan.confidence_score,
        evidence_refs=evidence_refs,
        ai_metadata=ai_metadata,
        coach_notes="Checkpoint is advisory only until a coach records evidence-backed outcomes.",
    )
    return [checkpoint]


def _build_monthly_stats(form_entries: list[models.PlayerForm]) -> list[MonthlyStats]:
    monthly_stats: list[MonthlyStats] = []
    for entry in sorted(form_entries, key=lambda item: item.period_end):
        deliveries = 0
        if entry.strike_rate and entry.runs > 0:
            deliveries = max(1, round((entry.runs * 100) / entry.strike_rate))
        dismissals = 0
        if entry.batting_average and entry.runs > 0:
            dismissals = max(1, round(entry.runs / entry.batting_average))
        monthly_stats.append(
            MonthlyStats(
                month=entry.period_end.strftime("%Y-%m"),
                total_runs=entry.runs,
                total_deliveries=deliveries,
                matches_played=entry.matches_played,
                innings_played=max(1, entry.matches_played)
                if entry.runs > 0
                else entry.matches_played,
                dismissals=dismissals,
                boundaries_4=0,
                boundaries_6=0,
                batting_average=entry.batting_average or 0.0,
                strike_rate=entry.strike_rate or 0.0,
                consistency_score=entry.form_score or 50.0,
                role="player",
            )
        )
    return monthly_stats


def _build_improvement_metrics(monthly_stats: list[MonthlyStats]) -> dict[str, ImprovementMetrics]:
    if len(monthly_stats) < 2:
        return {}
    return PlayerImprovementTracker.calculate_improvement_metrics(
        monthly_stats[-2], monthly_stats[-1]
    )


def _base_profile_refs(profile: models.PlayerProfile) -> list[dict[str, Any]]:
    return [
        {
            "type": "player_profile",
            "id": profile.player_id,
            "label": f"Player profile for {profile.player_name}",
        }
    ]


def _form_refs(form_entries: list[models.PlayerForm]) -> list[dict[str, Any]]:
    return [
        {
            "type": "player_form",
            "id": entry.id,
            "label": f"Form period ending {entry.period_end.isoformat()}",
        }
        for entry in form_entries[-3:]
    ]


def _coaching_note_refs(notes: list[models.PlayerCoachingNotes]) -> list[dict[str, Any]]:
    return [
        {
            "type": "coach_note",
            "id": note.id,
            "label": f"Coach note from {note.created_at.date().isoformat()}",
        }
        for note in notes[:3]
    ]


def _coaching_session_refs(sessions: list[models.CoachingSession]) -> list[dict[str, Any]]:
    return [
        {
            "type": "coaching_session",
            "id": session.id,
            "label": f"Coaching session: {session.focus_area}",
        }
        for session in sessions[:3]
    ]


def _video_session_refs(sessions: list[models.VideoSession]) -> list[dict[str, Any]]:
    return [
        {
            "type": "video_session",
            "id": session.id,
            "label": session.title,
        }
        for session in sessions[:2]
    ]


def _dedupe_refs(refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for ref in refs:
        ref_type = str(ref.get("type", "evidence"))
        ref_id = str(_ref_identifier(ref))
        label = str(ref.get("label", ref_type))
        key = (ref_type, ref_id, label)
        if key in seen:
            continue
        seen.add(key)
        normalized = dict(ref)
        normalized.setdefault("type", ref_type)
        normalized.setdefault("label", label)
        if ref_id:
            normalized.setdefault("id", ref_id)
        deduped.append(normalized)
    return deduped


def _ref_identifier(ref: dict[str, Any]) -> str:
    for key in ("id", "player_id", "match_id", "report_id", "session_id", "note_id", "metric"):
        value = ref.get(key)
        if value:
            return str(value)
    return ""


def _filter_ai_items(items: list[str], generic_items: set[str]) -> list[str]:
    return [item for item in items if item and item not in generic_items]


def _split_text_items(value: str) -> list[str]:
    parts = [part.strip(" .") for part in re.split(r"[;\n]+", value) if part.strip(" .")]
    return parts or [value.strip()]


def _classify_development_area(
    text: str,
) -> tuple[str, str, str, models.PlayerDevelopmentSeverity]:
    lowered = text.lower()
    if "strike rate" in lowered or "rotate strike" in lowered or "dot ball" in lowered:
        return (
            "shot_rotation",
            "Improve strike rotation during quieter phases.",
            "Strike rotation growth focus",
            models.PlayerDevelopmentSeverity.medium,
        )
    if "convert" in lowered or "start" in lowered:
        return (
            "innings_conversion",
            "Turn positive starts into longer innings more often.",
            "Starts conversion current focus area",
            models.PlayerDevelopmentSeverity.medium,
        )
    if "economy" in lowered or "expensive" in lowered:
        return (
            "bowling_control",
            "Tighten bowling control to reduce release pressure.",
            "Bowling control next coaching target",
            models.PlayerDevelopmentSeverity.high,
        )
    if "short" in lowered or "back-foot" in lowered or "pace" in lowered:
        return (
            "pace_handling",
            "Refine setup and options against pace and shorter lengths.",
            "Pace handling development area",
            models.PlayerDevelopmentSeverity.high,
        )
    if "spin" in lowered:
        return (
            "spin_handling",
            "Improve reading and response options against spin.",
            "Spin handling growth focus",
            models.PlayerDevelopmentSeverity.medium,
        )
    if "duck" in lowered or "low score" in lowered or "form" in lowered:
        return (
            "early_innings_stability",
            "Build a steadier early-innings routine under pressure.",
            "Early innings stability current focus area",
            models.PlayerDevelopmentSeverity.medium,
        )
    return (
        "general_development",
        "Continue targeted work on this recorded development area.",
        "Current coaching target",
        models.PlayerDevelopmentSeverity.medium,
    )


def _safe_development_phrase(text: str) -> str:
    _category, _label, safe_label, _severity = _classify_development_area(text)
    return safe_label


def _strength_category(text: str) -> str:
    lowered = text.lower()
    if "bowler" in lowered or "wicket" in lowered or "econom" in lowered:
        return "bowling"
    if "fielder" in lowered or "catch" in lowered or "run-out" in lowered:
        return "fielding"
    if "form" in lowered or "momentum" in lowered:
        return "recent_form"
    return "batting"


def _dedupe_strength_tags(
    tags: list[models.PlayerStrengthTag],
) -> list[models.PlayerStrengthTag]:
    deduped: list[models.PlayerStrengthTag] = []
    seen: set[tuple[str, str]] = set()
    for tag in tags:
        key = (tag.category, tag.label)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(tag)
    return deduped[:4]


def _dedupe_weakness_tags(
    tags: list[models.PlayerWeaknessTag],
) -> list[models.PlayerWeaknessTag]:
    deduped: list[models.PlayerWeaknessTag] = []
    seen: set[tuple[str, str]] = set()
    for tag in tags:
        key = (tag.category, tag.safe_display_label)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(tag)
    return deduped[:4]


def _weakness_scores_from_tags(
    tags: list[models.PlayerWeaknessTag],
) -> dict[str, float]:
    scores = {
        "pace_weakness": 0.0,
        "spin_weakness": 0.0,
        "dot_ball_weakness": 0.0,
        "yorker_weakness": 0.0,
        "aggressive_weakness": 0.0,
        "boundary_weakness": 0.0,
    }
    for tag in tags:
        if tag.category == "pace_handling":
            scores["pace_weakness"] = max(scores["pace_weakness"], 70.0)
        elif tag.category == "spin_handling":
            scores["spin_weakness"] = max(scores["spin_weakness"], 68.0)
        elif tag.category in {"shot_rotation", "early_innings_stability"}:
            scores["dot_ball_weakness"] = max(scores["dot_ball_weakness"], 65.0)
        elif tag.category == "innings_conversion":
            scores["aggressive_weakness"] = max(scores["aggressive_weakness"], 55.0)
            scores["boundary_weakness"] = max(scores["boundary_weakness"], 55.0)
        elif tag.category == "bowling_control":
            scores["yorker_weakness"] = max(scores["yorker_weakness"], 60.0)
    return scores


__all__ = [
    "DraftPlanGenerationResult",
    "generate_draft_player_development_plan",
    "get_draft_plan_by_id",
    "list_player_draft_plans",
]
