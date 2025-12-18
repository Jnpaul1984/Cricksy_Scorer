# Cricksy Scorer - CI/Workflow Pre-Check Guide

## Overview

This document defines the **local pre-commit validation** workflow that must be run before pushing to GitHub. This prevents CI failures and reduces turnaround time during development.

## Critical: Run Before Every Push

### Full Pre-Check Command
```bash
# Complete validation before push
python -m pre_commit run --all-files

# If that passes, run backend tests
cd backend
pytest -q tests/test_health.py tests/test_results_endpoint.py

# If all pass, run frontend checks
cd frontend
npm run type-check
npm run build

# Then push
git push
```

### Quick Reference: One-Liner
```bash
python -m pre_commit run --all-files && cd backend && pytest -q tests/ && cd ../frontend && npm run type-check && npm run build
```

---

## GitHub Actions Workflows (What CI Runs)

### 1. **Pre-Commit** (`pre-commit/action@v3.0.1`)
**Runs:** All files
**Checks:**
- ✅ YAML syntax validation
- ✅ File ending fixes
- ✅ Trailing whitespace removal
- ✅ Private key detection
- ✅ Ruff linting & formatting

**Local Test:**
```bash
python -m pre_commit run --all-files
```

**Common Failures & Fixes:**
| Error | Fix |
|-------|-----|
| `YAML parsing error` | Check `.mcp/checklist.yaml` - must be list only (remove root metadata) |
| `E501 Line too long` | Split long lines; check `ruff.toml` for exclusions |
| `Trailing whitespace` | Pre-commit auto-fixes; just stage & commit |
| `End of file issues` | Pre-commit auto-fixes; just stage & commit |
| `ruff format mismatch` | Run `python -m ruff format .` to auto-fix |

---

### 2. **Lint** (`lint.yml`)
**Runs:** Ruff + MyPy
**Tools:**
- `ruff==0.6.5` - Python linter
- `mypy==1.11.2` - Type checker

**Local Test:**
```bash
cd C:\Users\Hp\Cricksy_Scorer
python -m ruff check .
python -m ruff format --check .
cd backend && mypy .
```

**Common Failures & Fixes:**
| Error | Fix |
|-------|-----|
| `S602 subprocess shell=True` | Add to `ruff.toml` under `[lint.per-file-ignores]` |
| `mypy cache error` | `rm -Recurse -Force .mypy_cache` (clear cache) |
| `Import errors` | Check `PYTHONPATH=$PWD` in backend |
| `Type annotation missing` | Add return type hints to functions |

---

### 3. **Security** (`ci.yml` security job)
**Tools:**
- `bandit[toml]==1.7.9` - Bandit security scanner
- `pip-audit==2.7.3` - Dependency audit

**Local Test:**
```bash
# Bandit
bandit -r backend -c backend/pyproject.toml -ll

# pip-audit
pip-audit -r backend/requirements.txt --progress-spinner off
```

**Config:**
- Exceptions in `backend/pyproject.toml` under `[tool.bandit]`
- Ignored vulns in `.github/workflows/ci.yml`

---

### 4. **Backend Tests** (`ci.yml` backend-tests job)
**Test Suites:**
- `tests/test_health.py` - Health endpoint
- `tests/test_results_endpoint.py` - Results finalization

**Local Test:**
```bash
cd backend
$env:CRICKSY_IN_MEMORY_DB = "1"
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:?cache=shared"
$env:APP_SECRET_KEY = "test-secret-key"
pytest -q tests/test_health.py tests/test_results_endpoint.py
```

---

### 5. **Backend Integration Tests** (`ci.yml` backend-integration-tests job)
**Runs:** Full integration test suite
**Database:** In-memory SQLite

**Local Test:**
```bash
cd backend
$env:CRICKSY_IN_MEMORY_DB = "1"
pytest -q tests/ --tb=short
```

---

## Frontend Checks (Not in CI, But Required)

### Type Checking
```bash
cd frontend
npm run type-check
```

**Common Failures:**
- Vue 3 template syntax errors
- Missing type definitions
- Pinia store type mismatches

### Production Build
```bash
cd frontend
npm run build
```

**Common Failures:**
- Circular dependencies
- Missing imports
- Vite configuration issues

---

## Pre-Push Validation Script

Create this script to automate all checks (optional):

**File:** `scripts/precheck.sh` (Unix/Mac) or `scripts/precheck.ps1` (Windows)

```powershell
# scripts/precheck.ps1
Write-Host "🔍 Running Cricksy Scorer Pre-Push Validation..." -ForegroundColor Cyan

# 1. Pre-commit
Write-Host "`n✅ Running pre-commit checks..." -ForegroundColor Yellow
python -m pre_commit run --all-files
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Pre-commit failed!" -ForegroundColor Red
    exit 1
}

# 2. Backend tests
Write-Host "`n✅ Running backend tests..." -ForegroundColor Yellow
cd backend
$env:CRICKSY_IN_MEMORY_DB = "1"
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:?cache=shared"
$env:APP_SECRET_KEY = "test-secret-key"
pytest -q tests/test_health.py tests/test_results_endpoint.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Backend tests failed!" -ForegroundColor Red
    exit 1
}
cd ..

# 3. Frontend type-check
Write-Host "`n✅ Running frontend type-check..." -ForegroundColor Yellow
cd frontend
npm run type-check
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Frontend type-check failed!" -ForegroundColor Red
    exit 1
}

# 4. Frontend build
Write-Host "`n✅ Running frontend build..." -ForegroundColor Yellow
npm run build
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Frontend build failed!" -ForegroundColor Red
    exit 1
}
cd ..

Write-Host "`n✅ All checks passed! Ready to push." -ForegroundColor Green
```

**Usage:**
```bash
./scripts/precheck.ps1   # Windows
./scripts/precheck.sh    # Unix/Mac
```

---

## Agent Instructions for Copilot

### When Implementing Features

Before committing/pushing:

1. **Always run pre-commit first**
   ```bash
   python -m pre_commit run --all-files
   ```

2. **If backend code changed**: Run backend tests
   ```bash
   cd backend && pytest -q tests/test_health.py
   ```

3. **If frontend code changed**: Type-check & build
   ```bash
   cd frontend && npm run type-check && npm run build
   ```

4. **Commit only after ALL checks pass**

5. **Push only if git history is clean**

### Common Issues to Avoid

| Issue | Prevention |
|-------|-----------|
| YAML syntax errors | Validate YAML structure: `python -c "import yaml; yaml.safe_load(open('.mcp/checklist.yaml'))"` |
| Line length violations | Check `ruff.toml` line-length setting (100 chars) |
| Type errors in Vue | Run `npm run type-check` before committing |
| Stale mypy cache | `rm -Recurse -Force .mypy_cache` if mypy fails with weird errors |
| Import path issues | Ensure `PYTHONPATH` is set: `$env:PYTHONPATH="C:\Users\Hp\Cricksy_Scorer"` |
| Pre-commit modifies files | Re-run `python -m pre_commit run --all-files` until no changes |

---

## Workflow Checklist for Agents

**Before Running `git push`:**

- [ ] `python -m pre_commit run --all-files` → **PASSED**
- [ ] Backend tests pass (if backend files changed)
- [ ] `npm run type-check` passes (if frontend files changed)
- [ ] `npm run build` passes (if frontend files changed)
- [ ] No unstaged changes remain
- [ ] Commit messages are descriptive
- [ ] Branch is up-to-date with main (or intentionally divergent)

---

## Emergency Fixes

### If Pre-Commit Fails
```bash
# Clear caches
rm -Recurse -Force .mypy_cache
rm -Recurse -Force .ruff_cache

# Re-run with verbose
python -m pre_commit run --all-files -v

# Fix auto-fixable issues
python -m ruff format .
python -m pre_commit run --all-files  # Repeat until clean
```

### If MyPy Crashes
```bash
# Clear cache (most common fix)
rm -Recurse -Force .mypy_cache

# Upgrade mypy
pip install --upgrade mypy==1.11.2
```

### If Backend Tests Fail
```bash
# Ensure env vars
$env:CRICKSY_IN_MEMORY_DB = "1"
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:?cache=shared"
$env:APP_SECRET_KEY = "test-secret-key"

# Run with verbose output
cd backend && pytest tests/ -v --tb=short
```

### If Frontend Build Fails
```bash
# Clear cache
rm -Recurse -Force node_modules/.vite
rm -Recurse -Force dist

# Rebuild
npm install
npm run build
```

---

## CI Pipeline Summary

```
Push to GitHub
    ↓
[Pre-Commit] - YAML, formatting, trailing spaces
    ↓
[Lint] - Ruff + MyPy
    ↓
[Security] - Bandit + pip-audit
    ↓
[Backend Tests] - test_health.py, test_results_endpoint.py
    ↓
[Backend Integration] - Full test suite
    ↓
✅ All Checks Passed → Ready to Merge
```

---

## Files to Watch

When making changes, verify these don't break CI:

| File | CI Check | How to Fix |
|------|----------|-----------|
| `.mcp/checklist.yaml` | YAML syntax | Keep root level as list only |
| `.github/workflows/ci.yml` | Pipeline definition | Test locally with `python -m pre_commit` |
| `backend/pyproject.toml` | mypy config | Ensure `PYTHONPATH` set |
| `ruff.toml` | Linting rules | Add exceptions under `[lint.per-file-ignores]` |
| `.pre-commit-config.yaml` | Pre-commit hooks | Update carefully, test with `--all-files` |
| `frontend/package.json` | npm deps | Run `npm install` if changed |

---

## Support

For CI failures:
1. Check the error message in GitHub Actions
2. Reproduce locally with the exact command from this guide
3. Apply the fix from the "Common Failures" table
4. Re-run pre-check
5. Push

**Questions?** Check `.github/workflows/ci.yml` for the exact commands run by CI.
