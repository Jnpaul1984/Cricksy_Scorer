"""
Tests for the match context package service.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.main import fastapi_app
from backend.sql_app import models
from backend.sql_app.database import get_db, SessionLocal


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client() -> TestClient:
    """Create a TestClient for the FastAPI app."""
    return TestClient(fastapi_app)


@pytest.fixture
def authed_client(client, analyst_pro_token) -> TestClient:
    """Create a TestClient with analyst auth header."""
    client.headers["Authorization"] = f"Bearer {analyst_pro_token}"
    return client


# ---------------------------------------------------------------------------
# Unit Tests for Helper Functions
# ---------------------------------------------------------------------------


def test_get_phase_breakdowns_empty_deliveries():
    """Test phase breakdowns with no deliveries."""
    from backend.services.match_context_service import get_phase_breakdowns

    result = get_phase_breakdowns(
        deliveries=[],
        overs_limit=20,
        batting_team="Team A",
        innings_number=1,
    )

    assert result == []


def test_get_phase_breakdowns_with_deliveries():
    """Test phase breakdowns with sample deliveries."""
    from backend.services.match_context_service import get_phase_breakdowns

    deliveries = [
        {"over_number": 0, "ball_number": 1, "runs_scored": 4, "is_wicket": False},
        {"over_number": 0, "ball_number": 2, "runs_scored": 0, "is_wicket": False},
        {"over_number": 0, "ball_number": 3, "runs_scored": 6, "is_wicket": False},
        {"over_number": 0, "ball_number": 4, "runs_scored": 1, "is_wicket": False},
        {"over_number": 0, "ball_number": 5, "runs_scored": 0, "is_wicket": True, "dismissal_type": "caught"},
        {"over_number": 0, "ball_number": 6, "runs_scored": 2, "is_wicket": False},
    ]

    result = get_phase_breakdowns(
        deliveries=deliveries,
        overs_limit=20,
        batting_team="Lions",
        innings_number=1,
    )

    assert len(result) == 1  # Only powerplay has data
    pp = result[0]
    assert pp["phase_id"] == "powerplay_1"
    assert pp["label"] == "Powerplay"
    assert pp["team"] == "Lions"
    assert pp["runs"] == 13
    assert pp["wickets"] == 1
    assert pp["balls"] == 6
    assert pp["boundaries_4"] == 1
    assert pp["boundaries_6"] == 1
    # Dot balls: ball 2 (0 runs, no wicket), ball 5 is a wicket so not a dot ball
    assert pp["dot_balls"] == 1
    assert len(pp["notable_events"]) == 3  # 4, 6, wicket


def test_summarize_player_performance_batter():
    """Test player performance summary for a batter."""
    from backend.services.match_context_service import summarize_player_performance

    batting_scorecard = {
        "runs": 45,
        "balls": 30,
        "fours": 4,
        "sixes": 2,
        "is_out": True,
        "dismissal_type": "caught",
    }

    result = summarize_player_performance(
        player_id="player_1",
        player_name="Test Batter",
        team="Lions",
        batting_scorecard=batting_scorecard,
        bowling_scorecard=None,
        deliveries=[],
        overs_limit=20,
    )

    assert result["player_id"] == "player_1"
    assert result["player_name"] == "Test Batter"
    assert result["team"] == "Lions"
    assert result["role"] == "batter"
    assert result["batting"]["runs"] == 45
    assert result["batting"]["strike_rate"] == 150.0
    assert "impact_innings" in result["tags"]  # 30+ runs at 150+ SR
    assert result["impact_score"] is not None


def test_summarize_player_performance_bowler():
    """Test player performance summary for a bowler."""
    from backend.services.match_context_service import summarize_player_performance

    bowling_scorecard = {
        "overs": 4.0,
        "runs": 24,
        "wickets": 3,
        "maidens": 0,
    }

    result = summarize_player_performance(
        player_id="player_2",
        player_name="Test Bowler",
        team="Falcons",
        batting_scorecard=None,
        bowling_scorecard=bowling_scorecard,
        deliveries=[],
        overs_limit=20,
    )

    assert result["player_id"] == "player_2"
    assert result["role"] == "bowler"
    assert result["bowling"]["wickets"] == 3
    assert result["bowling"]["economy"] == 6.0
    assert "wicket_taker" in result["tags"]


def test_generate_callouts():
    """Test callout generation from phase and player data."""
    from backend.services.match_context_service import generate_callouts, PhaseBreakdown, PlayerPerformance

    phases = [
        PhaseBreakdown(
            phase_id="powerplay_1",
            label="Powerplay",
            innings=1,
            team="Lions",
            over_range=(0.1, 6.0),
            runs=60,
            wickets=1,
            balls=36,
            run_rate=10.0,
            boundaries_4=5,
            boundaries_6=3,
            dot_balls=5,
            extras=2,
            notable_events=[],
        ),
    ]

    players = [
        PlayerPerformance(
            player_id="p1",
            player_name="Top Scorer",
            team="Lions",
            role="batter",
            batting={"runs": 55},
            bowling=None,
            fielding=None,
            impact_score=60.0,
            tags=["fifty_plus"],
        ),
    ]

    result = generate_callouts(phases, players, "Lions won by 5 wickets")

    assert len(result) >= 2  # At least explosive powerplay + key innings callouts
    callout_titles = [c["title"] for c in result]
    assert "Explosive Powerplay" in callout_titles
    assert "Key Innings" in callout_titles


# ---------------------------------------------------------------------------
# Tests for get_context_for_commentary
# ---------------------------------------------------------------------------


def test_get_context_for_commentary_first_innings():
    """Test commentary context extraction for first innings."""
    from backend.services.match_context_service import get_context_for_commentary, PhaseBreakdown, PlayerPerformance

    mcp = {
        "match_id": "test-match-1",
        "format": "T20",
        "overs_per_side": 20,
        "team_a": {"name": "Lions", "players": []},
        "team_b": {"name": "Falcons", "players": []},
        "innings": [
            {"innings_number": 1, "team": "Lions", "runs": 85, "wickets": 2, "overs": 10.3, "run_rate": 8.1}
        ],
        "phase_breakdowns": [
            PhaseBreakdown(
                phase_id="powerplay_1",
                label="Powerplay",
                innings=1,
                team="Lions",
                over_range=(0.1, 6.0),
                runs=52,
                wickets=1,
                balls=36,
                run_rate=8.67,
                boundaries_4=5,
                boundaries_6=2,
                dot_balls=8,
                extras=3,
                notable_events=[
                    {"over": 2.3, "event_type": "boundary_6", "description": "SIX"},
                    {"over": 4.1, "event_type": "wicket", "description": "WICKET (caught)"},
                ],
            ),
            PhaseBreakdown(
                phase_id="middle_1",
                label="Middle Overs",
                innings=1,
                team="Lions",
                over_range=(6.1, 15.0),
                runs=33,
                wickets=1,
                balls=27,
                run_rate=7.33,
                boundaries_4=3,
                boundaries_6=1,
                dot_balls=6,
                extras=1,
                notable_events=[
                    {"over": 9.5, "event_type": "boundary_4", "description": "FOUR"},
                    {"over": 10.2, "event_type": "boundary_6", "description": "SIX"},
                ],
            ),
        ],
        "player_performances": [
            PlayerPerformance(
                player_id="p1",
                player_name="J Smith",
                team="Lions",
                role="batter",
                batting={"runs": 45, "balls_faced": 32, "strike_rate": 140.6},
                bowling=None,
                impact_score=50.0,
                tags=["impact_innings"],
            ),
            PlayerPerformance(
                player_id="p2",
                player_name="R Kumar",
                team="Lions",
                role="batter",
                batting={"runs": 28, "balls_faced": 25, "strike_rate": 112.0},
                bowling=None,
                impact_score=30.0,
                tags=[],
            ),
        ],
        "callouts": [],
    }

    result = get_context_for_commentary(mcp)

    # Check basic fields
    assert result["match_id"] == "test-match-1"
    assert result["format"] == "T20"
    assert result["batting_team"] == "Lions"
    assert result["bowling_team"] == "Falcons"
    assert result["score"] == "85/2 in 10.3 overs"
    assert result["run_rate"] == 8.1

    # First innings - no chase context
    assert result["target"] is None
    assert result["required_rate"] is None
    assert result["runs_needed"] is None

    # Current phase is middle (overs 10.3)
    assert result["current_phase"] == "middle"
    assert "Middle Overs" in result["phase_summary"]

    # Recent events (last 2 overs from 10.3 = 8.3+)
    assert len(result["recent_events"]) >= 1

    # Top performers
    assert len(result["top_performers"]) == 2
    assert result["top_performers"][0]["name"] == "J Smith"

    # Situation summary
    assert len(result["situation_summary"]) > 0


def test_get_context_for_commentary_chase():
    """Test commentary context extraction during a chase."""
    from backend.services.match_context_service import get_context_for_commentary

    mcp = {
        "match_id": "test-match-2",
        "format": "T20",
        "overs_per_side": 20,
        "team_a": {"name": "Lions", "players": []},
        "team_b": {"name": "Falcons", "players": []},
        "innings": [
            {"innings_number": 1, "team": "Lions", "runs": 165, "wickets": 6, "overs": 20.0, "run_rate": 8.25},
            {"innings_number": 2, "team": "Falcons", "runs": 120, "wickets": 4, "overs": 15.0, "run_rate": 8.0},
        ],
        "phase_breakdowns": [],
        "player_performances": [],
        "callouts": [],
    }

    result = get_context_for_commentary(mcp)

    # Chase context
    assert result["batting_team"] == "Falcons"
    assert result["bowling_team"] == "Lions"
    assert result["target"] == 166  # 165 + 1
    assert result["runs_needed"] == 46  # 166 - 120
    assert result["required_rate"] is not None
    assert result["balls_remaining"] == 30  # 5 overs * 6

    # Current phase is death (overs 15.0)
    assert result["current_phase"] == "death"


def test_get_context_for_commentary_empty_mcp():
    """Test handling of minimal/empty MCP."""
    from backend.services.match_context_service import get_context_for_commentary

    mcp = {
        "match_id": "empty-match",
        "format": "T20",
        "overs_per_side": 20,
        "team_a": {"name": "Team A"},
        "team_b": {"name": "Team B"},
        "innings": [],
        "phase_breakdowns": [],
        "player_performances": [],
        "callouts": [],
    }

    result = get_context_for_commentary(mcp)

    assert result["match_id"] == "empty-match"
    assert result["score"] == "0/0 in 0.0 overs"
    assert result["current_phase"] == "powerplay"
    assert result["top_performers"] == []
    assert len(result["situation_summary"]) > 0


def test_get_context_for_commentary_size():
    """Test that output is reasonably small for LLM use."""
    import json
    from backend.services.match_context_service import get_context_for_commentary, PhaseBreakdown, PlayerPerformance

    # Create a somewhat populated MCP
    mcp = {
        "match_id": "size-test",
        "format": "T20",
        "overs_per_side": 20,
        "team_a": {"name": "Lions", "players": [{"id": f"p{i}", "name": f"Player {i}"} for i in range(11)]},
        "team_b": {"name": "Falcons", "players": [{"id": f"q{i}", "name": f"Player {i}"} for i in range(11)]},
        "innings": [
            {"innings_number": 1, "team": "Lions", "runs": 175, "wickets": 5, "overs": 20.0, "run_rate": 8.75},
            {"innings_number": 2, "team": "Falcons", "runs": 140, "wickets": 6, "overs": 17.2, "run_rate": 8.08},
        ],
        "phase_breakdowns": [
            PhaseBreakdown(
                phase_id=f"{phase}_{inn}",
                label=phase.title(),
                innings=inn,
                team="Lions" if inn == 1 else "Falcons",
                over_range=(0.1, 6.0),
                runs=50,
                wickets=1,
                balls=36,
                run_rate=8.33,
                boundaries_4=4,
                boundaries_6=2,
                dot_balls=8,
                extras=2,
                notable_events=[{"over": i + 0.5, "event_type": "boundary_4", "description": "FOUR"} for i in range(10)],
            )
            for phase in ["powerplay", "middle", "death"]
            for inn in [1, 2]
        ],
        "player_performances": [
            PlayerPerformance(
                player_id=f"player_{i}",
                player_name=f"Player {i}",
                team="Lions" if i < 6 else "Falcons",
                role="batter" if i % 2 == 0 else "bowler",
                batting={"runs": 30 - i, "balls_faced": 20, "strike_rate": 150.0} if i % 2 == 0 else None,
                bowling={"wickets": 2, "runs_conceded": 25, "overs": 4} if i % 2 == 1 else None,
                impact_score=50.0 - i * 5,
                tags=["test_tag"],
            )
            for i in range(10)
        ],
        "callouts": [{"id": f"callout_{i}", "title": f"Callout {i}", "body": "Test body"} for i in range(5)],
    }

    result = get_context_for_commentary(mcp)

    # Serialize to JSON and check size
    json_str = json.dumps(result)
    char_count = len(json_str)

    # Rough estimate: 4 chars per token, target <3k tokens = <12k chars
    assert char_count < 12000, f"Output too large: {char_count} chars (~{char_count // 4} tokens)"

    # Verify stripping worked
    assert len(result["top_performers"]) <= 3
    assert len(result["recent_events"]) <= 6
    assert "players" not in str(result)  # No full player lists


# ---------------------------------------------------------------------------
# Integration Tests (API Endpoint)
# ---------------------------------------------------------------------------


def test_context_package_endpoint_not_found(authed_client, _setup_db):
    """Test 404 for non-existent match."""
    response = authed_client.get("/api/analyst/matches/nonexistent/context-package")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_context_package_endpoint_success(_setup_db):
    """Test successful context package generation."""
    from backend.sql_app.database import SessionLocal

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    # Create user and game
    email = "ctx_analyst@test.com"
    password = "secret123"

    with TestClient(fastapi_app) as client:
        client.session_maker = SessionLocal  # type: ignore[attr-defined]

        # Register user
        resp = client.post("/auth/register", json={"email": email, "password": password})
        assert resp.status_code == 201, resp.text

        # Login to get token
        resp = client.post(
            "/auth/login",
            data={"username": email, "password": password},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        assert resp.status_code == 200, resp.text
        token = resp.json()["access_token"]

        # Set role to analyst_pro
        async with SessionLocal() as session:
            from sqlalchemy import select

            result = await session.execute(select(models.User).where(models.User.email == email))
            user = result.scalar_one()
            user.role = models.RoleEnum.analyst_pro
            await session.commit()

        # Re-login after role change
        resp = client.post(
            "/auth/login",
            data={"username": email, "password": password},
            headers={"content-type": "application/x-www-form-urlencoded"},
        )
        token = resp.json()["access_token"]

        # Create test game
        async with SessionLocal() as session:
            game = models.Game(
                id="test-ctx-game-1",
                team_a={"name": "Lions", "players": [{"id": "p1", "name": "Player One"}]},
                team_b={"name": "Falcons", "players": [{"id": "p2", "name": "Player Two"}]},
                match_type="T20",
                overs_limit=20,
                toss_winner_team="Lions",
                decision="bat",
                batting_team_name="Lions",
                bowling_team_name="Falcons",
                deliveries=[
                    {"over_number": 0, "ball_number": 1, "runs_scored": 4, "striker_id": "p1", "is_wicket": False},
                    {"over_number": 0, "ball_number": 2, "runs_scored": 6, "striker_id": "p1", "is_wicket": False},
                ],
                batting_scorecard={"p1": {"runs": 10, "balls": 2, "fours": 1, "sixes": 1, "is_out": False}},
                bowling_scorecard={},
            )
            session.add(game)
            await session.commit()

        response = client.get(
            "/api/analyst/matches/test-ctx-game-1/context-package",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200, response.text

        data = response.json()
        assert data["match_id"] == "test-ctx-game-1"
        assert data["format"] == "T20"
        assert data["team_a"]["name"] == "Lions"
        assert data["team_b"]["name"] == "Falcons"
        assert data["toss"]["winner"] == "Lions"
        assert len(data["phase_breakdowns"]) > 0
        assert len(data["player_performances"]) > 0

    fastapi_app.dependency_overrides.pop(get_db, None)


def test_context_package_requires_auth(client, _setup_db):
    """Test that endpoint requires authentication."""
    # No auth header
    response = client.get("/api/analyst/matches/some-id/context-package")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Tests for get_context_for_case_study and summarize_phase_for_case_study
# ---------------------------------------------------------------------------


def test_summarize_phase_for_case_study_explosive_powerplay():
    """Test phase summarization for explosive powerplay."""
    from backend.services.match_context_service import summarize_phase_for_case_study, PhaseBreakdown

    phase = PhaseBreakdown(
        phase_id="powerplay_1",
        label="Powerplay",
        innings=1,
        team="Lions",
        over_range=(0.1, 6.0),
        runs=58,
        wickets=0,
        balls=36,
        run_rate=9.67,
        boundaries_4=6,
        boundaries_6=3,
        dot_balls=5,
        extras=2,
        notable_events=[
            {"over": 1.3, "event_type": "boundary_6", "description": "SIX"},
            {"over": 3.5, "event_type": "boundary_4", "description": "FOUR"},
        ],
    )

    # summarize_phase_for_case_study returns a plain string narrative
    result = summarize_phase_for_case_study(phase)

    # Check it's a non-trivial string
    assert isinstance(result, str)
    assert len(result) > 20

    # Should mention the explosive powerplay
    assert "58" in result or "dominated" in result.lower() or "powerplay" in result.lower()
    # Should mention sixes for power hitting
    assert "sixes" in result.lower() or "3" in result


def test_summarize_phase_for_case_study_collapse():
    """Test phase summarization for a middle-overs collapse."""
    from backend.services.match_context_service import summarize_phase_for_case_study, PhaseBreakdown

    phase = PhaseBreakdown(
        phase_id="middle_2",
        label="Middle Overs",
        innings=2,
        team="Falcons",
        over_range=(6.1, 15.0),
        runs=38,
        wickets=5,
        balls=54,
        run_rate=4.22,
        boundaries_4=2,
        boundaries_6=0,
        dot_balls=28,
        extras=1,
        notable_events=[
            {"over": 8.2, "event_type": "wicket", "description": "WICKET (bowled)"},
            {"over": 10.1, "event_type": "wicket", "description": "WICKET (lbw)"},
            {"over": 11.4, "event_type": "wicket", "description": "WICKET (caught)"},
        ],
    )

    result = summarize_phase_for_case_study(phase)

    # Check it's a string and picks up on wickets
    assert isinstance(result, str)
    assert "5" in result or "wicket" in result.lower() or "lost" in result.lower()


def test_summarize_phase_for_case_study_death_overs():
    """Test phase summarization for death overs acceleration."""
    from backend.services.match_context_service import summarize_phase_for_case_study, PhaseBreakdown

    phase = PhaseBreakdown(
        phase_id="death_1",
        label="Death Overs",
        innings=1,
        team="Lions",
        over_range=(15.1, 20.0),
        runs=72,
        wickets=3,
        balls=30,
        run_rate=14.4,
        boundaries_4=5,
        boundaries_6=5,
        dot_balls=4,
        extras=3,
        notable_events=[],
    )

    result = summarize_phase_for_case_study(phase)

    # High run rate should be captured
    assert isinstance(result, str)
    assert "72" in result or "14" in result or "death" in result.lower() or "strong" in result.lower()
    # Should mention sixes
    assert "sixes" in result.lower() or "5" in result


def test_get_context_for_case_study_full_mcp():
    """Test case study context extraction from full MCP."""
    from backend.services.match_context_service import (
        get_context_for_case_study,
        PhaseBreakdown,
        PlayerPerformance,
    )

    mcp = {
        "match_id": "case-study-match",
        "format": "T20",
        "overs_per_side": 20,
        "team_a": {"name": "Lions", "players": [{"id": f"p{i}", "name": f"Lion {i}"} for i in range(11)]},
        "team_b": {"name": "Falcons", "players": [{"id": f"q{i}", "name": f"Falcon {i}"} for i in range(11)]},
        "toss": {"winner": "Lions", "decision": "bat"},
        "venue": "Test Stadium",
        "result": "Lions won by 25 runs",
        "innings": [
            {"innings_number": 1, "team": "Lions", "runs": 185, "wickets": 6, "overs": 20.0, "run_rate": 9.25},
            {"innings_number": 2, "team": "Falcons", "runs": 160, "wickets": 8, "overs": 20.0, "run_rate": 8.0},
        ],
        "phase_breakdowns": [
            PhaseBreakdown(
                phase_id="powerplay_1",
                label="Powerplay",
                innings=1,
                team="Lions",
                over_range=(0.1, 6.0),
                runs=52,
                wickets=1,
                balls=36,
                run_rate=8.67,
                boundaries_4=5,
                boundaries_6=2,
                dot_balls=8,
                extras=3,
                notable_events=[],
            ),
            PhaseBreakdown(
                phase_id="middle_1",
                label="Middle Overs",
                innings=1,
                team="Lions",
                over_range=(6.1, 15.0),
                runs=68,
                wickets=2,
                balls=54,
                run_rate=7.56,
                boundaries_4=6,
                boundaries_6=2,
                dot_balls=12,
                extras=2,
                notable_events=[],
            ),
            PhaseBreakdown(
                phase_id="death_1",
                label="Death Overs",
                innings=1,
                team="Lions",
                over_range=(15.1, 20.0),
                runs=65,
                wickets=3,
                balls=30,
                run_rate=13.0,
                boundaries_4=4,
                boundaries_6=4,
                dot_balls=4,
                extras=1,
                notable_events=[],
            ),
        ],
        "player_performances": [
            PlayerPerformance(
                player_id="p1",
                player_name="Top Scorer",
                team="Lions",
                role="batter",
                batting={"runs": 72, "balls_faced": 48, "strike_rate": 150.0, "fours": 6, "sixes": 3},
                bowling=None,
                impact_score=75.0,
                tags=["fifty_plus", "impact_innings"],
            ),
            PlayerPerformance(
                player_id="q5",
                player_name="Best Bowler",
                team="Falcons",
                role="bowler",
                batting=None,
                bowling={"wickets": 3, "runs_conceded": 28, "overs": 4, "economy": 7.0},
                impact_score=45.0,
                tags=["wicket_taker"],
            ),
        ],
        "callouts": [
            {"id": "c1", "title": "Key Partnership", "body": "50-run stand", "severity": "info"},
            {"id": "c2", "title": "Turning Point", "body": "Quick wickets", "severity": "warning"},
        ],
    }

    result = get_context_for_case_study(mcp)

    # Check basic structure
    assert result["match_id"] == "case-study-match"
    assert result["format"] == "T20"
    assert result["result"] == "Lions won by 25 runs"
    assert result["venue"] == "Test Stadium"

    # Check innings
    assert len(result["innings"]) == 2
    assert result["innings"][0]["team"] == "Lions"
    assert result["innings"][0]["runs"] == 185

    # Check phases have narratives (not "summary")
    assert len(result["phases"]) == 3
    for phase in result["phases"]:
        assert "narrative" in phase
        assert len(phase["narrative"]) > 0

    # Check players have narratives
    assert len(result["players"]) == 2
    for player in result["players"]:
        assert "narrative" in player
        assert player["player_name"] in ["Top Scorer", "Best Bowler"]

    # Check callouts preserved
    assert len(result["callouts"]) == 2

    # Check match-level fields exist
    assert "match_tags" in result
    assert "match_narrative" in result
    assert len(result["match_narrative"]) > 0


def test_get_context_for_case_study_size():
    """Test that case study context stays within ~8k tokens."""
    import json
    from backend.services.match_context_service import (
        get_context_for_case_study,
        PhaseBreakdown,
        PlayerPerformance,
    )

    # Create a large MCP with many phases and players
    phases = []
    for inn in [1, 2]:
        for phase, label in [("powerplay", "Powerplay"), ("middle", "Middle Overs"), ("death", "Death Overs")]:
            phases.append(
                PhaseBreakdown(
                    phase_id=f"{phase}_{inn}",
                    label=label,
                    innings=inn,
                    team="Lions" if inn == 1 else "Falcons",
                    over_range=(0.1, 6.0),
                    runs=55,
                    wickets=2,
                    balls=36,
                    run_rate=9.17,
                    boundaries_4=5,
                    boundaries_6=2,
                    dot_balls=8,
                    extras=2,
                    notable_events=[
                        {"over": i + 0.3, "event_type": "boundary_4", "description": "FOUR"}
                        for i in range(15)  # Many events
                    ],
                )
            )

    players = [
        PlayerPerformance(
            player_id=f"player_{i}",
            player_name=f"Player {i}",
            team="Lions" if i < 11 else "Falcons",
            role="batter" if i % 3 == 0 else ("bowler" if i % 3 == 1 else "all_rounder"),
            batting={"runs": 40 - i, "balls_faced": 30, "strike_rate": 133.3, "fours": 3, "sixes": 1},
            bowling={"wickets": 2, "runs_conceded": 28, "overs": 4, "economy": 7.0} if i % 2 == 1 else None,
            impact_score=60.0 - i * 2,
            tags=["impact_innings"] if i < 5 else [],
        )
        for i in range(22)  # All 22 players
    ]

    mcp = {
        "match_id": "large-case-study",
        "format": "T20",
        "overs_per_side": 20,
        "team_a": {"name": "Lions", "players": [{"id": f"p{i}", "name": f"Lion {i}"} for i in range(11)]},
        "team_b": {"name": "Falcons", "players": [{"id": f"q{i}", "name": f"Falcon {i}"} for i in range(11)]},
        "toss": {"winner": "Lions", "decision": "bat"},
        "venue": "Test Stadium",
        "result": "Lions won by 15 runs",
        "innings": [
            {"innings_number": 1, "team": "Lions", "runs": 185, "wickets": 6, "overs": 20.0, "run_rate": 9.25},
            {"innings_number": 2, "team": "Falcons", "runs": 170, "wickets": 8, "overs": 20.0, "run_rate": 8.5},
        ],
        "phase_breakdowns": phases,
        "player_performances": players,
        "callouts": [{"id": f"c{i}", "title": f"Callout {i}", "body": "Description", "severity": "info"} for i in range(10)],
    }

    result = get_context_for_case_study(mcp)

    # Serialize to JSON and check size
    json_str = json.dumps(result)
    char_count = len(json_str)

    # ~8k tokens = ~32k chars (4 chars per token estimate)
    assert char_count < 32000, f"Output too large: {char_count} chars (~{char_count // 4} tokens)"

    # Verify structure is preserved
    assert len(result["innings"]) == 2
    assert len(result["phases"]) == 6  # All phases
    # All players included
    assert len(result["players"]) == 22


def test_get_context_for_case_study_empty_mcp():
    """Test handling of minimal MCP for case study."""
    from backend.services.match_context_service import get_context_for_case_study

    mcp = {
        "match_id": "empty-case-study",
        "format": "ODI",
        "overs_per_side": 50,
        "team_a": {"name": "Team A", "players": []},
        "team_b": {"name": "Team B", "players": []},
        "innings": [],
        "phase_breakdowns": [],
        "player_performances": [],
        "callouts": [],
    }

    result = get_context_for_case_study(mcp)

    assert result["match_id"] == "empty-case-study"
    assert result["format"] == "ODI"
    assert result["innings"] == []
    assert result["phases"] == []
    assert result["players"] == []
    assert result["callouts"] == []
    # Match-level fields always present
    assert "match_tags" in result
    assert "match_narrative" in result


# ---------------------------------------------------------------------------
# Tests for get_context_for_player_profile
# ---------------------------------------------------------------------------


def test_get_context_for_player_profile_batter():
    """Test player profile extraction for a batter."""
    from backend.services.match_context_service import get_context_for_player_profile, PlayerPerformance

    mcp = {
        "match_id": "player-profile-test",
        "format": "T20",
        "overs_per_side": 20,
        "venue": "Test Stadium",
        "result": "Lions won by 5 wickets",
        "team_a": {"name": "Lions", "players": [{"id": "p1", "name": "Star Batter"}]},
        "team_b": {"name": "Falcons", "players": []},
        "innings": [],
        "phase_breakdowns": [],
        "player_performances": [
            PlayerPerformance(
                player_id="p1",
                player_name="Star Batter",
                team="Lions",
                role="batter",
                batting={
                    "runs": 72,
                    "balls_faced": 48,
                    "fours": 6,
                    "sixes": 3,
                    "strike_rate": 150.0,
                    "is_out": False,
                },
                bowling=None,
                impact_score=75.0,
                tags=["fifty_plus", "match_winner"],
            ),
        ],
        "callouts": [],
    }

    result = get_context_for_player_profile(mcp, "p1")

    assert result is not None
    assert result["player_id"] == "p1"
    assert result["player_name"] == "Star Batter"
    assert result["team"] == "Lions"
    assert result["opponent"] == "Falcons"
    assert result["match_format"] == "T20"
    assert result["venue"] == "Test Stadium"
    assert result["match_result_for_team"] == "won"

    # Batting stats normalized
    assert result["batting"] is not None
    assert result["batting"]["runs"] == 72
    assert result["batting"]["balls_faced"] == 48
    assert result["batting"]["strike_rate"] == 150.0
    assert result["batting"]["is_out"] is False

    # No bowling
    assert result["bowling"] is None

    # Impact
    assert result["impact_score"] == 75.0
    assert result["impact_rating"] == "high"
    assert "fifty_plus" in result["tags"]
    assert "match_winner" in result["tags"]

    # Headline stat
    assert "72*" in result["headline_stat"]
    assert "(48)" in result["headline_stat"]

    # Narrative
    assert len(result["performance_narrative"]) > 0
    assert "Star Batter" in result["performance_narrative"]


def test_get_context_for_player_profile_bowler():
    """Test player profile extraction for a bowler."""
    from backend.services.match_context_service import get_context_for_player_profile, PlayerPerformance

    mcp = {
        "match_id": "bowler-test",
        "format": "T20",
        "overs_per_side": 20,
        "venue": "Home Ground",
        "result": "Falcons won by 20 runs",
        "team_a": {"name": "Lions", "players": []},
        "team_b": {"name": "Falcons", "players": [{"id": "b1", "name": "Fast Bowler"}]},
        "innings": [],
        "phase_breakdowns": [],
        "player_performances": [
            PlayerPerformance(
                player_id="b1",
                player_name="Fast Bowler",
                team="Falcons",
                role="bowler",
                batting=None,
                bowling={
                    "overs": 4,
                    "runs_conceded": 24,
                    "wickets": 3,
                    "maidens": 0,
                    "economy": 6.0,
                },
                impact_score=55.0,
                tags=["wicket_taker", "economical"],
            ),
        ],
        "callouts": [],
    }

    result = get_context_for_player_profile(mcp, "b1")

    assert result is not None
    assert result["player_id"] == "b1"
    assert result["player_name"] == "Fast Bowler"
    assert result["team"] == "Falcons"
    assert result["opponent"] == "Lions"
    assert result["match_result_for_team"] == "won"

    # Bowling stats normalized
    assert result["bowling"] is not None
    assert result["bowling"]["wickets"] == 3
    assert result["bowling"]["runs_conceded"] == 24
    assert result["bowling"]["overs"] == 4
    assert result["bowling"]["economy"] == 6.0

    # No batting
    assert result["batting"] is None

    # Headline stat
    assert "3/24" in result["headline_stat"]
    assert "4 ov" in result["headline_stat"]

    # Narrative mentions wickets
    assert "3" in result["performance_narrative"] or "wicket" in result["performance_narrative"].lower()


def test_get_context_for_player_profile_all_rounder():
    """Test player profile extraction for an all-rounder."""
    from backend.services.match_context_service import get_context_for_player_profile, PlayerPerformance

    mcp = {
        "match_id": "allrounder-test",
        "format": "T20",
        "overs_per_side": 20,
        "venue": None,
        "result": "Lions won by 3 wickets",
        "team_a": {"name": "Lions", "players": []},
        "team_b": {"name": "Falcons", "players": []},
        "innings": [],
        "phase_breakdowns": [],
        "player_performances": [
            PlayerPerformance(
                player_id="ar1",
                player_name="All Rounder",
                team="Lions",
                role="all-rounder",
                batting={
                    "runs": 35,
                    "balls_faced": 22,
                    "fours": 3,
                    "sixes": 2,
                    "strike_rate": 159.1,
                    "is_out": True,
                },
                bowling={
                    "overs": 3,
                    "runs_conceded": 18,
                    "wickets": 2,
                    "economy": 6.0,
                },
                impact_score=48.0,
                tags=["impact_innings"],
            ),
        ],
        "callouts": [],
    }

    result = get_context_for_player_profile(mcp, "ar1")

    assert result is not None

    # Both batting and bowling present
    assert result["batting"] is not None
    assert result["batting"]["runs"] == 35
    assert result["bowling"] is not None
    assert result["bowling"]["wickets"] == 2

    # Headline stat has both
    assert "35" in result["headline_stat"]
    assert "2/18" in result["headline_stat"]


def test_get_context_for_player_profile_not_found():
    """Test that None is returned for non-existent player."""
    from backend.services.match_context_service import get_context_for_player_profile

    mcp = {
        "match_id": "not-found-test",
        "format": "T20",
        "team_a": {"name": "Lions", "players": []},
        "team_b": {"name": "Falcons", "players": []},
        "player_performances": [],
        "callouts": [],
    }

    result = get_context_for_player_profile(mcp, "nonexistent-player")

    assert result is None


def test_get_context_for_player_profile_fallback_to_roster():
    """Test fallback to team roster when player not in performances."""
    from backend.services.match_context_service import get_context_for_player_profile

    mcp = {
        "match_id": "roster-fallback-test",
        "format": "ODI",
        "overs_per_side": 50,
        "venue": "Test Venue",
        "result": "Lions won by 10 runs",
        "team_a": {
            "name": "Lions",
            "players": [
                {"id": "reserve1", "name": "Reserve Player", "role": "batter"},
            ],
        },
        "team_b": {"name": "Falcons", "players": []},
        "innings": [],
        "phase_breakdowns": [],
        "player_performances": [],  # Player not in performances
        "callouts": [],
    }

    result = get_context_for_player_profile(mcp, "reserve1")

    assert result is not None
    assert result["player_id"] == "reserve1"
    assert result["player_name"] == "Reserve Player"
    assert result["team"] == "Lions"
    assert result["opponent"] == "Falcons"

    # No stats
    assert result["batting"] is None
    assert result["bowling"] is None
    assert result["headline_stat"] == "Did not bat/bowl"

    # Narrative indicates limited impact
    assert "limited impact" in result["performance_narrative"].lower() or "Reserve Player" in result["performance_narrative"]


def test_get_context_for_player_profile_lost_match():
    """Test result determination when player's team lost."""
    from backend.services.match_context_service import get_context_for_player_profile, PlayerPerformance

    mcp = {
        "match_id": "loss-test",
        "format": "T20",
        "overs_per_side": 20,
        "result": "Falcons won by 15 runs",  # Lions lost
        "team_a": {"name": "Lions", "players": []},
        "team_b": {"name": "Falcons", "players": []},
        "player_performances": [
            PlayerPerformance(
                player_id="loser1",
                player_name="Good Effort",
                team="Lions",
                role="batter",
                batting={"runs": 45, "balls_faced": 35, "strike_rate": 128.6, "is_out": True},
                bowling=None,
                impact_score=40.0,
                tags=[],
            ),
        ],
        "callouts": [],
    }

    result = get_context_for_player_profile(mcp, "loser1")

    assert result is not None
    assert result["match_result_for_team"] == "lost"
    assert result["team"] == "Lions"
    assert result["opponent"] == "Falcons"
