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
