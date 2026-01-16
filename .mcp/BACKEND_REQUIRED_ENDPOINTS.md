# Backend Endpoints Required for Frontend Truth

This document tracks backend API endpoints that frontend components need but don't currently exist or aren't documented.

**Status Legend**:
- ✅ **Exists**: Endpoint confirmed available
- 🚧 **In Progress**: Backend team working on it
- ⏳ **Planned**: Scheduled for future sprint  
- ❌ **Not Implemented**: Needs to be created

---

## Phase Analysis

### `GET /games/{gameId}/phase-analysis`
**Status**: ⏳ Planned

**Used By**: 
- `frontend/src/components/PhaseAnalysisWidget.vue`

**Priority**: HIGH

**Expected Response**:
```json
{
  "powerplay": {
    "total_runs": 72,
    "avg_per_over": 12.0,
    "fours": 6,
    "sixes": 2,
    "wickets": 1,
    "strike_rate": 154.3,
    "batting_order": [
      {
        "player_id": "uuid",
        "player_name": "Player Name",
        "runs": 45,
        "balls": 18,
        "strike_rate": 250.0
      }
    ]
  },
  "middle": { /* same structure */ },
  "death": { /* same structure */ }
}
```

**Workaround**: 
- Show "Phase analysis not available" message
- Remove hardcoded mock data (lines 250-320 in PhaseAnalysisWidget.vue)

---

## Organization Stats

### `GET /organizations/{orgId}/stats`
**Status**: ❌ Not Implemented

**Used By**:
- `frontend/src/views/OrgDashboardView.vue`

**Priority**: MEDIUM

**Expected Response**:
```json
{
  "total_teams": 8,
  "total_matches": 42,
  "season_win_rate": 68.5,
  "avg_run_rate": 7.4,
  "powerplay_net_runs": 12,
  "death_over_economy": 9.2
}
```

**Workaround**:
- Show "Organization stats pending" message
- Remove mock data (lines 214-246 in OrgDashboardView.vue)

---

### `GET /organizations/{orgId}/teams`
**Status**: ❌ Not Implemented

**Used By**:
- `frontend/src/views/OrgDashboardView.vue`

**Priority**: MEDIUM

**Expected Response**:
```json
{
  "teams": [
    {
      "id": "uuid",
      "name": "Team Name",
      "played": 12,
      "won": 9,
      "lost": 3,
      "win_percent": 75.0,
      "avg_score": 168,
      "nrr": 1.24
    }
  ]
}
```

**Workaround**:
- Show "Team standings unavailable" message
- Remove mock teams array (lines 232-240 in OrgDashboardView.vue)

---

## Tournament Leaderboards

### `GET /tournaments/{tournamentId}/leaderboards`
**Status**: ❌ Not Implemented

**Used By**:
- `frontend/src/components/FanStatsWidget.vue`

**Priority**: LOW

**Query Parameters**:
- `type`: "batting" | "bowling" | "all"
- `limit`: number (default: 10)

**Expected Response**:
```json
{
  "batting": [
    {
      "player_id": "uuid",
      "player_name": "Player Name",
      "runs": 652,
      "innings": 15,
      "average": 43.47,
      "strike_rate": 137.2,
      "fours": 65,
      "sixes": 28
    }
  ],
  "bowling": [
    {
      "player_id": "uuid",
      "player_name": "Player Name",
      "wickets": 24,
      "overs": 48.0,
      "runs_conceded": 384,
      "economy": 8.0,
      "average": 16.0
    }
  ]
}
```

**Workaround**:
- Remove `generateBatters()`, `generateBowlers()` functions (lines 330-360)
- Show "Tournament leaderboards unavailable" message

---

## Game Metrics Endpoint (Optional Enhancement)

### `GET /games/{gameId}/metrics`
**Status**: ⏳ Planned (Optional)

**Used By**:
- `frontend/src/composables/useCanonicalMetrics.ts` (fallback refresh)

**Priority**: LOW (snapshot already provides this data)

**Expected Response**:
```json
{
  "score": 156,
  "wickets": 5,
  "overs": "18.3",
  "balls_remaining": 10,
  "current_run_rate": 8.52,
  "required_run_rate": 9.75,
  "extras": {
    "total": 12,
    "wides": 6,
    "no_balls": 3,
    "byes": 2,
    "leg_byes": 1
  },
  "last_updated": "2026-01-16T14:35:22Z"
}
```

**Note**: This is redundant with live snapshot, only useful if:
1. Client reconnects after disconnect
2. Page loads without active socket
3. Want REST fallback for reliability

---

## Pressure Map (Analytics)

### `GET /games/{gameId}/pressure-map`
**Status**: ✅ Exists (backend/services/pressure_analyzer.py)

**Used By**:
- Not currently used in frontend! Need to wire up.

**Priority**: MEDIUM

**Expected Response**:
```json
{
  "deliveries": [
    {
      "over_number": 1,
      "ball_number": 1,
      "pressure_score": 42.5,
      "factors": {
        "dot_streak": 15,
        "rrr_gap": 20,
        "wickets_remaining": 5,
        "overs_remaining": 3
      }
    }
  ]
}
```

**Action Required**:
- Create `PressureMapWidget.vue` component
- Use backend pressure_analyzer data instead of local calculations

---

## AI Summary (Coach Module)

### `GET /games/{gameId}/ai-summary`
**Status**: ✅ Exists (backend has AI summary generation)

**Used By**:
- `frontend/src/views/MatchCaseStudyView.vue`

**Priority**: HIGH

**Expected Response**:
```json
{
  "overview": "Match summary text...",
  "key_themes": [
    "Powerplay domination by batting side",
    "Middle overs wicket cluster"
  ],
  "decisive_phases": [
    {
      "phase_id": "pp1",
      "label": "Powerplay",
      "over_range": [1, 6],
      "innings": 1,
      "impact_score": 12,
      "narrative": "Aggressive start with..."
    }
  ],
  "player_highlights": [
    {
      "player_id": "uuid",
      "player_name": "Player Name",
      "role": "batter",
      "highlight_type": "match_winner",
      "summary": "Scored crucial 68 runs..."
    }
  ],
  "momentum_shifts": [],
  "teams": [],
  "tags": ["high_scoring", "close_finish"],
  "created_at": "2026-01-16T14:35:22Z"
}
```

**Action Required**:
- Remove mock data generation (lines 709-730 in MatchCaseStudyView.vue)
- Use actual `ai_summary` field from game state
- Show "AI analysis pending" if not available

---

## Summary

**Total Endpoints Required**: 7

**By Status**:
- ✅ Exists: 2 (pressure-map, ai-summary)
- ⏳ Planned: 2 (phase-analysis, game-metrics)
- ❌ Not Implemented: 3 (org-stats, org-teams, tournament-leaderboards)

**By Priority**:
- HIGH: 2 (phase-analysis, ai-summary)
- MEDIUM: 3 (org-stats, org-teams, pressure-map)
- LOW: 2 (tournament-leaderboards, game-metrics)

**Next Steps**:
1. Coordinate with backend team on phase-analysis endpoint (HIGH priority)
2. Wire up existing pressure-map to frontend
3. Fix AI summary to use actual backend data
4. Defer org/tournament endpoints to future sprint (lower priority)

---

**Last Updated**: 2026-01-16  
**Maintained By**: Frontend Truth & Consistency Engineer
