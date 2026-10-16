from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.routes.gameplay import _reopen_current_innings_for_ledger_edit
from backend.services.game_helpers import _maybe_finalize_match, _recompute_totals_and_runtime
from backend.services.match_rules import build_practice_match_rules
from backend.services.scoring_rules import (
    innings_is_all_out,
    team_for_current_batting_side,
    validate_incoming_batter,
    wicket_limit_for_current_innings,
)
from backend.services.scoring_service import score_one
from backend.services.snapshot_service import build_snapshot
from backend.sql_app import models


def _team(name: str, count: int) -> dict[str, object]:
    return {
        "name": name,
        "players": [{"id": f"{name}-{index}", "name": f"{name} {index}"} for index in range(count)],
    }


def _game(
    side_size: int, *, inning: int = 1, wickets: int = 0, first_batting_side: str = "team_a"
) -> SimpleNamespace:
    team_a = _team("A", side_size)
    team_b = _team("B", side_size)
    rules = build_practice_match_rules(
        team_a_source_squad_id="squad-a",
        team_a_canonical_player_ids=[f"A-{index}" for index in range(side_size)],
        team_b_source_squad_id="squad-b",
        team_b_canonical_player_ids=[f"B-{index}" for index in range(side_size)],
        overs=1,
    )
    return SimpleNamespace(
        id="practice-game",
        match_purpose="practice",
        match_rules=rules,
        practice_start_context={"version": 1, "first_batting_side": first_batting_side},
        team_a=team_a,
        team_b=team_b,
        batting_team_name="A" if inning == 1 else "B",
        bowling_team_name="B" if inning == 1 else "A",
        current_inning=inning,
        total_runs=0,
        total_wickets=wickets,
        overs_completed=0,
        balls_this_over=0,
        balls_bowled_total=0,
        overs_limit=1,
        deliveries=[],
        batting_scorecard={}, bowling_scorecard={},
        current_striker_id="A-0" if inning == 1 else "B-0",
        current_non_striker_id="A-1" if inning == 1 else "B-1",
        current_bowler_id="B-0" if inning == 1 else "A-0",
        last_ball_bowler_id=None,
        status=models.GameStatus.in_progress,
        dls_enabled=True,
        target=None,
        first_inning_summary=None,
        result=None,
    )


@pytest.mark.parametrize(("side_size", "wickets"), [(2, 1), (6, 5), (8, 7), (11, 10)])
def test_practice_side_size_controls_final_wicket(side_size: int, wickets: int) -> None:
    game = _game(side_size, wickets=wickets)

    assert wicket_limit_for_current_innings(game) == wickets
    assert innings_is_all_out(game)
    snapshot = build_snapshot(game, None)
    assert snapshot["wicket_limit"] == wickets
    assert snapshot["canScore"] is False
    assert snapshot["dls"] == {}


def test_final_practice_wicket_does_not_request_a_replacement() -> None:
    game = _game(2)
    score_one(
        game,
        striker_id="A-0",
        non_striker_id="A-1",
        bowler_id="B-0",
        runs_scored=0,
        extra=None,
        is_wicket=True,
        dismissal_type="bowled",
        dismissed_player_id="A-0",
    )

    assert game.pending_new_batter is False


def test_illegal_deliveries_do_not_consume_practice_ball_limit() -> None:
    game = _game(2)
    game.deliveries = [
        {"extra_type": "wd", "runs_off_bat": 0, "extra_runs": 1, "runs_scored": 1},
        {"extra_type": "nb", "runs_off_bat": 0, "extra_runs": 0, "runs_scored": 1},
        {"extra_type": None, "runs_off_bat": 0, "extra_runs": 0, "runs_scored": 0},
    ]
    _recompute_totals_and_runtime(game)

    assert game.balls_bowled_total == 1
    assert game.balls_this_over == 1


def test_practice_wicket_margin_and_tie_use_resolved_limit() -> None:
    game = _game(6, inning=2, wickets=1)
    game.deliveries = [
        {"inning": 1, "runs_scored": 20, "is_wicket": False, "extra_type": None},
        {"inning": 2, "runs_scored": 21, "is_wicket": True, "extra_type": None},
    ]
    game.total_runs = 21
    game.target = 21
    _maybe_finalize_match(game)
    assert game.result.margin == 4

    tied = _game(2, inning=2, wickets=1)
    tied.deliveries = [
        {"inning": 1, "runs_scored": 5, "is_wicket": False, "extra_type": None},
        {"inning": 2, "runs_scored": 5, "is_wicket": True, "extra_type": None},
    ]
    tied.total_runs = 5
    tied.target = 6
    _maybe_finalize_match(tied)
    assert tied.result.method.value == "tie"


def test_practice_replacement_must_be_in_frozen_batting_side() -> None:
    game = _game(2)
    validate_incoming_batter(game, "A-1")
    with pytest.raises(ValueError, match="frozen practice batting side"):
        validate_incoming_batter(game, "B-0")


def test_undoing_a_final_wicket_reopens_the_practice_innings() -> None:
    game = _game(2, wickets=1)
    game.status = models.GameStatus.innings_break
    game.innings_history = [{"inning_no": 1, "runs": 8}]
    game.result = object()
    game.completed_at = object()

    _reopen_current_innings_for_ledger_edit(game)

    assert game.status is models.GameStatus.in_progress
    assert game.innings_history == []
    assert game.result is None
    assert game.completed_at is None


@pytest.mark.parametrize(
    ("first_batting_side", "inning", "expected_ids"),
    [
        ("team_a", 1, {"A-0", "A-1"}),
        ("team_a", 2, {"B-0", "B-1"}),
        ("team_b", 1, {"B-0", "B-1"}),
        ("team_b", 2, {"A-0", "A-1"}),
    ],
)
def test_same_named_practice_sides_use_persisted_order(
    first_batting_side: str, inning: int, expected_ids: set[str]
) -> None:
    game = _game(2, inning=inning, first_batting_side=first_batting_side)
    game.team_a["name"] = game.team_b["name"] = "Same Name"
    game.batting_team_name = game.bowling_team_name = "Same Name"

    assert wicket_limit_for_current_innings(game) == 1
    assert {player["id"] for player in team_for_current_batting_side(game)["players"]} == expected_ids
    allowed = next(iter(expected_ids))
    validate_incoming_batter(game, allowed)
    denied = "B-0" if allowed.startswith("A-") else "A-0"
    with pytest.raises(ValueError, match="frozen practice batting side"):
        validate_incoming_batter(game, denied)


def test_practice_side_resolution_fails_closed_without_persisted_order() -> None:
    game = _game(2)
    game.practice_start_context = {}
    with pytest.raises(ValueError, match="practice_start_context"):
        wicket_limit_for_current_innings(game)


@pytest.mark.parametrize(
    "context",
    [
        {"version": 2, "first_batting_side": "team_a"},
        {"version": True, "first_batting_side": "team_a"},
        {"version": 1.0, "first_batting_side": "team_a"},
        {"version": 1, "first_batting_side": "team_c"},
        {"version": 1, "first_batting_side": "team_a", "extra": True},
    ],
)
def test_practice_start_context_is_versioned_and_exact(context: dict[str, object]) -> None:
    game = _game(2)
    game.practice_start_context = context
    with pytest.raises(ValueError, match="practice_start_context"):
        wicket_limit_for_current_innings(game)


@pytest.mark.parametrize("first_batting_side", ["team_a", "team_b"])
def test_practice_score_rejects_foreign_participants_without_mutation(first_batting_side: str) -> None:
    game = _game(2, first_batting_side=first_batting_side)
    if first_batting_side == "team_b":
        game.current_striker_id, game.current_non_striker_id, game.current_bowler_id = "B-0", "B-1", "A-0"
        non_striker, bowler = "B-1", "A-0"
    else:
        non_striker, bowler = "A-1", "B-0"
    before = (game.total_runs, game.total_wickets, dict(game.batting_scorecard))
    with pytest.raises(ValueError, match="frozen batting side"):
        score_one(game, striker_id=bowler, non_striker_id=non_striker, bowler_id=bowler,
                  runs_scored=0, extra=None, is_wicket=False, dismissal_type=None, dismissed_player_id=None)
    assert (game.total_runs, game.total_wickets, game.batting_scorecard) == before
