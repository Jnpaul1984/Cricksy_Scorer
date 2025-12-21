# GitHub Actions Monitoring Guide

## How to Monitor Workflows

After pushing to main, GitHub Actions will automatically trigger. Here's how to monitor:

### Via GitHub Web UI
1. Go to: https://github.com/Jnpaul1984/Cricksy_Scorer
2. Click "Actions" tab at the top
3. You'll see active workflows for commit `7c75ab2`

### Expected Workflow Sequence

```
Commit pushed (7c75ab2)
    ↓
Workflows trigger simultaneously:
    ├── Lint (python lint)
    ├── CI (tests + security)
    ├── Deploy Backend (only if tests pass)
    └── Deploy Frontend (always)
```

---

## Workflow Details

### 1. **Lint Workflow**
- **File:** `.github/workflows/lint.yml`
- **Status:** Check badge at: https://github.com/Jnpaul1984/Cricksy_Scorer/actions/workflows/lint.yml
- **What it does:**
  - Runs ruff lint check
  - Runs ruff format check
  - Runs mypy type check
- **Expected result:** ✅ PASS (all passed locally)
- **Time:** ~5 minutes
- **If fails:** Review ruff output, fix format/lint issues, commit again

### 2. **CI Workflow**
- **File:** `.github/workflows/ci.yml`
- **Status:** Check badge at: https://github.com/Jnpaul1984/Cricksy_Scorer/actions/workflows/ci.yml
- **What it does:**
  - Pre-commit checks
  - Ruff lint + format
  - MyPy type check
  - Security scans (bandit, pip-audit)
  - Backend unit tests
  - Backend integration tests
- **Expected result:** ✅ PASS
- **Time:** ~20 minutes
- **If fails:** Check test logs, may need code adjustments

### 3. **Deploy Backend Workflow**
- **File:** `.github/workflows/deploy-backend.yml`
- **Status:** Check badge at: https://github.com/Jnpaul1984/Cricksy_Scorer/actions/workflows/deploy-backend.yml
- **Depends on:** Lint + CI must pass first
- **What it does:**
  - Runs tests on PostgreSQL database
  - Runs alembic migrations
  - Builds Docker image
  - Scans image for vulnerabilities
  - Pushes to AWS ECR
  - Deploys to ECS cluster
- **Expected result:** ✅ PASS (if AWS credentials valid)
- **Time:** ~30 minutes
- **Important:** This actually applies the alembic migration to the database!
- **If fails:**
  - Check if migration has issues
  - Verify AWS credentials/permissions
  - Check ECS service health

### 4. **Deploy Frontend Workflow**
- **File:** `.github/workflows/deploy-frontend.yml`
- **Status:** Check badge at: https://github.com/Jnpaul1984/Cricksy_Scorer/actions/workflows/deploy-frontend.yml
- **What it does:**
  - Builds Vue 3 + Vite app
  - Deploys to Firebase Hosting
- **Expected result:** ✅ PASS (no frontend changes)
- **Time:** ~10 minutes

---

## Important! Alembic Migration

When the Deploy Backend workflow runs successfully, it will:

1. Create PostgreSQL test database
2. Run `alembic upgrade head`
3. This applies the new migration: `m3h4i5j6k7l8_add_player_and_scorecard_models`
4. Creates these tables:
   - `players`
   - `batting_scorecards`
   - `bowling_scorecards`
   - `deliveries`

✅ **This is expected and correct!**

---

## What to Watch For

### ✅ Success Indicators
- All workflow badges show green ✓
- Deploy Backend logs show:
  ```
  INFO [alembic.runtime.migration] Running upgrade <id> -> m3h4i5j6k7l8
  INFO [alembic.runtime.migration] Running upgrade ... add_player_and_scorecard_models
  ```
- Deploy Frontend shows "Deployment successful"
- No error messages in logs

### ⚠️ Warning Signs
- Any workflow shows red ✗
- Test failures in CI workflow
- Migration errors in Deploy Backend
- AWS deployment issues (ECR, ECS)
- Firebase deployment issues

### 🚨 Critical Issues
- Lint fails (format/type check)
- Unit tests fail
- Migration fails (breaks database)
- Backend deploy fails
- Frontend deploy fails

---

## Troubleshooting

### If Lint Fails
```
Check: ruff lint + format issues
Fix: git reset, fix issues locally, commit again
Example:
  $ ruff check --fix .
  $ ruff format .
  $ git add .
  $ git commit -m "fix: ruff lint issues"
  $ git push
```

### If CI Tests Fail
```
Check: test output logs
Fix: Likely new test fixtures or imports needed
Action: Add tests/fixtures, test locally, commit
```

### If Deploy Backend Fails
```
Check: Alembic migration logs
Common issues:
  1. Migration syntax error → Fix migration file
  2. AWS credentials expired → Re-authenticate
  3. Database permission issue → Check IAM roles
  4. ECR/ECS issue → Check AWS console

Fix:
  1. Fix the issue locally
  2. Commit new changes
  3. Push again (workflow re-triggers)
```

### If Firebase Deploy Fails
```
Check: Firebase logs
Common issues:
  1. Firebase token expired
  2. Project ID mismatch
  3. Build failed

Fix:
  1. Check secrets in GitHub
  2. Re-authenticate Firebase
  3. Push again
```

---

## Live Dashboard

Monitor all workflows in real-time:

**GitHub Actions:** https://github.com/Jnpaul1984/Cricksy_Scorer/actions

Each workflow shows:
- Status (running 🟡, passed ✅, failed ❌)
- Time elapsed
- Detailed logs for each step

---

## Post-Deployment Verification

Once all workflows pass, verify:

### Backend Services
```bash
# Check if new tables exist
curl -X GET http://api.yourdomain.com/api/players
# Should return: {"detail": "Unauthorized"} or player list
```

### API Endpoints
```bash
# Create a player
curl -X POST http://api.yourdomain.com/api/players \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Player", "jersey_number": 7}'

# Get players
curl -X GET http://api.yourdomain.com/api/players

# Get deliveries
curl -X GET http://api.yourdomain.com/api/games/1/deliveries
```

### Database
```bash
# Query new tables directly (if you have DB access)
SELECT COUNT(*) FROM players;
SELECT COUNT(*) FROM deliveries;
SELECT COUNT(*) FROM batting_scorecards;
SELECT COUNT(*) FROM bowling_scorecards;
```

---

## Timeline Estimate

```
Push → All workflows complete: ~1 hour total

Breakdown:
  Lint workflow:           ~5 min
  CI workflow:             ~20 min
  Deploy Backend:          ~30 min (includes Alembic migration)
  Deploy Frontend:         ~10 min

Total: ~1 hour
```

---

## Key Commit Info to Reference

**Commit Hash:** `7c75ab2`

**What changed:**
- ✅ Added scorecard_service.py (500+ lines)
- ✅ Added scorecards.py routes (250+ lines)
- ✅ Added alembic migration
- ✅ Updated schemas.py with Pydantic schemas
- ✅ Fixed pressure_analysis.py bugs

**Total Lines Added:** ~996

---

## Emergency Rollback

If something critical breaks and you need to rollback:

```bash
# Revert the commit
git revert 7c75ab2
git push origin main

# OR reset to previous commit (be careful!)
git reset --hard 1e2d60c
git push origin main -f
```

This will:
1. Revert all changes
2. Trigger new workflows with old code
3. Roll back deploy automatically

---

## Success! 🎉

All code is committed and pushed. GitHub Actions will now:
1. Validate all lint/format
2. Run tests
3. Deploy backend with new database tables
4. Deploy frontend
5. **Dual-write scorecard system is LIVE**

Check back in 1 hour to verify all workflows pass!
