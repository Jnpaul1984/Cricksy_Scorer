"""Utility to regenerate the shared simulated T20 match fixture with full ball-by-ball data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class WicketEvent:
    kind: str
    fielder: str | None = None


def _simulate_innings(
    *,
    team_name: str,
    batting_prefix: str,
    bowling_prefix: str,
    over_run_patterns: List[List[int]],
    wicket_map: Dict[Tuple[int, int], WicketEvent],
) -> Dict[str, object]:
    """Build innings data using deterministic run patterns and wicket events."""
    batters = [f"{batting_prefix} Player {i}" for i in range(1, 12)]
    bowlers = [f"{bowling_prefix} Player {i}" for i in range(1, 7)]
    fielders = [f"{bowling_prefix} Player {i}" for i in range(1, 12)]

    striker_idx = 0
    non_striker_idx = 1
    next_batter_idx = 2
    opening_pair = {
        "striker": batters[striker_idx],
        "non_striker": batters[non_striker_idx],
    }
    bowling_order: List[str] = []

    total_runs = 0
    total_wkts = 0
    deliveries: List[Dict[str, object]] = []

    for over_number, pattern in enumerate(over_run_patterns, start=1):
        bowler_name = bowlers[(over_number - 1) % len(bowlers)]
        bowling_order.append(bowler_name)

        for ball_number, runs in enumerate(pattern, start=1):
            striker_name = batters[striker_idx]
            non_striker_name = batters[non_striker_idx]

            entry: Dict[str, object] = {
                "over": over_number,
                "ball": ball_number,
                "bowler": bowler_name,
                "batsman": striker_name,
                "non_striker": non_striker_name,
                "runs": runs,
                "extras": 0,
                "wicket": False,
            }

            event = wicket_map.get((over_number, ball_number))
            if event:
                entry["wicket"] = True
                entry["wicketType"] = event.kind
                if event.fielder:
                    # Ensure the fielder name exists in the fielding side roster
                    if event.fielder not in fielders:
                        raise ValueError(
                            f"Unknown fielder {event.fielder}. Valid fielders are: {fielders}"
                        )
                    entry["fielder"] = event.fielder
                total_wkts += 1

            deliveries.append(entry)
            total_runs += runs

            if event:
                if next_batter_idx >= len(batters):
                    raise RuntimeError(
                        f"Ran out of batters while simulating wickets at over {over_number}, ball {ball_number}"
                    )
                striker_idx = next_batter_idx
                next_batter_idx += 1
            else:
                if runs % 2 == 1:
                    striker_idx, non_striker_idx = non_striker_idx, striker_idx

            if ball_number == 6:
                striker_idx, non_striker_idx = non_striker_idx, striker_idx

    return {
        "team": team_name,
        "runs": total_runs,
        "wickets": total_wkts,
        "balls": deliveries,
        "opening_pair": opening_pair,
        "bowling_order": bowling_order,
    }


def _build_fixture() -> Dict[str, object]:
    innings_one_patterns: List[List[int]] = [
        [1, 0, 4, 1, 1, 1],
        [0, 2, 0, 1, 0, 4],
        [2, 1, 0, 4, 1, 1],
        [1, 0, 4, 2, 2, 0],
        [1, 1, 2, 0, 2, 2],
        [0, 1, 0, 2, 2, 2],
        [0, 2, 1, 0, 3, 2],
        [1, 0, 1, 4, 0, 1],
        [2, 0, 0, 3, 1, 2],
        [1, 1, 2, 2, 0, 3],
        [0, 2, 1, 1, 2, 1],
        [1, 1, 0, 2, 2, 2],
        [0, 1, 2, 1, 1, 2],
        [2, 2, 0, 1, 2, 2],
        [2, 0, 2, 1, 1, 2],
        [1, 0, 1, 2, 1, 2],
        [0, 2, 1, 1, 1, 2],
        [1, 1, 2, 0, 4, 0],
        [2, 1, 0, 1, 2, 2],
        [1, 2, 1, 0, 2, 2],
    ]

    innings_one_wickets = {
        (2, 3): WicketEvent("caught", "Beta Player 3"),
        (4, 6): WicketEvent("lbw"),
        (7, 1): WicketEvent("bowled"),
        (10, 5): WicketEvent("caught", "Beta Player 5"),
        (15, 2): WicketEvent("caught", "Beta Player 6"),
        (18, 6): WicketEvent("bowled"),
    }

    innings_two_patterns: List[List[int]] = [
        [1, 0, 2, 1, 1, 2],
        [2, 0, 1, 2, 1, 2],
        [1, 0, 0, 2, 1, 2],
        [0, 2, 1, 0, 2, 2],
        [3, 1, 1, 1, 2, 0],
        [1, 0, 0, 2, 1, 2],
        [0, 1, 2, 1, 1, 2],
        [2, 1, 0, 1, 2, 2],
        [1, 1, 2, 0, 1, 1],
        [0, 1, 2, 1, 1, 2],
        [2, 0, 2, 1, 3, 0],
        [1, 0, 1, 0, 2, 2],
        [1, 2, 0, 1, 1, 2],
        [2, 1, 0, 2, 1, 2],
        [0, 2, 1, 1, 0, 2],
        [1, 1, 0, 2, 1, 2],
        [2, 0, 2, 2, 0, 2],
        [1, 0, 1, 1, 1, 2],
        [2, 0, 1, 2, 1, 1],
        [1, 1, 2, 0, 4, 1],
    ]

    innings_two_wickets = {
        (3, 2): WicketEvent("caught", "Alpha Player 3"),
        (5, 6): WicketEvent("bowled"),
        (7, 1): WicketEvent("lbw"),
        (9, 4): WicketEvent("caught", "Alpha Player 5"),
        (11, 6): WicketEvent("caught", "Alpha Player 6"),
        (14, 3): WicketEvent("bowled"),
        (17, 5): WicketEvent("caught", "Alpha Player 7"),
        (19, 2): WicketEvent("caught", "Alpha Player 4"),
    }

    innings_one = _simulate_innings(
        team_name="Team Alpha",
        batting_prefix="Alpha",
        bowling_prefix="Beta",
        over_run_patterns=innings_one_patterns,
        wicket_map=innings_one_wickets,
    )

    innings_two = _simulate_innings(
        team_name="Team Beta",
        batting_prefix="Beta",
        bowling_prefix="Alpha",
        over_run_patterns=innings_two_patterns,
        wicket_map=innings_two_wickets,
    )

    if innings_one["runs"] != 157 or innings_one["wickets"] != 6:
        raise AssertionError(
            f"First innings totals do not match expected values: "
            f"runs={innings_one['runs']} (expected 157), "
            f"wickets={innings_one['wickets']} (expected 6)"
        )
    if innings_two["runs"] != 142 or innings_two["wickets"] != 8:
        raise AssertionError("Second innings totals do not match expected values")

    return {
        "matchType": "T20",
        "teams": ["Team Alpha", "Team Beta"],
        "venue": "Generic Cricket Ground",
        "innings": [innings_one, innings_two],
        "result": {
            "winner": "Team Alpha",
            "summary": "Team Alpha won by 15 runs.",
        },
    }


def main() -> None:
    fixture = _build_fixture()
    root = Path(__file__).resolve().parents[1]
    targets: Iterable[Path] = (
        root / "simulated_t20_match.json",
        root / "backend" / "tests" / "simulated_t20_match.json",
        root / "frontend" / "simulated_t20_match.json",
        root / "frontend" / "cypress" / "fixtures" / "simulated_t20_match.json",
    )

    payload = json.dumps(fixture, indent=2)

    wrote = 0
    for path in targets:
        path.write_text(payload + "\n", encoding="utf-8")
        wrote += 1
    print(f"Wrote fixture to {len(list(targets))} locations.")


if __name__ == "__main__":
    main()
