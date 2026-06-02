"""Phase 10T — CPL Current-Season Roster: Pydantic schemas.

Defines request/response models for:
- CPL current-season team registry
- CPL current-season player registry
- Roster import preview/apply (CSV or JSON)

All roster data is manually maintained and labeled as user-maintained.
No historical import behavior is touched.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field

CplRosterStatusType = Literal["active", "inactive", "unknown"]


# ---------------------------------------------------------------------------
# Team registry
# ---------------------------------------------------------------------------


class CplTeamCreate(BaseModel):
    """Request body to register a new CPL team for a season."""

    competition_code: str = "CPL_MEN"
    season: str
    team_name: str = Field(..., min_length=1, max_length=255)
    team_short_name: str | None = None
    home_ground: str | None = None
    source_note: str | None = None


class CplTeamResponse(BaseModel):
    """Response schema for a registered CPL team."""

    id: str
    competition_code: str
    season: str
    team_name: str
    normalized_team_name: str
    team_short_name: str | None = None
    home_ground: str | None = None
    source_note: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True, "use_enum_values": True}


class CplTeamListResponse(BaseModel):
    """List of registered CPL teams."""

    teams: list[CplTeamResponse] = Field(default_factory=list)
    total: int = 0
    trust_note: str = (
        "Team registry is user-maintained. Review before use in podcast output."
    )


# ---------------------------------------------------------------------------
# Player registry
# ---------------------------------------------------------------------------


class CplPlayerCreate(BaseModel):
    """Request body to register a new CPL player for a season."""

    competition_code: str = "CPL_MEN"
    season: str
    player_name: str = Field(..., min_length=1, max_length=255)
    display_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    team_name: str | None = None
    role: str | None = None
    batting_style: str | None = None
    bowling_style: str | None = None
    status: CplRosterStatusType = "active"
    source_note: str | None = None


class CplPlayerUpdate(BaseModel):
    """Request body to update an existing CPL player record."""

    display_name: str | None = None
    aliases: list[str] | None = None
    team_name: str | None = None
    role: str | None = None
    batting_style: str | None = None
    bowling_style: str | None = None
    status: CplRosterStatusType | None = None
    source_note: str | None = None


class CplPlayerResponse(BaseModel):
    """Response schema for a registered CPL player."""

    id: str
    competition_code: str
    season: str
    player_name: str
    normalized_player_name: str
    display_name: str | None = None
    aliases: list[str] = Field(default_factory=list)
    team_name: str | None = None
    role: str | None = None
    batting_style: str | None = None
    bowling_style: str | None = None
    status: str
    is_returning: bool = False
    prior_season: str | None = None
    source_note: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True, "use_enum_values": True}


class CplPlayerListResponse(BaseModel):
    """List of registered CPL players for a season (optionally filtered by team)."""

    players: list[CplPlayerResponse] = Field(default_factory=list)
    total: int = 0
    returning_count: int = 0
    new_count: int = 0
    trust_note: str = (
        "Roster data is user-maintained and should be reviewed before publication. "
        "Player statistics are not available for current-season roster entries unless "
        "historical match data exists."
    )


# ---------------------------------------------------------------------------
# Roster import (CSV / JSON)
# ---------------------------------------------------------------------------

# Preferred CSV columns:
# competition,season,team,player,role,batting_style,bowling_style,status,source_note


class RosterImportRow(BaseModel):
    """One row from a CSV/JSON roster import payload."""

    competition: str = "CPL_MEN"
    season: str
    team: str | None = None
    player: str
    role: str | None = None
    batting_style: str | None = None
    bowling_style: str | None = None
    status: CplRosterStatusType = "active"
    source_note: str | None = None


class RosterImportPreviewPlayer(BaseModel):
    """Preview details for a single player row during roster import."""

    row_index: int
    player_name: str
    team_name: str | None = None
    status: CplRosterStatusType
    is_new: bool
    is_duplicate: bool
    is_returning: bool
    prior_season: str | None = None
    warning: str | None = None


class RosterImportPreviewTeam(BaseModel):
    """Preview details for a team encountered during roster import."""

    team_name: str
    is_new: bool
    is_existing_match: bool


class RosterImportPreviewResponse(BaseModel):
    """Preview result of a roster import (before apply)."""

    competition_code: str
    season: str
    total_rows: int
    new_teams: list[RosterImportPreviewTeam] = Field(default_factory=list)
    existing_teams_matched: list[str] = Field(default_factory=list)
    new_players: list[RosterImportPreviewPlayer] = Field(default_factory=list)
    existing_players_matched: list[str] = Field(default_factory=list)
    duplicates: list[RosterImportPreviewPlayer] = Field(default_factory=list)
    returning_players: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    can_apply: bool = True
    trust_note: str = (
        "Preview only — no data has been changed. "
        "Review warnings and blockers before applying."
    )


class RosterImportApplyRequest(BaseModel):
    """Request body to apply a previewed roster import.

    Must include the same rows as the preview; apply is idempotent
    and will match existing records rather than creating duplicates.
    """

    rows: list[RosterImportRow]
    competition_code: str = "CPL_MEN"
    season: str
    confirm: bool = False  # Must be True to apply


class RosterImportApplyResponse(BaseModel):
    """Result after applying a roster import."""

    competition_code: str
    season: str
    teams_created: int = 0
    teams_matched: int = 0
    players_created: int = 0
    players_updated: int = 0
    players_skipped_duplicate: int = 0
    returning_players_detected: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    applied: bool = False
    trust_note: str = (
        "Roster data has been saved. It is user-maintained and should be "
        "reviewed before publication."
    )
