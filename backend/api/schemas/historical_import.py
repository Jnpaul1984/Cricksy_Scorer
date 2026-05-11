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


class HistoricalImportInningsPreview(BaseModel):
    inning_no: int
    team: str | None = None
    deliveries: int = 0
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
            "Must be true to proceed with the apply. "
            "Safeguard against accidental writes."
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
            "Must be true to proceed with rollback. "
            "Safeguard against accidental deletions."
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
