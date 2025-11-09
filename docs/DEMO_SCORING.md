# Core Scoring System Demo

This document demonstrates the core scoring system with real examples.

## Quick Start Demo

### 1. Start the Backend

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variable for in-memory mode (optional for quick testing)
export CRICKSY_IN_MEMORY_DB=1

# Start the server
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Create a Game

```bash
curl -X POST http://localhost:8000/games \
  -H "Content-Type: application/json" \
  -d '{
    "match_type": "limited",
    "overs_limit": 20,
    "team_a_name": "Mumbai Indians",
    "team_b_name": "Chennai Super Kings",
    "players_a": ["Rohit", "Ishan", "SKY", "Hardik", "Pollard", "Krunal", "Bumrah", "Boult", "Chahar", "Coulter-Nile", "Pattinson"],
    "players_b": ["Dhoni", "Raina", "Rayudu", "Jadeja", "Bravo", "Watson", "Chahar", "Tahir", "Harbhajan", "Ngidi", "Thakur"],
    "toss_winner_team": "Mumbai Indians",
    "decision": "bat"
  }'
```

Save the returned `game_id` for subsequent requests.

### 3. Score Some Deliveries

#### First Ball - Dot Ball
```bash
curl -X POST http://localhost:8000/games/{game_id}/deliveries \
  -H "Content-Type: application/json" \
  -d '{
    "striker_id": "{rohit_id}",
    "non_striker_id": "{ishan_id}",
    "bowler_id": "{chahar_id}",
    "runs_scored": 0,
    "runs_off_bat": 0,
    "is_wicket": false
  }'
```

#### Second Ball - Four Runs
```bash
curl -X POST http://localhost:8000/games/{game_id}/deliveries \
  -H "Content-Type: application/json" \
  -d '{
    "striker_id": "{rohit_id}",
    "non_striker_id": "{ishan_id}",
    "bowler_id": "{chahar_id}",
    "runs_scored": 4,
    "runs_off_bat": 0,
    "is_wicket": false
  }'
```

#### Third Ball - Wide
```bash
curl -X POST http://localhost:8000/games/{game_id}/deliveries \
  -H "Content-Type: application/json" \
  -d '{
    "striker_id": "{rohit_id}",
    "non_striker_id": "{ishan_id}",
    "bowler_id": "{chahar_id}",
    "runs_scored": 1,
    "extra": "wd",
    "is_wicket": false
  }'
```

#### Fourth Ball - Wicket (Bowled)
```bash
curl -X POST http://localhost:8000/games/{game_id}/deliveries \
  -H "Content-Type: application/json" \
  -d '{
    "striker_id": "{rohit_id}",
    "non_striker_id": "{ishan_id}",
    "bowler_id": "{chahar_id}",
    "runs_scored": 0,
    "runs_off_bat": 0,
    "is_wicket": true,
    "dismissal_type": "bowled",
    "dismissed_player_id": "{rohit_id}"
  }'
```

### 4. View Current Snapshot

```bash
curl http://localhost:8000/games/{game_id}/snapshot
```

Expected response structure:
```json
{
  "id": "game-123",
  "status": "in_progress",
  "score": {
    "runs": 5,
    "wickets": 1,
    "overs": 0.3
  },
  "batsmen": {
    "striker": {
      "id": "ishan_id",
      "name": "Ishan",
      "runs": 0,
      "balls": 0
    },
    "non_striker": {
      "id": "rohit_id",
      "name": "Rohit",
      "runs": 4,
      "balls": 2,
      "is_out": true
    }
  },
  "current_bowler": {
    "id": "chahar_id",
    "name": "Chahar",
    "overs": 0.3,
    "runs": 5,
    "wickets": 1
  }
}
```

### 5. Undo Last Delivery

```bash
curl -X POST http://localhost:8000/games/{game_id}/undo-last
```

The wicket is now undone, and the state is back to:
- Runs: 5 (dot + 4 + wide)
- Wickets: 0
- Overs: 0.2
- Rohit is back at the crease with 4 runs off 2 balls

### 6. View Delivery History

```bash
curl http://localhost:8000/games/{game_id}/deliveries?limit=10
```

Returns all deliveries in reverse chronological order.

### 7. View Recent Deliveries

```bash
curl http://localhost:8000/games/{game_id}/recent_deliveries?limit=3
```

Returns the 3 most recent deliveries.

## WebSocket Real-Time Updates

Connect to WebSocket for live updates:

```javascript
import io from 'socket.io-client';

const socket = io('http://localhost:8000');

// Join game room
socket.emit('join', {
  game_id: 'game-123',
  role: 'SCORER',
  name: 'John Doe'
});

// Listen for state updates
socket.on('state:update', (data) => {
  console.log('Game updated:', data.snapshot);
  // Update UI with new scores
});

// Listen for presence updates
socket.on('presence:update', (data) => {
  console.log('Connected users:', data.members);
});
```

## Running Tests

```bash
cd backend

# Run all core scoring tests
CRICKSY_IN_MEMORY_DB=1 python -m pytest tests/test_core_scoring.py tests/test_scoring_integration.py -v

# Run specific test
CRICKSY_IN_MEMORY_DB=1 python -m pytest tests/test_core_scoring.py::test_score_one_legal_delivery -v

# Run with coverage
CRICKSY_IN_MEMORY_DB=1 python -m pytest tests/test_core_scoring.py --cov=backend/services/scoring_service --cov-report=html
```

## Common Scenarios

### Complete Over (6 Legal Balls)

```bash
# Ball 1: 1 run
curl -X POST http://localhost:8000/games/{game_id}/deliveries -d '{...runs: 1...}'

# Ball 2: Dot
curl -X POST http://localhost:8000/games/{game_id}/deliveries -d '{...runs: 0...}'

# Ball 3: Wide (doesn't count)
curl -X POST http://localhost:8000/games/{game_id}/deliveries -d '{...extra: "wd"...}'

# Ball 3 (retry): 4 runs
curl -X POST http://localhost:8000/games/{game_id}/deliveries -d '{...runs: 4...}'

# Ball 4: 2 runs
curl -X POST http://localhost:8000/games/{game_id}/deliveries -d '{...runs: 2...}'

# Ball 5: 6 runs
curl -X POST http://localhost:8000/games/{game_id}/deliveries -d '{...runs: 6...}'

# Ball 6: 1 run (over complete)
curl -X POST http://localhost:8000/games/{game_id}/deliveries -d '{...runs: 1...}'

# After 6th ball: overs_completed = 1, balls_this_over = 0
```

### Consecutive Scoring and Undo

```bash
# Score 3 balls
for i in 1 2 3; do
  curl -X POST http://localhost:8000/games/{game_id}/deliveries -d '{...}'
done

# View deliveries
curl http://localhost:8000/games/{game_id}/deliveries

# Undo last delivery
curl -X POST http://localhost:8000/games/{game_id}/undo-last

# Now only 2 deliveries remain
curl http://localhost:8000/games/{game_id}/deliveries
```

### Error Handling

#### Try to undo with no deliveries
```bash
curl -X POST http://localhost:8000/games/{game_id}/undo-last

# Response: 409 Conflict
{
  "detail": "Nothing to undo"
}
```

#### Try to use invalid player IDs
```bash
curl -X POST http://localhost:8000/games/{game_id}/deliveries \
  -d '{
    "striker_id": "invalid-id",
    "bowler_id": "another-invalid-id",
    ...
  }'

# Response: 404 Not Found
{
  "detail": "Unknown player name or ID"
}
```

## Performance Benchmarks

Based on test results:

- **Scoring a delivery**: < 10ms
- **Undo operation** (100 deliveries): < 50ms
- **Undo operation** (300 deliveries): < 150ms
- **WebSocket emit**: < 5ms
- **Snapshot generation**: < 20ms

## Next Steps

1. Open `http://localhost:8000/docs` for interactive API documentation
2. Use the Swagger UI to test endpoints interactively
3. Connect the frontend application for full UI experience
4. Monitor WebSocket events in browser DevTools
5. Check logs for real-time scoring activity

## Troubleshooting

### Issue: "Module not found" errors
**Solution**: Ensure you're in the correct directory and have installed dependencies:
```bash
cd backend
pip install -r requirements.txt
```

### Issue: "Game not found" (404)
**Solution**: Verify the game_id exists:
```bash
curl http://localhost:8000/games
```

### Issue: "Nothing to undo" (409)
**Solution**: Check that deliveries exist:
```bash
curl http://localhost:8000/games/{game_id}/deliveries
```

### Issue: WebSocket not connecting
**Solution**: Check CORS settings in backend/app.py and ensure frontend URL is allowed.

## Additional Resources

- API Documentation: http://localhost:8000/docs
- Core Scoring Architecture: `/docs/CORE_SCORING_SYSTEM.md`
- Test Suite: `/backend/tests/test_core_scoring.py`
- Integration Tests: `/backend/tests/test_scoring_integration.py`
