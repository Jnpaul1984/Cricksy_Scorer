# Phase 5E Manual QA - Historical Import Rollback + Cleanup

## Scope Guardrails (must remain true)
- [ ] No delivery-level import is performed.
- [ ] No Player rows are created from historical JSON.
- [ ] No Team rows are created from historical JSON.
- [ ] Live or in-progress matches are never mutated by historical import apply/rollback.

## Environment Setup
- [ ] Start backend with test/staging-safe credentials.
- [ ] Confirm database is reachable.
- [ ] Confirm analyst/scorer account can access historical import endpoints.

## 1) Dry-Run Preview Flow
- [ ] Submit `POST /api/historical-import/json/dry-run` with valid historical JSON (`record_preview=false`).
- [ ] Verify response returns preview metadata, innings summary, duplicate detection, and no errors for valid input.
- [ ] Verify `no_persistence=true` and `record_id=null`.

## 2) Record Preview Flow
- [ ] Submit dry-run again with `record_preview=true`.
- [ ] Verify `record_id` is returned.
- [ ] Verify `GET /api/historical-import/json/batches` includes the recorded batch with `is_finalized=false`.

## 3) Duplicate Detection Flow
- [ ] Re-submit identical payload and verify likely duplicate by source hash.
- [ ] Re-submit semantically equivalent payload (same match key, different JSON hash) and verify semantic duplicate signal.

## 4) Apply Flow
- [ ] Call `POST /api/historical-import/json/batches/{batch_id}/apply` with `{ "confirm": true }`.
- [ ] Verify apply response returns `status=applied`, `records_created=1`, and non-null `applied_game_id`.
- [ ] Verify batch now shows `is_finalized=true` and `applied_game_id` set.
- [ ] Verify created game is historical metadata only (no deliveries imported).

## 5) Analyst Workspace Visibility Check
- [ ] Confirm applied historical game appears in analyst-visible result/workspace views expected for completed matches.
- [ ] Confirm data appears as completed historical context, not as an active live scoring game.

## 6) Rollback/Cleanup Flow
- [ ] Call `POST /api/historical-import/json/batches/{batch_id}/rollback` with `{ "confirm": true }`.
- [ ] Verify rollback response returns `status=rolled_back`, `records_deleted=1`, and `rolled_back_game_id`.
- [ ] Verify batch returns to `is_finalized=false` and `applied_game_id=null`.
- [ ] Verify only the game created by that batch is deleted.

## 7) No Live Scoring Mutation Check
- [ ] Create or identify a live/in-progress match before rollback testing.
- [ ] Run historical apply + rollback flow on a separate batch.
- [ ] Verify live/in-progress match still exists and remains unchanged.

## 8) Database Sanity Checks
- [ ] Verify `HistoricalImportBatch` row still exists after rollback (audit preserved).
- [ ] Verify `Game` count decreases by exactly one for rollback target only.
- [ ] Verify `Delivery`, `Player`, and `Team` row counts are unchanged by apply+rollback roundtrip.

## 9) Failure / Invalid Batch Checks
- [ ] Rollback with `{ "confirm": false }` returns validation error.
- [ ] Rollback of unknown batch id returns not found.
- [ ] Rollback of non-finalized batch is rejected.
- [ ] Rollback is rejected when `applied_game_id` is missing or game metadata is unsafe.

## Pass / Fail Sign-off
- [ ] PASS - all checks above completed successfully.
- [ ] FAIL - one or more checks failed; attach logs, batch ids, and reproduction steps.
- Tester name:
- Date:
- Environment:
