"""Safe aggregate-only API contract for the private Team Performance pilot."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel


class TeamPerformanceBatting(BaseModel):
    team_runs: int
    bat_runs: int
    wides: int
    no_ball_penalties: int
    byes: int
    leg_byes: int
    wickets_lost: int
    legal_balls: int
    legal_dots: int
    fours: int
    sixes: int
    run_rate: float | None
    legal_dot_percentage: float | None
    runs_per_wicket: float | None


class TeamPerformanceBowling(BaseModel):
    opposition_team_runs: int
    bowler_charged_runs: int
    wides: int
    no_ball_penalties: int
    byes: int
    leg_byes: int
    team_wickets: int
    bowler_credited_wickets: int
    legal_balls: int
    legal_dots: int
    team_concession_rate: float | None
    bowling_economy: float | None
    legal_dot_percentage: float | None


class TeamPerformanceCoverage(BaseModel):
    status: Literal[
        "no_eligible_games",
        "no_usable_ledger",
        "usable_with_exclusions",
        "usable_recorded_data",
    ]
    eligible_games: int
    included_games: int
    usable_batting_innings: int
    usable_bowling_innings: int
    used_delivery_rows: int
    observed_delivery_rows: int
    excluded_games: int
    excluded_innings: int
    cohort_excluded_games: int
    cohort_exclusion_counts: dict[str, int]
    no_ledger_games: int
    invalid_data_games: int
    invalid_data_innings: int
    warning_counts: dict[str, int]


class OrganizationTeamPerformanceResponse(BaseModel):
    organization_id: str
    team_id: str
    overs_limit: int
    completeness: Literal["unknown"] = "unknown"
    batting: TeamPerformanceBatting
    bowling: TeamPerformanceBowling
    coverage: TeamPerformanceCoverage


class OrganizationTeamPerformanceTeamOption(BaseModel):
    id: str
    name: str
    status: Literal["active", "archived"]


class OrganizationTeamPerformanceReadiness(BaseModel):
    organization_id: str
    team_id: str
    as_of_date: dt.date
    required_history: Literal[5] = 5
    usable_prior_match_count: int
    remaining_match_count: int
    state: Literal["ready", "not_ready", "data_unavailable"]
    usable_batting_match_count: int
    usable_bowling_match_count: int
    exclusion_counts: dict[str, int]


class TeamRecentFormMatch(BaseModel):
    ordinal: int
    played_date: dt.date
    batting: TeamPerformanceBatting
    bowling: TeamPerformanceBowling
    recorded_delivery_rows: int


class OrganizationTeamRecentForm(BaseModel):
    readiness: OrganizationTeamPerformanceReadiness
    sample_size: int
    completeness: Literal["unknown"] = "unknown"
    recorded_delivery_rows: int
    batting: TeamPerformanceBatting | None
    bowling: TeamPerformanceBowling | None
    matches: list[TeamRecentFormMatch]


class TeamPhaseBandResponse(BaseModel):
    name: Literal["opening", "middle", "closing"]
    start_over: int
    end_over: int
    batting_observed_matches: int
    bowling_observed_matches: int
    batting_unavailable_matches: int
    bowling_unavailable_matches: int
    batting_recorded_rows: int
    bowling_recorded_rows: int
    batting: TeamPerformanceBatting | None
    bowling: TeamPerformanceBowling | None


class OrganizationTeamPhaseAnalysis(BaseModel):
    readiness: OrganizationTeamPerformanceReadiness
    sample_size: int
    completeness: Literal["unknown"] = "unknown"
    phase_unavailable_matches: int
    phases: list[TeamPhaseBandResponse]


class TeamCoachReportObservation(BaseModel):
    subject: Literal["batting", "bowling"]
    earlier_band: Literal["opening", "middle", "closing"]
    later_band: Literal["opening", "middle", "closing"]
    earlier_rate: float
    later_rate: float
    earlier_runs: int
    later_runs: int
    earlier_legal_balls: int
    later_legal_balls: int
    observed_matches: int
    unit: Literal["runs_per_six_legal_balls"]
    evidence_section: Literal["phases"]


class OrganizationTeamCoachReport(BaseModel):
    readiness: OrganizationTeamPerformanceReadiness
    sample_size: int
    completeness: Literal["unknown"] = "unknown"
    recorded_delivery_rows: int
    batting: TeamPerformanceBatting | None
    bowling: TeamPerformanceBowling | None
    matches: list[TeamRecentFormMatch]
    phase_unavailable_matches: int
    phases: list[TeamPhaseBandResponse]
    observations: list[TeamCoachReportObservation]
