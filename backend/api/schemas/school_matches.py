"""Organization-scoped School match setup contracts for Phase 7I."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class SchoolMatchSideSelection(BaseModel):
    """One saved School Team and its explicit playing XI selection."""

    team_id: str = Field(min_length=1)
    playing_xi_membership_ids: list[str] = Field(min_length=11, max_length=11)
    captain_membership_id: str = Field(min_length=1)
    wicketkeeper_membership_id: str = Field(min_length=1)


class SchoolMatchCreate(BaseModel):
    """Create an existing Game from two governed School Team snapshots."""

    team_a: SchoolMatchSideSelection
    team_b: SchoolMatchSideSelection
    match_type: Literal["limited", "multi_day", "custom"] = "limited"
    overs_limit: int | None = Field(default=20, ge=1, le=120)
    days_limit: int | None = Field(default=None, ge=1, le=7)
    overs_per_day: int | None = Field(default=None, ge=1, le=120)
    dls_enabled: bool = False
    toss_winner_side: Literal["team_a", "team_b"]
    decision: Literal["bat", "bowl"]

    @model_validator(mode="after")
    def validate_match_limits(self) -> SchoolMatchCreate:
        if self.match_type == "limited" and self.overs_limit is None:
            raise ValueError("overs_limit is required for a limited-overs match")
        if self.match_type == "multi_day" and (
            self.days_limit is None or self.overs_per_day is None
        ):
            raise ValueError("days_limit and overs_per_day are required for a multi-day match")
        return self


class SchoolMatchCreateResponse(BaseModel):
    game_id: str
    organization_id: str
    team_a_id: str
    team_b_id: str
    team_a_name: str
    team_b_name: str
    team_a_player_profile_ids: list[str]
    team_b_player_profile_ids: list[str]
