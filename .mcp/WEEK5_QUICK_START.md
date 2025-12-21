# Week 5 AI Integration - Quick Start Guide

## 🎯 Current Status

✅ **Win Probability API** is already fully implemented and working!

**What exists:**
- API endpoint: `GET /games/{game_id}/predictions/win-probability`
- Real-time Socket.IO emission: `prediction:update` event on every delivery
- ML model integration with fallback to rule-based predictions
- Tests passing in `test_prediction_service.py` and `test_ml_integration.py`

**What's missing:**
- Frontend widget to display the probability curve in Scorer UI
- Viewer integration to show live probability to spectators

---

## 🚀 Recommended Next Steps (Today)

### Option A: Complete Win Probability (Finish this feature completely)
**Time: ~2-3 hours**

1. **Create Frontend Win Probability Widget** (`frontend/src/components/WinProbabilityChart.vue`)
   - Listen to Socket.IO `prediction:update` event
   - Store prediction history (last 50 points per phase)
   - Render Chart.js line chart with:
     - Batting team win probability (blue line)
     - Bowling team win probability (red line)
     - Confidence level indicator
   - Color coding by phase (green powerplay, yellow middle, red death)

2. **Wire up to Scorer UI** (`frontend/src/views/Scorer.vue`)
   - Add prediction widget to right sidebar
   - Display current batting/bowling probabilities
   - Show key factors (RRR, required runs, balls remaining)

3. **Test end-to-end**
   - Score a test delivery
   - Verify Socket.IO event is received
   - Chart updates in real-time

---

### Option B: Start Innings Grade Calculator (Begin next feature)
**Time: ~4-5 hours**

Create a new service to calculate performance grades:

```python
# backend/services/innings_grade_service.py
class InningsGradeCalculator:
    @staticmethod
    def calculate_grade(
        runs_scored: int,
        wickets_lost: int,
        overs_completed: int,
        overs_limit: int,
        match_format: str,  # "t20", "odi", "test"
    ) -> dict[str, Any]:
        """
        Calculate innings grade (A+, A, B, C, D)

        Based on:
        - Run rate vs par score
        - Wickets lost (penalty)
        - Boundary percentage
        - Consistency (if multiple batters)
        """
        par_score = get_par_score(match_format, overs_limit)
        # ... grading logic
        return {
            "grade": "A+",
            "grade_value": 95.0,
            "factors": {...}
        }
```

---

## 📊 Priority Matrix (Next 7 Days)

| Feature | Effort | Impact | Tier | Priority |
|---------|--------|--------|------|----------|
| Win Prob Widget | 2-3h | High | Free | 🔴 **DO TODAY** |
| Innings Grade | 4-5h | High | Free | 🟡 DO DAY 2 |
| Pressure Map | 5-6h | Medium | Free | 🟡 DO DAY 3 |
| Phase Predictions | 6-7h | Medium | Free | 🟡 DO DAY 4 |
| Tactical Engine | 8-10h | High | Coach Pro | 🟠 DO DAY 5 |
| Dismissal Patterns | 5-6h | Medium | Analyst Pro | 🟠 DO DAY 6 |
| Heatmaps | 7-8h | Medium | Analyst Pro | 🟠 DO DAY 6 |
| Ball Clustering | 6-7h | Low | Analyst Pro | 🟠 DO DAY 6 |
| Sponsor Rotation | 4-5h | Low | Org Pro | 🟠 DO DAY 7 |
| Branding System | 3-4h | Low | Org Pro | 🟠 DO DAY 7 |

---

## 🔧 How to Start

### Start with Win Probability Widget (Quick Win ✅)

1. **Run the server:**
   ```powershell
   cd backend
   $env:PYTHONPATH = "C:\Users\Hp\Cricksy_Scorer"
   $env:CRICKSY_IN_MEMORY_DB = "1"
   uvicorn backend.main:app --reload --port 8000
   ```

2. **Run the frontend:**
   ```powershell
   cd frontend
   npm run dev  # Runs on http://localhost:5173
   ```

3. **Create the widget component:**
   ```typescript
   // frontend/src/components/WinProbabilityChart.vue
   <template>
     <div class="prediction-widget">
       <div class="probability-display">
         <div class="batting-prob">{{ battingProb }}%</div>
         <div class="bowling-prob">{{ bowlingProb }}%</div>
       </div>
       <canvas ref="chartCanvas"></canvas>
     </div>
   </template>

   <script setup lang="ts">
   import { onMounted, ref } from 'vue'
   import { useGameStore } from '@/stores/gameStore'
   import Chart from 'chart.js/auto'

   const gameStore = useGameStore()
   const battingProb = ref(50)
   const bowlingProb = ref(50)
   const chartCanvas = ref<HTMLCanvasElement>()
   let chart: Chart | null = null

   onMounted(() => {
     // Listen for prediction updates
     gameStore.socket?.on('prediction:update', (data: any) => {
       battingProb.value = data.prediction.batting_team_win_prob
       bowlingProb.value = data.prediction.bowling_team_win_prob
       updateChart()
     })
   })

   function updateChart() {
     // Update Chart.js with new probability data
   }
   </script>
   ```

4. **Add to Scorer view:**
   ```vue
   <!-- frontend/src/views/Scorer.vue -->
   <div class="scorer-layout">
     <div class="main-scoring">
       <!-- Existing scoring UI -->
     </div>
     <div class="right-sidebar">
       <WinProbabilityChart />  <!-- NEW -->
     </div>
   </div>
   ```

5. **Test it:**
   - Navigate to Scorer
   - Score a delivery
   - Watch probability chart update in real-time

---

## 📚 Key Files to Reference

**Backend:**
- Win Probability API: `backend/routes/prediction.py:L21`
- Prediction Logic: `backend/services/prediction_service.py:L25`
- Socket.IO Emission: `backend/routes/gameplay.py:L1188-L1220`
- Live Bus: `backend/services/live_bus.py:L32`

**Frontend:**
- Game Store: `frontend/src/stores/gameStore.ts`
- Existing Socket.IO handlers: Look for `prediction:update` listener

**Tests:**
- `backend/tests/test_prediction_service.py`
- `backend/tests/test_ml_integration.py`

---

## ✅ Success Checklist

- [ ] Win Probability widget displays in Scorer UI
- [ ] Real-time updates working on Socket.IO `prediction:update` event
- [ ] Chart shows probability history over match progression
- [ ] Factors displayed clearly (RRR, required runs, etc.)
- [ ] No performance degradation (delivery still <1s)
- [ ] Tested with sample match data

---

## 💡 Notes

- **Win Probability already works:** No need to rebuild the prediction logic—just frontend integration!
- **Socket.IO ready:** Emissions already happening—frontend just needs to listen
- **Database ready:** Game model has all needed fields
- **Tests passing:** Core functionality validated

You're in good shape to finish Win Probability today and move to next features tomorrow! 🚀
