# Delivery Correction - Manual QA Test Plan

## Overview
End-to-end delivery correction allows scorers to fix mistakes in previously scored deliveries without recreating the entire innings. The system replays all deliveries after correction to ensure accurate scorecards, totals, and analytics.

## Test Environment Setup
1. Start backend: `uvicorn backend.main:app --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Create a test match with at least 2 teams (3 players each minimum)
4. Start scoring from the game scoring page

---

## Test Case 1: Wide to Legal Ball Correction

**Objective**: Verify that correcting a wide delivery to a legal ball updates totals and ball count correctly.

**Steps**:
1. Score a **wide (WD)** delivery with 1 run
   - Click "Wide" button
   - Runs: 1
   - Submit delivery
2. **Verify Initial State**:
   - ✅ Total runs should be **1**
   - ✅ Overs display should still be **0.0** (wide doesn't count as legal ball)
   - ✅ Recent balls should show **WD** badge
   - ✅ Extras tab should show: Wides = 1
3. Score a **legal 1 run** delivery
   - Runs: 1
   - Submit delivery
4. **Verify After Legal Ball**:
   - ✅ Total runs: **2** (1 WD + 1 legal)
   - ✅ Overs: **0.1**
   - ✅ Recent balls should show **BOTH** WD and 1
5. **Click the WD badge** in Recent Balls to open correction modal
6. **Correct the delivery**:
   - Change Extra Type: **None (legal ball)**
   - Runs Scored: **1**
   - Click "Save Correction"
7. **Verify After Correction**:
   - ✅ Total runs: **2** (unchanged, but now 1 + 1 legal)
   - ✅ Overs: **0.2** (now 2 legal balls)
   - ✅ Recent balls: Both deliveries show as **1** (no WD badge)
   - ✅ Extras tab: Wides = **0**
   - ✅ CRR (Current Run Rate) updates to reflect 2 legal balls

**Expected Result**: ✅ Wide converted to legal ball, ball count incremented, extras total decremented, CRR recalculated.

---

## Test Case 2: Correct Runs on Past Delivery

**Objective**: Verify that changing the runs on a past delivery recalculates all totals and scorecard.

**Steps**:
1. Score 3 legal deliveries:
   - Ball 1: **2 runs**
   - Ball 2: **0 runs** (dot)
   - Ball 3: **4 runs**
2. **Verify Initial State**:
   - ✅ Total runs: **6**
   - ✅ Overs: **0.3**
   - ✅ Batter 1 runs: **6**
   - ✅ CRR: **12.0** (6 runs in 0.5 overs)
3. **Click Ball 1** (2 runs) in Recent Balls
4. **Correct to 6 runs** (change 2 → 6):
   - Runs Scored: **6**
   - Click "Save Correction"
5. **Verify After Correction**:
   - ✅ Total runs: **10** (6 + 0 + 4)
   - ✅ Overs: **0.3** (unchanged, legal balls stay the same)
   - ✅ Batter 1 runs: **10**
   - ✅ CRR: **20.0** (10 runs in 0.5 overs)
   - ✅ Recent balls: First badge now shows **6** instead of **2**

**Expected Result**: ✅ Past delivery corrected, totals recalculated, scorecard updated, CRR reflects new total.

---

## Test Case 3: Correct Wicket Status

**Objective**: Verify adding/removing wicket status updates scorecards and wicket count.

**Steps**:
1. Score a **non-wicket delivery**:
   - Runs: 0
   - Wicket: **unchecked**
   - Submit
2. **Verify Initial State**:
   - ✅ Total wickets: **0**
   - ✅ Recent balls: **0** (dot, no W badge)
3. **Click the dot ball** in Recent Balls
4. **Add wicket**:
   - Check "Wicket"
   - Dismissal Type: **Bowled**
   - Click "Save Correction"
5. **Verify After Adding Wicket**:
   - ✅ Total wickets: **1**
   - ✅ Recent balls: **W** badge
   - ✅ Batting scorecard: Batter 1 is **out**
   - ✅ Bowling scorecard: Bowler 1 wickets = **1**
   - ✅ UI prompts for **new batter selection**

**Expected Result**: ✅ Wicket added, scorecards updated, UI reflects need for new batter.

---

## Test Case 4: No-Ball to Legal Ball Correction

**Objective**: Verify no-ball corrections handle runs_off_bat correctly.

**Steps**:
1. Score a **no-ball** with 4 runs off bat:
   - Click "No Ball"
   - Runs off Bat: **4**
   - Submit (total = 5: 1 penalty + 4 off bat)
2. **Verify Initial State**:
   - ✅ Total runs: **5**
   - ✅ Overs: **0.0** (no-ball doesn't count)
   - ✅ Recent balls: **NB4** badge
   - ✅ Extras tab: No Balls = 1
3. **Click NB4 badge** in Recent Balls
4. **Correct to legal 4**:
   - Extra Type: **None**
   - Runs Scored: **4**
   - Click "Save Correction"
5. **Verify After Correction**:
   - ✅ Total runs: **4** (penalty removed)
   - ✅ Overs: **0.1** (now legal ball)
   - ✅ Recent balls: **4** badge (no NB prefix)
   - ✅ Extras tab: No Balls = **0**

**Expected Result**: ✅ No-ball converted, penalty run removed, ball count updated.

---

## Test Case 5: Undo Last Still Works

**Objective**: Ensure delivery correction doesn't break the Undo Last functionality.

**Steps**:
1. Score **3 deliveries** (e.g., 1, 2, 4)
2. **Correct the 2nd delivery** (2 → 6)
3. **Verify**: Total runs = **11** (1 + 6 + 4)
4. **Click "Undo Last"** button
5. **Verify After Undo**:
   - ✅ Total runs: **7** (1 + 6)
   - ✅ Overs: **0.2**
   - ✅ Recent balls: Only 2 deliveries shown (4-run delivery removed)
6. **Score another delivery** (e.g., 1 run)
7. **Verify**: Total runs = **8** (1 + 6 + 1)

**Expected Result**: ✅ Undo removes last delivery correctly even after corrections.

---

## Test Case 6: Real-Time Updates (Multi-Client)

**Objective**: Verify Socket.IO broadcasts correction to all connected clients.

**Setup**: Open 2 browser windows/tabs to the same game.

**Steps**:
1. **Window 1 (Scorer)**: Score a wide (WD)
2. **Window 2 (Viewer)**: Verify WD appears in Recent Balls
3. **Window 1**: Click WD badge → Correct to legal 1 run
4. **Window 2**: **Immediately verify**:
   - ✅ Recent balls updates from **WD** to **1**
   - ✅ Totals update (extras decremented)
   - ✅ Overs count increments

**Expected Result**: ✅ All clients receive real-time correction updates via Socket.IO.

---

## Edge Cases & Error Handling

### EC1: Correct Non-Existent Delivery
**Steps**:
1. Manually call API: `PATCH /games/{game_id}/deliveries/999999`
2. **Expected**: 404 error with message "Delivery 999999 not found"

### EC2: Correct Delivery in Completed Game
**Steps**:
1. Complete a game (finalize match)
2. Try to correct a delivery from completed game
3. **Expected**: 400 error "Cannot correct deliveries in completed game"

### EC3: Correction Modal Closes on Cancel
**Steps**:
1. Click delivery to open correction modal
2. Make changes but click "Cancel"
3. **Verify**: Modal closes, no changes applied

---

## Acceptance Criteria Summary

✅ **All test cases pass**  
✅ **Totals (runs, wickets, overs) recalculate correctly**  
✅ **Scorecards (batting/bowling) update accurately**  
✅ **CRR and analytics reflect corrected state**  
✅ **Socket.IO emits updates to all clients**  
✅ **Undo Last still functions correctly**  
✅ **Error handling for edge cases**  
✅ **UI is responsive and user-friendly**

---

## Test Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| QA Engineer | _________ | ______ | ☐ Pass / ☐ Fail |
| Product Owner | _________ | ______ | ☐ Approved |
| Developer | _________ | ______ | ☐ Verified |

**Notes**:
