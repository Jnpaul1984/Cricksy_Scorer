# AI Win/Loss Prediction Feature

## Overview

The AI Win/Loss Prediction feature provides real-time probability calculations for cricket match outcomes. It uses a cricket-specific algorithm that considers multiple factors to determine the likelihood of each team winning.

## Architecture

### Backend Components

#### 1. Prediction Service (`backend/services/prediction_service.py`)

The core prediction engine that calculates win probabilities.

**Key Functions:**
- `WinProbabilityPredictor.calculate_win_probability()`: Main prediction method
- `get_win_probability()`: Convenience wrapper for game state dictionaries

**Algorithm Factors:**
- Current run rate vs required run rate
- Wickets remaining
- Balls remaining
- Target gap (when chasing)
- Match momentum and wicket pressure
- Over limit and match format

**Prediction Logic:**

*First Innings:*
- Projects final score based on current performance
- Compares to par scores (T20: 160, ODI: 270)
- Factors in wickets fallen and overs remaining
- Confidence increases with match progression (max 70%)

*Second Innings:*
- Calculates required run rate
- Assesses wicket pressure and ball pressure
- Considers achievability of target
- Higher confidence as match nears conclusion (max 95%)

#### 2. API Endpoint (`backend/routes/prediction.py`)

RESTful endpoint for fetching predictions:
```
GET /predictions/games/{game_id}/win-probability
```

Response format:
```json
{
  "batting_team_win_prob": 65.5,
  "bowling_team_win_prob": 34.5,
  "confidence": 75.0,
  "batting_team": "Team A",
  "bowling_team": "Team B",
  "game_id": "uuid",
  "factors": {
    "runs_needed": 45,
    "balls_remaining": 30,
    "required_run_rate": 9.0,
    "current_run_rate": 8.33,
    "wickets_remaining": 6
  }
}
```

#### 3. Socket Integration (`backend/services/live_bus.py`)

Real-time updates via WebSocket:
- Event: `prediction:update`
- Emitted after every delivery scored
- Payload includes full prediction data

Updated in `backend/routes/gameplay.py` after each ball is scored.

### Frontend Components

#### 1. Win Probability Widget (`frontend/src/components/WinProbabilityWidget.vue`)

Main display component showing:
- Current win probabilities for both teams
- Animated probability bars
- Confidence level indicator
- Contributing factors breakdown
- Real-time chart (optional)

**Props:**
- `prediction`: Current prediction object
- `battingTeam`: Batting team name
- `bowlingTeam`: Bowling team name
- `theme`: UI theme (dark/light)
- `showChart`: Toggle chart display
- `compact`: Compact mode flag

**Features:**
- Color-coded probability bars (green > 70%, yellow 50-70%, red < 50%)
- Responsive grid layout for factors
- Smooth transitions on updates

#### 2. Win Probability Chart (`frontend/src/components/analytics/WinProbabilityChart.vue`)

Line chart showing probability trends:
- Uses Chart.js for rendering
- Tracks probability history over match progress
- Filled area charts for visual clarity
- Interactive tooltips
- Maintains last 50 data points

**Chart Features:**
- Dual lines for both teams
- Y-axis: 0-100% probability
- X-axis: Match progress
- Theme-aware colors
- Responsive sizing

#### 3. Store Integration (`frontend/src/stores/gameStore.ts`)

State management for predictions:
- `currentPrediction`: Reactive prediction state
- Socket handler: `prediction:update`
- Automatic updates on live scoring events

## Usage

### Backend Usage

```python
from backend.services.prediction_service import get_win_probability

game_state = {
    "current_inning": 2,
    "total_runs": 120,
    "total_wickets": 4,
    "overs_completed": 15,
    "balls_this_over": 3,
    "overs_limit": 20,
    "target": 160,
    "match_type": "limited",
}

prediction = get_win_probability(game_state)
print(f"Batting team win probability: {prediction['batting_team_win_prob']}%")
```

### Frontend Usage

```vue
<template>
  <WinProbabilityWidget
    :prediction="currentPrediction"
    :batting-team="battingTeamName"
    :bowling-team="bowlingTeamName"
    theme="dark"
    :show-chart="true"
  />
</template>

<script setup>
import { storeToRefs } from 'pinia'
import { useGameStore } from '@/stores/gameStore'
import WinProbabilityWidget from '@/components/WinProbabilityWidget.vue'

const gameStore = useGameStore()
const { currentPrediction } = storeToRefs(gameStore)
</script>
```

## Testing

### Backend Tests

Run prediction service tests:
```bash
cd backend
python -m pytest tests/test_prediction_service.py -v
```

**Test Coverage:**
- 15 comprehensive unit tests
- First innings scenarios (early, strong, weak positions)
- Second innings scenarios (target achieved, all out, comfortable/difficult chases)
- Edge cases (no overs limit, no target)
- Probability sum validation
- Confidence progression
- Factor inclusion

### Frontend Tests

Run component tests:
```bash
cd frontend
npm run test:unit
```

**Test Coverage:**
- Widget rendering with/without predictions
- Probability display accuracy
- Compact vs full mode
- Theme application
- Factor display logic
- Edge cases and null handling

## Configuration

No configuration required. The feature is automatically enabled and works with existing match data.

**Customization Options:**
- Par scores can be adjusted in `prediction_service.py`
- Chart retention limit (default: 50 points) in `WinProbabilityChart.vue`
- Probability color thresholds in `WinProbabilityWidget.vue`

## Performance

- Prediction calculation: < 1ms per call
- Socket emission: Non-blocking, error-contained
- Chart rendering: Optimized with Chart.js
- Memory usage: Minimal (tracks last 50 points)

## Future Enhancements

Potential improvements:
1. Machine learning model integration
2. Historical match data training
3. Player form consideration
4. Weather/pitch condition factors
5. Innings momentum analysis
6. DLS adjustment integration
7. Export prediction history
8. Prediction accuracy tracking

## Troubleshooting

**Predictions not updating:**
- Verify WebSocket connection is established
- Check that `initLive()` was called in gameStore
- Ensure game has `overs_limit` set

**Confidence always 0:**
- Check match has progressed beyond 2 overs
- Verify required data (overs_limit, target for inning 2) is present

**Chart not displaying:**
- Ensure `showChart` prop is true
- Verify Chart.js is imported correctly
- Check theme prop is set

## API Integration

For external integrations, use the REST endpoint:

```bash
curl http://localhost:8000/predictions/games/{game_id}/win-probability
```

The endpoint requires:
- Valid game ID
- Game must be in progress or completed
- Returns 404 if game not found
- Returns neutral prediction (50/50) if insufficient data

## License

Part of Cricksy Scorer application. See main LICENSE file.
