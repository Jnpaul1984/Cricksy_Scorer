"""End-to-end integration tests."""

import argparse
from unittest.mock import patch

from cricksy_scorer.main import run
from cricksy_scorer.cli import run_from_args, parse_args


def test_run_with_default_args():
    """Test running the application with default arguments."""
    exit_code = run([])

    assert exit_code == 0


def test_run_with_custom_teams():
    """Test running with custom team names."""
    exit_code = run(["--team1", "India", "--team2", "Australia"])

    assert exit_code == 0


def test_run_with_overs():
    """Test running with custom overs count."""
    exit_code = run(["--overs", "50"])

    assert exit_code == 0


def test_run_from_args_integration(tmp_path):
    """Test run_from_args with a temporary config file."""
    config_file = tmp_path / "config.json"
    config_file.write_text('{"test": "config"}')

    args = parse_args(["-c", str(config_file), "--overs", "10"])
    exit_code = run_from_args(args)

    assert exit_code == 0


def test_run_prints_output(capsys):
    """Test that run produces expected output."""
    run(["--team1", "TestTeam1", "--team2", "TestTeam2"])

    captured = capsys.readouterr()

    # Verify output contains team names
    assert "TestTeam1" in captured.out
    assert "TestTeam2" in captured.out
    assert "Match scored" in captured.out


def test_full_cli_flow():
    """Test complete CLI flow from argument parsing to execution."""
    # Parse arguments
    args = parse_args(["--team1", "Team A", "--team2", "Team B", "--overs", "20"])

    # Verify parsed correctly
    assert args.team1 == "Team A"
    assert args.team2 == "Team B"
    assert args.overs == 20

    # Run with parsed args
    exit_code = run_from_args(args)

    assert exit_code == 0


def test_run_with_nonexistent_config():
    """Test running with a config file that doesn't exist."""
    # Should not fail - just use default empty config
    exit_code = run(["--config", "/nonexistent/config.json"])

    assert exit_code == 0
