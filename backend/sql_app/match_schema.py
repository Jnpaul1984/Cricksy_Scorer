"""Match schema models based on complete match data structure."""

from typing import Any
from pydantic import BaseModel
from enum import Enum


class DismissalType(str, Enum):
    """Dismissal types in cricket."""

    CAUGHT = "caught"
    LBW = "lbw"
    BOWLED = "bowled"


class Player(BaseModel):
    """Player information."""

    id: str
    name: str


class Team(BaseModel):
    """Team with list of players."""

    name: str
    players: list[Player]


class Delivery(BaseModel):
    """Single delivery details."""

    over_number: int
    ball_number: int
    bowler_id: str
    striker_id: str
    non_striker_id: str
    runs_off_bat: int
    extra_type: str | None
    extra_runs: int
    runs_scored: int
    is_extra: bool
    is_wicket: bool
    dismissal_type: DismissalType | None
    dismissed_player_id: str | None
    commentary: str | None
    fielder_id: str | None
    shot_map: Any | None


class Innings(BaseModel):
    """Innings with deliveries."""

    innings_number: int
    batting_team: str
    bowling_team: str
    deliveries: list[Delivery]


class BattingEntry(BaseModel):
    """Batting scorecard entry."""

    player_id: str
    player_name: str
    runs: int
    balls_faced: int
    is_out: bool


class BowlingEntry(BaseModel):
    """Bowling scorecard entry."""

    player_id: str
    player_name: str
    overs_bowled: float
    runs_conceded: int
    wickets_taken: int


class InningsSummary(BaseModel):
    """Summary of an innings."""

    runs: int
    wickets: int
    overs: float
    balls: int


class Result(BaseModel):
    """Match result information."""

    winner_team_id: str | None
    winner_team_name: str
    method: str
    margin: int
    result_text: str
    completed_at: str | None


class Match(BaseModel):
    """Complete match state with all details."""

    id: str
    team_a: Team
    team_b: Team
    match_type: str
    overs_limit: int
    days_limit: int | None
    dls_enabled: bool
    interruptions: list[Any]
    toss_winner_team: str
    decision: str
    batting_team_name: str
    bowling_team_name: str
    status: str
    current_inning: int
    total_runs: int
    total_wickets: int
    overs_completed: int
    balls_this_over: int
    current_striker_id: str | None
    current_non_striker_id: str | None
    current_bowler_id: str | None
    first_inning_summary: InningsSummary
    target: int
    result: Result
    is_game_over: bool
    completed_at: str | None
    team_a_captain_id: str | None
    team_a_keeper_id: str | None
    team_b_captain_id: str | None
    team_b_keeper_id: str | None
    innings: list[Innings]
    batting_scorecard: dict[str, BattingEntry]
    bowling_scorecard: dict[str, BowlingEntry]
