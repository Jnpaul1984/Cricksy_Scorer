"""
Pydantic schemas for the Phase 8C AI Insight Review workflow.

Contracts:
  POST /ai-insights/review/{insight_type}/{insight_id}  — submit a review decision
  GET  /ai-insights/review/{insight_type}/{insight_id}  — fetch latest review state

Governance rule:
    These schemas carry advisory-only review metadata.  They must never be
    used to mutate official cricket truth (scores, results, player stats, DLS).
"""

from __future__ import annotations

import datetime as dt

from backend.sql_app.models import AiInsightFeedbackType, AiInsightReviewState
from pydantic import BaseModel, Field


class AiInsightReviewSubmit(BaseModel):
    """Request body for submitting a review decision on an AI insight."""

    review_state: AiInsightReviewState = Field(
        description=("New review state: approved, rejected, changes_requested, or flagged.")
    )
    feedback_type: AiInsightFeedbackType | None = Field(
        default=None,
        description=(
            "Optional discrete feedback signal: useful, not_useful, unsafe, or unsupported_claim."
        ),
    )
    note: str | None = Field(
        default=None,
        max_length=2000,
        description="Optional reviewer note or requested change description.",
    )


class AiInsightReviewResponse(BaseModel):
    """Response for a single review record."""

    id: str
    insight_type: str
    insight_id: str
    reviewer_id: str
    reviewer_org_id: str | None
    review_state: AiInsightReviewState
    feedback_type: AiInsightFeedbackType | None
    note: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class AiInsightReviewStateResponse(BaseModel):
    """
    Current review state summary returned by GET /ai-insights/review/{type}/{id}.

    When no review exists the state is ``pending``.
    """

    insight_type: str
    insight_id: str
    current_state: AiInsightReviewState
    latest_review: AiInsightReviewResponse | None = None
    total_reviews: int = 0
    is_advisory_only: bool = Field(
        default=True,
        description=(
            "Always True — this review state is advisory metadata only and "
            "must never be treated as official cricket truth."
        ),
    )
