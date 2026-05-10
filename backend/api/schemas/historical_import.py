from __future__ import annotations

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
