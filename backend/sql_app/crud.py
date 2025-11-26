# sql_app/crud.py
import json
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas


def _coerce_result_to_text(value: Any) -> str | None:
    """
    The games.result column is stored as TEXT. Preserve structured payloads whenever possible
    so downstream consumers can deserialize them back into rich objects.
    """
    if value is None:
        return None

    if isinstance(value, str):
        return value

    # Pydantic models expose model_dump(); prefer full JSON for round-tripping.
    if hasattr(value, "model_dump"):
        try:
            data = value.model_dump(mode="json")
        except Exception:
            data = value.model_dump()
        return json.dumps(data, ensure_ascii=False, default=str)

    # Dataclasses can be serialized via asdict
    try:
        from dataclasses import asdict, is_dataclass

        if is_dataclass(value) and not isinstance(value, type):
            return json.dumps(asdict(cast(Any, value)), ensure_ascii=False)
    except Exception:
        pass  # nosec

    if hasattr(value, "__dict__"):
        try:
            return json.dumps(vars(value), ensure_ascii=False, default=str)
        except Exception:
            pass  # nosec

    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(value, ensure_ascii=False, default=str)
        except Exception:
            pass  # nosec

    try:
        import enum

        if isinstance(value, enum.Enum):
            return str(value.value)
    except Exception:
        pass  # nosec

    return str(value)


async def get_game(db: AsyncSession, game_id: str) -> models.Game | None:
    """
    Read a single game from the database by its ID.
    """
    result = await db.execute(select(models.Game).filter(models.Game.id == game_id))
    return result.scalar_one_or_none()


async def create_game(
    db: AsyncSession,
    game: schemas.GameCreate,
    game_id: str,
    batting_team: str,
    bowling_team: str,
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    batting_scorecard: dict[str, Any],
    bowling_scorecard: dict[str, Any],
) -> models.Game:
    """
    Insert a new game row. Status string remains 'in_progress' to match current code paths.
    """
    db_game = models.Game(
        id=game_id,
        team_a=team_a,
        team_b=team_b,
        match_type=game.match_type,
        overs_limit=game.overs_limit,
        days_limit=game.days_limit,
        overs_per_day=game.overs_per_day,
        dls_enabled=game.dls_enabled,
        interruptions=game.interruptions,
        toss_winner_team=game.toss_winner_team,
        decision=game.decision,
        batting_team_name=batting_team,
        bowling_team_name=bowling_team,
        batting_scorecard=batting_scorecard,
        bowling_scorecard=bowling_scorecard,
        # Start at innings 0 / break so the UI prompts "Start Innings"
        current_inning=0,
        status="innings_break",
    )
    db.add(db_game)
    await db.commit()
    await db.refresh(db_game)
    return db_game


async def update_game(db: AsyncSession, game_model: models.Game) -> models.Game:
    """
    Update an existing game record.
    IMPORTANT: Coerce any complex 'result' object to TEXT before commit to avoid DBAPI type errors.
    """
    if hasattr(game_model, "result"):
        try:
            game_model.result = _coerce_result_to_text(game_model.result)
        except Exception:
            # Defensive: never let result serialization block the commit
            try:
                game_model.result = str(game_model.result)
            except Exception:
                game_model.result = None

    db.add(game_model)
    await db.commit()
    await db.refresh(game_model)
    return game_model
