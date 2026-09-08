# Phase 10J.16 — V2 Report Correctness and Recommendation Deduplication

Issue #507 authorizes a bounded correction to the Phase 10J.15 player-presentation
layer. No analysis, threshold, validity, confidence, or recurring-signal logic changes.

## Correctness contract

- A signal displays its persisted positive `valid_sample_count` when available.
- Persisted supporting repetition IDs may supply a metric-specific count when they map
  to the report's repetitions.
- With neither source, the comparable count is unavailable; zero is never invented.
- Player-facing governed actions consolidate only on the exact registry `action_id`.
  The consolidated action retains the ordered unique `linked_metric_ids` for every
  contributing metric. Different or missing action IDs are never merged.
- The existing three-repetition insufficient-evidence gate and all coach-review fields
  remain unchanged.

Both PDF and UI consume this presentation behavior. The PDF already renders an absent
count as “Comparable repetition count unavailable”; the UI now does the same. No
database migration is required.
