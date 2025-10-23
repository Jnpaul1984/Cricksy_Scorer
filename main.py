"""Compatibility shim for cricksy_scorer package.

This file maintains backward compatibility by importing and calling
the new package structure. All logic has been moved to the cricksy_scorer package.
"""

import sys
from cricksy_scorer.main import run


if __name__ == "__main__":
    sys.exit(run())
