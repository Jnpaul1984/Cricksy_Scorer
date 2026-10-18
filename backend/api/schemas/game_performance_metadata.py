"""Request and safe response schemas for explicit Game history metadata."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator
from pydantic_core import PydanticCustomError


class GamePerformanceMetadataUpdate(BaseModel):
    expected_revision: StrictInt = Field(ge=1)
    reason: str = Field(min_length=1, max_length=2000)
    actual_played_date: dt.date | None = None
    original_overs_limit: StrictInt | None = Field(default=None, ge=1, le=120)

    model_config = ConfigDict(extra="forbid")

    @field_validator("actual_played_date", mode="before")
    @classmethod
    def validate_calendar_date(cls, value: object) -> dt.date | None:
        if value is None:
            return None
        if isinstance(value, str):
            try:
                parsed = dt.date.fromisoformat(value)
            except ValueError as exc:
                raise PydanticCustomError(
                    "calendar_date",
                    "actual_played_date must be an ISO calendar date without a time",
                ) from exc
            if parsed.isoformat() != value:
                raise PydanticCustomError(
                    "calendar_date",
                    "actual_played_date must be an ISO calendar date without a time",
                )
            return parsed
        if type(value) is dt.date:
            return value
        raise PydanticCustomError(
            "calendar_date",
            "actual_played_date must be an ISO calendar date without a time",
        )


class GamePerformanceMetadataResponse(BaseModel):
    actual_played_date: dt.date | None
    played_date_trust_state: Literal["unknown", "confirmed"]
    original_overs_limit: int | None
    original_format_trust_state: Literal["unknown", "setup_capture", "staff_corrected"]
    metadata_revision: int
