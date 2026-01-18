# Cricksy Frontend Fake/Demo Data Audit Report
**Date**: January 17, 2026
**Audit Scope**: All frontend UI components rendering demo/placeholder data

---

## Executive Summary

Found **4 critical areas** with hardcoded demo data:
1. **AnalystWorkspaceView** - "J. Smith" placeholder in summary
2. **DevDashboardWidget** - Celebrity player cards (Virat Kohli, MS Dhoni, Jasprit Bumrah)
3. **FanFeedWidget** - Hardcoded match highlights with celebrity names
4. **MultiPlayerComparisonWidget** - Celebrity comparison data generator

**Pricing Page**: ✅ **CLEAN** - Correctly wired to backend API with proper error handling

---

## Detailed Findings

### 1. Analyst Workspace View
**File**: `frontend/src/views/AnalystWorkspaceView.vue`

**Page**: `/analyst/workspace`

**Offending Data**:
```vue
Line 128: <p class="aw-summary-label">Top impact bowler</p>
Line 129: <p class="aw-summary-value">{{ summary.topBowler || '—' }}</p>

Line 411: topBowler: 'J. Smith'
```

**Data Flow**:
- Component: `AnalystWorkspaceView.vue`
- Store/Composable: Local reactive `summary` object (lines 408-412)
- API Endpoint: None (hardcoded value)
- Fallback: Shows `'—'` if null

**Fix Recommendation**:
- Remove hardcoded `'J. Smith'`
- Set `topBowler: null` by default
- Compute from `filteredPlayers` array or backend match data
- Display `'Unavailable'` or `'—'` when no data exists

---

### 2. Development Dashboard Widget
**File**: `frontend/src/components/DevDashboardWidget.vue`

**Used In**: `/coach/dashboard` (CoachesDashboardView.vue, line 161)

**Offending Data**:
```javascript
Lines 218-290: enrichedPlayers computed property returns hardcoded array:
- Virat Kohli (player_id: '1', 5500 runs, batting average 55.2)
- Jasprit Bumrah (player_id: '2', 120 wickets)
- MS Dhoni (player_id: '3', 6200 runs, 50 wickets)
```

**Data Flow**:
- Component: `DevDashboardWidget.vue`
- Store/Composable: Props `players` (optional)
- API Endpoint: None (component expects `players` prop from parent)
- Fallback: Generates celebrity demo cards when `props.players` is empty

**Fix Recommendation**:
- Remove `generatePlayers()` fallback logic (lines 218-290)
- Show "No Players" empty state when `props.players` is empty/undefined
- Require parent (CoachesDashboardView) to fetch real player data from backend
- Create `getCoachPlayers()` API endpoint if doesn't exist

---

### 3. Fan Feed Widget
**File**: `frontend/src/components/FanFeedWidget.vue`

**Used In**: `/fan` (FanModeView.vue, line 105)

**Offending Data**:
```javascript
Lines 228-310: generateMockFeed() returns hardcoded array:
- Match: India vs Australia (Virat Kohli 67(48), Maxwell, Bumrah)
- Highlight: "Stunning fielding effort by Virat Kohli"
- News: "Bumrah named Player of Match, Jasprit Bumrah took 3 crucial wickets"
- Match: England vs Pakistan
- Highlight: Rohit Sharma six-hitting
- News: Squad announcement
- Upcoming match: South Africa vs Sri Lanka
```

**Data Flow**:
- Component: `FanFeedWidget.vue`
- Store/Composable: Props `items` (optional)
- API Endpoint: None (component expects `items` prop from parent)
- Fallback: `generateMockFeed()` when `props.items` is undefined (line 319)

**Fix Recommendation**:
- Remove `generateMockFeed()` function entirely
- Show "No Recent Activity" empty state when `props.items` is empty/undefined
- Require parent (FanModeView) to fetch real feed data from backend
- Create `/api/fan/feed` endpoint if doesn't exist

---

### 4. Multi-Player Comparison Widget
**File**: `frontend/src/components/MultiPlayerComparisonWidget.vue`

**Used In**: Unknown (search found no imports - possibly orphaned component)

**Offending Data**:
```javascript
Lines 205-237: generatePlayers() returns hardcoded array:
- Virat Kohli (India)
- Babar Azam (Pakistan)
- Joe Root (England)
- Steve Smith (Australia)
- Rohit Sharma (India)
- Kane Williamson (New Zealand)

With randomized stats: runs, average, strike rate, centuries, etc.
```

**Data Flow**:
- Component: `MultiPlayerComparisonWidget.vue`
- Store/Composable: Computed `allPlayers` calls `generatePlayers()` (line 239)
- API Endpoint: None
- Fallback: Always uses generated data

**Fix Recommendation**:
- **Option A (if used)**: Replace with real player database API call
- **Option B (if orphaned)**: Delete component entirely if not used anywhere

---

## Pricing Page Analysis ✅

**File**: `frontend/src/views/PricingView.vue`

**Page**: `/pricing`

**Status**: **PROPERLY IMPLEMENTED**

**Data Flow**:
```
PricingView.vue
  └─> usePricingStore()
      └─> fetchPricing()
          └─> getAllPricing() from pricingApi.ts
              └─> GET /pricing (backend API)
                  └─> Returns AllPricingResponse
```

**Error Handling**:
```vue
Line 72-76: Proper error state:
<div v-else-if="pricingStore.error" class="pricing-error">
  <p>Unable to load pricing. Please try again later.</p>
</div>
```

**API Endpoint**: `GET ${API_BASE}/pricing` (pricingApi.ts, line 91)

**Fallback Behavior**:
- If API fails: Shows error message "Unable to load pricing"
- Caches pricing data in localStorage for offline resilience (pricingStore.ts, line 131)
- Falls back to cached data if available (lines 142-152)

**Verdict**: ✅ **NO ACTION NEEDED** - Pricing is properly wired to backend

---

## Other Mock Generators Found (Low Priority)

These are **legitimate** generators for visualization/placeholders:

1. **SeasonGraphsWidget.vue** (line 114)
   - `generateMatchData()` - Creates chart data from `props.profile.total_matches`
   - ✅ **OK** - Generates visualization data, not fake content

2. **AnalyticsTablesWidget.vue** (lines 239, 298)
   - `generateManhattanData()`, `generateScatterData()`
   - ✅ **OK** - Creates placeholder chart data (not celebrity names)

3. **ExportUI.vue** (line 240)
   - `generateExportData()` - Formats export data
   - ✅ **OK** - Data transformation, not fake data

---

## Implementation Plan

### Priority 1: Remove Celebrity Demo Cards

**Files to Fix**:
1. ✅ `DevDashboardWidget.vue` - Remove Virat/Dhoni/Bumrah fallback
2. ✅ `FanFeedWidget.vue` - Remove celebrity match highlights
3. ✅ `AnalystWorkspaceView.vue` - Remove "J. Smith" placeholder
4. ✅ `MultiPlayerComparisonWidget.vue` - Delete if unused, or wire to API

### Priority 2: Add Empty States

Replace demo data with proper "No Data" UI:
- DevDashboard: "No players assigned to you yet"
- FanFeed: "No recent cricket activity"
- AnalystWorkspace: Summary shows "—" (already handled)

### Priority 3: Type Safety

Ensure TypeScript compilation passes:
- Remove optional props where data is required
- Add proper type guards for empty arrays

---

## Testing Checklist

After fixes:
- [ ] `/coach/dashboard` shows empty state when no players
- [ ] `/fan` shows empty state when no feed items
- [ ] `/analyst/workspace` shows "—" for missing summary data
- [ ] `/pricing` still loads correctly from API
- [ ] `npm run type-check` passes with 0 errors
- [ ] `npm run build` succeeds

---

## Conclusion

**Total Demo Data Occurrences**: 4 components
**Pricing API**: ✅ Already correct
**Recommended Action**: Remove all celebrity/placeholder names and replace with empty states

