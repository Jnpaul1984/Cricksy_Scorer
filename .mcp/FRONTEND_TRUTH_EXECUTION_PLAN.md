# Frontend Truth & Consistency - Execution Plan
**Date**: 2026-01-16  
**Branch**: beta/audit-frontend-metrics-source-of-truth  
**Engineer**: Frontend Truth & Consistency Engineer

---

## Overview
Fix ALL 37 issues identified in FRONTEND_METRICS_AUDIT_REPORT.md by creating a canonical metrics contract and replacing dummy/drift-prone code with backend-driven values.

---

## PHASE 1: Canonical Metrics Contract

### 1.1 Create useCanonicalMetrics Composable
**File**: `frontend/src/composables/useCanonicalMetrics.ts`

**Purpose**: Single source of truth for all scoreboard-critical metrics

**Interface**:
```typescript
export function useCanonicalMetrics(gameId: Ref<string> | string) {
  return {
    // Core scoreboard
    score: computed(() => number | null),
    wickets: computed(() => number | null),
    overs: computed(() => string),  // "12.3" format
    ballsRemaining: computed(() => number | null),
    
    // Run rates
    crr: computed(() => number | null),
    rrr: computed(() => number | null),
    
    // Extras breakdown
    extras: computed(() => { total: number, wides: number, noBalls: number, byes: number, legByes: number }),
    
    // Meta
    updatedAt: computed(() => Date | null),
    isStale: computed(() => boolean),  // > 30s since last update
    
    // Refresh methods
    refresh: () => Promise<void>,
  }
}
```

**Data sources**:
1. Primary: `gameStore.liveSnapshot` (real-time Socket.IO)
2. Fallback: `GET /games/{gameId}` API call
3. On-demand: `GET /games/{gameId}/metrics` if endpoint exists

### 1.2 Update Pinia Store Types
**File**: `frontend/src/stores/gameStore.ts`

**Changes**:
- Ensure `liveSnapshot` uses `Snapshot` type from types/index.ts
- Add missing fields to `Snapshot` interface:
  - `balls_remaining?: number`
  - `extras?: ExtrasBreakdown`
  - `last_updated?: string`

**File**: `frontend/src/types/index.ts`

**Add**:
```typescript
export interface ExtrasBreakdown {
  total: number
  wides: number
  no_balls: number
  byes: number
  leg_byes: number
}

export interface Snapshot {
  // ... existing fields
  balls_remaining?: number
  extras?: ExtrasBreakdown
  last_updated?: string  // ISO timestamp
}
```

---

## PHASE 2: Replace Dummy Widgets

### Module A: Phase Analysis
**Files**:
- `frontend/src/components/PhaseAnalysisWidget.vue`

**Issues**:
- A1: Hardcoded phaseDataMap (lines 250-320)
- A2: Fake player names (lines 254-276)

**Fix**:
1. Remove `phaseDataMap` object
2. Add API call: `GET /games/{gameId}/phase-analysis`
3. Create service function in `frontend/src/services/api.ts`:
   ```typescript
   export async function getPhaseAnalysis(gameId: string) {
     return apiRequest<PhaseAnalysisResponse>(`/games/${gameId}/phase-analysis`)
   }
   ```
4. Use real phase data or show "No phase data available"

**Blocked by backend**: If endpoint doesn't exist, create TODO in BACKEND_REQUIRED_ENDPOINTS.md

---

### Module B: Live Match Card
**Files**:
- `frontend/src/components/LiveMatchCardCoach.vue`

**Issues**:
- A3: Empty lastSixBalls (lines 284-292)
- B5: Par run rate calculation (lines 307-315)
- B6: Bowler economy calculation (lines 272-278)

**Fixes**:
```typescript
// A3: Last 6 balls (line 284)
const lastSixBalls = computed(() => {
  const deliveries = gameStore.liveSnapshot?.deliveries ?? []
  return deliveries.slice(-6).map(d => {
    if (d.is_wicket) return 'W'
    if (d.runs_off_bat === 4) return '4'
    if (d.runs_off_bat === 6) return '6'
    if (!d.extra_type && d.runs_scored === 0) return '0'
    return String(d.runs_scored)
  })
})

// B5: Par vs CRR (line 307)
const parVsCRR = computed(() => {
  const snapshot = gameStore.liveSnapshot
  if (!snapshot?.dls?.par || !snapshot?.current_run_rate) return null
  const diff = snapshot.current_run_rate - snapshot.dls.par
  return diff >= 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2)
})

// B6: Bowler economy (line 272)
const bowlerEcon = computed(() => {
  const bowler = gameStore.liveSnapshot?.bowling_scorecard?.[selectedBowlerId.value]
  return bowler?.economy?.toFixed(2) ?? '—'
})
```

---

### Module C: Organization Dashboard
**Files**:
- `frontend/src/views/OrgDashboardView.vue`

**Issues**:
- A4: Complete mock data (lines 214-246)

**Fix**:
1. Create API calls:
   ```typescript
   GET /organizations/{orgId}/stats
   GET /organizations/{orgId}/teams
   ```
2. Replace all mock refs with API data
3. Show loading/empty states properly

**Blocked by backend**: Mark in BACKEND_REQUIRED_ENDPOINTS.md if endpoints missing

---

### Module D: Coaches Dashboard
**Files**:
- `frontend/src/views/CoachesDashboardView.vue`

**Issues**:
- A5: Mock key players (lines 207-213)

**Fix**:
```typescript
const keyPlayers = computed(() => {
  const batting = gameStore.currentGame?.batting_scorecard ?? {}
  const bowling = gameStore.currentGame?.bowling_scorecard ?? {}
  
  return Object.entries(batting)
    .map(([id, stats]) => ({
      id,
      name: stats.player_name,
      runs: stats.runs,
      wickets: bowling[id]?.wickets_taken ?? 0,
      avg: stats.runs / (stats.balls_faced || 1)
    }))
    .sort((a, b) => b.runs - a.runs)
    .slice(0, 6)
})
```

---

### Module E: Fan Stats Widget
**Files**:
- `frontend/src/components/FanStatsWidget.vue`

**Issues**:
- A6: Random stats generator (lines 330-360)

**Fix**:
1. Remove `generateBatters()`, `generateBowlers()`, `generateRecords()`
2. Add API call: `GET /tournaments/{tournamentId}/leaderboards`
3. Show "No stats available" if data missing

**Blocked by backend**: Mark in BACKEND_REQUIRED_ENDPOINTS.md

---

### Module F: Match Case Study
**Files**:
- `frontend/src/views/MatchCaseStudyView.vue`

**Issues**:
- A7: Mock AI summary (lines 709-730)

**Fix**:
```typescript
const aiSummary = computed(() => {
  const summary = gameStore.currentGame?.ai_summary
  if (!summary || !summary.overview) {
    return {
      overview: 'AI analysis not yet available',
      key_moments: [],
      turning_points: []
    }
  }
  return summary
})
// Remove lines 718-730 (mock generation)
```

---

### Module G: Base Components
**Files**:
- `frontend/src/components/BaseInput.vue`

**Issues**:
- A8: Math.random() ID (line 60)

**Fix**:
```typescript
// Use counter instead of Math.random()
let idCounter = 0
const inputId = computed(() => props.id ?? `input-${++idCounter}`)
```

---

## PHASE 3: Remove Local Calculations

### Module H: Scoreboard Widget
**Files**:
- `frontend/src/components/ScoreboardWidget.vue`

**Issues**:
- B1: Local CRR fallback (lines 394-404)

**Fix**:
```typescript
const crr = computed(() => {
  const backendCrr = liveSnapshot.value?.current_run_rate
  return backendCrr != null ? backendCrr.toFixed(2) : '—'
})
// REMOVE fallback calculation entirely
```

---

### Module I: Analytics View
**Files**:
- `frontend/src/views/AnalyticsView.vue`

**Issues**:
- B2: Redundant CRR calculation (lines 216-226)
- B3: RRR calculation (lines 228-245)

**Fixes**:
```typescript
// B2: CRR (line 216)
const crr = computed(() => gameStore.liveSnapshot?.current_run_rate ?? 0)

// B3: RRR (line 228)
const req = computed(() => {
  const s = snapshot.value
  if (!s?.target || !s?.required_run_rate) {
    return { rrr: null, remainingOvers: null, remainingRuns: null }
  }
  return {
    rrr: s.required_run_rate,
    remainingRuns: s.target - s.total_runs,
    remainingOvers: s.balls_remaining / 6
  }
})
```

---

### Module J: Game Scoring View
**Files**:
- `frontend/src/views/GameScoringView.vue`

**Issues**:
- B4: Local balls remaining (lines 613-616)
- B7: Last delivery assembly (lines 475-510)

**Fixes**:
```typescript
// B4: Balls remaining (line 613)
const ballsRemaining = computed(() => 
  gameStore.liveSnapshot?.balls_remaining ?? 0
)

// B7: Last delivery (line 475)
const lastDelivery = computed(() => 
  gameStore.liveSnapshot?.last_delivery ?? null
)
// Use backend values directly, remove local calculations
```

---

## PHASE 4: Event Log Tab

### Replace AI Commentary Tab
**File**: `frontend/src/views/GameScoringView.vue`

**Current**: AI Commentary tab (unused/placeholder)

**New**: EVENT LOG tab

**Features**:
1. Display deliveries from `deliveriesThisInnings`
2. Show non-delivery events (Drinks, Injury, Ball Change, Delay)
3. Add Event UI:
   - Dropdown: [Drinks, Injury, Ball Change, Delay, Other]
   - Text field: Note/description
   - Timestamp: auto-generated
4. Storage: Pinia store (client-side for now)
5. Copy-to-clipboard: "Over X summary: ..."

**Implementation**:
```vue
<template>
  <div class="event-log-tab">
    <div class="event-log-header">
      <h3>Event Log</h3>
      <BaseButton @click="showAddEvent = true">+ Add Event</BaseButton>
    </div>
    
    <div class="event-log-timeline">
      <div v-for="event in events" :key="event.id" class="event-item">
        <span class="event-time">{{ formatTime(event.timestamp) }}</span>
        <span class="event-type">{{ event.type }}</span>
        <span class="event-note">{{ event.note }}</span>
      </div>
    </div>
    
    <AddEventModal 
      v-model:show="showAddEvent" 
      @add="handleAddEvent" 
    />
  </div>
</template>
```

**Store additions**:
```typescript
// gameStore.ts
const gameEvents = ref<GameEvent[]>([])

interface GameEvent {
  id: string
  type: 'delivery' | 'drinks' | 'injury' | 'ball_change' | 'delay' | 'other'
  timestamp: string
  note?: string
  delivery?: Delivery
}

function addGameEvent(event: Omit<GameEvent, 'id' | 'timestamp'>) {
  gameEvents.value.push({
    ...event,
    id: crypto.randomUUID(),
    timestamp: new Date().toISOString()
  })
}
```

---

## PHASE 5: Documentation & Testing

### Create BACKEND_REQUIRED_ENDPOINTS.md
**File**: `.mcp/BACKEND_REQUIRED_ENDPOINTS.md`

**Template**:
```markdown
# Backend Endpoints Required for Frontend Truth

## Phase Analysis
- `GET /games/{gameId}/phase-analysis`
  - Returns: { powerplay: {...}, middle: {...}, death: {...} }
  - Used by: PhaseAnalysisWidget.vue
  - Priority: HIGH

## Organization Stats
- `GET /organizations/{orgId}/stats`
  - Returns: { totalTeams, totalMatches, avgRunRate, ... }
  - Used by: OrgDashboardView.vue
  - Priority: MEDIUM

## Tournament Leaderboards
- `GET /tournaments/{tournamentId}/leaderboards?type=batting`
  - Returns: [ { playerId, name, runs, avg, sr }, ... ]
  - Used by: FanStatsWidget.vue
  - Priority: LOW
```

### Update Audit Report
**File**: `.mcp/FRONTEND_METRICS_AUDIT_REPORT.md`

Add status column to each finding:
- ✅ **Fixed**: Implemented and tested
- 🚧 **Blocked**: Awaiting backend endpoint
- ⏳ **In Progress**: Implementation underway

### QA Checklist
**File**: `.mcp/QA_STADIUM_MODE_CHECKLIST.md`

```markdown
# Stadium Mode QA Checklist

## Scoreboard Accuracy
- [ ] Score matches backend snapshot exactly
- [ ] Wickets count is correct
- [ ] Overs display matches balls bowled
- [ ] CRR calculated by backend, no local fallback
- [ ] RRR shown correctly for 2nd innings

## Widget Integrity
- [ ] No widgets display mock/placeholder data
- [ ] LastSixBalls shows actual deliveries
- [ ] Phase analysis uses backend data OR shows "Unavailable"
- [ ] Player stats from real scorecards, not fake names

## Connection Resilience
- [ ] Disconnect → shows "Syncing..." indicator
- [ ] Reconnect → data refreshes correctly
- [ ] No stale values displayed after reconnect
- [ ] Socket state:update properly updates UI

## Event Log
- [ ] Deliveries appear in timeline
- [ ] Add Event UI functional
- [ ] Events stored in Pinia
- [ ] Copy-to-clipboard works
```

---

## File Changes Summary

### Created (New Files)
1. `frontend/src/composables/useCanonicalMetrics.ts`
2. `frontend/src/components/AddEventModal.vue`
3. `.mcp/BACKEND_REQUIRED_ENDPOINTS.md`
4. `.mcp/QA_STADIUM_MODE_CHECKLIST.md`

### Modified (Existing Files)

**Types & Store**:
1. `frontend/src/types/index.ts` - Add ExtrasBreakdown, update Snapshot
2. `frontend/src/stores/gameStore.ts` - Add gameEvents, addGameEvent

**Critical Widgets (7 files)**:
3. `frontend/src/components/PhaseAnalysisWidget.vue` - Remove mock data
4. `frontend/src/components/LiveMatchCardCoach.vue` - Fix 3 issues
5. `frontend/src/views/OrgDashboardView.vue` - Wire API
6. `frontend/src/views/CoachesDashboardView.vue` - Fix key players
7. `frontend/src/components/FanStatsWidget.vue` - Remove generators
8. `frontend/src/views/MatchCaseStudyView.vue` - Fix AI summary
9. `frontend/src/components/BaseInput.vue` - Remove Math.random

**High Priority (4 files)**:
10. `frontend/src/components/ScoreboardWidget.vue` - Remove CRR fallback
11. `frontend/src/views/AnalyticsView.vue` - Fix CRR + RRR
12. `frontend/src/views/GameScoringView.vue` - Fix balls, delivery, add Event Log tab

**Services**:
13. `frontend/src/services/api.ts` - Add new API functions

**Total Modified**: 13 files  
**Total Created**: 4 files  
**Total Changes**: 17 files

---

## Implementation Order

1. ✅ Create execution plan (this file)
2. 🔄 PHASE 1: Types & composable
3. 🔄 PHASE 2: Critical widgets (7 files)
4. 🔄 PHASE 3: High priority drift (4 files)
5. 🔄 PHASE 4: Event log tab
6. 🔄 PHASE 5: Documentation & testing
7. ✅ Run type-check & build
8. ✅ Update audit report with status

---

## Success Criteria

- ✅ All 37 audit items addressed (Fixed or Blocked with justification)
- ✅ `npm run type-check` passes
- ✅ `npm run build` succeeds
- ✅ QA checklist items verified
- ✅ No hardcoded metrics displayed in production UI
- ✅ All scoreboard values driven by backend snapshot
- ✅ Proper "Unavailable" states when data missing

---

**Status**: Execution in progress  
**Next Step**: Implement PHASE 1 - Canonical metrics composable
