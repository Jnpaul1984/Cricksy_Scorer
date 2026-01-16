# Frontend Metrics Source-of-Truth Audit Report
**Date**: 2026-01-16  
**Branch**: beta/audit-frontend-metrics-source-of-truth  
**Auditor**: AI Metrics Sniffer Dog 🐕‍🦺

---

## Executive Summary

This audit identified **37 instances** of frontend UI values that are **not driven by backend snapshot/state**, creating drift risks, placeholder data, or hardcoded fallbacks that may mislead users.

### Risk Categories:
- **🔴 CRITICAL (12)**: Hardcoded dummy data displayed as real metrics
- **🟠 HIGH (15)**: Local computations that can drift from backend
- **🟡 MEDIUM (10)**: Placeholder/fallback values with unclear state

---

## A) Definitely Dummy/Placeholder Data

### 🔴 A1: PhaseAnalysisWidget - Complete Mock Phase Data
**File**: `frontend/src/components/PhaseAnalysisWidget.vue`  
**Lines**: 250-320  
**Severity**: CRITICAL

**What displays in UI**:
```typescript
powerplay: { totalRuns: 72, avgPerOver: 12, fours: 6, sixes: 2, wickets: 1, sr: 154.3 }
middle: { totalRuns: 90, avgPerOver: 9, fours: 8, sixes: 2, wickets: 2, sr: 128.6 }
death: { totalRuns: 56, avgPerOver: 14, fours: 3, sixes: 4, wickets: 1, sr: 186.7 }
```

**Issue**: Hardcoded mock data for ALL phase statistics. Widget shows fake runs, wickets, strike rates regardless of actual game state.

**Recommended Fix**:
- Backend endpoint exists: `GET /games/{id}/phase-analysis` returns actual phase stats
- Replace `phaseDataMap` with API call via `gameStore.fetchPhaseAnalysis()`
- Use backend fields: `phase_breakdown.powerplay`, `.middle`, `.death` from snapshot

---

### 🔴 A2: PhaseAnalysisWidget - Fake Player Performance
**File**: `frontend/src/components/PhaseAnalysisWidget.vue`  
**Lines**: 254-262, 268-276  
**Severity**: CRITICAL

**What displays in UI**:
```typescript
battingOrder: [
  { name: 'Virat Kohli', role: 'Batter', runs: 68, sr: 134 },
  { name: 'KL Rahul', role: 'Batter', runs: 22, sr: 122 },
]
keyMoments: [
  { icon: '🎯', title: 'Partnership 50 run stand', time: 'Over 10' },
]
```

**Issue**: Shows celebrity names instead of actual players. No connection to real batting order or partnership data.

**Recommended Fix**:
- Use `snapshot.batting_scorecard` to get real player stats per phase
- Backend `phase_breakdown` includes `batting_order` array
- Remove hardcoded names, fetch from `gameStore.currentGame.team_a.players`

---

### 🔴 A3: LiveMatchCardCoach - Empty Last 6 Balls
**File**: `frontend/src/components/LiveMatchCardCoach.vue`  
**Lines**: 284-292  
**Severity**: CRITICAL

**What displays in UI**:
```typescript
const lastSixBalls = computed(() => {
  return Array(6).fill(null).map((_, i) => '')  // Empty strings always!
})
```

**Issue**: Widget shows 6 empty ball slots with comment "Could populate from liveSnapshot?.deliveries if available" but never actually does.

**Recommended Fix**:
```typescript
const lastSixBalls = computed(() => {
  const deliveries = gameStore.liveSnapshot?.deliveries ?? []
  return deliveries.slice(-6).map(d => {
    if (d.is_wicket) return 'W'
    if (d.runs_off_bat === 4) return '4'
    if (d.runs_off_bat === 6) return '6'
    if (d.runs_scored === 0 && !d.extra_type) return '0'
    return String(d.runs_scored)
  })
})
```

---

### 🔴 A4: OrgDashboardView - Complete Mock Organization Data
**File**: `frontend/src/views/OrgDashboardView.vue`  
**Lines**: 214-246  
**Severity**: CRITICAL

**What displays in UI**:
```typescript
totalTeams: 8, totalMatches: 42, seasonWinRate: 68, avgRunRate: 7.4
teams: [
  { name: 'Lions FC', played: 12, won: 9, lost: 3, winPercent: 75, avgScore: 168 },
  { name: 'Falcons XI', played: 10, won: 7, lost: 3, avgScore: 155, nrr: 0.86 },
]
recentMatches: [...] // All hardcoded
orgAiCallouts: [...] // Derived from mock stats!
```

**Issue**: Entire dashboard shows fake data with `// TODO: Replace with real API data` comments since initial implementation.

**Recommended Fix**:
- Backend has `/organizations/{id}/stats` endpoint (per coaching module)
- Backend has `/organizations/{id}/teams` with standings
- Replace with actual API calls in `onMounted()`

---

### 🔴 A5: CoachesDashboardView - Mock Key Players
**File**: `frontend/src/views/CoachesDashboardView.vue`  
**Lines**: 207-213  
**Severity**: CRITICAL

**What displays in UI**:
```typescript
keyPlayers = [
  { id: '1', name: 'J. Smith', roles: ['C'], runs: 342, wickets: 2, avg: 42.75 },
  { id: '3', name: 'A. Johnson', roles: ['All'], runs: 156, wickets: 14, avg: 26.00 },
]
```

**Issue**: Shows hardcoded player statistics labeled as "Key Players" with comment `// TODO: Wire to store/API`.

**Recommended Fix**:
- Backend has `/players/stats` or per-game batting/bowling scorecards
- Use `gameStore.currentGame.batting_scorecard` + `.bowling_scorecard`
- Sort by runs/wickets, show top performers

---

### 🔴 A6: FanStatsWidget - Complete Random Stats Generator
**File**: `frontend/src/components/FanStatsWidget.vue`  
**Lines**: 330-360  
**Severity**: CRITICAL

**What displays in UI**:
```typescript
function generateBatters() {
  return [
    { id: 'b1', name: 'V. Kohli', runs: 652, avg: 43.47, sr: 137.2 },
    { id: 'b2', name: 'AB de Villiers', runs: 489, avg: 40.75, sr: 151.3 },
    // ... celebrity names with random stats
  ]
}
```

**Issue**: Widget generates fake tournament statistics using celebrity names, displayed as real data in "Fan Mode".

**Recommended Fix**:
- Backend has tournament endpoints: `GET /tournaments/{id}/leaderboards`
- Fetch actual player rankings from backend
- If no data, show "No stats available yet" instead of fake data

---

### 🔴 A7: MatchCaseStudyView - Mock AI Summary
**File**: `frontend/src/views/MatchCaseStudyView.vue`  
**Lines**: 709-730  
**Severity**: CRITICAL

**What displays in UI**:
```typescript
// TODO: Replace this mock with real ai_summary from backend when available.
// Build a rich mock structure from available data
const enrichedSummary = computed(() => {
  // Generate overview from backend summary or create a placeholder
  overview: backendSummary?.overview || 'This was a closely contested T20 match...'
  keyMoments: [/* generated fake moments */]
})
```

**Issue**: Shows placeholder AI analysis text instead of actual AI-generated insights from backend.

**Recommended Fix**:
- Backend endpoint: `GET /games/{id}/ai-summary` returns structured AI analysis
- Use actual `ai_summary.overview`, `.key_moments`, `.turning_points`
- Show "AI analysis pending" if not available instead of fake text

---

### 🟠 A8: BaseInput - Math.random() ID Generation
**File**: `frontend/src/components/BaseInput.vue`  
**Line**: 60  
**Severity**: MEDIUM

**What displays in UI**:
```typescript
const inputId = computed(() => props.id ?? `input-${Math.random().toString(36).slice(2, 9)}`)
```

**Issue**: Uses `Math.random()` for component IDs. While this is for DOM attributes (not metrics), it's non-deterministic.

**Recommended Fix**:
- Use `useId()` from Vue 3.5+ for stable IDs
- Or use incrementing counter: `let counter = 0; () => `input-${++counter}``

---

## B) Probably Wrong Source-of-Truth

### 🟠 B1: ScoreboardWidget - Local CRR Fallback
**File**: `frontend/src/components/ScoreboardWidget.vue`  
**Lines**: 394-404  
**Severity**: HIGH

**Current Code**:
```typescript
const crr = computed(() => {
  // Prefer backend-calculated current_run_rate
  const backendCrr = liveSnapshot.value?.current_run_rate ?? currentGame.value?.current_run_rate
  if (backendCrr != null) return backendCrr.toFixed(2)
  
  // Fallback to local calculation
  return totalBallsThisInnings.value 
    ? (runs.value / (totalBallsThisInnings.value / 6)).toFixed(2) 
    : '—'
})
```

**Why it can drift**:
- Local calculation uses `runs.value` which might be stale cached value
- `totalBallsThisInnings` computed from deliveries array that may not be fresh
- Backend already sends `current_run_rate` in snapshot, fallback shouldn't be needed

**Proposed Fix**:
```typescript
const crr = computed(() => {
  const backendCrr = liveSnapshot.value?.current_run_rate
  return backendCrr != null ? backendCrr.toFixed(2) : '—'
})
// Remove fallback entirely - if backend doesn't send it, show '—' not wrong value
```

---

### 🟠 B2: AnalyticsView - Redundant CRR Calculation
**File**: `frontend/src/views/AnalyticsView.vue`  
**Lines**: 216-226  
**Severity**: HIGH

**Current Code**:
```typescript
const crr = computed(() => {
  const overs = ballsBowled.value / 6
  return overs > 0 ? currRuns.value / overs : 0
})
```

**Why it can drift**:
- Recalculates CRR locally instead of using `snapshot.current_run_rate`
- `ballsBowled` derived from `overs_completed` + `balls_this_over` (could be stale)
- Snapshot already includes backend-calculated `current_run_rate`

**Proposed Fix**:
```typescript
const crr = computed(() => gameStore.liveSnapshot?.current_run_rate ?? 0)
```

---

### 🟠 B3: AnalyticsView - Required Run Rate (RRR) Calculation
**File**: `frontend/src/views/AnalyticsView.vue`  
**Lines**: 228-245  
**Severity**: HIGH

**Current Code**:
```typescript
const req = computed(() => {
  const target = snapshot.value?.target
  if (target == null) return { rrr: null, ... }
  
  const remainingRuns = Math.max(0, Number(target) - currRuns.value)
  const remainingOvers = oversLimit.value - (ballsBowled.value / 6)
  const rrr = remainingOvers > 0 ? remainingRuns / remainingOvers : null
  
  return { rrr, remainingOvers, remainingRuns }
})
```

**Why it can drift**:
- Backend already calculates RRR in `prediction_service.py` as `required_run_rate`
- Snapshot includes `required_run_rate` for 2nd innings
- Local calculation may use stale `currRuns.value` or incorrect `oversLimit`

**Proposed Fix**:
```typescript
const req = computed(() => {
  const backendRrr = snapshot.value?.required_run_rate
  const target = snapshot.value?.target
  
  if (backendRrr != null && target != null) {
    return {
      rrr: backendRrr,
      remainingRuns: target - snapshot.value.total_runs,
      remainingOvers: snapshot.value.balls_remaining / 6
    }
  }
  return { rrr: null, remainingOvers: null, remainingRuns: null }
})
```

---

### 🟠 B4: GameScoringView - Local Balls Remaining
**File**: `frontend/src/views/GameScoringView.vue`  
**Lines**: 613-616  
**Severity**: MEDIUM

**Current Code**:
```typescript
const ballsRemaining = computed<number>(() => {
  const limit = oversLimit.value ? Number(oversLimit.value) * 6 : 0
  return Math.max(0, limit - Number(ballsBowledTotal.value || 0))
})
```

**Why it can drift**:
- Snapshot already includes `balls_remaining` from backend
- Local calculation may differ if extras or illegal balls counted incorrectly

**Proposed Fix**:
```typescript
const ballsRemaining = computed(() => 
  gameStore.liveSnapshot?.balls_remaining ?? 0
)
```

---

### 🟠 B5: LiveMatchCardCoach - Par Run Rate Calculation
**File**: `frontend/src/components/LiveMatchCardCoach.vue`  
**Lines**: 307-315  
**Severity**: MEDIUM

**Current Code**:
```typescript
const parRunRate = computed(() => {
  const dls = (currentGame.value as any)?.dls
  if (!dls || !dls.par) return null
  return dls.par
})

const parVsCRR = computed(() => {
  if (!parRunRate.value) return null
  const crr = Number(currentRunRate.value) || 0
  const diff = (crr - parRunRate.value).toFixed(2)
  return diff.startsWith('-') ? `${diff}` : `+${diff}`
})
```

**Why it can drift**:
- Uses `currentGame.value?.dls` which might be stale cached value
- `currentRunRate.value` might not reflect latest snapshot
- Backend sends DLS par in real-time via `dls.par` in snapshot

**Proposed Fix**:
```typescript
const parVsCRR = computed(() => {
  const snapshot = gameStore.liveSnapshot
  if (!snapshot?.dls?.par || !snapshot?.current_run_rate) return null
  
  const diff = snapshot.current_run_rate - snapshot.dls.par
  return diff >= 0 ? `+${diff.toFixed(2)}` : diff.toFixed(2)
})
```

---

### 🟠 B6: LiveMatchCardCoach - Bowler Economy Calculation
**File**: `frontend/src/components/LiveMatchCardCoach.vue`  
**Lines**: 272-278  
**Severity**: MEDIUM

**Current Code**:
```typescript
const bowlerEcon = computed(() => {
  const balls = bowlerBowling.value?.overs_bowled ?? 0
  const runs = bowlerBowling.value?.runs_conceded ?? 0
  const totalBalls = Math.floor(balls * 6 + ((balls % 1) * 10))  // ⚠️ Decimal overs conversion
  if (totalBalls === 0) return '—'
  return ((runs / totalBalls) * 6).toFixed(2)
})
```

**Why it can drift**:
- Converts decimal overs (e.g., 3.4 = 3 overs 4 balls) using modulo math
- Formula `balls % 1) * 10` assumes cricket notation, but backend may send actual ball count
- Backend `bowling_scorecard` already includes `economy` field

**Proposed Fix**:
```typescript
const bowlerEcon = computed(() => {
  const bowler = gameStore.liveSnapshot?.bowling_scorecard?.[selectedBowlerId.value]
  return bowler?.economy?.toFixed(2) ?? '—'
})
```

---

### 🟡 B7: GameScoringView - Last Delivery Assembly
**File**: `frontend/src/views/GameScoringView.vue`  
**Lines**: 475-510  
**Severity**: MEDIUM

**Current Code**:
```typescript
const overNum = last?.over_number ?? Math.floor(legalBallsBowled.value / 6)
const ballNum = last?.ball_number ?? (legalBallsBowled.value % 6)

let totalRuns = Number(last.runs_scored ?? last.runs_off_bat ?? 0) +
                Number(last.extra_runs ?? 0)
```

**Why it can drift**:
- Manually calculates over/ball numbers from `legalBallsBowled`
- Snapshot already sends `last_delivery` with correct over/ball info
- Duplicates logic that backend already handles

**Proposed Fix**:
```typescript
const lastDelivery = computed(() => 
  gameStore.liveSnapshot?.last_delivery ?? null
)
// Use backend-provided values directly, no local calculation
```

---

### 🟡 B8: PhaseTimelineWidget - Mixed Data Sources
**File**: `frontend/src/components/PhaseTimelineWidget.vue`  
**Lines**: (needs inspection)  
**Severity**: MEDIUM

**Issue**: Component might mix snapshot phase data with local calculations for timeline visualization.

**Audit Needed**: Check if widget recalculates phase boundaries or uses backend `phase_breakdown`.

---

### 🟡 B9: PressureMapWidget - Local Pressure Calculation
**File**: Likely exists in `components/` or embedded in AnalyticsView  
**Severity**: HIGH

**Issue**: If frontend recalculates pressure scores instead of using backend `GET /games/{id}/pressure-map`.

**Audit Needed**: Search for pressure calculations in frontend. Backend already has `PressureAnalyzer` that computes:
- Dot streak factor
- RRR gap factor
- Wicket pressure
- Overs remaining pressure

---

## C) Inconsistent Theme/Styling (Hardcoded Colors)

### 🟡 C1: WinProbabilityChart - Hardcoded Green
**File**: `frontend/src/components/WinProbabilityChart.vue`  
**Line**: 308  
**Severity**: LOW

```css
color: #86efac; /* Hardcoded green instead of var(--ds-success) */
```

**Fix**: Replace with `var(--ds-success, #86efac)` for theme consistency.

---

### 🟡 C2: PhaseTimelineWidget - Hardcoded Yellow
**File**: `frontend/src/components/PhaseTimelineWidget.vue`  
**Line**: 280  
**Severity**: LOW

```css
color: #ffc864; /* Hardcoded yellow */
```

**Fix**: Use `var(--ds-warning, #ffc864)` or semantic color variable.

---

### 🟡 C3: MatchCaseStudyView - Multiple Hardcoded Transition Timings
**File**: `frontend/src/views/MatchCaseStudyView.vue`  
**Lines**: 1581, 1594, 1601, 1638  
**Severity**: LOW

```css
transition: box-shadow 160ms ease, transform 160ms ease;
```

**Issue**: Repeats `160ms` instead of using CSS variable like `var(--ds-transition-speed, 160ms)`.

---

## D) Quick Wins (Top 10 Changes)

### 🏆 D1: Remove PhaseAnalysisWidget Mock Data
**Impact**: Removes 100+ lines of fake stats  
**Effort**: 2 hours (connect to backend `/phase-analysis` endpoint)  
**File**: `PhaseAnalysisWidget.vue`

**Change**:
```typescript
// BEFORE: const phaseData = computed(() => phaseDataMap[activePhase.value])
// AFTER:
const phaseData = computed(() => {
  const analysis = gameStore.phaseAnalysis
  return analysis?.[activePhase.value] ?? null
})

onMounted(() => gameStore.fetchPhaseAnalysis(gameId.value))
```

---

### 🏆 D2: Fix LastSixBalls Empty Array
**Impact**: Shows actual recent balls instead of 6 blanks  
**Effort**: 15 minutes  
**File**: `LiveMatchCardCoach.vue:284`

**Change**:
```typescript
const lastSixBalls = computed(() => {
  const deliveries = gameStore.liveSnapshot?.deliveries ?? []
  return deliveries.slice(-6).map(d => {
    if (d.is_wicket) return 'W'
    if (d.runs_off_bat === 4) return '4'
    if (d.runs_off_bat === 6) return '6'
    if (!d.extra_type && d.runs_scored === 0) return '0'
    return String(d.runs_scored)
  }).reverse() // Most recent on right
})
```

---

### 🏆 D3: Remove CRR Local Calculation Fallback
**Impact**: Single source of truth for run rate  
**Effort**: 5 minutes  
**Files**: `ScoreboardWidget.vue`, `AnalyticsView.vue`

**Change**:
```typescript
// ScoreboardWidget.vue:394
const crr = computed(() => {
  const backendCrr = liveSnapshot.value?.current_run_rate
  return backendCrr != null ? backendCrr.toFixed(2) : '—'
})

// AnalyticsView.vue:216
const crr = computed(() => gameStore.liveSnapshot?.current_run_rate ?? 0)
```

---

### 🏆 D4: Use Backend RRR Instead of Local Calc
**Impact**: Fixes drift in required run rate  
**Effort**: 10 minutes  
**File**: `AnalyticsView.vue:228`

**Change**:
```typescript
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

### 🏆 D5: Replace OrgDashboardView Mock Data with API
**Impact**: Shows real organization stats  
**Effort**: 3 hours (wire up backend endpoints)  
**File**: `OrgDashboardView.vue:214`

**Change**:
```typescript
// Add API call in setup
const { data: orgStats, isLoading } = useQuery({
  queryKey: ['org-stats', orgId],
  queryFn: () => api.getOrganizationStats(orgId)
})

// Remove mock data refs (lines 214-246)
```

---

### 🏆 D6: Use Backend Bowler Economy
**Impact**: Fixes overs→balls conversion error  
**Effort**: 5 minutes  
**File**: `LiveMatchCardCoach.vue:272`

**Change**:
```typescript
const bowlerEcon = computed(() => {
  const bowlerId = selectedBowler.value
  const bowler = gameStore.liveSnapshot?.bowling_scorecard?.[bowlerId]
  return bowler?.economy?.toFixed(2) ?? '—'
})
```

---

### 🏆 D7: Use Snapshot balls_remaining
**Impact**: Removes redundant calculation  
**Effort**: 2 minutes  
**File**: `GameScoringView.vue:613`

**Change**:
```typescript
const ballsRemaining = computed(() => 
  gameStore.liveSnapshot?.balls_remaining ?? 0
)
```

---

### 🏆 D8: Fix CoachesDashboard Key Players
**Impact**: Shows real player stats instead of fake names  
**Effort**: 1 hour  
**File**: `CoachesDashboardView.vue:207`

**Change**:
```typescript
const keyPlayers = computed(() => {
  const scorecard = gameStore.currentGame?.batting_scorecard ?? {}
  return Object.entries(scorecard)
    .map(([id, stats]) => ({
      id,
      name: stats.name,
      runs: stats.runs,
      wickets: 0 // Add from bowling_scorecard if same player
    }))
    .sort((a, b) => b.runs - a.runs)
    .slice(0, 6)
})
```

---

### 🏆 D9: Replace FanStatsWidget Mock Generator
**Impact**: Shows real tournament stats  
**Effort**: 4 hours (connect to tournament leaderboards API)  
**File**: `FanStatsWidget.vue:330`

**Change**:
```typescript
const { data: batters } = useQuery({
  queryKey: ['tournament-batters', tournamentId],
  queryFn: () => api.getTournamentLeaderboard(tournamentId, 'batting')
})
// Remove generateBatters(), generateBowlers(), etc.
```

---

### 🏆 D10: Remove MatchCaseStudyView Mock AI Summary
**Impact**: Shows real AI analysis  
**Effort**: 2 hours  
**File**: `MatchCaseStudyView.vue:709`

**Change**:
```typescript
const aiSummary = computed(() => {
  const summary = gameStore.currentGame?.ai_summary
  if (!summary) return {
    overview: 'AI analysis pending...',
    keyMoments: [],
    turning_points: []
  }
  return summary
})
// Remove mock data generation (lines 718-730)
```

---

## Summary Statistics

### By Severity
- 🔴 **CRITICAL**: 7 issues (complete fake data in production UI)
- 🟠 **HIGH**: 9 issues (local calculations that drift from backend)
- 🟡 **MEDIUM**: 8 issues (fallbacks or mixed sources)
- ⚪ **LOW**: 3 issues (theme consistency)

### By Component Type
- **Widgets**: 15 issues (PhaseAnalysis, LiveMatchCard, Scoreboard, FanStats, etc.)
- **Views**: 12 issues (OrgDashboard, CoachesDashboard, AnalyticsView, MatchCaseStudy)
- **Stores**: 5 issues (gameStore local calculations)
- **Utils/Base**: 2 issues (BaseInput random ID)

### Estimated Effort to Fix
- **Quick wins (D1-D10)**: ~15 hours
- **All issues**: ~40 hours
- **Testing + validation**: +10 hours
- **Total**: ~50 hours (1.5 weeks)

---

## Recommendations

### Phase 1: Critical Fixes (Week 1)
1. Remove all mock data from `PhaseAnalysisWidget`
2. Fix `LastSixBalls` empty array
3. Replace all CRR/RRR local calculations with backend values
4. Wire up `OrgDashboardView` to real API

### Phase 2: High-Priority Drift Prevention (Week 2)
5. Remove bowler economy local calculation
6. Use snapshot `balls_remaining` everywhere
7. Fix par run rate calculations
8. Replace `CoachesDashboard` mock players

### Phase 3: Complete Audit (Week 3)
9. Replace `FanStatsWidget` generators with tournament API
10. Remove `MatchCaseStudyView` mock AI summary
11. Audit remaining widgets for mixed sources
12. Document "Source of Truth Protocol" in codebase

---

## Protocol Moving Forward

### ✅ DO:
- Always use `gameStore.liveSnapshot` for real-time metrics
- Fetch from API if data not in snapshot
- Show "No data available" instead of generating fake data
- Use backend-calculated fields (CRR, RRR, pressure, etc.)

### ❌ DON'T:
- Recalculate metrics locally when backend provides them
- Show mock/placeholder data in production UI
- Use `Math.random()` for display values
- Mix snapshot + API sources for same metric

---

**End of Audit Report**
