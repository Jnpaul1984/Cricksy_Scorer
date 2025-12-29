# Testing Guide: CRR & Score Predictor

## Quick Test Steps

### Setup (Already Done)
✅ Backend running on http://localhost:8000
✅ Frontend running on http://127.0.0.1:5173
✅ TypeScript compilation clean

### Test 1: Current Run Rate (CRR) Calculation

1. Open http://127.0.0.1:5173/ in your browser
2. Login or create test account
3. Create a new T20 match (or join existing game ID: `c94da473-a40b-4912-a506-5cf9ad34f57f`)
4. Navigate to Analytics tab in scorer view
5. Score first delivery (e.g., 4 runs)

**Expected Result:**
- CRR should show immediately: `(4 runs / 1 ball) × 6 = 24.00`
- Display should update in the "Key Factors" section

6. Score another delivery (e.g., 1 run)

**Expected Result:**
- CRR updates: `(5 runs / 2 balls) × 6 = 15.00`

### Test 2: Score Predictor (First Innings)

1. Continue scoring deliveries in first innings
2. After 2-3 overs, check the Analytics tab

**Expected Result:**
- Widget title shows "**Score Prediction**" (not "Win Probability")
- Large purple gradient card displays:
  - "Projected Final Score" (e.g., 165)
  - "Par Score: 160 (+5)" in green if above par
  - Key Factors: CRR, Wickets Left, Balls Left

3. Open browser dev tools → Network tab → WS (WebSocket)
4. Filter for `prediction:update` events
5. Score another delivery

**Expected Result:**
- WebSocket event shows: `factors.projected_score` value
- `factors.prediction_method: "ml_score_predictor"`

### Test 3: Win Predictor (Second Innings)

1. Complete first innings (score 10 wickets or finish overs)
2. Start second innings
3. Navigate to Analytics tab

**Expected Result:**
- Widget title changes to "**Win Probability**"
- Two team probability bars appear (blue for batting, red for bowling)
- Key Factors show:
  - Required RR
  - Current RR
  - Runs Needed
  - Balls Left
  - Wickets Left

4. Score deliveries to see probabilities change

**Expected Result:**
- Probabilities update in real-time after each delivery
- `factors.prediction_method: "ml_win_predictor"` in WebSocket events

### Test 4: Viewer Scoreboard

1. Open scoreboard in new tab/window: http://127.0.0.1:5173/games/{game_id}/scoreboard
2. Replace `{game_id}` with actual game ID

**Expected Result (First Innings):**
- Compact score prediction widget at bottom
- Shows projected score (no chart)

**Expected Result (Second Innings):**
- Compact win probability widget
- Shows team probabilities
- Updates in real-time

## Verification Checklist

- [ ] CRR shows immediately after first ball
- [ ] CRR updates correctly after each delivery
- [ ] First innings shows "Score Prediction" title
- [ ] Projected score displays with par comparison
- [ ] Second innings shows "Win Probability" title
- [ ] Team probability bars animate
- [ ] WebSocket events include prediction data
- [ ] Viewer scoreboard shows same predictions
- [ ] No console errors in browser

## Browser DevTools Debugging

**Check Predictions:**
```javascript
// In browser console
gameStore.currentPrediction
// Should show object with batting_team_win_prob, factors, etc.

gameStore.currentGame.current_run_rate
// Should show calculated CRR (e.g., 7.85)
```

**Check WebSocket Events:**
1. DevTools → Network → WS tab
2. Click on socket connection
3. Filter Messages for "prediction"
4. Should see `prediction:update` events after each delivery

## Common Issues

**Issue:** CRR shows 0.00
- **Cause:** No balls bowled yet
- **Fix:** Normal behavior, will show after first legal delivery

**Issue:** Score predictor not showing
- **Cause:** Still in second innings, or target already set
- **Fix:** Start fresh T20 game from first innings

**Issue:** Widget not updating
- **Cause:** Socket.IO connection lost
- **Fix:** Refresh browser, check backend logs for connection

**Issue:** TypeScript errors in console
- **Cause:** Hot reload didn't pick up type changes
- **Fix:** Hard refresh (Ctrl+Shift+R) or restart Vite dev server

## Next Steps After Testing

If all tests pass:
1. Commit changes: `git add backend/services/snapshot_service.py frontend/src/components/WinProbabilityChart.vue frontend/src/types/index.ts .mcp/CRR_AND_SCORE_PREDICTOR_FIX.md`
2. Commit message: `feat(week5): Add CRR calculation and score predictor for first innings`
3. Continue with Week 5 remaining features (Innings Grade next)

If issues found:
- Check browser console for JavaScript errors
- Check backend logs: `docker compose logs backend --tail 50`
- Verify WebSocket connection established
- Check Network tab for API errors
