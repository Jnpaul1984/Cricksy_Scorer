"""Private, organization-scoped practice scoring workflow.

These functions are intentionally not adapters around ``/games``.  A practice
Game has no generic read, scoring, broadcast, or public projection surface.
They use the shared scoring engine only after re-authorizing the organization,
checking the persisted private snapshot, and locking the row.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Mapping
from typing import Any

from backend.services import game_helpers, school_match_service
from backend.services.match_rules import PRACTICE_MATCH_PURPOSE, MatchRulesValidationError
from backend.services.practice_match_persistence_service import (
    _practice_game_belongs_to_organization,
    validate_practice_start_context,
)
from backend.services.scoring_rules import (
    innings_is_all_out,
    team_for_current_batting_side,
    team_for_current_bowling_side,
    validate_delivery_participants,
)
from backend.services.scoring_service import score_one
from backend.services.snapshot_service import build_snapshot
from backend.sql_app import models
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

UTC = getattr(dt, "UTC", dt.UTC)


def _error(status_code: int, detail: str) -> school_match_service.SchoolMatchServiceError:
    return school_match_service.SchoolMatchServiceError(status_code, detail)


async def _load_private_game(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    game_id: str,
    lock: bool,
) -> models.Game:
    await school_match_service._authorize(
        db, organization_id=organization_id, actor_user_id=actor_user_id
    )
    statement = select(models.Game).where(models.Game.id == game_id)
    if lock:
        statement = statement.with_for_update()
    game = await db.scalar(statement)
    if (
        game is None
        or game.match_purpose != PRACTICE_MATCH_PURPOSE
        or game.publication_state not in {"private", "published_live", "published_final"}
        or not _practice_game_belongs_to_organization(game, organization_id)
    ):
        raise _error(404, "Practice match not found")
    try:
        validate_practice_start_context(game.practice_start_context)
    except school_match_service.SchoolMatchServiceError as exc:
        raise _error(409, exc.detail) from exc
    return game


def _revision(game: models.Game) -> int:
    value = game.practice_workflow_revision
    if type(value) is not int or value < 1:
        raise _error(409, "Practice workflow revision is malformed")
    return value


def _require_revision(game: models.Game, expected_revision: int) -> None:
    if _revision(game) != expected_revision:
        raise _error(409, "Practice workflow revision conflict")


def _delivery_runs(row: Mapping[str, Any]) -> int:
    """Read a replayed delivery's scoring value without trusting JSON types."""
    if row.get("extra_type") == "nb":
        value = row.get("runs_off_bat")
    elif row.get("extra_type") in {"wd", "b", "lb"}:
        value = row.get("extra_runs")
    else:
        value = row.get("runs_off_bat")
    if value is None:
        return 0
    if isinstance(value, (int, float, str)):
        return int(value)
    raise ValueError("Persisted practice delivery has an invalid runs value")


def _side_name(game: models.Game, side_key: str) -> str:
    side = game.team_a if side_key == "team_a" else game.team_b
    name = side.get("name") if isinstance(side, dict) else None
    if not isinstance(name, str) or not name:
        raise _error(409, "Practice team snapshot is malformed")
    return name


def _side_ids(team: Mapping[str, Any]) -> set[str]:
    players = team.get("players")
    if not isinstance(players, list):
        raise _error(409, "Practice team snapshot is malformed")
    ids = {str(player.get("id")) for player in players if isinstance(player, dict)}
    if not ids or "None" in ids:
        raise _error(409, "Practice team snapshot is malformed")
    return ids


def _assert_roles(
    game: models.Game, *, striker_id: str, non_striker_id: str, bowler_id: str
) -> None:
    try:
        validate_delivery_participants(
            game,
            striker_id=striker_id,
            non_striker_id=non_striker_id,
            bowler_id=bowler_id,
            dismissed_player_id=None,
        )
    except MatchRulesValidationError as exc:
        raise _error(422, str(exc)) from exc


def _reset_current_innings(game: models.Game) -> None:
    game.total_runs = 0
    game.total_wickets = 0
    game.overs_completed = 0
    game.balls_this_over = 0
    game.current_striker_id = None
    game.current_non_striker_id = None
    game.current_bowler_id = None
    game.last_ball_bowler_id = None
    game.extras_totals = {}
    game.fall_of_wickets = []
    batting = _side_ids(team_for_current_batting_side(game))
    bowling = _side_ids(team_for_current_bowling_side(game))
    # Practice snapshots intentionally store stable IDs rather than mutable
    # player-profile display fields; scorecard display names are therefore
    # optional while the engine's participant identity stays exact.
    game.batting_scorecard = {
        player_id: {
            "player_id": player_id,
            "player_name": None,
            "runs": 0,
            "balls_faced": 0,
            "is_out": False,
            "fours": 0,
            "sixes": 0,
            "how_out": "",
        }
        for player_id in batting
    }
    game.bowling_scorecard = {
        player_id: {
            "player_id": player_id,
            "player_name": None,
            "overs_bowled": 0.0,
            "runs_conceded": 0,
            "wickets_taken": 0,
        }
        for player_id in bowling
    }


def _close_if_terminal(game: models.Game) -> None:
    if game.current_inning >= 2:
        game_helpers._ensure_target_if_chasing(game)
    balls_limit = int(game.overs_limit or 0) * 6
    balls_bowled = int(game.overs_completed) * 6 + int(game.balls_this_over)
    chase_reached = (
        game.current_inning >= 2
        and game.target is not None
        and int(game.total_runs) >= int(game.target)
    )
    if (
        not chase_reached
        and not innings_is_all_out(game)
        and not (balls_limit > 0 and balls_bowled >= balls_limit)
    ):
        return
    history = list(game.practice_innings_history or [])
    if not any(entry.get("inning_no") == game.current_inning for entry in history):
        history.append(
            {
                "inning_no": game.current_inning,
                "batting_team": game.batting_team_name,
                "bowling_team": game.bowling_team_name,
                "runs": game.total_runs,
                "wickets": game.total_wickets,
                "overs": f"{game.overs_completed}.{game.balls_this_over}",
                "batting_scorecard": game.batting_scorecard,
                "bowling_scorecard": game.bowling_scorecard,
                "closed_at": dt.datetime.now(UTC).isoformat(),
            }
        )
    game.practice_innings_history = history
    game.current_striker_id = None
    game.current_non_striker_id = None
    game.current_bowler_id = None
    game.status = models.GameStatus.innings_break
    if game.current_inning >= 2:
        game_helpers._maybe_finalize_match(game)


def _snapshot(game: models.Game) -> dict[str, Any]:
    last = game.deliveries[-1] if game.deliveries else None
    snapshot = build_snapshot(game, last)
    snapshot["practice_workflow_revision"] = _revision(game)
    return snapshot


async def _persist(db: AsyncSession, game: models.Game, *, expected_revision: int) -> models.Game:
    for field in (
        "deliveries",
        "batting_scorecard",
        "bowling_scorecard",
        "practice_innings_history",
    ):
        flag_modified(game, field)
    if game.result is not None and not isinstance(game.result, str):
        game.result = str(getattr(game.result, "result_text", game.result))
    # SQLite ignores SELECT FOR UPDATE. Claim the next token before the dirty
    # ORM state can flush so concurrent stale writers cannot silently win.
    with db.no_autoflush:
        claimed = await db.execute(
            update(models.Game)
            .where(
                models.Game.id == game.id,
                models.Game.practice_workflow_revision == expected_revision,
            )
            .values(practice_workflow_revision=expected_revision + 1)
            .execution_options(synchronize_session=False)
        )
    if claimed.rowcount != 1:
        await db.rollback()
        raise _error(409, "Practice workflow revision conflict")
    game.practice_workflow_revision = expected_revision + 1
    db.add(game)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(game)
    return game


async def read_practice_workflow(
    db: AsyncSession, *, organization_id: str, actor_user_id: str, game_id: str
) -> tuple[models.Game, dict[str, Any]]:
    game = await _load_private_game(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        game_id=game_id,
        lock=False,
    )
    return game, _snapshot(game)


async def start_practice_innings(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    game_id: str,
    expected_revision: int,
    striker_id: str,
    non_striker_id: str,
    opening_bowler_id: str,
) -> tuple[models.Game, dict[str, Any]]:
    game = await _load_private_game(
        db, organization_id=organization_id, actor_user_id=actor_user_id, game_id=game_id, lock=True
    )
    _require_revision(game, expected_revision)
    if game.status == models.GameStatus.started:
        if game.current_inning != 1 or game.deliveries:
            raise _error(409, "Practice first innings is no longer ready")
    elif game.status == models.GameStatus.innings_break:
        if game.current_inning != 1:
            raise _error(409, "Practice match has no further innings")
        game.current_inning = 2
        _reset_current_innings(game)
    else:
        raise _error(409, "Practice innings is not ready to start")

    first_side = validate_practice_start_context(game.practice_start_context)
    batting_side = (
        first_side
        if game.current_inning == 1
        else ("team_b" if first_side == "team_a" else "team_a")
    )
    bowling_side = "team_b" if batting_side == "team_a" else "team_a"
    game.batting_team_name = _side_name(game, batting_side)
    game.bowling_team_name = _side_name(game, bowling_side)
    _assert_roles(
        game, striker_id=striker_id, non_striker_id=non_striker_id, bowler_id=opening_bowler_id
    )
    _reset_current_innings(game)
    game.current_striker_id = striker_id
    game.current_non_striker_id = non_striker_id
    game.current_bowler_id = opening_bowler_id
    game.status = models.GameStatus.in_progress
    if game.current_inning == 2:
        game_helpers._ensure_target_if_chasing(game)
    game = await _persist(db, game, expected_revision=expected_revision)
    return game, _snapshot(game)


async def start_practice_over(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    game_id: str,
    expected_revision: int,
    bowler_id: str,
) -> tuple[models.Game, dict[str, Any]]:
    game = await _load_private_game(
        db, organization_id=organization_id, actor_user_id=actor_user_id, game_id=game_id, lock=True
    )
    _require_revision(game, expected_revision)
    if game.status != models.GameStatus.in_progress or game.current_bowler_id is not None:
        raise _error(409, "Practice over is not ready for a bowler")
    if game.current_striker_id is None or game.current_non_striker_id is None:
        raise _error(409, "Practice innings needs batters before starting an over")
    _assert_roles(
        game,
        striker_id=game.current_striker_id,
        non_striker_id=game.current_non_striker_id,
        bowler_id=bowler_id,
    )
    if game.last_ball_bowler_id == bowler_id:
        raise _error(422, "Bowler cannot bowl consecutive overs")
    game.current_bowler_id = bowler_id
    game = await _persist(db, game, expected_revision=expected_revision)
    return game, _snapshot(game)


async def score_practice_delivery(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    game_id: str,
    expected_revision: int,
    striker_id: str,
    non_striker_id: str,
    bowler_id: str,
    runs_scored: int,
    extra: str | None,
    is_wicket: bool,
    dismissal_type: str | None,
    dismissed_player_id: str | None,
) -> tuple[models.Game, dict[str, Any]]:
    game = await _load_private_game(
        db, organization_id=organization_id, actor_user_id=actor_user_id, game_id=game_id, lock=True
    )
    _require_revision(game, expected_revision)
    if game.status != models.GameStatus.in_progress:
        raise _error(409, "Practice match is not ready for scoring")
    if innings_is_all_out(game):
        raise _error(409, "Practice innings is already all out")
    if (
        game.current_striker_id != striker_id
        or game.current_non_striker_id != non_striker_id
        or game.current_bowler_id != bowler_id
    ):
        raise _error(409, "Practice delivery roles do not match the current innings")
    try:
        kwargs = score_one(
            game,
            striker_id=striker_id,
            non_striker_id=non_striker_id,
            bowler_id=bowler_id,
            runs_scored=runs_scored,
            extra=extra,
            is_wicket=is_wicket,
            dismissal_type=dismissal_type,
            dismissed_player_id=dismissed_player_id,
        )
    except (MatchRulesValidationError, ValueError) as exc:
        raise _error(422, str(exc)) from exc
    if kwargs["is_wicket"]:
        game.total_wickets = int(game.total_wickets) + 1
    delivery = dict(kwargs)
    delivery["inning"] = game.current_inning
    game.deliveries = [*(game.deliveries or []), delivery]
    _close_if_terminal(game)
    game = await _persist(db, game, expected_revision=expected_revision)
    return game, _snapshot(game)


async def undo_last_practice_delivery(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    game_id: str,
    expected_revision: int,
) -> tuple[models.Game, dict[str, Any]]:
    game = await _load_private_game(
        db, organization_id=organization_id, actor_user_id=actor_user_id, game_id=game_id, lock=True
    )
    _require_revision(game, expected_revision)
    ledger = list(game.deliveries or [])
    if not ledger:
        raise _error(409, "Nothing to undo")
    if game.status in {models.GameStatus.innings_break, models.GameStatus.completed}:
        game.status = models.GameStatus.in_progress
        game.result = None
        game.practice_innings_history = [
            entry
            for entry in (game.practice_innings_history or [])
            if entry.get("inning_no") != game.current_inning
        ]
    game.deliveries = ledger[:-1]
    _reset_current_innings(game)
    current_ledger = [
        row
        for row in game.deliveries
        if isinstance(row, dict) and row.get("inning") == game.current_inning
    ]
    for row in current_ledger:
        try:
            replayed = score_one(
                game,
                striker_id=str(row.get("striker_id") or ""),
                non_striker_id=str(row.get("non_striker_id") or ""),
                bowler_id=str(row.get("bowler_id") or ""),
                runs_scored=_delivery_runs(row),
                extra=row.get("extra_type"),
                is_wicket=bool(row.get("is_wicket")),
                dismissal_type=row.get("dismissal_type"),
                dismissed_player_id=row.get("dismissed_player_id"),
            )
            if replayed["is_wicket"]:
                game.total_wickets = int(game.total_wickets) + 1
        except (MatchRulesValidationError, ValueError) as exc:
            raise _error(409, f"Persisted practice delivery is invalid: {exc}") from exc
    _close_if_terminal(game)
    game = await _persist(db, game, expected_revision=expected_revision)
    return game, _snapshot(game)
