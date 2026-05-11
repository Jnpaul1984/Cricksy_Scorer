# Phase 5J - Historical Import Metadata Accuracy and Registry Readiness

## Bug summary from manual QA

Manual Analyst Workspace QA found three data-correctness issues in imported Cricsheet-style matches:
- second innings were sometimes shown as the first batting side again;
- completed historical matches could show `In progress` because Cricsheet outcome metadata was not converted into a stored result string;
- overs could be displayed from raw delivery counts instead of legal-ball counts, so wides/no-balls could produce invalid cricket-over displays.

The same QA also confirmed that venue, competition, season, match number, and date metadata are needed for future grouping and venue analysis.

## Audit findings

### Historical import preview parser
- File: `backend/services/historical_import_preview.py`
- Dry-run already normalized Cricsheet single-key innings wrappers and derived innings previews.
- Team extraction sorted names alphabetically, which was safe for duplicate keys but not safe for preserving source team order.
- Result preview only read `result.summary` and did not derive a result from `info.outcome`.
- Venue/date were already read, but event name, season, match number, and the full dates list were not preserved.

### Historical import apply service
- File: `backend/services/historical_import_apply_service.py`
- Apply already created historical `Game` rows with `status=completed` and stored metadata inside `Game.phases["historical_import"]`.
- Only venue/date/hash/source fields were persisted there.
- Team shell creation relied on `teams_preview`, so preserving source team order mattered.

### Historical import delivery service
- File: `backend/services/historical_import_delivery_service.py`
- Delivery import normalized Cricsheet overs/deliveries but treated every delivery as legal for totals/overs.
- Second innings totals were persisted into `game.total_runs`, `game.total_wickets`, `game.overs_completed`, and `game.balls_this_over`.
- `game.batting_team_name` was not updated to the second-innings batting team after delivery import.

### Analyst Workspace match list/detail/case-study builders
- Files: `backend/routes/analytics_case_study.py`, `backend/routes/analyst_pro.py`, `backend/services/analytics_case_study.py`
- Match list already exposed historical venue and source markers.
- Analyst detail built innings from `first_inning_summary` plus live-state fields and could miss or mislabel the second innings for historical imports.
- Case study used historical summaries before delivery import, but after delivery import it still relied on `game.batting_team_name` for the second innings and used a result fallback of `In progress`.
- Second-innings display overs used decimal math (`overs_completed + balls_this_over / 6`) instead of cricket-over notation.

### How innings team names are persisted and read
- Persisted in dry-run `innings_preview[].team` and copied into `Game.phases["historical_innings_summary"]`.
- First-innings summary used the innings team correctly.
- Second-innings display after delivery import depended on `game.batting_team_name`, which still pointed at the first batting team.

### How result/status is derived for imported historical matches
- `Game.status` was already persisted as `completed`.
- `Game.result` came from dry-run metadata preview.
- Cricsheet `info.outcome` was not converted into a result string, so `Game.result` could stay null and downstream case-study code fell back to `In progress`.

### How overs are calculated for imported innings
- Dry-run preview already excluded wides/no-balls when deriving innings preview overs.
- Delivery import, totals validation, first-innings summary derivation, and historical display paths still treated all deliveries as legal or used decimal-over display math.

### Where venue/date/event/season/match number are stored now
- No new columns were required.
- Dry-run metadata is already retained in `HistoricalImportBatch.dry_run_summary` JSON.
- Applied historical game metadata is already retained in `Game.phases["historical_import"]` JSON.
- Phase 5J extends those existing JSON blobs with:
  - `event_name`
  - `season`
  - `match_number`
  - `source_dates`
  - existing `venue` / `match_date`

### Migration decision
- **No migration required for Phase 5J.**
- Existing JSON storage in `HistoricalImportBatch.dry_run_summary` and `Game.phases` safely holds the required metadata for Analyst Workspace and future registry work.
- A dedicated competition/venue registry table is still deferred because Phase 5J only needs metadata correctness and exposure, not relational grouping UI or par-score modeling.

## Root causes found

### Root cause of innings-team bug
- Historical delivery import kept `game.batting_team_name` set to the side that batted first.
- Analyst detail and case-study second-innings rendering used that stale field, so the first batting team could appear twice.
- Team extraction also alphabetized source teams, which was not safe for preserving real source order during apply.

### Root cause of result/status bug
- Cricsheet `info.outcome` was ignored when building dry-run metadata.
- The imported historical `Game` row therefore had `result=None` for Cricsheet payloads.
- Case-study response logic then fell back to `In progress` despite `status=completed`.

### Root cause of overs bug
- Delivery import and historical display code counted all deliveries as legal.
- Wides and no-balls therefore inflated innings legal-ball totals.
- Some display paths also converted overs using decimal math instead of cricket-over notation.

## Metadata mapping rules after Phase 5J

- `info.teams` order is preserved for `teams_preview`, `Game.team_a`, and `Game.team_b`.
- Each innings summary uses the batting team from the innings node itself.
- `info.outcome.winner` + `info.outcome.by` are converted into a stored result string when no explicit result summary is present.
- Wides and no-balls do **not** increment legal-ball counts for historical preview, totals validation, first-innings summary, or second-innings persisted state.
- Metadata preservation now maps:
  - `info.venue` -> `venue`
  - `info.dates` -> `match_date` (first entry) and `source_dates` (all entries)
  - `info.event.name` -> `event_name`
  - `info.season` -> `season`
  - `info.event.match_number` -> `match_number`

## What is fixed now

- Correct innings-team mapping for historical imports in preview, apply, analyst detail, and case-study responses.
- Correct completed result strings for Cricsheet outcome metadata, with safe `Completed` fallback when a historical game is completed but no explicit outcome text exists.
- Correct legal-ball over calculations for imported innings with wides/no-balls.
- Venue/event/season/match-number/source-date metadata preserved in existing JSON metadata and exposed in Analyst Workspace backend responses.
- Added sanitized real-structure regression fixtures for:
  - Barbados Tridents vs St Lucia Zouks
  - Guyana Amazon Warriors vs Trinidad & Tobago Red Steel

## Venue handling decision

- Phase 5J keeps venue in existing historical metadata JSON (`Game.phases["historical_import"]["venue"]`).
- This is sufficient for Analyst Workspace response exposure now.
- **Deferred to Phase 5K:** dedicated venue registry / canonicalization / venue par-score modeling.

## Competition / season / match-number handling decision

- Phase 5J parses and preserves competition event name, season, match number, and dates in existing JSON metadata.
- Phase 5J exposes those fields through Analyst Workspace backend responses where it is low-risk.
- **Deferred to Phase 5K:** registry tables, grouped filters/folders UI, and broader competition/season browsing workflows.

## Files changed

- `backend/api/schemas/historical_import.py`
- `backend/api/schemas/analyst_matches.py`
- `backend/api/schemas/case_study.py`
- `backend/services/historical_import_preview.py`
- `backend/services/historical_import_delivery_service.py`
- `backend/services/historical_import_apply_service.py`
- `backend/services/analytics_case_study.py`
- `backend/routes/analytics_case_study.py`
- `backend/routes/analyst_pro.py`
- `backend/tests/test_historical_import_dry_run.py`
- `backend/tests/test_historical_import_apply_deliveries.py`
- `backend/tests/test_analyst_pro_features.py`
- `backend/tests/sanitized_cricsheet_635215.json`
- `backend/tests/sanitized_cricsheet_635216.json`

## Tests added/updated

- Dry-run regression coverage for metadata parsing, preserved team order, innings-team mapping, and legal-ball overs.
- Delivery-import regression coverage for legal-ball counting, second-innings team mapping, stored metadata, and case-study output.
- Analyst Workspace regression coverage for imported list/detail/case-study metadata and completed results.

## Phase 5K follow-up recommendation

- Add canonical competition and venue registry tables only when grouping/filtering/par-score workflows are implemented.
- Build Analyst Workspace filters over preserved metadata after registry/canonicalization rules are locked.
- Consider storing explicit historical innings legal-ball counts anywhere else they become broadly reusable outside import analytics.

## Manual QA checklist

- [ ] Dry-run a Cricsheet-style JSON and confirm innings teams follow the source innings team names.
- [ ] Apply the batch and confirm Analyst Workspace match list shows the real completed result, not `In progress`.
- [ ] Open case study and confirm innings 1/innings 2 show different batting teams where the source says so.
- [ ] Confirm wides/no-balls do not push displayed overs beyond valid cricket notation.
- [ ] Confirm venue is visible in Analyst Workspace responses.
- [ ] Confirm event name, season, match number, and date metadata are present in backend responses for historical matches.
- [ ] Confirm no scoring engine, DLS, live bus, video-analysis, or mental-analysis behavior changed.
