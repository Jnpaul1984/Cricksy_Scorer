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


class AnalystPlayerAggregate(BaseModel):
    player: str
    role: str = "Unknown"
    innings: int = 0
    matches: int = 0
    runs: int = 0
    strike_rate: float = 0.0
    wickets: int = 0
    economy: float = 0.0


class AnalystPlayersResponse(BaseModel):
    items: list[AnalystPlayerAggregate] = Field(default_factory=list)
    total: int = 0
    data_completeness: str = "metadata_only"


class AnalystDeliveryRow(BaseModel):
    match_id: str
    innings: int | None = None
    team: str | None = None
    over_number: int | None = None
    ball_number: int | None = None
    batter: str | None = None
    bowler: str | None = None
    non_striker: str | None = None
    batter_source_player_id: str | None = None
    bowler_source_player_id: str | None = None
    non_striker_source_player_id: str | None = None
    runs_off_bat: int = 0
    extra_runs: int = 0
    total_runs: int = 0
    extra_type: str | None = None
    wicket: bool = False
    dismissal_type: str | None = None
    player_out: str | None = None
    player_out_source_player_id: str | None = None
    fielders: list[str] = Field(default_factory=list)
    phase: str | None = None
    data_completeness: str = "metadata_only"


class AnalystDeliveriesResponse(BaseModel):
    items: list[AnalystDeliveryRow] = Field(default_factory=list)
    total: int = 0
    data_completeness: str = "metadata_only"


class AnalystRegistryEntry(BaseModel):
    """A single entry in the unified Analyst Match Registry.

    Returned by GET /analytics/registry (Phase 10M).

    Every completed match in the system gets exactly one entry,
    classified by competition, gender, source type, and data completeness.
    Unknown values are always explicit — never silently coerced.
    """

    match_id: str
    match_title: str  # "Team A vs Team B"
    team_a: str
    team_b: str
    canonical_team_a: str | None = None
    canonical_team_b: str | None = None

    competition_name: str | None = None  # raw event_name
    competition_code: str = "unknown"  # CPL_MEN | WCPL | unknown

    season: str | None = None
    season_year: int | None = None

    gender_category: str = "unknown"  # men | women | mixed | unknown
    age_category: str = "unknown"  # senior | youth | school | unknown

    format: str = "unknown"  # T20 | ODI | TEST | custom | unknown

    venue_raw: str | None = None
    venue_canonical: str | None = None

    match_date: str | None = None

    source_type: str = "unknown"
    # historical_import | cricksy_completed_scored | cricksy_live_scored |
    # csv_import | scorecard_import | unknown

    data_completeness: str = "metadata_only"
    # metadata_only | innings_totals | phase_level | delivery_complete

    has_delivery_data: bool = False
    has_phase_data: bool = False
    has_scorecard_data: bool = False

    result: str | None = None  # winner / result text when available
    analyst_ready: bool = False


class AnalystMatchRegistryListResponse(BaseModel):
    """Response model for GET /analytics/registry (Phase 10M).

    Returns all completed matches visible to the authenticated user,
    each classified by competition, gender, source type, and data completeness.
    Also includes count diagnostics for filter UI initialisation.
    """

    entries: list[AnalystRegistryEntry]
    total: int
    diagnostics: dict[str, int] = Field(default_factory=dict)


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
