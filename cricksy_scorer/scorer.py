"""Cricket match scoring logic."""

from .models import MatchConfig, ScoreResult


__all__ = ["score_match"]


def score_match(config: MatchConfig) -> ScoreResult:
    """Score a cricket match based on configuration.

    TODO: Implement actual scoring logic in follow-up PR.
    This is a stub that returns a basic ScoreResult.

    Args:
        config: Match configuration

    Returns:
        ScoreResult with match outcome
    """
    # Stub implementation - just return a basic result
    result = ScoreResult(
        match_id=config.match_id,
        team1_score=0,
        team2_score=0,
        team1_wickets=0,
        team2_wickets=0,
        winner=None,
        status="not_started",
    )
    return result
