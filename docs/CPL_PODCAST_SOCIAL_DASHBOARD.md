# CPL Podcast & Social Visual Dashboard

## Overview

The CPL Podcast & Social Visual Dashboard is a deterministic, read-only analytical workspace built for Caribbean Premier League historical data. It is integrated into the **Analyst Workspace** under the **CPL Dashboard** tab.

All data displayed in the dashboard comes exclusively from validated, fully-imported historical match data. No AI-generated statistics, fabricated values, or fallback demo data are used at any time.

---

## Location

The dashboard is accessible from the Analyst Workspace:

- **Route**: `/analyst` or `/analyst/workspace`
- **Tab**: "CPL Dashboard"
- **Access**: Requires `analyst_pro` or `org_pro` role

---

## Features

### 1. Provenance Bar

Always visible. Shows:

- Data source: validated historical import
- Number of eligible matches in archive
- Excluded metadata-only count (if any)
- Excluded invalid/unvalidated count (if any)

### 2. Filters

Available at the top of the dashboard:

| Filter | Default | Description |
|--------|---------|-------------|
| Season | All seasons | Filter by CPL season (e.g., 2023) |
| Team | All teams | Filter by team name |
| Venue | All venues | Filter by venue name |

Filters are derived entirely from imported data — only values present in the archive appear as options.

### 3. Season Summary Cards

Shows deterministic statistics for the current filter selection:

- **Matches available** — number of eligible CPL matches
- **Teams represented** — unique teams across filtered matches
- **Venues represented** — unique venues across filtered matches
- **Total runs** — sum of runs from innings totals
- **Total wickets** — sum of wickets from innings totals
- **Top team by wins** — visible when win data is available in imports (currently `—` as win data is not in the stats schema; this is a documented future enhancement)

⚠ Cards show insufficiency warnings when delivery data is absent.

### 4. Match Story Visuals

Select any CPL match from the dropdown to see:

- **Match header** — teams, venue, date, format, provenance source file
- **Innings Comparison** — visual comparison of innings scores with run-rate bars
- **Delivery data indicator** — confirms whether ball-by-ball data is available

> Phase breakdown (powerplay/middle/death overs) requires delivery data import. When absent, a warning is shown.

### 5. Leaderboard Visuals

- **Top Run Scorers** — top 10 by runs scored (delivery data required)
- **Top Wicket Takers** — top 10 by wickets (delivery data required)
- **Team Averages** — avg score, total runs per team

All leaderboard data comes from `batting_scorecard` / `bowling_scorecard` fields populated during Phase 5F delivery import. If no delivery data has been imported, an insufficiency warning is shown.

### 6. Venue Intelligence

Each CPL venue card shows:

- Match count
- Average first-innings score (0 / unavailable if no delivery data)
- Average total runs

⚠ When `avg_first_innings_score` is 0, a warning is shown indicating delivery data is required for that calculation.

### 7. Podcast Prep Panel

Deterministic talking-point candidates grounded in imported match data:

- Season-level facts (matches, total runs, total wickets, teams, venues)
- Top scorer and top wicket taker facts
- Selected match facts (scores, venue, date)
- Venue facts (if a venue is selected)

Each fact includes a caveat when the underlying data is incomplete (e.g., "From matches with delivery data only").

### 8. AI Talking-Point Assistant

The **AI Talking-Point Assistant** generates reviewable podcast talking-point drafts directly from the deterministic facts shown in the Podcast Prep Panel.

**Architecture:**
- **Frontend-only** — no new backend endpoint is required. All content is generated client-side from the visible fact bundle.
- All generated content is grounded exclusively in the deterministic `podcastFacts` computed array.
- No AI model contact, no database access, no mutation side effects.

**Fact bundle:**
- The analyst sees a preview of exactly which facts (by label) will be used before generation.
- If the fact bundle contains fewer than 2 facts, the Generate button is disabled and a warning is shown.

**Generated talking-point sections:**

| Section | Grounding |
|---------|-----------|
| Opening hook | Selected match facts or season summary |
| Key season facts | Total runs, wickets, match count |
| Player / team angle | Top scorer and wicket taker (delivery data only) |
| Venue angle | Venue avg first innings or venue list |
| Caution / limitation | Any missing or incomplete data signals |
| Questions for host | Context-aware discussion starters |

Every talking point includes:
- `section` label
- `title`
- `text` (draft — editable by analyst)
- `sourceFactIds` — IDs of the specific facts used
- `confidence` badge (`high` / `medium` / `low`)
- `status` badge (`needs_review` / `approved` / `rejected`)

**Review gates:**

All generated talking points start as `needs_review`. The analyst must explicitly approve each point before it can be considered final copy. Controls per point:
- **✓ Approve** — marks the point as reviewed and approved
- **↩ Unapprove** — reverts an approved point back to needs_review
- **✎ Edit** — opens an inline editor; saving updates the draft text
- **📋 Copy (Unreviewed)** / **📋 Copy (Reviewed)** — copies text to clipboard, with a label indicating review status
- **✕ Reject** — dismisses the point; it can be restored

A review summary at the bottom shows how many points are approved vs total.

**Safety rules enforced:**
- AI will not calculate official scores, averages, or records.
- AI will not mention facts not present in the supplied bundle.
- AI will not generate gambling/betting language.
- If delivery data is absent, a Caution/limitation talking point explains what is missing.
- If player leaderboard data is unavailable, no top-scorer narratives are generated.
- Unreviewed points are clearly labeled as `[UNREVIEWED — not final]` when copied.

**Deterministic fallback:**
- The assistant is entirely frontend-based and works without any backend AI service.
- If CPL data is absent, the Generate button is disabled and the panel explains why.

### 8. Advanced Podcast Script Builder

The dashboard now includes an **Advanced Podcast Script Builder** directly under the talking-point assistant.

**Scope and safety:**
- Frontend-only assembly from deterministic dashboard facts and current filter context.
- Includes only **approved** talking points in final script copy/export by default.
- Shows unapproved talking points in a separate "needs review" list.
- No publishing automation, no social posting, no new AI/LLM calls.

**Template sections generated:**
- Episode working title
- Episode objective
- Opening hook
- Context setup
- Key facts to mention
- Visual cue list
- Approved talking points
- Host/analyst questions
- Limitations / data caveats
- Closing summary
- Follow-up content ideas
- Provenance & limitations block

**Review gates and insufficiency behavior:**
- Script generation is disabled when CPL data is unavailable.
- Script generation is disabled when fewer than 2 deterministic facts are available.
- If no talking points are approved, a facts-only script is generated and marked incomplete.
- Missing delivery/leaderboard signals are carried into the caveats block.

**Export/copy workflow:**
- Analyst can edit the generated script in-place before export.
- Copy as Markdown.
- Copy as plain text.
- Download local `.md` file.

### 9. CPL Social Image Export Pack

The dashboard now includes a guarded **Social Image Export Pack** for deterministic sections.

Supported export targets:
- Season summary cards
- Selected match story panel
- Leaderboards panel
- Venue intelligence panel
- Podcast prep facts panel

Supported output formats:
- Podcast landscape: **1920×1080**
- Social square: **1080×1080**
- Story/reel vertical: **1080×1920**

Workflow:
1. Select an export target, output format, and visual template.
2. Review watermark/provenance toggles.
3. Generate preview.
4. Review preview and download PNG.

Template library (frontend-only):
- Template families:
  - Match Story Template
  - Season Summary Template
  - Leaderboard Template
  - Venue Intelligence Template
  - Podcast Episode Card Template
- Template variants:
  - Clean Broadcast
  - Bold Social
  - Data Desk
  - Minimal Stat Card
- Format-aware spacing:
  - Podcast landscape (1920×1080)
  - Social square (1080×1080)
  - Story/reel vertical (1080×1920)

Watermark/provenance options:
- `Powered by Cricksy`
- `Imported CPL historical data`
- Season/match/venue context label
- Generated timestamp

Safe disable behavior:
- No CPL data: export disabled
- No selected match: match story export disabled
- Match has no delivery data: match story export disabled to avoid misleading advanced visuals
- No leaderboard data: leaderboard export disabled
- No venue data: venue export disabled
- Template-specific requirements: if selected template requires match/leaderboard/venue/fact data, preview/export stays disabled until required deterministic data exists

Limitations:
- Templates restyle deterministic dashboard content only; they do not invent or mutate cricket facts.
- No automated posting/publishing was added.
- No backend schema or migration changes were required for the template library.

---

## Data Sources

All data is served by the existing endpoint:

```
GET /analytics/historical-stats/summary
```

- Requires `analyst_pro` or `org_pro` role
- Returns deterministic aggregate stats from all validated historical matches
- Metadata-only and invalid/unvalidated imports are excluded
- No official cricket truth is mutated

**No additional backend endpoints were added for this dashboard.**

---

## Empty / Insufficient Data States

The dashboard degrades safely in all these conditions:

| State | Behaviour |
|-------|-----------|
| No CPL imports at all | "No CPL data available" message with import instructions |
| API error | Error message with retry button |
| Loading | Loading spinner |
| No delivery data for a match | Warning in innings section; leaderboards show no data |
| Venue avg score unavailable | ⚠ badge on venue card |
| No leaderboard data | Insufficiency message in leaderboard section |
| No match selected | Hint to select a match |

---

## No-Fake-Data Confirmation

- No hardcoded player names, scores, or statistics exist in the component.
- All displayed values are derived from the API response.
- When the API returns empty lists, empty states are shown — not placeholder data.
- Tests assert that no fake player names appear when the API returns empty data.

---

## Tests

### Backend

File: `backend/tests/test_cpl_dashboard_historical_stats.py`

Tests:
- Empty state returns safe zero totals
- CPL-tagged imports appear in competitions aggregate
- Non-CPL matches do not contaminate CPL competition list
- No mutation of official Game truth fields
- Schema fields required by dashboard are all present
- Season appears in seasons list
- Note field is deterministic provenance statement

Run:
```bash
cd backend
CRICKSY_IN_MEMORY_DB=1 APP_SECRET_KEY=test-secret-key \
  python -m pytest tests/test_cpl_dashboard_historical_stats.py -v
```

### Frontend

File: `frontend/tests/unit/CplPodcastDashboard.spec.ts`

Tests (22):
- Loading, error, and empty states
- Summary cards with correct values from mock data
- Venue rendering and missing-score warnings
- Leaderboard rendering (run scorers, wicket takers)
- Innings comparison when match is selected
- Delivery-data warning for matches without ball data
- Podcast prep panel deterministic facts
- AI placeholder note
- Provenance bar always visible
- No fake/hardcoded data
- Filter reset
- Export target/format controls
- Match story export disabled without selected match
- Preview generation + download enablement
- Leaderboard export disabled when delivery data is absent

Run:
```bash
cd frontend
npx vitest run tests/unit/CplPodcastDashboard.spec.ts
```

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/CplPodcastDashboard.vue` | Added full AI Talking-Point Assistant panel (replaced placeholder) |
| `frontend/tests/unit/CplPodcastDashboard.spec.ts` | Updated AI placeholder test; added 14 new AI panel tests |
| `docs/CPL_PODCAST_SOCIAL_DASHBOARD.md` | Updated Section 7/8, Known Limitations, and Next Steps |

---

## Known Limitations

1. **Win/loss data** — The `HistoricalStatsSummaryResponse` schema does not include per-team win/loss counts. The "Top team by wins" card shows `—` until win data is added to the schema.

2. **Player-to-competition scoping** — Player aggregates in the summary response are global (not scoped per competition). The dashboard shows all players from the archive when CPL matches with delivery data exist. A future enhancement would scope players to CPL specifically.

3. **Phase breakdown** — Powerplay/middle/death phase visuals require ball-by-ball delivery data import (Phase 5F). Only innings totals are shown for matches without delivery data.

4. **AI talking points** — The AI Talking-Point Assistant is frontend-only and deterministic. It does not use a backend AI model. The `_buildTalkingPoints()` function generates all content from the fact bundle only. For production use, a backend AI endpoint could replace this with an LLM-based generation step while keeping the same review gates and fact-bundle constraints.

5. **Image export fidelity** — Export snapshots are generated client-side from dashboard DOM. Complex browser differences (fonts/rendering) may cause minor visual variance.

---

## Next Steps

The next issue should focus on:

1. **Win/loss data** — Add win/loss tracking to the historical stats schema to enable the "top team by wins" card.
2. **Player-to-competition scoping** — Scope player aggregates to CPL specifically once per-match player attribution is available in the summary endpoint.
3. **Backend AI integration** — If an LLM-based AI service becomes available, wire the AI Talking-Point Assistant to a backend endpoint using the same fact-bundle payload and review-gate structure already in place.
4. **Advanced podcast script builder** — Reusable visual templates and a content calendar workflow to take approved talking points through to a full podcast prep document.
5. **Image/social export formats** — Add per-section PNG stat card export for individual summary cards.
