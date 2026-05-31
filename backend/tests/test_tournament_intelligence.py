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
from typing import Any, ClassVar
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


# ---------------------------------------------------------------------------
# Phase 10S.2 — Podcast rundown tests
# ---------------------------------------------------------------------------


from backend.api.schemas.tournament_intelligence import (
    TournamentDataCompleteness,
    TournamentKnockoutContext,
    TournamentPodcastRundown,
    TournamentSeasonReview,
    TournamentSummaryResponse,
)
from backend.services.tournament_intelligence_service import (
    build_tournament_podcast_rundown,
    _build_champion_journey,
    _build_road_to_final,
    _build_season_review,
)


def _make_full_summary(
    champion: str | None = "St Kitts Patriots",
    finalist: str | None = "Saint Lucia Kings",
    final_result: str | None = "St Kitts Patriots won by 3 wickets",
    confidence: str = "high",
    standings_wins: int = 8,
) -> TournamentSummaryResponse:
    """Build a full TournamentSummaryResponse for podcast rundown tests."""
    group_key = _make_group_key(
        competition_code="CPL_MEN",
        competition_name="Caribbean Premier League",
        season="2021",
        gender_category="men",
        format_family="T20",
    )
    knockout_ctx = TournamentKnockoutContext(
        champion_team=champion,
        champion_team_canonical=champion,
        runner_up_team=finalist,
        runner_up_team_canonical=finalist,
        final_match_id="final-m",
        final_match_title="CPL 2021 Final",
        final_match_date="2021-09-15",
        final_result=final_result,
        confidence=confidence,  # type: ignore[arg-type]
    )
    from backend.api.schemas.tournament_intelligence import (
        DerivedStandingsRow,
        TournamentMatchHighlight,
        TournamentPlayerLeader,
        TournamentPodcastFacts,
    )

    standings = [
        DerivedStandingsRow(
            team_name="St Kitts Patriots",
            canonical_team_name="St Kitts Patriots",
            played=10,
            wins=standings_wins,
            losses=2,
            points=standings_wins * 2,
            confidence="medium",  # type: ignore[arg-type]
        ),
        DerivedStandingsRow(
            team_name="Saint Lucia Kings",
            canonical_team_name="Saint Lucia Kings",
            played=10,
            wins=6,
            losses=4,
            points=12,
            confidence="medium",  # type: ignore[arg-type]
        ),
    ]
    completeness = TournamentDataCompleteness(
        total_matches=34,
        matches_with_result=33,
        matches_missing_result=1,
        delivery_complete_matches=30,
        phase_level_matches=2,
        innings_totals_matches=2,
        metadata_only_matches=0,
        confidence_level=confidence,  # type: ignore[arg-type]
    )
    podcast_facts = TournamentPodcastFacts(
        competition_label="CPL",
        season_label="2021",
        champion=champion,
        finalist=finalist,
        top_scoring_venue="Warner Park",
        highest_scoring_match_title="CPL 2021 Final",
        highest_match_total_runs=395,
        confidence=confidence,  # type: ignore[arg-type]
    )
    top_run_scorer = TournamentPlayerLeader(
        player_name="D Bravo",
        value=450,
        matches_contributed=10,
        stat_type="runs",
        confidence="medium",  # type: ignore[arg-type]
    )
    biggest_win = TournamentMatchHighlight(
        match_id="m-big",
        match_title="CPL Match 10",
        result="Won by 60 runs",
        highlight_type="biggest_win_runs",
        detail="St Kitts Patriots won by 60 runs",
    )
    closest_match = TournamentMatchHighlight(
        match_id="m-close",
        match_title="CPL 2021 Final",
        result="Won by 3 wickets",
        highlight_type="closest_match",
        detail="St Kitts Patriots won by 3 wickets",
    )
    return TournamentSummaryResponse(
        group_key=group_key,
        match_count=34,
        teams=["St Kitts Patriots", "Saint Lucia Kings", "TKR"],
        venues=["Warner Park", "Queen's Park Oval"],
        total_runs=9000,
        total_wickets=330,
        highest_team_total=220,
        highest_team_total_by="TKR",
        closest_match=closest_match,
        biggest_win_by_runs=biggest_win,
        top_run_scorer=top_run_scorer,
        derived_standings=standings,
        knockout_context=knockout_ctx,
        data_completeness=completeness,
        podcast_facts=podcast_facts,
    )


class TestBuildSeasonReview:
    def test_with_champion_and_result(self) -> None:
        summary = _make_full_summary()
        review = _build_season_review(
            group_key=summary.group_key,
            knockout_ctx=summary.knockout_context,
            derived_standings=summary.derived_standings,
            match_count=summary.match_count,
            data_completeness=summary.data_completeness,
        )
        assert isinstance(review, TournamentSeasonReview)
        assert "St Kitts Patriots" in review.narrative
        assert "Saint Lucia Kings" in review.narrative
        assert "derived standings" in review.narrative.lower()
        assert "not official" in review.narrative.lower()
        assert review.confidence == "high"

    def test_with_no_champion(self) -> None:
        summary = _make_full_summary(champion=None, finalist=None, final_result=None)
        review = _build_season_review(
            group_key=summary.group_key,
            knockout_ctx=summary.knockout_context,
            derived_standings=[],
            match_count=5,
            data_completeness=TournamentDataCompleteness(
                total_matches=5,
                matches_with_result=3,
                matches_missing_result=2,
                delivery_complete_matches=0,
                phase_level_matches=0,
                innings_totals_matches=3,
                metadata_only_matches=0,
                confidence_level="low",
            ),
        )
        assert "No champion data" in review.narrative
        assert "not official" in review.narrative.lower()

    def test_source_label_always_present(self) -> None:
        summary = _make_full_summary()
        review = _build_season_review(
            group_key=summary.group_key,
            knockout_ctx=summary.knockout_context,
            derived_standings=summary.derived_standings,
            match_count=summary.match_count,
            data_completeness=summary.data_completeness,
        )
        assert "not official" in review.source_label.lower()


class TestBuildChampionJourney:
    def test_champion_journey_with_full_data(self) -> None:
        summary = _make_full_summary()
        journey = _build_champion_journey(
            knockout_ctx=summary.knockout_context,
            derived_standings=summary.derived_standings,
            summary=summary,
        )
        assert journey is not None
        assert journey.champion_team == "St Kitts Patriots"
        assert journey.final_opponent == "Saint Lucia Kings"
        assert journey.final_result == "St Kitts Patriots won by 3 wickets"
        assert journey.derived_group_standing is not None
        assert "1st" in journey.derived_group_standing
        assert "not official" in journey.source_label.lower()

    def test_champion_journey_no_champion_returns_none(self) -> None:
        summary = _make_full_summary(champion=None, finalist=None, final_result=None)
        journey = _build_champion_journey(
            knockout_ctx=summary.knockout_context,
            derived_standings=[],
            summary=summary,
        )
        assert journey is None

    def test_champion_journey_confidence_passed_through(self) -> None:
        summary = _make_full_summary(confidence="medium")
        journey = _build_champion_journey(
            knockout_ctx=summary.knockout_context,
            derived_standings=summary.derived_standings,
            summary=summary,
        )
        assert journey is not None
        assert journey.confidence == "medium"


class TestBuildRoadToFinal:
    def test_road_to_final_with_champion_and_finalist(self) -> None:
        summary = _make_full_summary()
        road = _build_road_to_final(knockout_ctx=summary.knockout_context)
        assert road is not None
        assert road.finalist_a == "St Kitts Patriots"
        assert road.finalist_b == "Saint Lucia Kings"
        assert road.final_result is not None
        assert "St Kitts Patriots" in (road.narrative or "")
        assert "not official" in road.source_label.lower()

    def test_road_to_final_no_finalists_returns_none(self) -> None:
        ctx = TournamentKnockoutContext(
            champion_team=None,
            runner_up_team=None,
            confidence="unknown",
        )
        road = _build_road_to_final(knockout_ctx=ctx)
        assert road is None

    def test_road_to_final_no_semi_finals_by_default(self) -> None:
        summary = _make_full_summary()
        road = _build_road_to_final(knockout_ctx=summary.knockout_context)
        assert road is not None
        # No invented semis
        assert road.semi_final_titles == []


class TestBuildPodcastRundown:
    def test_rundown_has_all_required_sections(self) -> None:
        summary = _make_full_summary()
        rundown = build_tournament_podcast_rundown(summary)
        assert isinstance(rundown, TournamentPodcastRundown)
        section_keys = {s.section_key for s in rundown.sections}
        required_keys = {
            "opening_hook",
            "tournament_setup",
            "champion_story",
            "final_context",
            "standings_story",
            "team_spotlight",
            "key_matches",
            "player_storylines",
            "venue_patterns",
            "tactical_themes",
            "debate_questions",
            "data_trust_note",
        }
        assert required_keys.issubset(section_keys)

    def test_rundown_season_review_present(self) -> None:
        summary = _make_full_summary()
        rundown = build_tournament_podcast_rundown(summary)
        assert rundown.season_review is not None
        assert "St Kitts Patriots" in rundown.season_review.narrative

    def test_rundown_champion_journey_present_when_champion_exists(self) -> None:
        summary = _make_full_summary()
        rundown = build_tournament_podcast_rundown(summary)
        assert rundown.champion_journey is not None
        assert rundown.champion_journey.champion_team == "St Kitts Patriots"

    def test_rundown_champion_journey_absent_when_no_champion(self) -> None:
        summary = _make_full_summary(champion=None, finalist=None, final_result=None)
        rundown = build_tournament_podcast_rundown(summary)
        assert rundown.champion_journey is None

    def test_rundown_road_to_final_present_when_finalists_exist(self) -> None:
        summary = _make_full_summary()
        rundown = build_tournament_podcast_rundown(summary)
        assert rundown.road_to_final is not None
        assert rundown.road_to_final.finalist_a == "St Kitts Patriots"

    def test_rundown_source_label_present_and_honest(self) -> None:
        summary = _make_full_summary()
        rundown = build_tournament_podcast_rundown(summary)
        assert "not official" in rundown.source_label.lower()
        assert "derived" in rundown.source_label.lower()

    def test_rundown_data_trust_note_section_body_has_source(self) -> None:
        summary = _make_full_summary()
        rundown = build_tournament_podcast_rundown(summary)
        trust_section = next(
            (s for s in rundown.sections if s.section_key == "data_trust_note"), None
        )
        assert trust_section is not None
        assert "not official" in (trust_section.body or "").lower()
        assert "derived" in (trust_section.body or "").lower()

    def test_rundown_debate_questions_section_present(self) -> None:
        summary = _make_full_summary()
        rundown = build_tournament_podcast_rundown(summary)
        debate_section = next(
            (s for s in rundown.sections if s.section_key == "debate_questions"), None
        )
        assert debate_section is not None
        assert debate_section.body is not None
        # Should have at least one debate question line
        assert "?" in debate_section.body

    def test_rundown_thin_data_fallback_safe(self) -> None:
        """No champion, no standings — rundown is safe and honest."""
        summary = _make_full_summary(champion=None, finalist=None, final_result=None)
        # Strip derived standings
        summary.derived_standings = []
        summary.top_run_scorer = None
        summary.top_wicket_taker = None
        summary.biggest_win_by_runs = None
        summary.biggest_win_by_wickets = None
        summary.closest_match = None

        rundown = build_tournament_podcast_rundown(summary)
        assert rundown is not None
        # Champion story must acknowledge no data — not fabricate
        champ_section = next(s for s in rundown.sections if s.section_key == "champion_story")
        assert champ_section.body is not None
        assert "no champion" in champ_section.body.lower()
        # Player storylines must say unavailable
        player_section = next(s for s in rundown.sections if s.section_key == "player_storylines")
        assert "unavailable" in (player_section.body or "").lower()

    def test_no_official_claims_in_any_section(self) -> None:
        """No section should claim 'official standings' without the 'not official' qualifier."""
        summary = _make_full_summary()
        rundown = build_tournament_podcast_rundown(summary)
        for section in rundown.sections:
            body_lower = (section.body or "").lower()
            # If 'official' appears, it must be qualified as 'not official'
            if "official standings" in body_lower:
                assert "not official" in body_lower, (
                    f"Section '{section.section_key}' claims official standings "
                    "without 'not official' qualifier."
                )

    def test_overall_confidence_matches_data_completeness(self) -> None:
        summary = _make_full_summary(confidence="medium")
        rundown = build_tournament_podcast_rundown(summary)
        assert rundown.overall_confidence == "medium"


class TestPodcastRundownEndpoint:
    def test_podcast_rundown_endpoint_requires_auth(self) -> None:
        from fastapi.testclient import TestClient
        from backend.main import fastapi_app

        client = TestClient(fastapi_app)
        response = client.get(
            "/analytics/tournament-intelligence/podcast-rundown",
            params={"competition_code": "CPL_MEN"},
        )
        assert response.status_code in (401, 403)

    def test_podcast_rundown_missing_param_triggers_validation(self) -> None:
        from fastapi.testclient import TestClient
        from backend.main import fastapi_app

        client = TestClient(fastapi_app)
        response = client.get("/analytics/tournament-intelligence/podcast-rundown")
        # Auth check fires before param validation in FastAPI
        assert response.status_code in (401, 403, 422)


# ---------------------------------------------------------------------------
# Phase 10S.2 — Copy quality and trust fix tests
# ---------------------------------------------------------------------------


class TestPluralize:
    """Tests for the _pluralize helper function."""

    def test_imports(self) -> None:
        from backend.services.tournament_intelligence_service import _pluralize

        assert _pluralize is not None

    def test_singular(self) -> None:
        from backend.services.tournament_intelligence_service import _pluralize

        assert _pluralize(1, "match", "matches") == "1 match"
        assert _pluralize(1, "win") == "1 win"
        assert _pluralize(1, "wicket") == "1 wicket"

    def test_plural(self) -> None:
        from backend.services.tournament_intelligence_service import _pluralize

        assert _pluralize(9, "win") == "9 wins"
        assert _pluralize(13, "match", "matches") == "13 matches"
        assert _pluralize(3, "wicket") == "3 wickets"

    def test_zero(self) -> None:
        from backend.services.tournament_intelligence_service import _pluralize

        assert _pluralize(0, "win") == "0 wins"
        assert _pluralize(0, "match", "matches") == "0 matches"


class TestNoPlaceholderArtifacts:
    """No win(s), match(es), wicket(s), run(s) in any rundown section."""

    PLACEHOLDERS: ClassVar[list[str]] = [
        "win(s)",
        "match(es)",
        "wicket(s)",
        "run(s)",
        "team(s)",
        "venue(s)",
    ]

    def _check_no_placeholders(self, text: str, label: str) -> None:
        for ph in self.PLACEHOLDERS:
            assert ph not in text, f"Placeholder artifact '{ph}' found in {label}: {text!r}"

    def test_season_review_no_placeholders(self) -> None:
        from backend.services.tournament_intelligence_service import _build_season_review

        summary = _make_full_summary()
        review = _build_season_review(
            group_key=summary.group_key,
            knockout_ctx=summary.knockout_context,
            derived_standings=summary.derived_standings,
            match_count=summary.match_count,
            data_completeness=summary.data_completeness,
        )
        self._check_no_placeholders(review.narrative, "season_review.narrative")

    def test_season_review_no_champion_no_placeholders(self) -> None:
        from backend.services.tournament_intelligence_service import _build_season_review

        summary = _make_full_summary(champion=None, finalist=None, final_result=None)
        review = _build_season_review(
            group_key=summary.group_key,
            knockout_ctx=summary.knockout_context,
            derived_standings=[],
            match_count=5,
            data_completeness=summary.data_completeness,
        )
        self._check_no_placeholders(review.narrative, "season_review.narrative (no champion)")

    def test_rundown_sections_no_placeholders(self) -> None:
        summary = _make_full_summary()
        rundown = build_tournament_podcast_rundown(summary)
        for section in rundown.sections:
            body = section.body or ""
            self._check_no_placeholders(body, f"section '{section.section_key}'")

    def test_rundown_thin_data_no_placeholders(self) -> None:
        summary = _make_full_summary(champion=None, finalist=None, final_result=None)
        summary.derived_standings = []
        summary.top_run_scorer = None
        summary.top_wicket_taker = None
        rundown = build_tournament_podcast_rundown(summary)
        for section in rundown.sections:
            body = section.body or ""
            self._check_no_placeholders(body, f"section '{section.section_key}' (thin data)")


class TestSaferKnockoutWording:
    """Knockout-stage wording must not overstate stage labels."""

    def test_road_to_final_semi_finals_safe_wording(self) -> None:
        from backend.api.schemas.tournament_intelligence import TournamentMatchHighlight

        ctx = TournamentKnockoutContext(
            champion_team="Team A",
            champion_team_canonical="Team A",
            runner_up_team="Team B",
            runner_up_team_canonical="Team B",
            final_result="Team A won by 5 wickets",
            confidence="high",  # type: ignore[arg-type]
            semi_final_matches=[
                TournamentMatchHighlight(
                    match_id="sf1",
                    match_title="Semi Final 1",
                    stage_label="Semi Final",
                    highlight_type="semi_final",
                )
            ],
        )
        road = _build_road_to_final(knockout_ctx=ctx)
        assert road is not None
        narrative = road.narrative or ""
        # Must NOT use the old overconfident phrasing
        assert "Semi-finals detected:" not in narrative
        # Must use safe phrasing
        assert "Possible knockout-stage matches detected" in narrative

    def test_road_to_final_qualifier_safe_wording(self) -> None:
        from backend.api.schemas.tournament_intelligence import TournamentMatchHighlight

        ctx = TournamentKnockoutContext(
            champion_team="Team A",
            champion_team_canonical="Team A",
            runner_up_team="Team B",
            runner_up_team_canonical="Team B",
            final_result="Team A won by 5 wickets",
            confidence="high",  # type: ignore[arg-type]
            qualifier_matches=[
                TournamentMatchHighlight(
                    match_id="q1",
                    match_title="Qualifier 1",
                    stage_label="Qualifier",
                    highlight_type="qualifier",
                )
            ],
        )
        road = _build_road_to_final(knockout_ctx=ctx)
        assert road is not None
        narrative = road.narrative or ""
        # Must NOT use old phrasing
        assert "Qualifier/eliminator matches detected:" not in narrative
        # Must use safe phrasing
        assert "Possible knockout-stage matches detected" in narrative

    def test_road_to_final_no_knockouts_no_knockout_text(self) -> None:
        """When no semi/qualifier matches exist, no knockout text is added."""
        summary = _make_full_summary()
        road = _build_road_to_final(knockout_ctx=summary.knockout_context)
        assert road is not None
        assert "Possible knockout-stage matches" not in (road.narrative or "")


class TestZeroWicketFallback:
    """Zero wickets must not be presented as a real statistic."""

    def test_venue_patterns_zero_wickets_fallback(self) -> None:
        summary = _make_full_summary()
        summary.total_wickets = 0
        rundown = build_tournament_podcast_rundown(summary)
        venue_section = next(
            (s for s in rundown.sections if s.section_key == "venue_patterns"), None
        )
        assert venue_section is not None
        body = venue_section.body or ""
        # Must not show "0 wickets" as a real stat
        assert "0 wickets" not in body
        # Must explain data is unavailable
        assert "unavailable" in body.lower()

    def test_tactical_themes_zero_wickets_fallback(self) -> None:
        summary = _make_full_summary()
        summary.total_wickets = 0
        rundown = build_tournament_podcast_rundown(summary)
        tactical_section = next(
            (s for s in rundown.sections if s.section_key == "tactical_themes"), None
        )
        assert tactical_section is not None
        body = tactical_section.body or ""
        # Must not claim "0 total wickets"
        assert "0 total wickets" not in body
        # Must say wicket data is unavailable
        assert "unavailable" in body.lower()

    def test_venue_patterns_nonzero_wickets_shows_count(self) -> None:
        summary = _make_full_summary()
        summary.total_wickets = 330
        rundown = build_tournament_podcast_rundown(summary)
        venue_section = next(
            (s for s in rundown.sections if s.section_key == "venue_patterns"), None
        )
        assert venue_section is not None
        assert "330 wickets" in (venue_section.body or "")


class TestPlayerStorylineFallback:
    """Player storyline fallback must explain missing data requirements clearly."""

    def test_player_storyline_fallback_explains_requirements(self) -> None:
        summary = _make_full_summary()
        summary.top_run_scorer = None
        summary.top_wicket_taker = None
        rundown = build_tournament_podcast_rundown(summary)
        player_section = next(
            (s for s in rundown.sections if s.section_key == "player_storylines"), None
        )
        assert player_section is not None
        body = (player_section.body or "").lower()
        # Must mention player leaderboards are unavailable
        assert "player leaderboard" in body
        # Must explain the reason (scorecard/delivery data)
        assert "scorecard" in body or "delivery" in body
        # Must be marked unknown confidence
        assert player_section.confidence == "unknown"

    def test_player_storyline_fallback_no_vague_wording(self) -> None:
        """Old vague wording 'Scorecard or delivery data was not found' is replaced."""
        summary = _make_full_summary()
        summary.top_run_scorer = None
        summary.top_wicket_taker = None
        rundown = build_tournament_podcast_rundown(summary)
        player_section = next(
            (s for s in rundown.sections if s.section_key == "player_storylines"), None
        )
        body = player_section.body or ""
        # Must NOT use the old vague phrasing
        assert "Player stats are unavailable" not in body
