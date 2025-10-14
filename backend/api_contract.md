# Cricksy Scorer API Contract (MVP)

This file is the single source of truth for request/response shapes. Your tests and backend must match this.

---
## Create a game

### Endpoint
`POST /games`

### Request (flat schema; required for "limited" matches)
```json
{
  "match_type": "limited",
  "overs_limit": 20,
  "team_a_name": "Alpha",
  "team_b_name": "Bravo",
  "players_a": ["A1","A2","A3","A4","A5","A6","A7","A8","A9","A10","A11"],
  "players_b": ["B1","B2","B3","B4","B5","B6","B7","B8","B9","B10","B11"],
  "toss_winner_team": "A",
  "decision": "bat"
}
