from __future__ import annotations

import contextlib
import logging
import os
from typing import Any

# Optional early instrumentation for asyncpg (see backend/debug_asyncpg.py).
# Importing it early ensures we catch any asyncpg.connect/create_pool calls
# that happen during app/module import time.
if os.getenv("CRICKSY_DEBUG_ASYNCPG") == "1":
    with contextlib.suppress(Exception):
        pass  # type: ignore  # nosec

from backend.app import create_app
from backend.logging_setup import configure_logging
from backend.sql_app import (
    crud,  # Re-exported for tests
    models,  # Re-exported for tests
    schemas,  # Re-exported for tests
)
from backend.sql_app.database import get_db as get_db

__all__ = [
    "ConcreteGameState",
    "app",
    "crud",
    "fastapi_app",
    "get_db",
    "models",
    "schemas",
]

configure_logging(json=True, level=logging.INFO)

# Build the ASGI app and expose a FastAPI instance for tests
app, _fastapi = create_app()
fastapi_app = _fastapi  # compatibility for tests


class ConcreteGameState:
    def __init__(self, id: str, team_a: dict[str, Any], team_b: dict[str, Any]):
        self.id = id
        self.team_a = team_a
        self.team_b = team_b
        self.match_type = "limited"
        self.status = "SCHEDULED"
        self.current_inning = 1
        self.total_runs = 0
        self.total_wickets = 0
        self.overs_completed = 0
        self.balls_this_over = 0
        self.is_game_over = False
        self.deliveries: list[dict[str, Any]] = []
        self.batting_scorecard: dict[str, Any] = {}
        self.bowling_scorecard: dict[str, Any] = {}

    async def save(self) -> None:  # no-op stub
        return None


# Re-export helper(s) that some tests import from backend.main
try:
    from backend.services import game_helpers as _gh

    _recompute_totals_and_runtime = getattr(_gh, "_recompute_totals_and_runtime", None)
    _rebuild_scorecards_from_deliveries = getattr(
        _gh, "_rebuild_scorecards_from_deliveries", None
    )
    _maybe_finalize_match = getattr(_gh, "_maybe_finalize_match", None)
    _ensure_target_if_chasing = getattr(_gh, "_ensure_target_if_chasing", None)
except Exception:
    pass  # nosec

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)  # nosec
