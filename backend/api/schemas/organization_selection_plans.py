"""Private shared School/Club selection-plan API contracts."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

SelectionPlanStatus = Literal["draft", "published"]


class OrganizationSelectionPlanCreate(BaseModel):
    team_id: str = Field(min_length=1)
    fixture_id: str = Field(min_length=1)

    model_config = {"extra": "forbid"}


class OrganizationSelectionPlanUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    xi_roster_membership_ids: list[str] = Field(default_factory=list, max_length=11)
    reserve_roster_membership_ids: list[str] = Field(default_factory=list)
    captain_roster_membership_id: str | None = None
    wicketkeeper_roster_membership_id: str | None = None

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def validate_memberships(self) -> OrganizationSelectionPlanUpdate:
        fields = self.model_fields_set
        xi = self.xi_roster_membership_ids
        reserves = self.reserve_roster_membership_ids
        if "xi_roster_membership_ids" in fields and len(set(xi)) != len(xi):
            raise PydanticCustomError(
                "duplicate_planned_xi",
                "Planned XI cannot contain duplicate roster memberships",
            )
        if "reserve_roster_membership_ids" in fields and len(set(reserves)) != len(reserves):
            raise PydanticCustomError(
                "duplicate_reserve",
                "Reserves cannot contain duplicate roster memberships",
            )
        if (
            "xi_roster_membership_ids" in fields
            and "reserve_roster_membership_ids" in fields
            and set(xi) & set(reserves)
        ):
            raise PydanticCustomError(
                "selection_overlap",
                "A player cannot be both planned XI and reserve",
            )
        return self


class OrganizationSelectionPlanResponse(BaseModel):
    id: str
    organization_id: str
    team_id: str
    fixture_id: str
    status: SelectionPlanStatus
    revision: int
    xi_roster_membership_ids: list[str]
    reserve_roster_membership_ids: list[str]
    captain_roster_membership_id: str | None
    wicketkeeper_roster_membership_id: str | None
    created_by_user_id: str
    updated_by_user_id: str
    created_at: dt.datetime
    updated_at: dt.datetime


class OrganizationSelectionCandidate(BaseModel):
    roster_membership_id: str
    player_profile_id: str
    player_name: str
    eligible: bool


class OrganizationSelectionCandidateResponse(BaseModel):
    organization_id: str
    team_id: str
    fixture_id: str
    candidates: list[OrganizationSelectionCandidate]
