"""Command-line interface for cricket scoring."""

import argparse
import sys
from typing import List, Optional

from .config import load_config
from .models import MatchConfig, Player
from .scorer import score_match


__all__ = ["parse_args", "run_from_args"]


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command-line arguments.

    TODO: Expand with full CLI options in follow-up PR.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="cricksy_scorer",
        description="Cricket scoring application",
    )

    parser.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="Path to configuration JSON file",
    )

    parser.add_argument(
        "--overs",
        "-o",
        type=int,
        default=20,
        help="Number of overs per innings (default: 20)",
    )

    parser.add_argument(
        "--team1",
        type=str,
        default="Team 1",
        help="Name of first team (default: Team 1)",
    )

    parser.add_argument(
        "--team2",
        type=str,
        default="Team 2",
        help="Name of second team (default: Team 2)",
    )

    return parser.parse_args(argv)


def run_from_args(args: argparse.Namespace) -> int:
    """Run the cricket scorer with parsed arguments.

    TODO: Implement full CLI workflow in follow-up PR.
    This is a stub that demonstrates the structure.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code (0 for success)
    """
    # Load configuration if provided
    config_data = load_config(args.config)

    # Create match configuration from args and config file
    match_config = MatchConfig(
        team1_name=args.team1,
        team2_name=args.team2,
        overs=args.overs,
    )

    # Score the match (stub)
    result = score_match(match_config)

    # Print result (stub)
    print(f"Match scored: {match_config.team1_name} vs {match_config.team2_name}")
    print(f"Status: {result.status}")

    return 0
