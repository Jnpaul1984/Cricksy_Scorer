"""
AI Routes - Endpoints for AI-powered features.

This module provides API endpoints for:
- Delivery commentary generation
- (Future) Player insights, match predictions, etc.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.services.ai_commentary import (
    AiCommentaryResponse,
    DeliveryContextRequest,
    build_delivery_commentary,
)
from backend.services.ai_usage import log_ai_usage
from backend.sql_app import crud, models
from backend.sql_app.database import get_db

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/commentary", response_model=AiCommentaryResponse)
async def generate_ai_commentary(
    payload: DeliveryContextRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[models.User | None, Depends(security.get_current_user_optional)] = None,
) -> AiCommentaryResponse:
    """
    Generate AI-style commentary for a specific delivery.

    This endpoint returns a short 1-2 sentence insight about the delivery,
    considering the match context, players involved, and current phase.

    Args:
        payload: Request with game_id, over_number, ball_number, and optional tone
        db: Database session

    Returns:
        AiCommentaryResponse with:
        - commentary: Short AI-generated insight
        - tone: The tone used (neutral/hype/coach)
        - tags: Relevant tags (wicket, boundary, dot_ball, etc.)
        - generated_at: Timestamp

    Raises:
        HTTPException 404: If game or delivery not found
    """
    # Fetch game from database
    game = await crud.get_game(db, payload.game_id)

    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {payload.game_id} not found",
        )

    try:
        result = build_delivery_commentary(game, payload)

        # Log AI usage if user is authenticated
        if current_user:
            await log_ai_usage(
                db=db,
                user_id=str(current_user.id),
                feature="delivery_commentary",
                tokens_used=50,  # Approximate token count for rule-based generation
                context_id=payload.game_id,
                model_name="rule-based",
            )

        return result
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from None
