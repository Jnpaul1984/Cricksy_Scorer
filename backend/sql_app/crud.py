# sql_app/crud.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any
import json

from . import models, schemas


def _coerce_result_to_text(value: Any) -> str | None:
    """
    Your DB column 'games.result' is TEXT/VARCHAR. Ensure we always write a string.
    Prefer a human-readable 'result_text' when present (e.g. 'Alpha won by 3 runs').
    Otherwise stringify or JSON-dump as a last resort.
    """
    if value is None:
        return None

    # Pydantic v2 model?
    try:
        if hasattr(value, "model_dump"):
            data = value.model_dump()
            if isinstance(data, dict) and data.get("result_text"):
                return str(data["result_text"])
            return json.dumps(data, ensure_ascii=False)
    except Exception:
        pass

    # Plain dataclass / object with attribute
    if hasattr(value, "result_text"):
        try:
            rt = getattr(value, "result_text")
            if rt:
                return str(rt)
        except Exception:
            pass

    # Dict/list → JSON
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            pass

    # Enum? (e.g., value.value)
    try:
        import enum
        if isinstance(value, enum.Enum):
            return str(value.value)
    except Exception:
        pass

    # Fallback: plain string
    return str(value)


async def get_game(db: AsyncSession, game_id: str) -> Optional[models.Game]:
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
    team_a: Dict[str, Any],
    team_b: Dict[str, Any],
    batting_scorecard: Dict[str, Any],
    bowling_scorecard: Dict[str, Any],
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
        # Keep your existing casing; tests do not assert on this exact literal
        status="in_progress",
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
