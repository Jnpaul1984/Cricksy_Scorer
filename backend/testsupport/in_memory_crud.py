from __future__ import annotations

from typing import Any, Dict
from enum import Enum
from importlib import import_module
import sys

from backend.sql_app import crud, models, schemas


class InMemoryCrudRepository:
    """Lightweight in-memory stand-in for SQLAlchemy CRUD used during CI."""

    def __init__(self) -> None:
        self._games: Dict[str, models.Game] = {}

    async def create_game(
        self,
        db: object,
        *,
        game: schemas.GameCreate,
        game_id: str,
        batting_team: str,
        bowling_team: str,
        team_a: Dict[str, Any],
        team_b: Dict[str, Any],
        batting_scorecard: Dict[str, Any],
        bowling_scorecard: Dict[str, Any],
    ) -> models.Game:
        g = models.Game(
            id=game_id,
            team_a=team_a,
            team_b=team_b,
            match_type=game.match_type.value if isinstance(game.match_type, Enum) else str(game.match_type),
            overs_limit=game.overs_limit,
            days_limit=game.days_limit,
            overs_per_day=game.overs_per_day,
            dls_enabled=game.dls_enabled,
            interruptions=game.interruptions,
            toss_winner_team=game.toss_winner_team,
            decision=game.decision,
            batting_team_name=batting_team,
            bowling_team_name=bowling_team,
            status=models.GameStatus.in_progress,
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

        g.current_inning = 1
        g.current_bowler_id = None
        g.last_ball_bowler_id = None
        g.current_over_balls = 0
        g.mid_over_change_used = False
        g.needs_new_over = True
        g.needs_new_batter = True
        g.needs_new_innings = False
        g.first_inning_summary = None
        g.target = None
        g.result = None
        g.is_game_over = False
        g.completed_at = None
        g.extras_totals = {"wides": 0, "no_balls": 0, "byes": 0, "leg_byes": 0, "penalty": 0, "total": 0}
        g.fall_of_wickets = []
        g.phases = {}
        g.projections = {}
        g.innings_history = []

        self._games[game_id] = g
        return g

    async def get_game(self, db: object, game_id: str) -> models.Game | None:
        return self._games.get(game_id)

    async def update_game(self, db: object, game_model: models.Game) -> models.Game:
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
        target.create_game = repository.create_game  # type: ignore[assignment]
        target.get_game = repository.get_game  # type: ignore[assignment]
        target.update_game = repository.update_game  # type: ignore[assignment]



