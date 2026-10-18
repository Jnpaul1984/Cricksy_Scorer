"""Safe aggregate-only API contract for the private Team Performance pilot."""

from __future__ import annotations

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
