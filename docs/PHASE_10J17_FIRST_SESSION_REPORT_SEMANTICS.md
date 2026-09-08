# Phase 10J.17 — First-Session Report Semantics

Issue #509 authorizes a presentation-only correction to the Phase 10J.15–10J.16 report
contract. Analysis, comparison, confidence, validity, thresholds, and governance remain
unchanged.

## Completed behavior

- A longitudinal response with exactly one considered session is a `Baseline established`.
  An embedded report without prior longitudinal evidence uses the same constructive state.
- Valid current-session `STRONG` measurements appear under “What looked good in this
  session” without claiming cross-session repeatability.
- Missing metric-specific comparable counts remain `null` internally and are omitted from
  player-facing UI/PDF cards.
- UI movement evidence is collapsed behind a native disclosure after a concise count and
  phase-confidence summary. The main PDF contains only that summary.
- The PDF appendix reports evidence counts and exact metric/action governance identifiers,
  while full repetition IDs, phase IDs, timestamps, frames, and evidence locators remain in
  the unchanged persisted V2 report for technical review.

No database migration is required.
