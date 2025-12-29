# Current Run Rate & Score Predictor Fix

## Issues Fixed

### 1. Current Run Rate (CRR) Not Calculated
**Problem:** CRR was not being calculated and included in the game snapshot, so it wasn't available in real-time to the frontend.

**Solution:** Added CRR calculation to `snapshot_service.py`:
```python
# Calculate current run rate
total_balls = int(getattr(g, "overs_completed", 0)) * 6 + int(getattr(g, "balls_this_over", 0))
total_runs = int(getattr(g, "total_runs", 0))
current_run_rate = round((total_runs / total_balls) * 6, 2) if total_balls > 0 else 0.0
```

Now `current_run_rate` is included in every snapshot emitted via Socket.IO.

### 2. Score Predictor Not Visible in First Innings
**Problem:** The backend already had score predictor logic for first innings (using `t20_score_predictor.pkl` and `odi_score_predictor.pkl`), but the frontend widget only showed win probability bars.

**Solution:** Enhanced `WinProbabilityChart.vue` to:
- Detect first innings (no target set)
- Display **Score Prediction** instead of Win Probability
- Show projected final score with comparison to par score
- Display appropriate key factors for each innings

## Changes Made

### Backend: `backend/services/snapshot_service.py`
- Added `current_run_rate` calculation based on total runs and balls
- Formula: `(total_runs / total_balls) * 6` rounded to 2 decimal places
- Returns 0.0 if no balls bowled yet
- Included in snapshot payload sent to all connected clients

### Frontend: `frontend/src/components/WinProbabilityChart.vue`

**Template Changes:**
- Dynamic title: "Score Prediction" (1st innings) vs "Win Probability" (2nd innings)
- Conditional rendering:
  - First innings: Large purple gradient card showing projected score
  - Second innings: Team probability bars (existing functionality)
- Updated factors section:
  - First innings: Shows CRR, wickets left, balls left
  - Second innings: Shows RRR, CRR, runs needed, balls left, wickets left

**Script Changes:**
- Added `currentGame` from store (via storeToRefs)
- Added `isFirstInnings` computed property (checks if `target` is null)
- Added `currentRunRate` computed property (reads from `currentGame.current_run_rate`)

**Style Changes:**
- Added `.score-prediction` styles with purple gradient background
- Added `.projected-score` with centered layout
- Added `.above-par` (green) and `.below-par` (red) color classes

## How It Works

### First Innings Flow
1. Backend calculates projected score using ML model
2. Compares to par score (160 for T20, 270 for ODI)
3. Returns prediction with `factors.projected_score` and `factors.par_score`
4. Frontend displays large score card with projection and difference from par
5. Shows CRR and wickets/balls remaining in factors grid

### Second Innings Flow
1. Backend calculates win probability using target-based ML model
2. Returns batting/bowling team probabilities
3. Frontend displays animated probability bars
4. Shows RRR, CRR, runs needed, balls/wickets remaining in factors grid

## Real-Time Updates

Both CRR and predictions update automatically after every delivery:
1. Delivery scored → `scoring_service.py` updates game state
2. Snapshot built → includes new `current_run_rate`
3. Prediction calculated → uses score predictor (1st innings) or win predictor (2nd innings)
4. Socket.IO emission → `state:update` and `prediction:update` events
5. Frontend updates → widget re-renders with new data

## User Experience

**Scorers** see the widget in the Analytics tab of GameScoringView:
- Chart mode enabled (historical trend shown)
- Full metrics visible

**Viewers** see the widget in ScoreboardWidget:
- Compact mode (no historical chart)
- Key metrics still visible
- Updates in real-time with no refresh needed

## Testing Checklist

- [x] Backend CRR calculation added to snapshot
- [x] Frontend detects first vs second innings correctly
- [x] Score prediction displayed for first innings
- [x] Win probability displayed for second innings
- [x] CRR shown in both innings
- [ ] Manual testing: Create T20 game, score deliveries, verify CRR updates
- [ ] Manual testing: Complete first innings, verify score predictor shows
- [ ] Manual testing: Start second innings, verify win predictor shows
- [ ] Manual testing: Check viewer scoreboard shows same data

## ML Models Used

- **First Innings:** `backend/ml_models/t20_score_predictor.pkl` or `odi_score_predictor.pkl`
- **Second Innings:** `backend/ml_models/t20_win_predictor.pkl` or `odi_win_predictor.pkl`

All models are bundled in Docker image and loaded at startup.

## Files Modified

1. `backend/services/snapshot_service.py` - Added CRR calculation
2. `frontend/src/components/WinProbabilityChart.vue` - Enhanced UI for both innings types

## Next Steps

1. Test manually with Docker containers (already running)
2. Verify CRR updates immediately after first delivery
3. Verify score predictor appears in first innings
4. Verify win predictor appears in second innings
5. Commit changes to git
6. Continue with remaining Week 5 AI features (Innings Grade, Pressure Mapping, etc.)
