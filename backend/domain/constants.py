from __future__ import annotations

from typing import Final

__all__ = [
    "CREDIT_BOWLER",
    "CREDIT_TEAM",
    "INVALID_ON_NO_BALL",
    "INVALID_ON_WIDE",
    "as_extra_code",
    "norm_extra",
]

# Dismissal credit rules
CREDIT_BOWLER: Final[frozenset[str]] = frozenset(
    {"bowled", "caught", "lbw", "stumped", "hit_wicket"}
)
CREDIT_TEAM: Final[frozenset[str]] = frozenset(
    {
        "run_out",
        "obstructing_the_field",
        "hit_ball_twice",
        "timed_out",
        "retired_out",
        "handled_ball",
    }
)

# Invalid dismissals under specific extras
INVALID_ON_NO_BALL: Final[frozenset[str]] = frozenset(
    {"bowled", "caught", "lbw", "stumped", "hit_wicket"}
)
INVALID_ON_WIDE: Final[frozenset[str]] = frozenset({"bowled", "lbw"})

# Canonical short codes for extras
_EXTRA_MAP: dict[str, str] = {
    "wd": "wd",
    "nb": "nb",
    "b": "b",
    "lb": "lb",
}


def norm_extra(x: str | None | object) -> str | None:
    """
    Normalize to canonical extra codes: None | 'wd' | 'nb' | 'b' | 'lb'.
    Accept several synonyms to keep inbound payload flexibility.
    """
    if not x:
        return None
    s = (str(x) or "").strip().lower()
    if s in {"wide", "wd"}:
        return "wd"
    if s in {"no_ball", "nb"}:
        return "nb"
    if s in {"b", "bye"}:
        return "b"
    if s in {"lb", "leg_bye", "leg-bye"}:
        return "lb"
    return None


def as_extra_code(x: str | None) -> str | None:
    """
    Return the canonical short code for an extra, or None.
    """
    if x is None:
        return None
    return _EXTRA_MAP.get(x)
