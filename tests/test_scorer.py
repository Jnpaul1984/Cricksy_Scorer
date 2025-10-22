"""Tests for match scoring logic."""

from cricksy_scorer.models import MatchConfig, ScoreResult
from cricksy_scorer.scorer import score_match


def test_score_match_basic():
    """Test basic score_match functionality with simple config."""
    config = MatchConfig(
        match_id="test001",
        team1_name="Team A",
        team2_name="Team B",
        overs=20,
    )

    result = score_match(config)

    # Verify result is a ScoreResult
    assert isinstance(result, ScoreResult)
    assert result.match_id == "test001"


def test_score_match_returns_score_result():
    """Test that score_match returns a valid ScoreResult structure."""
    config = MatchConfig()

    result = score_match(config)

    # Verify all expected fields exist
    assert hasattr(result, "match_id")
    assert hasattr(result, "team1_score")
    assert hasattr(result, "team2_score")
    assert hasattr(result, "team1_wickets")
    assert hasattr(result, "team2_wickets")
    assert hasattr(result, "winner")
    assert hasattr(result, "status")


def test_score_match_stub_behavior():
    """Test that score_match stub returns expected initial values."""
    config = MatchConfig(match_id="stub_test")

    result = score_match(config)

    # Stub should return zeros and not_started status
    assert result.match_id == "stub_test"
    assert result.team1_score == 0
    assert result.team2_score == 0
    assert result.team1_wickets == 0
    assert result.team2_wickets == 0
    assert result.winner is None
    assert result.status == "not_started"
