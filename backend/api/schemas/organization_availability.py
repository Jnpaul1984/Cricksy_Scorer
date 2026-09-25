"""Shared School/Club organization player availability API contracts."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

AvailabilityState = Literal["available", "unavailable", "maybe"]
AvailabilityFilter = Literal["available", "unavailable", "maybe", "no_response"]
AvailabilityTargetType = Literal["event", "fixture"]


def _utc(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise PydanticCustomError(
            "timezone_required", "Availability deadline must include a timezone offset"
        )
    return value.astimezone(dt.UTC)


class OrganizationAvailabilityTargetUpdate(BaseModel):
    response_deadline: dt.datetime | None

    model_config = {"extra": "forbid"}

    @field_validator("response_deadline")
    @classmethod
    def require_timezone(cls, value: dt.datetime | None) -> dt.datetime | None:
        return _utc(value)

    @model_validator(mode="after")
    def require_deadline_field(self) -> OrganizationAvailabilityTargetUpdate:
        if "response_deadline" not in self.model_fields_set:
            raise PydanticCustomError(
                "empty_availability_target_update",
                "response_deadline must be supplied",
            )
        return self


class OrganizationPlayerAvailabilityUpdate(BaseModel):
    state: AvailabilityState

    model_config = {"extra": "forbid"}


class OrganizationAvailabilityTargetResponse(BaseModel):
    target_type: AvailabilityTargetType
    target_id: str
    title: str
    starts_at: dt.datetime | None
    response_deadline: dt.datetime | None
    deadline_passed: bool


class OrganizationAvailabilityCounts(BaseModel):
    available: int
    unavailable: int
    maybe: int
    no_response: int
    total: int


class OrganizationAvailabilityPlayer(BaseModel):
    roster_membership_id: str
    player_profile_id: str
    player_name: str
    team_ids: list[str]
    state: AvailabilityState | None
    recorded_by_user_id: str | None
    recorded_at: dt.datetime | None
    recorded_after_deadline: bool


class OrganizationAvailabilitySummaryResponse(BaseModel):
    target: OrganizationAvailabilityTargetResponse
    counts: OrganizationAvailabilityCounts
    players: list[OrganizationAvailabilityPlayer]
    total: int
    limit: int
    offset: int


class OrganizationPlayerAvailabilityResponse(BaseModel):
    organization_id: str
    target_type: AvailabilityTargetType
    target_id: str
    roster_membership_id: str
    player_profile_id: str
    state: AvailabilityState
    recorded_by_user_id: str
    recorded_at: dt.datetime
    recorded_after_deadline: bool


class OrganizationPlayerAvailabilityHistoryEntry(BaseModel):
    id: str
    state: AvailabilityState
    recorded_by_user_id: str
    recorded_at: dt.datetime
    recorded_after_deadline: bool


class OrganizationPlayerAvailabilityHistoryResponse(BaseModel):
    organization_id: str
    target_type: AvailabilityTargetType
    target_id: str
    roster_membership_id: str
    player_profile_id: str
    items: list[OrganizationPlayerAvailabilityHistoryEntry]


class OrganizationAvailabilityQuery(BaseModel):
    state: AvailabilityFilter | None = None
    team_id: str | None = Field(default=None, min_length=1)
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0, le=10_000)

    model_config = {"extra": "forbid"}
