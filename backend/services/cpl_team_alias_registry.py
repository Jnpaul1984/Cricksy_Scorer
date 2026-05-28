from __future__ import annotations

import re

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")

_ALIASES: dict[str, tuple[str, str]] = {
    "barbados royals": ("Barbados Royals", "barbados_franchise"),
    "barbados tridents": ("Barbados Royals", "barbados_franchise"),
    "guyana amazon warriors": ("Guyana Amazon Warriors", "guyana_franchise"),
    "jamaica tallawahs": ("Jamaica Tallawahs", "jamaica_franchise"),
    "st kitts and nevis patriots": (
        "St Kitts & Nevis Patriots",
        "st_kitts_and_nevis_franchise",
    ),
    "st kitts nevis patriots": (
        "St Kitts & Nevis Patriots",
        "st_kitts_and_nevis_franchise",
    ),
    "st lucia kings": ("St Lucia Kings", "st_lucia_franchise"),
    "st lucia stars": ("St Lucia Kings", "st_lucia_franchise"),
    "st lucia zouks": ("St Lucia Kings", "st_lucia_franchise"),
    "trinbago knight riders": ("Trinbago Knight Riders", "trinbago_franchise"),
    "trinidad and tobago red steel": ("Trinbago Knight Riders", "trinbago_franchise"),
    "trinidad tobago red steel": ("Trinbago Knight Riders", "trinbago_franchise"),
}


def normalize_team_name(value: str | None) -> str:
    if not value:
        return ""
    normalized = _NORMALIZE_RE.sub(" ", value.strip().lower())
    return " ".join(normalized.split())


def canonicalize_team_name(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    normalized = normalize_team_name(value)
    if not normalized:
        return None, None
    mapped = _ALIASES.get(normalized)
    if mapped:
        return mapped
    return value.strip(), normalized


def is_known_team_alias(value: str | None) -> bool:
    normalized = normalize_team_name(value)
    if not normalized:
        return False
    return normalized in _ALIASES
