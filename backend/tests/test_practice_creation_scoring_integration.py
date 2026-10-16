from __future__ import annotations

import pytest

from backend.routes.gameplay import _reopen_current_innings_for_ledger_edit
from backend.services.practice_match_persistence_service import start_private_practice_match
from backend.services.scoring_rules import (
    team_for_current_batting_side,
    wicket_limit_for_current_innings,
)
from backend.services.scoring_service import score_one
from backend.sql_app.database import SessionLocal
from backend.sql_app.models import Game, GameStatus
from backend.tests.test_practice_start_context import _draft


@pytest.mark.parametrize("first_batting_side", ["team_a", "team_b"])
async def test_persisted_private_draft_starts_reloads_scores_final_wicket_and_undoes(
    first_batting_side: str,
) -> None:
    """Exercise the creation-owned side key through the scoring engine boundary."""

    organization_id, owner_id, game_id = await _draft(same_display_name=True)
    async with SessionLocal() as session:
        started = await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side=first_batting_side,
        )
        assert started.status is GameStatus.started

    async with SessionLocal() as session:
        game = await session.get(Game, game_id)
        assert game is not None
        assert game.team_a["name"] == game.team_b["name"]
        assert game.practice_start_context == {
            "version": 1,
            "first_batting_side": first_batting_side,
        }

        batting_ids = [player["id"] for player in team_for_current_batting_side(game)["players"]]
        bowling_ids = [
            player["id"]
            for player in (game.team_b if first_batting_side == "team_a" else game.team_a)["players"]
        ]
        assert len(batting_ids) == len(bowling_ids) == 2
        assert wicket_limit_for_current_innings(game) == 1

        delivery = score_one(
            game,
            striker_id=batting_ids[0],
            non_striker_id=batting_ids[1],
            bowler_id=bowling_ids[0],
            runs_scored=0,
            extra=None,
            is_wicket=True,
            dismissal_type="bowled",
            dismissed_player_id=batting_ids[0],
        )
        assert game.pending_new_batter is False
        game.deliveries = [{**delivery, "inning": 1}]
        game.total_wickets = 1
        game.status = GameStatus.innings_break
        game.innings_history = [{"inning_no": 1, "runs": 0}]
        game.result = "synthetic completed result"
        game.completed_at = object()
        await session.commit()

        _reopen_current_innings_for_ledger_edit(game)
        assert game.status is GameStatus.in_progress
        assert game.innings_history == []
        assert game.result is None
        assert game.completed_at is None
