from __future__ import annotations

from typing import Any, Dict, List, Optional, cast
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app import crud, schemas, models

# Local lightweight helpers (copied from main.py to avoid circular imports)
def _mk_players(names: List[str]) -> List[Dict[str, str]]:
    return [{"id": str(uuid.uuid4()), "name": n} for n in names]

def _mk_batting_scorecard(team: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for p in team.get("players", []):
        out[p["id"]] = {
            "player_id": p["id"],
            "player_name": p["name"],
            "runs": 0,
            "balls_faced": 0,
            "is_out": False,
            "fours": 0,
            "sixes": 0,
            "how_out": "",
        }
    return out

def _mk_bowling_scorecard(team: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for p in team.get("players", []):
        out[p["id"]] = {
            "player_id": p["id"],
            "player_name": p["name"],
            "overs_bowled": 0.0,
            "runs_conceded": 0,
            "wickets_taken": 0,
        }
    return out

def _coerce_match_type(raw: str) -> schemas.MatchType:
    try:
        return schemas.MatchType(raw)
    except Exception:
        return schemas.MatchType.limited


async def create_game(
    payload: Any,  # payload is main.CreateGameRequest Pydantic model; keep loose typing to avoid circular typing import
    db: AsyncSession,
) -> schemas.Game:
    """
    Orchestrate creating a Game row + pre-seeded scorecards.
    Returns the db Game (ORM row) as main.create_game did.
    """
    # --- Build players lists (prefer explicit lists, otherwise generate) ---
    players_a_list = payload.players_a
    players_b_list = payload.players_b
    if not players_a_list or not players_b_list:
        per_side = int(payload.players_per_team or 11)
        players_a_list = players_a_list or [f"PlayerA{i}" for i in range(1, per_side + 1)]
        players_b_list = players_b_list or [f"PlayerB{i}" for i in range(1, per_side + 1)]

    team_a: Dict[str, Any] = {"name": payload.team_a_name, "players": _mk_players(players_a_list)}
    team_b: Dict[str, Any] = {"name": payload.team_b_name, "players": _mk_players(players_b_list)}

    # --- Determine initial batting side (toss/decision) with safe defaults ---
    toss = (payload.toss_winner_team or "").strip()
    decision = (payload.decision or "").strip().lower()
    if toss:
        if toss == payload.team_a_name:
            batting_team_name = payload.team_a_name if decision == "bat" else payload.team_b_name
        elif toss == payload.team_b_name:
            batting_team_name = payload.team_b_name if decision == "bat" else payload.team_a_name
        else:
            batting_team_name = payload.team_a_name
    else:
        batting_team_name = payload.team_a_name

    bowling_team_name = payload.team_b_name if batting_team_name == payload.team_a_name else payload.team_a_name

    # Pre-seed scorecards
    batting_scorecard = _mk_batting_scorecard(team_a if batting_team_name == payload.team_a_name else team_b)
    bowling_scorecard = _mk_bowling_scorecard(team_b if batting_team_name == payload.team_a_name else team_a)

    game_create = schemas.GameCreate(
        team_a_name=payload.team_a_name,
        team_b_name=payload.team_b_name,
        players_a=players_a_list,
        players_b=players_b_list,
        match_type=_coerce_match_type(payload.match_type),
        overs_limit=payload.overs_limit,
        days_limit=payload.days_limit,
        overs_per_day=payload.overs_per_day,
        dls_enabled=payload.dls_enabled,
        interruptions=payload.interruptions,
        # If caller didn't provide toss/decision, synthesize a safe default:
        toss_winner_team=payload.toss_winner_team or batting_team_name,
        decision=payload.decision or "bat",
    )

    game_id = str(uuid.uuid4())

    db_game = await crud.create_game(
        db=db,
        game=game_create,
        game_id=game_id,
        batting_team=batting_team_name,
        bowling_team=bowling_team_name,
        team_a=cast(Dict[str, Any], team_a),
        team_b=cast(Dict[str, Any], team_b),
        batting_scorecard=cast(Dict[str, Any], batting_scorecard),
        bowling_scorecard=cast(Dict[str, Any], bowling_scorecard),
    )

    return db_game


