from __future__ import annotations

import re

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")

_ALIASES: dict[str, tuple[str, str]] = {
    "barbados royals": ("Barbados Royals", "barbados_franchise"),
    "barbados tridents": ("Barbados Royals", "barbados_franchise"),
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

