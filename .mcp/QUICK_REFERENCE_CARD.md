# 🚀 Week 5 Quick Reference Card

## TODAY'S TASK: Build Win Probability Frontend Widget

### Time Estimate: 2-3 hours
### Impact: High (enables real-time AI predictions in UI)
### Difficulty: Medium

---

## What You're Building

A Chart.js component that displays live win probability as the match progresses.

**Inputs:** Socket.IO `prediction:update` events
**Output:** Line chart showing batting/bowling team win probability
**Updates:** Real-time with each delivery

---

## Files to Work With

### Create (NEW):
```
frontend/src/components/WinProbabilityChart.vue
```

### Modify:
```
frontend/src/stores/gameStore.ts
  - Add listener for prediction:update event
  - Store prediction history

frontend/src/views/Scorer.vue
  - Import and add <WinProbabilityChart /> component
```

---

## API Response Format

```json
{
  "batting_team_win_prob": 65.3,
  "bowling_team_win_prob": 34.7,
  "confidence": 75.5,
  "factors": {
    "runs_needed": 52,
    "balls_remaining": 48,
    "required_run_rate": 6.5,
    "current_run_rate": 7.2,
    "wickets_remaining": 4
  },
  "batting_team": "Mumbai",
  "bowling_team": "Delhi"
}
```

**Event name:** `prediction:update`
**Frequency:** Once per delivery scored
**Source:** Backend Socket.IO emission

---

## Quick Code Sketch

```vue
<template>
  <div class="prediction-widget">
    <div class="probs">
      <div>{{ battingTeam }}: {{ battingProb }}%</div>
      <div>{{ bowlingTeam }}: {{ bowlingProb }}%</div>
    </div>
    <canvas ref="chartCanvas"></canvas>
    <div class="factors">{{ currentFactors }}</div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useGameStore } from '@/stores/gameStore'
import Chart from 'chart.js/auto'

const gameStore = useGameStore()
const battingProb = ref(50)
const bowlingProb = ref(50)
const battingTeam = ref('')
const bowlingTeam = ref('')
const currentFactors = ref({})
const chartCanvas = ref()

let chart = null
let predictions = []  // Keep last 50

function handlePredictionUpdate(data) {
  const pred = data.prediction

  battingProb.value = pred.batting_team_win_prob
  bowlingProb.value = pred.bowling_team_win_prob
  battingTeam.value = pred.batting_team
  bowlingTeam.value = pred.bowling_team
  currentFactors.value = pred.factors

  predictions.push(pred)
  if (predictions.length > 50) predictions.shift()

  updateChart()
}

function updateChart() {
  if (!chart) createChart()

  chart.data.labels = predictions.map((_, i) => i + 1)
  chart.data.datasets[0].data = predictions.map(p => p.batting_team_win_prob)
  chart.data.datasets[1].data = predictions.map(p => p.bowling_team_win_prob)
  chart.update()
}

function createChart() {
  const ctx = chartCanvas.value
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: [],
      datasets: [
        {
          label: battingTeam.value,
          data: [],
          borderColor: 'blue',
          tension: 0.1
        },
        {
          label: bowlingTeam.value,
          data: [],
          borderColor: 'red',
          tension: 0.1
        }
      ]
    }
  })
}

onMounted(() => {
  gameStore.socket?.on('prediction:update', handlePredictionUpdate)
})
</script>

<style scoped>
.prediction-widget {
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
}

.probs {
  display: flex;
  justify-content: space-around;
  margin-bottom: 20px;
  font-size: 18px;
  font-weight: bold;
}

canvas {
  max-height: 300px;
}

.factors {
  margin-top: 10px;
  font-size: 12px;
  color: #666;
}
</style>
```

---

## Testing Checklist

- [ ] Component creates without errors
- [ ] Socket.IO event listener active
- [ ] Chart renders on first event
- [ ] Chart updates with new data
- [ ] History preserved (last 50 points)
- [ ] Factors display correctly
- [ ] No performance degradation

---

## Common Gotchas

1. **Socket.IO not emitting?**
   - Check backend server is running
   - Verify `emit_prediction_update()` is called in `gameplay.py`

2. **Chart not showing?**
   - Ensure Chart.js is installed: `npm install chart.js`
   - Check canvas ref is set correctly

3. **Data not updating?**
   - Check gameStore has socket reference
   - Verify event name matches: `prediction:update`

4. **Chart library conflict?**
   - Check if Chart.js already used elsewhere
   - Look for naming conflicts

---

## Documentation to Reference

| Document | Use Case |
|----------|----------|
| `WIN_PROBABILITY_API_REFERENCE.md` | See response format & examples |
| `WEEK5_QUICK_START.md` | Full step-by-step guide |
| `WEEK5_SETUP_SUMMARY.md` | Architecture overview |

---

## Success Criteria

✅ Component displays in Scorer UI
✅ Real-time updates on Socket.IO event
✅ Chart shows probability history
✅ Factors visible to user
✅ No errors in console
✅ Scoring speed unaffected (<1s per delivery)

---

## What's Next (After This)

1. **Tomorrow:** Innings Grade Calculator (4-5 hours)
2. **Day 3:** Pressure Mapping (5-6 hours)
3. **Day 4:** Phase Predictions (6-7 hours)
4. **Day 5:** Tactical Engine (8-10 hours)
5. **Days 6-7:** Heatmaps, Clustering, Sponsor Rotation, Branding

See `WEEK5_STATUS.md` for full timeline.

---

## Quick Links

```
Backend Prediction API:
  backend/routes/prediction.py (Line 21)

Socket.IO Emission:
  backend/routes/gameplay.py (Line 1197-1220)

Game Store (Socket.IO ref):
  frontend/src/stores/gameStore.ts

Existing Chart Examples:
  Search for Chart.js usage in project
```

---

**You've got this! 🎯 Let's build an AI-powered cricket platform!** 🏏⚡
