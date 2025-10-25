# Backend Error Message Improvements

## Overview

This document proposes improvements to backend error messages to make them more actionable and developer-friendly.

---

## Current Issues

### 1. Generic 409 Error

**Current:**
```json
{
  "detail": "Select a new batter before scoring the next ball."
}
```

**Problems:**
- Doesn't explain WHY a new batter is needed
- Doesn't provide the current state
- Doesn't suggest which endpoint to call
- Doesn't indicate which batsman was dismissed

---

## Proposed Improvements

### 1. Enhanced 409 Error for Batsman Selection

**Improved Response:**
```json
{
  "error": "batsman_selection_required",
  "detail": "A wicket occurred in the previous delivery. Select a new batsman before posting the next delivery.",
  "current_state": {
    "pending_new_batter": true,
    "last_dismissal": {
      "player_id": "uuid-123",
      "player_name": "Player 1",
      "dismissal_type": "bowled",
      "delivery_number": 15
    },
    "current_batsmen": {
      "striker_id": null,
      "non_striker_id": "uuid-456"
    }
  },
  "required_action": {
    "endpoint": "/games/{game_id}/next-batter",
    "method": "POST",
    "body_example": {
      "batter_id": "<uuid-of-new-batsman>"
    }
  },
  "available_batsmen": [
    {
      "id": "uuid-789",
      "name": "Player 3",
      "is_out": false
    },
    {
      "id": "uuid-012",
      "name": "Player 4",
      "is_out": false
    }
  ]
}
```

### 2. Validation Errors with Context

**Current:**
```json
{
  "detail": "Invalid player ID"
}
```

**Improved:**
```json
{
  "error": "invalid_player_id",
  "detail": "The provided player ID does not exist in this game.",
  "provided_value": "uuid-invalid",
  "field": "batsman_id",
  "valid_players": [
    { "id": "uuid-1", "name": "Player 1", "team": "A" },
    { "id": "uuid-2", "name": "Player 2", "team": "A" }
  ]
}
```

### 3. State Conflict Errors

**Current:**
```json
{
  "detail": "Game already completed"
}
```

**Improved:**
```json
{
  "error": "game_already_completed",
  "detail": "Cannot post deliveries to a completed game.",
  "current_state": {
    "status": "COMPLETED",
    "completed_at": "2025-10-20T15:30:00Z",
    "result": "Team Alpha won by 15 runs"
  },
  "suggestion": "Create a new game or use the /games endpoint to view completed games."
}
```

---

## Implementation Example

### Python Code (FastAPI)

```python
from fastapi import HTTPException
from typing import Dict, Any, List, Optional

class DetailedHTTPException(HTTPException):
    """Enhanced HTTP exception with structured error details."""

    def __init__(
        self,
        status_code: int,
        error_code: str,
        detail: str,
        current_state: Optional[Dict[str, Any]] = None,
        required_action: Optional[Dict[str, Any]] = None,
        additional_info: Optional[Dict[str, Any]] = None
    ):
        error_response = {
            "error": error_code,
            "detail": detail
        }

        if current_state:
            error_response["current_state"] = current_state

        if required_action:
            error_response["required_action"] = required_action

        if additional_info:
            error_response.update(additional_info)

        super().__init__(status_code=status_code, detail=error_response)


# Usage in endpoint
@_fastapi.post("/games/{game_id}/deliveries")
async def post_delivery(...):
    if g.pending_new_batter:
        # Get last dismissal info
        last_wicket = _get_last_wicket_delivery(g)
        dismissed_player = _get_player_by_id(g, last_wicket.get("dismissed_player_id"))

        # Get available batsmen
        available = _get_available_batsmen(g)

        raise DetailedHTTPException(
            status_code=409,
            error_code="batsman_selection_required",
            detail="A wicket occurred in the previous delivery. Select a new batsman before posting the next delivery.",
            current_state={
                "pending_new_batter": True,
                "last_dismissal": {
                    "player_id": dismissed_player.get("id"),
                    "player_name": dismissed_player.get("name"),
                    "dismissal_type": last_wicket.get("dismissal_type"),
                    "delivery_number": len(g.deliveries)
                },
                "current_batsmen": {
                    "striker_id": g.current_striker_id,
                    "non_striker_id": g.current_non_striker_id
                }
            },
            required_action={
                "endpoint": f"/games/{game_id}/next-batter",
                "method": "POST",
                "body_example": {
                    "batter_id": "<uuid-of-new-batsman>"
                }
            },
            additional_info={
                "available_batsmen": [
                    {
                        "id": p["id"],
                        "name": p["name"],
                        "is_out": p.get("is_out", False)
                    }
                    for p in available
                ]
            }
        )
```

---

## Error Code Standards

### Format

`<category>_<specific_error>`

### Categories

- `validation_` - Input validation errors
- `state_` - Game state conflicts
- `auth_` - Authentication/authorization errors
- `resource_` - Resource not found or unavailable
- `workflow_` - Workflow requirement errors

### Examples

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `batsman_selection_required` | 409 | New batsman must be selected after wicket |
| `validation_invalid_player_id` | 422 | Player ID doesn't exist |
| `state_game_not_started` | 409 | Game hasn't started yet |
| `state_game_completed` | 409 | Game is already completed |
| `resource_game_not_found` | 404 | Game ID doesn't exist |
| `workflow_openers_not_set` | 409 | Openers must be set before deliveries |
| `validation_invalid_dismissal_type` | 422 | Invalid dismissal type provided |

---

## Benefits

### For Developers

1. **Self-documenting** - Error messages explain what went wrong and how to fix it
2. **Faster debugging** - Current state included in error response
3. **Better testing** - Can verify specific error codes
4. **Reduced support** - Fewer questions about error meanings

### For Applications

1. **Better UX** - Can show specific, helpful error messages to users
2. **Automated recovery** - Can programmatically handle errors
3. **State synchronization** - Error response includes current state
4. **Guided workflows** - Suggested actions help guide users

---

## Migration Strategy

### Phase 1: Add New Error Format (Non-Breaking)

Keep existing errors but add enhanced format for new errors:

```python
# Old format (keep for backward compatibility)
raise HTTPException(status_code=409, detail="Select a new batter...")

# New format (add for new errors)
raise DetailedHTTPException(...)
```

### Phase 2: Enhance Critical Errors

Update high-impact errors first:
1. Batsman selection (409)
2. Game state conflicts (409)
3. Validation errors (422)
4. Not found errors (404)

### Phase 3: Comprehensive Update

Update all remaining errors to use new format.

### Phase 4: Deprecate Old Format

After sufficient adoption, deprecate simple error format.

---

## Testing

### Unit Tests

```python
def test_batsman_selection_error_format():
    """Test that batsman selection error has correct format."""
    # Setup: create game and post wicket
    ...

    # Attempt to post next delivery without selecting batsman
    response = client.post(f"/games/{game_id}/deliveries", json={...})

    assert response.status_code == 409
    error = response.json()

    # Verify error structure
    assert "error" in error
    assert error["error"] == "batsman_selection_required"
    assert "detail" in error
    assert "current_state" in error
    assert "required_action" in error
    assert "available_batsmen" in error

    # Verify current state
    assert error["current_state"]["pending_new_batter"] is True
    assert "last_dismissal" in error["current_state"]

    # Verify required action
    assert error["required_action"]["endpoint"] == f"/games/{game_id}/next-batter"
    assert error["required_action"]["method"] == "POST"
```

---

## Documentation

### API Documentation Update

Add error response schemas to OpenAPI spec:

```yaml
paths:
  /games/{game_id}/deliveries:
    post:
      responses:
        '409':
          description: Conflict - batsman selection required
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/BatsmanSelectionRequiredError'

components:
  schemas:
    BatsmanSelectionRequiredError:
      type: object
      properties:
        error:
          type: string
          example: "batsman_selection_required"
        detail:
          type: string
        current_state:
          type: object
        required_action:
          type: object
        available_batsmen:
          type: array
```

---

## Examples for Common Scenarios

### Scenario 1: Wicket Without Batsman Selection

**Request:**
```http
POST /games/abc-123/deliveries
{
  "batsman_id": "player-1",
  "bowler_id": "player-2",
  "runs_scored": 0
}
```

**Response: 409 Conflict**
```json
{
  "error": "batsman_selection_required",
  "detail": "A wicket occurred in the previous delivery. Select a new batsman before posting the next delivery.",
  "current_state": {
    "pending_new_batter": true,
    "last_dismissal": {
      "player_id": "player-1",
      "player_name": "John Doe",
      "dismissal_type": "bowled"
    }
  },
  "required_action": {
    "endpoint": "/games/abc-123/next-batter",
    "method": "POST",
    "body_example": {
      "batter_id": "<uuid>"
    }
  }
}
```

### Scenario 2: Invalid Player ID

**Request:**
```http
POST /games/abc-123/deliveries
{
  "batsman_id": "invalid-id",
  "bowler_id": "player-2",
  "runs_scored": 1
}
```

**Response: 422 Unprocessable Entity**
```json
{
  "error": "validation_invalid_player_id",
  "detail": "The provided batsman_id does not exist in this game.",
  "provided_value": "invalid-id",
  "field": "batsman_id",
  "valid_players": [
    { "id": "player-1", "name": "John Doe", "team": "A" },
    { "id": "player-2", "name": "Jane Smith", "team": "A" }
  ]
}
```

### Scenario 3: Game Already Completed

**Request:**
```http
POST /games/abc-123/deliveries
{
  "batsman_id": "player-1",
  "bowler_id": "player-2",
  "runs_scored": 1
}
```

**Response: 409 Conflict**
```json
{
  "error": "state_game_completed",
  "detail": "Cannot post deliveries to a completed game.",
  "current_state": {
    "status": "COMPLETED",
    "completed_at": "2025-10-20T15:30:00Z",
    "result": "Team Alpha won by 15 runs"
  },
  "suggestion": "Create a new game or use GET /games to view completed games."
}
```

---

## Client-Side Handling

### JavaScript/TypeScript Example

```typescript
async function postDelivery(gameId: string, delivery: Delivery) {
  try {
    const response = await fetch(`/games/${gameId}/deliveries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(delivery)
    })

    if (!response.ok) {
      const error = await response.json()

      // Handle specific error codes
      switch (error.error) {
        case 'batsman_selection_required':
          // Show batsman selection dialog
          const availableBatsmen = error.available_batsmen
          const selectedBatsman = await showBatsmanSelectionDialog(availableBatsmen)

          // Call the suggested endpoint
          await fetch(error.required_action.endpoint, {
            method: error.required_action.method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ batter_id: selectedBatsman.id })
          })

          // Retry original request
          return postDelivery(gameId, delivery)

        case 'state_game_completed':
          showError('Game is already completed', error.current_state.result)
          break

        case 'validation_invalid_player_id':
          showError(`Invalid player: ${error.provided_value}`,
                   `Valid players: ${error.valid_players.map(p => p.name).join(', ')}`)
          break

        default:
          showError('An error occurred', error.detail)
      }

      throw new Error(error.detail)
    }

    return await response.json()
  } catch (err) {
    console.error('Failed to post delivery:', err)
    throw err
  }
}
```

---

## Monitoring and Analytics

### Error Tracking

With structured error codes, you can:

1. **Track error frequency** by error code
2. **Identify problematic workflows** (high 409 rates)
3. **Measure API usability** (validation error rates)
4. **Detect integration issues** (client error patterns)

### Example Metrics

```
error_rate{code="batsman_selection_required"} 0.15
error_rate{code="validation_invalid_player_id"} 0.05
error_rate{code="state_game_completed"} 0.02
```

---

## Future Enhancements

1. **Localization** - Translate error messages
2. **Error recovery suggestions** - Automated fix recommendations
3. **Error documentation links** - Link to docs for each error
4. **Error history** - Track error patterns per game
5. **Client SDKs** - Auto-generated error handling code

---

**Last Updated:** October 20, 2025
**Status:** Proposed
**Priority:** Medium
