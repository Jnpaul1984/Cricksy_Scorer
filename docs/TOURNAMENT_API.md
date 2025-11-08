# Tournament Management API

This document describes the tournament management API endpoints added to Cricksy Scorer.

## Overview

The tournament management system allows you to:
- Create and manage tournaments
- Add teams to tournaments
- Schedule fixtures (matches)
- Track points tables with automatic calculations
- View tournament standings with net run rate

## API Endpoints

### Tournaments

#### Create Tournament
```
POST /tournaments/
```

**Request Body:**
```json
{
  "name": "Premier League 2024",
  "description": "Annual cricket tournament",
  "tournament_type": "league",
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-03-31T00:00:00Z"
}
```

**Response:** Tournament object with ID

#### List Tournaments
```
GET /tournaments/?skip=0&limit=100
```

**Response:** Array of tournament objects

#### Get Tournament
```
GET /tournaments/{tournament_id}
```

**Response:** Tournament object with teams

#### Update Tournament
```
PATCH /tournaments/{tournament_id}
```

**Request Body:**
```json
{
  "name": "Updated Tournament Name",
  "status": "ongoing"
}
```

**Response:** Updated tournament object

#### Delete Tournament
```
DELETE /tournaments/{tournament_id}
```

**Response:** `{"status": "deleted"}`

### Teams

#### Add Team to Tournament
```
POST /tournaments/{tournament_id}/teams
```

**Request Body:**
```json
{
  "team_name": "Mumbai Indians",
  "team_data": {
    "players": [
      {"id": "1", "name": "Player 1"},
      {"id": "2", "name": "Player 2"}
    ]
  }
}
```

**Response:** Team object with stats

#### Get Tournament Teams
```
GET /tournaments/{tournament_id}/teams
```

**Response:** Array of team objects with stats

#### Get Points Table
```
GET /tournaments/{tournament_id}/points-table
```

**Response:**
```json
[
  {
    "team_name": "Mumbai Indians",
    "matches_played": 5,
    "matches_won": 4,
    "matches_lost": 1,
    "matches_drawn": 0,
    "points": 8,
    "net_run_rate": 1.234
  }
]
```

### Fixtures

#### Create Fixture
```
POST /tournaments/fixtures
```

**Request Body:**
```json
{
  "tournament_id": "abc123",
  "match_number": 1,
  "team_a_name": "Mumbai Indians",
  "team_b_name": "Chennai Super Kings",
  "venue": "Wankhede Stadium",
  "scheduled_date": "2024-01-15T19:00:00Z"
}
```

**Response:** Fixture object

#### Get Fixture
```
GET /tournaments/fixtures/{fixture_id}
```

**Response:** Fixture object

#### Get Tournament Fixtures
```
GET /tournaments/{tournament_id}/fixtures
```

**Response:** Array of fixture objects sorted by date

#### Update Fixture
```
PATCH /tournaments/fixtures/{fixture_id}
```

**Request Body:**
```json
{
  "status": "completed",
  "result": "Mumbai Indians won by 5 wickets",
  "game_id": "game123"
}
```

**Response:** Updated fixture object

#### Delete Fixture
```
DELETE /tournaments/fixtures/{fixture_id}
```

**Response:** `{"status": "deleted"}`

## Data Models

### Tournament
- `id`: UUID (generated)
- `name`: string (required)
- `description`: string (optional)
- `tournament_type`: "league" | "knockout" | "round-robin"
- `start_date`: datetime (optional)
- `end_date`: datetime (optional)
- `status`: "upcoming" | "ongoing" | "completed"
- `created_at`: datetime
- `updated_at`: datetime
- `teams`: array of team objects

### Tournament Team
- `id`: integer
- `tournament_id`: UUID
- `team_name`: string
- `team_data`: object (player info, etc.)
- `matches_played`: integer
- `matches_won`: integer
- `matches_lost`: integer
- `matches_drawn`: integer
- `points`: integer (2 per win, 1 per draw)
- `net_run_rate`: float

### Fixture
- `id`: UUID (generated)
- `tournament_id`: UUID
- `match_number`: integer (optional)
- `team_a_name`: string
- `team_b_name`: string
- `venue`: string (optional)
- `scheduled_date`: datetime (optional)
- `game_id`: UUID (links to actual game)
- `status`: "scheduled" | "in_progress" | "completed" | "cancelled"
- `result`: string (optional)
- `created_at`: datetime
- `updated_at`: datetime

## Frontend Routes

- `/tournaments` - Tournament dashboard (list all tournaments)
- `/tournaments/{id}` - Tournament detail page with tabs:
  - Overview
  - Teams
  - Points Table
  - Fixtures

## Points Calculation

Points are calculated automatically based on match results:
- **Win**: 2 points
- **Draw**: 1 point
- **Loss**: 0 points

### Net Run Rate (NRR)
NRR is calculated as:
```
NRR = (Runs Scored / Overs Faced) - (Runs Conceded / Overs Bowled)
```

The points table is sorted by:
1. Points (descending)
2. Net Run Rate (descending)

## Database Migration

To apply the tournament tables:
```bash
cd backend
alembic upgrade head
```

The migration `e1f7a8b2c9d3_add_tournament_tables.py` creates:
- `tournaments` table
- `tournament_teams` table
- `fixtures` table

## Usage Example

```python
import httpx

# Create a tournament
tournament = await httpx.post("http://localhost:8000/tournaments/", json={
    "name": "Summer League 2024",
    "tournament_type": "league"
})

tournament_id = tournament.json()["id"]

# Add teams
await httpx.post(f"http://localhost:8000/tournaments/{tournament_id}/teams", json={
    "team_name": "Mumbai Indians"
})

await httpx.post(f"http://localhost:8000/tournaments/{tournament_id}/teams", json={
    "team_name": "Chennai Super Kings"
})

# Create fixture
await httpx.post("http://localhost:8000/tournaments/fixtures", json={
    "tournament_id": tournament_id,
    "match_number": 1,
    "team_a_name": "Mumbai Indians",
    "team_b_name": "Chennai Super Kings",
    "venue": "Wankhede Stadium"
})

# Get points table
points = await httpx.get(f"http://localhost:8000/tournaments/{tournament_id}/points-table")
print(points.json())
```
