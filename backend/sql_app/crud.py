from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, Dict, Any

from . import models, schemas

async def get_game(db: AsyncSession, game_id: str) -> Optional[models.Game]:
    """
    Reads a single game from the database by its ID.
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
        status="in_progress",
    )
    db.add(db_game)
    await db.commit()
    await db.refresh(db_game)
    return db_game


async def update_game(db: AsyncSession, game_model: models.Game) -> models.Game:
    """
    Updates an existing game record in the database.
    """
    db.add(game_model)
    await db.commit()
    await db.refresh(game_model)
    return game_model
