"""Main entry point for cricksy_scorer package."""

import sys
from .cli import parse_args, run_from_args


__all__ = ["run", "main"]


def run(argv=None) -> int:
    """Run the cricksy scorer application.

    This is the main entry point that orchestrates CLI parsing and execution.

    Args:
        argv: Command-line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code (0 for success)
    """
    args = parse_args(argv)
    return run_from_args(args)


def main() -> None:
    """Main entry point when called as a script."""
    sys.exit(run())


if __name__ == "__main__":
    main()
