# Phase 4F — Analyst Workspace Manual QA Checklist

## Scope
Phase 4F is a UX polish and stabilization pass for the existing Analyst Workspace workflow. No major new analyst features are introduced in this phase.

## Test Environment Assumptions
- Frontend and backend are running from the current repository state.
- Backend provides real match/case-study/export data from existing analyst endpoints.
- Feature is tested with at least one account that can access Analyst Workspace.
- Browser coverage: latest Chrome (primary), plus one secondary browser (Firefox/Safari/Edge) for smoke checks.
- Viewport checks include desktop and tablet widths.

## User Role / Access Assumptions
- Tester uses a user with analyst-capable access (`analyst_pro` or `org_pro`) so analyst endpoints are authorized.
- If role access is missing, expected behavior is an honest error/empty state (not fake data fallback).

## Manual QA Flow (Step-by-Step)

### 1) Open Analyst Workspace
- **Action:** Navigate to `/analyst/workspace`.
- **Expected:** Workspace shell renders with header, filters, summary cards, tabs, and export control.

### 2) Match List Loading Behavior
- **Action:** Load/reload page.
- **Expected:** Loading message appears while data is fetched.
- **Expected:** If request fails, an error message plus Retry is shown.

### 3) Real Matches or Honest Empty State
- **Action:** Observe matches tab after loading.
- **Expected:** Either:
  - real completed matches are listed, or
  - explicit empty state explains no completed matches match current filters.
- **Expected:** No fabricated matches or synthetic rows appear.

### 4) Select a Match
- **Action:** Click a match row (and keyboard check: focus row then Enter/Space).
- **Expected:** Match Intelligence panel opens and loads selected match context.

### 5) Match Intelligence Data
- **Action:** Review loaded detail panel.
- **Expected:** Result/format/date and innings table show backend-derived values.
- **Expected:** Loading/error states are explicit and retry-safe.

### 6) Visual Sections (Phase Breakdown + Key Players)
- **Action:** Inspect “Phase breakdown” and “Key players”.
- **Expected:**
  - real section data displays when available, and
  - honest empty-state copy displays when unavailable.
- **Expected:** No hardcoded player names, match facts, or fake impact claims.

### 7) Export Flow Checks
- **Action:** Verify export button state with and without workspace match context.
- **Expected:**
  - export trigger is disabled when no data context exists,
  - export modal/download is available when context exists,
  - no-row responses show explicit empty-data message,
  - no fake export rows are generated locally.

### 8) Podcast Prep Package Checks
- **Action:** Open podcast section for selected match.
- **Expected:** Section is generated from real loaded fields only.
- **Expected:** Missing data paths show honest “insufficient/not available” copy.
- **Expected:** Copy button is disabled when package lacks enough real data.

### 9) Copy/Export Safety Checks
- **Action:** Test copy and export actions across data-rich and data-poor matches.
- **Expected:** Actions are blocked/disabled when unavailable and do not output fabricated content.

### 10) Fake-Data Regression Checks
- **Action:** Scan visible Analyst Workspace, Match Intelligence, Export, and Podcast sections.
- **Expected:** No fake chart rows, fake names, fabricated match narratives, or AI-generated claims are introduced.

### 11) Mobile/Tablet Sanity Checks
- **Action:** Resize to tablet widths (~900px and ~768px).
- **Expected:** Layout remains readable, controls stay reachable, and key sections are scannable.
- **Action:** Optional narrow mobile smoke (~600px).
- **Expected:** No major overlap/clipping that blocks core workflow actions.

## Known Limitations (Phase 4F)
- Phase 4F does not introduce new analyst backend capabilities.
- Data completeness depends on existing recorded matches and endpoint payload coverage.
- Export availability still depends on real backend rows for selected context/filters.

## Pass/Fail Sign-Off
- [ ] PASS
- [ ] FAIL

### Sign-Off Details
- Tester:
- Date:
- Environment:
- Build/commit:
- Notes:

## Recommended Phase 4G Follow-Up
- Add automated e2e coverage for analyst end-to-end flow (workspace load → select match → detail/podcast/export checks).
- Add deeper accessibility pass (ARIA audit, keyboard traversal order, screen reader labeling).
- Add telemetry for analyst empty/error states to prioritize next data-quality improvements.
- Expand responsive polish for smaller mobile breakpoints if analyst usage on phones becomes a priority.
