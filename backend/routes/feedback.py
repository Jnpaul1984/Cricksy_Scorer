"""Feedback submission route for user feedback collection."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.security import get_current_user_optional
from backend.sql_app import models, schemas
from backend.sql_app.database import get_db

router = APIRouter(prefix="/api/feedback", tags=["feedback"])
logger = logging.getLogger(__name__)


@router.post(
    "",
    response_model=schemas.FeedbackRead,
    status_code=status.HTTP_201_CREATED,
    summary="Submit user feedback",
    description="Accepts feedback from users with optional email and page context.",
)
async def submit_feedback(
    feedback_in: schemas.FeedbackCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    x_page_route: Annotated[str | None, Header(alias="X-Page-Route")] = None,
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> schemas.FeedbackRead:
    """
    Submit user feedback.

    - **text**: The feedback text (required, 1-5000 chars)
    - **email**: Optional contact email
    - **userId**: Optional user ID (ignored if user is authenticated)
    - **pageRoute**: Optional page/route context (can also be sent via X-Page-Route header)

    If the user is authenticated, their user_id and role are automatically captured.
    """
    # Determine user info from auth or request body
    user_id = current_user.id if current_user else feedback_in.userId
    user_role = current_user.role.value if current_user and current_user.role else None

    # Use header if pageRoute not provided in body
    page_route = feedback_in.pageRoute or x_page_route

    feedback = models.FeedbackSubmission(
        text=feedback_in.text,
        email=feedback_in.email,
        user_id=user_id,
        user_role=user_role,
        page_route=page_route,
    )

    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    logger.info(
        "Feedback submitted: id=%s user_id=%s page=%s",
        feedback.id,
        user_id,
        page_route,
    )

    return schemas.FeedbackRead.model_validate(feedback)
