"""
Highlights API routes.

Provides endpoints for:
- Generating highlights from match data
- Retrieving highlights for a game
- Sharing highlights on social media
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.highlights_service import HighlightsService
from backend.sql_app import models, schemas
from backend.sql_app.database import get_db

router = APIRouter(prefix="/highlights", tags=["highlights"])


@router.post("/games/{game_id}/generate", response_model=schemas.HighlightList)
async def generate_highlights(
    game_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.HighlightList:
    """
    Generate highlights for a completed or ongoing match.
    
    Detects key moments (boundaries, wickets, milestones) from the match
    deliveries and creates highlight records.
    """
    # Fetch the game
    result = await db.execute(select(models.Game).where(models.Game.id == game_id))
    game = result.scalar_one_or_none()
    
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # Detect highlights from deliveries
    highlight_dicts = HighlightsService.detect_highlights(
        deliveries=game.deliveries or [],
        batting_scorecard=game.batting_scorecard or {},
        bowling_scorecard=game.bowling_scorecard or {},
        game_id=game_id,
        current_inning=game.current_inning,
    )
    
    # Check if highlights already exist for this game to avoid duplicates
    existing_result = await db.execute(
        select(models.Highlight).where(models.Highlight.game_id == game_id)
    )
    existing_highlights = existing_result.scalars().all()
    
    # If highlights already exist, return them
    if existing_highlights:
        return schemas.HighlightList(
            highlights=[schemas.Highlight.model_validate(h) for h in existing_highlights],
            total=len(existing_highlights),
        )
    
    # Create highlight records
    highlights = []
    for h_dict in highlight_dicts:
        highlight = models.Highlight(
            id=str(uuid.uuid4()),
            game_id=h_dict["game_id"],
            event_type=h_dict["event_type"],
            over_number=h_dict["over_number"],
            ball_number=h_dict["ball_number"],
            inning=h_dict["inning"],
            title=h_dict["title"],
            description=h_dict.get("description"),
            player_id=h_dict.get("player_id"),
            player_name=h_dict.get("player_name"),
            event_metadata=h_dict.get("event_metadata", {}),
            video_generated=False,
        )
        
        # Generate video URL (mock for now)
        highlight.video_url = HighlightsService.generate_video_url(h_dict)
        
        db.add(highlight)
        highlights.append(highlight)
    
    await db.commit()
    
    # Refresh highlights to get created_at timestamps
    for h in highlights:
        await db.refresh(h)
    
    return schemas.HighlightList(
        highlights=[schemas.Highlight.model_validate(h) for h in highlights],
        total=len(highlights),
    )


@router.get("/games/{game_id}", response_model=schemas.HighlightList)
async def get_game_highlights(
    game_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.HighlightList:
    """
    Retrieve all highlights for a specific game.
    """
    result = await db.execute(
        select(models.Highlight)
        .where(models.Highlight.game_id == game_id)
        .order_by(models.Highlight.over_number, models.Highlight.ball_number)
    )
    highlights = result.scalars().all()
    
    return schemas.HighlightList(
        highlights=[schemas.Highlight.model_validate(h) for h in highlights],
        total=len(highlights),
    )


@router.get("/{highlight_id}", response_model=schemas.Highlight)
async def get_highlight(
    highlight_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.Highlight:
    """
    Retrieve a specific highlight by ID.
    """
    result = await db.execute(
        select(models.Highlight).where(models.Highlight.id == highlight_id)
    )
    highlight = result.scalar_one_or_none()
    
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")
    
    return schemas.Highlight.model_validate(highlight)


@router.post("/share", response_model=schemas.HighlightShareResponse)
async def share_highlight(
    request: schemas.HighlightShareRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.HighlightShareResponse:
    """
    Generate a share URL for a highlight on a social media platform.
    """
    # Verify highlight exists
    result = await db.execute(
        select(models.Highlight).where(models.Highlight.id == request.highlight_id)
    )
    highlight = result.scalar_one_or_none()
    
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")
    
    # Generate share URL
    share_url = HighlightsService.generate_share_url(
        request.highlight_id,
        request.platform,
    )
    
    return schemas.HighlightShareResponse(
        success=True,
        share_url=share_url,
        message=f"Share URL generated for {request.platform}",
    )


@router.delete("/{highlight_id}")
async def delete_highlight(
    highlight_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """
    Delete a specific highlight.
    """
    result = await db.execute(
        select(models.Highlight).where(models.Highlight.id == highlight_id)
    )
    highlight = result.scalar_one_or_none()
    
    if not highlight:
        raise HTTPException(status_code=404, detail="Highlight not found")
    
    await db.delete(highlight)
    await db.commit()
    
    return {"message": "Highlight deleted successfully"}
