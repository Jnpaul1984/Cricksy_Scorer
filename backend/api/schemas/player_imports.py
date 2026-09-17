"""Phase 7G School roster-import API contracts."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ImportFileType = Literal["csv", "xlsx"]
ImportClassification = Literal[
    "create_new",
    "duplicate_existing_school_membership",
    "ambiguous_needs_review",
    "invalid",
    "team_assignment_only",
]
ImportResolutionAction = Literal[
    "create_new",
    "use_existing",
    "reactivate_existing",
    "skip",
]


class PlayerImportValues(BaseModel):
    player_name: str | None = None
    student_identifier: str | None = None
    year_group: str | None = None
    team_name: str | None = None


class PlayerImportCandidate(BaseModel):
    school_player_membership_id: str
    player_name: str
    status: Literal["active", "inactive"]


class PlayerImportTeamCandidate(BaseModel):
    team_id: str
    team_name: str


class PlayerImportPreviewRow(BaseModel):
    source_row_number: int
    values: PlayerImportValues
    classification: ImportClassification
    validation_errors: list[str]
    warnings: list[str]
    ambiguity_reason: str | None = None
    resolution_required: bool
    candidate_memberships: list[PlayerImportCandidate]
    resolved_school_player_membership_id: str | None = None
    team_candidates: list[PlayerImportTeamCandidate]
    resolved_team_id: str | None = None


class PlayerImportPreviewResponse(BaseModel):
    import_id: str
    file_type: ImportFileType
    original_filename: str
    content_sha256: str
    row_count: int
    column_mapping: dict[str, str]
    expires_at: dt.datetime
    rows: list[PlayerImportPreviewRow]


class PlayerImportRowResolution(BaseModel):
    source_row_number: int = Field(..., ge=2)
    action: ImportResolutionAction
    school_player_membership_id: str | None = None
    team_id: str | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_action_fields(self) -> PlayerImportRowResolution:
        if self.action in {"use_existing", "reactivate_existing"}:
            if not self.school_player_membership_id:
                raise ValueError("Existing-player actions require school_player_membership_id")
        elif self.school_player_membership_id is not None:
            raise ValueError("school_player_membership_id is not allowed for this action")
        if self.action == "skip" and self.team_id is not None:
            raise ValueError("Skipped rows cannot select a Team")
        return self


class PlayerImportApplyRequest(BaseModel):
    resolutions: list[PlayerImportRowResolution] = Field(default_factory=list, max_length=1000)

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def unique_rows(self) -> PlayerImportApplyRequest:
        rows = [item.source_row_number for item in self.resolutions]
        if len(rows) != len(set(rows)):
            raise ValueError("Each source row may have at most one resolution")
        return self


class PlayerImportRowResult(BaseModel):
    source_row_number: int
    outcome: Literal[
        "created",
        "linked_existing",
        "reactivated",
        "team_assigned",
        "no_op",
        "skipped",
        "failed",
    ]
    school_player_membership_id: str | None = None
    player_profile_id: str | None = None
    team_id: str | None = None
    detail: str


class PlayerImportApplySummary(BaseModel):
    created_players: int = 0
    linked_existing_players: int = 0
    reactivated_memberships: int = 0
    team_assignments_created: int = 0
    team_assignments_reactivated: int = 0
    no_op_rows: int = 0
    skipped_rows: int = 0
    failed_rows: int = 0


class PlayerImportApplyResponse(BaseModel):
    import_id: str
    status: Literal["applied"]
    applied_at: dt.datetime
    summary: PlayerImportApplySummary
    rows: list[PlayerImportRowResult]
