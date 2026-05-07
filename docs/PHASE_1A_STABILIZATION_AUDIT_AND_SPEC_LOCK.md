# PHASE 1A — Existing App Stabilization Audit + Spec Lock

**Repository:** `Jnpaul1984/Cricksy_Scorer`  
**Branch:** `agent/phase-1a-stabilization-audit-spec-lock`  
**Checklist source:** `docs/CRICKSY_MASTER_EXECUTION_CHECKLIST.md`  
**Baseline audit source:** `docs/PHASE_0_REPO_BASELINE_AUDIT.md`  
**Audit date:** 2026-05-07  
**Scope:** Docs-only pre-phase audit and spec lock. No app code modified.

---

## 1. Current Health Endpoint Audit

### Endpoints Discovered

| Route | File | Behavior |
|-------|------|----------|
| `GET /health` | `backend/routes/health.py` | Returns `{"status": "ok"}` (no auth, no DB) |
| `GET /healthz` | `backend/routes/health.py` | Returns `{"status": "ok"}` (alias) |
| `GET /health/cors-config` | `backend/routes/health.py` | Returns `{"cors_origins": [...]}` (debug, no auth) |
| `GET /health/db` | `backend/routes/health.py` | Async DB ping + table list (uses `get_db`) |
| `GET /health/admin` | `backend/routes/health.py` | Shows first user email + hash prefix + alembic version (debug) |

### Test Coverage

- `backend/tests/test_health.py` — unit test using `TestClient`, accepts `{"status": "ok"}` or `"ok"` text
- `backend/tests/ci_smoke/test_health.py` — retry-loop smoke test against a live server (`BASE_URL`)
- `backend/tests/EXAMPLE_test_organization.py` — example smoke/e2e patterns (not run in fast CI)

### Contract (locked)

- `GET /health` **must** return HTTP 200 with JSON `{"status": "ok"}`.
- No authentication required.
- Response must be synchronous (no DB dependency).

### Risks

- `GET /health/admin` exposes password hash prefix and user email — debug endpoint, no auth guard. Risk is low but should be noted; do not add auth in Phase 1.
- `GET /health/db` may return `{"status": "error", ...}` if DB is unreachable; this is acceptable graceful degradation.

---

## 2. Current Results Endpoint Audit

### Endpoints Discovered

| Route | File | Method | Notes |
|-------|------|--------|-------|
| `POST /games/{game_id}/results` | `backend/routes/games_router.py` | Create/overwrite match result | Accepts `MatchResultRequest`; auto-computes method/margin/text if omitted |
| `GET /games/{game_id}/results` | `backend/routes/games_router.py` | Retrieve single game result | 404 if no result stored |
| `GET /games/results` | `backend/routes/games_router.py` | List all games with results | Returns list of dicts with `match_id`, `winner`, scores, etc. |

### Schema Contracts (from `backend/sql_app/schemas.py`)

**POST body** (`MatchResultRequest`):
```
match_id, team_a_score, team_b_score (optional), winner (optional),
winner_team_name (optional), method (optional), margin (optional), result_text (optional)
```

**GET response** (`MatchResult`):
```
match_id, winner_team_id (opt), winner_team_name (opt), method (opt),
margin (opt), result_text (opt), completed_at (opt)
```

**Listing item** (plain dict):
```
match_id, winner, team_a_score, team_b_score,
[optional: winner_team_id, winner_team_name, method, margin, result_text, completed_at]
```

### Auto-computation rules (locked)

- If `team_a_score > team_b_score`: method defaults to `by_runs`, `result_text` = `"<team_a> won by <margin> runs"`
- If `team_b_score > team_a_score`: method defaults to `by_runs`, `result_text` = `"<team_b> won by <margin> runs"` *(note: the POST body accepts only scores — not wickets remaining — so the backend cannot distinguish a wicket-chase win; pass `method="by wickets"` and `result_text` explicitly when recording a Team B chase win)*
- If `team_a_score == team_b_score`: method = `tie`, `margin = 0`, `result_text` = `"Match tied"`, no winner
- Explicit `winner_team_name`, `result_text`, `method`, `margin` in POST body **override** auto-computation

### Test Coverage

`backend/tests/test_results_endpoint.py` covers:
- `test_results_endpoint_with_valid_id` — GET after POST returns 200, `winner_team_name`, `result_text`
- `test_results_listing` — `GET /games/results` returns list including the posted game
- `test_auto_computed_result_team_a_wins` — margin text computed correctly
- `test_tie_result` — tie detection, `method == "tie"`, empty `winner_team_name`
- `test_no_result_manual_entry` — abandoned match override (`"Match abandoned due to rain"`)
- `test_manual_override_winner_and_text` — explicit `result_text` and `winner_team_name` preserved
- `test_finalize_blocks_future_deliveries` — finalizing game blocks delivery POSTs (400/409/422)

### Risks

- `game.result` is stored as a JSON string (`json.dumps`). If the game row exists but has `result = None`, `GET /games/{id}/results` returns 404. This is the current documented behavior — do not change.

---

## 3. Current Scoring Flow Audit

### Primary Route

`POST /games/{game_id}/deliveries` in `backend/routes/gameplay.py`

### Data Flow

```
Client POST /games/{game_id}/deliveries
    ↓
gameplay.add_delivery()
    ↓
_score_one() via scoring_service.score_one()
    ↓
GameState mutation (total_runs, overs, balls, batting/bowling scorecards)
    ↓
Persist updated game to DB (crud.update_game)
    ↓
build_snapshot() via snapshot_service.build_snapshot()
    ↓
emit_state_update(game_id, snap) via live_bus
    ↓
Socket.IO "state:update" event → all clients in game room
```

### Key Files

| File | Role |
|------|------|
| `backend/routes/gameplay.py` | REST handlers for deliveries, innings start/end, finalize, undo |
| `backend/services/scoring_service.py` | `score_one()` — per-ball mutation logic |
| `backend/domain/constants.py` | `CREDIT_BOWLER`, `INVALID_ON_NO_BALL`, `INVALID_ON_WIDE`, `norm_extra()` |
| `backend/services/snapshot_service.py` | `build_snapshot()` — assembles snapshot dict for live broadcast |
| `backend/services/live_bus.py` | `emit_state_update()` — broadcasts via Socket.IO |
| `backend/socket_handlers.py` | Socket.IO join/presence handlers |

### Scoring Rules (locked — must not change)

1. **Legal delivery**: not a wide (`wd`) and not a no-ball (`nb`)
2. **Balls count**: legal deliveries only. Wides and no-balls do not increment `balls_this_over`.
3. **Over completion**: 6 legal balls → `overs_completed += 1`, `balls_this_over = 0`, ends swap
4. **Strike rotation**: odd runs off bat → swap striker/non-striker; wides only swap on runs > 1 and odd
5. **Extras**: wide/bye/leg-bye add to `extra_runs`; no-ball adds 1 penalty to team total
6. **Wicket credit**: only assigned to bowler if dismissal type is in `CREDIT_BOWLER`; no credit on no-ball for `INVALID_ON_NO_BALL` types; no credit on wide for `INVALID_ON_WIDE` types
7. **Finalized game**: `POST /games/{id}/deliveries` blocked with 400/409/422 after finalize

### Delivery Payload Contract (locked)

```json
{
  "striker_id": "<uuid>",
  "non_striker_id": "<uuid>",
  "bowler_id": "<uuid>",
  "runs_scored": 0,
  "runs_off_bat": 0,
  "is_wicket": false,
  "extra": null,
  "dismissal_type": null,
  "dismissed_player_id": null
}
```

### Supporting Tests

- `backend/tests/test_scoring_integration.py` — full API flow tests (innings start, deliveries, snapshot checks, over completion, wickets)
- `backend/tests/test_core_scoring.py` — unit-style tests for `score_one()` + `emit_state_update()` side effects
- `backend/tests/test_wicket_counting.py` — wicket counting edge cases
- `backend/tests/integration/test_full_match_integration.py` — end-to-end full match via API

---

## 4. Current DLS Calculation/Test Audit

### Implementation Files

| File | Role |
|------|------|
| `backend/dls.py` | Main DLS engine: `compute_dls_target()`, `ResourceTable`, `DLSEnv`, helpers |
| `backend/services/dls_service.py` | Service wrapper: `resource_remaining()`, `calc_target()` |
| `backend/services/dls/__init__.py` | Package entry: `calculate_dls_target()`, `load_international_table()` |
| `backend/static/dls_20.json` | T20 resource table (JSON) |
| `backend/services/dls_tables/` | ICC official tables |

### Core Function Contract (locked)

```python
compute_dls_target(
    *,
    team1_score: int,
    team1_wickets_lost: int,
    team1_overs_left_at_end: float,
    format_overs: int,
    team2_wkts_lost_now: int,
    team2_overs_left_now: float,
) -> DLSComputation
```

Returns `DLSComputation(target, par_score, R1_total, R2_total, R2_used)`.

**Standard Edition formula (locked):**
- Fewer resources: `floor(S1 * R2 / R1) + 1`
- More resources: `S1 + floor((R2 - R1) * G50 / 100) + 1`
- Equal resources: `S1 + 1`
- Minimum target: `max(1, computed_target)`

**Extras counting (locked):**
- Wides (`wd`) and no-balls (`nb`) do **not** count as legal balls in `compute_state_from_ledger()`

### Test Coverage

`backend/tests/test_dls_calculations.py`:
- `TestResourceTable` — loads table, verifies resource decreases with overs/wickets, interpolation
- `TestDLSBasicCalculations` — no interruption, reduced overs, wickets effect
- `TestDLSRealisticScenarios` — T20 rain interruption, mid-innings interruption, ODI scenario
- `TestDLSEdgeCases` — zero overs, all wickets, very low score, very high score
- `TestDLSHelperFunctions` — `compute_state_from_ledger()`, `revised_target()`, partial resources
- `TestDLSResourceCalculations` — team 1/team 2 resource calculation helpers

`backend/tests/integration/test_dls_integration.py` — DLS via full API (create game, play overs, check snapshot DLS fields)

### Risks

- DLS table CSV/JSON files must remain in place; removing or corrupting them causes graceful degradation to simplified calculation with deterministic but less accurate results.
- `G` constant: 150.0 for T20, 245.0 for ODI; do not change.

---

## 5. Current Viewer/Snapshot Contract Audit

### Snapshot Endpoint

`GET /games/{game_id}/snapshot` → `backend/routes/gameplay.py:get_snapshot()`

Returns a snapshot dict built by `build_snapshot()` from `backend/services/snapshot_service.py`.

### Real-time Delivery

1. After every delivery/innings/finalize action, `emit_state_update(game_id, snap)` fires via `backend/services/live_bus.py`
2. Socket.IO event name: `"state:update"`
3. Payload: `{ "id": "<game_id>", "snapshot": <snapshot_dict> }`

### Frontend Handler

`frontend/src/stores/gameStore.ts`:
- `ServerEvents['state:update']` typed as `{ id: string; snapshot: ApiSnapshot | any }`
- `handleStateUpdate()` calls `normalizeServerSnapshot()` then updates `liveSnapshot`, `currentGame`, and `snapshot` refs
- Syncs `current_striker_id`, `current_non_striker_id`, `current_bowler_id` from snapshot keys

### Snapshot Key Contract (locked — frontend depends on these keys)

```
id, status, score.runs, score.wickets, score.overs,
current_striker_id, current_non_striker_id, current_bowler_id,
batsmen.striker, batsmen.non_striker, current_bowler,
batting_scorecard (dict), bowling_scorecard (dict),
pending_new_batter, pending_new_over,
is_game_over, result (obj/null),
team_a (obj), team_b (obj),
innings, overs_limit
```

### Socket.IO Room Protocol (locked)

- Clients join with event `"join"` and payload `{ game_id, role, name }`
- All in-room clients receive `"state:update"` after each scored delivery

### Risks

- Snapshot assembly in `build_snapshot()` depends on `GameState`-like ORM row attributes. Any ORM column rename is a snapshot-breaking change.
- Frontend trusts `snapshotRecord.current_striker_id` and `snapshotRecord.batsmen?.striker?.id` with fallback; removing either key breaks live UI.

---

## 6. Current Frontend Fake-Data Guard Audit

### Guard Script

`scripts/check-fake-data.js` — invoked via `npm run guard:fake-data` from `frontend/`

**Scans:** `frontend/src/**/*.vue`, `**/*.ts`, `**/*.js`  
**Excludes:** `**/*.spec.ts`, `**/*.test.ts`, `**/__tests__/**`

### ERROR-level Patterns (fail CI immediately)

| Pattern | Reason |
|---------|--------|
| `Math.random()` | Random data generation |
| Hardcoded country opponent arrays (India/Australia/etc. adjacent) | Hardcoded fixture data |
| `generateMatchData`, `generateManhattanData`, `generateMockFeed`, `generateScatterData`, `generateWormData` | Mock data generator functions |

### WARNING-level Patterns

| Pattern | Reason |
|---------|--------|
| Celebrity player names (Virat, Kohli, Dhoni, Bumrah, etc.) | Hardcoded player names |

### Current Status (from `FAKE_DATA_AUDIT_REPORT.md` and `FRONTEND_DATA_SOURCE_FORENSIC_AUDIT.md`)

- **Known remaining issue:** `frontend/src/components/ExportUI.vue` — `generateExportData()` contains hardcoded sample player rows (Player A, Player B, Player C with hardcoded stats). This function is not triggered by the ERROR patterns above but is a WARNING-level fake-data concern. It generates mock export data when the real data pipeline is unavailable.
- All other major fake-data generators removed (commit `e2a3265` removed mock feed generator from `FanFeedWidget.vue`).
- `DEFAULT_MODEL = "gemini-pro"` in LLM provider is a legitimate default, not fake data.
- `generatePrintContent()`, `generateAICommentary()`, `generateExportData()`, `generateCoachSuggestions()` — all confirmed as either API calls or export transforms (not random generators).

### Current Guard Result

The guard currently exits with `0` (pass) for the ERROR patterns. The ExportUI sample data does not match the ERROR regex patterns and only raises a WARNING. **Phase 1 must not introduce any new fake data.**

---

## 7. Current Backend/Frontend Validation Command Baseline

### Backend Commands

```bash
# Environment (required)
export CRICKSY_IN_MEMORY_DB=1
export DATABASE_URL="sqlite+aiosqlite:///:memory:?cache=shared"
export APP_SECRET_KEY="test-secret-key"
export PYTHONPATH="<repo-root>"

# Lint + type safety
ruff check .
ruff format --check .
cd backend && mypy --config-file pyproject.toml --explicit-package-bases .

# Security
pip-audit --requirement backend/requirements.txt
bandit -r backend -c backend/pyproject.toml -ll

# Fast tests (Phase 1 gate)
cd backend && pytest -q tests/test_health.py tests/test_results_endpoint.py

# Integration tests
cd backend && pytest tests/integration/ -v --tb=short --cov=. --cov-report=xml --cov-report=term

# DLS tests
cd backend && pytest tests/test_dls_calculations.py -v --tb=short
```

### Frontend Commands

```bash
cd frontend
npm ci
VITE_API_BASE=http://localhost:8000 npm run guard:fake-data
npm run type-check
npm run build-only
```

### CI Equivalent Local Gate

```bash
make ci   # Enforces Python 3.12.12 and Node 20.18.1 before lint/test steps
```

### CI Path-Ignore Reminder

`.github/workflows/ci.yml` ignores `**.md` and `docs/**` and `.mcp/**` changes. This Phase 1A PR is docs-only and CI may not run. The next code-change PR (Phase 1B) **must** pass all CI jobs.

---

## 8. Current Protected Files List for Phase 1 Stabilization

The following files must not be modified without an explicit audit + spec lock + regression test cycle:

### Hard-Protected (never touch in Phase 1 without explicit approval)

| File/Path | Reason |
|-----------|--------|
| `backend/alembic/versions/` | All migrations; do not edit deployed migrations |
| `backend/services/coach_plus_analysis.py` | Coach Pro Plus video analysis pipeline |
| `backend/services/pose_service.py` | MediaPipe pose inference service |
| `backend/workers/analysis_worker.py` | SQS-driven video analysis worker |
| `backend/scripts/run_video_analysis_worker.py` | Worker entry point |
| `frontend/src/services/coachPlusVideoService.ts` | Coach Pro Plus frontend service |
| `frontend/src/stores/coachPlusVideoStore.ts` | Coach Pro Plus Pinia store |
| `infra/terraform/` | All Terraform infrastructure |
| `.github/workflows/` | All CI/CD workflows |
| `backend/config/pricing.py` | Pricing/tier entitlement config |

### Scoring/DLS Core (audit first, spec lock before any edit)

| File/Path | Reason |
|-----------|--------|
| `backend/main.py` | App factory and legacy scoring helpers |
| `backend/services/scoring_service.py` | Per-ball scoring logic |
| `backend/domain/constants.py` | Cricket rules constants |
| `backend/dls.py` | DLS calculation engine |
| `backend/services/dls_service.py` | DLS service wrapper |
| `backend/services/dls/` | DLS package |
| `backend/static/dls_20.json` | T20 DLS resource table |
| `backend/services/dls_tables/` | ICC DLS tables |
| `backend/routes/gameplay.py` | Delivery/innings/finalize routes |
| `backend/routes/games_router.py` | Game CRUD + results routes |
| `backend/services/snapshot_service.py` | Snapshot builder |
| `backend/services/live_bus.py` | Socket.IO broadcast |
| `frontend/src/stores/gameStore.ts` | Central game state + socket handlers |

### Test Files (must not degrade)

| File/Path | Reason |
|-----------|--------|
| `backend/tests/test_health.py` | Health endpoint contract |
| `backend/tests/test_results_endpoint.py` | Results endpoint contract |
| `backend/tests/test_dls_calculations.py` | DLS calculation contract |
| `backend/tests/integration/` | Full API integration tests |
| `backend/tests/test_scoring_integration.py` | Scoring flow contract |
| `backend/tests/test_core_scoring.py` | Core scoring unit tests |
| `backend/tests/test_live_bus.py` | Live bus / state:update contract |
| `scripts/check-fake-data.js` | Fake-data guard script |

---

## 9. Existing Behavior That Must Not Change

The following behaviors are locked as the stability baseline for Phase 1 and all subsequent phases:

### Health

1. `GET /health` returns HTTP 200 + `{"status": "ok"}`, no auth, no DB, synchronous.
2. `/healthz` is a valid alias returning the same response.

### Scoring

3. Legal deliveries are counted toward `balls_this_over`; wides and no-balls are not.
4. 6 legal balls completes an over: `overs_completed` increments, `balls_this_over` resets to 0, ends swap occurs.
5. Strike rotates on odd runs off bat; wide swaps only on runs > 1 and odd.
6. Wicket credit assigned to bowler only for dismissal types in `CREDIT_BOWLER`; no credit on no-ball `INVALID_ON_NO_BALL`; no credit on wide `INVALID_ON_WIDE`.
7. `POST /games/{id}/deliveries` on a finalized game must return 400/409/422.
8. `score_one()` input/output dict schema must remain stable (keys: `over_number`, `ball_number`, `bowler_id`, `striker_id`, `non_striker_id`, `runs_off_bat`, `extra_type`, `extra_runs`, `runs_scored`, `is_extra`, `is_wicket`, `dismissal_type`, `dismissed_player_id`, `commentary`, `fielder_id`).

### Results

9. `POST /games/{id}/results` auto-computes method/margin/result_text when omitted.
10. `GET /games/{id}/results` returns 404 if no result is stored.
11. `GET /games/results` returns a list of all games with stored results.
12. Explicit `winner_team_name`, `result_text`, `method`, `margin` in POST body override auto-computation.
13. Tie detection: equal scores → method = `"tie"`, margin = 0, empty winner.

### DLS

14. `compute_dls_target()` Standard Edition formula: fewer/equal/more resources logic as documented in Section 4.
15. Wides and no-balls do not count as legal balls in `compute_state_from_ledger()`.
16. DLS minimum target is always `max(1, computed)`.
17. T20 G constant = 150.0, ODI G constant = 245.0.

### Viewer/Snapshot

18. `"state:update"` Socket.IO event fires after every `score_one()` cycle.
19. Snapshot keys `current_striker_id`, `current_non_striker_id`, `current_bowler_id` must be present and accurate.
20. `GET /games/{id}/snapshot` returns the same snapshot dict as the live broadcast.

### Fake-Data Guard

21. `npm run guard:fake-data` must exit 0 (no ERROR-level violations) on every frontend code change.
22. No `Math.random()` in `frontend/src/` production code.
23. No celebrity player names as hardcoded strings in production frontend code.

---

## 10. Proposed Phase 1 Stabilization Spec Lock

### Objective

Add missing test coverage and harden the existing app behavior without changing product identity or architecture.

### Strict Scope

Phase 1B (the implementation slice following this audit) is limited to:

- **Adding** targeted regression tests for any currently uncovered scoring edge cases identified in this audit.
- **Adding** targeted regression tests for snapshot key contract (if not already covered).
- **Fixing** any confirmed silent bugs in existing test coverage (e.g., incorrect assertions that do not actually test the described behavior).
- **Not** changing scoring logic, DLS logic, or API contracts.
- **Not** changing frontend components.
- **Not** changing database models or running migrations.

### Product Behavior

No product behavior changes in Phase 1. The scorer, viewer, DLS, and results flows must work identically before and after any Phase 1 commits.

### API Changes

None permitted in Phase 1.

### DB/Schema Changes

None permitted in Phase 1. No new Alembic migrations.

### Frontend Behavior

None permitted in Phase 1, except documentation updates.

### Permissions/RBAC Behavior

No changes.

### Feature Flags

No changes.

---

## 11. Exact Allowed Files/Folders for the Next Implementation Slice (Phase 1B)

The following files and folders **may** be modified in Phase 1B:

```
docs/
    PHASE_1A_STABILIZATION_AUDIT_AND_SPEC_LOCK.md   ← this file (minor additions only)

backend/tests/
    test_health.py                    ← may add test cases
    test_results_endpoint.py          ← may add test cases
    test_dls_calculations.py          ← may add test cases
    test_core_scoring.py              ← may add test cases
    test_live_bus.py                  ← may add test cases
    test_scoring_integration.py       ← may add test cases
    integration/
        test_dls_integration.py       ← may add test cases
        test_full_match_integration.py ← may add test cases
        test_edge_cases.py            ← may add test cases
```

Adding new test files under `backend/tests/` is permitted if they follow the existing `conftest.py` fixture pattern and do not require new migrations.

---

## 12. Exact Forbidden/Protected Files/Folders Unless Explicitly Approved

The following files and folders **must not be modified** in Phase 1B without a new spec lock:

```
backend/main.py
backend/app.py
backend/routes/gameplay.py
backend/routes/games_router.py
backend/routes/games.py
backend/routes/health.py
backend/services/scoring_service.py
backend/services/snapshot_service.py
backend/services/live_bus.py
backend/domain/constants.py
backend/dls.py
backend/services/dls_service.py
backend/services/dls/
backend/static/dls_20.json
backend/services/dls_tables/
backend/sql_app/models.py
backend/sql_app/schemas.py
backend/sql_app/crud.py
backend/sql_app/database.py
backend/alembic/versions/
backend/alembic.ini
backend/services/coach_plus_analysis.py
backend/services/pose_service.py
backend/services/sqs_service.py
backend/workers/analysis_worker.py
backend/scripts/run_video_analysis_worker.py
backend/mediapipe_init.py
backend/config/pricing.py
frontend/                             ← entire frontend tree
infra/                                ← entire infra tree
.github/workflows/                    ← all CI/CD workflows
scripts/check-fake-data.js            ← fake-data guard (do not weaken)
docker-compose*.yml
Dockerfile
pyproject.toml
ruff.toml
requirements.txt
backend/requirements.txt
```

---

## 13. Required Tests for the Next Implementation Slice (Phase 1B)

All existing tests in the following files must continue to pass:

```bash
cd backend && pytest -q tests/test_health.py tests/test_results_endpoint.py
cd backend && pytest tests/test_dls_calculations.py -v --tb=short
cd backend && pytest tests/integration/ -v --tb=short
```

Additionally, Phase 1B must achieve test coverage for any gap identified in this audit. Specifically, the following behaviors should be verified in `backend/tests/`:

1. **Health — `/healthz` alias** responds HTTP 200 + `{"status": "ok"}` (currently not tested in `test_health.py`).
2. **Snapshot key contract** — `GET /games/{id}/snapshot` returns `current_striker_id`, `current_non_striker_id`, `current_bowler_id` after at least one delivery.
3. **`state:update` event payload** — after `score_one()`, the emitted snapshot contains `current_striker_id` (covered in `test_live_bus.py` but worth confirming stability).
4. **DLS: wides/no-balls exclusion** — already covered; verify no regression.
5. **Finalized game blocks deliveries** — already in `test_results_endpoint.py`; keep passing.

These tests must be added in a backwards-compatible way without altering existing assertions.

---

## 14. Rollback Plan for Phase 1 Implementation Work

### Git-Level Rollback

1. Every Phase 1B PR is merged from `agent/phase-1b-*` into `main`.
2. If any test regression or runtime error is introduced, revert the PR merge commit:
   ```bash
   git revert <merge-commit-sha> --mainline 1
   git push origin main
   ```
3. This is safe because Phase 1B contains only test additions — no DB migrations, no API changes.

### CI Checkpoint

- All Phase 1B PRs must pass the full CI suite before merge, including:
  - `pre-commit`
  - `lint` (ruff + mypy)
  - `security` (pip-audit + bandit)
  - `backend-tests` (fast + integration + DLS)
  - `frontend-build` (guard + type-check + build-only)

### Deployment Impact

- Phase 1B is test-only; no backend deployment needed.
- No Alembic migrations; no ECS task re-registration.
- Frontend deployment not triggered (no `frontend/` changes).

### If Test Additions Reveal Real Bugs

- Do **not** fix the bug in the same PR as the test.
- Open a new issue describing the bug.
- Create a separate `agent/phase-1b-fix-<description>` branch with its own spec lock.

---

## 15. Recommended Smallest Safe Phase 1B Implementation Issue

### Title

**Phase 1B: Regression Test Hardening for Health, Results, Snapshot, and DLS Contracts**

### Objective

Add targeted regression tests for the gaps identified in the Phase 1A audit, without changing any app code.

### Exact Files to Change

```
backend/tests/test_health.py              ← add /healthz alias test
backend/tests/test_scoring_integration.py ← add snapshot key contract test
backend/tests/test_live_bus.py            ← confirm state:update snapshot key test
backend/tests/test_dls_calculations.py    ← add any coverage gaps found
```

### Work Defined

1. Add test `test_healthz` in `test_health.py`:
   ```python
   def test_healthz(client: TestClient):
       resp = client.get("/healthz")
       assert resp.status_code == 200
       assert resp.json().get("status") == "ok"
   ```

2. Add test in `test_scoring_integration.py` to assert snapshot returned from `GET /games/{id}/snapshot` contains `current_striker_id`, `current_non_striker_id`, and `current_bowler_id` after the first delivery.

3. Review `test_live_bus.py` to confirm `state:update` payload includes `current_striker_id` and `current_bowler_id`; add assertion if missing.

4. Run full CI gate before PR submission:
   ```bash
   cd backend && pytest -q tests/test_health.py tests/test_results_endpoint.py
   cd backend && pytest tests/test_dls_calculations.py -v --tb=short
   cd backend && pytest tests/integration/ -v --tb=short
   cd frontend && npm run guard:fake-data
   cd frontend && npm run type-check
   cd frontend && npm run build-only
   ```

### Gates

- No scoring regression
- No DLS regression
- No fake data introduction
- No broken frontend build
- All existing test assertions pass
- New test assertions pass

### Risks

- Low: test-only changes with no logic impact
- Snapshot key test may require adjusting the game creation fixture to set openers before delivering; use existing conftest helpers

### Branch Name

`agent/phase-1b-regression-test-hardening`

---

## Appendix A: CI Validation Status for This PR

This is a docs-only PR. Per `ci.yml` path-ignore rules, CI may skip on `docs/**` changes. No backend or frontend code was modified.

**Files changed:**
- `docs/PHASE_1A_STABILIZATION_AUDIT_AND_SPEC_LOCK.md` (new file)

**Confirmed not modified:**
- `backend/` — no changes
- `frontend/` — no changes
- `infra/` — no changes
- `.github/workflows/` — no changes
- `backend/alembic/versions/` — no changes
- Scoring code — no changes
- DLS code — no changes
- Deployment files — no changes

**Validation commands run (informational only, not blocking this PR):**

```
cd backend && pytest -q tests/test_health.py tests/test_results_endpoint.py
cd backend && pytest tests/test_dls_calculations.py -v --tb=short
cd frontend && npm run guard:fake-data
cd frontend && npm run type-check
cd frontend && npm run build-only
```

Actual validation run status is reported in the PR description.

---

## Appendix B: Known Risks and Unknowns

| Risk | Severity | Mitigation |
|------|----------|------------|
| `GET /health/admin` exposes user email + hash prefix with no auth | Low | Document as known debug endpoint; do not add auth in Phase 1 |
| `ExportUI.vue` hardcoded sample export rows | Low | Does not fail ERROR-level guard; document as WARNING; clean up in Phase 2 |
| DLS graceful degradation when table files missing | Medium | CSV/JSON tables must stay in place; verify on deploy |
| Shallow git clone may miss full commit history | Low | Use `git fetch --unshallow origin` before any merge/rebase |
| `ci.yml` docs path-ignore means this PR may not trigger CI | Info | Next code-change PR (Phase 1B) must pass full CI |
| `make ci` requires exact Python 3.12.12 and Node 20.18.1 | Medium | Ensure developer environments match; CI uses pinned versions |
| `windows-selector-event-loop-policy` used for asyncpg compat | Low | Keep `asyncio_mode` setting in pytest.ini; do not change event loop policy |

---

*End of Phase 1A Stabilization Audit and Spec Lock.*
