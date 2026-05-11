# Phase 5H - Historical JSON Real-Dataset Validation + Analyst Workspace QA

## Fixture list and format notes

1. `backend/tests/simulated_t20_match.json`
   - Type: sanitized structured historical-style fixture already used in Phase 5D/5F tests.
   - Shape: `cricksy_fixture` (`matchType`, `teams`, `innings[].balls`).
2. `backend/tests/sanitized_cricsheet_t20.json`
   - Type: sanitized real-structure fixture modeled on Cricsheet JSON conventions.
   - Shape: `cricsheet_json` (`meta`, `info`, `innings[].<team>.overs[].deliveries[]`).

No private, licensed, or sensitive match data was committed.

## Dry-run results

- `simulated_t20_match.json`: `status=valid`, `detected_format=cricksy_fixture`.
- `sanitized_cricsheet_t20.json`: `status=valid`, `detected_format=cricsheet_json`.
- Unsupported-shape control payload: `status=unsupported` with `UNSUPPORTED_FORMAT`.

## Apply results

- For both sanitized fixtures: dry-run with `record_preview=true` returns `record_id`, then `/apply` succeeds with `status=applied`, `records_created=1`, and `is_finalized=true`.
- Imported games remain marked as historical (`phases.historical_import.is_historical=true`).

## Delivery import results

- For both sanitized fixtures: `/apply-deliveries?confirm=true` succeeds.
- `simulated_t20_match.json`: delivery import count matches dry-run preview count.
- `sanitized_cricsheet_t20.json`: over/delivery format normalizes correctly and imports 24 deliveries.
- Totals validation returns `ok`/`warning` only for valid fixtures.

## Analyst Workspace visibility results

- For both fixtures:
  - `/analytics/matches` includes the imported game.
  - Match list marks source as historical import.
  - `/analytics/matches/{id}/case-study` returns populated innings/phases/key players.

## Analyst Workspace useful-data checks

- Case-study responses include non-zero innings and real computed phases when deliveries are imported.
- Real match IDs are used (no mock `m1`/`m2` fallback IDs).
- Existing tests still enforce real rows or honest empty-state behavior and no fake fallback rows.

## Duplicate detection checks

- Existing hash duplicate and semantic duplicate tests remain passing.
- Repeated fixture submissions still return `likely_duplicate` where expected.

## Rollback checks

- Existing rollback tests remain passing:
  - rollback requires confirm,
  - rollback refuses unsafe/non-finalized cases,
  - rollback deletes only the applied historical game,
  - rollback resets batch finalize markers,
  - rollback keeps non-game tables safe.

## Known unsupported cases

- Unknown/malformed shapes still return clear dry-run errors (`UNSUPPORTED_FORMAT`, `MISSING_INNINGS`, etc.).
- Dry-run unsupported flow does not create game rows and does not persist batches unless `record_preview=true`.

## Recommended Phase 5I follow-up

1. Add explicit support for additional real-world Cricsheet edge variants (if encountered), including alternate delivery-key encodings.
2. Expand fixture catalog with more sanitized domestic/international variants while keeping CI fixture size small.
3. Continue hardening validation messages with fixture-path context for faster analyst/operator triage.
