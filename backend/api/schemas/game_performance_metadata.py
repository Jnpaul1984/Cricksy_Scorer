"""Request and safe response schemas for explicit Game history metadata."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt


class GamePerformanceMetadataUpdate(BaseModel):
    expected_revision: StrictInt = Field(ge=1)
    reason: str = Field(min_length=1, max_length=2000)
    actual_played_date: dt.date | None = None
    original_overs_limit: StrictInt | None = Field(default=None, ge=1, le=120)

    model_config = ConfigDict(extra="forbid")


class GamePerformanceMetadataResponse(BaseModel):
    actual_played_date: dt.date | None
    played_date_trust_state: Literal["unknown", "confirmed"]
    original_overs_limit: int | None
    original_format_trust_state: Literal["unknown", "setup_capture", "staff_corrected"]
    metadata_revision: int
