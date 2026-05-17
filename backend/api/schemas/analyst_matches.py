"""
Pydantic schemas for the Analyst Workspace Match List API.

Response models for:
  GET /analytics/matches
  GET /analytics/matches/{match_id}/registry

Powers the AnalystWorkspaceView.vue "Matches" tab table and the
"Registry & Provenance" detail panel.
"""

from datetime import date, datetime

from typing import Any

from pydantic import BaseModel, Field, field_validator


def _normalize_source_dates(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


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
    event_name: str | None = None
    season: str | None = None
    match_number: int | None = None
    source_dates: list[str] = Field(default_factory=list)
    match_datetime: datetime | None = None
    is_historical: bool = False
    source: str = "live"
    historical_batch_id: str | None = None

    @field_validator("source_dates", mode="before")
    @classmethod
    def validate_source_dates(cls, value: Any) -> list[str]:
        return _normalize_source_dates(value)


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
    event_name: str | None = None
    season: str | None = None
    match_number: int | None = None
    source_dates: list[str] = Field(default_factory=list)
    match_datetime: datetime | None = None
    innings: list[AnalystMatchInningsSummary]
    batting_scorecard: dict[str, object] | None = None
    bowling_scorecard: dict[str, object] | None = None

    @field_validator("source_dates", mode="before")
    @classmethod
    def validate_source_dates(cls, value: Any) -> list[str]:
        return _normalize_source_dates(value)


class AnalystExportDataResponse(BaseModel):
    rows: list[dict[str, Any]]
    meta: dict[str, Any]


class MatchRegistryResponse(BaseModel):
    """Registry metadata, provenance, and training eligibility for a match.

    Returned by GET /analytics/matches/{match_id}/registry.

    Exposes import-batch linkage, source provenance, validation/registration
    status, and training-eligibility gating for the Analyst Workspace
    "Registry & Provenance" panel.

    For non-historical (live) matches:
      - is_historical=False
      - validation_status="not_applicable"
      - registration_status="not_registered"
      - training_eligible=False

    For historical imports without a traceable batch record:
      - validation_status="unknown"
      - registration_status="not_registered"
      - training_eligible=False
      - blocking_reason="batch_record_not_found"
    """

    match_id: str
    is_historical: bool

    # Competition context from historical metadata
    competition: str | None = None  # event_name from historical import
    competition_type: str | None = None
    competition_name: str | None = None
    match_format: str | None = None
    tournament_name: str | None = None
    tournament_round: str | None = None
    season: str | None = None
    venue: str | None = None
    venue_context: dict[str, Any] | None = None
    teams: str | None = None
    match_number: int | None = None
    player_count: int = 0
    innings_count: int = 0
    has_deliveries: bool = False
    roster_snapshot_available: bool = False

    # Import batch / source provenance
    import_batch_id: str | None = None
    source_filename: str | None = None
    source_format: str | None = None
    source_schema: str | None = None
    source_schema_version: str | None = None
    adapter_id: str | None = None
    adapter_version: str | None = None
    source_type: str = "json"
    imported_at: datetime | None = None

    # Validation / registration / training eligibility
    validation_status: str = Field(
        ...,
        description=(
            "Structural validation outcome: 'valid', 'invalid', 'unsupported', "
            "'not_applicable' (live match), or 'unknown' (batch not found)."
        ),
    )
    registration_status: str = Field(
        ...,
        description=(
            "'registered' when batch is finalized, valid, and error-free; "
            "'not_registered' otherwise."
        ),
    )
    training_eligible: bool = Field(
        ...,
        description=(
            "True only when the import is finalized, registered (valid, 0 errors), "
            "and the game row was created.  False for all live matches and any import "
            "that fails validation or registration checks."
        ),
    )
    blocking_reason: str | None = Field(
        default=None,
        description=(
            "Machine-readable reason why training_eligible is False, "
            "e.g. 'batch_not_finalized', 'has_errors', 'not_a_historical_import'. "
            "None when training_eligible=True."
        ),
    )
