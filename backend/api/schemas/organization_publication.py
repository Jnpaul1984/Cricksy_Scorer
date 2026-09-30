"""Narrow contracts for organization publication and anonymous projection."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel


class OrganizationPublicationSettingsResponse(BaseModel):
    organization_id: str
    public_identifier: str
    publication_state: Literal["unpublished", "published"]
    publication_version: int
    published_at: dt.datetime | None
    unpublished_at: dt.datetime | None
    published_by_user_id: str | None
    unpublished_by_user_id: str | None
    updated_by_user_id: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class PublicOrganizationResponse(BaseModel):
    """Exhaustive anonymous allowlist; deliberately contains no internal identifiers."""

    public_identifier: str
    display_name: str
    organization_type: Literal["school", "club"]

    model_config = {"extra": "forbid"}
