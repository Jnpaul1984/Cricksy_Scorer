from __future__ import annotations

from functools import lru_cache
from typing import Literal

# âœ… Import from the correct package path
# If this file is at backend/services/dls_services.py and your DLS package is backend/services/dls/,
# then the correct absolute import is:
from backend.services.dls import load_international_table, calculate_dls_target
# (If you ever move this into another package level,
# a relative import would be: from .dls import ...)

FormatOvers = Literal[20, 50]


@lru_cache(maxsize=2)
def _get_table(fmt: FormatOvers):
    # fmt will be 20 or 50; ensure it's int for safety
    return load_international_table(int(fmt))


def resource_remaining(fmt: FormatOvers, *, balls_left: int, wickets_lost: int) -> float:
    """
    Return the DLS resource percentage remaining for the given match format,
    balls left, and wickets lost.
    """
    tbl = _get_table(fmt)
    # Clamp here as well (DLSTable.resource also clamps)
    balls_left = max(0, min(int(balls_left), tbl.max_balls))
    wickets_lost = max(0, min(int(wickets_lost), 9))
    return float(tbl.resource(balls_left=balls_left, wickets_lost=wickets_lost))


def calc_target(team1_score: int, team1_res: float, team2_res: float, G50: int = 245) -> int:
    """
    Standard Edition target calculation wrapper.
    """
    return int(calculate_dls_target(int(team1_score), float(team1_res), float(team2_res), int(G50)))
