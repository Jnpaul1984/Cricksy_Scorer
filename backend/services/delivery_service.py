"""
Delivery service: persist a scored delivery.

This module provides a single, focused function:

    async def apply_scoring_and_persist(g: GameState, delivery_dict: dict, db: AsyncSession) -> GameState

It expects the caller to:
- have already rebuilt scorecards + recomputed totals (if needed)
- to have performed validation that depends on many helpers in main.py

Responsibilities:
- Call scoring_service.score_one (if caller asks it to compute the per-ball kwargs)
- Append the resulting delivery dict to g.deliveries
- flag_modified on the ORM object fields and call crud.update_game to persist
- return the updated ORM row (as GameState-like object)
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import BaseModel

from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app import crud, schemas
from backend.services.scoring_service import score_one as _score_one


async def apply_scoring_and_persist(
    g: Any,
    *,
    # Either pass the raw payload fields and let score_one compute kwargs:
    compute_kwargs: bool = True,
    striker_id: Optional[str] = None,
    non_striker_id: Optional[str] = None,
    bowler_id: Optional[str] = None,
    runs_scored: Optional[int] = 0,
    extra: Optional[str] = None,
    is_wicket: Optional[bool] = False,
    dismissal_type: Optional[str] = None,
    dismissed_player_id: Optional[str] = None,
    # Or pass a fully-formed delivery_dict (result of schemas.Delivery) to append directly:
    delivery_dict: Optional[Dict[str, Any]] = None,
    db: AsyncSession = None,
) -> Any:
    """
    Apply scoring to GameState-like `g`, append to g.deliveries and persist via crud.update_game.

    Returns the updated ORM row (GameState-like) returned by crud.update_game.
    """
    # compute delivery kwargs if requested
    if delivery_dict is None and compute_kwargs:
        # score_one returns a dict suitable for schemas.Delivery kw args
        kwargs = _score_one(
            g,
            striker_id=str(striker_id or ""),
            non_striker_id=str(non_striker_id or ""),
            bowler_id=str(bowler_id or ""),
            runs_scored=int(runs_scored or 0),
            extra=extra,
            is_wicket=bool(is_wicket),
            dismissal_type=dismissal_type,
            dismissed_player_id=dismissed_player_id,
        )
        # build a Pydantic Delivery to normalize wire format
        try:
            del_dict = schemas.Delivery(**kwargs).model_dump()
        except Exception:
            # fallback to raw dict if schema normalization fails
            del_dict = dict(kwargs)
    elif delivery_dict is not None:
        # trust that caller supplied a normalized delivery dict
        del_dict = dict(delivery_dict)
    else:
        raise ValueError("Either delivery_dict must be provided or compute_kwargs=True with proper args")

    # Ensure inning tag is present (best-effort)
    if "inning" not in del_dict:
        del_dict["inning"] = int(getattr(g, "current_inning", 1) or 1)

    # Optional extra fields caller may have provided (keep existing values if any)
    # e.g., shot_angle_deg, shot_map
    # Append to g.deliveries (ensure it's a mutable list)
    if not isinstance(getattr(g, "deliveries", None), list):
        g.deliveries = []  # type: ignore[assignment]

    g.deliveries = list(getattr(g, "deliveries", []))  # copy to concrete list
    g.deliveries.append(del_dict)

    # Ensure scorecards fields are persisted
    flag_modified(g, "deliveries")
    flag_modified(g, "batting_scorecard")
    flag_modified(g, "bowling_scorecard")

    # Persist via CRUD (pass the ORM row)
    updated = await crud.update_game(db=db, game_model=g)
    return updated
