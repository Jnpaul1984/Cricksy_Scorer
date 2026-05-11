"""Phase 5F - Historical Import Delivery Service.

Provides helpers to:
- Normalize historical JSON innings/ball data into a format compatible with
  the live scoring analytics pipeline (``_aggregate_per_over``).
- Derive innings-level batting and bowling aggregates from ball events.
- Validate that derived totals reconcile with stored preview expectations.

Design constraints:
- No live scoring engine code is invoked.
- No ORM Player/Team rows are created; player names are stored inline.
- All player IDs used in scorecards are the player *names* from the source
  JSON (since historical data carries no real player UUIDs).
- The caller must verify the source hash before invoking these helpers.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from typing import Any

# Tolerance for run total reconciliation.
# If ``|derived_runs - expected_runs| <= _RUNS_TOLERANCE``, we issue a warning
# but do not block the import.  Values outside the tolerance block the import.
_RUNS_TOLERANCE = 5

# Same tolerance for wicket counts.
_WICKETS_TOLERANCE = 0


def _hash_payload(raw_payload: bytes) -> str:
    """Return canonical SHA-256 hex digest of the raw payload bytes."""
    data = json.loads(raw_payload.decode("utf-8"))
    canonical = json.dumps(data, separators=(",", ":"), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def verify_payload_hash(raw_payload: bytes, expected_hash: str) -> bool:
    """Return True if the canonical hash of ``raw_payload`` matches ``expected_hash``."""
    return _hash_payload(raw_payload) == expected_hash


# ---------------------------------------------------------------------------
# Delivery normalization
# ---------------------------------------------------------------------------


def _normalize_ball(
    ball: dict[str, Any],
    inning_idx: int,
    *,
    over_number: int | None = None,
    ball_in_over: int | None = None,
) -> dict[str, Any]:
    """Normalize a single ball dict from the fixture into analytics format.

    The analytics pipeline (``_aggregate_per_over``) expects:
    - ``inning``: 1-indexed innings number
    - ``over_number``: 1-indexed over
    - ``runs_off_bat``: int
    - ``extra_runs``: int
    - ``is_wicket``: bool
    - ``batsman``, ``bowler``: player names (strings)
    - ``_source``: provenance marker

    The cricksy_fixture format provides:
    - ``over``: int (over number, 1-indexed)
    - ``ball``: int (ball within over)
    - ``runs``: int (runs off bat)
    - ``extras``: int or dict (extra runs)
    - ``wicket``: bool or dict (wicket event)
    - ``batsman``, ``bowler``: str (player names)
    """
    runs_raw = ball.get("runs")
    if isinstance(runs_raw, dict):
        runs_off_bat = int(runs_raw.get("batter") or runs_raw.get("batsman") or 0)
        extra_runs = int(runs_raw.get("extras") or 0)
    else:
        runs_off_bat = int(ball.get("runs") or 0)

        extras_raw = ball.get("extras", 0)
        if isinstance(extras_raw, dict):
            extra_runs = sum(int(v or 0) for v in extras_raw.values())
        else:
            extra_runs = int(extras_raw or 0)

    wicket_raw = ball.get("wicket", False)
    wickets_list_raw = ball.get("wickets")
    has_wickets_list = isinstance(wickets_list_raw, list) and len(wickets_list_raw) > 0
    is_wicket = has_wickets_list or (
        bool(wicket_raw) if not isinstance(wicket_raw, dict) else bool(wicket_raw)
    )

    return {
        "inning": inning_idx,
        "over_number": over_number if over_number is not None else int(ball.get("over") or 1),
        "ball_in_over": ball_in_over if ball_in_over is not None else int(ball.get("ball") or 1),
        "runs_off_bat": runs_off_bat,
        "extra_runs": extra_runs,
        "is_wicket": is_wicket,
        "batsman": str(ball.get("batsman") or ball.get("batter") or ""),
        "bowler": str(ball.get("bowler") or ""),
        "_source": "historical_import",
    }


def extract_normalized_innings(
    parsed: dict[str, Any],
) -> list[dict[str, Any]]:
    """Parse the raw payload and return a list of innings dicts with normalized deliveries.

    Each item has the shape::

        {
            "inning_no": 1,
            "team": "Team Alpha",
            "runs_explicit": 157,
            "wickets_explicit": 6,
            "deliveries": [<normalized ball dicts>, ...],
        }
    """
    innings_raw = parsed.get("innings") or []
    result: list[dict[str, Any]] = []

    for idx, innings in enumerate(innings_raw, start=1):
        if not isinstance(innings, dict):
            continue

        innings_obj = innings
        if len(innings_obj) == 1 and not any(k in innings_obj for k in ("balls", "deliveries", "overs")):
            nested = next(iter(innings_obj.values()))
            if isinstance(nested, dict):
                innings_obj = dict(nested)
                if "team" not in innings_obj:
                    innings_obj["team"] = next(iter(innings.keys()))

        balls_raw = innings_obj.get("balls") or innings_obj.get("deliveries") or []
        normalized_deliveries: list[dict[str, Any]]
        if isinstance(balls_raw, list):
            normalized_deliveries = [_normalize_ball(b, idx) for b in balls_raw if isinstance(b, dict)]
        else:
            normalized_deliveries = []

        if not normalized_deliveries:
            overs_raw = innings_obj.get("overs")
            if isinstance(overs_raw, list):
                for over in overs_raw:
                    if not isinstance(over, dict):
                        continue
                    over_idx_raw = over.get("over")
                    over_number = int(over_idx_raw) + 1 if isinstance(over_idx_raw, int) else None
                    over_deliveries = over.get("deliveries")
                    if not isinstance(over_deliveries, list):
                        continue
                    for ball_idx, ball in enumerate(over_deliveries, start=1):
                        if isinstance(ball, dict):
                            normalized_deliveries.append(
                                _normalize_ball(
                                    ball,
                                    idx,
                                    over_number=over_number,
                                    ball_in_over=ball_idx,
                                )
                            )

        runs_explicit = innings_obj.get("runs")
        wickets_explicit = innings_obj.get("wickets")

        result.append(
            {
                "inning_no": idx,
                "team": innings_obj.get("team") or None,
                "runs_explicit": int(runs_explicit) if isinstance(runs_explicit, int) else None,
                "wickets_explicit": (
                    int(wickets_explicit) if isinstance(wickets_explicit, int) else None
                ),
                "deliveries": normalized_deliveries,
            }
        )

    return result


# ---------------------------------------------------------------------------
# Scorecard derivation
# ---------------------------------------------------------------------------


def _derive_batting_scorecard(
    deliveries: list[dict[str, Any]],
    inning_no: int,
) -> dict[str, dict[str, Any]]:
    """Derive batting scorecard from normalized deliveries for one innings.

    Returns a dict keyed by batsman name (used as the player "id" for historical
    games, since no real player UUIDs exist).

    Scorecard format is compatible with ``_compute_player_stats()`` in
    ``analytics_case_study.py``:
      {
        runs: int,
        balls_faced: int,
        fours: int,
        sixes: int,
        is_out: bool,
      }
    """
    scorecard: dict[str, dict[str, Any]] = {}

    for d in deliveries:
        if d.get("inning") != inning_no:
            continue
        batsman = d.get("batsman") or ""
        if not batsman:
            continue

        if batsman not in scorecard:
            scorecard[batsman] = {
                "runs": 0,
                "balls_faced": 0,
                "fours": 0,
                "sixes": 0,
                "is_out": False,
            }

        entry = scorecard[batsman]
        runs = int(d.get("runs_off_bat") or 0)
        entry["runs"] += runs
        entry["balls_faced"] += 1
        if runs == 4:
            entry["fours"] += 1
        elif runs == 6:
            entry["sixes"] += 1

        if d.get("is_wicket"):
            entry["is_out"] = True

    return scorecard


def _derive_bowling_scorecard(
    deliveries: list[dict[str, Any]],
    inning_no: int,
) -> dict[str, dict[str, Any]]:
    """Derive bowling scorecard from normalized deliveries for one innings.

    Returns a dict keyed by bowler name (used as player "id" for historical games).

    Format compatible with ``_compute_player_stats()`` in analytics_case_study.py:
      {
        overs_bowled: float,
        balls_bowled: int,
        runs_conceded: int,
        wickets_taken: int,
        maidens: int,
      }
    """
    bowler_balls: dict[str, dict[str, Any]] = {}
    over_runs: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))

    for d in deliveries:
        if d.get("inning") != inning_no:
            continue
        bowler = d.get("bowler") or ""
        if not bowler:
            continue

        if bowler not in bowler_balls:
            bowler_balls[bowler] = {
                "balls_bowled": 0,
                "runs_conceded": 0,
                "wickets_taken": 0,
            }

        entry = bowler_balls[bowler]
        over_num = int(d.get("over_number") or 1)

        total_runs = int(d.get("runs_off_bat") or 0) + int(d.get("extra_runs") or 0)
        entry["balls_bowled"] += 1
        entry["runs_conceded"] += total_runs

        over_runs[bowler][over_num] += total_runs

        if d.get("is_wicket"):
            entry["wickets_taken"] += 1

    scorecard: dict[str, dict[str, Any]] = {}
    for bowler, stats in bowler_balls.items():
        balls = stats["balls_bowled"]
        complete_overs = balls // 6
        remaining_balls = balls % 6
        overs_float = float(f"{complete_overs}.{remaining_balls}")

        # Count maiden overs: overs where 0 runs were conceded
        maidens = sum(
            1
            for over_num, over_run in over_runs[bowler].items()
            if over_run == 0
        )

        scorecard[bowler] = {
            "overs_bowled": overs_float,
            "balls_bowled": balls,
            "runs_conceded": stats["runs_conceded"],
            "wickets_taken": stats["wickets_taken"],
            "maidens": maidens,
        }

    return scorecard


# ---------------------------------------------------------------------------
# Totals validation
# ---------------------------------------------------------------------------


def validate_innings_totals(
    normalized_innings: list[dict[str, Any]],
    innings_preview: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], str | None]:
    """Validate that derived totals reconcile with stored preview expectations.

    ``innings_preview`` items are the stored dry-run preview dicts from
    ``batch.dry_run_summary["innings_preview"]``.

    Returns:
        (totals_validation, warnings, blocking_error)
        - totals_validation: list of per-innings validation result dicts
        - warnings: non-fatal messages
        - blocking_error: non-None string if import should be blocked
    """
    preview_by_no: dict[int, dict[str, Any]] = {
        p.get("inning_no", i + 1): p
        for i, p in enumerate(innings_preview or [])
    }

    validation_results: list[dict[str, Any]] = []
    warnings: list[str] = []
    blocking_error: str | None = None

    for inn in normalized_innings:
        inning_no = inn["inning_no"]
        deliveries = inn["deliveries"]
        team = inn.get("team") or f"Innings {inning_no}"

        # Derive totals from delivery events
        derived_runs = sum(
            int(d.get("runs_off_bat") or 0) + int(d.get("extra_runs") or 0)
            for d in deliveries
        )
        derived_wickets = sum(1 for d in deliveries if d.get("is_wicket"))
        # All balls in the fixture format are treated as legal deliveries;
        # wide/no-ball detection is deferred to Phase 5G with richer formats.
        legal_balls = len(deliveries)

        # Compare against explicit totals in the raw payload
        explicit_runs = inn.get("runs_explicit")
        explicit_wickets = inn.get("wickets_explicit")

        # Compare against stored preview (for additional validation)
        preview = preview_by_no.get(inning_no, {})
        expected_runs = explicit_runs if explicit_runs is not None else preview.get("runs")
        expected_wickets = explicit_wickets if explicit_wickets is not None else preview.get("wickets")

        # Determine validation status
        runs_diff = abs(derived_runs - expected_runs) if expected_runs is not None else 0

        if expected_runs is not None and runs_diff > _RUNS_TOLERANCE:
            val_status = "blocked"
            blocking_error = (
                f"Innings {inning_no} ({team}): derived run total {derived_runs} "
                f"differs from expected {expected_runs} by {runs_diff} runs "
                f"(tolerance: {_RUNS_TOLERANCE}). "
                "Import blocked to preserve data integrity. "
                "Verify the source JSON and re-submit after correction."
            )
            notes = f"Runs mismatch: derived={derived_runs}, expected={expected_runs}"
        elif expected_runs is not None and runs_diff > 0:
            val_status = "warning"
            msg = (
                f"Innings {inning_no} ({team}): derived run total {derived_runs} "
                f"differs from expected {expected_runs} by {runs_diff} runs "
                f"(within tolerance: {_RUNS_TOLERANCE})."
            )
            warnings.append(msg)
            notes = f"Minor runs discrepancy: derived={derived_runs}, expected={expected_runs}"
        else:
            val_status = "ok"
            notes = ""

        validation_results.append(
            {
                "inning_no": inning_no,
                "team": team,
                "derived_runs": derived_runs,
                "expected_runs": expected_runs,
                "derived_wickets": derived_wickets,
                "expected_wickets": expected_wickets,
                "legal_balls": legal_balls,
                "status": val_status,
                "notes": notes,
            }
        )

    return validation_results, warnings, blocking_error


# ---------------------------------------------------------------------------
# Team player list derivation
# ---------------------------------------------------------------------------


def _collect_team_players(
    normalized_innings: list[dict[str, Any]],
    teams_preview: list[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Derive inline player lists for team_a and team_b JSON blobs.

    Uses the innings batting order (batsman names) and bowling order (bowler
    names) from delivery events.  Each player entry has ``{"id": name, "name":
    name}`` - the name is used as a surrogate ID since historical data has no
    real player UUIDs.

    No ORM Player rows are created.

    Returns (team_a_players, team_b_players).
    """
    team_a_batters: set[str] = set()
    team_b_batters: set[str] = set()
    team_a_bowlers: set[str] = set()
    team_b_bowlers: set[str] = set()

    for inn in normalized_innings:
        inning_no = inn["inning_no"]
        deliveries = inn["deliveries"]
        # Innings 1 batters bat for team that bats first (team_a by index)
        # Innings 1 bowlers bowl for the other team
        if inning_no == 1:
            for d in deliveries:
                if d.get("batsman"):
                    team_a_batters.add(d["batsman"])
                if d.get("bowler"):
                    team_b_bowlers.add(d["bowler"])
        elif inning_no == 2:
            for d in deliveries:
                if d.get("batsman"):
                    team_b_batters.add(d["batsman"])
                if d.get("bowler"):
                    team_a_bowlers.add(d["bowler"])

    team_a_names = team_a_batters | team_a_bowlers
    team_b_names = team_b_batters | team_b_bowlers

    def _player_entry(name: str) -> dict[str, str]:
        return {"id": name, "name": name}

    return (
        [_player_entry(n) for n in sorted(team_a_names)],
        [_player_entry(n) for n in sorted(team_b_names)],
    )


# ---------------------------------------------------------------------------
# First innings summary derivation
# ---------------------------------------------------------------------------


def _derive_first_inning_summary(
    inn: dict[str, Any],
    team_name: str,
) -> dict[str, Any]:
    """Build a ``first_inning_summary`` JSON blob from a normalized innings dict.

    The blob format mirrors what the live scoring engine writes:
    ``{batting_team, runs, wickets, overs}``.
    """
    deliveries = inn["deliveries"]
    runs_explicit = inn.get("runs_explicit")
    wickets_explicit = inn.get("wickets_explicit")

    derived_runs = sum(
        int(d.get("runs_off_bat") or 0) + int(d.get("extra_runs") or 0)
        for d in deliveries
    )
    derived_wickets = sum(1 for d in deliveries if d.get("is_wicket"))

    legal_balls = len(deliveries)  # simplified: all fixture balls treated as legal
    complete_overs = legal_balls // 6
    remaining_balls = legal_balls % 6
    overs_float = float(f"{complete_overs}.{remaining_balls}")

    return {
        "batting_team": team_name,
        "runs": runs_explicit if runs_explicit is not None else derived_runs,
        "wickets": wickets_explicit if wickets_explicit is not None else derived_wickets,
        "overs": overs_float,
    }
