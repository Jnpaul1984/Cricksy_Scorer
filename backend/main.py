from __future__ import annotations

from typing import Any

# App factory builds the ASGI and FastAPI apps (no side effects at import time)
from backend.app import create_app
from backend.sql_app import crud, models, schemas  # noqa: F401
from backend.sql_app.database import get_db as get_db
import logging

from backend.logging_setup import configure_logging

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

    _recompute_totals_and_runtime = _gh._recompute_totals_and_runtime
    _rebuild_scorecards_from_deliveries = _gh._rebuild_scorecards_from_deliveries
    _maybe_finalize_match = _gh._maybe_finalize_match
    _ensure_target_if_chasing = _gh._ensure_target_if_chasing
except Exception:
    pass

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
