"""Private, recorded-ledger analytics for an authorized School/Club Team."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

from backend.domain.constants import CREDIT_BOWLER, INVALID_ON_NO_BALL, INVALID_ON_WIDE, norm_extra
from backend.services import school_statistics_service
from backend.sql_app import models
from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession


class BattingTotals(TypedDict):
    team_runs: int
    bat_runs: int
    wides: int
    no_ball_penalties: int
    byes: int
    leg_byes: int
    wickets_lost: int
    legal_balls: int
    legal_dots: int
    fours: int
    sixes: int
    run_rate: float | None
    legal_dot_percentage: float | None
    runs_per_wicket: float | None


class BowlingTotals(TypedDict):
    opposition_team_runs: int
    bowler_charged_runs: int
    wides: int
    no_ball_penalties: int
    byes: int
    leg_byes: int
    team_wickets: int
    bowler_credited_wickets: int
    legal_balls: int
    legal_dots: int
    team_concession_rate: float | None
    bowling_economy: float | None
    legal_dot_percentage: float | None


CoverageStatus = Literal[
    "no_eligible_games",
    "no_usable_ledger",
    "invalid_or_ambiguous_records",
    "usable_recorded_data",
]


@dataclass(frozen=True)
class TeamAnalyticsRequest:
    actor_user_id: str
    organization_id: str
    team_id: str
    overs_limit: int


@dataclass(frozen=True)
class AnalyticsExclusion:
    game_id: str
    reason_code: str
    innings_number: int | None = None


@dataclass(frozen=True)
class InningsAttribution:
    game_id: str
    innings_number: int
    batting_side: Literal["team_a", "team_b"]
    team_role: Literal["batting", "bowling"]


@dataclass(frozen=True)
class TeamAnalyticsResult:
    organization_id: str
    team_id: str
    overs_limit: int
    analysis_basis: Literal["recorded_delivery_ledger"]
    completeness: Literal["unknown"]
    coverage_status: CoverageStatus
    eligible_match_count: int
    included_match_count: int
    included_innings_count: int
    observed_delivery_count: int
    included_delivery_count: int
    source_game_ids: tuple[str, ...]
    innings_attribution: tuple[InningsAttribution, ...]
    exclusions: tuple[AnalyticsExclusion, ...]
    batting: BattingTotals
    bowling: BowlingTotals


def _empty_batting() -> BattingTotals:
    return {
        "team_runs": 0,
        "bat_runs": 0,
        "wides": 0,
        "no_ball_penalties": 0,
        "byes": 0,
        "leg_byes": 0,
        "wickets_lost": 0,
        "legal_balls": 0,
        "legal_dots": 0,
        "fours": 0,
        "sixes": 0,
        "run_rate": None,
        "legal_dot_percentage": None,
        "runs_per_wicket": None,
    }


def _empty_bowling() -> BowlingTotals:
    return {
        "opposition_team_runs": 0,
        "bowler_charged_runs": 0,
        "wides": 0,
        "no_ball_penalties": 0,
        "byes": 0,
        "leg_byes": 0,
        "team_wickets": 0,
        "bowler_credited_wickets": 0,
        "legal_balls": 0,
        "legal_dots": 0,
        "team_concession_rate": None,
        "bowling_economy": None,
        "legal_dot_percentage": None,
    }


def _school_source(side: dict) -> tuple[str | None, str | None]:
    source = side.get("school_source")
    if not isinstance(source, dict):
        return None, None
    organization_id = source.get("organization_id")
    team_id = source.get("team_id")
    return (
        organization_id if isinstance(organization_id, str) else None,
        team_id if isinstance(team_id, str) else None,
    )


def _team_scope_clause(request: TeamAnalyticsRequest):
    org_a = models.Game.team_a["school_source"]["organization_id"].as_string()
    team_a = models.Game.team_a["school_source"]["team_id"].as_string()
    org_b = models.Game.team_b["school_source"]["organization_id"].as_string()
    team_b = models.Game.team_b["school_source"]["team_id"].as_string()
    return or_(
        and_(
            org_a == request.organization_id,
            team_a == request.team_id,
            or_(org_b == request.organization_id, org_b.is_(None)),
        ),
        and_(
            org_b == request.organization_id,
            team_b == request.team_id,
            or_(org_a == request.organization_id, org_a.is_(None)),
        ),
    )


def _team_metadata_stmt(request: TeamAnalyticsRequest):
    return (
        select(
            models.Game.id,
            models.Game.match_purpose,
            models.Game.status,
            models.Game.match_type,
            models.Game.overs_limit,
            models.Game.days_limit,
            models.Game.match_rules,
        )
        .where(_team_scope_clause(request))
        .order_by(models.Game.id)
    )


def _team_games_stmt(
    request: TeamAnalyticsRequest, eligible_game_ids: set[str]
) -> Select[tuple[models.Game]]:
    """Load delivery JSON only for the exact Team and eligible overs cohort."""
    return (
        select(models.Game)
        .where(
            _team_scope_clause(request),
            models.Game.id.in_(eligible_game_ids),
        )
        .order_by(models.Game.id)
    )


def _cohort_exclusion(
    *,
    match_purpose: str,
    status: models.GameStatus,
    match_type: str,
    overs_limit: int | None,
    days_limit: int | None,
    match_rules: object,
    requested_overs_limit: int,
) -> str | None:
    if match_purpose != "official":
        return "non_official_match"
    if status != models.GameStatus.completed:
        return "not_completed"
    if match_type != "limited":
        return "unsupported_match_type"
    if overs_limit != requested_overs_limit:
        return "overs_limit_mismatch"
    if days_limit is not None:
        return "multi_day_match"
    if match_rules is not None:
        return "unsupported_match_rules"
    return None


def _frozen_side_ids(side: dict, *, require_canonical: bool) -> set[str] | None:
    players = side.get("players")
    playing_xi = side.get("playing_xi")
    if not isinstance(players, list) or not isinstance(playing_xi, list) or not playing_xi:
        return None
    frozen_ids: set[str] = set()
    for player in players:
        if not isinstance(player, dict) or not isinstance(player.get("id"), str):
            return None
        player_id = player["id"]
        if (
            not player_id.strip()
            or player_id in frozen_ids
            or (require_canonical and player.get("player_profile_id") != player_id)
        ):
            return None
        frozen_ids.add(player_id)
    if any(
        not isinstance(player_id, str) or player_id not in frozen_ids for player_id in playing_xi
    ):
        return None
    if len(set(playing_xi)) != len(playing_xi):
        return None
    return set(playing_xi)


def _integer_field(delivery: dict, field: str) -> int | None:
    value = delivery.get(field)
    if type(value) is not int or value < 0:
        return None
    return value


def _delivery_error(
    delivery: dict,
    *,
    batting_side: Literal["team_a", "team_b"] | None,
    side_ids: dict[Literal["team_a", "team_b"], set[str]],
) -> str | None:
    inning = delivery.get("inning")
    if type(inning) is not int or inning < 1:
        return "invalid_innings_tag"
    if any(
        _integer_field(delivery, key) is None
        for key in ("runs_off_bat", "extra_runs", "runs_scored")
    ):
        return "invalid_numeric_field"
    if type(delivery.get("is_wicket")) is not bool:
        return "invalid_wicket_record"

    striker = delivery.get("striker_id")
    non_striker = delivery.get("non_striker_id")
    bowler = delivery.get("bowler_id")
    if not all(
        isinstance(value, str) and value.strip() for value in (striker, non_striker, bowler)
    ):
        return "missing_participant_identity"
    if batting_side is None:
        return "ambiguous_innings_side"
    bowling_side: Literal["team_a", "team_b"] = "team_b" if batting_side == "team_a" else "team_a"
    if (
        striker not in side_ids[batting_side]
        or non_striker not in side_ids[batting_side]
        or bowler not in side_ids[bowling_side]
    ):
        return "ambiguous_participant_identity"

    raw_extra = delivery.get("extra_type")
    extra = norm_extra(raw_extra)
    if raw_extra is not None and (
        not isinstance(raw_extra, str) or (raw_extra.strip() and extra is None)
    ):
        return "unknown_extra_type"
    off_bat = delivery["runs_off_bat"]
    extra_runs = delivery["extra_runs"]
    team_runs = delivery["runs_scored"]
    if extra is None and (extra_runs != 0 or team_runs != off_bat):
        return "contradictory_run_record"
    if extra == "wd" and (off_bat != 0 or extra_runs != team_runs or team_runs < 1):
        return "contradictory_run_record"
    if extra == "nb" and (extra_runs not in {0, 1} or team_runs != off_bat + 1):
        return "contradictory_run_record"
    if extra in {"b", "lb"} and (off_bat != 0 or extra_runs != team_runs):
        return "contradictory_run_record"

    is_wicket = delivery["is_wicket"]
    dismissal = delivery.get("dismissal_type")
    dismissed_id = delivery.get("dismissed_player_id")
    if is_wicket:
        if not isinstance(dismissal, str) or not dismissal.strip():
            return "invalid_dismissal_record"
        if not isinstance(dismissed_id, str) or dismissed_id not in side_ids[batting_side]:
            return "ambiguous_dismissed_player_identity"
        normalized_dismissal = dismissal.strip().lower()
        if normalized_dismissal == "retired_hurt":
            return "invalid_dismissal_record"
        if extra == "nb" and normalized_dismissal in INVALID_ON_NO_BALL:
            return "invalid_dismissal_record"
        if extra == "wd" and normalized_dismissal in INVALID_ON_WIDE:
            return "invalid_dismissal_record"
    elif dismissal or dismissed_id is not None:
        return "contradictory_dismissal_record"
    return None


def _add_delivery(
    totals: dict[str, int],
    delivery: dict,
    *,
    into_batting: bool,
) -> None:
    extra = norm_extra(delivery.get("extra_type"))
    team_runs = delivery["runs_scored"]
    off_bat = delivery["runs_off_bat"]
    is_legal = extra not in {"wd", "nb"}
    is_dot = is_legal and team_runs == 0
    if into_batting:
        totals["team_runs"] += team_runs
        totals["bat_runs"] += off_bat
        totals["wickets_lost"] += int(delivery["is_wicket"])
        totals["fours"] += int(off_bat == 4)
        totals["sixes"] += int(off_bat == 6)
    else:
        totals["opposition_team_runs"] += team_runs
        totals["team_wickets"] += int(delivery["is_wicket"])
        if delivery["is_wicket"] and delivery["dismissal_type"].strip().lower() in CREDIT_BOWLER:
            totals["bowler_credited_wickets"] += 1

    if extra == "wd":
        totals["wides"] += team_runs
    elif extra == "nb":
        totals["no_ball_penalties"] += 1
    elif extra == "b":
        totals["byes"] += delivery["extra_runs"]
    elif extra == "lb":
        totals["leg_byes"] += delivery["extra_runs"]
    if is_legal:
        totals["legal_balls"] += 1
    if is_dot:
        totals["legal_dots"] += 1
    if not into_batting:
        totals["bowler_charged_runs"] += team_runs - (
            delivery["extra_runs"] if extra in {"b", "lb"} else 0
        )


def _finish_batting(totals: dict[str, int]) -> BattingTotals:
    balls = totals["legal_balls"]
    wickets = totals["wickets_lost"]
    return {
        "team_runs": totals["team_runs"],
        "bat_runs": totals["bat_runs"],
        "wides": totals["wides"],
        "no_ball_penalties": totals["no_ball_penalties"],
        "byes": totals["byes"],
        "leg_byes": totals["leg_byes"],
        "wickets_lost": totals["wickets_lost"],
        "legal_balls": balls,
        "legal_dots": totals["legal_dots"],
        "fours": totals["fours"],
        "sixes": totals["sixes"],
        "run_rate": round(totals["team_runs"] * 6 / balls, 2) if balls else None,
        "legal_dot_percentage": round(totals["legal_dots"] * 100 / balls, 2) if balls else None,
        "runs_per_wicket": round(totals["team_runs"] / wickets, 2) if wickets else None,
    }


def _finish_bowling(totals: dict[str, int]) -> BowlingTotals:
    balls = totals["legal_balls"]
    return {
        "opposition_team_runs": totals["opposition_team_runs"],
        "bowler_charged_runs": totals["bowler_charged_runs"],
        "wides": totals["wides"],
        "no_ball_penalties": totals["no_ball_penalties"],
        "byes": totals["byes"],
        "leg_byes": totals["leg_byes"],
        "team_wickets": totals["team_wickets"],
        "bowler_credited_wickets": totals["bowler_credited_wickets"],
        "legal_balls": balls,
        "legal_dots": totals["legal_dots"],
        "team_concession_rate": (
            round(totals["opposition_team_runs"] * 6 / balls, 2) if balls else None
        ),
        "bowling_economy": (round(totals["bowler_charged_runs"] * 6 / balls, 2) if balls else None),
        "legal_dot_percentage": round(totals["legal_dots"] * 100 / balls, 2) if balls else None,
    }


async def calculate_team_limited_overs_analytics(
    db: AsyncSession, request: TeamAnalyticsRequest
) -> TeamAnalyticsResult:
    """Calculate a single Team's perspective for one exact limited-overs cohort."""
    if type(request.overs_limit) is not int or not 1 <= request.overs_limit <= 120:
        raise ValueError("overs_limit must be an integer from 1 to 120")

    await school_statistics_service._authorize(
        db,
        organization_id=request.organization_id,
        actor_user_id=request.actor_user_id,
        capability="school_basic_statistics",
    )
    team = await db.scalar(
        select(models.Team).where(
            models.Team.id == request.team_id,
            models.Team.organization_id == request.organization_id,
        )
    )
    if team is None:
        raise school_statistics_service._not_found("Team")

    metadata_rows = (await db.execute(_team_metadata_stmt(request))).all()
    eligible_game_ids: set[str] = set()
    exclusions: list[AnalyticsExclusion] = []
    for (
        game_id,
        match_purpose,
        status,
        match_type,
        overs_limit,
        days_limit,
        match_rules,
    ) in metadata_rows:
        reason = _cohort_exclusion(
            match_purpose=match_purpose,
            status=status,
            match_type=match_type,
            overs_limit=overs_limit,
            days_limit=days_limit,
            match_rules=match_rules,
            requested_overs_limit=request.overs_limit,
        )
        if reason is None:
            eligible_game_ids.add(game_id)
        else:
            exclusions.append(AnalyticsExclusion(game_id, reason))
    games = list((await db.scalars(_team_games_stmt(request, eligible_game_ids))).all())
    batting = {key: value for key, value in _empty_batting().items() if isinstance(value, int)}
    bowling = {key: value for key, value in _empty_bowling().items() if isinstance(value, int)}
    attributions: list[InningsAttribution] = []
    source_game_ids: set[str] = set()
    eligible_matches = len(eligible_game_ids)
    observed_deliveries = included_deliveries = included_innings = 0
    invalid_records = False
    no_ledger = False

    for game in games:
        raw_deliveries = game.deliveries
        if raw_deliveries is None or raw_deliveries == []:
            exclusions.append(AnalyticsExclusion(game.id, "no_usable_ledger"))
            no_ledger = True
            continue
        if not isinstance(raw_deliveries, list):
            exclusions.append(AnalyticsExclusion(game.id, "invalid_ledger_shape"))
            invalid_records = True
            continue
        observed_deliveries += len(raw_deliveries)

        team_a_org, team_a_id = _school_source(game.team_a)
        team_b_org, team_b_id = _school_source(game.team_b)
        candidate_sides = [
            side
            for side, organization_id, source_team_id in (
                ("team_a", team_a_org, team_a_id),
                ("team_b", team_b_org, team_b_id),
            )
            if organization_id == request.organization_id and source_team_id == request.team_id
        ]
        if len(candidate_sides) != 1:
            exclusions.append(AnalyticsExclusion(game.id, "ambiguous_team_side"))
            invalid_records = True
            continue
        target_side: Literal["team_a", "team_b"] = candidate_sides[0]  # type: ignore[assignment]
        ids_a = _frozen_side_ids(game.team_a, require_canonical=target_side == "team_a")
        ids_b = _frozen_side_ids(game.team_b, require_canonical=target_side == "team_b")
        if not ids_a or not ids_b or ids_a.intersection(ids_b):
            exclusions.append(AnalyticsExclusion(game.id, "invalid_frozen_side_identity"))
            invalid_records = True
            continue
        side_ids: dict[Literal["team_a", "team_b"], set[str]] = {
            "team_a": ids_a,
            "team_b": ids_b,
        }

        grouped: dict[int, list[dict]] = {}
        game_has_unattributed_record = False
        for record in raw_deliveries:
            if not isinstance(record, dict):
                exclusions.append(AnalyticsExclusion(game.id, "invalid_delivery_record"))
                invalid_records = True
                game_has_unattributed_record = True
                continue
            inning = record.get("inning")
            if type(inning) is not int or inning < 1:
                exclusions.append(AnalyticsExclusion(game.id, "invalid_innings_tag"))
                invalid_records = True
                game_has_unattributed_record = True
                continue
            grouped.setdefault(inning, []).append(record)

        if game_has_unattributed_record:
            continue

        for inning, deliveries in sorted(grouped.items()):
            inferred_sides: set[str] = set()
            side_ambiguous = False
            for delivery in deliveries:
                striker_id = delivery.get("striker_id")
                matching = (
                    [side for side, ids in side_ids.items() if striker_id in ids]
                    if isinstance(striker_id, str)
                    else []
                )
                if len(matching) != 1:
                    side_ambiguous = True
                    break
                inferred_sides.add(matching[0])
            batting_side = (
                next(iter(inferred_sides))
                if len(inferred_sides) == 1 and not side_ambiguous
                else None
            )
            errors = {
                error
                for delivery in deliveries
                if (
                    error := _delivery_error(
                        delivery,
                        batting_side=batting_side,  # type: ignore[arg-type]
                        side_ids=side_ids,
                    )
                )
                is not None
            }
            if errors:
                for error in sorted(errors):
                    exclusions.append(AnalyticsExclusion(game.id, error, inning))
                invalid_records = True
                continue

            is_team_batting = batting_side == target_side
            accumulator = batting if is_team_batting else bowling
            for delivery in deliveries:
                _add_delivery(accumulator, delivery, into_batting=is_team_batting)
            included_deliveries += len(deliveries)
            included_innings += 1
            source_game_ids.add(game.id)
            attributions.append(
                InningsAttribution(
                    game_id=game.id,
                    innings_number=inning,
                    batting_side=batting_side,  # type: ignore[arg-type]
                    team_role="batting" if is_team_batting else "bowling",
                )
            )

    coverage_status: CoverageStatus
    if eligible_matches == 0:
        coverage_status = "no_eligible_games"
    elif invalid_records:
        coverage_status = "invalid_or_ambiguous_records"
    elif included_innings:
        coverage_status = "usable_recorded_data"
    elif no_ledger:
        coverage_status = "no_usable_ledger"
    else:
        coverage_status = "no_usable_ledger"

    return TeamAnalyticsResult(
        organization_id=request.organization_id,
        team_id=request.team_id,
        overs_limit=request.overs_limit,
        analysis_basis="recorded_delivery_ledger",
        completeness="unknown",
        coverage_status=coverage_status,
        eligible_match_count=eligible_matches,
        included_match_count=len(source_game_ids),
        included_innings_count=included_innings,
        observed_delivery_count=observed_deliveries,
        included_delivery_count=included_deliveries,
        source_game_ids=tuple(sorted(source_game_ids)),
        innings_attribution=tuple(attributions),
        exclusions=tuple(exclusions),
        batting=_finish_batting(batting),
        bowling=_finish_bowling(bowling),
    )
