"""Tests for data models."""

from cricksy_scorer.models import Player, MatchConfig, ScoreResult


def test_player_creation():
    """Test creating a Player instance."""
    player = Player(name="John Doe", player_id="p001")

    assert player.name == "John Doe"
    assert player.player_id == "p001"
    assert player.is_captain is False
    assert player.is_wicketkeeper is False


def test_player_with_roles():
    """Test creating a Player with captain and wicketkeeper roles."""
    player = Player(
        name="Jane Doe",
        player_id="p002",
        is_captain=True,
        is_wicketkeeper=True,
    )

    assert player.is_captain is True
    assert player.is_wicketkeeper is True


def test_match_config_creation():
    """Test creating a MatchConfig instance."""
    config = MatchConfig(
        match_id="m001",
        team1_name="India",
        team2_name="Australia",
        overs=50,
    )

    assert config.match_id == "m001"
    assert config.team1_name == "India"
    assert config.team2_name == "Australia"
    assert config.overs == 50
    assert config.team1_players == []
    assert config.team2_players == []


def test_match_config_with_players():
    """Test creating a MatchConfig with players."""
    player1 = Player(name="Player 1")
    player2 = Player(name="Player 2")

    config = MatchConfig(
        team1_players=[player1],
        team2_players=[player2],
    )

    assert len(config.team1_players) == 1
    assert len(config.team2_players) == 1
    assert config.team1_players[0].name == "Player 1"


def test_score_result_creation():
    """Test creating a ScoreResult instance."""
    result = ScoreResult(
        match_id="m001",
        team1_score=250,
        team2_score=240,
        team1_wickets=5,
        team2_wickets=10,
        winner="Team 1",
        status="completed",
    )

    assert result.match_id == "m001"
    assert result.team1_score == 250
    assert result.team2_score == 240
    assert result.team1_wickets == 5
    assert result.team2_wickets == 10
    assert result.winner == "Team 1"
    assert result.status == "completed"


def test_score_result_defaults():
    """Test ScoreResult with default values."""
    result = ScoreResult()

    assert result.match_id is None
    assert result.team1_score == 0
    assert result.team2_score == 0
    assert result.team1_wickets == 0
    assert result.team2_wickets == 0
    assert result.winner is None
    assert result.status == "pending"
