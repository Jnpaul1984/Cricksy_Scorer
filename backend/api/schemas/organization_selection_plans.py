"""Private shared School/Club selection-plan API contracts."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, model_validator
from pydantic_core import PydanticCustomError

SelectionPlanStatus = Literal["draft", "published"]
SelectionAvailabilityState = Literal["available", "unavailable", "maybe"]
BowlingPlanRole = Literal["primary", "secondary"]


class OrganizationBowlingPlanEntry(BaseModel):
    roster_membership_id: str = Field(min_length=1)
    role: BowlingPlanRole

    model_config = {"extra": "forbid"}


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
    batting_order_roster_membership_ids: list[str] = Field(default_factory=list, max_length=11)
    bowling_plan: list[OrganizationBowlingPlanEntry] = Field(default_factory=list, max_length=11)

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
        batting_order = self.batting_order_roster_membership_ids
        if "batting_order_roster_membership_ids" in fields and len(set(batting_order)) != len(
            batting_order
        ):
            raise PydanticCustomError(
                "duplicate_batting_order_player",
                "Batting order cannot contain duplicate roster memberships",
            )
        bowling_ids = [entry.roster_membership_id for entry in self.bowling_plan]
        if "bowling_plan" in fields and len(set(bowling_ids)) != len(bowling_ids):
            raise PydanticCustomError(
                "duplicate_bowling_plan_player",
                "Bowling plan cannot contain duplicate roster memberships",
            )
        return self


class OrganizationSelectionRevisionRequest(BaseModel):
    expected_revision: int = Field(ge=1)

    model_config = {"extra": "forbid"}


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
    batting_order_roster_membership_ids: list[str]
    bowling_plan: list[OrganizationBowlingPlanEntry]
    latest_publication_version: int | None
    created_by_user_id: str
    updated_by_user_id: str
    created_at: dt.datetime
    updated_at: dt.datetime


class OrganizationSelectionCandidate(BaseModel):
    roster_membership_id: str
    player_profile_id: str
    player_name: str
    eligible: bool
    availability_state: SelectionAvailabilityState | None


class OrganizationSelectionCandidateResponse(BaseModel):
    organization_id: str
    team_id: str
    fixture_id: str
    candidates: list[OrganizationSelectionCandidate]


class OrganizationSelectionPublishedPlayer(BaseModel):
    roster_membership_id: str
    player_profile_id: str
    player_name: str
    selection_role: Literal["xi", "reserve"]
    batting_position: int | None
    bowling_priority: int | None
    bowling_role: BowlingPlanRole | None


class OrganizationSelectionPublicationResponse(BaseModel):
    id: str
    organization_id: str
    selection_plan_id: str
    team_id: str
    fixture_id: str
    plan_revision: int
    publication_version: int
    status: Literal["published"] = "published"
    captain_roster_membership_id: str
    wicketkeeper_roster_membership_id: str
    players: list[OrganizationSelectionPublishedPlayer]
    published_by_user_id: str
    published_at: dt.datetime


class OrganizationSelectionHandoffSide(BaseModel):
    """Current match-setup identities derived from one immutable publication."""

    team_id: str
    playing_xi_membership_ids: list[str] = Field(min_length=11, max_length=11)
    captain_membership_id: str
    wicketkeeper_membership_id: str


class OrganizationSelectionHandoffResponse(BaseModel):
    """Validated one-way prefill for the existing organization match setup."""

    organization_id: str
    selection_plan_id: str
    publication_version: int
    fixture_id: str
    fixture_team_a_id: str
    fixture_team_b_id: str
    selected_side: Literal["team_a", "team_b"]
    selected_team: OrganizationSelectionHandoffSide
    planned_batting_order_membership_ids: list[str]
