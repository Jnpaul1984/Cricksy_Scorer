from __future__ import annotations

import sys
from contextlib import suppress
from enum import Enum
from importlib import import_module
from typing import Any, cast

from backend.sql_app import crud, models, schemas


class InMemoryCrudRepository:
    """Lightweight in-memory stand-in for SQLAlchemy CRUD used during CI."""

    def __init__(self) -> None:
        self._games: dict[str, models.Game] = {}

    async def list_games_with_result(self) -> list[models.Game]:
        """Return all games that have a non-null result."""
        return [g for g in self._games.values() if getattr(g, "result", None)]

    async def create_game(
        self,
        db: object,
        *,
        game: schemas.GameCreate,
        game_id: str,
        batting_team: str,
        bowling_team: str,
        team_a: dict[str, Any],
        team_b: dict[str, Any],
        batting_scorecard: dict[str, Any],
        bowling_scorecard: dict[str, Any],
    ) -> models.Game:
        g = models.Game(
            id=game_id,
            team_a=team_a,
            team_b=team_b,
            match_type=(
                game.match_type.value if isinstance(game.match_type, Enum) else str(game.match_type)
            ),
            overs_limit=game.overs_limit,
            days_limit=game.days_limit,
            overs_per_day=game.overs_per_day,
            dls_enabled=game.dls_enabled,
            interruptions=game.interruptions,
            toss_winner_team=game.toss_winner_team,
            decision=game.decision,
            batting_team_name=batting_team,
            bowling_team_name=bowling_team,
            status=models.GameStatus.innings_break,
            total_runs=0,
            total_wickets=0,
            overs_completed=0,
            balls_this_over=0,
            current_striker_id=None,
            current_non_striker_id=None,
            deliveries=[],
            batting_scorecard=batting_scorecard,
            bowling_scorecard=bowling_scorecard,
        )

        g.current_inning = 0
        g.current_bowler_id = None
        g.last_ball_bowler_id = None
        g.current_over_balls = 0
        g.mid_over_change_used = False
        g.needs_new_over = True
        g.needs_new_batter = True
        # g.needs_new_innings is computed from status
        g.first_inning_summary = None
        g.target = None
        g.result = None
        # g.is_game_over is computed from status
        g.completed_at = None
        g.extras_totals = {
            "wides": 0,
            "no_balls": 0,
            "byes": 0,
            "leg_byes": 0,
            "penalty": 0,
            "total": 0,
        }
        g.fall_of_wickets = []
        g.phases = {}
        g.projections = {}
        g.innings_history = []

        self._games[game_id] = g
        return g

    async def get_game(self, db: object, game_id: str) -> models.Game | None:
        return self._games.get(game_id)

    async def update_game(self, db: object, game_model: models.Game) -> models.Game:
        # Ensure result is always a string (JSON) for compatibility with endpoints
        import json

        result_value = getattr(game_model, "result", None)
        if result_value is not None and not isinstance(result_value, str):
            if hasattr(result_value, "model_dump"):
                try:
                    data = result_value.model_dump(mode="json")
                except Exception:
                    data = result_value.model_dump()
                result_value = json.dumps(data, ensure_ascii=False, default=str)
            elif isinstance(result_value, (dict, list, tuple)):
                result_value = json.dumps(result_value, ensure_ascii=False, default=str)
            else:
                try:
                    result_value = json.dumps(result_value, ensure_ascii=False, default=str)
                except Exception:
                    result_value = str(result_value)
            game_model.result = result_value
        self._games[game_model.id] = game_model
        return game_model


def enable_in_memory_crud(repository: InMemoryCrudRepository) -> None:
    """Patch the global CRUD module to use the supplied in-memory repository."""

    targets = [crud]

    # The backend imports CRUD via both ``sql_app`` and ``backend.sql_app``.
    # Ensure we replace the functions on every loaded module alias.
    module = sys.modules.get("sql_app.crud")
    if module is None:
        try:
            module = import_module("sql_app.crud")
        except ModuleNotFoundError:
            module = None
    if module is not None:
        targets.append(module)

    for target in targets:
        target_any = cast(Any, target)
        try:
            print(
                "DEBUG: patching in-memory CRUD target",
                getattr(target_any, "__name__", str(target_any)),
            )
        except Exception:
            print("DEBUG: patching in-memory CRUD target (unknown) ->", target_any)
        target_any.create_game = repository.create_game
        target_any.get_game = repository.get_game
        target_any.update_game = repository.update_game
        target_any.list_games_with_result = repository.list_games_with_result
        with suppress(Exception):
            print(
                "DEBUG: patched target create_game ->",
                getattr(target_any, "create_game", None),
            )
