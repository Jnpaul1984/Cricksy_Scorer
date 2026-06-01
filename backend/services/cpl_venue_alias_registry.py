from __future__ import annotations

import re
from dataclasses import dataclass

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")
_CPL_CONTEXT_CODES = frozenset({"CPL_MEN", "WCPL"})
_CPL_CONTEXT_NAMES = (
    "caribbean premier league",
    "women's caribbean premier league",
    "womens caribbean premier league",
)


@dataclass(frozen=True, slots=True)
class VenueIdentity:
    key: str
    display_name: str
    city: str | None = None
    country: str | None = None


@dataclass(frozen=True, slots=True)
class VenueResolution:
    canonical_venue_key: str
    canonical_display_name: str
    raw_venue_name: str
    source_method: str
    confidence: str
    city: str | None = None
    country: str | None = None


_IDENTITIES: dict[str, VenueIdentity] = {
    "brian_lara_stadium_tarouba": VenueIdentity(
        key="brian_lara_stadium_tarouba",
        display_name="Brian Lara Stadium, Tarouba, Trinidad",
        city="Tarouba",
        country="Trinidad",
    ),
    "kensington_oval_bridgetown": VenueIdentity(
        key="kensington_oval_bridgetown",
        display_name="Kensington Oval, Bridgetown, Barbados",
        city="Bridgetown",
        country="Barbados",
    ),
    "queens_park_oval_port_of_spain_trinidad": VenueIdentity(
        key="queens_park_oval_port_of_spain_trinidad",
        display_name="Queen's Park Oval, Port of Spain, Trinidad",
        city="Port of Spain",
        country="Trinidad",
    ),
    "kennington_oval_london_england": VenueIdentity(
        key="kennington_oval_london_england",
        display_name="Kennington Oval, London, England",
        city="London",
        country="England",
    ),
    "providence_stadium": VenueIdentity(
        key="providence_stadium",
        display_name="Providence Stadium, Guyana",
        city=None,
        country="Guyana",
    ),
    "daren_sammy_national_cricket_stadium_gros_islet_st_lucia": VenueIdentity(
        key="daren_sammy_national_cricket_stadium_gros_islet_st_lucia",
        display_name="Daren Sammy National Cricket Stadium, Gros Islet, St Lucia",
        city="Gros Islet",
        country="St Lucia",
    ),
    "sir_vivian_richards_stadium_north_sound_antigua": VenueIdentity(
        key="sir_vivian_richards_stadium_north_sound_antigua",
        display_name="Sir Vivian Richards Stadium, North Sound, Antigua",
        city="North Sound",
        country="Antigua",
    ),
}

_ALIASES: dict[str, str] = {
    "brian lara stadium tarouba": "brian_lara_stadium_tarouba",
    "brian lara stadium tarouba trinidad": "brian_lara_stadium_tarouba",
    "kensington oval bridgetown": "kensington_oval_bridgetown",
    "kensington oval bridgetown barbados": "kensington_oval_bridgetown",
    "kensington oval": "kensington_oval_bridgetown",
    "queens park oval": "queens_park_oval_port_of_spain_trinidad",
    "queen s park oval": "queens_park_oval_port_of_spain_trinidad",
    "queens park oval port of spain": "queens_park_oval_port_of_spain_trinidad",
    "queens park oval port of spain trinidad": "queens_park_oval_port_of_spain_trinidad",
    "queen s park oval port of spain": "queens_park_oval_port_of_spain_trinidad",
    "queen s park oval port of spain trinidad": "queens_park_oval_port_of_spain_trinidad",
    "the oval": "kennington_oval_london_england",
    "kennington oval": "kennington_oval_london_england",
    "kennington oval london": "kennington_oval_london_england",
    "kia oval": "kennington_oval_london_england",
    "the kia oval": "kennington_oval_london_england",
    "providence stadium guyana": "providence_stadium",
    "providence stadium": "providence_stadium",
    "daren sammy national cricket stadium gros islet": (
        "daren_sammy_national_cricket_stadium_gros_islet_st_lucia"
    ),
    "daren sammy national cricket stadium gros islet st lucia": (
        "daren_sammy_national_cricket_stadium_gros_islet_st_lucia"
    ),
    "daren sammy national cricket stadium": (
        "daren_sammy_national_cricket_stadium_gros_islet_st_lucia"
    ),
    "sir vivian richards stadium north sound": "sir_vivian_richards_stadium_north_sound_antigua",
    "sir vivian richards stadium north sound antigua": (
        "sir_vivian_richards_stadium_north_sound_antigua"
    ),
}

_CPL_CONTEXT_ALIASES: dict[str, str] = {
    "gros islet": "daren_sammy_national_cricket_stadium_gros_islet_st_lucia",
    "north sound": "sir_vivian_richards_stadium_north_sound_antigua",
    "port of spain": "queens_park_oval_port_of_spain_trinidad",
}


def normalize_venue_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = _NORMALIZE_RE.sub(" ", value.strip().lower())
    return " ".join(normalized.split())


def _canonical_from_key(
    identity_key: str, raw_value: str, source_method: str, confidence: str
) -> VenueResolution:
    identity = _IDENTITIES[identity_key]
    return VenueResolution(
        canonical_venue_key=identity.key,
        canonical_display_name=identity.display_name,
        raw_venue_name=raw_value,
        source_method=source_method,
        confidence=confidence,
        city=identity.city,
        country=identity.country,
    )


def _is_cpl_context(competition_name: str | None, competition_code: str | None) -> bool:
    if competition_code and competition_code.strip().upper() in _CPL_CONTEXT_CODES:
        return True
    if not competition_name:
        return False
    normalized = normalize_venue_name(competition_name)
    return normalized in _CPL_CONTEXT_NAMES


def resolve_venue_identity(
    raw_venue_name: str | None,
    *,
    competition_name: str | None = None,
    competition_code: str | None = None,
) -> VenueResolution | None:
    if not raw_venue_name:
        return None
    raw_value = raw_venue_name.strip()
    if not raw_value:
        return None
    normalized = normalize_venue_name(raw_value)
    if not normalized:
        return None

    identity_key = _ALIASES.get(normalized)
    if identity_key:
        return _canonical_from_key(identity_key, raw_value, "explicit_alias", "high")

    if _is_cpl_context(competition_name, competition_code):
        context_key = _CPL_CONTEXT_ALIASES.get(normalized)
        if context_key:
            return _canonical_from_key(
                context_key, raw_value, "competition_context_alias", "medium"
            )

    return VenueResolution(
        canonical_venue_key=normalized,
        canonical_display_name=raw_value,
        raw_venue_name=raw_value,
        source_method="raw_fallback",
        confidence="low",
    )


def canonicalize_venue_name(value: str | None) -> tuple[str | None, str | None]:
    resolution = resolve_venue_identity(value)
    if resolution is None:
        return None, None
    return resolution.canonical_display_name, resolution.canonical_venue_key


def is_known_venue_alias(value: str | None) -> bool:
    normalized = normalize_venue_name(value)
    if not normalized:
        return False
    return normalized in _ALIASES
