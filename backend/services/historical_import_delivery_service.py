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

from backend.domain.constants import norm_extra

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


def coerce_delivery_ledger(raw_deliveries: Any) -> list[dict[str, Any]]:
    """Return deliveries as a list of dict rows.

    Historical environments may surface JSON columns as text; accept both
    native list payloads and JSON-string encoded arrays.
    """
    if isinstance(raw_deliveries, list):
        return [row for row in raw_deliveries if isinstance(row, dict)]

    if isinstance(raw_deliveries, str):
        text = raw_deliveries.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return []
        if isinstance(parsed, list):
            return [row for row in parsed if isinstance(row, dict)]
    return []


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def cricket_overs_from_legal_balls(legal_balls: int) -> float:
    complete_overs = max(int(legal_balls), 0) // 6
    remaining_balls = max(int(legal_balls), 0) % 6
    return float(f"{complete_overs}.{remaining_balls}")


def legal_balls_to_decimal_overs(legal_balls: int) -> float:
    return max(int(legal_balls), 0) / 6.0


def cricket_overs_to_legal_balls(overs_value: Any) -> int:
    if overs_value in (None, ""):
        return 0
    text = str(overs_value).strip()
    if not text:
        return 0
    whole_part, dot, fractional_part = text.partition(".")
    whole = _safe_int(whole_part)
    balls = _safe_int(fractional_part[:1]) if dot else 0
    return (whole * 6) + balls


def is_legal_delivery(delivery: dict[str, Any]) -> bool:
    explicit = delivery.get("is_legal_delivery")
    if isinstance(explicit, bool):
        return explicit

    extra_type = norm_extra(delivery.get("extra_type"))
    if extra_type in {"wd", "nb"}:
        return False

    extras = delivery.get("extras")
    if isinstance(extras, dict):
        if _safe_int(extras.get("wides")) > 0 or _safe_int(extras.get("noballs")) > 0:
            return False
    return True


def _extract_registry_people_map(parsed: dict[str, Any]) -> dict[str, str]:
    info_payload = parsed.get("info")
    info = info_payload if isinstance(info_payload, dict) else {}
    registry_payload = info.get("registry")
    registry = registry_payload if isinstance(registry_payload, dict) else {}
    people_payload = registry.get("people")
    people = people_payload if isinstance(people_payload, dict) else {}
    result: dict[str, str] = {}
    for name, source_id in people.items():
        name_text = str(name).strip()
        source_id_text = str(source_id).strip() if source_id is not None else ""
        if name_text and source_id_text:
            result[name_text] = source_id_text
    return result


def _phase_from_over_number(over_number: int) -> str:
    if over_number <= 6:
        return "powerplay"
    if over_number <= 15:
        return "middle"
    return "death"


def _parse_powerplay_ranges(innings_obj: dict[str, Any]) -> list[dict[str, Any]]:
    powerplays_raw = innings_obj.get("powerplays")
    if not isinstance(powerplays_raw, list):
        return []

    def _ball_position(raw: Any) -> int | None:
        text = str(raw).strip()
        if not text or "." not in text:
            return None
        over_text, _, ball_text = text.partition(".")
        try:
            over = int(over_text)
            ball = int(ball_text)
        except ValueError:
            return None
        if ball < 1:
            ball = 1
        return over * 10 + ball

    parsed_ranges: list[dict[str, Any]] = []
    for entry in powerplays_raw:
        if not isinstance(entry, dict):
            continue
        start = _ball_position(entry.get("from"))
        end = _ball_position(entry.get("to"))
        if start is None or end is None:
            continue
        parsed_ranges.append(
            {
                "start": start,
                "end": end,
                "powerplay_type": str(entry.get("type") or "mandatory").strip() or "mandatory",
            }
        )
    return parsed_ranges


def _resolve_powerplay_type(
    *,
    over_number: int,
    ball_in_over: int,
    powerplay_ranges: list[dict[str, Any]],
) -> str | None:
    position = (max(over_number, 1) - 1) * 10 + max(ball_in_over, 1)
    for item in powerplay_ranges:
        start = item.get("start")
        end = item.get("end")
        if isinstance(start, int) and isinstance(end, int) and start <= position <= end:
            value = item.get("powerplay_type")
            if isinstance(value, str) and value.strip():
                return value.strip()
            return "mandatory"
    return None


# ---------------------------------------------------------------------------
# Delivery normalization
# ---------------------------------------------------------------------------


def _normalize_ball(
    ball: dict[str, Any],
    inning_idx: int,
    *,
    over_number: int | None = None,
    ball_in_over: int | None = None,
    batting_team: str | None = None,
    bowling_team: str | None = None,
    registry_people_map: dict[str, str] | None = None,
    legal_ball_index: int | None = None,
    powerplay_ranges: list[dict[str, Any]] | None = None,
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
    extra_type: str | None = None
    is_legal = True
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

    extras_detail = ball.get("extras")
    if isinstance(extras_detail, dict):
        if _safe_int(extras_detail.get("wides")) > 0:
            extra_type = "wd"
            is_legal = False
        elif _safe_int(extras_detail.get("noballs")) > 0:
            extra_type = "nb"
            is_legal = False
        elif _safe_int(extras_detail.get("legbyes")) > 0:
            extra_type = "lb"
        elif _safe_int(extras_detail.get("byes")) > 0:
            extra_type = "b"
    else:
        normalized_extra_type = norm_extra(ball.get("extra_type"))
        if normalized_extra_type:
            extra_type = normalized_extra_type
            if normalized_extra_type in {"wd", "nb"}:
                is_legal = False

    wicket_raw = ball.get("wicket", False)
    wickets_list_raw = ball.get("wickets")
    has_wickets_list = isinstance(wickets_list_raw, list) and len(wickets_list_raw) > 0
    is_wicket = has_wickets_list or (
        bool(wicket_raw) if not isinstance(wicket_raw, dict) else bool(wicket_raw)
    )

    wicket_data: dict[str, Any] | None = None
    if isinstance(wickets_list_raw, list) and wickets_list_raw:
        first_wicket = wickets_list_raw[0]
        wicket_data = first_wicket if isinstance(first_wicket, dict) else None
    elif isinstance(wicket_raw, dict):
        wicket_data = wicket_raw

    player_out = (
        str(wicket_data.get("player_out") or "").strip() if isinstance(wicket_data, dict) else ""
    )
    dismissal_type = (
        str(wicket_data.get("kind") or wicket_data.get("dismissal_type") or "").strip()
        if isinstance(wicket_data, dict)
        else ""
    )
    fielders: list[str] = []
    if isinstance(wicket_data, dict):
        raw_fielders = wicket_data.get("fielders")
        if isinstance(raw_fielders, list):
            for entry in raw_fielders:
                if isinstance(entry, str) and entry.strip():
                    fielders.append(entry.strip())
                elif isinstance(entry, dict):
                    name = str(entry.get("name") or "").strip()
                    if name:
                        fielders.append(name)
        elif isinstance(raw_fielders, dict):
            name = str(raw_fielders.get("name") or "").strip()
            if name:
                fielders.append(name)
        single_fielder = str(wicket_data.get("fielder") or "").strip()
        if single_fielder:
            fielders.append(single_fielder)

    fielders = sorted(set(fielders))
    primary_fielder = fielders[0] if fielders else None
    resolved_over = over_number if over_number is not None else int(ball.get("over") or 1)
    resolved_ball_in_over = ball_in_over if ball_in_over is not None else int(ball.get("ball") or 1)
    powerplay_type = _resolve_powerplay_type(
        over_number=resolved_over,
        ball_in_over=resolved_ball_in_over,
        powerplay_ranges=powerplay_ranges or [],
    )

    batter_name = str(ball.get("batsman") or ball.get("batter") or "")
    bowler_name = str(ball.get("bowler") or "")
    non_striker_name = str(ball.get("non_striker") or ball.get("nonStriker") or "")
    registry = registry_people_map or {}
    extras_detail = ball.get("extras")
    extras_types: list[str] = []
    if isinstance(extras_detail, dict):
        for key, value in extras_detail.items():
            if _safe_int(value) > 0:
                extras_types.append(str(key))

    dismissal_value = dismissal_type or ("Unknown" if is_wicket else None)

    return {
        "inning": inning_idx,
        "inning_no": inning_idx,
        "over_number": resolved_over,
        "ball_in_over": resolved_ball_in_over,
        "runs_off_bat": runs_off_bat,
        "extra_runs": extra_runs,
        "runs_scored": runs_off_bat + extra_runs,
        "extra_type": extra_type,
        "extras_types": extras_types,
        "extras": extras_detail if isinstance(extras_detail, dict) else {},
        "is_wicket": is_wicket,
        "is_legal_delivery": is_legal,
        "batsman": batter_name,
        "batter": batter_name,
        "batter_id": batter_name,
        "batter_source_player_id": registry.get(batter_name),
        "bowler": bowler_name,
        "bowler_id": bowler_name,
        "bowler_source_player_id": registry.get(bowler_name),
        "non_striker": non_striker_name,
        "non_striker_id": non_striker_name,
        "non_striker_source_player_id": registry.get(non_striker_name),
        "player_out": player_out or None,
        "player_out_source_player_id": registry.get(player_out) if player_out else None,
        "dismissal_type": dismissal_value,
        "wicket_type": dismissal_value,
        "fielder_id": primary_fielder,
        "fielder_source_player_id": registry.get(primary_fielder) if primary_fielder else None,
        "fielders": fielders,
        "fielders_source_player_ids": [
            {"name": fielder_name, "source_player_id": registry.get(fielder_name)}
            for fielder_name in fielders
        ],
        "batting_team": batting_team,
        "bowling_team": bowling_team,
        "phase": _phase_from_over_number(resolved_over),
        "powerplay_type": powerplay_type,
        "legal_ball_index": legal_ball_index,
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
    info_payload = parsed.get("info")
    info = info_payload if isinstance(info_payload, dict) else {}
    teams_payload = info.get("teams")
    teams = (
        [str(team).strip() for team in teams_payload if isinstance(team, str) and str(team).strip()]
        if isinstance(teams_payload, list)
        else []
    )
    registry_people_map = _extract_registry_people_map(parsed)
    result: list[dict[str, Any]] = []

    for idx, innings in enumerate(innings_raw, start=1):
        if not isinstance(innings, dict):
            continue

        innings_obj = innings
        # Cricsheet JSON often stores innings as {"<Team Name>": {...}} instead
        # of a flat innings object. Unwrap that single-key wrapper for import.
        if len(innings_obj) == 1 and not any(
            k in innings_obj for k in ("balls", "deliveries", "overs")
        ):
            nested = next(iter(innings_obj.values()))
            if isinstance(nested, dict):
                innings_obj = dict(nested)
                if "team" not in innings_obj:
                    innings_obj["team"] = next(iter(innings.keys()))

        innings_team = innings_obj.get("team") or None
        innings_team_text = str(innings_team).strip() if isinstance(innings_team, str) else None
        bowling_team = None
        if innings_team_text and len(teams) >= 2:
            if teams[0] == innings_team_text:
                bowling_team = teams[1]
            elif teams[1] == innings_team_text:
                bowling_team = teams[0]

        powerplay_ranges = _parse_powerplay_ranges(innings_obj)
        balls_raw = innings_obj.get("balls") or innings_obj.get("deliveries") or []
        normalized_deliveries: list[dict[str, Any]]
        legal_ball_counter = 0
        if isinstance(balls_raw, list):
            normalized_deliveries = []
            for ball in balls_raw:
                if not isinstance(ball, dict):
                    continue
                delivery = _normalize_ball(
                    ball,
                    idx,
                    batting_team=innings_team_text,
                    bowling_team=bowling_team,
                    registry_people_map=registry_people_map,
                    powerplay_ranges=powerplay_ranges,
                )
                if is_legal_delivery(delivery):
                    legal_ball_counter += 1
                    delivery["legal_ball_index"] = legal_ball_counter
                normalized_deliveries.append(delivery)
        else:
            normalized_deliveries = []

        if not normalized_deliveries:
            overs_raw = innings_obj.get("overs")
            if isinstance(overs_raw, list):
                for over in overs_raw:
                    if not isinstance(over, dict):
                        continue
                    over_idx_raw = over.get("over")
                    # Cricsheet over numbers are 0-indexed; internal delivery rows
                    # use 1-indexed over_number for analytics compatibility.
                    over_number = int(over_idx_raw) + 1 if isinstance(over_idx_raw, int) else None
                    over_deliveries = over.get("deliveries")
                    if not isinstance(over_deliveries, list):
                        continue
                    for ball_idx, ball in enumerate(over_deliveries, start=1):
                        if isinstance(ball, dict):
                            delivery = _normalize_ball(
                                ball,
                                idx,
                                over_number=over_number,
                                ball_in_over=ball_idx,
                                batting_team=innings_team_text,
                                bowling_team=bowling_team,
                                registry_people_map=registry_people_map,
                                powerplay_ranges=powerplay_ranges,
                            )
                            if is_legal_delivery(delivery):
                                legal_ball_counter += 1
                                delivery["legal_ball_index"] = legal_ball_counter
                            normalized_deliveries.append(delivery)

        runs_explicit = innings_obj.get("runs")
        wickets_explicit = innings_obj.get("wickets")

        result.append(
            {
                "inning_no": idx,
                "team": innings_team_text,
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
        if is_legal_delivery(d):
            entry["balls_faced"] += 1
        if runs == 4:
            entry["fours"] += 1
        elif runs == 6:
            entry["sixes"] += 1

        if d.get("is_wicket"):
            player_out = str(d.get("player_out") or "").strip()
            if player_out:
                out_entry = scorecard.get(player_out)
                if out_entry is None:
                    out_entry = {
                        "runs": 0,
                        "balls_faced": 0,
                        "fours": 0,
                        "sixes": 0,
                        "is_out": False,
                    }
                    scorecard[player_out] = out_entry
                out_entry["is_out"] = True
            else:
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
        if is_legal_delivery(d):
            entry["balls_bowled"] += 1
        entry["runs_conceded"] += total_runs

        over_runs[bowler][over_num] += total_runs

        if d.get("is_wicket"):
            entry["wickets_taken"] += 1

    scorecard: dict[str, dict[str, Any]] = {}
    for bowler, stats in bowler_balls.items():
        balls = stats["balls_bowled"]
        overs_float = cricket_overs_from_legal_balls(balls)

        # Count maiden overs: overs where 0 runs were conceded
        maidens = sum(1 for over_num, over_run in over_runs[bowler].items() if over_run == 0)

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
        p.get("inning_no", i + 1): p for i, p in enumerate(innings_preview or [])
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
            int(d.get("runs_off_bat") or 0) + int(d.get("extra_runs") or 0) for d in deliveries
        )
        derived_wickets = sum(1 for d in deliveries if d.get("is_wicket"))
        legal_balls = sum(1 for d in deliveries if is_legal_delivery(d))

        # Compare against explicit totals in the raw payload
        explicit_runs = inn.get("runs_explicit")
        explicit_wickets = inn.get("wickets_explicit")

        # Compare against stored preview (for additional validation)
        preview = preview_by_no.get(inning_no, {})
        expected_runs = explicit_runs if explicit_runs is not None else preview.get("runs")
        expected_wickets = (
            explicit_wickets if explicit_wickets is not None else preview.get("wickets")
        )

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
    team_a_name = teams_preview[0] if teams_preview else None
    team_b_name = teams_preview[1] if len(teams_preview) > 1 else None
    team_a_batters: set[str] = set()
    team_b_batters: set[str] = set()
    team_a_bowlers: set[str] = set()
    team_b_bowlers: set[str] = set()

    for inn in normalized_innings:
        inning_no = inn["inning_no"]
        deliveries = inn["deliveries"]
        batting_team = inn.get("team")
        if batting_team and batting_team == team_a_name:
            for d in deliveries:
                if d.get("batsman"):
                    team_a_batters.add(d["batsman"])
                if d.get("bowler"):
                    team_b_bowlers.add(d["bowler"])
        elif batting_team and batting_team == team_b_name:
            for d in deliveries:
                if d.get("batsman"):
                    team_b_batters.add(d["batsman"])
                if d.get("bowler"):
                    team_a_bowlers.add(d["bowler"])
        elif inning_no == 1:
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
        int(d.get("runs_off_bat") or 0) + int(d.get("extra_runs") or 0) for d in deliveries
    )
    derived_wickets = sum(1 for d in deliveries if d.get("is_wicket"))

    legal_balls = sum(1 for d in deliveries if is_legal_delivery(d))
    overs_float = cricket_overs_from_legal_balls(legal_balls)

    return {
        "batting_team": team_name,
        "runs": runs_explicit if runs_explicit is not None else derived_runs,
        "wickets": wickets_explicit if wickets_explicit is not None else derived_wickets,
        "overs": overs_float,
    }
