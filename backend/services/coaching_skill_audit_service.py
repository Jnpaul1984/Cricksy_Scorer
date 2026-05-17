from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.player_development_skill_contract import PLAYER_DEVELOPMENT_SKILL_REGISTRY
from backend.sql_app import models, schemas

_REVIEW_EVENT_TYPES: dict[schemas.PlayerDevelopmentPlanReviewDecision, str] = {
    schemas.PlayerDevelopmentPlanReviewDecision.approved: "review_approved",
    schemas.PlayerDevelopmentPlanReviewDecision.rejected: "review_rejected",
    schemas.PlayerDevelopmentPlanReviewDecision.changes_requested: "review_changes_requested",
}
_UNSAFE_KEY_FRAGMENTS = frozenset(
    {
        "api_key",
        "frame",
        "frames",
        "medical",
        "password",
        "pose_keypoints",
        "private",
        "prompt",
        "psychological",
        "raw",
        "secret",
        "token",
    }
)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _find_unsafe_key_names(value: Any) -> set[str]:
    found: set[str] = set()
    stack = [value]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, nested in current.items():
                normalized = str(key).strip().lower()
                if any(fragment in normalized for fragment in _UNSAFE_KEY_FRAGMENTS):
                    found.add(normalized)
                stack.append(nested)
        elif isinstance(current, list):
            stack.extend(current)
    return found


def _sorted_unique(values: Iterable[str | None]) -> list[str]:
    return sorted({value for value in values if value})


def _extract_video_identifiers(
    plan: models.PlayerDevelopmentPlan,
) -> tuple[str | None, str | None]:
    ai_metadata = _as_dict(plan.ai_metadata)
    evidence_refs = _as_dict_list(plan.evidence_refs)

    video_session_id = _coerce_text(ai_metadata.get("video_session_id"))
    video_analysis_job_id = _coerce_text(ai_metadata.get("video_analysis_job_id"))

    for ref in evidence_refs:
        ref_type = _coerce_text(ref.get("type"))
        ref_id = _coerce_text(ref.get("id"))
        if ref_type == "video_session" and video_session_id is None:
            video_session_id = ref_id
        if ref_type == "video_analysis_job" and video_analysis_job_id is None:
            video_analysis_job_id = ref_id

    return video_session_id, video_analysis_job_id


def _resolve_skill_metadata(plan: models.PlayerDevelopmentPlan) -> tuple[str, str]:
    ai_metadata = _as_dict(plan.ai_metadata)
    skill_id = _coerce_text(ai_metadata.get("skill_id")) or _coerce_text(
        ai_metadata.get("skill_contract_id")
    )
    skill_version = _coerce_text(ai_metadata.get("skill_version"))

    video_session_id, video_analysis_job_id = _extract_video_identifiers(plan)
    if skill_id is None and (video_session_id or video_analysis_job_id):
        skill_id = "coaching_video_evidence_skill.v1"

    if skill_id is None and plan.source_type == models.PlayerDevelopmentSourceType.ai_insight:
        skill_id = "player_development_plan.v1"

    registry_entry = PLAYER_DEVELOPMENT_SKILL_REGISTRY.get(skill_id or "")
    if skill_id is None:
        skill_id = "unknown"
    if skill_version is None:
        skill_version = _coerce_text((registry_entry or {}).get("version")) or "unknown"

    return skill_id, skill_version


def _build_input_summary(
    plan: models.PlayerDevelopmentPlan,
    *,
    reviewer_notes: str | None,
) -> dict[str, Any]:
    ai_metadata = _as_dict(plan.ai_metadata)
    evidence_refs = _as_dict_list(plan.evidence_refs)
    source_refs = _as_dict_list(ai_metadata.get("source_refs"))
    unsafe_fields_removed = _sorted_unique(_find_unsafe_key_names([ai_metadata, evidence_refs]))

    return {
        "source_type": getattr(plan.source_type, "value", str(plan.source_type)),
        "evidence_ref_count": len(evidence_refs),
        "evidence_types": _sorted_unique(_coerce_text(ref.get("type")) for ref in evidence_refs),
        "requires_review": bool(ai_metadata.get("requires_review")),
        "grounded_in_data": bool(ai_metadata.get("grounded_in_data")),
        "confidence_score": plan.confidence_score,
        "limitations_count": len(ai_metadata.get("limitations", []))
        if isinstance(ai_metadata.get("limitations"), list)
        else 0,
        "source_ref_count": len(source_refs),
        "reviewer_notes_present": bool(_coerce_text(reviewer_notes)),
        "unsafe_fields_removed": unsafe_fields_removed,
    }


def _build_output_summary(plan: models.PlayerDevelopmentPlan) -> dict[str, Any]:
    return {
        "plan_status": getattr(plan.status, "value", str(plan.status)),
        "approval_state_after": getattr(plan.approval_state, "value", str(plan.approval_state)),
        "coach_approved_after": plan.coach_approved,
    }


async def write_player_development_review_audit_event(
    *,
    db: AsyncSession,
    plan: models.PlayerDevelopmentPlan,
    decision: schemas.PlayerDevelopmentPlanReviewDecision,
    reviewer: models.User,
    reviewer_notes: str | None = None,
) -> models.CoachingSkillAuditLog:
    """Persist a safe review audit event for governed coaching-skill workflows."""

    skill_id, skill_version = _resolve_skill_metadata(plan)
    video_session_id, video_analysis_job_id = _extract_video_identifiers(plan)

    audit_event = models.CoachingSkillAuditLog(
        event_type=_REVIEW_EVENT_TYPES[decision],
        skill_id=skill_id,
        skill_version=skill_version,
        triggered_by_user_id=reviewer.id,
        reviewed_by_user_id=reviewer.id,
        player_profile_id=plan.player_profile_id,
        plan_id=plan.id,
        video_session_id=video_session_id,
        video_analysis_job_id=video_analysis_job_id,
        approval_decision=decision.value,
        approval_state_after=getattr(plan.approval_state, "value", str(plan.approval_state)),
        coach_approved_after=plan.coach_approved,
        organization_id=plan.org_id or reviewer.org_id,
        input_summary=_build_input_summary(plan, reviewer_notes=reviewer_notes),
        output_summary=_build_output_summary(plan),
    )
    db.add(audit_event)
    await db.flush()
    return audit_event
