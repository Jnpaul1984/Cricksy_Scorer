from __future__ import annotations

import datetime as dt
import json
from collections.abc import Mapping, Sequence
from typing import Annotated, Any, TypedDict, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

# NOTE: add crud here so we can honor in-memory mode via dependency overrides
from backend.sql_app import crud, models, schemas
from backend.sql_app.database import get_db  # async generator -> AsyncSession

UTC = getattr(dt, "UTC", dt.UTC)

router = APIRouter(prefix="/games", tags=["games"])


# --- Typed JSON helpers to satisfy Pylance ---
class PlayerJSON(TypedDict, total=False):
    id: str  # UUID as string is fine for transport/JSON
    name: str


class TeamJSON(TypedDict, total=False):
    name: str
    players: Sequence[PlayerJSON]


def _ids_from_team_json(team_json: dict[str, Any] | None) -> set[str]:
    if not team_json:
        return set()
    players: Sequence[PlayerJSON] = cast(Sequence[PlayerJSON], team_json.get("players") or [])
    ids: set[str] = set()
    for p in players:
        pid = p.get("id")
        if isinstance(pid, str) and pid:
            ids.add(pid)
    return ids


@router.post("/{game_id}/playing-xi", response_model=schemas.PlayingXIResponse)
async def set_playing_xi(
    game_id: UUID,
    payload: schemas.PlayingXIRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.PlayingXIResponse:
    game = await crud.get_game(db, game_id=str(game_id))
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    team_a_json: dict[str, Any] = (game.team_a or {}).copy()
    team_b_json: dict[str, Any] = (game.team_b or {}).copy()

    allowed_a = _ids_from_team_json(team_a_json)
    allowed_b = _ids_from_team_json(team_b_json)

    req_a = set(map(str, payload.team_a))
    req_b = set(map(str, payload.team_b))

    if not req_a.issubset(allowed_a):
        unknown = sorted(req_a - allowed_a)
        raise HTTPException(
            status_code=400,
            detail={"error": "Unknown players in team A XI", "ids": unknown},
        )

    if not req_b.issubset(allowed_b):
        unknown = sorted(req_b - allowed_b)
        raise HTTPException(
            status_code=400,
            detail={"error": "Unknown players in team B XI", "ids": unknown},
        )

    team_a_json["playing_xi"] = list(req_a)
    team_b_json["playing_xi"] = list(req_b)

    game.team_a = team_a_json
    game.team_b = team_b_json

    game.team_a_captain_id = str(payload.captain_a) if payload.captain_a else None
    game.team_a_keeper_id = str(payload.keeper_a) if payload.keeper_a else None
    game.team_b_captain_id = str(payload.captain_b) if payload.captain_b else None
    game.team_b_keeper_id = str(payload.keeper_b) if payload.keeper_b else None

    await db.commit()
    return schemas.PlayingXIResponse(ok=True, game_id=game_id)


@router.post("/{game_id}/playing_xi", response_model=schemas.PlayingXIResponse)
async def set_playing_xi_alias(
    game_id: UUID,
    payload: schemas.PlayingXIRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.PlayingXIResponse:
    return await set_playing_xi(game_id, payload, db)


# NOTE: _name function retained for potential future use / testing / debugging
# It's not currently called by active routes but may be needed for legacy compatibility
__all__ = ["_name", "router", "search_games", "set_playing_xi", "set_playing_xi_alias"]


def _name(obj: Any, fallback: str = "") -> str:
    """
    Extract a team name from JSON columns that might be dicts, strings, or legacy values.
    (Retained for compatibility; not currently called by active routes.)
    """
    if obj is None:
        return fallback

    if isinstance(obj, str):
        if not obj:
            return fallback
        try:
            parsed = json.loads(obj)
        except ValueError:
            return obj
        obj = parsed

    if isinstance(obj, Mapping):
        # Cast to concrete dict to avoid partially-unknown .get() overload warnings
        m = cast(dict[str, Any], obj)
        value_raw = m.get("name")
        if isinstance(value_raw, str) and value_raw:
            return value_raw
        return fallback

    return fallback


@router.get("/search")
async def search_games(
    db: Annotated[AsyncSession, Depends(get_db)],
    team_a: str | None = None,
    team_b: str | None = None,
) -> Sequence[dict[str, Any]]:
    rows = None

    # If we're running in the in-memory test mode, prefer the in-memory repo
    # first so seeded matches are visible to search without touching the DB.
    try:
        import backend.app as backend_app

        repo = getattr(backend_app, "_memory_repo", None)
        if repo is not None:
            try:
                # prefer the helper that returns only games with a stored result
                rows = await repo.list_games_with_result()
            except Exception:
                try:
                    rows = list(repo._games.values())
                except Exception:
                    rows = None
    except Exception:
        rows = None

    # If not using in-memory repo, fall back to DB query and then try in-memory
    # if DB is unavailable or returns nothing.
    if rows is None:
        try:
            res = await db.execute(select(models.Game))
            # scalars().all() is not awaitable; cast to concrete list for typing
            rows = cast(list[models.Game], res.scalars().all())
        except Exception:
            rows = None

        if not rows:
            try:
                import backend.app as backend_app

                repo = getattr(backend_app, "_memory_repo", None)
                if repo is not None:
                    try:
                        rows = list(repo._games.values())
                    except Exception:
                        rows = None
                    if not rows and hasattr(repo, "list_games_with_result"):
                        try:
                            rows = await repo.list_games_with_result()
                        except Exception:
                            rows = rows or []
            except Exception:
                rows = rows or []

    def _name2(x: dict[str, Any] | None) -> str:
        try:
            return str((x or {}).get("name") or "")
        except Exception:
            return ""

    ta_f = (team_a or "").strip().lower()
    tb_f = (team_b or "").strip().lower()

    # Debug: indicate what rows we are about to iterate (helps diagnose in-memory vs DB)
    try:
        if rows is None:
            print("DEBUG: search rows is None")
        else:
            try:
                ln = len(rows) if hasattr(rows, "__len__") else "?"
            except Exception:
                ln = "?"
            # Suppress partially-unknown type warning for debug print
            print("DEBUG: search rows type:", str(type(rows)), "len:", ln)  # type: ignore[arg-type]
    except Exception:
        pass  # nosec
    # Ensure rows is an iterable for the loop (avoid mypy union-attr error)
    rows = rows or []

    out: list[dict[str, Any]] = []
    for g in rows:
        ta = _name2(getattr(g, "team_a", {}))
        tb = _name2(getattr(g, "team_b", {}))
        ok = True
        if ta_f:
            ok = ok and (ta_f in ta.lower() or ta_f in tb.lower())
        if tb_f:
            ok = ok and (tb_f in ta.lower() or tb_f in tb.lower())
        if not ok:
            continue
        out.append(
            {
                "id": getattr(g, "id", None),
                "team_a_name": ta,
                "team_b_name": tb,
                "status": str(getattr(g, "status", "")),
                "current_inning": getattr(g, "current_inning", None),
                "total_runs": getattr(g, "total_runs", None),
                "total_wickets": getattr(g, "total_wickets", None),
            }
        )
    return out


@router.get("/{game_id}/results", response_model=schemas.MatchResult)
async def get_game_results(
    game_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.MatchResult:
    """Retrieve results for a specific game (CRUD-backed)."""
    game = await crud.get_game(db, game_id=str(game_id))
    if not game or not getattr(game, "result", None):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results not found for the game",
        )

    raw = getattr(game, "result", None)
    try:
        payload: dict[str, Any] = json.loads(raw) if isinstance(raw, str) else (raw or {})
    except Exception:
        payload = {}

    margin_raw = payload.get("margin")
    margin = int(margin_raw) if margin_raw is not None else None

    winner_team_id = payload.get("winner_team_id")
    winner_team_name = payload.get("winner_team_name")
    result_text = payload.get("result_text")

    return schemas.MatchResult(
        winner_team_id=str(winner_team_id) if winner_team_id is not None else None,
        winner_team_name=(str(winner_team_name) if winner_team_name is not None else None),
        method=payload.get("method"),
        margin=margin,
        result_text=str(result_text) if result_text is not None else None,
        completed_at=payload.get("completed_at"),
    )


@router.post(
    "/{game_id}/results",
    response_model=schemas.MatchResult,
    status_code=status.HTTP_201_CREATED,
)
async def post_game_results(
    game_id: UUID,
    payload: schemas.MatchResultRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.MatchResult:
    """
    Create/update results for a specific game (CRUD-backed).
    Computes a sensible result_text if not provided.
    """
    game = await crud.get_game(db, game_id=str(game_id))
    if not game:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game not found",
        )

    try:
        ta: int = int(payload.team_a_score)
        tb_opt = payload.team_b_score
        tb: int = int(tb_opt) if tb_opt is not None else 0
        tb_missing = tb_opt is None
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid scores provided",
        ) from None

    try:
        # Optional: persist scores if your model has these columns
        if hasattr(game, "team_a_score"):
            game.team_a_score = ta  # type: ignore[attr-defined]
        if hasattr(game, "team_b_score"):
            game.team_b_score = None if tb_missing else tb  # type: ignore[attr-defined]

        def _team_name(obj: Any, key_json: str, key_legacy: str) -> str:
            try:
                v = (getattr(obj, key_json, {}) or {}).get("name") or getattr(obj, key_legacy, None)
                return str(v or "")
            except Exception:
                return ""

        team_a_name = _team_name(game, "team_a", "team_a_name") or "Team A"
        team_b_name = _team_name(game, "team_b", "team_b_name") or "Team B"

        # Winner name: prefer explicit winner_team_name, then 'winner' string.
        winner_name: str = (payload.winner_team_name or payload.winner or "").strip()
        if not winner_name:
            winner_name = team_a_name if ta >= tb else team_b_name

        # Derive method as Optional[str] first; ensure str before persisting.
        method_val: str | None
        if isinstance(payload.method, schemas.MatchMethod):
            method_val = payload.method.value
        elif payload.method is None:
            method_val = None
        else:
            method_val = str(payload.method)

        margin = payload.margin
        result_text = payload.result_text

        # If anything essential is missing, compute simple “by runs”/“tied”.
        if not method_val or margin is None or not result_text:
            if ta > tb:
                margin = ta - tb
                method_val = method_val or schemas.MatchMethod.by_runs.value
                winner_name = winner_name or team_a_name
                result_text = result_text or f"{winner_name} won by {margin} runs"
            elif tb > ta:
                margin = tb - ta
                method_val = method_val or schemas.MatchMethod.by_runs.value
                winner_name = winner_name or team_b_name
                result_text = result_text or f"{winner_name} won by {margin} runs"
            else:
                method_val = schemas.MatchMethod.tie.value
                margin = 0
                winner_name = ""  # no winner label for a tie
                result_text = result_text or "Match tied"

        # At this point: method_val is str, result_text is str, margin is int.
        result_dict: dict[str, Any] = {
            "match_id": str(payload.match_id),
            "winner": (payload.winner or winner_name or None),
            "team_a_score": ta,
            "team_b_score": (int(tb_opt) if tb_opt is not None else None),
            "winner_team_id": getattr(payload, "winner_team_id", None) or None,
            "winner_team_name": winner_name or None,
            "method": method_val,
            "margin": margin,  # Already int at this point (assigned above)
            "result_text": result_text,
            "completed_at": getattr(payload, "completed_at", None),
        }

        game.result = json.dumps(result_dict, ensure_ascii=False)
        try:
            game.status = models.GameStatus.completed
        except Exception:
            # Fallback for older model versions
            game.status = "completed"  # type: ignore[assignment]
        # game.is_game_over is a computed property based on status
        try:
            game.completed_at = dt.datetime.now(UTC)
        except Exception:
            game.completed_at = dt.datetime.now(UTC)

        await crud.update_game(db, game_model=game)

        # Debugging: report whether an in-memory repo exists and contains the game
        try:
            import backend.app as backend_app

            repo = getattr(backend_app, "_memory_repo", None)
            if repo is not None:
                try:
                    print("DEBUG: in-memory repo games keys:", list(repo._games.keys()))
                except Exception:
                    print("DEBUG: in-memory repo present but failed to inspect _games")
            else:
                print("DEBUG: no in-memory repo configured")
        except Exception:
            print("DEBUG: could not import backend.app for repo inspection")

        return schemas.MatchResult(
            winner_team_id=result_dict["winner_team_id"],
            winner_team_name=result_dict["winner_team_name"],
            method=result_dict["method"],
            margin=result_dict["margin"],
            result_text=result_dict["result_text"],
            completed_at=result_dict["completed_at"],
        )
    except SQLAlchemyError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred updating the game results",
        ) from err


@router.get("/results")
async def list_game_results(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Sequence[dict[str, Any]]:
    """Return all games that have a stored result as simple dicts."""
    # Prefer DB-backed query when possible. If DB is unavailable or empty,
    # fall back to in-memory CRUD repository when configured.
    rows = None
    try:
        res = await db.execute(select(models.Game).where(models.Game.result.isnot(None)))
        # scalars().all() is not awaitable; cast to concrete list for typing
        rows = cast(list[models.Game], res.scalars().all())
    except Exception:
        rows = None

    if not rows:
        try:
            import backend.app as backend_app

            repo = getattr(backend_app, "_memory_repo", None)
            if repo is not None:
                rows = await repo.list_games_with_result()
        except Exception:
            rows = rows or []

    # Make sure rows is iterable for the loop (fix mypy union-attr error)
    rows = rows or []

    out: list[dict[str, Any]] = []
    for g in rows:
        # g may be a SQLAlchemy model instance or an in-memory model stub
        raw = getattr(g, "result", None)
        if not raw:
            continue
        try:
            if isinstance(raw, str):
                data = cast(dict[str, Any], json.loads(raw))
            elif isinstance(raw, dict):
                data = cast(dict[str, Any], raw)
            else:
                data = {}
        except Exception:
            data = {}

        item: dict[str, Any] = {
            "match_id": str(data.get("match_id") or getattr(g, "id", None) or ""),
            "winner": data.get("winner"),
            "team_a_score": int(data.get("team_a_score") or 0),
            "team_b_score": int(data.get("team_b_score") or 0),
        }
        for k in (
            "winner_team_id",
            "winner_team_name",
            "method",
            "margin",
            "result_text",
            "completed_at",
        ):
            if k in data:
                item[k] = data[k]
        out.append(item)

    return out
