"""Organization-scoped School match setup contracts for Phase 7I."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError


def _contract_error(message: str) -> PydanticCustomError:
    """Return a validation error that the repository error handler can serialize."""
    return PydanticCustomError("school_match_contract", message)


class SchoolMatchSideSelection(BaseModel):
    """One saved School Team and its explicit playing XI selection."""

    team_id: str = Field(min_length=1)
    playing_xi_membership_ids: list[str] = Field(min_length=11, max_length=11)
    captain_membership_id: str = Field(min_length=1)
    wicketkeeper_membership_id: str = Field(min_length=1)


class ExternalOpponentSelection(BaseModel):
    """Match-local opponent data; no School or canonical identity is accepted."""

    team_name: str = Field(min_length=1, max_length=255)
    player_names: list[str] = Field(min_length=11, max_length=11)
    captain_index: int = Field(ge=0, le=10)
    wicketkeeper_index: int = Field(ge=0, le=10)
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def validate_external_xi(self) -> ExternalOpponentSelection:
        self.team_name = self.team_name.strip()
        self.player_names = [name.strip() for name in self.player_names]
        if not self.team_name:
            raise _contract_error("External opponent Team name is required")
        if any(not name or len(name) > 255 for name in self.player_names):
            raise _contract_error(
                "External opponent player names must be between 1 and 255 characters"
            )
        normalized = [name.casefold() for name in self.player_names]
        if len(set(normalized)) != 11:
            raise _contract_error("External opponent XI must contain 11 distinct player names")
        return self


class SchoolMatchCreate(BaseModel):
    """Create a Game from governed School snapshots and an optional external side."""

    mode: Literal["school_vs_school", "school_vs_external"] = "school_vs_school"
    school_side: Literal["team_a", "team_b"] | None = None
    team_a: SchoolMatchSideSelection | None = None
    team_b: SchoolMatchSideSelection | None = None
    external_opponent: ExternalOpponentSelection | None = None
    match_type: Literal["limited", "multi_day", "custom"] = "limited"
    overs_limit: int | None = Field(default=20, ge=1, le=120)
    days_limit: int | None = Field(default=None, ge=1, le=7)
    overs_per_day: int | None = Field(default=None, ge=1, le=120)
    dls_enabled: bool = False
    toss_winner_side: Literal["team_a", "team_b"]
    decision: Literal["bat", "bowl"]

    @model_validator(mode="after")
    def validate_match_limits(self) -> SchoolMatchCreate:
        if self.mode == "school_vs_school":
            if self.team_a is None or self.team_b is None:
                raise _contract_error("Two saved School Teams are required")
            if self.school_side is not None or self.external_opponent is not None:
                raise _contract_error(
                    "External opponent fields are not valid for a School Team match"
                )
        else:
            if self.school_side is None or self.external_opponent is None:
                raise _contract_error("School side and external opponent are required")
            school_selection = self.team_a if self.school_side == "team_a" else self.team_b
            external_selection = self.team_b if self.school_side == "team_a" else self.team_a
            if school_selection is None:
                raise _contract_error(
                    "A saved School Team is required for the selected School side"
                )
            if external_selection is not None:
                raise _contract_error("The external side must not reference a saved School Team")
        if self.match_type == "limited" and self.overs_limit is None:
            raise _contract_error("overs_limit is required for a limited-overs match")
        if self.match_type == "multi_day" and (
            self.days_limit is None or self.overs_per_day is None
        ):
            raise _contract_error("days_limit and overs_per_day are required for a multi-day match")
        return self


class SchoolMatchCreateResponse(BaseModel):
    game_id: str
    organization_id: str
    team_a_id: str | None
    team_b_id: str | None
    team_a_name: str
    team_b_name: str
    team_a_player_profile_ids: list[str]
    team_b_player_profile_ids: list[str]
