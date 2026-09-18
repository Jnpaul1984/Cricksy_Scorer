"""Organization-scoped deterministic School Free statistics contracts."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel


class SchoolPlayerStatistics(BaseModel):
    player_profile_id: str
    player_name: str
    roster_status: Literal["active", "inactive"]
    matches: int
    innings: int
    runs: int
    highest_score: int
    batting_average: float | None
    balls_faced: int
    strike_rate: float
    fours: int
    sixes: int
    bowling_innings: int
    balls_bowled: int
    overs: str
    runs_conceded: int
    wickets: int
    bowling_average: float | None
    economy: float | None
    best_bowling: str | None


class SchoolTeamStatistics(BaseModel):
    team_id: str
    team_name: str
    team_status: Literal["active", "archived"]
    matches: int
    wins: int
    losses: int
    ties: int
    draws: int
    no_results: int
    runs_scored: int
    runs_conceded: int
    wickets_taken: int
    wickets_lost: int


class SchoolMatchResult(BaseModel):
    game_id: str
    team_a_id: str
    team_a_name: str
    team_b_id: str
    team_b_name: str
    status: str
    result: str | None
    publication_state: Literal["private", "published_live", "published_final"]
    current_inning: int
    team_a_runs: int
    team_a_wickets: int
    team_b_runs: int
    team_b_wickets: int
    public_scorecard_available: bool


class SchoolFixtureSummary(BaseModel):
    fixture_id: str
    competition_id: str
    competition_name: str
    team_a_id: str
    team_a_name: str
    team_b_id: str
    team_b_name: str
    match_number: int | None
    venue: str | None
    scheduled_date: dt.datetime | None
    fixture_status: str
    game_id: str | None
    game_status: str | None
    result: str | None
    publication_state: Literal["private", "published_live", "published_final"] | None
    public_scorecard_available: bool
