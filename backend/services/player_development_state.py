from __future__ import annotations

from typing import Any

ACTIVE_STATUS = "active"
AI_SOURCE_TYPE = "ai_insight"
APPROVAL_CHANGES_REQUESTED = "changes_requested"
APPROVAL_NOT_REQUIRED = "not_required"
APPROVAL_PENDING_REVIEW = "pending_review"
APPROVAL_REJECTED = "rejected"
DRAFT_STATUS = "draft"


def _enum_value(value: Any) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))


def validate_player_development_plan_governance(
    status: Any,
    coach_approved: bool | None,
    approval_state: Any | None = None,
) -> None:
    normalized_status = _enum_value(status)
    normalized_approval_state = _enum_value(approval_state)

    if normalized_status == ACTIVE_STATUS and not coach_approved:
        raise ValueError("Active player development plans require coach approval.")

    if normalized_status == ACTIVE_STATUS and normalized_approval_state in {
        APPROVAL_PENDING_REVIEW,
        APPROVAL_REJECTED,
        APPROVAL_CHANGES_REQUESTED,
    }:
        raise ValueError(
            "Active player development plans cannot remain pending or blocked for review."
        )


def normalize_player_development_plan_governance(
    source_type: Any,
    status: Any | None = None,
    coach_approved: bool | None = None,
    approval_state: Any | None = None,
) -> tuple[str, bool, str]:
    normalized_source_type = _enum_value(source_type) or "manual"
    normalized_status = _enum_value(status) or DRAFT_STATUS
    normalized_coach_approved = False if coach_approved is None else coach_approved
    normalized_approval_state = _enum_value(approval_state)

    if normalized_source_type == AI_SOURCE_TYPE:
        if status is None:
            normalized_status = DRAFT_STATUS
        if coach_approved is None:
            normalized_coach_approved = False
        if approval_state is None:
            normalized_approval_state = APPROVAL_PENDING_REVIEW

    if normalized_approval_state is None:
        normalized_approval_state = (
            APPROVAL_PENDING_REVIEW
            if normalized_source_type == AI_SOURCE_TYPE
            else APPROVAL_NOT_REQUIRED
        )

    validate_player_development_plan_governance(
        normalized_status,
        normalized_coach_approved,
        normalized_approval_state,
    )

    return normalized_status, normalized_coach_approved, normalized_approval_state
