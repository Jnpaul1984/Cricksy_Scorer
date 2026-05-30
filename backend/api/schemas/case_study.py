"""
Pydantic schemas for the Match Case Study API.

Response model for:
  GET /analytics/matches/{match_id}/case-study

Powers the MatchCaseStudyView.vue UI with structured match analysis data.
"""

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _normalize_source_dates(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


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
    event_name: str | None = None
    season: str | None = None
    match_number: int | None = None
    source_dates: list[str] = Field(default_factory=list)
    result: str
    overs_per_side: int | None = None
    innings: list[CaseStudyInningsSummary]

    @field_validator("source_dates", mode="before")
    @classmethod
    def validate_source_dates(cls, value: Any) -> list[str]:
        return _normalize_source_dates(value)


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
    innings_index: int | None = None
    phase_id: str | None = None
    level: Literal["innings", "match"] = "innings"
    swing_metric: CaseStudySwingMetric | None = None


# -----------------------------------------------------------------------------
# Key Phase
# -----------------------------------------------------------------------------


class CaseStudyKeyPhase(BaseModel):
    """The single most impactful phase of the match."""

    title: str
    detail: str
    innings_index: int | None = None
    team: str | None = None
    level: Literal["innings", "match"] = "innings"
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
    innings_index: int | None = None
    team: str | None = None
    level: Literal["innings", "match"] = "innings"


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

    level: Literal["innings", "match"] = "innings"
    innings_index: int | None = None
    summary: str | None = None
    total_wickets: int = 0
    wickets_by_phase: list[dict[str, Any]] = []
    wickets_by_over_band: list[dict[str, Any]] = []
    dismissal_types: list[dict[str, Any]] = []
    bowler_involvement: list[dict[str, Any]] = []
    fielding_involvement: list[dict[str, Any]] = []
    dismissed_batters: list[str] = []
    wicket_timeline: list[dict[str, Any]] = []
    wicket_cluster_callout: str | None = None
    fallback_reason: str | None = None
    by_bowler_type: list[CaseStudyDismissalByBowlerType] = []
    by_shot_type: list[CaseStudyDismissalByShotType] = []
    by_zone: list[CaseStudyDismissalByZone] = []


class CaseStudyStoryBlocks(BaseModel):
    """Deterministic innings story derived from score/phase data."""

    opening_story: str
    middle_overs_story: str
    death_overs_story: str
    scoring_acceleration: str
    wickets_by_phase: str
    strongest_phase: str
    weakest_phase: str
    innings_outcome_contribution: str


class CaseStudyAnalystCallout(BaseModel):
    """Deterministic analyst callout with evidence."""

    title: str
    level: Literal["innings", "match"] = "innings"
    innings: int | None = None
    phase: str
    category: Literal["batting", "bowling", "player", "dismissal", "momentum", "outcome"]
    severity: Literal["positive", "warning", "info"]
    explanation: str
    source_metrics: list[str] = []
    confidence: float = Field(ge=0.0, le=1.0, default=0.7)
    why_it_matters: str


class CaseStudyInningsAnalysis(BaseModel):
    """All innings-scoped case study intelligence."""

    innings_index: int
    team: str
    deterministic_summary: str
    momentum_summary: CaseStudyMomentumSummary
    key_phase: CaseStudyKeyPhase
    phases: list[CaseStudyPhase]
    key_players: list[CaseStudyKeyPlayer]
    key_players_scope: Literal["innings", "match"] = "innings"
    dismissal_patterns: CaseStudyDismissalPatterns
    story_blocks: CaseStudyStoryBlocks
    callouts: list[CaseStudyAnalystCallout] = []


class CaseStudyMultiDayInningsContext(BaseModel):
    """Innings-scoped multi-day summary row."""

    innings_number: int
    team: str
    runs: int
    wickets: int
    overs: float
    deliveries: int | None = None
    lead_deficit_after_innings: int | None = None


class CaseStudyMultiDaySummary(BaseModel):
    """Format-safe summary payload for Test/multi-day matches."""

    match_status: Literal["won", "lost", "draw", "tie", "no_result", "unknown"]
    innings: list[CaseStudyMultiDayInningsContext] = []
    fourth_innings_chase_note: str | None = None
    notice: str = (
        "Test/multi-day analysis is currently limited and uses innings/session-safe summaries."
    )


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

    analysis_mode: Literal["limited_overs", "test_multi_day", "unknown"] = "unknown"
    match: CaseStudyMatch
    momentum_summary: CaseStudyMomentumSummary
    key_phase: CaseStudyKeyPhase
    phases: list[CaseStudyPhase]
    key_players: list[CaseStudyKeyPlayer]
    dismissal_patterns: CaseStudyDismissalPatterns | None = None
    innings_analysis: list[CaseStudyInningsAnalysis] = []
    match_callouts: list[CaseStudyAnalystCallout] = []
    match_level_summary: str | None = None
    multi_day_summary: CaseStudyMultiDaySummary | None = None
    ai: CaseStudyAIBlock | None = None
