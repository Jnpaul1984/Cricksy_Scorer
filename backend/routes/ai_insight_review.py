"""
Phase 8C — AI Insight Review API.

Endpoints:
  GET  /ai-insights/review/{insight_type}/{insight_id}
       Return the current review state for an AI insight.

  POST /ai-insights/review/{insight_type}/{insight_id}
       Submit a review decision (approve, reject, flag, etc.).

Governance rules:
- Reviewer roles: analyst_pro, org_pro.
- Official cricket truth is never mutated through these endpoints.
- All outputs remain advisory — review state is metadata, not official truth.
"""

from __future__ import annotations

from typing import Annotated

from backend import security
from backend.api.schemas.ai_insight_review import (
    AiInsightReviewResponse,
    AiInsightReviewStateResponse,
    AiInsightReviewSubmit,
)
from backend.services.ai_insight_review_service import get_review_state, submit_review
from backend.sql_app import models
from backend.sql_app.database import get_db
from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/ai-insights",
    tags=["ai-insight-review"],
)

# Allowed insight output types (mirrors AiOutputType values)
_ALLOWED_INSIGHT_TYPES = frozenset(
    {"commentary", "insight", "recommendation", "report", "summary", "draft"}
)


def _validate_insight_type(insight_type: str) -> None:
    if insight_type not in _ALLOWED_INSIGHT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"insight_type '{insight_type}' is not valid.  "
                f"Allowed values: {sorted(_ALLOWED_INSIGHT_TYPES)}"
            ),
        )


@router.get(
    "/review/{insight_type}/{insight_id}",
    response_model=AiInsightReviewStateResponse,
    summary="Get current review state for an AI insight",
)
async def get_ai_insight_review(
    insight_type: Annotated[str, Path(description="AI output type (summary, insight, …)")],
    insight_id: Annotated[str, Path(description="Insight identifier (match_id, player_id, …)")],
    current_user: Annotated[
        models.User,
        Depends(security.require_roles(["analyst_pro", "org_pro"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiInsightReviewStateResponse:
    """
    Return the current review state and latest reviewer decision for an AI insight.

    When no review has been submitted the response carries ``current_state='pending'``.
    """
    _validate_insight_type(insight_type)
    try:
        return await get_review_state(
            db=db,
            insight_type=insight_type,
            insight_id=insight_id,
            requesting_user=current_user,
        )
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from None


@router.post(
    "/review/{insight_type}/{insight_id}",
    response_model=AiInsightReviewResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a review decision for an AI insight",
)
async def submit_ai_insight_review(
    insight_type: Annotated[str, Path(description="AI output type (summary, insight, …)")],
    insight_id: Annotated[str, Path(description="Insight identifier (match_id, player_id, …)")],
    payload: AiInsightReviewSubmit,
    current_user: Annotated[
        models.User,
        Depends(security.require_roles(["analyst_pro", "org_pro"])),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AiInsightReviewResponse:
    """
    Submit a review decision (approve / reject / request-changes / flag) for an AI insight.

    Each call creates a new audit row.  The latest row defines the current state.
    Reviewer role must be analyst_pro or org_pro.
    """
    _validate_insight_type(insight_type)
    try:
        review = await submit_review(
            db=db,
            insight_type=insight_type,
            insight_id=insight_id,
            payload=payload,
            reviewer=current_user,
        )
        await db.commit()
        return review
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from None
    except ValueError as exc:
        # Catches validate_no_official_truth_mutation violations
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from None
