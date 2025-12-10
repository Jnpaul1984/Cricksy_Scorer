"""
Pydantic schemas for Match AI Commentary endpoint.

Path: GET /matches/{match_id}/ai-commentary
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

UTC = getattr(dt, "UTC", dt.UTC)


class CommentaryItem(BaseModel):
    """Single AI-generated commentary entry."""

    over: float | None = Field(
        default=None,
        description="Over number as decimal (e.g., 5.3 for 3rd ball of 6th over)",
    )
    ball_index: int | None = Field(
        default=None,
        description="Sequential ball index within the innings (0-indexed)",
    )
    event_tags: list[str] = Field(
        default_factory=list,
        description="Tags describing the event (e.g., ['boundary', 'four', 'powerplay'])",
    )
    text: str = Field(
        description="AI-generated commentary text",
    )
    tone: Literal["neutral", "hype", "critical"] = Field(
        default="neutral",
        description="Tone of the commentary",
    )
    created_at: str = Field(
        description="ISO 8601 timestamp when commentary was generated",
    )


class MatchAiCommentaryResponse(BaseModel):
    """Response schema for GET /matches/{match_id}/ai-commentary."""

    match_id: str = Field(description="The match/game ID")
    commentary: list[CommentaryItem] = Field(
        default_factory=list,
        description="List of AI commentary entries for the match",
    )
