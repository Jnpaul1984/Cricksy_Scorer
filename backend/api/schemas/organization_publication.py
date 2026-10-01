"""Narrow contracts for organization publication and anonymous projection."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


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
    logo_url: str | None
    logo_alt_text: str | None
    branding_version: int
    branding_updated_at: dt.datetime | None
    branding_updated_by_user_id: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class PublicOrganizationResponse(BaseModel):
    """Exhaustive anonymous allowlist; deliberately contains no internal identifiers."""

    public_identifier: str
    display_name: str
    organization_type: Literal["school", "club"]

    model_config = {"extra": "forbid"}


class PublicTeamAggregateStats(BaseModel):
    """Team-only totals derived exclusively from published final games."""

    published_games: int = Field(ge=0)

    model_config = ConfigDict(extra="forbid")


class PublicTeamResponse(BaseModel):
    """Deliberate anonymous allowlist; no membership or player data."""

    public_identifier: str
    display_name: str
    aggregate_stats: PublicTeamAggregateStats

    model_config = ConfigDict(extra="forbid")


class OrganizationBrandingUpdate(BaseModel):
    logo_url: str | None = Field(default=None, max_length=2048)
    logo_alt_text: str | None = Field(default=None, max_length=120)

    @field_validator("logo_url", "logo_alt_text", mode="before")
    @classmethod
    def empty_string_is_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class OrganizationCompetitionPublicationResponse(BaseModel):
    competition_id: str
    competition_name: str
    publication_state: Literal["unpublished", "published"]
    publication_version: int
    published_at: dt.datetime | None
    unpublished_at: dt.datetime | None
    updated_by_user_id: str | None

    model_config = ConfigDict(extra="forbid")


class OrganizationCommunitySettingsResponse(BaseModel):
    organization_id: str
    public_identifier: str
    publication_state: Literal["unpublished", "published"]
    logo_url: str | None
    logo_alt_text: str | None
    branding_version: int
    branding_updated_at: dt.datetime | None
    competitions: list[OrganizationCompetitionPublicationResponse]

    model_config = ConfigDict(extra="forbid")


class PublicOrganizationBranding(BaseModel):
    logo_url: str | None
    logo_alt_text: str
    fallback_text: str

    model_config = ConfigDict(extra="forbid")


class PublicCommunityStanding(BaseModel):
    team_name: str
    matches_played: int
    matches_won: int
    matches_lost: int
    matches_drawn: int
    points: int

    model_config = ConfigDict(extra="forbid")


class PublicCommunityFixture(BaseModel):
    team_a_name: str
    team_b_name: str
    match_number: int | None
    venue: str | None
    scheduled_date: dt.datetime | None
    fixture_status: str
    game_status: str | None
    result: str | None
    public_scorecard_path: str | None

    model_config = ConfigDict(extra="forbid")


class PublicCommunityCompetition(BaseModel):
    public_key: str
    name: str
    tournament_type: str
    start_date: dt.datetime | None
    end_date: dt.datetime | None
    status: str
    team_names: list[str]
    fixtures: list[PublicCommunityFixture]
    standings: list[PublicCommunityStanding]

    model_config = ConfigDict(extra="forbid")


class PublicOrganizationCommunityResponse(BaseModel):
    public_identifier: str
    display_name: str
    organization_type: Literal["school", "club"]
    branding: PublicOrganizationBranding
    competitions: list[PublicCommunityCompetition]

    model_config = ConfigDict(extra="forbid")
