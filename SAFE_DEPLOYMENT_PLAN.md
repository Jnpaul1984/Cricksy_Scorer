# Dual-Write Implementation - Safe Deployment Plan

## Workflow Requirements Summary

### ✅ Workflows That Will Run on Push to Main

1. **Lint Workflow** (`lint.yml`)
   - Ruff: Format check
   - Ruff: Lint check
   - MyPy: Type checking (strict-ish)

2. **CI Workflow** (`ci.yml`)
   - Pre-commit checks (auto-fix format)
   - Lint (ruff + mypy)
   - Security (bandit + pip-audit)
   - Backend unit tests (fast)
   - Backend integration tests

3. **Deploy Backend** (`deploy-backend.yml`)
   - Test Backend with PostgreSQL
   - Build ECR image
   - Scan and deploy to AWS

4. **Deploy Frontend** (`deploy-frontend.yml`)
   - Build Vue 3 + Vite app
   - Deploy to Firebase Hosting

---

## Implementation Strategy

### Phase 1: Local Validation (Before Commit)
1. Create `backend/services/scorecard_service.py` with dual-write logic
2. Run local tests: `pytest`
3. Run local lint: `ruff check` + `ruff format` + `mypy`
4. Verify no import errors

### Phase 2: Git Commit
5. Add files: `git add`
6. Commit: `git commit`
7. Push: `git push origin main`

### Phase 3: GitHub Actions Validation (Auto-triggered)
8. Monitor workflows on GitHub
9. Verify all 4 workflows pass
10. Verify deploy succeeds

---

## Files to Create/Modify

### Create:
- `backend/services/scorecard_service.py` - Main service logic

### Modify:
- `backend/routes/scorecards.py` - Wire services into routes (already exists but shell)
- `backend/app.py` - Already includes router

### Already Done:
- `backend/sql_app/models.py` - Models created ✅
- `backend/alembic/versions/m3h4i5j6k7l8_*` - Migration created ✅

---

## Local Test Commands

```bash
# Terminal 1: Set environment
$env:PYTHONPATH = "C:\Users\Hp\Cricksy_Scorer"
$env:CRICKSY_IN_MEMORY_DB = "1"
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:?cache=shared"
$env:APP_SECRET_KEY = "test-secret-key"

# Run tests
cd c:\Users\Hp\Cricksy_Scorer\backend
pytest -q tests/

# Check format
cd c:\Users\Hp\Cricksy_Scorer
ruff format . --check --config ruff.toml

# Fix format
ruff format . --config ruff.toml

# Lint check
ruff check . --config ruff.toml

# Type check
mypy --config-file backend/pyproject.toml --explicit-package-bases backend
```

---

## Checklist Before Push

- [ ] `scorecard_service.py` created with full implementation
- [ ] Routes updated to use service functions
- [ ] No syntax errors: `pytest --collect-only` passes
- [ ] Format check passes: `ruff format --check`
- [ ] Lint check passes: `ruff check`
- [ ] Type check passes: `mypy`
- [ ] No new import errors
- [ ] Models imported correctly

---

## Expected GitHub Actions Results

### On Push to Main:
1. ✅ Lint workflow completes (15 min)
2. ✅ CI workflow completes (20 min)
3. ✅ Deploy Backend workflow starts (30 min) → Runs migrations + deploys
4. ✅ Deploy Frontend workflow starts (10 min) → Builds + deploys to Firebase

All should be green ✅

---

## Rollback Plan (If Something Fails)

If any GitHub workflow fails:
1. Fix the issue locally
2. Run tests to verify fix
3. Push again (new commit)
4. Monitor workflows again

If deploy fails but tests pass:
1. Issue is likely with AWS credentials/infrastructure
2. Check GitHub Secrets are set correctly
3. Verify AWS IAM permissions
4. May need manual deploy

---

## Next Steps

1. Implement `scorecard_service.py`
2. Run local validation
3. Commit and push
4. Monitor GitHub workflows
5. Verify deployments succeed
