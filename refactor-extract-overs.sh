#!/usr/bin/env bash
# One-shot script to:
# - create branch refactor/extract-overs from origin/refactor/split-main
# - add backend/helpers.py and tests/test_backend_helpers.py
# - replace local _overs_str_from_balls in backend/main.py with import alias
# - run formatters (if available) and run tests
# - push branch and (optionally) open a draft PR with gh
#
# Run this from the repo root.
# Usage:
#   chmod +x refactor-extract-overs.sh
#   ./refactor-extract-overs.sh
set -euo pipefail

REPO_ROOT="$(pwd)"
BRANCH="refactor/extract-overs"
BASE_REMOTE_BRANCH="origin/refactor/split-main"
HELPER_PATH="backend/helpers.py"
TEST_PATH="tests/test_backend_helpers.py"
MAIN_PY="backend/main.py"

echo "Starting refactor script in: ${REPO_ROOT}"
# Basic checks
if [ ! -d ".git" ]; then
  echo "ERROR: This directory does not look like a git repository (no .git). Exit."
  exit 1
fi

if ! git rev-parse --verify "${BASE_REMOTE_BRANCH}" >/dev/null 2>&1; then
  echo "ERROR: Remote branch ${BASE_REMOTE_BRANCH} not found locally. Run 'git fetch origin' then retry."
  echo "You can run: git fetch origin && git checkout -b ${BRANCH} origin/refactor/split-main"
  exit 1
fi

# Require clean working tree to avoid accidental conflicts
if [ -n "$(git status --porcelain)" ]; then
  echo "Your working tree has uncommitted changes. Please commit or stash them before running this script."
  git status --porcelain
  exit 1
fi

# Create branch
echo "Creating branch ${BRANCH} from ${BASE_REMOTE_BRANCH}..."
git checkout -b "${BRANCH}" "${BASE_REMOTE_BRANCH}"

# Create backend/helpers.py
echo "Adding ${HELPER_PATH}..."
mkdir -p "$(dirname "${HELPER_PATH}")"
cat > "${HELPER_PATH}" <<'PY'
"""Backend helper utilities (small, well-tested helpers).

This module is a safe place for pure helpers extracted from backend/main.py.
Start with overs_str_from_balls extracted from the original module.
"""
from __future__ import annotations

from typing import Final

__all__ = ["overs_str_from_balls"]

BALLS_PER_OVER: Final[int] = 6


def overs_str_from_balls(balls: int) -> str:
    """Return a string in 'overs.balls' format for a given legal-ball count.

    Examples:
      0 -> "0.0"
      6 -> "1.0"
      7 -> "1.1"
    """
    # Accept int-like values but prefer ints to keep behavior explicit
    try:
        b = int(balls)
    except Exception as exc:  # defensive
        raise TypeError("balls must be an integer-like value") from exc
    return f"{b // BALLS_PER_OVER}.{b % BALLS_PER_OVER}"
PY

# Create tests file
echo "Adding ${TEST_PATH}..."
mkdir -p "$(dirname "${TEST_PATH}")"
cat > "${TEST_PATH}" <<'PY'
from backend.helpers import overs_str_from_balls


def test_overs_str_from_balls_zero():
    assert overs_str_from_balls(0) == "0.0"


def test_overs_str_from_balls_full_over():
    assert overs_str_from_balls(6) == "1.0"


def test_overs_str_from_balls_mixed():
    assert overs_str_from_balls(13) == "2.1"


def test_overs_str_from_balls_coerce_int_like():
    # Accept int-like float but coerce to int
    assert overs_str_from_balls(7.0) == "1.1"
PY

# Stage and commit helper + tests as first focused commit
git add "${HELPER_PATH}" "${TEST_PATH}"
git commit -m "chore(refactor): add backend.helpers and unit tests for overs_str_from_balls"

# Modify backend/main.py: replace existing def _overs_str_from_balls(...) body with import alias
if [ ! -f "${MAIN_PY}" ]; then
  echo "ERROR: ${MAIN_PY} not found. Aborting."
  exit 1
fi

echo "Modifying ${MAIN_PY} to import overs_str_from_balls as _overs_str_from_balls..."
# Create a backup
cp "${MAIN_PY}" "${MAIN_PY}.bak"

python - <<'PY'
import io,sys,re,os
p = "backend/main.py"
txt = open(p, "r", encoding="utf-8").read().splitlines()
out_lines = []
i = 0
n = len(txt)
pattern = re.compile(r"^\s*def\s+_overs_str_from_balls\s*\(")
replaced = False
while i < n:
    line = txt[i]
    if pattern.match(line) and not replaced:
        # skip the entire indented block starting at this def line
        # find next line index j where line starts at column 0 (no leading whitespace) and is not empty
        i += 1
        while i < n:
            l = txt[i]
            if re.match(r"^[^\s#@]", l) and not l.startswith(" "):  # first-column non-whitespace
                break
            # If the line is blank (no chars), it's potentially end-of-block too: but keep scanning until dedent
            if l.strip() == "" and i+1 < n and re.match(r"^[^\s#@]", txt[i+1]):
                i += 1
                break
            i += 1
        # insert import alias at this position
        out_lines.append("from .helpers import overs_str_from_balls as _overs_str_from_balls")
        replaced = True
        continue
    else:
        out_lines.append(line)
        i += 1

# If pattern was not found, insert import after top-level imports block
if not replaced:
    # try to insert after the initial block of imports (first non-import occurs)
    ins_at = None
    for idx,l in enumerate(out_lines):
        if not (l.strip().startswith("import ") or l.strip().startswith("from ") or l.strip()=="" or l.strip().startswith("#")):
            ins_at = idx
            break
    if ins_at is None:
        out_lines.append("\nfrom .helpers import overs_str_from_balls as _overs_str_from_balls")
    else:
        out_lines.insert(ins_at, "from .helpers import overs_str_from_balls as _overs_str_from_balls")

open(p, "w", encoding="utf-8").write("\n".join(out_lines) + "\n")
print("Modification applied to", p)
PY

# Stage and commit the main.py change
git add "${MAIN_PY}"
git commit -m "refactor(backend): import overs_str_from_balls from backend.helpers (preserve _overs_str_from_balls alias)"

# Optionally run formatters if available
if command -v black >/dev/null 2>&1; then
  echo "Running black..."
  black .
  if git status --porcelain | grep -q '^'; then
    git add -A
    git commit -m "style: apply black formatting"
  fi
else
  echo "black not found; skipping formatting step. (Install with 'pip install black' if desired.)"
fi

# Run the new tests (fast)
echo "Running new unit tests: pytest -q ${TEST_PATH}"
if command -v pytest >/dev/null 2>&1; then
  pytest -q "${TEST_PATH}" || {
    echo "Unit tests failed. See output above. To debug, restore backup: cp ${MAIN_PY}.bak ${MAIN_PY}"
    exit 1
  }
else
  echo "pytest not found. Install dependencies and run: pytest -q ${TEST_PATH}"
  exit 1
fi

# Also run full test-suite (optional)
echo "Now running full test-suite: pytest -q (this may take a while)"
pytest -q || {
  echo "Some tests failed in the full suite. Review failures locally. Backup of main.py is at ${MAIN_PY}.bak"
  # still attempt to push branch so you can inspect on remote
}

# Push branch
echo "Pushing branch ${BRANCH} to origin..."
git push -u origin "${BRANCH}"

# Attempt to create a draft PR if gh is available
PR_TITLE="refactor(backend): extract overs_str_from_balls into backend.helpers"
PR_BODY="This small, safe refactor extracts the overs-string helper from backend/main.py into backend/helpers.py and adds unit tests.

Summary:
- Add backend/helpers.py with overs_str_from_balls and BALLS_PER_OVER constant.
- Add tests/test_backend_helpers.py (unit tests cover zero/full/mixed and int-like inputs).
- Update backend/main.py to import overs_str_from_balls as _overs_str_from_balls to preserve the original private name and avoid changing call sites.
- This is a pure refactor; no business logic changes intended."

if command -v gh >/dev/null 2>&1; then
  echo "Creating a draft PR with gh..."
  gh pr create --base refactor/split-main --head "${BRANCH}" --title "${PR_TITLE}" --body "${PR_BODY}" --draft
  echo "Draft PR created (if gh authenticated)."
else
  echo "gh CLI not found; to open a PR, run:"
  echo "  gh pr create --base refactor/split-main --head ${BRANCH} --title \"${PR_TITLE}\" --body \"${PR_BODY}\" --draft"
fi

echo "Script finished. Branch ${BRANCH} pushed. Open the draft PR to review and let CI run."
