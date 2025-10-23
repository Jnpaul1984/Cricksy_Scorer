"""Tests for CLI argument parsing."""

from cricksy_scorer.cli import parse_args


def test_parse_args_defaults():
    """Test parsing arguments with defaults."""
    args = parse_args([])

    assert args.config is None
    assert args.overs == 20
    assert args.team1 == "Team 1"
    assert args.team2 == "Team 2"


def test_parse_args_with_config():
    """Test parsing with config file argument."""
    args = parse_args(["--config", "test.json"])

    assert args.config == "test.json"


def test_parse_args_with_overs():
    """Test parsing with overs argument."""
    args = parse_args(["--overs", "50"])

    assert args.overs == 50


def test_parse_args_with_teams():
    """Test parsing with team name arguments."""
    args = parse_args(["--team1", "India", "--team2", "Australia"])

    assert args.team1 == "India"
    assert args.team2 == "Australia"


def test_parse_args_short_flags():
    """Test parsing with short flag arguments."""
    args = parse_args(["-c", "config.json", "-o", "10"])

    assert args.config == "config.json"
    assert args.overs == 10
