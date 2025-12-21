# Win Probability API - Response Format & Examples

## API Endpoint

```
GET /games/{game_id}/predictions/win-probability
```

**Parameters:**
- `game_id` (path): UUID of the game

**Response:** 200 OK

---

## Response Schema

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
    "wickets_remaining": 4,
    "prediction_method": "ml_win_predictor"
  },
  "batting_team": "Mumbai Indians",
  "bowling_team": "Delhi Capitals",
  "game_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Field Descriptions

| Field | Type | Description | Range |
|-------|------|-------------|-------|
| `batting_team_win_prob` | float | Probability batting team wins | 0-100 |
| `bowling_team_win_prob` | float | Probability bowling team wins | 0-100 |
| `confidence` | float | Model confidence in prediction | 0-100 |
| `factors.runs_needed` | int | Runs required (2nd inns) or projected advantage | Integer |
| `factors.balls_remaining` | int | Balls left in current innings | 0-120 |
| `factors.required_run_rate` | float | RRR (2nd inns only) | 0-99.99 |
| `factors.current_run_rate` | float | Current run rate | 0-20+ |
| `factors.wickets_remaining` | int | Wickets still available | 0-10 |
| `factors.prediction_method` | string | `ml_win_predictor` or `ml_score_predictor` or `rule_based` | Enum |
| `batting_team` | string | Name of batting team | String |
| `bowling_team` | string | Name of bowling team | String |
| `game_id` | string | Game UUID | UUID string |

---

## Example Responses by Scenario

### Scenario 1: First Innings (T20) - Early Stage
**After 12 balls, 45 runs, 0 wickets lost**

```json
{
  "batting_team_win_prob": 52.3,
  "bowling_team_win_prob": 47.7,
  "confidence": 25.0,
  "factors": {
    "projected_score": 168,
    "par_score": 160,
    "current_run_rate": 7.5,
    "wickets_remaining": 10,
    "balls_remaining": 108,
    "prediction_method": "ml_score_predictor"
  },
  "batting_team": "Mumbai",
  "bowling_team": "Delhi",
  "game_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Interpretation:**
- Very early in match (confidence only 25%)
- Current RR (7.5) vs par (7.5) = neutral
- ML projects 168 vs par 160 = slight advantage Mumbai
- 108 balls remaining = lots of time to change

---

### Scenario 2: First Innings (T20) - Middle Overs
**After 12 overs, 95 runs, 2 wickets lost**

```json
{
  "batting_team_win_prob": 62.5,
  "bowling_team_win_prob": 37.5,
  "confidence": 55.0,
  "factors": {
    "projected_score": 178,
    "par_score": 160,
    "current_run_rate": 7.92,
    "wickets_remaining": 8,
    "balls_remaining": 48,
    "prediction_method": "ml_score_predictor"
  },
  "batting_team": "Mumbai",
  "bowling_team": "Delhi",
  "game_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Interpretation:**
- Medium confidence (55%) - halfway through innings
- Projected score 178 (+18 above par) = strong
- Lost 2 wickets = some penalty applied
- 8 wickets in hand = runway available
- Mumbai 62.5% likely to post winning total

---

### Scenario 3: First Innings (T20) - Death Overs
**After 18 overs, 150 runs, 3 wickets lost**

```json
{
  "batting_team_win_prob": 70.2,
  "bowling_team_win_prob": 29.8,
  "confidence": 68.0,
  "factors": {
    "projected_score": 185,
    "par_score": 160,
    "current_run_rate": 8.33,
    "wickets_remaining": 7,
    "balls_remaining": 12,
    "prediction_method": "ml_score_predictor"
  },
  "batting_team": "Mumbai",
  "bowling_team": "Delhi",
  "game_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Interpretation:**
- High confidence (68%) - almost at end of innings
- Only 2 balls to project from (very certain)
- Projected 185 is strong
- Mumbai 70.2% likely to win (depends on Delhi reply)

---

### Scenario 4: Second Innings (T20) - Early Chase
**Target 160, after 12 balls, 15 runs, 0 wickets**

```json
{
  "batting_team_win_prob": 78.5,
  "bowling_team_win_prob": 21.5,
  "confidence": 45.0,
  "factors": {
    "runs_needed": 145,
    "balls_remaining": 108,
    "required_run_rate": 8.06,
    "current_run_rate": 7.5,
    "wickets_remaining": 10,
    "prediction_method": "rule_based"
  },
  "batting_team": "Delhi",
  "bowling_team": "Mumbai",
  "game_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Interpretation:**
- RRR 8.06 vs CRR 7.5 = slightly ahead of rate
- 10 wickets in hand = very safe
- 145 runs needed from 108 balls = comfortable
- Delhi 78.5% likely to win

---

### Scenario 5: Second Innings (T20) - Tight Chase
**Target 170, after 15 overs, 120 runs, 4 wickets**

```json
{
  "batting_team_win_prob": 42.3,
  "bowling_team_win_prob": 57.7,
  "confidence": 68.0,
  "factors": {
    "runs_needed": 50,
    "balls_remaining": 30,
    "required_run_rate": 10.0,
    "current_run_rate": 8.0,
    "wickets_remaining": 6,
    "prediction_method": "ml_win_predictor"
  },
  "batting_team": "Delhi",
  "bowling_team": "Mumbai",
  "game_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Interpretation:**
- RRR 10.0 vs CRR 8.0 = falling behind required rate
- Only 6 wickets left = pressure mounting
- 50 runs from 30 balls = achievable but not easy
- Mumbai 57.7% likely to win (better position)

---

### Scenario 6: Second Innings (T20) - Final Over
**Target 160, chasing 155 after 19 overs, 5 wickets down**

```json
{
  "batting_team_win_prob": 85.5,
  "bowling_team_win_prob": 14.5,
  "confidence": 95.0,
  "factors": {
    "runs_needed": 5,
    "balls_remaining": 6,
    "required_run_rate": 50.0,
    "current_run_rate": 15.5,
    "wickets_remaining": 5,
    "prediction_method": "ml_win_predictor"
  },
  "batting_team": "Delhi",
  "bowling_team": "Mumbai",
  "game_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Interpretation:**
- Very high confidence (95%) - almost complete match
- Only need 5 runs from 6 balls = massive favorite
- CRR 15.5 >> RRR 50 = comfortable
- Delhi 85.5% likely to win (almost certain)

---

### Scenario 7: Second Innings (T20) - Innings Over, Team Lost
**Target 165, all out for 158**

```json
{
  "batting_team_win_prob": 0.0,
  "bowling_team_win_prob": 100.0,
  "confidence": 100.0,
  "factors": {
    "reason": "All out",
    "wickets_remaining": 0,
    "runs_needed": 7
  },
  "batting_team": "Delhi",
  "bowling_team": "Mumbai",
  "game_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**Interpretation:**
- Match over - definitive result
- All wickets lost = 0% win probability
- Mumbai wins by 7 runs

---

## Socket.IO Event Format

When a delivery is scored, the backend emits:

```json
{
  "event": "prediction:update",
  "data": {
    "game_id": "550e8400-e29b-41d4-a716-446655440000",
    "prediction": {
      "batting_team_win_prob": 65.3,
      "bowling_team_win_prob": 34.7,
      "confidence": 75.5,
      "factors": { ... },
      "batting_team": "Mumbai",
      "bowling_team": "Delhi",
      "game_id": "550e8400-e29b-41d4-a716-446655440000"
    }
  }
}
```

---

## Frontend Integration Example

```typescript
// In your Vue component or Pinia store
import { defineStore } from 'pinia'

export const useGameStore = defineStore('game', () => {
  const predictions = ref<PredictionHistory[]>([])

  socket?.on('prediction:update', (data: any) => {
    const prediction = data.prediction

    // Add to history (keep last 50)
    predictions.value.push(prediction)
    if (predictions.value.length > 50) {
      predictions.value.shift()
    }

    // Update chart
    updateProbabilityChart(predictions.value)
  })

  return {
    predictions
  }
})
```

---

## Error Responses

### 404 - Game Not Found
```json
{
  "detail": "Game not found"
}
```

### 500 - Prediction Calculation Failed
```json
{
  "detail": "Internal server error"
}
```
**Note:** The scoring request will still succeed even if prediction fails—it's non-critical.

---

## Testing the API

### Using curl
```bash
curl -X GET "http://localhost:8000/predictions/games/550e8400-e29b-41d4-a716-446655440000/win-probability" \
  -H "accept: application/json"
```

### Using Swagger UI
1. Visit `http://localhost:8000/docs`
2. Find "predictions" section
3. Expand `GET /predictions/games/{game_id}/win-probability`
4. Enter a valid game_id
5. Click "Try it out"

### Using frontend
```typescript
const response = await fetch('/predictions/games/' + gameId + '/win-probability')
const prediction = await response.json()
console.log(prediction)
```

---

## Performance Notes

- **Prediction calculation:** <100ms (typically 10-50ms)
- **Socket.IO emission:** Non-blocking, sent immediately after delivery scoring
- **Chart update:** Depends on frontend rendering (Chart.js auto-debounces)
- **Historical data:** Stores last 50 predictions per game for trend analysis
