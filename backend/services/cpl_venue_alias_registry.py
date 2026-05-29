from __future__ import annotations

import re

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")

_ALIASES: dict[str, tuple[str, str]] = {
    "brian lara stadium tarouba": ("Brian Lara Stadium, Tarouba", "brian_lara_stadium_tarouba"),
    "brian lara stadium tarouba trinidad": (
        "Brian Lara Stadium, Tarouba",
        "brian_lara_stadium_tarouba",
    ),
    "kensington oval bridgetown": ("Kensington Oval, Bridgetown", "kensington_oval_bridgetown"),
    "kensington oval bridgetown barbados": (
        "Kensington Oval, Bridgetown",
        "kensington_oval_bridgetown",
    ),
    "kensington oval": ("Kensington Oval, Bridgetown", "kensington_oval_bridgetown"),
    "queens park oval": ("Queen's Park Oval, Port of Spain", "queens_park_oval_port_of_spain"),
    "queen s park oval": ("Queen's Park Oval, Port of Spain", "queens_park_oval_port_of_spain"),
    "the oval": ("Kennington Oval, London, England", "kennington_oval_london_england"),
    "kennington oval": ("Kennington Oval, London, England", "kennington_oval_london_england"),
    "kennington oval london": (
        "Kennington Oval, London, England",
        "kennington_oval_london_england",
    ),
    "kia oval": ("Kennington Oval, London, England", "kennington_oval_london_england"),
    "the kia oval": ("Kennington Oval, London, England", "kennington_oval_london_england"),
    "providence stadium guyana": ("Providence Stadium", "providence_stadium"),
    "providence stadium": ("Providence Stadium", "providence_stadium"),
    "daren sammy national cricket stadium gros islet": (
        "Daren Sammy National Cricket Stadium, Gros Islet",
        "daren_sammy_national_cricket_stadium",
    ),
    "daren sammy national cricket stadium": (
        "Daren Sammy National Cricket Stadium, Gros Islet",
        "daren_sammy_national_cricket_stadium",
    ),
}


def normalize_venue_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = _NORMALIZE_RE.sub(" ", value.strip().lower())
    return " ".join(normalized.split())


def canonicalize_venue_name(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    normalized = normalize_venue_name(value)
    if not normalized:
        return None, None
    mapped = _ALIASES.get(normalized)
    if mapped:
        return mapped
    return value.strip(), normalized


def is_known_venue_alias(value: str | None) -> bool:
    normalized = normalize_venue_name(value)
    if not normalized:
        return False
    return normalized in _ALIASES
