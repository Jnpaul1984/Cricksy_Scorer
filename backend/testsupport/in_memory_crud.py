from __future__ import annotations

import datetime as dt
import sys
import uuid
from contextlib import suppress
from enum import Enum
from importlib import import_module
from typing import Any, cast

from backend.sql_app import crud, models, schemas, tournament_crud


class InMemoryCrudRepository:
    """Lightweight in-memory stand-in for SQLAlchemy CRUD used during CI."""

    def __init__(self) -> None:
        self._games: dict[str, models.Game] = {}
        self._tournaments: dict[str, models.Tournament] = {}
        self._tournament_teams: dict[int, models.TournamentTeam] = {}
        self._fixtures: dict[str, models.Fixture] = {}
        self._team_id_counter = 1

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

        # Also insert into the actual SQLite database for routes that use raw queries
        try:
            from sqlalchemy.ext.asyncio import AsyncSession

            if isinstance(db, AsyncSession):
                db.add(g)
                await db.commit()
                await db.refresh(g)
        except Exception:
            pass  # nosec - fallback to in-memory only

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

    async def create_tournament_eager(
        self, db: object, tournament: schemas.TournamentCreate
    ) -> models.Tournament:
        t_id = str(uuid.uuid4())
        db_obj = models.Tournament(
            id=t_id,
            name=tournament.name,
            description=tournament.description,
            tournament_type=tournament.tournament_type,
            start_date=tournament.start_date,
            end_date=tournament.end_date,
            status="upcoming",
            created_at=dt.datetime.now(dt.UTC),
            updated_at=dt.datetime.now(dt.UTC),
            teams=[],
            fixtures=[],
        )
        self._tournaments[t_id] = db_obj
        return db_obj

    async def get_tournaments(
        self, db: object, skip: int = 0, limit: int = 100
    ) -> list[models.Tournament]:
        return list(self._tournaments.values())[skip : skip + limit]

    async def get_tournament(self, db: object, tournament_id: str) -> models.Tournament | None:
        return self._tournaments.get(tournament_id)

    async def add_team_to_tournament(
        self, db: object, tournament_id: str, team_data: schemas.TeamAdd
    ) -> models.TournamentTeam | None:
        t = self._tournaments.get(tournament_id)
        if not t:
            return None

        team_id = self._team_id_counter
        self._team_id_counter += 1

        team = models.TournamentTeam(
            id=team_id,
            tournament_id=tournament_id,
            team_name=team_data.team_name,
            team_data=team_data.team_data,
            matches_played=0,
            matches_won=0,
            matches_lost=0,
            matches_drawn=0,
            points=0,
            net_run_rate=0.0,
        )
        self._tournament_teams[team_id] = team
        return team

    async def get_tournament_teams(
        self, db: object, tournament_id: str
    ) -> list[models.TournamentTeam]:
        return [t for t in self._tournament_teams.values() if t.tournament_id == tournament_id]

    async def create_fixture(self, db: object, fixture_in: schemas.FixtureCreate) -> models.Fixture:
        f_id = str(uuid.uuid4())
        fixture = models.Fixture(
            id=f_id,
            tournament_id=fixture_in.tournament_id,
            match_number=fixture_in.match_number,
            team_a_name=fixture_in.team_a_name,
            team_b_name=fixture_in.team_b_name,
            venue=fixture_in.venue,
            scheduled_date=fixture_in.scheduled_date,
            status="scheduled",
            created_at=dt.datetime.now(dt.UTC),
            updated_at=dt.datetime.now(dt.UTC),
        )
        self._fixtures[f_id] = fixture
        return fixture

    async def get_fixture(self, db: object, fixture_id: str) -> models.Fixture | None:
        return self._fixtures.get(fixture_id)

    async def get_tournament_fixtures(self, db: object, tournament_id: str) -> list[models.Fixture]:
        return [f for f in self._fixtures.values() if f.tournament_id == tournament_id]

    async def get_points_table(
        self, db: object, tournament_id: str
    ) -> list[schemas.PointsTableEntry]:
        teams = await self.get_tournament_teams(db, tournament_id)
        return [
            schemas.PointsTableEntry(
                team_name=team.team_name,
                matches_played=team.matches_played,
                matches_won=team.matches_won,
                matches_lost=team.matches_lost,
                matches_drawn=team.matches_drawn,
                points=team.points,
                net_run_rate=team.net_run_rate,
            )
            for team in teams
        ]


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

    # Patch tournament_crud
    tournament_targets = [tournament_crud]
    module = sys.modules.get("backend.sql_app.tournament_crud")
    if module is not None:
        tournament_targets.append(module)

    for target in tournament_targets:
        target_any = cast(Any, target)
        target_any.create_tournament_eager = repository.create_tournament_eager
        target_any.get_tournaments = repository.get_tournaments
        target_any.get_tournament = repository.get_tournament
        target_any.add_team_to_tournament = repository.add_team_to_tournament
        target_any.get_tournament_teams = repository.get_tournament_teams
        target_any.create_fixture = repository.create_fixture
        target_any.get_fixture = repository.get_fixture
        target_any.get_tournament_fixtures = repository.get_tournament_fixtures
        target_any.get_points_table = repository.get_points_table
        target_any.add_team_to_tournament = repository.add_team_to_tournament
        target_any.get_tournament_teams = repository.get_tournament_teams
        target_any.create_fixture = repository.create_fixture
        target_any.get_fixture = repository.get_fixture
        target_any.get_tournament_fixtures = repository.get_tournament_fixtures
        target_any.get_points_table = repository.get_points_table
