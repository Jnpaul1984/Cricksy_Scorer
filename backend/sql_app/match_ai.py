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


# ---------------------------------------------------------------------------
# Match AI Summary Schemas (for /analyst/matches/{match_id}/ai-summary)
# ---------------------------------------------------------------------------


class MatchAiSummaryTeam(BaseModel):
    """Team summary in the AI match analysis."""

    team_id: str = Field(description="Team identifier")
    team_name: str = Field(description="Team display name")
    result: Literal["won", "lost", "tied", "no_result"] = Field(
        description="Match result for this team"
    )
    total_runs: int = Field(description="Total runs scored")
    wickets_lost: int = Field(description="Wickets lost")
    overs_faced: float = Field(description="Overs faced (decimal)")
    key_stats: list[str] = Field(
        default_factory=list,
        description="Short bullet-like stat points",
    )


class DecisivePhaseSummary(BaseModel):
    """A decisive phase in the match."""

    phase_id: str = Field(description="Unique phase identifier")
    innings: int = Field(description="Innings number (1 or 2)")
    label: str = Field(description="Phase label (Powerplay, Middle Overs, Death Overs)")
    over_range: tuple[float, float] = Field(description="Start and end over (decimal)")
    impact_score: float = Field(description="Impact score from -100 to 100 (normalized)")
    narrative: str = Field(description="1-2 sentence narrative of what happened")


class MomentumShiftSummary(BaseModel):
    """A momentum shift event in the match."""

    shift_id: str = Field(description="Unique shift identifier")
    innings: int = Field(description="Innings number")
    over: float = Field(description="Over when shift occurred (decimal)")
    description: str = Field(description="Description of the momentum shift")
    impact_delta: float = Field(description="Change in win probability or impact (-100 to 100)")
    team_benefiting_id: str = Field(description="Team ID that benefited from the shift")


class PlayerHighlightSummary(BaseModel):
    """A player highlight in the match."""

    player_id: str = Field(description="Player identifier")
    player_name: str = Field(description="Player display name")
    team_id: str = Field(description="Team identifier")
    role: str = Field(description="Player role (batter, bowler, allrounder, keeper)")
    highlight_type: str = Field(description="Type of highlight (innings, spell, fielding, etc.)")
    summary: str = Field(description="Summary of the highlight")


class MatchAiSummaryResponse(BaseModel):
    """Response schema for GET /analyst/matches/{match_id}/ai-summary."""

    match_id: str = Field(description="The match/game ID")
    format: Literal["T20", "ODI", "Custom"] = Field(description="Match format")
    teams: list[MatchAiSummaryTeam] = Field(description="Team summaries")
    key_themes: list[str] = Field(
        default_factory=list,
        description="Key themes identified in the match",
    )
    decisive_phases: list[DecisivePhaseSummary] = Field(
        default_factory=list,
        description="Decisive phases of the match",
    )
    momentum_shifts: list[MomentumShiftSummary] = Field(
        default_factory=list,
        description="Momentum shift events",
    )
    player_highlights: list[PlayerHighlightSummary] = Field(
        default_factory=list,
        description="Player highlights",
    )
    overall_summary: str = Field(description="Natural language match summary")
    created_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(UTC),
        description="When this summary was generated",
    )
