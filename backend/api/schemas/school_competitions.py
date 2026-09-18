"""Narrow organization-scoped contracts for School competitions and publication."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

CompetitionStatus = Literal["upcoming", "ongoing", "completed"]
FixtureStatus = Literal["scheduled", "in_progress", "completed", "cancelled"]
PublicationState = Literal["private", "published_live", "published_final"]


class SchoolCompetitionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    tournament_type: Literal["league", "knockout", "round-robin"] = "league"
    start_date: dt.datetime | None = None
    end_date: dt.datetime | None = None
    status: CompetitionStatus = "upcoming"


class SchoolCompetitionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    tournament_type: Literal["league", "knockout", "round-robin"] | None = None
    start_date: dt.datetime | None = None
    end_date: dt.datetime | None = None
    status: CompetitionStatus | None = None


class SchoolCompetitionResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None
    tournament_type: str
    start_date: dt.datetime | None
    end_date: dt.datetime | None
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class SchoolCompetitionTeamAdd(BaseModel):
    team_id: str = Field(min_length=1)


class SchoolCompetitionTeamResponse(BaseModel):
    id: int
    tournament_id: str
    team_id: str
    team_name: str

    model_config = ConfigDict(from_attributes=True)


class SchoolFixtureCreate(BaseModel):
    team_a_id: str = Field(min_length=1)
    team_b_id: str = Field(min_length=1)
    match_number: int | None = Field(default=None, ge=1)
    venue: str | None = Field(default=None, max_length=255)
    scheduled_date: dt.datetime | None = None
    status: FixtureStatus = "scheduled"

    @model_validator(mode="after")
    def distinct_teams(self) -> SchoolFixtureCreate:
        if self.team_a_id == self.team_b_id:
            raise ValueError("Fixture teams must be different")
        return self


class SchoolFixtureUpdate(BaseModel):
    match_number: int | None = Field(default=None, ge=1)
    venue: str | None = Field(default=None, max_length=255)
    scheduled_date: dt.datetime | None = None
    status: FixtureStatus | None = None


class SchoolFixtureResponse(BaseModel):
    id: str
    tournament_id: str
    team_a_id: str
    team_b_id: str
    team_a_name: str
    team_b_name: str
    match_number: int | None
    venue: str | None
    scheduled_date: dt.datetime | None
    game_id: str | None
    status: str
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class SchoolFixtureGameLink(BaseModel):
    game_id: str = Field(min_length=1)


class SchoolStandingEntry(BaseModel):
    team_id: str
    team_name: str
    matches_played: int
    matches_won: int
    matches_lost: int
    matches_drawn: int
    points: int


class SchoolStandingsResponse(BaseModel):
    competition_id: str
    entries: list[SchoolStandingEntry]
    unresolved_completed_games: int


class SchoolPublicationUpdate(BaseModel):
    publication_state: PublicationState


class SchoolPublicationResponse(BaseModel):
    game_id: str
    organization_id: str
    publication_state: PublicationState


class PublicPlayer(BaseModel):
    name: str


class PublicTeam(BaseModel):
    name: str
    players: list[PublicPlayer]


class PublicScorecardEntry(BaseModel):
    player_name: str
    runs: int | None = None
    balls_faced: int | None = None
    fours: int | None = None
    sixes: int | None = None
    is_out: bool | None = None
    how_out: str | None = None
    overs_bowled: float | int | None = None
    runs_conceded: int | None = None
    wickets_taken: int | None = None


class PublicSchoolScorecard(BaseModel):
    game_id: str
    publication_state: Literal["published_live", "published_final"]
    status: str
    team_a: PublicTeam
    team_b: PublicTeam
    match_type: str
    overs_limit: int | None
    days_limit: int | None
    overs_per_day: int | None
    toss_winner_team: str | None
    decision: str | None
    batting_team_name: str | None
    bowling_team_name: str | None
    total_runs: int
    total_wickets: int
    overs_completed: int
    balls_this_over: int
    current_inning: int
    result: str | None
    batting_scorecard: list[PublicScorecardEntry]
    bowling_scorecard: list[PublicScorecardEntry]
