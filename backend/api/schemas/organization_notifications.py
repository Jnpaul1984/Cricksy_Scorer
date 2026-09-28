"""Schemas for the shared School/Club in-app notification foundation."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core import PydanticCustomError

OrganizationNotificationCategory = Literal[
    "organization_announcement",
    "team_announcement",
    "event",
    "selection",
    "availability_reminder",
]
OrganizationNotificationSourceType = Literal[
    "organization_announcement",
    "team_announcement",
    "organization_event",
    "selection_publication",
    "availability_target",
]
OrganizationNotificationOrigin = Literal["actor", "system"]


def _utc(value: dt.datetime | None) -> dt.datetime | None:
    if value is None:
        return None
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=dt.UTC)
    return value.astimezone(dt.UTC)


class OrganizationNotificationResponse(BaseModel):
    id: str
    organization_id: str
    recipient_user_id: str
    category: OrganizationNotificationCategory
    source_type: OrganizationNotificationSourceType
    source_id: str | None
    source_version: str | None
    source_key: str | None
    idempotency_key: str
    title: str
    summary: str
    origin: OrganizationNotificationOrigin
    actor_user_id: str | None
    created_at: dt.datetime
    read_at: dt.datetime | None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("created_at", "read_at", mode="before")
    @classmethod
    def serialize_unambiguous_time(cls, value: dt.datetime | None) -> dt.datetime | None:
        return _utc(value)


class OrganizationNotificationListResponse(BaseModel):
    items: list[OrganizationNotificationResponse]
    total: int
    limit: int
    offset: int


class OrganizationNotificationUnreadCountResponse(BaseModel):
    unread_count: int


class OrganizationNotificationPreferenceResponse(BaseModel):
    organization_id: str
    user_id: str
    category: OrganizationNotificationCategory
    enabled: bool
    created_at: dt.datetime | None
    updated_at: dt.datetime | None

    @field_validator("created_at", "updated_at", mode="before")
    @classmethod
    def serialize_unambiguous_time(cls, value: dt.datetime | None) -> dt.datetime | None:
        return _utc(value)


class OrganizationNotificationPreferenceListResponse(BaseModel):
    items: list[OrganizationNotificationPreferenceResponse]


class OrganizationNotificationPreferenceUpdate(BaseModel):
    enabled: bool

    model_config = ConfigDict(extra="forbid")


class OrganizationNotificationCreate(BaseModel):
    """Internal-only deterministic creation contract; it is not exposed as a route."""

    recipient_user_id: str = Field(min_length=1, max_length=255)
    category: OrganizationNotificationCategory
    source_type: OrganizationNotificationSourceType
    source_id: str | None = Field(default=None, min_length=1, max_length=255)
    source_version: str | None = Field(default=None, min_length=1, max_length=128)
    source_key: str | None = Field(default=None, min_length=1, max_length=255)
    idempotency_key: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    summary: str = Field(min_length=1, max_length=1000)
    origin: OrganizationNotificationOrigin
    actor_user_id: str | None = Field(default=None, min_length=1, max_length=255)

    model_config = ConfigDict(extra="forbid")

    @field_validator(
        "recipient_user_id",
        "source_id",
        "source_version",
        "source_key",
        "idempotency_key",
        "title",
        "summary",
        "actor_user_id",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise PydanticCustomError("empty_notification_value", "Value must not be empty")
        return normalized
