"""Backend helper utilities (small, well-tested helpers).

This module is a safe place for pure helpers extracted from backend/main.py.
Start with overs_str_from_balls extracted from the original module.
"""
from __future__ import annotations

from typing import Final

__all__ = ["overs_str_from_balls"]

BALLS_PER_OVER: Final[int] = 6


def overs_str_from_balls(balls: int) -> str:
    """Return a string in 'overs.balls' format for a given legal-ball count.

    Examples:
      0 -> "0.0"
      6 -> "1.0"
      7 -> "1.1"
    """
    # Accept int-like values but prefer ints to keep behavior explicit
    try:
        b = int(balls)
    except Exception as exc:  # defensive
        raise TypeError("balls must be an integer-like value") from exc
    return f"{b // BALLS_PER_OVER}.{b % BALLS_PER_OVER}"


