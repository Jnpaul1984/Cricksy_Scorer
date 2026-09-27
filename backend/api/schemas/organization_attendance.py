"""Shared School/Club organization event attendance API contracts."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel

AttendanceState = Literal["present", "absent", "excused"]
AttendanceFilter = Literal["present", "absent", "excused", "unmarked"]


class OrganizationPlayerAttendanceUpdate(BaseModel):
    state: AttendanceState

    model_config = {"extra": "forbid"}


class OrganizationAttendanceCounts(BaseModel):
    present: int
    absent: int
    excused: int
    unmarked: int
    total: int
    attendance_percentage: float | None


class OrganizationAttendancePlayer(BaseModel):
    roster_membership_id: str
    player_profile_id: str
    player_name: str
    team_ids: list[str]
    eligible: bool
    state: AttendanceState | None
    recorded_by_user_id: str | None
    recorded_at: dt.datetime | None


class OrganizationAttendanceRegisterResponse(BaseModel):
    organization_id: str
    event_id: str
    event_title: str
    event_status: str
    start_at: dt.datetime
    counts: OrganizationAttendanceCounts
    players: list[OrganizationAttendancePlayer]
    total: int
    limit: int
    offset: int


class OrganizationPlayerAttendanceResponse(BaseModel):
    organization_id: str
    event_id: str
    roster_membership_id: str
    player_profile_id: str
    state: AttendanceState
    recorded_by_user_id: str
    recorded_at: dt.datetime


class OrganizationPlayerAttendanceHistoryEntry(BaseModel):
    id: str
    state: AttendanceState
    recorded_by_user_id: str
    recorded_at: dt.datetime


class OrganizationPlayerAttendanceHistoryResponse(BaseModel):
    organization_id: str
    event_id: str
    roster_membership_id: str
    player_profile_id: str
    items: list[OrganizationPlayerAttendanceHistoryEntry]


class OrganizationAttendanceSummaryResponse(BaseModel):
    organization_id: str
    from_at: dt.datetime | None
    to_at: dt.datetime | None
    team_id: str | None
    roster_membership_id: str | None
    counts: OrganizationAttendanceCounts
    event_count: int
