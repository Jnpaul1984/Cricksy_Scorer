from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select

from backend.services.organization_entitlement_service import OrganizationCapabilityError
from backend.services.organization_service import OrganizationServiceError
from backend.services.school_statistics_service import SchoolStatisticsServiceError
from backend.services.school_team_analytics_service import (
    TeamAnalyticsRequest,
    _delivery_error,
    calculate_team_limited_overs_analytics,
)
from backend.sql_app.models import (
    Game,
    GameStatus,
    OrganizationEntitlement,
    OrganizationMembership,
    PlayerProfile,
    RoleEnum,
    Team,
    User,
)
from backend.tests.school_test_helpers import create_school, register_user


def _team_snapshot(
    organization_id: str,
    team_id: str,
    players: list[PlayerProfile],
    *,
    source_organization_id: str | None = None,
) -> dict:
    ids = [player.player_id for player in players]
    return {
        "name": "Same display name",
        "players": [
            {
                "id": player.player_id,
                "name": player.player_name,
                "player_profile_id": player.player_id,
            }
            for player in players
        ],
        "playing_xi": ids,
        "school_source": {
            "organization_id": source_organization_id or organization_id,
            "team_id": team_id,
        },
    }


def _delivery(
    inning: int,
    striker: str,
    non_striker: str,
    bowler: str,
    *,
    runs: int = 0,
    extra: str | None = None,
    extra_runs: int = 0,
    wicket: str | None = None,
    dismissed: str | None = None,
) -> dict:
    off_bat = runs if extra in {None, "nb", "no_ball"} else 0
    team_runs = off_bat + (1 if extra in {"nb", "no_ball"} else extra_runs)
    if extra in {"wd", "wide", "b", "bye", "lb", "leg-bye"}:
        team_runs = extra_runs
    return {
        "inning": inning,
        "striker_id": striker,
        "non_striker_id": non_striker,
        "bowler_id": bowler,
        "runs_off_bat": off_bat,
        "extra_type": extra,
        "extra_runs": extra_runs,
        "runs_scored": team_runs,
        "is_wicket": wicket is not None,
        "dismissal_type": wicket,
        "dismissed_player_id": dismissed,
    }


async def _seed_team_game(
    client: TestClient,
    organization_id: str,
    owner_id: str,
    *,
    deliveries: list[dict] | None,
    purpose: str = "official",
    status: GameStatus = GameStatus.completed,
    match_type: str = "limited",
    overs_limit: int = 20,
    reuse_team: Team | None = None,
    dls_enabled: bool = False,
    opponent_organization_id: str | None = None,
) -> tuple[Team, Game, list[PlayerProfile], list[PlayerProfile]]:
    async with client.session_maker() as session:  # type: ignore[attr-defined]
        team = reuse_team or Team(
            id=str(uuid.uuid4()),
            name="Archived XI",
            organization_id=organization_id,
            owner_user_id=owner_id,
            status="archived",
            players=[],
            competitions=[],
        )
        opponent_team = Team(
            id=str(uuid.uuid4()),
            name="Archived XI",
            organization_id=organization_id,
            owner_user_id=owner_id,
            status="archived",
            players=[],
            competitions=[],
        )
        target_players = [
            PlayerProfile(player_id=str(uuid.uuid4()), player_name="Alex Same"),
            PlayerProfile(player_id=str(uuid.uuid4()), player_name="Alex Same"),
        ]
        opponent_players = [
            PlayerProfile(player_id=str(uuid.uuid4()), player_name="Alex Same"),
            PlayerProfile(player_id=str(uuid.uuid4()), player_name="Opponent"),
        ]
        rows = [opponent_team, *target_players, *opponent_players]
        if reuse_team is None:
            rows.append(team)
        session.add_all(rows)
        await session.flush()
        game = Game(
            id=str(uuid.uuid4()),
            team_a=_team_snapshot(organization_id, team.id, target_players),
            team_b=_team_snapshot(
                organization_id,
                opponent_team.id,
                opponent_players,
                source_organization_id=opponent_organization_id,
            ),
            status=status,
            match_purpose=purpose,
            match_type=match_type,
            overs_limit=overs_limit,
            days_limit=None,
            dls_enabled=dls_enabled,
            match_rules=None,
            deliveries=deliveries,
        )
        session.add(game)
        await session.commit()
        return team, game, target_players, opponent_players


def _hand_calculated_deliveries(
    target: list[PlayerProfile], opponent: list[PlayerProfile]
) -> list[dict]:
    batter, non_striker = (player.player_id for player in target)
    opponent_batter, opponent_non_striker = (player.player_id for player in opponent)
    return [
        _delivery(1, batter, non_striker, opponent_batter),
        _delivery(1, batter, non_striker, opponent_batter, runs=4),
        _delivery(1, batter, non_striker, opponent_batter, runs=6),
        _delivery(1, batter, non_striker, opponent_batter, extra="wide", extra_runs=2),
        _delivery(1, batter, non_striker, opponent_batter, extra="no_ball"),
        _delivery(1, batter, non_striker, opponent_batter, runs=2, extra="nb"),
        _delivery(1, batter, non_striker, opponent_batter, extra="bye", extra_runs=2),
        _delivery(1, batter, non_striker, opponent_batter, extra="leg-bye", extra_runs=1),
        _delivery(
            1,
            batter,
            non_striker,
            opponent_batter,
            wicket="run_out",
            dismissed=non_striker,
        ),
        _delivery(2, opponent_batter, opponent_non_striker, batter, runs=2),
        _delivery(2, opponent_batter, opponent_non_striker, batter, extra="b", extra_runs=3),
        _delivery(2, opponent_batter, opponent_non_striker, batter, extra="lb", extra_runs=1),
        _delivery(2, opponent_batter, opponent_non_striker, batter, extra="wd", extra_runs=2),
        _delivery(2, opponent_batter, opponent_non_striker, batter, runs=4, extra="nb"),
        _delivery(2, opponent_batter, opponent_non_striker, batter),
        _delivery(
            2,
            opponent_batter,
            opponent_non_striker,
            batter,
            wicket="run_out",
            dismissed=opponent_non_striker,
        ),
        _delivery(
            2,
            opponent_batter,
            opponent_non_striker,
            batter,
            wicket="caught",
            dismissed=opponent_batter,
        ),
    ]


@pytest.mark.asyncio
async def test_team_analytics_calculates_recorded_counters_and_reloads_corrections(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "internal-team-analytics@example.com")
    organization = create_school(school_client, owner, "Internal Analytics School")
    team, game, target, opponent = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[]
    )
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        saved = await session.get(Game, game.id)
        assert saved is not None
        saved.deliveries = _hand_calculated_deliveries(target, opponent)
        await session.commit()

    request = TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
    async with session_maker() as session:
        result = await calculate_team_limited_overs_analytics(session, request)

    assert result.coverage_status == "usable_recorded_data"
    assert result.analysis_basis == "recorded_delivery_ledger"
    assert result.completeness == "unknown"
    assert result.source_game_ids == (game.id,)
    assert result.included_match_count == 1
    assert result.included_innings_count == 2
    assert result.observed_delivery_count == result.included_delivery_count == 17
    assert [(row.innings_number, row.team_role) for row in result.innings_attribution] == [
        (1, "batting"),
        (2, "bowling"),
    ]
    assert result.batting == {
        "team_runs": 19,
        "bat_runs": 12,
        "wides": 2,
        "no_ball_penalties": 2,
        "byes": 2,
        "leg_byes": 1,
        "wickets_lost": 1,
        "legal_balls": 6,
        "legal_dots": 2,
        "fours": 1,
        "sixes": 1,
        "run_rate": 19.0,
        "legal_dot_percentage": 33.33,
        "runs_per_wicket": 19.0,
    }
    assert result.bowling == {
        "opposition_team_runs": 13,
        "bowler_charged_runs": 9,
        "wides": 2,
        "no_ball_penalties": 1,
        "byes": 3,
        "leg_byes": 1,
        "team_wickets": 2,
        "bowler_credited_wickets": 1,
        "legal_balls": 6,
        "legal_dots": 3,
        "team_concession_rate": 13.0,
        "bowling_economy": 9.0,
        "legal_dot_percentage": 50.0,
    }

    async with session_maker() as session:
        saved = await session.get(Game, game.id)
        assert saved is not None
        corrected = list(saved.deliveries)
        corrected[1] = {**corrected[1], "runs_off_bat": 1, "runs_scored": 1}
        saved.deliveries = corrected
        await session.commit()
    async with session_maker() as session:
        recalculated = await calculate_team_limited_overs_analytics(session, request)
    assert recalculated.batting["team_runs"] == 16
    assert recalculated.batting["fours"] == 0
    async with session_maker() as session:
        saved = await session.get(Game, game.id)
        assert saved is not None
        corrected = list(saved.deliveries)
        corrected[1] = {**corrected[1], "runs_off_bat": 4, "runs_scored": 4}
        saved.deliveries = corrected
        await session.commit()
    async with session_maker() as session:
        restored = await calculate_team_limited_overs_analytics(session, request)
    assert restored.batting["team_runs"] == 19


@pytest.mark.asyncio
async def test_team_analytics_reports_cohort_and_ledger_exclusions(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-exclusions@example.com")
    organization = create_school(school_client, owner, "Analytics Exclusions School")
    team, game, target, opponent = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[]
    )
    await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=None,
        purpose="practice",
        reuse_team=team,
    )
    await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=[],
        overs_limit=10,
        reuse_team=team,
    )
    await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=[],
        status=GameStatus.in_progress,
        reuse_team=team,
    )
    await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=[],
        match_type="custom",
        reuse_team=team,
    )
    await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[], reuse_team=team
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, game.id)
        assert saved is not None
        malformed = _hand_calculated_deliveries(target, opponent)
        malformed[0] = {**malformed[0], "runs_off_bat": -1}
        saved.deliveries = malformed
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )
    assert result.coverage_status == "invalid_or_ambiguous_records"
    assert result.eligible_match_count == 2
    assert result.included_innings_count == 1
    assert set(result.cohort_exclusion_counts) >= {
        "non_official_match",
        "overs_limit_mismatch",
        "not_completed",
        "unsupported_match_type",
    }
    assert {row.reason_code for row in result.exclusions} >= {
        "no_usable_ledger",
        "invalid_numeric_field",
    }


@pytest.mark.asyncio
async def test_team_analytics_excludes_bad_innings_atomically_and_keeps_valid_sibling(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-atomic@example.com")
    organization = create_school(school_client, owner, "Atomic Ledger School")
    team, game, target, opponent = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[]
    )
    good_inning = _delivery(
        1, target[0].player_id, target[1].player_id, opponent[0].player_id, runs=4
    )
    malformed_inning = _delivery(
        2, opponent[0].player_id, opponent[1].player_id, target[0].player_id, runs=6
    )
    malformed_inning["runs_scored"] = -1
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, game.id)
        assert saved is not None
        saved.deliveries = [good_inning, malformed_inning]
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )
    assert result.coverage_status == "invalid_or_ambiguous_records"
    assert result.included_innings_count == 1
    assert result.included_delivery_count == 1
    assert result.source_game_ids == (game.id,)
    assert result.batting["team_runs"] == 4
    assert result.bowling["opposition_team_runs"] == 0
    assert any(
        exclusion.game_id == game.id
        and exclusion.innings_number == 2
        and exclusion.reason_code == "invalid_numeric_field"
        for exclusion in result.exclusions
    )

    second_team, second_game, second_target, second_opponent = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[], reuse_team=team
    )
    tagged_sibling = _delivery(
        1,
        second_target[0].player_id,
        second_target[1].player_id,
        second_opponent[0].player_id,
        runs=6,
    )
    missing_tag = _delivery(
        2,
        second_opponent[0].player_id,
        second_opponent[1].player_id,
        second_target[0].player_id,
    )
    missing_tag.pop("inning")
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, second_game.id)
        assert saved is not None
        saved.deliveries = [tagged_sibling, missing_tag]
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        missing_tag_result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )
    assert missing_tag_result.batting["team_runs"] == 4
    assert missing_tag_result.included_innings_count == 1
    assert missing_tag_result.source_game_ids == (game.id,)
    assert any(
        exclusion.game_id == second_game.id
        and exclusion.reason_code == "invalid_innings_tag"
        and exclusion.innings_number is None
        for exclusion in missing_tag_result.exclusions
    )
    assert second_team.id == team.id

    _, invalid_record_game, third_target, third_opponent = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[], reuse_team=team
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, invalid_record_game.id)
        assert saved is not None
        valid_record = _delivery(
            1,
            third_target[0].player_id,
            third_target[1].player_id,
            third_opponent[0].player_id,
            runs=6,
        )
        saved.deliveries = [valid_record, "malformed"]  # type: ignore[list-item]
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        invalid_record_result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )
    assert invalid_record_result.batting["team_runs"] == 4
    assert invalid_record_result.included_innings_count == 1
    assert invalid_record_game.id not in invalid_record_result.source_game_ids
    assert any(
        exclusion.game_id == invalid_record_game.id
        and exclusion.reason_code == "invalid_delivery_record"
        and exclusion.innings_number is None
        for exclusion in invalid_record_result.exclusions
    )


@pytest.mark.asyncio
async def test_team_analytics_excludes_unsupported_innings_and_preserves_sibling_game(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-unsupported-innings@example.com")
    organization = create_school(school_client, owner, "Unsupported Innings Analytics Org")
    team, invalid_game, target, opponent = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[]
    )
    valid_innings = [
        _delivery(1, target[0].player_id, target[1].player_id, opponent[0].player_id, runs=4),
        _delivery(2, opponent[0].player_id, opponent[1].player_id, target[0].player_id, runs=6),
    ]
    unsupported_innings = [
        _delivery(innings, target[0].player_id, target[1].player_id, opponent[0].player_id)
        for innings in (3, 99)
    ]
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, invalid_game.id)
        assert saved is not None
        saved.deliveries = valid_innings + unsupported_innings
        await session.commit()

    _, sibling_game, sibling_target, sibling_opponent = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[], reuse_team=team
    )
    sibling_delivery = _delivery(
        1,
        sibling_target[0].player_id,
        sibling_target[1].player_id,
        sibling_opponent[0].player_id,
        runs=2,
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, sibling_game.id)
        assert saved is not None
        saved.deliveries = [sibling_delivery]
        await session.commit()

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )

    assert result.coverage_status == "invalid_or_ambiguous_records"
    assert result.included_match_count == 1
    assert result.included_innings_count == 1
    assert result.included_delivery_count == 1
    assert result.source_game_ids == (sibling_game.id,)
    assert result.batting["team_runs"] == 2
    assert {
        (exclusion.reason_code, exclusion.innings_number)
        for exclusion in result.exclusions
        if exclusion.game_id == invalid_game.id
    } == {("unsupported_innings_tag", 3), ("unsupported_innings_tag", 99)}


def test_team_analytics_delivery_validation_rejects_unsupported_categories() -> None:
    side_ids = {"team_a": {"batter", "partner"}, "team_b": {"bowler"}}
    delivery = _delivery(1, "batter", "partner", "bowler", wicket="caught", dismissed="batter")
    for innings in (3, 99):
        assert (
            _delivery_error(
                {**delivery, "inning": innings}, batting_side="team_a", side_ids=side_ids
            )
            == "unsupported_innings_tag"
        )
    assert (
        _delivery_error(
            {**delivery, "dismissal_type": "mystery"}, batting_side="team_a", side_ids=side_ids
        )
        == "unsupported_dismissal_type"
    )
    assert (
        _delivery_error(
            {
                **delivery,
                "dismissal_type": " caught  ",
                "extra_type": "no_ball",
                "runs_scored": 1,
            },
            batting_side="team_a",
            side_ids=side_ids,
        )
        == "invalid_dismissal_record"
    )
    wide_bowled = _delivery(
        1,
        "batter",
        "partner",
        "bowler",
        extra="wide",
        extra_runs=1,
        wicket="bowled",
        dismissed="batter",
    )
    assert (
        _delivery_error(wide_bowled, batting_side="team_a", side_ids=side_ids)
        == "invalid_dismissal_record"
    )


@pytest.mark.asyncio
async def test_team_analytics_normalizes_supported_dismissals_and_rejects_unknown_labels(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-dismissals@example.com")
    organization = create_school(school_client, owner, "Dismissal Analytics Org")
    team, game, target, opponent = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[]
    )
    dismissal_types = (
        "bowled",
        "caught",
        "lbw",
        "stumped",
        "HIT   WICKET",
        "run out",
        "obstructing the field",
        "hit the ball twice",
        "timed out",
        "retired out",
        "handled the ball",
    )
    valid_innings = [
        _delivery(
            2,
            opponent[0].player_id,
            opponent[1].player_id,
            target[0].player_id,
            wicket=dismissal,
            dismissed=opponent[0].player_id,
        )
        for dismissal in dismissal_types
    ]
    valid_innings[0]["dismissal_type"] = "  BOWLED "
    unknown_wicket = _delivery(
        2,
        opponent[0].player_id,
        opponent[1].player_id,
        target[0].player_id,
        wicket="mystery dismissal",
        dismissed=opponent[0].player_id,
    )
    valid_sibling_inning = _delivery(
        1, target[0].player_id, target[1].player_id, opponent[0].player_id, runs=4
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, game.id)
        assert saved is not None
        saved.deliveries = [valid_sibling_inning, *valid_innings, unknown_wicket]
        await session.commit()

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )

    assert result.coverage_status == "invalid_or_ambiguous_records"
    assert result.included_innings_count == 1
    assert result.included_delivery_count == 1
    assert result.batting["team_runs"] == 4
    assert result.bowling["team_wickets"] == 0
    assert result.bowling["bowler_credited_wickets"] == 0
    assert any(
        exclusion.game_id == game.id
        and exclusion.innings_number == 2
        and exclusion.reason_code == "unsupported_dismissal_type"
        for exclusion in result.exclusions
    )


@pytest.mark.asyncio
async def test_team_analytics_counts_normalized_bowler_and_team_dismissals(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-dismissal-categories@example.com")
    organization = create_school(school_client, owner, "Dismissal Category Analytics Org")
    team, game, target, opponent = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[]
    )
    dismissal_types = (
        "bowled",
        "caught",
        "lbw",
        "stumped",
        "hit wicket",
        "run out",
        "obstructing the field",
        "hit the ball twice",
        "timed out",
        "retired out",
        "handled the ball",
    )
    deliveries = [
        _delivery(
            2,
            opponent[0].player_id,
            opponent[1].player_id,
            target[0].player_id,
            wicket=dismissal,
            dismissed=opponent[0].player_id,
        )
        for dismissal in dismissal_types
    ]
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, game.id)
        assert saved is not None
        saved.deliveries = deliveries
        await session.commit()

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )

    assert result.coverage_status == "usable_recorded_data"
    assert result.bowling["team_wickets"] == 11
    assert result.bowling["bowler_credited_wickets"] == 5


@pytest.mark.asyncio
async def test_team_analytics_weights_match_rates_and_accepts_eleven_ball_reduced_innings(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-weighted@example.com")
    organization = create_school(school_client, owner, "Weighted Analytics School")
    team, first_game, target, opponent = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[]
    )
    first_innings = [
        _delivery(
            1,
            target[0].player_id,
            target[1].player_id,
            opponent[0].player_id,
            runs=4 if index == 0 else 0,
        )
        for index in range(6)
    ]
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, first_game.id)
        assert saved is not None
        saved.deliveries = first_innings
        await session.commit()
    _, reduced_game, reduced_target, reduced_opponent = await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=[],
        reuse_team=team,
        dls_enabled=True,
    )
    opposition_first_innings = [
        _delivery(
            1,
            reduced_opponent[0].player_id,
            reduced_opponent[1].player_id,
            reduced_target[0].player_id,
            runs=1,
        )
        for _ in range(6)
    ]
    reduced_chase = [
        _delivery(
            2,
            reduced_target[0].player_id,
            reduced_target[1].player_id,
            reduced_opponent[0].player_id,
            runs=1 if index == 0 else 0,
        )
        for index in range(11)
    ]
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, reduced_game.id)
        assert saved is not None
        saved.deliveries = opposition_first_innings + reduced_chase
        await session.commit()

    statements: list[str] = []
    engine = school_client.session_maker.kw["bind"]  # type: ignore[attr-defined]

    def record_statement(*args: object) -> None:
        statement = str(args[2]).upper()
        if "FROM GAMES" in statement:
            statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record_statement)
    try:
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            result = await calculate_team_limited_overs_analytics(
                session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
            )
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record_statement)

    assert result.coverage_status == "usable_recorded_data"
    assert result.eligible_match_count == 2
    assert result.included_match_count == 2
    assert result.included_innings_count == 3
    assert result.batting["team_runs"] == 5
    assert result.batting["legal_balls"] == 17
    assert result.batting["run_rate"] == 1.76
    assert result.batting["legal_dot_percentage"] == 88.24
    assert len(statements) == 3


@pytest.mark.asyncio
async def test_team_analytics_excludes_a_foreign_opposite_side_in_sql(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-foreign-side@example.com")
    foreign_owner = register_user(school_client, "team-analytics-foreign-other@example.com")
    organization = create_school(school_client, owner, "Target Analytics Org")
    foreign_organization = create_school(school_client, foreign_owner, "Opponent Analytics Org")
    team, _, target, _ = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[], overs_limit=10
    )
    opposing_player = PlayerProfile(player_id=str(uuid.uuid4()), player_name="Foreign Player")
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        session.add(opposing_player)
        await session.flush()
        foreign_team = Team(
            id=str(uuid.uuid4()),
            name="Foreign XI",
            organization_id=foreign_organization["id"],
            owner_user_id=foreign_owner.id,
            status="archived",
            players=[],
            competitions=[],
        )
        session.add(foreign_team)
        await session.flush()
        game = Game(
            id=str(uuid.uuid4()),
            team_a=_team_snapshot(organization["id"], team.id, target),
            team_b=_team_snapshot(
                organization["id"],
                foreign_team.id,
                [opposing_player],
                source_organization_id=foreign_organization["id"],
            ),
            status=GameStatus.completed,
            match_purpose="official",
            match_type="limited",
            overs_limit=20,
            days_limit=None,
            dls_enabled=False,
            match_rules=None,
            deliveries=[],
        )
        session.add(game)
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )
    assert result.coverage_status == "no_eligible_games"
    assert result.source_game_ids == ()
    assert game.id not in result.source_game_ids


@pytest.mark.asyncio
@pytest.mark.parametrize("target_side", ["team_a", "team_b"])
@pytest.mark.parametrize("malformed_side", [[], "not-an-object"])
async def test_team_analytics_excludes_malformed_opposite_side_snapshots(
    school_client: TestClient,
    target_side: str,
    malformed_side: object,
) -> None:
    owner = register_user(
        school_client,
        f"team-analytics-malformed-side-{target_side}-{type(malformed_side).__name__}@example.com",
    )
    organization = create_school(school_client, owner, "Malformed Side Analytics Org")
    team, game, target_players, opponent_players = await _seed_team_game(
        school_client,
        organization["id"],
        owner.id,
        deliveries=[],
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, game.id)
        assert saved is not None
        valid_target = _team_snapshot(organization["id"], team.id, target_players)
        if target_side == "team_a":
            saved.team_a = valid_target
            saved.team_b = malformed_side
        else:
            saved.team_a = malformed_side
            saved.team_b = valid_target
        saved.deliveries = [
            _delivery(
                1,
                target_players[0].player_id,
                target_players[1].player_id,
                opponent_players[0].player_id,
                runs=4,
            )
        ]
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )
    assert result.coverage_status == "invalid_or_ambiguous_records"
    assert result.source_game_ids == ()
    assert result.observed_delivery_count == 1
    assert result.included_innings_count == 0
    assert [(row.game_id, row.reason_code) for row in result.exclusions] == [
        (game.id, "invalid_frozen_side_identity")
    ]


@pytest.mark.asyncio
async def test_team_analytics_excludes_non_list_deliveries_container(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-invalid-container@example.com")
    organization = create_school(school_client, owner, "Invalid Container Analytics Org")
    team, game, _, _ = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[]
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, game.id)
        assert saved is not None
        saved.deliveries = {"not": "a list"}  # type: ignore[assignment]
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )
    assert result.coverage_status == "invalid_or_ambiguous_records"
    assert result.observed_delivery_count == 0
    assert [(row.game_id, row.reason_code) for row in result.exclusions] == [
        (game.id, "invalid_ledger_shape")
    ]


@pytest.mark.asyncio
async def test_team_analytics_denies_inactive_and_removed_membership(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-membership@example.com")
    organization = create_school(school_client, owner, "Membership Analytics Org")
    team, _, _, _ = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[]
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        membership = await session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization["id"],
                OrganizationMembership.user_id == owner.id,
            )
        )
        assert membership is not None
        membership.status = "disabled"
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(OrganizationServiceError):
            await calculate_team_limited_overs_analytics(
                session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
            )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        membership = await session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization["id"],
                OrganizationMembership.user_id == owner.id,
            )
        )
        assert membership is not None
        await session.delete(membership)
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(OrganizationServiceError):
            await calculate_team_limited_overs_analytics(
                session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
            )


@pytest.mark.asyncio
async def test_team_analytics_separates_no_cohort_from_empty_ledger_and_zero_denominators(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-empty@example.com")
    organization = create_school(school_client, owner, "Empty Analytics School")
    team, game, target, opponent = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[]
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        no_cohort = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 10)
        )
    assert no_cohort.coverage_status == "no_eligible_games"
    assert no_cohort.cohort_exclusion_counts == {"overs_limit_mismatch": 1}

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        empty_ledger = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )
    assert empty_ledger.coverage_status == "no_usable_ledger"
    assert empty_ledger.batting["run_rate"] is None
    assert empty_ledger.batting["legal_dot_percentage"] is None
    assert empty_ledger.batting["runs_per_wicket"] is None

    wide_only = _delivery(
        1,
        target[0].player_id,
        target[1].player_id,
        opponent[0].player_id,
        extra="wd",
        extra_runs=1,
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, game.id)
        assert saved is not None
        saved.deliveries = [wide_only]
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )
    assert result.coverage_status == "usable_recorded_data"
    assert result.batting["legal_balls"] == 0
    assert result.batting["run_rate"] is None
    assert result.batting["legal_dot_percentage"] is None
    assert result.batting["runs_per_wicket"] is None


@pytest.mark.asyncio
async def test_team_analytics_excludes_missing_unknown_and_ambiguous_delivery_data(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-invalid@example.com")
    organization = create_school(school_client, owner, "Invalid Analytics School")
    reason_codes: set[str] = set()
    for failure in (
        "missing_number",
        "unknown_extra",
        "ambiguous_player",
        "missing_tag",
        "ambiguous_side",
        "retired_hurt",
    ):
        team, game, target, opponent = await _seed_team_game(
            school_client, organization["id"], owner.id, deliveries=[]
        )
        record = _hand_calculated_deliveries(target, opponent)[0]
        if failure == "missing_number":
            record.pop("runs_off_bat")
        elif failure == "unknown_extra":
            record["extra_type"] = "mystery"
        elif failure == "ambiguous_player":
            record["striker_id"] = str(uuid.uuid4())
        elif failure == "ambiguous_side":
            record = _hand_calculated_deliveries(target, opponent)[0]
        elif failure == "retired_hurt":
            record.update(
                {
                    "is_wicket": True,
                    "dismissal_type": "retired_hurt",
                    "dismissed_player_id": target[0].player_id,
                }
            )
        else:
            record.pop("inning")
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            saved = await session.get(Game, game.id)
            assert saved is not None
            saved.deliveries = [record]
            if failure == "ambiguous_side":
                saved.team_b = {
                    **saved.team_b,
                    "school_source": {
                        "organization_id": organization["id"],
                        "team_id": team.id,
                    },
                }
            await session.commit()
        async with school_client.session_maker() as session:  # type: ignore[attr-defined]
            result = await calculate_team_limited_overs_analytics(
                session,
                TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20),
            )
        assert result.coverage_status == "invalid_or_ambiguous_records"
        reason_codes.update(row.reason_code for row in result.exclusions)
    assert {
        "invalid_numeric_field",
        "unknown_extra_type",
        "ambiguous_innings_side",
        "ambiguous_team_side",
        "invalid_innings_tag",
        "invalid_dismissal_record",
    } <= reason_codes


@pytest.mark.asyncio
async def test_team_analytics_is_tenant_safe_and_uses_existing_capability(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "team-analytics-owner@example.com")
    foreign_owner = register_user(school_client, "team-analytics-foreign@example.com")
    organization = create_school(school_client, owner, "Analytics Tenant")
    foreign_organization = create_school(school_client, foreign_owner, "Foreign Analytics Tenant")
    team, _, _, _ = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[]
    )
    foreign_team, _, _, _ = await _seed_team_game(
        school_client, foreign_organization["id"], foreign_owner.id, deliveries=[]
    )

    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(SchoolStatisticsServiceError) as denied:
            await calculate_team_limited_overs_analytics(
                session, TeamAnalyticsRequest(owner.id, organization["id"], foreign_team.id, 20)
            )
        assert denied.value.status_code == 404

        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        assert entitlement is not None
        entitlement.status = "disabled"
        user = await session.get(User, owner.id)
        assert user is not None
        user.role = RoleEnum.org_pro
        user.is_superuser = True
        user.org_id = organization["id"]
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        with pytest.raises(OrganizationCapabilityError) as denied:
            await calculate_team_limited_overs_analytics(
                session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
            )
    assert denied.value.capability == "school_basic_statistics"
