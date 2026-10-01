"""Closed contracts for staff public-entity favorites."""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PublicFavoriteKind = Literal["organization", "team", "competition"]


class PublicFavoritePut(BaseModel):
    subject_kind: PublicFavoriteKind
    subject_public_key: str = Field(min_length=1, max_length=64)
    model_config = ConfigDict(extra="forbid")


class PublicFavoriteRead(BaseModel):
    id: str
    subject_kind: PublicFavoriteKind
    public_key: str
    display_name: str
    canonical_path: str
    created_at: dt.datetime
    model_config = ConfigDict(extra="forbid")


class PublicFavoriteList(BaseModel):
    items: list[PublicFavoriteRead]
    next_offset: int | None
    model_config = ConfigDict(extra="forbid")
