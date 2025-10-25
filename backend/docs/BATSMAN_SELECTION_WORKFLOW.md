# Batsman Selection Workflow Documentation

## Overview

This document explains the batsman selection workflow in the Cricksy Scorer API, specifically how to handle wickets and select new batsmen during a match.

---

## Key Concept: `pending_new_batter` State

The backend uses a `pending_new_batter` flag to enforce proper batsman selection after wickets.

### When It's Set

**Location:** `backend/main.py:1579`

```python
if out_happened and out_player_id:
    out_entry = _ensure_batting_entry(g, out_player_id)
    out_entry["is_out"] = True
    # Block next ball until a new batter is provided
    g.pending_new_batter = True
```

**Trigger:** Automatically set to `True` when:
- A delivery is posted with `is_wicket: true`
- A valid dismissal type is provided
- A batsman is dismissed

### When It's Cleared

**Location:** `backend/main.py:2576`

```python
g.pending_new_batter = False
```

**Trigger:** Cleared when `/next-batter` endpoint is called successfully

---

## Workflow: Posting Deliveries with Wickets

### Step-by-Step Process

#### 1. Post a Normal Delivery (No Wicket)

```http
POST /games/{game_id}/deliveries
Content-Type: application/json

{
  "batsman_id": "player-uuid-1",
  "bowler_id": "player-uuid-2",
  "runs_scored": 0,
  "is_wicket": false
}
```

**Response:** `200 OK`

**State:** `pending_new_batter = false` (no change)

---

#### 2. Post a Wicket Delivery

```http
POST /games/{game_id}/deliveries
Content-Type: application/json

{
  "batsman_id": "player-uuid-1",
  "bowler_id": "player-uuid-2",
  "runs_scored": 0,
  "is_wicket": true,
  "dismissal_type": "caught",
  "fielder_id": "player-uuid-3"  // Optional
}
```

**Response:** `200 OK`

**State Change:** `pending_new_batter = true` ✅

**Important:** The backend accepts this delivery but sets a flag blocking the next delivery.

---

#### 3. Attempt to Post Next Delivery (Without Selecting New Batsman)

```http
POST /games/{game_id}/deliveries
Content-Type: application/json

{
  "batsman_id": "player-uuid-4",
  "bowler_id": "player-uuid-2",
  "runs_scored": 1
}
```

**Response:** `409 Conflict` ❌

```json
{
  "detail": "Select a new batter before scoring the next ball."
}
```

**Reason:** `pending_new_batter = true` blocks new deliveries

---

#### 4. Select New Batsman

```http
POST /games/{game_id}/next-batter
Content-Type: application/json

{
  "batter_id": "player-uuid-5"
}
```

**Response:** `200 OK`

```json
{
  "ok": true,
  "current_striker_id": "player-uuid-5"
}
```

**State Change:** `pending_new_batter = false` ✅

**Effect:**
- New batsman becomes the current striker
- Batting entry created for the new batsman
- Scorecards rebuilt
- State update emitted via WebSocket

---

#### 5. Post Next Delivery (After Selecting New Batsman)

```http
POST /games/{game_id}/deliveries
Content-Type: application/json

{
  "batsman_id": "player-uuid-5",  // The new batsman
  "bowler_id": "player-uuid-2",
  "runs_scored": 4
}
```

**Response:** `200 OK` ✅

**State:** Normal operation resumes

---

## Complete Example: Simulating an Over with a Wicket

### Scenario
- Over 3.1-3.6
- Ball 3.3 is a wicket
- New batsman comes in at 3.4

### API Calls

```javascript
// Ball 3.1 - Normal delivery
POST /games/{game_id}/deliveries
{ "batsman_id": "player-1", "bowler_id": "bowler-1", "runs_scored": 1 }
// ✅ 200 OK

// Ball 3.2 - Normal delivery
POST /games/{game_id}/deliveries
{ "batsman_id": "player-2", "bowler_id": "bowler-1", "runs_scored": 0 }
// ✅ 200 OK

// Ball 3.3 - WICKET!
POST /games/{game_id}/deliveries
{
  "batsman_id": "player-1",
  "bowler_id": "bowler-1",
  "runs_scored": 0,
  "is_wicket": true,
  "dismissal_type": "bowled"
}
// ✅ 200 OK
// ⚠️ pending_new_batter = true

// SELECT NEW BATSMAN (required before next ball)
POST /games/{game_id}/next-batter
{ "batter_id": "player-3" }
// ✅ 200 OK
// ✅ pending_new_batter = false

// Ball 3.4 - New batsman's first ball
POST /games/{game_id}/deliveries
{ "batsman_id": "player-3", "bowler_id": "bowler-1", "runs_scored": 0 }
// ✅ 200 OK

// Ball 3.5 - Continue normally
POST /games/{game_id}/deliveries
{ "batsman_id": "player-2", "bowler_id": "bowler-1", "runs_scored": 6 }
// ✅ 200 OK

// Ball 3.6 - End of over
POST /games/{game_id}/deliveries
{ "batsman_id": "player-3", "bowler_id": "bowler-1", "runs_scored": 2 }
// ✅ 200 OK
```

---

## Field Reference

### POST /games/{game_id}/deliveries

#### Request Body (ScoreDelivery)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `batsman_id` | string | Yes | UUID of the batsman facing |
| `bowler_id` | string | Yes | UUID of the bowler |
| `runs_scored` | integer | Yes | Total runs scored (including extras) |
| `runs_off_bat` | integer | No | Runs scored off the bat (for extras) |
| `extra_type` | string | No | Type of extra: `"wd"`, `"nb"`, `"b"`, `"lb"` |
| `is_wicket` | boolean | No | Whether this delivery resulted in a wicket |
| `dismissal_type` | string | No* | Type of dismissal (required if `is_wicket: true`) |
| `dismissed_player_id` | string | No | UUID of dismissed player (defaults to striker) |
| `fielder_id` | string | No | UUID of fielder (for caught, run out, etc.) |

*Required when `is_wicket: true`

#### Dismissal Types

Valid values for `dismissal_type`:
- `"bowled"`
- `"caught"`
- `"lbw"`
- `"run_out"`
- `"stumped"`
- `"hit_wicket"`
- `"handled_ball"`
- `"obstructing_field"`
- `"timed_out"`
- `"retired_hurt"` (not counted as wicket)

### POST /games/{game_id}/next-batter

#### Request Body (NextBatterBody)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `batter_id` | string | Yes | UUID of the new batsman |

#### Response

```json
{
  "ok": true,
  "current_striker_id": "player-uuid",
  "message": "No replacement batter required"  // If no wicket pending
}
```

---

## Common Errors

### 409 Conflict: "Select a new batter before scoring the next ball"

**Cause:** Attempted to post a delivery when `pending_new_batter = true`

**Solution:** Call `/next-batter` endpoint first

**Example:**
```javascript
// ❌ This will fail
POST /games/{id}/deliveries { ... }

// ✅ Do this first
POST /games/{id}/next-batter { "batter_id": "new-player-uuid" }

// ✅ Then this will work
POST /games/{id}/deliveries { ... }
```

### 404 Not Found: Endpoint

**Cause:** Using incorrect endpoint URL

**Common mistakes:**
- `/batsman` ❌ (doesn't exist)
- `/batter` ❌ (doesn't exist)
- `/select-batter` ❌ (doesn't exist)

**Correct:** `/next-batter` ✅

### 422 Unprocessable Entity: Missing batter_id

**Cause:** Request body missing required `batter_id` field

**Solution:**
```json
{
  "batter_id": "player-uuid"  // ✅ Required
}
```

---

## State Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Normal Batting State                      │
│                 pending_new_batter = false                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ POST /deliveries
                              │ { is_wicket: true }
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   Wicket Occurred State                      │
│                  pending_new_batter = true                   │
│                                                               │
│  ⚠️  Next delivery will be BLOCKED until new batter selected │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ POST /next-batter
                              │ { batter_id: "..." }
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                New Batsman Selected State                    │
│                 pending_new_batter = false                   │
│                                                               │
│  ✅  New batsman is now current striker                      │
│  ✅  Deliveries can be posted normally                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Notes

### For Test Fixtures

When creating test fixtures with wickets:

1. **Track batting order** - Know which batsmen are available
2. **Maintain state** - Track which batsmen are currently batting
3. **Select sequentially** - Choose next available batsman after each wicket
4. **Handle edge cases** - All out (10 wickets), retired hurt, etc.

### For Match Simulators

```javascript
// Pseudo-code for match simulator
const availableBatsmen = team.players.map(p => p.id)
let nextBatsmanIndex = 2  // First 2 are openers

for (const ball of innings.balls) {
  // If previous ball was a wicket, select new batsman
  if (previousBallWasWicket && nextBatsmanIndex < availableBatsmen.length) {
    await fetch(`/games/${gameId}/next-batter`, {
      method: 'POST',
      body: JSON.stringify({
        batter_id: availableBatsmen[nextBatsmanIndex++]
      })
    })
    previousBallWasWicket = false
  }

  // Post the delivery
  await fetch(`/games/${gameId}/deliveries`, {
    method: 'POST',
    body: JSON.stringify({
      batsman_id: ball.batsman_id,
      bowler_id: ball.bowler_id,
      runs_scored: ball.runs,
      is_wicket: ball.wicket || false,
      dismissal_type: ball.wicket ? ball.wicketType : undefined
    })
  })

  // Mark if this was a wicket
  if (ball.wicket) {
    previousBallWasWicket = true
  }
}
```

### For Frontend Applications

```typescript
// Listen for state updates via WebSocket
socket.on('state:update', (data) => {
  const snapshot = data.snapshot

  // Check if new batsman is required
  if (snapshot.pending_new_batter) {
    // Show batsman selection UI
    showBatsmanSelectionDialog()
  }
})

// When user selects new batsman
async function selectNewBatsman(batterId: string) {
  const response = await fetch(`/games/${gameId}/next-batter`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ batter_id: batterId })
  })

  if (response.ok) {
    // Continue scoring
    hideBatsmanSelectionDialog()
  }
}
```

---

## Best Practices

### ✅ DO

- Always check `pending_new_batter` state before posting deliveries
- Call `/next-batter` immediately after a wicket (before next delivery)
- Track available batsmen in your application state
- Handle the 409 error gracefully with retry logic
- Use WebSocket updates to stay synchronized with server state

### ❌ DON'T

- Don't post deliveries without checking `pending_new_batter` state
- Don't assume wicket deliveries will fail - they succeed but set the flag
- Don't skip `/next-batter` call after wickets
- Don't reuse dismissed batsmen (check `is_out` status)
- Don't forget to handle the "all out" scenario (10 wickets)

---

## Testing Checklist

When testing wicket scenarios:

- [ ] Post delivery with `is_wicket: true` succeeds
- [ ] `pending_new_batter` flag is set after wicket
- [ ] Next delivery without `/next-batter` returns 409
- [ ] `/next-batter` call succeeds and clears flag
- [ ] Next delivery after `/next-batter` succeeds
- [ ] New batsman appears in scorecards
- [ ] Wicket count increments correctly
- [ ] Bowler's wickets tally increases
- [ ] WebSocket emits state update
- [ ] Frontend displays new batsman correctly

---

## Troubleshooting

### Q: I'm getting 409 errors even though I called `/next-batter`

**A:** Check the order of operations:
1. Post wicket delivery ✅
2. Call `/next-batter` ✅
3. Post next delivery ✅

Make sure you're not posting the next delivery before `/next-batter` completes.

### Q: The new batsman isn't showing up in the UI

**A:** Ensure you're:
1. Listening to WebSocket `state:update` events
2. Refreshing the snapshot after `/next-batter`
3. Checking the `current_striker_id` in the response

### Q: Can I select any player as the new batsman?

**A:** Yes, but best practice is to:
1. Only select players from the batting team
2. Don't select players who are already out (`is_out: true`)
3. Don't select players currently batting
4. Follow the batting order in your fixture/application

### Q: What happens if all 10 wickets fall?

**A:** The innings should automatically end. Check:
1. `current_inning` increments to 2
2. `pending_new_batter` is cleared
3. Match status updates appropriately

---

## Related Documentation

- [API Reference](./API_REFERENCE.md)
- [Match Simulation Guide](./MATCH_SIMULATION.md)
- [Testing Guide](../TESTING.md)
- [WebSocket Events](./WEBSOCKET_EVENTS.md)

---

**Last Updated:** October 20, 2025
**Version:** 1.0.0
**Maintainer:** Cricksy Scorer Development Team
