# CI/CD Workflow Troubleshooting Guide

## Problem: Local Tests Pass but GitHub Actions Fail

### Root Cause Analysis

When local tests pass but GitHub Actions workflows fail, it's usually one of:

1. **Missing Type Imports** (MOST COMMON)
   - Python type hints reference classes but don't import them
   - Works locally if you've imported in REPL/have stale caches
   - CI runs fresh, finds errors

2. **Environment Variables Missing**
   - `PYTHONPATH` not set in CI
   - Database URL misconfigured
   - Secret keys not injected

3. **File Path Issues**
   - Absolute vs relative imports
   - Different working directories
   - Case sensitivity on Linux CI vs Windows local

4. **Dependency Version Mismatches**
   - `requirements.txt` pins old versions
   - CI installs different transitive deps
   - Local has development packages not in CI

### Solution: The Type Annotation Import Pattern

Every route file that uses type hints MUST import the types:

```python
# ❌ BAD - Will fail mypy in CI
@router.post("/endpoint")
async def handler(db: AsyncSession = Depends(get_db)) -> Game:
    ...

# ✅ GOOD - Imports at top
from backend.sql_app.models import Game
from sqlalchemy.ext.asyncio import AsyncSession

@router.post("/endpoint")
async def handler(db: AsyncSession = Depends(get_db)) -> Game:
    ...
```

### Checklist: Before Committing to Main

Every commit to `main` must pass this checklist (scripts in `.mcp/` auto-validate):

```bash
# 1. Lint check
ruff check backend/ frontend/

# 2. Format check
ruff format --check backend/ frontend/

# 3. Type check (THE CRITICAL ONE)
cd backend && mypy --config-file pyproject.toml --explicit-package-bases .

# 4. Test check
pytest backend/tests/ -v --tb=short

# 5. Frontend build
cd frontend && npm run typecheck && npm run build
```

### Why Workflows Fail (Common Scenarios)

| Error | Root Cause | Fix |
|-------|-----------|-----|
| `error: Name "X" is not defined [name-defined]` | Missing import in route file | Add `from backend.sql_app.models import X` |
| `error: mypy: No module named 'backend'` | `PYTHONPATH` not set | CI workflow adds `PYTHONPATH: ${{ github.workspace }}` |
| `AttributeError: module 'backend' has no attribute` | Circular imports or missing `__init__.py` | Check imports don't create cycles |
| `ImportError: cannot import name 'X'` | Schema/model name mismatch | Verify class name in `schemas.py` or `models.py` |
| `mypy: Found N errors` | Type mismatches | Fix types or add `# type: ignore` with comment |

### Git Pre-Commit Hook (Recommended)

Create `.git/hooks/pre-commit`:

```bash
#!/bin/bash
set -e

echo "🔍 Running pre-commit checks..."

# 1. Type check
echo "  • MyPy..."
cd backend
python -m mypy --config-file pyproject.toml --explicit-package-bases . || {
  echo "❌ MyPy failed. Fix errors above."
  exit 1
}
cd ..

# 2. Lint
echo "  • Ruff..."
ruff check . || {
  echo "❌ Ruff check failed. Run: ruff check . --fix"
  exit 1
}

# 3. Format
echo "  • Ruff Format..."
ruff format --check . || {
  echo "❌ Format failed. Run: ruff format ."
  exit 1
}

echo "✅ Pre-commit checks passed!"
```

Make executable: `chmod +x .git/hooks/pre-commit`

### How to Debug Local vs CI Mismatch

**Step 1: Replicate CI locally**

```powershell
# Set exact environment as CI
$env:PYTHONPATH = "c:\Users\Hp\Cricksy_Scorer"
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:"
$env:CRICKSY_IN_MEMORY_DB = "1"

# Run exact CI commands
cd backend
python -m mypy --config-file pyproject.toml --explicit-package-bases .
pytest -v
```

**Step 2: Check output for first error**

- First mypy error tells you which import is missing
- First pytest error tells you which dependency is missing

**Step 3: Fix and re-run**

```powershell
# Fix imports, then validate
ruff check .
ruff format --check .
mypy --config-file backend/pyproject.toml --explicit-package-bases backend
```

### Common Fixes Applied

#### Fix 1: Add Missing Imports to Route Files

**Symptom:** `error: Name "Game" is not defined [name-defined]`

**File:** `backend/routes/training_drills.py` (and others)

**Fix:**
```python
# Add to imports section
from backend.sql_app.models import Game, Player, BattingScorecard
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

# Now use in type hints
@router.get("/drills/{game_id}", response_model=Game)
async def get_drills(game_id: str, db: AsyncSession = Depends(get_db)) -> Game:
    ...
```

#### Fix 2: Duplicate Schema Definitions

**Symptom:** `error: Name "Player" already defined on line N [no-redef]`

**File:** `backend/sql_app/schemas.py`

**Fix:** Remove duplicate class definitions; keep only the first definition of each class.

#### Fix 3: PYTHONPATH Not Set in CI

**Symptom:** Works locally but fails in CI with `ModuleNotFoundError: No module named 'backend'`

**File:** `.github/workflows/*.yml`

**Fix:** Add to every job that runs Python:
```yaml
env:
  PYTHONPATH: ${{ github.workspace }}
```

### CI Workflow Validation Sequence

GitHub Actions runs workflows in this order (from `.github/workflows/`):

1. **lint.yml** - Runs first, checks format/types
   - If fails → All dependent jobs blocked
   - Fix: `mypy` errors

2. **ci.yml** - Runs unit tests  
   - Depends on: Pre-commit hook passing
   - Fix: Test failures, missing migrations

3. **deploy-backend.yml** - Builds Docker image
   - Depends on: ci.yml passing
   - Fix: Runtime errors, missing secrets

4. **deploy-frontend.yml** - Builds frontend
   - Independent of backend
   - Fix: TypeScript errors, build failures

### Preventing Workflow Failures

**Rule 1:** Always run `mypy` locally before `git push`

```powershell
cd backend
python -m mypy --config-file pyproject.toml --explicit-package-bases .
```

**Rule 2:** Every type hint needs an import

```python
# Route file template
from backend.sql_app.models import Game, Player, BattingScorecard, Delivery
from backend.sql_app.schemas import ...
from fastapi import APIRouter, Depends, HTTPException

router = APIRouter(...)

# Now safe to use in type hints
@router.get("/{id}", response_model=Game)
async def get_game(id: str) -> Game:
    ...
```

**Rule 3:** Test the full CI locally before pushing

```powershell
# Simulate full CI
./scripts/test-full-ci.ps1
```

### Emergency Rollback

If workflows are blocked:

```bash
# Revert last commit
git revert HEAD

# Push revert
git push origin main

# This unblocks other commits; investigate the error locally
```

## Quick Reference: Troubleshooting Steps

1. ✅ Run `mypy` locally → Fix type errors
2. ✅ Run `ruff check` locally → Fix lint errors
3. ✅ Run `ruff format --check` → Run formatter if needed
4. ✅ Run `pytest` locally → Fix test failures
5. ✅ Commit with clear message referencing the fix
6. ✅ Push and monitor GitHub Actions
7. ✅ If still fails, check workflow logs for exact error
8. ✅ Compare CI error to local → Find environment difference

## Files to Update When Fixing Workflows

When you fix a type issue that was blocking CI:

1. **Update this file** - Add to the fixes section with symptom/fix
2. **Update `.mcp/checklist.yaml`** - Mark task done with verification commands run
3. **Commit together** - Code fix + doc updates in one commit

```bash
git add backend/routes/file.py WORKFLOW_TROUBLESHOOTING_GUIDE.md
git commit -m "fix: Add missing imports to routes

- Added Game, Player, BattingScorecard imports to training_drills.py
- Fixed mypy errors: [name-defined] for type hints
- Local validation: mypy ✓, ruff ✓, pytest ✓"
git push
```

---

**Last Updated:** 2025-12-21  
**Maintained By:** Copilot + Dev Team  
**Next Review:** After next workflow failure or major change
