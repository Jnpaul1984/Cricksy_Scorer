"""Shared School/Club announcement and immutable publication contracts."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pydantic_core import PydanticCustomError

OrganizationAnnouncementAudience = Literal["organization", "team", "staff"]
OrganizationAnnouncementStatus = Literal["draft", "published"]


def _single_line(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise PydanticCustomError("empty_announcement_value", "Value must not be empty")
    return normalized


def _body(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise PydanticCustomError("empty_announcement_body", "Body must not be empty")
    return normalized


class OrganizationAnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=6000)
    audience_type: OrganizationAnnouncementAudience
    team_id: str | None = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        return _single_line(value)

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        return _body(value)

    @model_validator(mode="after")
    def validate_audience(self) -> OrganizationAnnouncementCreate:
        if self.audience_type == "team" and self.team_id is None:
            raise PydanticCustomError(
                "announcement_team_required", "Team audience requires team_id"
            )
        if self.audience_type != "team" and self.team_id is not None:
            raise PydanticCustomError(
                "announcement_team_not_allowed", "team_id is only valid for Team audience"
            )
        return self


class OrganizationAnnouncementUpdate(BaseModel):
    expected_revision: int = Field(ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=255)
    body: str | None = Field(default=None, min_length=1, max_length=6000)
    audience_type: OrganizationAnnouncementAudience | None = None
    team_id: str | None = Field(default=None, min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("title")
    @classmethod
    def normalize_optional_title(cls, value: str | None) -> str | None:
        return None if value is None else _single_line(value)

    @field_validator("body")
    @classmethod
    def normalize_optional_body(cls, value: str | None) -> str | None:
        return None if value is None else _body(value)

    @model_validator(mode="after")
    def reject_null_required_fields(self) -> OrganizationAnnouncementUpdate:
        for field_name in ("title", "body", "audience_type"):
            if field_name in self.model_fields_set and getattr(self, field_name) is None:
                raise PydanticCustomError(
                    "announcement_field_not_nullable", f"{field_name} may not be null"
                )
        return self


class OrganizationAnnouncementRevisionRequest(BaseModel):
    expected_revision: int = Field(ge=1)

    model_config = ConfigDict(extra="forbid")


class OrganizationAnnouncementResponse(BaseModel):
    id: str
    organization_id: str
    title: str
    body: str
    audience_type: OrganizationAnnouncementAudience
    team_id: str | None
    status: OrganizationAnnouncementStatus
    revision: int
    last_published_version: int
    created_by_user_id: str | None
    updated_by_user_id: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationAnnouncementPublicationResponse(BaseModel):
    id: str
    announcement_id: str
    organization_id: str
    publication_version: int
    announcement_revision: int
    title: str
    body: str
    audience_type: OrganizationAnnouncementAudience
    team_id: str | None
    published_by_user_id: str | None
    published_at: dt.datetime
    eligible_recipient_count: int
    delivered_count: int
    suppressed_by_preference_count: int
    unresolved_recipient_count: int

    model_config = ConfigDict(from_attributes=True)


class OrganizationAnnouncementFeedItem(BaseModel):
    announcement_id: str
    organization_id: str
    title: str
    body: str
    audience_type: OrganizationAnnouncementAudience
    team_id: str | None
    status: OrganizationAnnouncementStatus
    revision: int
    publication_version: int | None
    published_by_user_id: str | None
    published_at: dt.datetime | None
    eligible_recipient_count: int | None
    delivered_count: int | None
    suppressed_by_preference_count: int | None
    unresolved_recipient_count: int | None
    created_by_user_id: str | None
    created_at: dt.datetime
    updated_at: dt.datetime


class OrganizationAnnouncementFeedResponse(BaseModel):
    items: list[OrganizationAnnouncementFeedItem]
    total: int
    limit: int
    offset: int
