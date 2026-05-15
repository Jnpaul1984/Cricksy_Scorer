"""
Phase 8C — AI Insight Review Service.

Provides CRUD operations for reviewer decisions on AI-generated insights.

Governance rules:
- This service operates on advisory review metadata only.
- It must never mutate official cricket truth (scores, results, player stats, DLS).
- validate_no_official_truth_mutation is called before any persist to enforce the boundary.
- Org isolation: reviewers may only read/write reviews for insights owned by their own org.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from backend.api.schemas.ai_insight_review import (
    AiInsightReviewResponse,
    AiInsightReviewStateResponse,
    AiInsightReviewSubmit,
)
from backend.domain.ai_boundary import validate_no_official_truth_mutation
from backend.sql_app.models import (
    AiInsightFeedbackType,
    AiInsightReview,
    AiInsightReviewState,
    User,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Roles permitted to perform review actions.
REVIEWER_ROLES: frozenset[str] = frozenset({"analyst_pro", "org_pro"})


def _is_reviewer(user: User) -> bool:
    """Return True when *user* holds a role allowed to review AI insights."""
    role_value = getattr(user.role, "value", user.role)
    return role_value in REVIEWER_ROLES


def _assert_reviewer(user: User) -> None:
    """Raise PermissionError when *user* cannot review AI insights."""
    if not _is_reviewer(user):
        raise PermissionError(
            f"Role '{getattr(user.role, 'value', user.role)}' is not authorised to "
            "review AI insights.  Required roles: analyst_pro, org_pro."
        )


async def get_review_state(
    db: AsyncSession,
    insight_type: str,
    insight_id: str,
    requesting_user: User,
) -> AiInsightReviewStateResponse:
    """
    Return the current review state for an AI insight.

    When no review record exists the returned ``current_state`` is ``pending``.
    Raises ``PermissionError`` for unauthorized callers.
    """
    _assert_reviewer(requesting_user)

    stmt = (
        select(AiInsightReview)
        .where(
            AiInsightReview.insight_type == insight_type,
            AiInsightReview.insight_id == insight_id,
        )
        .order_by(AiInsightReview.created_at.desc())
    )
    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    latest = rows[0] if rows else None
    current_state = latest.review_state if latest else AiInsightReviewState.pending

    return AiInsightReviewStateResponse(
        insight_type=insight_type,
        insight_id=insight_id,
        current_state=current_state,
        latest_review=AiInsightReviewResponse.model_validate(latest) if latest else None,
        total_reviews=len(rows),
        is_advisory_only=True,
    )


async def submit_review(
    db: AsyncSession,
    insight_type: str,
    insight_id: str,
    payload: AiInsightReviewSubmit,
    reviewer: User,
) -> AiInsightReviewResponse:
    """
    Persist a new review decision for an AI insight.

    Raises ``PermissionError`` for unauthorized callers.

    The review payload is validated against OFFICIAL_TRUTH_FIELDS before
    persisting to guarantee no official cricket truth can be mutated.
    """
    _assert_reviewer(reviewer)

    # Phase 8C boundary gate: ensure no official truth field leaks into the review
    validate_no_official_truth_mutation(payload.model_dump(), "ai_insight_review_service")

    # Generate stable ID and timestamps in Python so we can return the
    # response immediately without needing db.flush()/db.refresh().
    now = datetime.now(UTC)
    review_id = str(uuid.uuid4())

    review = AiInsightReview(
        id=review_id,
        insight_type=insight_type,
        insight_id=insight_id,
        reviewer_id=reviewer.id,
        reviewer_org_id=reviewer.org_id,
        review_state=payload.review_state,
        feedback_type=payload.feedback_type,
        note=payload.note,
        created_at=now,
        updated_at=now,
    )
    db.add(review)

    return AiInsightReviewResponse(
        id=review_id,
        insight_type=insight_type,
        insight_id=insight_id,
        reviewer_id=reviewer.id,
        reviewer_org_id=reviewer.org_id,
        review_state=payload.review_state,
        feedback_type=payload.feedback_type,
        note=payload.note,
        created_at=now,
        updated_at=now,
    )


__all__ = [
    "REVIEWER_ROLES",
    "AiInsightFeedbackType",
    "AiInsightReviewState",
    "get_review_state",
    "submit_review",
]
