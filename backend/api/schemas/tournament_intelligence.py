"""Phase 10S.1 — Tournament Intelligence: Pydantic response schemas.

These schemas define the shape of deterministic tournament-level intelligence
derived from the historical archive and the Analyst Match Registry.

All statistics are derived from imported match data and labeled with their
confidence level. No official standings or statistics are fabricated.
"""

from __future__ import annotations

import datetime as dt
from typing import Any, Literal

from pydantic import BaseModel, Field


class TournamentGroupKey(BaseModel):
    """Identifies a unique tournament/season group.

    A group is defined by the combination of competition_code, season,
    gender_category, and format_family. Matches with unknown classification
    are placed into safe 'unknown' groups rather than forced into incorrect ones.
    """

    competition_code: str  # CPL_MEN | WCPL | ONE_DAY_CUP | unknown | …
    competition_name: str | None = None
    season: str | None = None
    season_year: int | None = None
    gender_category: str = "unknown"  # men | women | mixed | unknown
    format_family: str = "unknown"  # T20 | ODI | TEST | unknown
    source_type: str = "unknown"  # historical_import | cricksy_completed_scored | mixed | unknown


class TournamentGroupSummary(BaseModel):
    """Compact summary of one tournament/season group for the selector UI."""

    group_key: TournamentGroupKey
    match_count: int
    teams_count: int
    has_result_data: bool
    has_delivery_data: bool
    champion_detected: bool
    champion_team: str | None = None
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"


class DerivedStandingsRow(BaseModel):
    """One row in a derived standings table.

    Labeled as 'derived' — this is NOT official standings.
    Points are estimated using 2-for-win, 1-for-tie/no-result, 0-for-loss
    unless competition-specific rules are known.
    """

    team_name: str
    canonical_team_name: str | None = None
    played: int = 0
    wins: int = 0
    losses: int = 0
    ties: int = 0
    no_results: int = 0
    points: int = 0
    # Net run rate only when safely computable; None = unavailable
    net_run_rate: float | None = None
    nrr_available: bool = False
    confidence: Literal["high", "medium", "low"] = "low"
    note: str = "Derived from imported match results. Not official standings."


class TournamentMatchHighlight(BaseModel):
    """A notable match within a tournament for analyst/podcast use."""

    match_id: str
    match_title: str
    match_date: str | None = None
    stage_label: str | None = None
    result: str | None = None
    highlight_type: str  # biggest_win_runs | biggest_win_wickets | closest_match | final | semi_final
    detail: str | None = None


class TournamentPlayerLeader(BaseModel):
    """Top performer in a tournament (batting or bowling)."""

    player_name: str
    value: int | float  # runs or wickets
    matches_contributed: int
    stat_type: str  # runs | wickets
    source: str = "scorecard_or_delivery"
    confidence: Literal["high", "medium", "low"] = "medium"


class TournamentDataCompleteness(BaseModel):
    """Data completeness summary for a tournament group."""

    total_matches: int
    matches_with_result: int
    matches_missing_result: int
    delivery_complete_matches: int
    phase_level_matches: int
    innings_totals_matches: int
    metadata_only_matches: int
    confidence_level: Literal["high", "medium", "low", "unknown"] = "unknown"
    note: str = ""


class TournamentKnockoutContext(BaseModel):
    """Knockout/finals context derived from stage labels and result parsing."""

    champion_team: str | None = None
    champion_team_canonical: str | None = None
    runner_up_team: str | None = None
    runner_up_team_canonical: str | None = None
    final_match_id: str | None = None
    final_match_title: str | None = None
    final_match_date: str | None = None
    final_result: str | None = None
    semi_final_matches: list[TournamentMatchHighlight] = Field(default_factory=list)
    qualifier_matches: list[TournamentMatchHighlight] = Field(default_factory=list)
    outcome_source: str = "not_detected"
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    note: str = "Derived from stage labels and result text. Not from official records."


class TournamentPodcastFacts(BaseModel):
    """Deterministic tournament facts for podcast/analyst talking points.

    All values are derived from imported data only. Each fact includes a
    confidence label. Do not present these as official facts without verification.
    """

    competition_label: str
    season_label: str | None = None
    champion: str | None = None
    finalist: str | None = None
    strongest_team_by_wins: str | None = None
    top_scoring_venue: str | None = None
    highest_scoring_match_title: str | None = None
    highest_match_total_runs: int | None = None
    closest_finish_match_title: str | None = None
    key_journey_note: str | None = None
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    source_label: str = "derived from imported match data"


class TournamentSummaryResponse(BaseModel):
    """Full tournament/season intelligence summary.

    Phase 10S.1: read-only, deterministic. No fabricated stats.
    All unavailable values are explicitly marked as None or labeled.
    """

    group_key: TournamentGroupKey

    # Core counts
    match_count: int = 0
    teams: list[str] = Field(default_factory=list)
    venues: list[str] = Field(default_factory=list)

    # Run/wicket aggregates
    total_runs: int = 0
    total_wickets: int = 0
    highest_team_total: int | None = None
    highest_team_total_by: str | None = None
    lowest_completed_total: int | None = None
    lowest_completed_total_by: str | None = None

    # Match highlights
    closest_match: TournamentMatchHighlight | None = None
    biggest_win_by_runs: TournamentMatchHighlight | None = None
    biggest_win_by_wickets: TournamentMatchHighlight | None = None

    # Player leaders (only when available)
    top_run_scorer: TournamentPlayerLeader | None = None
    top_wicket_taker: TournamentPlayerLeader | None = None

    # Derived standings (labeled as non-official)
    derived_standings: list[DerivedStandingsRow] = Field(default_factory=list)
    standings_label: str = "Derived standings — estimated from imported match results only. Not official."

    # Knockout / finals context
    knockout_context: TournamentKnockoutContext = Field(
        default_factory=TournamentKnockoutContext
    )

    # Data completeness
    data_completeness: TournamentDataCompleteness = Field(
        default_factory=TournamentDataCompleteness
    )

    # Podcast facts
    podcast_facts: TournamentPodcastFacts | None = None

    generated_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))
    note: str = (
        "Deterministic on-demand tournament intelligence derived from imported match data. "
        "Standings and outcomes are estimated — not official. "
        "No live scoring truth is mutated."
    )


class TournamentGroupsResponse(BaseModel):
    """Response for GET /analytics/tournament-intelligence/groups.

    Lists all discoverable tournament/season groups from the current
    match registry. Used to power the tournament selector UI.
    """

    groups: list[TournamentGroupSummary] = Field(default_factory=list)
    total: int = 0
    note: str = (
        "Groups are derived from imported match metadata. "
        "Matches with incomplete classification appear in 'unknown' groups."
    )


# ---------------------------------------------------------------------------
# Team journey schemas
# ---------------------------------------------------------------------------


class TeamJourneyMatch(BaseModel):
    """A single match in a team's tournament journey."""

    match_id: str
    match_title: str
    match_date: str | None = None
    opponent: str | None = None
    venue: str | None = None
    result: str | None = None
    outcome: Literal["win", "loss", "tie", "no_result", "unknown"] = "unknown"
    team_runs: int | None = None
    opponent_runs: int | None = None
    stage_label: str | None = None
    highlight: str | None = None


class TeamJourneySummary(BaseModel):
    """Summary stats for a team's tournament journey."""

    wins: int = 0
    losses: int = 0
    ties: int = 0
    no_results: int = 0
    total_runs_for: int = 0
    total_runs_against: int = 0
    best_win: TeamJourneyMatch | None = None
    worst_defeat: TeamJourneyMatch | None = None
    closest_match: TeamJourneyMatch | None = None
    top_scorer_name: str | None = None
    top_scorer_runs: int | None = None


class TeamJourneyResponse(BaseModel):
    """Team journey within a competition/season.

    Phase 10S.1: team-specific tournament journey view for analyst/podcast use.
    """

    team_name: str
    canonical_team_name: str | None = None
    group_key: TournamentGroupKey
    matches: list[TeamJourneyMatch] = Field(default_factory=list)
    summary: TeamJourneySummary = Field(default_factory=TeamJourneySummary)
    data_completeness: TournamentDataCompleteness = Field(
        default_factory=TournamentDataCompleteness
    )
    note: str = (
        "Team journey derived from imported match data. "
        "Outcomes are inferred from result text where available."
    )
