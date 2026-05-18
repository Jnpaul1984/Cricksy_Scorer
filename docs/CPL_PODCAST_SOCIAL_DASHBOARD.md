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

**AI Talking-Point Assistant** is documented as a future enhancement. The placeholder explains:
- AI will only summarise deterministic chart data
- AI will never calculate official scores, invent missing facts, or publish without review

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

Tests (18):
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

Run:
```bash
cd frontend
npx vitest run tests/unit/CplPodcastDashboard.spec.ts
```

---

## Files Changed

| File | Change |
|------|--------|
| `frontend/src/components/CplPodcastDashboard.vue` | **New** — CPL podcast/social dashboard component |
| `frontend/src/views/AnalystWorkspaceView.vue` | Added "CPL Dashboard" tab + import |
| `frontend/src/services/api.ts` | Added `getHistoricalStatsSummary()` + types |
| `backend/tests/test_cpl_dashboard_historical_stats.py` | **New** — backend contract tests |
| `frontend/tests/unit/CplPodcastDashboard.spec.ts` | **New** — frontend component tests |
| `docs/CPL_PODCAST_SOCIAL_DASHBOARD.md` | **New** — this documentation |

---

## Known Limitations

1. **Win/loss data** — The `HistoricalStatsSummaryResponse` schema does not include per-team win/loss counts. The "Top team by wins" card shows `—` until win data is added to the schema.

2. **Player-to-competition scoping** — Player aggregates in the summary response are global (not scoped per competition). The dashboard shows all players from the archive when CPL matches with delivery data exist. A future enhancement would scope players to CPL specifically.

3. **Phase breakdown** — Powerplay/middle/death phase visuals require ball-by-ball delivery data import (Phase 5F). Only innings totals are shown for matches without delivery data.

4. **AI talking points** — The AI Talking-Point Assistant is a documented future enhancement. No AI commentary is generated in this version.

---

## Next Steps

The next issue should focus on:

1. **Image/social export formats** — If a small image-export button can be safely reused from ExportUI, add PNG stat card export for individual summary cards.
2. **AI-assisted podcast talking points** — When AI talking-point generation is safely available, wire it to the deterministic facts in the podcast prep panel with full review gates.
3. **Win/loss data** — Add win/loss tracking to the historical stats schema to enable the "top team by wins" card.
4. **Player-to-competition scoping** — Scope player aggregates to CPL specifically once per-match player attribution is available in the summary endpoint.
