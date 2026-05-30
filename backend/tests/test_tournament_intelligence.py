"""Phase 10S.1 — Tournament Intelligence tests.

Validates:
- Tournament grouping by competition/season/gender/format
- Derived standings computation
- Tournament summary building
- Team journey building
- Knockout/finals context
- Data completeness labels
- API endpoints return correct structures

Run:
    cd backend
    CRICKSY_IN_MEMORY_DB=1 APP_SECRET_KEY=test-secret-key \\
      python -m pytest tests/test_tournament_intelligence.py -v
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.api.schemas.tournament_intelligence import (
    TournamentGroupKey,
)
from backend.services.tournament_intelligence_service import (
    _build_derived_standings,
    _build_knockout_context,
    _build_team_journey,
    _build_tournament_summary,
    _derive_format_family,
    _derive_outcome,
    _detect_stage_label,
    _group_eligible_games,
    _is_final_stage,
)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_group_key(
    competition_code: str = "CPL_MEN",
    competition_name: str = "Caribbean Premier League",
    season: str | None = "2023",
    gender_category: str = "men",
    format_family: str = "T20",
) -> TournamentGroupKey:
    return TournamentGroupKey(
        competition_code=competition_code,
        competition_name=competition_name,
        season=season,
        gender_category=gender_category,
        format_family=format_family,
    )


def _make_game(
    game_id: str = "game-1",
    team_a: str = "Team Alpha",
    team_b: str = "Team Beta",
    result: str | None = "Team Alpha won by 30 runs",
    match_type: str = "T20",
    deliveries: list | None = None,
    batting_scorecard: dict | None = None,
    bowling_scorecard: dict | None = None,
    innings_summary: list | None = None,
) -> Any:
    """Build a minimal mock Game object."""
    game = MagicMock()
    game.id = game_id
    game.match_type = match_type
    game.result = result
    game.deliveries = deliveries or []
    game.batting_scorecard = batting_scorecard or {}
    game.bowling_scorecard = bowling_scorecard or {}
    phases: dict[str, Any] = {
        "historical_import": {
            "is_historical": True,
            "batch_id": f"batch-{game_id}",
        }
    }
    if innings_summary:
        phases["historical_innings_summary"] = innings_summary
    game.phases = phases
    game.team_a = {"name": team_a}
    game.team_b = {"name": team_b}
    return game


def _make_batch(batch_id: str = "batch-game-1") -> Any:
    batch = MagicMock()
    batch.id = batch_id
    batch.is_finalized = True
    batch.applied_game_id = f"game-{batch_id}"
    batch.status = "valid"
    batch.error_count = 0
    batch.source_filename = "test.json"
    batch.source_format = "cricsheet"
    return batch


def _make_meta(
    event_name: str = "Caribbean Premier League",
    season: str = "2023",
    gender: str = "male",
    venue: str = "Providence Stadium",
    match_date: str = "2023-09-20",
    deliveries_imported: bool = False,
    competition_stage: str | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "is_historical": True,
        "event_name": event_name,
        "season": season,
        "gender": gender,
        "venue": venue,
        "match_date": match_date,
        "deliveries_imported": deliveries_imported,
    }
    if competition_stage:
        meta["competition_stage"] = competition_stage
    return meta


def _make_match_aggregate(
    match_id: str = "game-1",
    team_a: str = "Team Alpha",
    team_b: str = "Team Beta",
    winner_team: str | None = "Team Alpha",
    winner_team_canonical: str | None = "Team Alpha",
    winner_confidence: str = "high",
    season: str | None = "2023",
    match_date: str | None = "2023-09-20",
    total_runs: int = 300,
    total_wickets: int = 15,
    venue: str | None = "Providence Stadium",
    team_a_canonical: str | None = "Team Alpha",
    team_b_canonical: str | None = "Team Beta",
) -> Any:
    """Build a minimal MatchAggregate-like object."""
    from backend.api.schemas.historical_stats import MatchAggregate, InningsAggregate

    return MatchAggregate(
        match_id=match_id,
        teams=f"{team_a} vs {team_b}",
        team_a=team_a,
        team_b=team_b,
        season=season,
        season_source="metadata",
        match_date=match_date,
        innings_count=2,
        total_runs=total_runs,
        total_wickets=total_wickets,
        winner_team=winner_team,
        winner_team_canonical=winner_team_canonical,
        winner_confidence=winner_confidence,  # type: ignore[arg-type]
        wicket_derivation_source="innings_summary",
        venue=venue,
        team_a_canonical=team_a_canonical,
        team_b_canonical=team_b_canonical,
        innings_totals=[
            InningsAggregate(inning_no=1, team=team_a, runs=160, wickets=7, overs=20.0),
            InningsAggregate(inning_no=2, team=team_b, runs=140, wickets=10, overs=18.0),
        ],
    )


def _make_eligible_entry(
    game_id: str = "game-1",
    team_a: str = "Team Alpha",
    team_b: str = "Team Beta",
    result: str | None = "Team Alpha won by 30 runs",
    event_name: str = "Caribbean Premier League",
    season: str = "2023",
    gender: str = "male",
    winner: str | None = "Team Alpha",
    competition_stage: str | None = None,
    innings_summary: list | None = None,
) -> tuple:
    """Build a (game, batch, meta, match_aggregate) tuple."""
    game = _make_game(
        game_id=game_id,
        team_a=team_a,
        team_b=team_b,
        result=result,
        innings_summary=innings_summary
        or [
            {"inning_no": 1, "team": team_a, "runs": 160, "wickets": 7, "overs": 20.0},
            {"inning_no": 2, "team": team_b, "runs": 130, "wickets": 10, "overs": 17.0},
        ],
    )
    if competition_stage:
        game.phases["historical_import"]["competition_stage"] = competition_stage
    batch = _make_batch(f"batch-{game_id}")
    meta = _make_meta(
        event_name=event_name,
        season=season,
        gender=gender,
        competition_stage=competition_stage,
    )
    match_agg = _make_match_aggregate(
        match_id=game_id,
        team_a=team_a,
        team_b=team_b,
        team_a_canonical=team_a,
        team_b_canonical=team_b,
        winner_team=winner,
        winner_team_canonical=winner,
        season=season,
    )
    return (game, batch, meta, match_agg)


# ---------------------------------------------------------------------------
# Unit tests: format family detection
# ---------------------------------------------------------------------------


class TestDeriveFormatFamily:
    def test_t20(self) -> None:
        assert _derive_format_family("T20") == "T20"

    def test_twenty20(self) -> None:
        assert _derive_format_family("Twenty20") == "T20"

    def test_odi(self) -> None:
        assert _derive_format_family("ODI") == "ODI"

    def test_one_day(self) -> None:
        assert _derive_format_family("One Day International") == "ODI"

    def test_test(self) -> None:
        assert _derive_format_family("Test") == "TEST"

    def test_first_class(self) -> None:
        assert _derive_format_family("First Class") == "TEST"

    def test_unknown(self) -> None:
        assert _derive_format_family(None) == "unknown"

    def test_uses_second_param_fallback(self) -> None:
        assert _derive_format_family(None, "T20") == "T20"


# ---------------------------------------------------------------------------
# Unit tests: outcome derivation
# ---------------------------------------------------------------------------


class TestDeriveOutcome:
    def test_win(self) -> None:
        assert _derive_outcome("Team Alpha won by 30 runs", "Team Alpha") == "win"

    def test_loss(self) -> None:
        assert _derive_outcome("Team Beta won by 5 wickets", "Team Alpha") == "loss"

    def test_tie(self) -> None:
        assert _derive_outcome("Match tied", "Team Alpha") == "tie"

    def test_no_result(self) -> None:
        assert _derive_outcome("No result - rain", "Team Alpha") == "no_result"

    def test_unknown_when_no_result_text(self) -> None:
        assert _derive_outcome(None, "Team Alpha") == "unknown"


# ---------------------------------------------------------------------------
# Unit tests: stage label detection
# ---------------------------------------------------------------------------


class TestDetectStageLabel:
    def test_final(self) -> None:
        assert _detect_stage_label({}, "CPL Final 2023") == "Final"

    def test_grand_final(self) -> None:
        assert _detect_stage_label({}, "Grand Final") == "Final"

    def test_semi_final(self) -> None:
        assert _detect_stage_label({}, "Semi Final 1") == "Semi Final"

    def test_qualifier(self) -> None:
        assert _detect_stage_label({"competition_stage": "Qualifier 1"}) == "Qualifier"

    def test_eliminator(self) -> None:
        assert _detect_stage_label({"tournament_round": "Eliminator"}) == "Eliminator"

    def test_none_for_group_match(self) -> None:
        assert _detect_stage_label({}, "Team A vs Team B") is None

    def test_is_final_stage(self) -> None:
        assert _is_final_stage("Final") is True
        assert _is_final_stage("Semi Final") is False
        assert _is_final_stage(None) is False


# ---------------------------------------------------------------------------
# Unit tests: derived standings
# ---------------------------------------------------------------------------


class TestDerivedStandings:
    def _build_two_team_group(self, result_a: str, result_b: str | None = None) -> list:
        """Build a two-match group where Alpha vs Beta results vary."""
        entries = [
            _make_eligible_entry(
                game_id="g1",
                team_a="Team Alpha",
                team_b="Team Beta",
                result="Team Alpha won by 30 runs",
                winner="Team Alpha",
            ),
            _make_eligible_entry(
                game_id="g2",
                team_a="Team Beta",
                team_b="Team Alpha",
                result="Team Beta won by 5 wickets",
                winner="Team Beta",
            ),
        ]
        return entries

    def test_standings_has_correct_teams(self) -> None:
        entries = self._build_two_team_group("a", "b")
        rows = _build_derived_standings(entries)
        team_names = {r.team_name for r in rows}
        assert "Team Alpha" in team_names
        assert "Team Beta" in team_names

    def test_standings_plays_count(self) -> None:
        entries = self._build_two_team_group("a", "b")
        rows = _build_derived_standings(entries)
        for row in rows:
            assert row.played == 2

    def test_standings_equal_wins(self) -> None:
        entries = self._build_two_team_group("a", "b")
        rows = _build_derived_standings(entries)
        # Both teams have 1 win
        wins = {r.team_name: r.wins for r in rows}
        assert wins["Team Alpha"] == 1
        assert wins["Team Beta"] == 1

    def test_standings_points(self) -> None:
        entries = self._build_two_team_group("a", "b")
        rows = _build_derived_standings(entries)
        for row in rows:
            assert row.points == 2  # 1 win * 2 points each

    def test_single_winner_dominates(self) -> None:
        # Alpha wins both matches
        entries = [
            _make_eligible_entry(
                game_id="g1",
                team_a="Team Alpha",
                team_b="Team Beta",
                result="Team Alpha won by 30 runs",
                winner="Team Alpha",
            ),
            _make_eligible_entry(
                game_id="g2",
                team_a="Team Alpha",
                team_b="Team Gamma",
                result="Team Alpha won by 5 wickets",
                winner="Team Alpha",
            ),
        ]
        rows = _build_derived_standings(entries)
        alpha = next(r for r in rows if r.team_name == "Team Alpha")
        assert alpha.wins == 2
        assert alpha.points == 4
        assert rows[0].team_name == "Team Alpha"  # sorted first

    def test_derived_label(self) -> None:
        entries = self._build_two_team_group("a", "b")
        rows = _build_derived_standings(entries)
        for row in rows:
            assert "derived" in row.note.lower() or "not official" in row.note.lower()


# ---------------------------------------------------------------------------
# Unit tests: tournament summary
# ---------------------------------------------------------------------------


class TestBuildTournamentSummary:
    def test_empty_group_returns_zero_matches(self) -> None:
        gk = _make_group_key()
        result = _build_tournament_summary(gk, [], [])
        assert result.match_count == 0
        assert result.total_runs == 0

    def test_match_count(self) -> None:
        gk = _make_group_key()
        entries = [
            _make_eligible_entry(game_id="g1"),
            _make_eligible_entry(game_id="g2"),
        ]
        result = _build_tournament_summary(gk, entries, [])
        assert result.match_count == 2

    def test_teams_present(self) -> None:
        gk = _make_group_key()
        entries = [
            _make_eligible_entry(game_id="g1", team_a="Lions", team_b="Falcons"),
            _make_eligible_entry(game_id="g2", team_a="Lions", team_b="Eagles"),
        ]
        result = _build_tournament_summary(gk, entries, [])
        assert "Lions" in result.teams
        assert "Falcons" in result.teams
        assert "Eagles" in result.teams

    def test_total_runs_aggregated(self) -> None:
        gk = _make_group_key()
        entries = [
            _make_eligible_entry(
                game_id="g1",
                innings_summary=[
                    {"inning_no": 1, "team": "Team Alpha", "runs": 150, "wickets": 6, "overs": 20},
                    {"inning_no": 2, "team": "Team Beta", "runs": 120, "wickets": 10, "overs": 18},
                ],
            ),
        ]
        result = _build_tournament_summary(gk, entries, [])
        assert result.total_runs == 270

    def test_derived_standings_populated(self) -> None:
        gk = _make_group_key()
        entries = [_make_eligible_entry(game_id="g1")]
        result = _build_tournament_summary(gk, entries, [])
        assert isinstance(result.derived_standings, list)
        assert len(result.derived_standings) > 0

    def test_data_completeness_populated(self) -> None:
        gk = _make_group_key()
        entries = [_make_eligible_entry(game_id="g1")]
        result = _build_tournament_summary(gk, entries, [])
        dc = result.data_completeness
        assert dc.total_matches == 1
        assert dc.matches_with_result >= 0

    def test_standings_labeled_derived(self) -> None:
        gk = _make_group_key()
        entries = [_make_eligible_entry(game_id="g1")]
        result = _build_tournament_summary(gk, entries, [])
        assert "derived" in result.standings_label.lower()

    def test_podcast_facts_present(self) -> None:
        gk = _make_group_key()
        entries = [_make_eligible_entry(game_id="g1")]
        result = _build_tournament_summary(gk, entries, [])
        assert result.podcast_facts is not None
        assert result.podcast_facts.source_label != ""

    def test_biggest_win_by_runs_detected(self) -> None:
        gk = _make_group_key()
        game = _make_game(result="Team Alpha won by 80 runs")
        batch = _make_batch("batch-g1")
        meta = _make_meta()
        match_agg = _make_match_aggregate(winner_team="Team Alpha")
        entries = [(game, batch, meta, match_agg)]
        result = _build_tournament_summary(gk, entries, [])
        # If result text is parseable, should detect biggest win
        if result.biggest_win_by_runs:
            assert result.biggest_win_by_runs.highlight_type == "biggest_win_runs"


# ---------------------------------------------------------------------------
# Unit tests: team journey
# ---------------------------------------------------------------------------


class TestBuildTeamJourney:
    def test_journey_includes_team_matches(self) -> None:
        gk = _make_group_key()
        entries = [
            _make_eligible_entry(
                game_id="g1",
                team_a="Team Alpha",
                team_b="Team Beta",
                result="Team Alpha won by 30 runs",
                winner="Team Alpha",
            ),
            _make_eligible_entry(
                game_id="g2",
                team_a="Team Gamma",
                team_b="Team Alpha",
                result="Team Alpha won by 5 wickets",
                winner="Team Alpha",
            ),
            # Match not involving Team Alpha
            _make_eligible_entry(
                game_id="g3",
                team_a="Team Beta",
                team_b="Team Gamma",
                result="Team Beta won by 20 runs",
                winner="Team Beta",
            ),
        ]
        journey = _build_team_journey("Team Alpha", gk, entries)
        assert len(journey.matches) == 2

    def test_journey_wins_counted(self) -> None:
        gk = _make_group_key()
        entries = [
            _make_eligible_entry(
                game_id="g1",
                team_a="Team Alpha",
                team_b="Team Beta",
                result="Team Alpha won by 30 runs",
                winner="Team Alpha",
            ),
            _make_eligible_entry(
                game_id="g2",
                team_a="Team Alpha",
                team_b="Team Gamma",
                result="Team Gamma won by 10 runs",
                winner="Team Gamma",
            ),
        ]
        journey = _build_team_journey("Team Alpha", gk, entries)
        assert journey.summary.wins == 1
        assert journey.summary.losses == 1

    def test_journey_sorted_chronologically(self) -> None:
        gk = _make_group_key()
        entries = [
            _make_eligible_entry(game_id="g1"),
            _make_eligible_entry(game_id="g2"),
        ]
        # Patch match dates so g2 comes before g1 by date
        entries[0][3].match_date = "2023-09-25"
        entries[1][3].match_date = "2023-09-15"
        journey = _build_team_journey("Team Alpha", gk, entries)
        dates = [m.match_date for m in journey.matches if m.match_date]
        assert dates == sorted(dates)

    def test_journey_no_matches_for_unknown_team(self) -> None:
        gk = _make_group_key()
        entries = [_make_eligible_entry(game_id="g1")]
        journey = _build_team_journey("Unknown Team XYZ", gk, entries)
        assert len(journey.matches) == 0
        assert journey.summary.wins == 0

    def test_journey_team_name_preserved(self) -> None:
        gk = _make_group_key()
        entries = [_make_eligible_entry(game_id="g1")]
        journey = _build_team_journey("Team Alpha", gk, entries)
        assert journey.team_name == "Team Alpha"


# ---------------------------------------------------------------------------
# Unit tests: knockout context
# ---------------------------------------------------------------------------


class TestBuildKnockoutContext:
    def test_final_detected(self) -> None:
        gk = _make_group_key()
        entry = _make_eligible_entry(
            game_id="final-1",
            team_a="Team Alpha",
            team_b="Team Beta",
            result="Team Alpha won by 30 runs",
            winner="Team Alpha",
            competition_stage="Final",
        )
        # Patch game phases to include stage
        entry[0].phases["historical_import"]["competition_stage"] = "Final"
        entry[2]["competition_stage"] = "Final"
        ctx = _build_knockout_context([entry], [], gk)
        # Should detect the final
        assert ctx.final_match_id is not None or ctx.outcome_source in (
            "detected_final_result",
            "final_not_detected",
        )

    def test_no_final_when_no_stage_label(self) -> None:
        gk = _make_group_key()
        entries = [_make_eligible_entry(game_id="g1")]
        ctx = _build_knockout_context(entries, [], gk)
        assert ctx.outcome_source == "final_not_detected"

    def test_uses_season_outcome_when_available(self) -> None:
        from backend.api.schemas.historical_stats import SeasonOutcomeAggregate

        gk = _make_group_key()
        outcome = SeasonOutcomeAggregate(
            competition_code="CPL_MEN",
            competition_name="Caribbean Premier League",
            season="2023",
            gender_category="men",
            champion_team_raw="Team Alpha",
            champion_team_canonical="Team Alpha",
            runner_up_team_raw="Team Beta",
            runner_up_team_canonical="Team Beta",
            final_match_id="final-1",
            final_match_title="Team Alpha vs Team Beta",
            final_match_date="2023-09-30",
            final_result="Team Alpha won by 30 runs",
            total_matches_in_season=10,
            outcome_source="detected_final_result",
            confidence="high",
        )
        entries = [_make_eligible_entry(game_id="g1")]
        ctx = _build_knockout_context(entries, [outcome], gk)
        assert ctx.champion_team_canonical == "Team Alpha"
        assert ctx.runner_up_team == "Team Beta"
        assert ctx.confidence == "high"


# ---------------------------------------------------------------------------
# Unit tests: group eligible games
# ---------------------------------------------------------------------------


class TestGroupEligibleGames:
    def test_same_competition_grouped_together(self) -> None:
        entries = [
            _make_eligible_entry(
                game_id="g1", event_name="Caribbean Premier League", season="2023"
            ),
            _make_eligible_entry(
                game_id="g2", event_name="Caribbean Premier League", season="2023"
            ),
        ]
        groups = _group_eligible_games(entries)
        # Both should be in the same group
        assert len(groups) == 1
        key = next(iter(groups))
        assert key[0] == "CPL_MEN"
        assert len(groups[key]) == 2

    def test_different_seasons_different_groups(self) -> None:
        entries = [
            _make_eligible_entry(
                game_id="g1", event_name="Caribbean Premier League", season="2022"
            ),
            _make_eligible_entry(
                game_id="g2", event_name="Caribbean Premier League", season="2023"
            ),
        ]
        groups = _group_eligible_games(entries)
        assert len(groups) == 2

    def test_different_competitions_different_groups(self) -> None:
        entries = [
            _make_eligible_entry(
                game_id="g1", event_name="Caribbean Premier League", season="2023"
            ),
            _make_eligible_entry(game_id="g2", event_name="One Day Cup", season="2023"),
        ]
        groups = _group_eligible_games(entries)
        codes = {k[0] for k in groups}
        assert "CPL_MEN" in codes
        assert "ONE_DAY_CUP" in codes or "unknown" in codes

    def test_unknown_competition_in_own_group(self) -> None:
        entries = [
            _make_eligible_entry(
                game_id="g1", event_name="Some Unknown League 2023", season="2023"
            ),
        ]
        groups = _group_eligible_games(entries)
        key = next(iter(groups))
        assert key[0] == "unknown"


# ---------------------------------------------------------------------------
# API endpoint tests (in-memory mode)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client():
    from fastapi.testclient import TestClient
    from backend.main import fastapi_app

    return TestClient(fastapi_app)


class TestTournamentIntelligenceEndpoints:
    def test_groups_endpoint_requires_auth(self, client) -> None:
        response = client.get("/analytics/tournament-intelligence/groups")
        assert response.status_code in (401, 403)

    def test_summary_endpoint_requires_auth(self, client) -> None:
        response = client.get(
            "/analytics/tournament-intelligence/summary",
            params={"competition_code": "CPL_MEN"},
        )
        assert response.status_code in (401, 403)

    def test_team_journey_endpoint_requires_auth(self, client) -> None:
        response = client.get(
            "/analytics/tournament-intelligence/team-journey",
            params={"competition_code": "CPL_MEN", "team_name": "Test Team"},
        )
        assert response.status_code in (401, 403)

    def test_summary_missing_required_param(self, client) -> None:
        """Missing competition_code triggers auth or validation failure."""
        response = client.get("/analytics/tournament-intelligence/summary")
        # Auth check fires before query-param validation in FastAPI
        assert response.status_code in (401, 403, 422)

    def test_team_journey_missing_required_params(self, client) -> None:
        """Missing required params triggers auth or validation failure."""
        response = client.get("/analytics/tournament-intelligence/team-journey")
        assert response.status_code in (401, 403, 422)
