"""Phase 10T — Podcast Prep Studio: Pydantic schemas.

Defines request/response models for:
- Podcast research pack generation (match / tournament / archive topics)
- Saved podcast prep reports (CRUD)

All generated content is derived from deterministic imported data.
No official standings or invented player stats are ever asserted.
"""

from __future__ import annotations

import datetime as dt
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums as Literal aliases for schema documentation
# ---------------------------------------------------------------------------

PodcastTopicType = Literal["match", "tournament", "team", "roster", "archive", "custom"]
PodcastReportStatus = Literal["draft", "reviewed", "approved", "archived"]


# ---------------------------------------------------------------------------
# Research pack sections
# ---------------------------------------------------------------------------


class PodcastResearchSection(BaseModel):
    """One named section of a podcast research pack.

    Body may be None if insufficient data exists (thin-data fallback).
    All values carry a confidence label and a source note.
    """

    section_key: str
    title: str
    body: str | None = None
    confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    note: str = "Derived from imported data — not official."


class PodcastResearchPack(BaseModel):
    """Structured podcast research pack generated from deterministic data.

    Phase 10T: covers match / tournament / archive comparison topics.
    All sections are derived from imported match data.
    No unsupported AI claims are made.
    """

    # Identity
    topic_type: PodcastTopicType
    episode_title: str
    # Context
    match_context: str | None = None
    competition_label: str | None = None
    season_label: str | None = None
    venue_context: str | None = None
    format_label: str | None = None
    # Research sections (ordered for podcast flow)
    sections: list[PodcastResearchSection] = Field(default_factory=list)
    # Source entity references
    source_match_id: str | None = None
    source_competition_code: str | None = None
    source_season: str | None = None
    source_team_name: str | None = None
    # Trust governance
    trust_note: str = (
        "All facts are derived from imported match data and are not official standings or records."
    )
    overall_confidence: Literal["high", "medium", "low", "unknown"] = "unknown"
    generated_at: dt.datetime = Field(default_factory=lambda: dt.datetime.now(dt.UTC))

    # Convenience: pre-rendered markdown and plain text
    generated_markdown: str | None = None
    generated_plain_text: str | None = None


# ---------------------------------------------------------------------------
# Saved report schemas
# ---------------------------------------------------------------------------


class PodcastPrepReportCreate(BaseModel):
    """Request body for saving a new podcast prep report."""

    title: str = Field(..., min_length=1, max_length=512)
    topic_type: PodcastTopicType = "custom"
    source_match_id: str | None = None
    source_competition_code: str | None = None
    source_season: str | None = None
    source_team_name: str | None = None
    generated_markdown: str | None = None
    generated_plain_text: str | None = None
    trust_summary: str | None = None
    status: PodcastReportStatus = "draft"


class PodcastPrepReportUpdate(BaseModel):
    """Request body for updating an existing saved report."""

    title: str | None = None
    generated_markdown: str | None = None
    generated_plain_text: str | None = None
    trust_summary: str | None = None
    status: PodcastReportStatus | None = None


class PodcastPrepReportResponse(BaseModel):
    """Response schema for a single saved podcast prep report."""

    id: str
    title: str
    topic_type: str
    source_match_id: str | None = None
    source_competition_code: str | None = None
    source_season: str | None = None
    source_team_name: str | None = None
    generated_markdown: str | None = None
    generated_plain_text: str | None = None
    trust_summary: str | None = None
    status: str
    created_by_id: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True, "use_enum_values": True}


class PodcastPrepReportListResponse(BaseModel):
    """Paginated list of saved podcast prep reports."""

    reports: list[PodcastPrepReportResponse] = Field(default_factory=list)
    total: int = 0


# ---------------------------------------------------------------------------
# Research pack request schemas
# ---------------------------------------------------------------------------


class MatchPodcastPackRequest(BaseModel):
    """Request body to generate a podcast research pack for a single match."""

    match_id: str


class TournamentPodcastPackRequest(BaseModel):
    """Request body to generate a podcast research pack for a tournament."""

    competition_code: str
    season: str | None = None
    gender_category: str = "unknown"


class ArchivePodcastPackRequest(BaseModel):
    """Request body to generate a podcast research pack for archive comparisons."""

    competition_code: str | None = None
    season_start: int | None = None
    season_end: int | None = None
    format_family: str | None = None
    gender_category: str | None = None


class RosterPodcastPackRequest(BaseModel):
    """Request body to generate a podcast research pack using current roster data."""

    competition_code: str = "CPL_MEN"
    season: str
    team_name: str | None = None
