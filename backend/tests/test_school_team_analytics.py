from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.services.organization_entitlement_service import OrganizationCapabilityError
from backend.services.school_statistics_service import SchoolStatisticsServiceError
from backend.services.school_team_analytics_service import (
    TeamAnalyticsRequest,
    calculate_team_limited_overs_analytics,
)
from backend.sql_app.models import (
    Game,
    GameStatus,
    OrganizationEntitlement,
    PlayerProfile,
    RoleEnum,
    Team,
    User,
)
from backend.tests.school_test_helpers import create_school, register_user


def _team_snapshot(organization_id: str, team_id: str, players: list[PlayerProfile]) -> dict:
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
        "school_source": {"organization_id": organization_id, "team_id": team_id},
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
            team_b=_team_snapshot(organization_id, opponent_team.id, opponent_players),
            status=status,
            match_purpose=purpose,
            match_type=match_type,
            overs_limit=overs_limit,
            days_limit=None,
            dls_enabled=False,
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
    malformed = _hand_calculated_deliveries(target, opponent)
    malformed[0] = {**malformed[0], "runs_off_bat": -1}
    await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=malformed, reuse_team=team
    )
    malformed_ledger_team, malformed_ledger_game, _, _ = await _seed_team_game(
        school_client, organization["id"], owner.id, deliveries=[], reuse_team=team
    )
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        saved = await session.get(Game, malformed_ledger_game.id)
        assert saved is not None
        saved.deliveries = {"not": "a ledger"}  # type: ignore[assignment]
        await session.commit()
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        result = await calculate_team_limited_overs_analytics(
            session, TeamAnalyticsRequest(owner.id, organization["id"], team.id, 20)
        )
    assert result.coverage_status == "invalid_or_ambiguous_records"
    assert result.eligible_match_count == 3
    assert result.included_innings_count == 0
    assert {row.reason_code for row in result.exclusions} >= {
        "non_official_match",
        "overs_limit_mismatch",
        "no_usable_ledger",
        "invalid_ledger_shape",
        "invalid_numeric_field",
    }
    assert malformed_ledger_team.id == team.id


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
    assert no_cohort.exclusions[0].reason_code == "overs_limit_mismatch"

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
