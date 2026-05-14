"""Phase 5N — Historical Stats Aggregation Layer: Pydantic response schemas.

These schemas define the shape of deterministic aggregate statistics
computed from validated, fully-imported historical match data.

Metadata-only imports are excluded and flagged separately.
No live scoring truth is mutated by these schemas.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

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
    venue: str | None = None
    match_date: str | None = None
    match_type: str | None = None

    # Match-level aggregates
    innings_count: int
    total_runs: int
    total_wickets: int
    innings_totals: list[InningsAggregate] = Field(default_factory=list)

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
    matches_played: int
    innings_batted: int = 0
    avg_score: float = 0.0
    avg_wickets: float = 0.0
    total_runs: int = 0
    total_wickets: int = 0


class VenueAggregate(BaseModel):
    """Aggregate stats for matches played at a specific venue."""

    venue: str
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

    generated_at: dt.datetime = Field(
        default_factory=lambda: dt.datetime.now(dt.timezone.utc)
    )
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
