"""Shared School/Club organization event and calendar API contracts."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

OrganizationEventType = Literal["training", "other"]
OrganizationEventStatus = Literal["scheduled", "cancelled"]
OrganizationEventParticipantScope = Literal["organization", "teams", "selected_players"]


def _utc(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        raise PydanticCustomError(
            "timezone_required", "Event date/time values must include a timezone offset"
        )
    return value.astimezone(dt.UTC)


class OrganizationEventCreate(BaseModel):
    event_type: OrganizationEventType
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    start_at: dt.datetime
    end_at: dt.datetime | None = None
    location: str = Field(min_length=1, max_length=255)
    participant_scope: OrganizationEventParticipantScope = "organization"
    team_ids: list[str] = Field(default_factory=list, max_length=50)
    roster_membership_ids: list[str] = Field(default_factory=list, max_length=500)

    model_config = {"extra": "forbid"}

    @field_validator("title", "location")
    @classmethod
    def normalize_required_text(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise PydanticCustomError("empty_value", "Value must not be empty")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("start_at", "end_at")
    @classmethod
    def require_timezone(cls, value: dt.datetime | None) -> dt.datetime | None:
        return _utc(value)

    @field_validator("team_ids", "roster_membership_ids")
    @classmethod
    def unique_ids(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise PydanticCustomError("empty_participant_id", "Participant IDs must not be empty")
        if len(set(normalized)) != len(normalized):
            raise PydanticCustomError("duplicate_participant_id", "Participant IDs must be unique")
        return normalized

    @model_validator(mode="after")
    def validate_scope_and_time(self) -> OrganizationEventCreate:
        if self.end_at is not None and self.end_at <= self.start_at:
            raise PydanticCustomError("invalid_time_range", "end_at must be later than start_at")
        if self.participant_scope == "organization":
            if self.team_ids or self.roster_membership_ids:
                raise PydanticCustomError(
                    "invalid_participant_scope",
                    "Organization-scoped events cannot include participant IDs",
                )
        elif self.participant_scope == "teams":
            if not self.team_ids or self.roster_membership_ids:
                raise PydanticCustomError(
                    "invalid_participant_scope", "Team-scoped events require only team_ids"
                )
        elif not self.roster_membership_ids or self.team_ids:
            raise PydanticCustomError(
                "invalid_participant_scope",
                "Selected-player events require only roster_membership_ids",
            )
        return self


class OrganizationEventUpdate(BaseModel):
    event_type: OrganizationEventType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    start_at: dt.datetime | None = None
    end_at: dt.datetime | None = None
    location: str | None = Field(default=None, min_length=1, max_length=255)
    participant_scope: OrganizationEventParticipantScope | None = None
    team_ids: list[str] | None = Field(default=None, max_length=50)
    roster_membership_ids: list[str] | None = Field(default=None, max_length=500)

    model_config = {"extra": "forbid"}

    @field_validator("title", "location")
    @classmethod
    def normalize_required_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise PydanticCustomError("empty_value", "Value must not be empty")
        return normalized

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("start_at", "end_at")
    @classmethod
    def require_timezone(cls, value: dt.datetime | None) -> dt.datetime | None:
        return _utc(value)

    @field_validator("team_ids", "roster_membership_ids")
    @classmethod
    def unique_ids(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise PydanticCustomError("empty_participant_id", "Participant IDs must not be empty")
        if len(set(normalized)) != len(normalized):
            raise PydanticCustomError("duplicate_participant_id", "Participant IDs must be unique")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> OrganizationEventUpdate:
        if not self.model_fields_set:
            raise PydanticCustomError(
                "empty_event_update", "At least one event field must be supplied"
            )
        return self


class OrganizationEventResponse(BaseModel):
    id: str
    organization_id: str
    event_type: str
    title: str
    description: str | None
    start_at: dt.datetime
    end_at: dt.datetime | None
    location: str
    participant_scope: str
    team_ids: list[str]
    roster_membership_ids: list[str]
    status: OrganizationEventStatus
    created_by_user_id: str | None
    updated_by_user_id: str | None
    cancelled_by_user_id: str | None
    cancelled_at: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator(
        "start_at",
        "end_at",
        "cancelled_at",
        "created_at",
        "updated_at",
        mode="before",
    )
    @classmethod
    def serialize_unambiguous_time(cls, value: dt.datetime | None) -> dt.datetime | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=dt.UTC)
        return value.astimezone(dt.UTC)


class OrganizationEventListResponse(BaseModel):
    items: list[OrganizationEventResponse]
    total: int
    limit: int
    offset: int


class OrganizationCalendarItem(BaseModel):
    source_type: Literal["organization_event", "fixture"]
    source_id: str
    title: str
    start_at: dt.datetime
    end_at: dt.datetime | None
    location: str | None
    status: str
    event_type: str | None
    participant_scope: str | None
    team_ids: list[str]
    game_id: str | None
    competition_id: str | None


class OrganizationCalendarResponse(BaseModel):
    items: list[OrganizationCalendarItem]
    total: int
    limit: int
    offset: int
