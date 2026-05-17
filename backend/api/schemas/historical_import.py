from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field


class HistoricalImportIssue(BaseModel):
    code: str
    message: str
    severity: Literal["error", "warning"]
    path: str | None = None


class HistoricalImportDetectedSections(BaseModel):
    teams: bool
    players: bool
    innings: bool
    deliveries: bool
    metadata: bool


class HistoricalImportMetadataPreview(BaseModel):
    match_type: str | None = None
    venue: str | None = None
    date: str | None = None
    result: str | None = None
    event_name: str | None = None
    season: str | None = None
    match_number: int | None = None
    source_dates: list[str] = Field(default_factory=list)


class HistoricalImportSchemaClassification(BaseModel):
    source_schema_category: Literal[
        "cricksy_internal_json",
        "cricsheet_style_json",
        "franchise_tournament_json",
        "international_match_json",
        "domestic_club_match_json",
        "school_academy_match_json",
        "unknown_unsupported_json",
    ]
    source_schema: str
    source_schema_version: str | None = None
    adapter_id: str
    adapter_version: str


class HistoricalImportCompetitionContext(BaseModel):
    competition_type: Literal[
        "franchise",
        "club",
        "international",
        "domestic",
        "school",
        "academy",
        "unknown",
    ] = "unknown"
    competition_name: str | None = None
    competition_stage: str | None = None
    season: str | None = None
    match_format: str = "unknown"
    tournament_name: str | None = None
    tournament_round: str | None = None
    value_status: dict[str, Literal["source", "inferred", "missing", "unknown"]] = Field(
        default_factory=dict
    )


class HistoricalImportVenueContext(BaseModel):
    venue_name: str | None = None
    city: str | None = None
    country: str | None = None
    ground_code: str | None = None
    source_venue_raw: str | None = None
    venue_resolution_status: Literal["resolved", "unresolved", "unknown"] = "unknown"


class HistoricalImportRosterTeamSnapshot(BaseModel):
    team_name: str
    playing_xi: list[str] = Field(default_factory=list)
    named_squad: list[str] = Field(default_factory=list)
    substitutes: list[str] = Field(default_factory=list)
    unresolved_entries: list[str] = Field(default_factory=list)
    mapping_confidence: Literal["high", "medium", "low", "unknown"] = "unknown"


class HistoricalImportCanonicalPreview(BaseModel):
    match_metadata: dict[str, object] = Field(default_factory=dict)
    competition_context: HistoricalImportCompetitionContext
    tournament_season_context: dict[str, object] = Field(default_factory=dict)
    venue_context: HistoricalImportVenueContext
    team_context: dict[str, object] = Field(default_factory=dict)
    squad_roster_snapshot: list[HistoricalImportRosterTeamSnapshot] = Field(default_factory=list)
    player_identity_mapping: dict[str, object] = Field(default_factory=dict)
    innings_summaries: list[dict[str, object]] = Field(default_factory=list)
    delivery_events: dict[str, object] = Field(default_factory=dict)
    result_metadata: dict[str, object] = Field(default_factory=dict)
    source_provenance: dict[str, object] = Field(default_factory=dict)
    validation_report: dict[str, object] = Field(default_factory=dict)


class HistoricalImportInningsPreview(BaseModel):
    inning_no: int
    team: str | None = None
    deliveries: int = 0
    legal_balls: int | None = None
    runs: int | None = None
    wickets: int | None = None
    overs: float | None = None


class HistoricalImportDuplicatePreview(BaseModel):
    source_hash_sha256: str
    probable_duplicate: Literal["unknown", "likely_duplicate", "not_duplicate"] = "unknown"
    tracking_available: bool = False
    duplicate_batch_id: str | None = None
    semantic_key: str | None = None
    semantic_duplicate: bool = False
    message: str


class HistoricalImportDryRunResponse(BaseModel):
    status: Literal["valid", "invalid", "unsupported"]
    detected_format: str
    top_level_keys: list[str] = Field(default_factory=list)
    detected_sections: HistoricalImportDetectedSections
    metadata_preview: HistoricalImportMetadataPreview
    schema_classification: HistoricalImportSchemaClassification | None = None
    canonical_preview: HistoricalImportCanonicalPreview | None = None
    teams_preview: list[str] = Field(default_factory=list)
    innings_count: int = 0
    delivery_count: int = 0
    player_names_found: list[str] = Field(default_factory=list)
    innings_preview: list[HistoricalImportInningsPreview] = Field(default_factory=list)
    warnings: list[HistoricalImportIssue] = Field(default_factory=list)
    errors: list[HistoricalImportIssue] = Field(default_factory=list)
    duplicate_detection: HistoricalImportDuplicatePreview
    no_persistence: bool = True
    record_id: str | None = None


class HistoricalImportBatchRecord(BaseModel):
    """API response shape for a persisted historical import batch record."""

    id: str
    owner_user_id: str | None = None
    owner_org_id: str | None = None
    source_filename: str | None = None
    source_format: str
    source_hash_sha256: str
    semantic_key: str | None = None
    status: str
    error_count: int
    warning_count: int
    innings_count: int
    delivery_count: int
    is_finalized: bool
    applied_game_id: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime


# ---------------------------------------------------------------------------
# Phase 10H - Venue intelligence access schemas
# ---------------------------------------------------------------------------


class HistoricalVenueIntelligenceRecord(BaseModel):
    id: str
    canonical_name: str
    short_name: str | None = None
    alternate_names: list[str] = Field(default_factory=list)
    city: str | None = None
    region: str | None = None
    country: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    venue_type: str | None = None
    indoor_outdoor: str | None = None
    verification_status: str
    confidence_score: float | None = None
    source_type: str | None = None
    created_from_import: bool = False
    notes: str | None = None
    provenance_references: list[dict[str, object]] = Field(default_factory=list)
    created_at: dt.datetime
    updated_at: dt.datetime


class HistoricalVenueUnresolvedRecord(BaseModel):
    id: str
    decision_id: str | None = None
    raw_imported_value: str
    normalized_raw_value: str
    source_schema: str | None = None
    source_system: str | None = None
    queue_state: str
    reason: str
    review_required: bool
    provenance_references: list[dict[str, object]] = Field(default_factory=list)
    created_at: dt.datetime
    last_seen: dt.datetime
    resolved_at: dt.datetime | None = None


class HistoricalVenueResolutionSnapshot(BaseModel):
    id: str
    batch_id: str | None = None
    game_id: str | None = None
    raw_imported_value: str
    normalized_raw_value: str
    canonical_venue_id: str | None = None
    resolution_state: str
    matched_by: str | None = None
    confidence_score: float | None = None
    unresolved_reason: str | None = None
    review_required: bool
    source_schema: str | None = None
    source_system: str | None = None
    competition_name: str | None = None
    season: str | None = None
    provenance_references: list[dict[str, object]] = Field(default_factory=list)
    resolution_snapshot: dict[str, object] = Field(default_factory=dict)
    created_at: dt.datetime
    updated_at: dt.datetime


class HistoricalVenueUsageRecord(BaseModel):
    id: str
    canonical_venue_id: str
    competition_name: str | None = None
    season: str | None = None
    source_schema: str | None = None
    source_system: str | None = None
    matches_count: int
    game_references: list[str] = Field(default_factory=list)
    provenance_references: list[dict[str, object]] = Field(default_factory=list)
    review_required: bool
    created_at: dt.datetime
    updated_at: dt.datetime


class HistoricalVenueAliasRecord(BaseModel):
    id: int
    venue_id: str
    alias_name: str
    normalized_alias: str
    source_schema: str | None = None
    source_system: str | None = None
    confidence_score: float | None = None
    provenance_reference: dict[str, object] = Field(default_factory=dict)
    created_at: dt.datetime
    updated_at: dt.datetime


# ---------------------------------------------------------------------------
# Phase 5L - Bulk ZIP historical JSON schemas
# ---------------------------------------------------------------------------


class HistoricalImportBulkZipFilePreview(BaseModel):
    """Per-file dry-run result inside a ZIP bulk upload."""

    file_name: str
    status: Literal["valid", "invalid", "duplicate", "unsupported", "error"]
    message: str = Field(
        ...,
        description=(
            "Human-readable per-file outcome details. "
            "Examples: invalid JSON reason, duplicate explanation, or valid preview confirmation."
        ),
    )
    duplicate_within_zip: bool = False
    duplicate_batch_id: str | None = None
    semantic_duplicate: bool = False
    detected_format: str | None = None
    warnings: list[HistoricalImportIssue] = Field(default_factory=list)
    errors: list[HistoricalImportIssue] = Field(default_factory=list)
    dry_run_preview: HistoricalImportDryRunResponse | None = None


class HistoricalImportBulkZipDryRunResponse(BaseModel):
    """Dry-run response for a ZIP containing multiple historical JSON files."""

    status: Literal["preview_ready", "invalid_zip"]
    source_filename: str | None = None
    total_entries: int = 0
    files_scanned: int = 0
    json_entries: int = 0
    non_json_entries: int = 0
    metadata_only_intake_required: bool = False
    metadata_only_pending_count: int = 0
    intake_status: str = "scanned"
    cost_control_message: str | None = None
    full_import_deferred: bool = False
    selected_apply_requires_confirm: bool = True
    max_files: int
    max_file_size_bytes: int
    max_total_uncompressed_bytes: int
    max_total_compressed_bytes: int
    summary: dict[str, int] = Field(default_factory=dict)
    files: list[HistoricalImportBulkZipFilePreview] = Field(default_factory=list)


class HistoricalImportBulkZipApplyFileResult(BaseModel):
    """Per-file result for selected apply from a ZIP bulk upload."""

    file_name: str
    status: Literal["applied", "metadata_extracted", "skipped", "error"]
    message: str
    batch_id: str | None = None
    applied_game_id: str | None = None


class HistoricalImportBulkZipApplyResponse(BaseModel):
    """Apply response for selected files from ZIP bulk upload."""

    status: Literal["applied", "metadata_recorded", "partial", "failed"]
    source_filename: str | None = None
    selected_count: int = 0
    applied_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    metadata_only_count: int = 0
    full_import_deferred: bool = False
    selected_apply_requires_confirm: bool = True
    results: list[HistoricalImportBulkZipApplyFileResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 7 - OCR/PDF/Image review-only candidate flow schemas
# ---------------------------------------------------------------------------


HistoricalOcrReviewStatus = Literal[
    "uploaded",
    "extracted",
    "needs_review",
    "reviewed",
    "rejected",
    "ready_for_dry_run",
    "dry_run_failed",
    "dry_run_passed",
    "applied_via_structured_import_only",
]


class HistoricalOcrSourceDocument(BaseModel):
    filename: str
    content_type: str
    size_bytes: int
    storage: dict[str, str]


class HistoricalOcrExtractionMetadata(BaseModel):
    method: str
    confidence: float | None = None
    uncertainty_flags: list[str] = Field(default_factory=list)
    ocr_text: str | None = None
    warnings: list[str] = Field(default_factory=list)
    non_authoritative_notice: str = (
        "OCR/AI extraction is non-authoritative and must be reviewed before historical import."
    )


class HistoricalOcrReviewCandidateResponse(BaseModel):
    candidate_id: str
    batch_id: str
    status: HistoricalOcrReviewStatus
    status_history: list[HistoricalOcrReviewStatus] = Field(default_factory=list)
    source_document: HistoricalOcrSourceDocument
    extraction: HistoricalOcrExtractionMetadata
    candidate_json: dict | None = None
    reviewed_json: dict | None = None
    reviewer_notes: str | None = None
    rejection_reason: str | None = None
    validation_errors: list[HistoricalImportIssue] = Field(default_factory=list)
    dry_run_result: HistoricalImportDryRunResponse | None = None
    dry_run_batch_id: str | None = None


class HistoricalOcrReviewUpdateRequest(BaseModel):
    reviewed_json: dict
    reviewer_notes: str | None = None
    uncertainty_flags: list[str] = Field(default_factory=list)


class HistoricalOcrRejectRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class HistoricalOcrDryRunRequest(BaseModel):
    record_preview: bool = True


class HistoricalOcrDryRunResponse(BaseModel):
    candidate_id: str
    status: HistoricalOcrReviewStatus
    dry_run_result: HistoricalImportDryRunResponse
    dry_run_batch_id: str | None = None
    message: str


# ---------------------------------------------------------------------------
# Phase 5D - Apply schemas
# ---------------------------------------------------------------------------


class HistoricalImportApplyRequest(BaseModel):
    """Request body for the Phase 5D apply endpoint.

    ``confirm`` must be explicitly ``True``; any other value is rejected.
    This prevents accidental writes.
    """

    confirm: bool = Field(
        ...,
        description=(
            "Must be true to proceed with the apply. Safeguard against accidental writes."
        ),
    )


class HistoricalImportApplyResponse(BaseModel):
    """Response body returned by the Phase 5D apply endpoint."""

    batch_id: str
    applied_game_id: str | None = None
    records_created: int = 0
    status: Literal["applied", "skipped", "failed"]
    warnings: list[str] = Field(default_factory=list)
    rollback_info: str = Field(
        default="",
        description=(
            "Instructions for rollback, including the Phase 5E rollback endpoint "
            "and safety constraints."
        ),
    )


class HistoricalImportRollbackRequest(BaseModel):
    """Request body for the Phase 5E rollback endpoint."""

    confirm: bool = Field(
        ...,
        description=(
            "Must be true to proceed with rollback. Safeguard against accidental deletions."
        ),
    )


class HistoricalImportRollbackResponse(BaseModel):
    """Response body returned by the Phase 5E rollback endpoint."""

    batch_id: str
    rolled_back_game_id: str | None = None
    records_deleted: int = 0
    status: Literal["rolled_back"]
    warnings: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Phase 5F - Apply deliveries schemas
# ---------------------------------------------------------------------------


class HistoricalImportTotalsValidation(BaseModel):
    """Per-innings totals reconciliation result."""

    inning_no: int
    team: str | None = None
    derived_runs: int
    expected_runs: int | None = None
    derived_wickets: int
    expected_wickets: int | None = None
    legal_balls: int
    status: Literal["ok", "warning", "blocked"]
    notes: str = ""


class HistoricalImportApplyDeliveriesResponse(BaseModel):
    """Response body returned by the Phase 5F apply-deliveries endpoint."""

    batch_id: str
    applied_game_id: str
    deliveries_imported: int
    innings_processed: int
    status: Literal["deliveries_applied", "already_applied", "failed"]
    totals_validation: list[HistoricalImportTotalsValidation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rollback_info: str = Field(
        default="",
        description=(
            "Instructions for rollback, including the Phase 5E rollback endpoint. "
            "Rolling back the batch will delete the entire historical game record "
            "including any imported deliveries."
        ),
    )


# ---------------------------------------------------------------------------
# Phase 5K - Metadata repair schemas
# ---------------------------------------------------------------------------


class HistoricalImportRepairRequest(BaseModel):
    """Request body for the Phase 5K metadata repair endpoint.

    ``confirm`` must be explicitly ``True``; any other value is rejected.
    """

    confirm: bool = Field(
        ...,
        description=(
            "Must be true to proceed with the repair. Safeguard against accidental writes."
        ),
    )


class HistoricalImportRepairResponse(BaseModel):
    """Response body returned by the Phase 5K repair-metadata endpoint."""

    batch_id: str
    game_id: str | None = None
    status: Literal["repaired", "already_complete", "refused"]
    fields_added: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    detail: str = Field(
        default="",
        description="Human-readable summary of the repair outcome.",
    )


class HistoricalImportTrainingStatus(BaseModel):
    """Training dataset readiness status for a historical import batch.

    Computed from existing batch metadata — no DB migration required.
    Raw source JSON is NOT retained in Phase 5I (deferred to a later phase).
    Training eligibility is determined by:
      - batch is finalized (apply was called)
      - a game record was created (applied_game_id is set)
      - batch status is 'valid' (no structural errors)
      - error_count is 0

    If all conditions are met, training_eligible=True and the batch metadata
    can be used to register the import in a future ML dataset registry.
    """

    batch_id: str
    source_format: str
    source_hash_sha256: str
    source_filename: str | None = None
    semantic_key: str | None = None
    applied_game_id: str | None = None
    imported_at: dt.datetime
    innings_count: int
    delivery_count: int
    training_eligible: bool
    exclusion_reason: str | None = Field(
        default=None,
        description=(
            "Human-readable reason why the batch is not training-eligible. "
            "None when training_eligible=True."
        ),
    )
    raw_json_retained: bool = Field(
        default=False,
        description=(
            "Whether the raw source JSON bytes are stored server-side. "
            "False in Phase 5I — raw retention is deferred to a later phase."
        ),
    )
    training_registry_phase: str = Field(
        default="deferred",
        description=(
            "Phase that will implement the full ML dataset registry/export. 'deferred' in Phase 5I."
        ),
    )
