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
from datetime import date, datetime, timezone
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

_COMPETITION_REGISTRY: tuple[dict[str, Any], ...] = (
    {
        "code": "WCPL",
        "label": "Women's Caribbean Premier League",
        "competition_type": "franchise_league",
        "region": "Caribbean",
        "default_gender": "women",
        "patterns": (
            re.compile(r"\bwcpl\b", re.I),
            re.compile(r"women'?s\s+caribbean\s+premier\s+league", re.I),
            re.compile(r"women'?s\s+cpl", re.I),
            re.compile(r"\bwomen\b.*\bcaribbean\b.*\bleague\b", re.I),
        ),
    },
    {
        "code": "CPL_MEN",
        "label": "Caribbean Premier League",
        "competition_type": "franchise_league",
        "region": "Caribbean",
        "default_gender": "men",
        "patterns": (
            re.compile(r"caribbean\s+premier\s+league", re.I),
            re.compile(r"\bcpl\b", re.I),
        ),
    },
    {
        "code": "ONE_DAY_CUP",
        "label": "One-Day Cup",
        "competition_type": "domestic_cup",
        "region": "England",
        "patterns": (
            re.compile(r"\bone[- ]day cup\b", re.I),
            re.compile(r"\broyal london one[- ]day cup\b", re.I),
        ),
    },
    {
        "code": "COUNTY_CHAMPIONSHIP",
        "label": "County Championship",
        "competition_type": "domestic_league",
        "region": "England",
        "patterns": (re.compile(r"\bcounty championship\b", re.I),),
    },
    {
        "code": "T20_BLAST",
        "label": "T20 Blast",
        "competition_type": "domestic_league",
        "region": "England",
        "patterns": (
            re.compile(r"\bvitality blast\b", re.I),
            re.compile(r"\bt20 blast\b", re.I),
            re.compile(r"\bblast\b", re.I),
        ),
    },
    {
        "code": "THE_HUNDRED_WOMEN",
        "label": "The Hundred Women",
        "competition_type": "franchise_league",
        "region": "England",
        "default_gender": "women",
        "patterns": (
            re.compile(r"\bthe hundred\b.*\bwomen\b", re.I),
            re.compile(r"\bhundred women\b", re.I),
        ),
    },
    {
        "code": "THE_HUNDRED_MEN",
        "label": "The Hundred Men",
        "competition_type": "franchise_league",
        "region": "England",
        "default_gender": "men",
        "patterns": (
            re.compile(r"\bthe hundred\b.*\bmen\b", re.I),
            re.compile(r"\bhundred men\b", re.I),
            re.compile(r"\bthe hundred\b", re.I),
        ),
    },
    {
        "code": "WPL",
        "label": "Women's Premier League",
        "competition_type": "franchise_league",
        "region": "India",
        "default_gender": "women",
        "patterns": (
            re.compile(r"\bwpl\b", re.I),
            re.compile(r"women'?s\s+premier\s+league", re.I),
        ),
    },
    {
        "code": "IPL",
        "label": "Indian Premier League",
        "competition_type": "franchise_league",
        "region": "India",
        "default_gender": "men",
        "patterns": (
            re.compile(r"\bindian premier league\b", re.I),
            re.compile(r"\bipl\b", re.I),
        ),
    },
    {
        "code": "WBBL",
        "label": "Women's Big Bash League",
        "competition_type": "franchise_league",
        "region": "Australia",
        "default_gender": "women",
        "patterns": (
            re.compile(r"\bwbbbl\b", re.I),
            re.compile(r"\bwbbl\b", re.I),
            re.compile(r"women'?s\s+big bash league", re.I),
        ),
    },
    {
        "code": "BBL",
        "label": "Big Bash League",
        "competition_type": "franchise_league",
        "region": "Australia",
        "default_gender": "men",
        "patterns": (
            re.compile(r"\bbbl\b", re.I),
            re.compile(r"\bbig bash league\b", re.I),
        ),
    },
    {
        "code": "PSL",
        "label": "Pakistan Super League",
        "competition_type": "franchise_league",
        "region": "Pakistan",
        "patterns": (
            re.compile(r"\bpsl\b", re.I),
            re.compile(r"\bpakistan super league\b", re.I),
        ),
    },
    {
        "code": "SA20",
        "label": "SA20",
        "competition_type": "franchise_league",
        "region": "South Africa",
        "patterns": (re.compile(r"\bsa20\b", re.I),),
    },
    {
        "code": "ILT20",
        "label": "ILT20",
        "competition_type": "franchise_league",
        "region": "United Arab Emirates",
        "patterns": (
            re.compile(r"\bilt20\b", re.I),
            re.compile(r"\binternational league t20\b", re.I),
        ),
    },
    {
        "code": "MAJOR_LEAGUE_CRICKET",
        "label": "Major League Cricket",
        "competition_type": "franchise_league",
        "region": "United States",
        "patterns": (
            re.compile(r"\bmajor league cricket\b", re.I),
            re.compile(r"\bmlc\b", re.I),
        ),
    },
    {
        "code": "SUPER_SMASH",
        "label": "Super Smash",
        "competition_type": "domestic_league",
        "region": "New Zealand",
        "patterns": (re.compile(r"\bsuper smash\b", re.I),),
    },
    {
        "code": "SHEFFIELD_SHIELD",
        "label": "Sheffield Shield",
        "competition_type": "domestic_league",
        "region": "Australia",
        "patterns": (re.compile(r"\bsheffield shield\b", re.I),),
    },
    {
        "code": "MARSH_ONE_DAY_CUP",
        "label": "Marsh One-Day Cup",
        "competition_type": "domestic_cup",
        "region": "Australia",
        "patterns": (
            re.compile(r"\bmarsh one[- ]day cup\b", re.I),
            re.compile(r"\bone[- ]day cup\b", re.I),
        ),
    },
    {
        "code": "RANJI_TROPHY",
        "label": "Ranji Trophy",
        "competition_type": "domestic_cup",
        "region": "India",
        "patterns": (re.compile(r"\branji trophy\b", re.I),),
    },
    {
        "code": "VIJAY_HAZARE_TROPHY",
        "label": "Vijay Hazare Trophy",
        "competition_type": "domestic_cup",
        "region": "India",
        "patterns": (re.compile(r"\bvijay hazare trophy\b", re.I),),
    },
    {
        "code": "ICC_T20_WORLD_CUP",
        "label": "ICC T20 World Cup",
        "competition_type": "international_tournament",
        "patterns": (
            re.compile(r"\bicc\b.*\bt20\b.*\bworld cup\b", re.I),
            re.compile(r"\bt20\b.*\bworld cup\b", re.I),
        ),
    },
    {
        "code": "ICC_CHAMPIONS_TROPHY",
        "label": "ICC Champions Trophy",
        "competition_type": "international_tournament",
        "patterns": (re.compile(r"\bicc\b.*\bchampions trophy\b", re.I),),
    },
    {
        "code": "ICC_CRICKET_WORLD_CUP",
        "label": "ICC Cricket World Cup",
        "competition_type": "international_tournament",
        "patterns": (
            re.compile(r"\bicc\b.*\bcricket world cup\b", re.I),
            re.compile(r"\bicc\b.*\bworld cup\b", re.I),
            re.compile(r"\bcricket world cup\b", re.I),
        ),
    },
)

_WOMEN_KEYWORDS = re.compile(r"\bwomen\b|\bfemale\b|\bgirl\b|\bwcpl\b", re.I)
_SCHOOL_KEYWORDS = re.compile(r"\bschool\b|\bschools\b|\bcollege\b", re.I)
_CUSTOM_KEYWORDS = re.compile(r"\bcustom\b|\bexhibition\b|\bfriendly\b|\bfestival\b", re.I)
_INTERNATIONAL_EVENT_HINTS = ("icc", "international", "world cup", "test championship")
_COMPETITION_TYPE_BY_CODE = {
    "CPL_MEN": "franchise_league",
    "WCPL": "franchise_league",
    "ONE_DAY_CUP": "domestic_cup",
    "COUNTY_CHAMPIONSHIP": "domestic_league",
    "T20_BLAST": "domestic_league",
    "THE_HUNDRED_MEN": "franchise_league",
    "THE_HUNDRED_WOMEN": "franchise_league",
    "IPL": "franchise_league",
    "WPL": "franchise_league",
    "BBL": "franchise_league",
    "WBBL": "franchise_league",
    "PSL": "franchise_league",
    "SA20": "franchise_league",
    "ILT20": "franchise_league",
    "MAJOR_LEAGUE_CRICKET": "franchise_league",
    "SUPER_SMASH": "domestic_league",
    "SHEFFIELD_SHIELD": "domestic_league",
    "MARSH_ONE_DAY_CUP": "domestic_cup",
    "RANJI_TROPHY": "domestic_cup",
    "VIJAY_HAZARE_TROPHY": "domestic_cup",
    "INTERNATIONAL_TEST_SERIES": "international_series",
    "INTERNATIONAL_ODI_SERIES": "international_series",
    "INTERNATIONAL_T20I_SERIES": "international_series",
    "ICC_CRICKET_WORLD_CUP": "international_tournament",
    "ICC_T20_WORLD_CUP": "international_tournament",
    "ICC_CHAMPIONS_TROPHY": "international_tournament",
    "DOMESTIC_MULTI_DAY": "domestic_league",
    "DOMESTIC_T20_ENGLAND": "domestic_league",
    "LOCAL_BARBADOS": "regional_league",
    "SCHOOL_CRICKET": "school_or_custom",
    "CUSTOM": "school_or_custom",
    "UNKNOWN": "unknown",
    "unknown": "unknown",
}
_COMPETITION_REGION_BY_CODE = {
    entry["code"]: entry.get("region") for entry in _COMPETITION_REGISTRY if entry.get("region")
} | {
    "DOMESTIC_T20_ENGLAND": "England",
    "DOMESTIC_MULTI_DAY": "England",
    "LOCAL_BARBADOS": "Barbados",
}
_MEN_COMPETITION_CODES = {
    "CPL_MEN",
    "THE_HUNDRED_MEN",
    "IPL",
    "BBL",
    "PSL",
    "SA20",
    "ILT20",
    "MAJOR_LEAGUE_CRICKET",
    "SUPER_SMASH",
    "T20_BLAST",
    "COUNTY_CHAMPIONSHIP",
    "ONE_DAY_CUP",
    "SHEFFIELD_SHIELD",
    "MARSH_ONE_DAY_CUP",
    "RANJI_TROPHY",
    "VIJAY_HAZARE_TROPHY",
    "INTERNATIONAL_TEST_SERIES",
    "INTERNATIONAL_ODI_SERIES",
    "INTERNATIONAL_T20I_SERIES",
    "ICC_CRICKET_WORLD_CUP",
    "ICC_T20_WORLD_CUP",
    "ICC_CHAMPIONS_TROPHY",
}
_WOMEN_COMPETITION_CODES = {
    "WCPL",
    "THE_HUNDRED_WOMEN",
    "WPL",
    "WBBL",
}


def _normalize_match_format(match_format: str | None) -> str:
    value = (match_format or "").strip().lower()
    if value in {"t20", "t20i", "twenty20", "20_over"}:
        return "T20"
    if value in {"odi", "odm", "one-day", "one day", "list a", "list_a"}:
        return "ODI"
    if value in {"test", "test match"}:
        return "Test"
    if value in {"first-class", "first class", "multi_day", "multi-day"}:
        return "First-class / multi-day"
    return "unknown"


def _international_team_names(team_names: list[str] | None) -> set[str]:
    normalized = {
        team.strip().lower()
        for team in (team_names or [])
        if isinstance(team, str) and team.strip()
    }
    return normalized


def classify_competition(
    event_name: str | None,
    *,
    match_format: str | None = None,
    team_names: list[str] | None = None,
    age_category: str | None = None,
) -> tuple[str, str]:
    """Return (competition_code, competition_name) for the given event name.

    Rules (conservative):
    - WCPL if event name matches any WCPL pattern
    - CPL_MEN if event name matches CPL pattern AND no WCPL/women markers
    - unknown otherwise

    Returns (competition_code, canonical_name).
    """
    name = (event_name or "").strip()
    normalized_format = _normalize_match_format(match_format)
    normalized_teams = _international_team_names(team_names)
    is_international = bool(normalized_teams) and normalized_teams.issubset(
        {
            "india",
            "australia",
            "england",
            "new zealand",
            "south africa",
            "pakistan",
            "sri lanka",
            "bangladesh",
            "afghanistan",
            "west indies",
            "ireland",
            "zimbabwe",
            "netherlands",
            "scotland",
        }
    )

    if not name:
        if normalized_format == "Test" and is_international:
            return ("INTERNATIONAL_TEST_SERIES", "International Test Series")
        if normalized_format == "ODI" and is_international:
            return ("INTERNATIONAL_ODI_SERIES", "International ODI Series")
        if normalized_format == "T20" and is_international:
            return ("INTERNATIONAL_T20I_SERIES", "International T20I Series")
        if normalized_format in {"Test", "First-class / multi-day"}:
            return ("DOMESTIC_MULTI_DAY", "Domestic multi-day match")
        return ("unknown", "Unknown")

    for entry in _COMPETITION_REGISTRY:
        patterns = entry.get("patterns") or ()
        if any(pattern.search(name) for pattern in patterns):
            if entry["code"] == "CPL_MEN" and _WOMEN_KEYWORDS.search(name):
                continue
            if entry["code"] == "THE_HUNDRED_MEN" and _WOMEN_KEYWORDS.search(name):
                continue
            if entry["code"] == "BBL" and _WOMEN_KEYWORDS.search(name):
                continue
            return (str(entry["code"]), name)

    lowered = name.lower()
    if age_category == "school":
        return ("SCHOOL_CRICKET", name)
    if _CUSTOM_KEYWORDS.search(name):
        return ("CUSTOM", name)
    if any(token in lowered for token in ("barbados cricket", "barbados", "bca", "barbadian")):
        return ("LOCAL_BARBADOS", name)
    if normalized_format == "Test" and (
        "series" in lowered
        or any(token in lowered for token in _INTERNATIONAL_EVENT_HINTS)
        or is_international
    ):
        return ("INTERNATIONAL_TEST_SERIES", name)
    if normalized_format == "ODI" and (
        "series" in lowered
        or any(token in lowered for token in _INTERNATIONAL_EVENT_HINTS)
        or is_international
    ):
        return ("INTERNATIONAL_ODI_SERIES", name)
    if normalized_format == "T20" and (
        "series" in lowered
        or any(token in lowered for token in _INTERNATIONAL_EVENT_HINTS)
        or is_international
    ):
        return ("INTERNATIONAL_T20I_SERIES", name)
    if normalized_format in {"Test", "First-class / multi-day"}:
        return ("DOMESTIC_MULTI_DAY", name)
    if normalized_format == "T20" and "county" in lowered:
        return ("DOMESTIC_T20_ENGLAND", name)
    return ("unknown", name)


def classify_competition_type(
    competition_code: str,
    *,
    event_name: str | None = None,
    team_names: list[str] | None = None,
) -> str:
    competition_type = _COMPETITION_TYPE_BY_CODE.get(competition_code)
    if competition_type and competition_type != "unknown":
        return competition_type
    lowered = (event_name or "").strip().lower()
    if any(token in lowered for token in ("world cup", "champions trophy")):
        return "international_tournament"
    if any(token in lowered for token in ("series",)):
        return "international_series"
    if any(token in lowered for token in ("academy", "school", "schools")):
        return "school_or_custom"
    if any(token in lowered for token in ("premier league", "hundred", "bbl", "ipl", "wpl")):
        return "franchise_league"
    if any(token in lowered for token in ("cup", "trophy")):
        return "domestic_cup"
    if any(token in lowered for token in ("championship", "blast", "league")):
        return "domestic_league"
    normalized_teams = _international_team_names(team_names)
    if normalized_teams and normalized_teams.issubset(
        {
            "india",
            "australia",
            "england",
            "new zealand",
            "south africa",
            "pakistan",
            "sri lanka",
            "bangladesh",
            "afghanistan",
            "west indies",
            "ireland",
            "zimbabwe",
            "netherlands",
            "scotland",
        }
    ):
        return "international_series"
    return "unknown"


def competition_region_for_code(competition_code: str) -> str | None:
    return _COMPETITION_REGION_BY_CODE.get(competition_code)


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
    if competition_code in _WOMEN_COMPETITION_CODES:
        return "women"
    if competition_code in _MEN_COMPETITION_CODES:
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


def _parse_registry_match_date(value: str | None) -> date | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        return None


def _normalize_sort_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.min
    if value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc).replace(tzinfo=None)


def _registry_sort_key(
    entry: AnalystRegistryEntry,
    *,
    game_created_at: datetime | None,
    batch_created_at: datetime | None,
) -> tuple[int, date, datetime, str]:
    parsed_match_date = _parse_registry_match_date(entry.match_date)
    return (
        1 if parsed_match_date is not None else 0,
        parsed_match_date or date.min,
        _normalize_sort_datetime(batch_created_at or game_created_at),
        entry.match_id,
    )


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

    entries_with_sort: list[tuple[tuple[int, date, datetime, str], AnalystRegistryEntry]] = []

    for game in games:
        hist_meta = _hist_meta_from_game(game)
        batch_id = hist_meta.get("batch_id") if hist_meta else None
        batch = batches_by_id.get(str(batch_id)) if batch_id else None
        created_at = getattr(game, "created_at", None)

        team_a_name = _team_name(game.team_a, "Team A")
        team_b_name = _team_name(game.team_b, "Team B")
        team_a_canonical, _ = canonicalize_team_name(team_a_name)
        team_b_canonical, _ = canonicalize_team_name(team_b_name)

        # Basic metadata
        match_date: str | None = None
        if hist_meta:
            raw_match_date = hist_meta.get("match_date")
            if isinstance(raw_match_date, str) and raw_match_date.strip():
                match_date = raw_match_date.strip()
        elif created_at:
            match_date = created_at.date().isoformat()

        event_name: str | None = hist_meta.get("event_name") if hist_meta else None
        season: str | None = hist_meta.get("season") if hist_meta else None
        venue_raw: str | None = hist_meta.get("venue") if hist_meta else None
        venue_context_raw = hist_meta.get("venue_context") if hist_meta else None
        venue_context = venue_context_raw if isinstance(venue_context_raw, dict) else {}
        venue_canonical = (
            venue_context.get("venue_name")
            if isinstance(venue_context.get("venue_name"), str)
            else canonicalize_venue_name(venue_raw)[0]
        )

        # Classification
        age_category = classify_age_category(hist_meta)
        stored_competition_code = hist_meta.get("competition_code") if hist_meta else None
        if isinstance(stored_competition_code, str) and stored_competition_code.strip():
            competition_code = stored_competition_code.strip()
            if competition_code.upper() == "UNKNOWN":
                competition_code = "unknown"
            competition_name = event_name or stored_competition_code.strip()
        else:
            competition_code, competition_name = classify_competition(
                event_name,
                match_format=game.match_type,
                team_names=[team_a_name, team_b_name],
                age_category=age_category,
            )
        gender_category = classify_gender(
            competition_code,
            (hist_meta.get("gender") if hist_meta else None)
            or (hist_meta.get("gender_category") if hist_meta else None),
        )
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

        entry = AnalystRegistryEntry(
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
        entries_with_sort.append(
            (
                _registry_sort_key(
                    entry,
                    game_created_at=created_at,
                    batch_created_at=getattr(batch, "created_at", None),
                ),
                entry,
            )
        )

    entries = [
        entry for _, entry in sorted(entries_with_sort, key=lambda item: item[0], reverse=True)
    ]

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
