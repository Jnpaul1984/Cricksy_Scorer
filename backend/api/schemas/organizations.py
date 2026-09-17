"""Phase 7B organization and organization-membership API contracts."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

OrganizationType = Literal["school"]
OrganizationStatus = Literal["active", "suspended", "archived"]
MembershipRole = Literal["owner", "admin", "coach", "scorer", "viewer"]
AssignableMembershipRole = Literal["admin", "coach", "scorer", "viewer"]
MembershipStatus = Literal["active", "disabled"]
OrganizationEntitlementPlanKey = Literal["school_free"]
OrganizationEntitlementSource = Literal["system", "admin", "billing"]


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    organization_type: OrganizationType = "school"

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Organization name must not be empty")
        return normalized


class OrganizationResponse(BaseModel):
    id: str
    name: str
    organization_type: OrganizationType
    status: OrganizationStatus
    created_by_user_id: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class OrganizationWithMembershipResponse(OrganizationResponse):
    membership_role: MembershipRole


class OrganizationMembershipCreate(BaseModel):
    user_id: str = Field(..., min_length=1)
    role: AssignableMembershipRole


class OrganizationMembershipUpdate(BaseModel):
    role: MembershipRole | None = None
    status: MembershipStatus | None = None

    @model_validator(mode="after")
    def require_change(self) -> OrganizationMembershipUpdate:
        if self.role is None and self.status is None:
            raise ValueError("At least one membership field must be supplied")
        return self


class OrganizationMembershipResponse(BaseModel):
    id: str
    organization_id: str
    user_id: str
    role: MembershipRole
    status: MembershipStatus
    created_by_user_id: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class OrganizationMembershipListResponse(BaseModel):
    items: list[OrganizationMembershipResponse]
    total: int
    limit: int
    offset: int


class OrganizationEntitlementRecordResponse(BaseModel):
    id: str
    organization_id: str
    plan_key: OrganizationEntitlementPlanKey
    status: MembershipStatus
    source: OrganizationEntitlementSource
    effective_from: dt.datetime
    effective_until: dt.datetime | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class OrganizationEntitlementResponse(OrganizationEntitlementRecordResponse):
    capabilities: list[str]
    excluded_capabilities: list[str]


class SchoolTeamCreate(BaseModel):
    """Organization-scoped team creation input; tenancy comes only from the route."""

    name: str = Field(..., min_length=1, max_length=255)
    home_ground: str | None = Field(default=None, max_length=255)
    season: str | None = Field(default=None, max_length=50)
    coach_name: str | None = Field(default=None, max_length=255)
    coach_id: str | None = None

    model_config = {"extra": "forbid"}

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Team name must not be empty")
        return normalized


class SchoolTeamUpdate(BaseModel):
    """Mutable School team metadata; ownership and lifecycle are server-governed."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    home_ground: str | None = Field(default=None, max_length=255)
    season: str | None = Field(default=None, max_length=50)
    coach_name: str | None = Field(default=None, max_length=255)
    coach_id: str | None = None

    model_config = {"extra": "forbid"}

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Team name must not be empty")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> SchoolTeamUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one team field must be supplied")
        return self


class SchoolTeamResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    status: Literal["active", "archived"]
    home_ground: str | None
    season: str | None
    owner_user_id: str | None
    coach_user_id: str | None
    coach_name: str | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}


class SchoolRosterPlayerCreate(BaseModel):
    """Create only the minimum canonical profile and School-local roster metadata."""

    player_name: str = Field(..., min_length=1, max_length=255)
    student_identifier: str | None = Field(default=None, max_length=128)
    year_group: str | None = Field(default=None, max_length=64)

    model_config = {"extra": "forbid"}

    @field_validator("player_name")
    @classmethod
    def normalize_player_name(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if not normalized:
            raise ValueError("Player name must not be empty")
        return normalized

    @field_validator("student_identifier", "year_group")
    @classmethod
    def normalize_optional_metadata(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None


class SchoolRosterPlayerLink(BaseModel):
    """Link one explicitly selected canonical PlayerProfile by exact ID."""

    player_profile_id: str = Field(..., min_length=1, max_length=255)
    student_identifier: str | None = Field(default=None, max_length=128)
    year_group: str | None = Field(default=None, max_length=64)

    model_config = {"extra": "forbid"}

    @field_validator("player_profile_id")
    @classmethod
    def normalize_player_profile_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Player profile ID must not be empty")
        return normalized

    @field_validator("student_identifier", "year_group")
    @classmethod
    def normalize_optional_metadata(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None


class SchoolRosterPlayerUpdate(BaseModel):
    """Mutable School-local roster metadata; canonical identity is immutable here."""

    student_identifier: str | None = Field(default=None, max_length=128)
    year_group: str | None = Field(default=None, max_length=64)
    status: Literal["active", "inactive"] | None = None

    model_config = {"extra": "forbid"}

    @field_validator("student_identifier", "year_group")
    @classmethod
    def normalize_optional_metadata(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = " ".join(value.split())
        return normalized or None

    @model_validator(mode="after")
    def require_change(self) -> SchoolRosterPlayerUpdate:
        if not self.model_fields_set:
            raise ValueError("At least one roster field must be supplied")
        return self


class SchoolRosterPlayerResponse(BaseModel):
    id: str
    organization_id: str
    player_profile_id: str
    player_name: str
    status: Literal["active", "inactive"]
    student_identifier: str | None
    year_group: str | None
    created_by_user_id: str | None
    created_at: dt.datetime
    updated_at: dt.datetime
