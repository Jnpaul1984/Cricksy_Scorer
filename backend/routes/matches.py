"""
Match AI Commentary route.

GET /matches/{match_id}/ai-commentary - Returns AI-generated commentary for a match.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.match_ai_service import get_match_ai_commentary
from backend.sql_app.database import get_db
from backend.sql_app.match_ai import MatchAiCommentaryResponse

router = APIRouter(prefix="/matches", tags=["matches", "ai-commentary"])


@router.get(
    "/{match_id}/ai-commentary",
    response_model=MatchAiCommentaryResponse,
    summary="Get AI-generated commentary for a match",
    description=(
        "Returns mock AI commentary based on match metadata including "
        "powerplay swings, wickets, and boundaries. "
        "Future versions will use LLM-generated commentary."
    ),
)
async def get_ai_commentary(
    match_id: str,
    db: AsyncSession = Depends(get_db),
) -> MatchAiCommentaryResponse:
    """
    Get AI-generated commentary for a specific match.

    Args:
        match_id: The match/game ID to get commentary for.
        db: Database session (injected).

    Returns:
        MatchAiCommentaryResponse with commentary entries.

    Raises:
        HTTPException 404: If the match is not found.
    """
    try:
        return await get_match_ai_commentary(db, match_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
