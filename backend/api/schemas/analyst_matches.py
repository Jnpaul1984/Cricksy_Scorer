"""
Pydantic schemas for the Analyst Workspace Match List API.

Response model for:
  GET /analytics/matches

Powers the AnalystWorkspaceView.vue "Matches" tab table.
"""

from datetime import date, datetime

from pydantic import BaseModel


class AnalystMatchListItem(BaseModel):
    """A single match row in the Analyst Workspace matches table."""

    id: str
    date: date
    format: str  # e.g. "T20", "ODI", "TEST", "CUSTOM"
    teams: str  # e.g. "Lions vs Falcons"
    result: str  # e.g. "Lions won by 18 runs"
    run_rate: float  # overall match run rate
    phase_swing: str  # e.g. "+18 in death", "-12 in powerplay"
    status: str
    venue: str | None = None
    match_datetime: datetime | None = None


class AnalystMatchListResponse(BaseModel):
    """Response model for GET /analytics/matches."""

    items: list[AnalystMatchListItem]
    total: int


class AnalystMatchInningsSummary(BaseModel):
    inning_no: int
    team: str | None = None
    runs: int | None = None
    wickets: int | None = None
    overs: float | None = None


class AnalystMatchDetailResponse(BaseModel):
    match_id: str
    status: str
    format: str
    teams: str
    result: str | None = None
    venue: str | None = None
    match_datetime: datetime | None = None
    innings: list[AnalystMatchInningsSummary]
    batting_scorecard: dict[str, object] | None = None
    bowling_scorecard: dict[str, object] | None = None


class AnalystExportDataResponse(BaseModel):
    rows: list[dict[str, object]]
    meta: dict[str, object]
