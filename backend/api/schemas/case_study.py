"""
Pydantic schemas for the Match Case Study API.

Response model for:
  GET /analytics/matches/{match_id}/case-study

Powers the MatchCaseStudyView.vue UI with structured match analysis data.
"""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# -----------------------------------------------------------------------------
# Innings Summary
# -----------------------------------------------------------------------------


class CaseStudyInningsSummary(BaseModel):
    """Summary of a single innings in the match."""

    team: str
    runs: int
    wickets: int
    overs: float
    run_rate: float


# -----------------------------------------------------------------------------
# Match Header
# -----------------------------------------------------------------------------


class CaseStudyMatch(BaseModel):
    """Core match metadata for the case study header."""

    id: str
    date: date
    format: Literal["T20", "ODI", "TEST", "CUSTOM"]
    home_team: str | None = None
    away_team: str | None = None
    teams_label: str  # e.g. "Lions vs Falcons"
    venue: str | None = None
    result: str
    overs_per_side: int | None = None
    innings: list[CaseStudyInningsSummary]


# -----------------------------------------------------------------------------
# Momentum Summary
# -----------------------------------------------------------------------------


class CaseStudySwingMetric(BaseModel):
    """Quantified momentum swing data."""

    runs_above_par: int | None = None
    win_probability_shift: float | None = None


class CaseStudyMomentumSummary(BaseModel):
    """High-level momentum verdict for the match."""

    title: str
    subtitle: str
    winning_side: str | None = None
    swing_metric: CaseStudySwingMetric | None = None


# -----------------------------------------------------------------------------
# Key Phase
# -----------------------------------------------------------------------------


class CaseStudyKeyPhase(BaseModel):
    """The single most impactful phase of the match."""

    title: str
    detail: str
    overs_range: dict | None = None  # {"start_over": int, "end_over": int}
    reason_codes: list[str] = []


# -----------------------------------------------------------------------------
# Phase Breakdown
# -----------------------------------------------------------------------------


class CaseStudyPhase(BaseModel):
    """Breakdown of a single phase (powerplay, middle, death, or custom)."""

    id: Literal["powerplay", "middle", "death", "custom"]
    label: str
    start_over: int
    end_over: int
    runs: int
    wickets: int
    run_rate: float
    net_swing_vs_par: int
    impact: Literal["positive", "negative", "neutral"]
    impact_label: str


# -----------------------------------------------------------------------------
# Key Players
# -----------------------------------------------------------------------------


class CaseStudyPlayerBatting(BaseModel):
    """Batting statistics for a key player."""

    innings: int
    runs: int
    balls: int
    strike_rate: float
    boundaries: dict  # {"fours": int, "sixes": int}


class CaseStudyPlayerBowling(BaseModel):
    """Bowling statistics for a key player."""

    overs: float
    maidens: int
    runs: int
    wickets: int
    economy: float


class CaseStudyPlayerFielding(BaseModel):
    """Fielding statistics for a key player."""

    catches: int
    run_outs: int
    drops: int


class CaseStudyKeyPlayer(BaseModel):
    """A key player with match impact analysis."""

    id: str
    name: str
    team: str
    role: str
    batting: CaseStudyPlayerBatting | None = None
    bowling: CaseStudyPlayerBowling | None = None
    fielding: CaseStudyPlayerFielding | None = None
    impact: Literal["high", "medium", "low"]
    impact_label: str
    impact_score: float | None = None


# -----------------------------------------------------------------------------
# Dismissal Patterns
# -----------------------------------------------------------------------------


class CaseStudyDismissalByBowlerType(BaseModel):
    """Wickets grouped by bowler type (pace, spin, etc.)."""

    type: str
    wickets: int


class CaseStudyDismissalByShotType(BaseModel):
    """Wickets grouped by shot type (drive, pull, etc.)."""

    shot: str
    wickets: int


class CaseStudyDismissalByZone(BaseModel):
    """Wickets grouped by field zone (covers, deep midwicket, etc.)."""

    zone: str
    wickets: int


class CaseStudyDismissalPatterns(BaseModel):
    """Aggregated dismissal pattern analysis."""

    summary: str | None = None
    by_bowler_type: list[CaseStudyDismissalByBowlerType] = []
    by_shot_type: list[CaseStudyDismissalByShotType] = []
    by_zone: list[CaseStudyDismissalByZone] = []


# -----------------------------------------------------------------------------
# AI Block
# -----------------------------------------------------------------------------


class CaseStudyAIBlock(BaseModel):
    """AI-generated match summary with metadata."""

    model_config = ConfigDict(populate_by_name=True)

    match_summary: str
    generated_at: datetime | None = None
    ml_model_version: str | None = Field(default=None, alias="model_version")
    tokens_used: int | None = None


# -----------------------------------------------------------------------------
# Full Response
# -----------------------------------------------------------------------------


class MatchCaseStudyResponse(BaseModel):
    """
    Complete response model for GET /analytics/matches/{match_id}/case-study.

    Provides all data needed to render the MatchCaseStudyView.vue UI.
    """

    match: CaseStudyMatch
    momentum_summary: CaseStudyMomentumSummary
    key_phase: CaseStudyKeyPhase
    phases: list[CaseStudyPhase]
    key_players: list[CaseStudyKeyPlayer]
    dismissal_patterns: CaseStudyDismissalPatterns | None = None
    ai: CaseStudyAIBlock | None = None
