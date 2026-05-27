"""Phase 5N — Historical Stats Aggregation Layer: Pydantic response schemas.

These schemas define the shape of deterministic aggregate statistics
computed from validated, fully-imported historical match data.

Metadata-only imports are excluded and flagged separately.
No live scoring truth is mutated by these schemas.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, Field


class InningsAggregate(BaseModel):
    """Aggregate stats for a single innings within a historical match."""

    inning_no: int
    team: str | None = None
    runs: int
    wickets: int
    overs: float
    extras: int = 0


class MatchAggregate(BaseModel):
    """Deterministic aggregate statistics for a single historical match.

    Computed from Game.phases['historical_innings_summary'] and,
    when available, Game.batting_scorecard / Game.bowling_scorecard.
    Source fields are read-only — no official truth is mutated.
    """

    match_id: str
    teams: str
    team_a: str | None = None
    team_b: str | None = None

    # Provenance
    import_batch_id: str | None = None
    source_filename: str | None = None
    source_format: str | None = None
    competition: str | None = None
    season: str | None = None
    season_raw: str | None = None
    season_source: Literal["metadata", "match_date", "missing"] = "missing"
    venue: str | None = None
    venue_raw: str | None = None
    venue_canonical: str | None = None
    venue_continuity_group: str | None = None
    match_date: str | None = None
    match_type: str | None = None

    # Match-level aggregates
    innings_count: int
    total_runs: int
    total_wickets: int
    innings_totals: list[InningsAggregate] = Field(default_factory=list)
    winner_team: str | None = None
    winner_team_canonical: str | None = None
    winner_source: str | None = None
    winner_confidence: Literal["high", "medium", "low", "none"] = "none"
    wicket_derivation_source: Literal["deliveries", "innings_summary", "scorecard", "missing"] = (
        "missing"
    )
    phase_breakdown: dict[str, dict[str, int | float]] = Field(default_factory=dict)
    team_a_canonical: str | None = None
    team_b_canonical: str | None = None

    # Whether delivery-level data has been imported (Phase 5F)
    has_delivery_data: bool = False


class PlayerAggregate(BaseModel):
    """Aggregate batting and bowling stats for a player across historical matches.

    Computed from Game.batting_scorecard and Game.bowling_scorecard.
    Only populated for games that have had Phase 5F delivery data imported.
    Player identity is keyed by name string (no ORM Player rows exist for historical games).
    """

    player_name: str
    matches_contributed: int = 0

    # Batting
    runs_scored: int = 0
    balls_faced: int = 0
    strike_rate: float = 0.0
    fours: int = 0
    sixes: int = 0
    dismissals: int = 0

    # Bowling
    overs_bowled: float = 0.0
    runs_conceded: int = 0
    wickets: int = 0
    economy_rate: float = 0.0
    maidens: int = 0


class TeamAggregate(BaseModel):
    """Aggregate stats for a team across historical matches."""

    team_name: str
    canonical_team_name: str | None = None
    continuity_group: str | None = None
    matches_played: int
    innings_batted: int = 0
    avg_score: float = 0.0
    avg_wickets: float = 0.0
    total_runs: int = 0
    total_wickets: int = 0


class VenueAggregate(BaseModel):
    """Aggregate stats for matches played at a specific venue."""

    venue: str
    canonical_venue: str | None = None
    continuity_group: str | None = None
    raw_venues: list[str] = Field(default_factory=list)
    match_count: int
    avg_first_innings_score: float = 0.0
    avg_second_innings_score: float | None = None
    avg_total_runs: float = 0.0
    avg_wickets: float = 0.0


class CompetitionAggregate(BaseModel):
    """Aggregate stats for a competition (event) across historical matches."""

    competition: str
    match_count: int
    avg_total_runs: float = 0.0
    avg_wickets: float = 0.0


class SeasonAggregate(BaseModel):
    """Aggregate stats for a season across historical matches."""

    season: str
    match_count: int
    avg_total_runs: float = 0.0
    avg_wickets: float = 0.0


class SeasonOutcomeStageMatch(BaseModel):
    """Detected playoff/final-stage match metadata within a season."""

    match_id: str
    match_title: str
    match_date: str | None = None
    stage_label: str
    result: str | None = None
    winner_team_raw: str | None = None
    winner_team_canonical: str | None = None
    winner_confidence: Literal["high", "medium", "low", "none"] = "none"


class SeasonOutcomeAggregate(BaseModel):
    """Deterministic tournament season outcome intelligence."""

    competition_code: str
    competition_name: str
    season: str | None = None
    season_year: int | None = None
    gender_category: str
    champion_team_raw: str | None = None
    champion_team_canonical: str | None = None
    runner_up_team_raw: str | None = None
    runner_up_team_canonical: str | None = None
    final_match_id: str | None = None
    final_match_title: str | None = None
    final_match_date: str | None = None
    final_result: str | None = None
    league_table_leader_raw: str | None = None
    league_table_leader_canonical: str | None = None
    playoff_stage_matches_detected: list[SeasonOutcomeStageMatch] = Field(default_factory=list)
    total_matches_in_season: int
    outcome_source: str
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    unresolved_reason: str | None = None


class TrophySummaryAggregate(BaseModel):
    """Deterministic trophy/finals summary by canonical franchise/team."""

    canonical_team: str
    raw_team_names_seen: list[str] = Field(default_factory=list)
    trophies_detected: int = 0
    finals_appearances_detected: int = 0
    runner_up_finishes_detected: int = 0
    seasons_won: list[str] = Field(default_factory=list)
    competitions: list[str] = Field(default_factory=list)
    competition_codes: list[str] = Field(default_factory=list)
    gender_categories: list[str] = Field(default_factory=list)
    confidence_notes: list[str] = Field(default_factory=list)


class HistoricalStatsSummaryResponse(BaseModel):
    """Full deterministic historical stats summary.

    Phase 5N: on-demand aggregation from validated historical match data.

    Excluded records:
    - metadata_only: batches with status in {scanned, metadata_extracted, pending_full_import}
    - invalid: batches that are not finalized, have errors, or have non-valid status

    No live scoring truth, DLS logic, or official scorecards are mutated.
    """

    total_eligible_matches: int
    excluded_metadata_only_count: int
    excluded_invalid_count: int

    matches: list[MatchAggregate] = Field(default_factory=list)
    players: list[PlayerAggregate] = Field(default_factory=list)
    teams: list[TeamAggregate] = Field(default_factory=list)
    venues: list[VenueAggregate] = Field(default_factory=list)
    competitions: list[CompetitionAggregate] = Field(default_factory=list)
    seasons: list[SeasonAggregate] = Field(default_factory=list)
    diagnostics: dict[str, int] = Field(default_factory=dict)
    top_team_by_wins: dict[str, Any] | None = None
    case_studies: list[dict[str, Any]] = Field(default_factory=list)
    season_outcomes: list[SeasonOutcomeAggregate] = Field(default_factory=list)
    trophy_summary: list[TrophySummaryAggregate] = Field(default_factory=list)
    deterministic_outcome_insights: list[str] = Field(default_factory=list)

    generated_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))
    note: str = (
        "Deterministic on-demand aggregation from validated historical match data only. "
        "Metadata-only imports are excluded. No official cricket truth is mutated."
    )


class HistoricalMatchAggregateResponse(BaseModel):
    """Single-match aggregate stats response.

    Phase 5N: on-demand aggregation for a single historical match.
    Returns aggregate stats plus per-player batting/bowling summaries
    when delivery-level data has been imported (Phase 5F).
    """

    match: MatchAggregate
    players: list[PlayerAggregate] = Field(default_factory=list)
    provenance: dict[str, Any] = Field(default_factory=dict)
    note: str = (
        "Deterministic on-demand aggregation from a single validated historical match. "
        "No official cricket truth is mutated."
    )
