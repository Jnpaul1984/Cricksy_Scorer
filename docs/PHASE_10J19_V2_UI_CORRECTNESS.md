# Phase 10J.19 V2 UI Correctness and Coach Review Access

## Confirmed defects and minimum fixes

1. The Analysis Results view mounted the separate longitudinal endpoint component without passing
   the governed V2 report's `player_presentation.progress`. That allowed older first-session wording
   to replace the report/PDF state. V2 results now render the persisted governed progress contract,
   including **Baseline established** and its first-assessment explanation. The existing endpoint
   remains available when no governed presentation is supplied, preserving real multi-session
   comparison behavior without changing longitudinal calculations.
2. The movement disclosure was enabled by repetition count alone. Persisted presentation rows whose
   display fields were blank or `-` therefore produced a dash-only list. The disclosure now includes
   only repetitions with a meaningful governed repetition or phase display field and is suppressed
   when none exist. No movement wording, phase, timestamp, or conclusion is fabricated.
3. The exact recommendation error **Organization access is not configured for this user** is the
   existing fail-closed result for an `org_pro` user with no `org_id`; it is not emitted for a
   `coach_pro_plus` role. The UI now explains the existing setup requirement instead of displaying
   the raw backend detail. An administrator must link the Organization Pro account to an
   organization, and the player must have an active coach assignment whose coach belongs to that
   same organization. Authorization and assignment checks are unchanged.

## Focused validation

- Coach Pro Plus Analysis Results tests cover the governed baseline copy, suppression of 16
  dash-only movement rows, clear organization setup guidance, and the Phase 10J.18B non-blocking and
  stale-request protections.
- Longitudinal presentation tests cover governed first-session baseline state and existing
  multi-session comparison rendering.
- Existing player-development route tests cover denied unassigned/cross-organization access and
  successful configured organization access.
- Frontend type-check, changed-file hooks, and `git diff --check` cover the modified surface.

No deployment result is claimed. No backend contract, authorization mechanism, metric, threshold,
PDF behavior, telemetry, database schema, or migration changed.
