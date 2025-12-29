# CRR & Score Predictor Troubleshooting Guide

**Issue**: User not seeing CRR in scoreboard or Score Predictor widget despite backend sending data correctly.

## ✅ Backend Confirmed Working

- API: `GET /games/{id}/snapshot` returns `current_run_rate: 24` ✓
- Calculation: 4 runs in 1 ball = 24 run rate (correct) ✓  
- Socket.IO: `emit_prediction_update()` called after each delivery ✓
- Deliveries: 1 delivery scored in game ✓

## 🔍 Frontend Checks Required

### 1. Socket.IO Connection (CRITICAL)

Open browser DevTools (F12) → Network tab → WS filter

**Expected**:
- Connection to `ws://localhost:8000/socket.io/` (NOT port 5173)
- Status: Connected (green circle)
- Messages showing `state:update` and `prediction:update` events

**If NOT connected to port 8000**:
- Check `frontend/.env` exists with `VITE_SOCKET_URL=http://localhost:8000`
- Hard refresh browser: `Ctrl + Shift + R`
- Restart Vite dev server if needed

### 2. CRR Display in Scoreboard

**Where to Look**:
ScoreboardWidget → Info Strip (below bowler stats, above scorecards)

**Expected HTML** (Inspect Element - F12):
```html
<div class="info-strip">
  <div class="cell" data-testid="scoreboard-crr">
    <span class="lbl">CRR</span> <strong>24.00</strong>
  </div>
</div>
```

**If CRR element exists but invisible**:
- Check CSS: `.info-strip .cell` should have `display: block` or `flex`
- Check `v-if="showCrr"` condition: `totalBallsThisInnings > 0` (should be true with 1 ball)
- Check computed `crr.value` in Vue DevTools

**If CRR element doesn't exist**:
- Check `liveSnapshot.current_run_rate` in Vue DevTools gameStore
- Should be `24` (number) not string
- Verify ScoreboardWidget is using `liveSnapshot` ref

### 3. Score Predictor in Win Probability Widget

**Where to Look**:
GameScoringView → Analytics Tab → Win Probability Card

**Expected Display**:
- Title: "Score Prediction" (NOT "Win Probability" for first innings)
- Large number showing "Projected Final Score"
- Par Score comparison
- Key Factors section with "Current RR: 24.00"

**If showing "Win Probability" instead**:
- Check `currentGame.target` in Vue DevTools
- Should be `null` or `undefined` for first innings
- If target exists, backend thinks it's second innings

**If empty/loading/error**:
- Check `currentPrediction` in Vue DevTools gameStore
- Should have `{ confidence, factors: { projected_score, par_score, current_run_rate } }`
- Check browser console for Socket.IO `prediction:update` events
- Verify Socket.IO connected (see step 1)

## 🛠️ Debug Actions

### Action 1: Vue DevTools Inspection
1. Install Vue DevTools browser extension
2. Open DevTools → Vue tab
3. Find "gameStore" in components or Pinia
4. Expand state and check:
   - `liveSnapshot.current_run_rate` = 24
   - `currentPrediction` has data
   - `currentGame.target` = null

### Action 2: Console Commands
Open browser console (F12) and run:

```javascript
// Check if CRR element exists in DOM
document.querySelector('[data-testid="scoreboard-crr"]')

// Check computed CRR value
const el = document.querySelector('[data-testid="scoreboard-crr"] strong')
console.log('CRR displayed:', el?.textContent)

// Check Socket.IO connection
window.io?.engine?.transport?.name  // Should be 'websocket'
window.io?.connected  // Should be true
```

### Action 3: Network Tab Verification
1. Open DevTools → Network tab
2. Filter: WS (WebSocket)
3. Look for connection to `localhost:8000`
4. Click on connection → Messages tab
5. Should see JSON messages with `state:update` and `prediction:update`

### Action 4: Score a New Delivery
1. In scoring page, score another delivery (any runs)
2. Watch Network → WS → Messages
3. Should see `state:update` with new CRR
4. Should see `prediction:update` with new projected score
5. UI should update immediately

## 🎯 Most Likely Issues

### Issue 1: Browser Cache
**Symptom**: Old JavaScript running without new changes  
**Fix**: Hard refresh `Ctrl + Shift + R` or clear cache

### Issue 2: Socket.IO Wrong Port
**Symptom**: WebSocket connecting to port 5173 instead of 8000  
**Fix**: 
1. Verify `frontend/.env` has `VITE_SOCKET_URL=http://localhost:8000`
2. Restart Vite dev server
3. Hard refresh browser

### Issue 3: Socket.IO Not Connected
**Symptom**: Network tab shows no WebSocket connection  
**Fix**:
1. Check backend running: `docker ps | grep backend`
2. Check browser console for Socket.IO errors
3. Verify `gameStore.initLive()` called on page load

### Issue 4: Component Not Mounted
**Symptom**: WinProbabilityChart not in DOM  
**Fix**:
1. Navigate to Analytics tab in scoring page
2. Check if `<WinProbabilityChart />` in GameScoringView template
3. Verify component imported correctly

### Issue 5: Conditional Rendering
**Symptom**: Elements exist but `v-if` false  
**Fix**:
1. CRR: Check `showCrr` computed (needs `totalBallsThisInnings > 0`)
2. Predictor: Check `prediction && isFirstInnings` condition
3. Verify game state loaded: `currentGame.value` exists

## 📊 Expected Data Flow

```
User scores delivery
  ↓
POST /games/{id}/deliveries
  ↓
Backend calculates CRR & prediction
  ↓
emit_state_update({current_run_rate: 24})
emit_prediction_update({factors: {projected_score, current_run_rate}})
  ↓
Socket.IO broadcasts to room
  ↓
Frontend gameStore receives events
  ↓
Updates refs: liveSnapshot, currentPrediction
  ↓
Vue reactivity triggers component re-render
  ↓
ScoreboardWidget shows CRR 24.00
WinProbabilityChart shows Score Prediction
```

## 🔧 Quick Fixes to Try

1. **Hard Refresh Browser**: `Ctrl + Shift + R` (clears JavaScript cache)
2. **Restart Vite**: `Ctrl+C` in terminal, then `npm run dev`
3. **Check .env file**: `cat frontend/.env` should show `VITE_SOCKET_URL=http://localhost:8000`
4. **Score new delivery**: Trigger fresh Socket.IO emissions
5. **Check Vue DevTools**: Verify data in gameStore state

## 📝 Files to Check

1. `frontend/.env` - Socket URL configuration
2. `frontend/src/utils/socket.ts` - Socket connection logic
3. `frontend/src/stores/gameStore.ts` - State management, Socket handlers
4. `frontend/src/components/ScoreboardWidget.vue` - CRR display (line 1099)
5. `frontend/src/components/WinProbabilityChart.vue` - Score predictor display

## ✨ Success Criteria

When working correctly, you should see:

1. **CRR in Scoreboard**: "CRR 24.00" in info strip below bowler stats
2. **Score Predictor**: 
   - Title: "Score Prediction"
   - Large projected score number
   - Par score comparison
   - Key Factors with Current RR: 24.00
3. **Real-time updates**: Both update immediately when scoring new deliveries
4. **Socket.IO connected**: Green status in Network → WS tab

## 🆘 If Still Not Working

1. Open `debug_crr_predictor.html` in browser
2. Click "Fetch Snapshot" - should show CRR: 24
3. Click "Fetch Predictions" - should show prediction data
4. Check all sections and report which ones fail

This will isolate whether issue is:
- Backend API (unlikely - we've verified this works)
- Socket.IO connection (most likely)
- Frontend state management
- Component rendering
- CSS/visibility issues
