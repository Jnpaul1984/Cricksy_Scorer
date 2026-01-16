# Backend Deployment Protocol

**Purpose**: Prevent CI/deployment failures by ensuring all changes pass rigorous local validation before pushing to `main` branch.

## ⚠️ CRITICAL RULE ⚠️

**YOU MUST RUN LOCAL VALIDATION BEFORE EVERY COMMIT/PUSH TO MAIN**

This is NOT optional. Running tests in CI after push wastes time and pollutes git history with fix commits. Local validation catches issues before they reach CI.

## Mandatory Pre-Push Checklist

### 1. Run Local CI Validation (ALWAYS REQUIRED)

**Run these commands BEFORE every `git push`:**

```powershell
# Set environment variables for in-memory DB mode
$env:CRICKSY_IN_MEMORY_DB = "1"
$env:DATABASE_URL = "sqlite+aiosqlite:///:memory:?cache=shared"
$env:PYTHONPATH = "C:\Users\Hp\Cricksy_Scorer"

# Backend validation
cd C:\Users\Hp\Cricksy_Scorer\backend

# Step 1: Ruff lint (BLOCKING - must pass)
python -m ruff check .
# MUST PASS: "All checks passed!"
# IF FAILS: Run `python -m ruff check --fix --unsafe-fixes .` then re-check

# Step 2: Ruff format (BLOCKING - must pass)
python -m ruff format --check .
# MUST PASS: "X files already formatted"
# IF FAILS: Run `python -m ruff format .` then re-check

# Step 3: MyPy type-check (BLOCKING - must pass)
python -m mypy --config-file pyproject.toml --explicit-package-bases .
# MUST PASS: "Success: no issues found in X source files"

# Step 4: Run pytest (CRITICAL - must pass, skip only if cv2 unavailable locally)
cd C:\Users\Hp\Cricksy_Scorer
python -m pytest backend/tests/ -v
# MUST PASS: "X passed" with 0 failures
# NOTE: If cv2 missing locally, tests will fail - in this case, ensure Steps 1-3 pass
#       and verify your test additions follow patterns in DEPLOY_BACKEND_PROTOCOL
```

**If ANY step fails, DO NOT PUSH. Fix the issue first, then re-run all checks.**

### 1b. Quick Validation (For Small Changes)

For trivial changes (docs, comments only), minimum validation:

```powershell
# Minimum checks (still required)
cd backend
python -m ruff check .
python -m ruff format --check .
```

### 2. Test Creation Guidelines

**CRITICAL**: When adding new tests that create game instances:

#### ✅ DO:
- Use `async_client.post("/games", json={...})` to create games via API
- Include minimum 2 players per team in `players_a` and `players_b`
- Extract game_id from response: `game_id = game_data.get("id") or game_data.get("gid") or game_data.get("game", {}).get("id")`
- Score deliveries via `async_client.post(f"/games/{game_id}/deliveries", json={...})`
- Extract delivery IDs from response snapshots, not hardcoded values

#### ❌ DON'T:
- Use `crud.create_game(db_session, schema)` directly (incompatible with in-memory CRUD)
- Create games with only 1 player per team (violates GameCreate schema validation)
- Hardcode delivery IDs (use IDs from API responses)
- Use `games_impl.append_delivery_and_persist_impl()` (bypasses API validation)

#### Example Pattern:
```python
@pytest.mark.asyncio
async def test_my_feature(async_client, db_session):
    # Create game via API
    create_response = await async_client.post(
        "/games",
        json={
            "match_type": "limited",
            "overs_limit": 20,
            "team_a_name": "Team A",
            "team_b_name": "Team B",
            "players_a": ["bat1", "bat2"],  # Min 2 players
            "players_b": ["bowl1", "bowl2"],  # Min 2 players
            "toss_winner_team": "Team A",
            "decision": "bat",
        },
    )
    assert create_response.status_code in (200, 201)
    game_data = create_response.json()
    game_id = game_data.get("id") or game_data.get("gid") or game_data.get("game", {}).get("id")

    # Score delivery via API
    score_response = await async_client.post(
        f"/games/{game_id}/deliveries",
        json={
            "striker_id": "bat1",
            "non_striker_id": "bat2",
            "bowler_id": "bowl1",
            "runs_scored": 4,  # Legal ball: use runs_scored
            "runs_off_bat": 0,  # Must be 0 for legal balls
            "extra": None,
            "is_wicket": False,
        },
    )
    assert score_response.status_code == 200
    snapshot = score_response.json()
    delivery_id = snapshot["deliveries"][0]["id"]  # Extract from response

    # Use API for all operations
    patch_response = await async_client.patch(
        f"/games/{game_id}/deliveries/{delivery_id}",
        json={"runs_scored": 6},
    )
    assert patch_response.status_code == 200
```

### 3. Pre-Commit Auto-Fixes

If ruff reports fixable errors:
```powershell
python -m ruff check --fix --unsafe-fixes .
python -m ruff format .
```

Then re-run validation checks to ensure fixes didn't break anything.

### 4. Commit Message Format

```
<type>: <short description>

<optional body explaining why/what changed>
```

Types:
- `fix:` - Bug fixes (CI failures, runtime errors)
- `feat:` - New features (new endpoints, functionality)
- `chore:` - Maintenance (deps, config, docs)
- `test:` - Test-only changes
- `refactor:` - Code restructuring without behavior change

### 5. Push to Main Workflow

```powershell
# 1. Ensure all local validation passes
# 2. Stage changes
git add <files>

# 3. Commit with descriptive message
git commit -m "fix: delivery correction tests use API instead of direct CRUD"

# 4. Push to main
git push origin main

# 5. Monitor GitHub Actions workflow
# Visit: https://github.com/Jnpaul1984/Cricksy_Scorer/actions
# Ensure "Run pytest -v" and "Deploy Backend" workflows pass
```

### 6. Rollback Procedure (If CI Fails After Push)

```powershell
# Option 1: Fix forward (preferred)
# Fix the issue locally, validate, commit, push

# Option 2: Revert commit
git revert HEAD
git push origin main

# Option 3: Force rollback (use with caution)
git reset --hard HEAD~1
git push origin main --force
```

## Common CI Failure Patterns & Solutions

### Pattern 1: Schema Validation Errors
**Error**: `pydantic_core._pydantic_core.ValidationError: List should have at least 2 items`

**Cause**: Test creates game with only 1 player per team

**Fix**: Ensure `players_a` and `players_b` each have ≥2 players

### Pattern 2: InMemoryCRUD Signature Mismatch
**Error**: `InMemoryCrudRepository.create_game() takes 2 positional arguments but 3 were given`

**Cause**: Test calls `crud.create_game(db_session, schema)` instead of using API

**Fix**: Use `async_client.post("/games", json={...})` to create games

### Pattern 3: Ruff F841 Unused Variables
**Error**: `F841 Local variable 'x' is assigned to but never used`

**Fix**: Either use the variable or remove the assignment

### Pattern 4: MyPy Type Errors
**Error**: `Incompatible types in assignment`

**Cause**: Type mismatch (e.g., `Mapping` vs `dict`)

**Fix**: Use explicit type casts: `cast(dict[str, Any], value)` or change iteration pattern

### Pattern 5: Import Order
**Error**: `I001 Import block is un-sorted or un-formatted`

**Fix**: Run `python -m ruff check --fix .` to auto-sort imports

### Pattern 6: API Schema Validation (422 Unprocessable Entity)
**Error**: `assert 422 == 200` when calling `POST /games/{game_id}/deliveries`

**Cause**: Payload doesn't match `ScoreDelivery` Pydantic schema validator rules

**Schema Rules** (`backend/sql_app/schemas.py:ScoreDelivery`):
- **No-ball (nb)**: MUST provide `runs_off_bat`, `runs_scored` auto-set to None
- **Wide/Bye/Leg-bye (wd/b/lb)**: MUST provide `runs_scored`, `runs_off_bat` must be 0 or None
- **Legal ball (extra=None)**: Use `runs_scored`, `runs_off_bat` must be 0 or None

**Fix Examples**:
```python
# ✅ CORRECT: Wide delivery
{
    "striker_id": "bat1",
    "non_striker_id": "bat2",
    "bowler_id": "bowl1",
    "runs_scored": 1,  # Required for extras
    "runs_off_bat": 0,  # Must be 0 for non-nb extras
    "extra": "wd",
    "is_wicket": False,
}

# ✅ CORRECT: Legal 4 runs
{
    "striker_id": "bat1",
    "non_striker_id": "bat2",
    "bowler_id": "bowl1",
    "runs_scored": 4,  # Required for legal balls
    "runs_off_bat": 0,  # Must be 0 for legal balls
    "extra": None,
    "is_wicket": False,
}

# ✅ CORRECT: No-ball + 4 runs
{
    "striker_id": "bat1",
    "non_striker_id": "bat2",
    "bowler_id": "bowl1",
    "runs_off_bat": 4,  # Required for no-balls
    "extra": "nb",
    "is_wicket": False,
    # runs_scored auto-calculated as 1 + runs_off_bat
}

# ❌ WRONG: Missing runs_off_bat for wide
{
    "runs_scored": 1,
    "extra": "wd",  # Missing runs_off_bat field
}

# ❌ WRONG: Using runs_scored for no-ball
{
    "runs_scored": 5,  # Should use runs_off_bat
    "extra": "nb",
}
```

**Quick Reference**:
| Extra Type | Required Field | Other Field |
|------------|---------------|-------------|
| `None` (legal) | `runs_scored` | `runs_off_bat: 0` |
| `"wd"`, `"b"`, `"lb"` | `runs_scored` | `runs_off_bat: 0` |
| `"nb"` | `runs_off_bat` | `runs_scored: None` (auto) |

## Deployment Workflow (GitHub Actions)

The `deploy-backend.yml` workflow runs these steps:

1. **Test Backend (Postgres)**: Runs full pytest suite with PostgreSQL service
2. **Build and Scan ECR Image**: Builds Docker image, pushes to ECR, scans for vulnerabilities
3. **Deploy**: Runs migrations, updates ECS service, deploys worker service

**Blocking Conditions**:
- Any pytest failure stops deployment
- HIGH/CRITICAL vulnerabilities in ECR scan stops deployment
- Migration task exit code ≠ 0 stops deployment

## Emergency Hotfix Procedure

For critical production fixes that need immediate deployment:

```powershell
# 1. Create hotfix branch
git checkout -b hotfix/critical-issue main

# 2. Make minimal fix
# ... edit files ...

# 3. Run FULL local validation (no shortcuts)
python -m ruff check .
python -m mypy --config-file pyproject.toml --explicit-package-bases .
pytest -v

# 4. Commit with clear description
git commit -m "hotfix: fix critical production issue XYZ"

# 5. Push to main (or create PR for review if time allows)
git checkout main
git merge hotfix/critical-issue --no-ff
git push origin main

# 6. Monitor deployment
# Watch GitHub Actions and ECS service health
```

## Maintenance

Review this protocol quarterly and update based on:
- New CI tools/checks added to workflow
- Recurring failure patterns
- Team feedback on friction points

**Last Updated**: January 15, 2026
**Owner**: Development Team
**Related Docs**: `.mcp/CI_CONSISTENCY_ENGINEER.md`, `.github/workflows/deploy-backend.yml`
