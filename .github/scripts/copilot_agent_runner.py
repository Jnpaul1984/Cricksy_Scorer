#!/usr/bin/env python3
"""
Minimal runner for the Copilot agent workflow.

This placeholder verifies required environment variables and prints
instructions. It is intentionally small so it passes ruff/mypy checks.

When you are ready, we can replace this file with the full runner that:
 - creates branch feature/upload-ocr-worker-ws-hardening
 - commits prepared files (one commit per major area)
 - opens a pull request

Do NOT paste tokens in chat. Set COPILOT_AUTOMATION_TOKEN
as a repository secret in GitHub Actions before running the workflow.
"""

from __future__ import annotations

import os
import sys


def main() -> int:
    token: str | None = os.getenv("COPILOT_AUTOMATION_TOKEN")
    repo: str | None = os.getenv("GITHUB_REPOSITORY")

    print("Copilot runner placeholder starting...")

    if token is None:
        print(
            "Warning: COPILOT_AUTOMATION_TOKEN is not set. "
            "Add it to repository secrets to enable automation."
        )

    if repo is None:
        print(
            "Warning: GITHUB_REPOSITORY is not set. The Actions environment "
            "normally sets this automatically."
        )

    print()
    print("This placeholder does not modify the repository.")
    print("To proceed with automated PR creation, replace this file with")
    print("the full runner that creates the branch, uploads files, and")
    print("opens the pull request using the COPILOT_AUTOMATION_TOKEN.")
    print()
    print("If you want, I can generate the full runner in smaller commits")
    print("that comply with ruff/mypy. Tell me when to proceed.")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
