"""
AI Routes - Endpoints for AI-powered features.

This module provides API endpoints for:
- Delivery commentary generation
- (Future) Player insights, match predictions, etc.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.ai_commentary import (
    AiCommentaryResponse,
    DeliveryContextRequest,
    build_delivery_commentary,
)
from backend.sql_app import crud
from backend.sql_app.database import get_db

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/commentary", response_model=AiCommentaryResponse)
async def generate_ai_commentary(
    payload: DeliveryContextRequest,
    db: AsyncSession = Depends(get_db),
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
        return build_delivery_commentary(game, payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from None
