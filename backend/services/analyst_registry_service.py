"""Phase 10M — Analyst Data Registry: unified match classification and registry service.

Provides deterministic classification of every completed match in the system so
the Analyst Workspace can discover, filter, and analyze all match sources through
a single governed data foundation.

Classification is conservative:
  - If competition cannot be determined → competition_code = "unknown"
  - If gender cannot be determined → gender_category = "unknown"
  - If source cannot be determined → source_type = "unknown"

Never silently merges women's records into men's analysis.
Never fabricates metadata.
"""

from __future__ import annotations

import re
from typing import Any

from backend.api.schemas.analyst_matches import (
    AnalystRegistryEntry,
    AnalystMatchRegistryListResponse,
)
from backend.services.analyst_access import scoped_games_stmt
from backend.services.cpl_team_alias_registry import canonicalize_team_name
from backend.services.cpl_venue_alias_registry import canonicalize_venue_name
from backend.sql_app.models import Game, GameStatus, HistoricalImportBatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# ---------------------------------------------------------------------------
# Competition classification
# ---------------------------------------------------------------------------

_WCPL_PATTERNS = [
    re.compile(r"\bwcpl\b", re.I),
    re.compile(r"women'?s\s+caribbean\s+premier\s+league", re.I),
    re.compile(r"women'?s\s+cpl", re.I),
    re.compile(r"\bwomen\b.*\bcaribbean\b.*\bleague\b", re.I),
]

_CPL_MEN_PATTERNS = [
    re.compile(r"caribbean\s+premier\s+league", re.I),
    re.compile(r"\bcpl\b", re.I),
]

_WOMEN_KEYWORDS = re.compile(r"\bwomen\b|\bfemale\b|\bgirl\b|\bwcpl\b", re.I)


def classify_competition(event_name: str | None) -> tuple[str, str]:
    """Return (competition_code, competition_name) for the given event name.

    Rules (conservative):
    - WCPL if event name matches any WCPL pattern
    - CPL_MEN if event name matches CPL pattern AND no WCPL/women markers
    - unknown otherwise

    Returns (competition_code, canonical_name).
    """
    if not event_name or not event_name.strip():
        return ("unknown", "Unknown")

    name = event_name.strip()

    # Check WCPL first (more specific)
    if any(p.search(name) for p in _WCPL_PATTERNS):
        return ("WCPL", name)

    # Check CPL_MEN — but only if no women markers present
    if any(p.search(name) for p in _CPL_MEN_PATTERNS):
        if not _WOMEN_KEYWORDS.search(name):
            return ("CPL_MEN", name)

    return ("unknown", name)


def classify_gender(
    competition_code: str,
    gender_metadata: str | None = None,
) -> str:
    """Return gender_category: 'men', 'women', 'mixed', or 'unknown'.

    Rules:
    - WCPL → women
    - CPL_MEN → men
    - gender_metadata hint when competition_code is 'unknown'
    - Default: unknown (never force unknown into men)
    """
    if competition_code == "WCPL":
        return "women"
    if competition_code == "CPL_MEN":
        return "men"

    # Use explicit gender metadata as fallback
    if gender_metadata:
        gm = gender_metadata.strip().lower()
        if gm in ("women", "female", "f"):
            return "women"
        if gm in ("men", "male", "m"):
            return "men"
        if gm in ("mixed",):
            return "mixed"

    return "unknown"


# ---------------------------------------------------------------------------
# Age category classification
# ---------------------------------------------------------------------------

_KNOWN_AGE_CATEGORIES: frozenset[str] = frozenset({"senior", "youth", "school"})


def classify_age_category(hist_meta: dict[str, Any] | None) -> str:
    """Return age_category: 'senior', 'youth', 'school', or 'unknown'.

    Rules (conservative):
    - Only returns a non-unknown value when hist_meta explicitly contains a
      recognised age_category value ('senior', 'youth', or 'school').
    - Any absent, None, empty, or unrecognised value → 'unknown'.
    - Never infers 'senior' by default.
    """
    if not hist_meta:
        return "unknown"
    raw = hist_meta.get("age_category")
    if not raw or not isinstance(raw, str):
        return "unknown"
    normalised = raw.strip().lower()
    if normalised in _KNOWN_AGE_CATEGORIES:
        return normalised
    return "unknown"


# ---------------------------------------------------------------------------
# Source type classification
# ---------------------------------------------------------------------------


def classify_source_type(
    hist_meta: dict[str, Any] | None,
    batch: HistoricalImportBatch | None,
) -> str:
    """Return source_type string.

    Rules:
    - historical_import: hist_meta present AND batch linked
    - cricksy_completed_scored: no hist_meta (scored via live pipeline)
    - unknown: hist_meta present but no batch linkage (legacy or orphaned)
    """
    if hist_meta is None:
        return "cricksy_completed_scored"
    if batch is not None:
        return "historical_import"
    # hist_meta exists but batch not found — could be orphaned / legacy
    return "unknown"


# ---------------------------------------------------------------------------
# Data completeness classification
# ---------------------------------------------------------------------------


def classify_data_completeness(
    game: Game,
    hist_meta: dict[str, Any] | None,
) -> str:
    """Return data_completeness: 'metadata_only', 'innings_totals',
    'phase_level', or 'delivery_complete'.

    Hierarchy (best wins):
      delivery_complete > phase_level > innings_totals > metadata_only
    """
    # delivery_complete: actual ball-by-ball data
    has_deliveries = bool(hist_meta and hist_meta.get("deliveries_imported")) or bool(
        isinstance(game.deliveries, list) and len(game.deliveries) > 0
    )
    if has_deliveries:
        return "delivery_complete"

    # phase_level: powerplay/middle/death breakdown present
    phases = game.phases if isinstance(game.phases, dict) else {}
    has_phases = any(
        isinstance(phases.get(p), dict) and phases.get(p) for p in ("powerplay", "middle", "death")
    )
    if has_phases:
        return "phase_level"

    # innings_totals: historical innings summary present
    hist_innings = phases.get("historical_innings_summary") or []
    if isinstance(hist_innings, list) and len(hist_innings) > 0:
        return "innings_totals"

    # Also check first_inning_summary (live scored completions)
    if isinstance(game.first_inning_summary, dict) and game.first_inning_summary:
        return "innings_totals"

    return "metadata_only"


# ---------------------------------------------------------------------------
# Main registry builder
# ---------------------------------------------------------------------------


def _hist_meta_from_game(game: Game) -> dict[str, Any] | None:
    phases = game.phases if isinstance(game.phases, dict) else {}
    meta = phases.get("historical_import")
    if isinstance(meta, dict) and meta.get("is_historical"):
        return meta
    return None


def _team_name(team_data: Any, fallback: str) -> str:
    if isinstance(team_data, dict):
        name = team_data.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return fallback


def _season_year(season: str | None) -> int | None:
    if not season:
        return None
    m = re.search(r"(?:19|20)\d{2}", season)
    return int(m.group(0)) if m else None


async def build_analyst_registry(
    current_user: Any,
    db: AsyncSession,
) -> AnalystMatchRegistryListResponse:
    """Build the unified Analyst Match Registry for a user.

    Returns one AnalystRegistryEntry per completed match visible to the user.
    Each entry is classified by competition, gender, source type, and data completeness.
    No fabrication — unknown values remain explicitly 'unknown'.
    """
    stmt = (
        scoped_games_stmt(current_user)
        .where(Game.status == GameStatus.completed)
        .order_by(Game.id.desc())
    )
    result = await db.execute(stmt)
    games = result.scalars().all()

    # Pre-load all referenced HistoricalImportBatch records in one query
    batch_ids: list[str] = []
    for game in games:
        hist_meta = _hist_meta_from_game(game)
        if hist_meta:
            bid = hist_meta.get("batch_id")
            if bid:
                batch_ids.append(bid)

    batches_by_id: dict[str, HistoricalImportBatch] = {}
    if batch_ids:
        batch_stmt = select(HistoricalImportBatch).where(
            HistoricalImportBatch.id.in_(batch_ids)  # type: ignore[arg-type]
        )
        batch_result = await db.execute(batch_stmt)
        for batch in batch_result.scalars().all():
            batches_by_id[str(batch.id)] = batch

    entries: list[AnalystRegistryEntry] = []

    for game in games:
        hist_meta = _hist_meta_from_game(game)
        batch_id = hist_meta.get("batch_id") if hist_meta else None
        batch = batches_by_id.get(str(batch_id)) if batch_id else None

        team_a_name = _team_name(game.team_a, "Team A")
        team_b_name = _team_name(game.team_b, "Team B")
        team_a_canonical, _ = canonicalize_team_name(team_a_name)
        team_b_canonical, _ = canonicalize_team_name(team_b_name)

        # Basic metadata
        match_date: str | None = None
        if hist_meta:
            match_date = hist_meta.get("match_date")
        if not match_date:
            created_at = getattr(game, "created_at", None)
            if created_at:
                match_date = created_at.date().isoformat()

        event_name: str | None = hist_meta.get("event_name") if hist_meta else None
        season: str | None = hist_meta.get("season") if hist_meta else None
        venue_raw: str | None = hist_meta.get("venue") if hist_meta else None
        venue_canonical, _ = canonicalize_venue_name(venue_raw)

        # Classification
        competition_code, competition_name = classify_competition(event_name)
        gender_category = classify_gender(
            competition_code,
            hist_meta.get("gender") if hist_meta else None,
        )
        age_category = classify_age_category(hist_meta)
        source_type = classify_source_type(hist_meta, batch)
        data_completeness = classify_data_completeness(game, hist_meta)

        # Derived flags
        phases = game.phases if isinstance(game.phases, dict) else {}
        has_delivery_data = bool(hist_meta and hist_meta.get("deliveries_imported")) or bool(
            isinstance(game.deliveries, list) and len(game.deliveries) > 0
        )
        has_phase_data = any(
            isinstance(phases.get(p), dict) and phases.get(p)
            for p in ("powerplay", "middle", "death")
        )
        hist_innings = phases.get("historical_innings_summary") or []
        has_scorecard_data = (
            isinstance(hist_innings, list) and len(hist_innings) > 0
        ) or isinstance(game.first_inning_summary, dict)

        # analyst_ready: completeness better than metadata_only
        analyst_ready = data_completeness in ("delivery_complete", "phase_level", "innings_totals")

        # Format
        match_format = (game.match_type or "unknown").upper()
        if match_format not in ("T20", "ODI", "TEST"):
            match_format = "custom" if match_format not in ("", "UNKNOWN") else "unknown"

        entries.append(
            AnalystRegistryEntry(
                match_id=game.id,
                match_title=f"{team_a_name} vs {team_b_name}",
                team_a=team_a_name,
                team_b=team_b_name,
                canonical_team_a=team_a_canonical,
                canonical_team_b=team_b_canonical,
                competition_name=event_name,
                competition_code=competition_code,
                season=season,
                season_year=_season_year(season),
                gender_category=gender_category,
                age_category=age_category,
                format=match_format,
                venue_raw=venue_raw,
                venue_canonical=venue_canonical,
                match_date=match_date,
                source_type=source_type,
                data_completeness=data_completeness,
                has_delivery_data=has_delivery_data,
                has_phase_data=has_phase_data,
                has_scorecard_data=has_scorecard_data,
                result=game.result,
                analyst_ready=analyst_ready,
            )
        )

    # Build diagnostics
    diagnostics: dict[str, int] = {
        "total": len(entries),
        "historical_import": sum(1 for e in entries if e.source_type == "historical_import"),
        "cricksy_completed_scored": sum(
            1 for e in entries if e.source_type == "cricksy_completed_scored"
        ),
        "unknown_source": sum(1 for e in entries if e.source_type == "unknown"),
        "CPL_MEN": sum(1 for e in entries if e.competition_code == "CPL_MEN"),
        "WCPL": sum(1 for e in entries if e.competition_code == "WCPL"),
        "unknown_competition": sum(1 for e in entries if e.competition_code == "unknown"),
        "gender_men": sum(1 for e in entries if e.gender_category == "men"),
        "gender_women": sum(1 for e in entries if e.gender_category == "women"),
        "gender_unknown": sum(1 for e in entries if e.gender_category == "unknown"),
        "delivery_complete": sum(1 for e in entries if e.data_completeness == "delivery_complete"),
        "phase_level": sum(1 for e in entries if e.data_completeness == "phase_level"),
        "innings_totals": sum(1 for e in entries if e.data_completeness == "innings_totals"),
        "metadata_only": sum(1 for e in entries if e.data_completeness == "metadata_only"),
        "analyst_ready": sum(1 for e in entries if e.analyst_ready),
    }

    return AnalystMatchRegistryListResponse(
        entries=entries,
        total=len(entries),
        diagnostics=diagnostics,
    )
