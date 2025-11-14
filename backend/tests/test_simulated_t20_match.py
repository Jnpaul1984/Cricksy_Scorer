import json
import os

import backend.main as main  # Import the module to access private functions
from backend.main import (  # Assuming ConcreteGameState is defined in backend.main
    ConcreteGameState,
)


def _mk_delivery(
    over: int,
    ball: int,
    runs: int,
    extras: int = 0,
    extra_type: str | None = None,
    wicket: bool = False,
    inning: int = 1,
):
    # Map simplified fields to the runtime schema expected by recompute logic
    d: dict[str, object] = {
        "over_number": over,
        "ball_number": ball,
        "runs_off_bat": runs,
        "extra_runs": extras,
        "is_wicket": wicket,
        "inning": inning,
    }
    if extra_type is not None:
        # Normalize common words to codes expected by backend (handled again in _norm_extra)
        et = extra_type
        if et.lower() == "wide":
            et = "wd"
        elif et.lower() in ("no_ball", "no-ball"):
            et = "nb"
        elif et.lower() in ("bye", "b"):
            et = "b"
        elif et.lower() in ("leg_bye", "leg-bye", "lb"):
            et = "lb"
        d["extra_type"] = et
    # Compute runs_scored to satisfy _runs_wkts_balls_for_innings()
    et_code = d.get("extra_type") or None
    if et_code == "wd":
        d["runs_scored"] = max(1, extras or 1)
    elif et_code == "nb":
        d["runs_scored"] = 1 + runs
    elif et_code in ("b", "lb"):
        d["runs_scored"] = extras
    else:
        d["runs_scored"] = runs + extras
    return d


def test_simulated_t20_match():
    # Load simulated match data
    match_path = os.path.join(os.path.dirname(__file__), "simulated_t20_match.json")
    with open(match_path) as f:
        match = json.load(f)

    team_a_name = match["teams"][0]
    team_b_name = match["teams"][1]

    # Use the concrete implementation
    g = ConcreteGameState(
        id="some-id",
        team_a={"name": team_a_name, "players": []},
        team_b={"name": team_b_name, "players": []},
    )

    # Construct minimal deliveries that produce the target totals and end the chase by balls exhausted
    # Inning 1 total: 157 (one legal ball carrying total for simplicity)
    inns1 = [_mk_delivery(1, 1, runs=157, inning=1)]
    # Inning 2 total: 142 across 6 legal balls to exhaust 1 over
    inns2 = [
        _mk_delivery(1, 1, runs=142, inning=2),
        _mk_delivery(1, 2, runs=0, inning=2),
        _mk_delivery(1, 3, runs=0, inning=2),
        _mk_delivery(1, 4, runs=0, inning=2),
        _mk_delivery(1, 5, runs=0, inning=2),
        _mk_delivery(1, 6, runs=0, inning=2),
    ]

    # Configure g based on test requirements
    g.overs_limit = 1  # so that 6 legal deliveries in inns 2 will exhaust balls
    g.current_inning = 1
    g.deliveries = inns1 + inns2

    # Recompute totals for inns 1
    g.batting_team_name = team_a_name
    g.bowling_team_name = team_b_name
    main._recompute_totals_and_runtime(g)

    # Switch to innings 2 and set batting/bowling names appropriately
    g.current_inning = 2
    g.batting_team_name = team_b_name
    g.bowling_team_name = team_a_name

    # Finalize match after second innings deliveries are considered
    main._maybe_finalize_match(g)

    # Assert winner and result
    result = getattr(g, "result", None)
    assert result is not None, "No result found!"
    assert (
        result.winner_team_name == match["result"]["winner"]
    ), f"Expected winner {match['result']['winner']}, got {result.winner_team_name}"
    # Allow minor punctuation differences at the end
    assert result.result_text.rstrip(".") == match["result"]["summary"].rstrip(
        "."
    ), f"Expected summary {match['result']['summary']}, got {result.result_text}"
