"""
Route handler implementations for /games endpoints.

This module contains the extracted implementation logic for the main /games routes.
It intentionally does NOT include FastAPI decorators so it can be imported by
backend.main without creating circular imports. main.py will keep the route
decorators and call these functions.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, cast

from sqlalchemy.ext.asyncio import AsyncSession

from backend.services import delivery_service
from backend.services import game_helpers as gh
from backend.services import game_service, scoring_service
from backend.sql_app import crud, schemas


async def create_game_impl(payload: Any, db: AsyncSession) -> schemas.Game:
    """
    Delegate orchestration of game creation to game_service.
    Payload is the Pydantic CreateGameRequest instance passed from main.py.
    """
    db_game = await game_service.create_game(payload, db)
    return db_game


async def get_game_impl(game_id: str, db: AsyncSession) -> Optional[schemas.Game]:
    """
    Return the Game ORM row (or None) for the given ID.
    main.py will convert/return the proper response model.
    """
    return await crud.get_game(db=db, game_id=game_id)


async def build_snapshot_impl(
    db_game: Any, last_delivery: Optional[Mapping[str, Any]] = None
) -> Dict[str, Any]:
    """
    Build the snapshot dict from the ORM game row using helpers.
    main.py previously used _snapshot_from_game; we replicate the semantics by
    calling helpers and returning the snapshot mapping.
    """
    # Rebuild scorecards & totals in memory (helpers operate on game-like object)
    gh._rebuild_scorecards_from_deliveries(db_game)
    gh._recompute_totals_and_runtime(db_game)

    # Snapshot builder in main.py references many fields; reuse main._snapshot_from_game if available.
    # To avoid importing main, build a minimal snapshot consistent with tests:
    snap: Dict[str, Any] = {}
    snap["id"] = getattr(db_game, "id", None)
    snap["team_a"] = getattr(db_game, "team_a", {})
    snap["team_b"] = getattr(db_game, "team_b", {})
    snap["batting_team_name"] = getattr(db_game, "batting_team_name", None)
    snap["bowling_team_name"] = getattr(db_game, "bowling_team_name", None)
    snap["total_runs"] = getattr(db_game, "total_runs", 0)
    snap["total_wickets"] = getattr(db_game, "total_wickets", 0)
    snap["overs"] = gh._overs_string_from_ledger(db_game)
    snap["batting_scorecard"] = getattr(db_game, "batting_scorecard", {}) or {}
    snap["bowling_scorecard"] = getattr(db_game, "bowling_scorecard", {}) or {}
    snap["deliveries"] = getattr(db_game, "deliveries", []) or []
    snap["current_striker_id"] = getattr(db_game, "current_striker_id", None)
    snap["current_non_striker_id"] = getattr(db_game, "current_non_striker_id", None)
    snap["current_bowler_id"] = getattr(db_game, "current_bowler_id", None)
    snap["last_ball_bowler_id"] = getattr(db_game, "last_ball_bowler_id", None)
    # snapshot flags (needs_new_batter/neew_new_over)
    snap.update(gh._compute_snapshot_flags(db_game))
    return snap


async def append_delivery_and_persist_impl(
    db_game: Any,
    *,
    delivery_dict: Optional[Dict[str, Any]] = None,
    compute_kwargs: bool = False,
    striker_id: Optional[str] = None,
    non_striker_id: Optional[str] = None,
    bowler_id: Optional[str] = None,
    runs_scored: Optional[int] = 0,
    extra: Optional[str] = None,
    is_wicket: Optional[bool] = False,
    dismissal_type: Optional[str] = None,
    dismissed_player_id: Optional[str] = None,
    db: AsyncSession,
) -> Any:
    """
    Append a delivery (either prebuilt or computed via scoring_service.score_one)
    and persist using delivery_service. Returns the updated ORM row.
    """
    if delivery_dict is not None:
        updated = await delivery_service.apply_scoring_and_persist(
            db_game,
            compute_kwargs=False,
            delivery_dict=delivery_dict,
            db=db,
        )
    else:
        # Let delivery_service compute the kwargs via scoring_service
        updated = await delivery_service.apply_scoring_and_persist(
            db_game,
            compute_kwargs=True,
            striker_id=striker_id,
            non_striker_id=non_striker_id,
            bowler_id=bowler_id,
            runs_scored=runs_scored,
            extra=extra,
            is_wicket=is_wicket,
            dismissal_type=dismissal_type,
            dismissed_player_id=dismissed_player_id,
            db=db,
        )
    return updated
