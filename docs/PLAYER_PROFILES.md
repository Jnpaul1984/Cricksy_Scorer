# Player Profiles Feature

## Overview

The Player Profiles feature provides comprehensive player statistics tracking, achievements, badges, and leaderboards for the Cricksy Scorer application. This feature enables personalized player profiles with detailed performance metrics and gamification elements to enhance user engagement.

## Features

### 1. Player Statistics Tracking

#### Batting Statistics
- Total matches and innings
- Total runs scored and balls faced
- Batting average (runs/dismissals)
- Strike rate ((runs/balls) * 100)
- Highest score
- Centuries (100+ runs)
- Half-centuries (50-99 runs)
- Fours and sixes hit

#### Bowling Statistics
- Total innings bowled
- Overs bowled
- Total wickets taken
- Runs conceded
- Bowling average (runs/wickets)
- Economy rate (runs/overs)
- Best bowling figures (e.g., "5/28")
- Five-wicket hauls (5+ wickets in an innings)
- Maiden overs

#### Fielding Statistics
- Catches taken
- Stumpings made
- Run-outs assisted

### 2. Achievement System

The achievement system recognizes player milestones and exceptional performances:

#### Achievement Types
1. **Century** 🏏 - Score 100+ runs in an innings
2. **Half Century** 🏏 - Score 50-99 runs in an innings
3. **Five Wickets** 🎳 - Take 5+ wickets in an innings
4. **Best Scorer** 🌟 - Top scorer of the match
5. **Best Bowler** 🌟 - Best bowler of the match
6. **Hat Trick** 🎩 - Take 3 consecutive wickets
7. **Golden Duck** 🦆 - Out on first ball
8. **Maiden Over** ⚾ - Bowl a maiden over
9. **Six Sixes** 🚀 - Hit 6 sixes in an innings
10. **Perfect Catch** 🧤 - Take 3+ catches in a match

Each achievement includes:
- Title and description
- Badge icon (emoji)
- Earned timestamp
- Metadata (runs, wickets, etc.)
- Optional game association

### 3. Leaderboards

Dynamic leaderboards for various performance metrics:

#### Batting Leaderboards
- **Most Runs**: Total runs scored
- **Best Batting Average**: Runs per dismissal
- **Highest Strike Rate**: Scoring rate
- **Most Centuries**: 100+ scores

#### Bowling Leaderboards
- **Most Wickets**: Total wickets taken
- **Best Bowling Average**: Runs per wicket
- **Best Economy Rate**: Runs per over
- **Most Five-Wicket Hauls**: 5+ wicket performances

Features:
- Top 10 rankings
- Medal badges (🥇🥈🥉) for top 3
- Additional stats for context
- Real-time updates

### 4. User Interface

#### Player Profile Page
- Player header with name and ID
- Statistics cards for batting, bowling, fielding
- Achievements & badges section
- Responsive grid layout
- Visual emphasis on key metrics

#### Leaderboard Page
- Metric selector dropdown
- Sortable table with rankings
- Player links to profiles
- Additional stats column
- Medal badges for top performers

## Technical Implementation

### Backend (Python/FastAPI)

#### Database Models

**PlayerProfile**
```python
- player_id (primary key)
- player_name
- Batting stats (runs, balls, average, strike rate, etc.)
- Bowling stats (wickets, overs, average, economy, etc.)
- Fielding stats (catches, stumpings, run-outs)
- Timestamps (created_at, updated_at)
```

**PlayerAchievement**
```python
- id (primary key)
- player_id (foreign key)
- game_id (foreign key, optional)
- achievement_type (enum)
- title, description, badge_icon
- earned_at
- achievement_metadata (JSON)
```

#### API Endpoints

```
GET  /api/players/{player_id}/profile
     Returns player profile with statistics and achievements

GET  /api/players/{player_id}/achievements
     Returns all achievements for a player

POST /api/players/{player_id}/achievements
     Awards a new achievement to a player
     Body: {
       "achievement_type": "century",
       "title": "Century Master",
       "description": "Scored 150 runs",
       "badge_icon": "💯",
       "game_id": "optional",
       "metadata": { "runs": 150 }
     }

GET  /api/players/leaderboard?metric={metric}&limit={limit}
     Returns leaderboard for specified metric
     Metrics: batting_average, strike_rate, total_runs, centuries,
              bowling_average, economy_rate, total_wickets, five_wickets
```

#### Computed Properties

Statistics are computed on-the-fly using property methods:
- `batting_average`: total_runs / times_out
- `strike_rate`: (total_runs / balls_faced) * 100
- `bowling_average`: runs_conceded / wickets
- `economy_rate`: runs_conceded / overs_bowled

### Frontend (Vue.js/TypeScript)

#### Components

**PlayerProfileView**
- Displays comprehensive player profile
- Three-column grid for statistics
- Achievements section with badges
- Responsive design

**LeaderboardView**
- Dynamic metric selector
- Sortable rankings table
- Medal badges for top 3
- Additional stats display

#### Services

**playerApi.ts**
- `getPlayerProfile(playerId)`: Fetch profile
- `getPlayerAchievements(playerId)`: Fetch achievements
- `awardAchievement(playerId, achievement)`: Award achievement
- `getLeaderboard(metric, limit)`: Fetch leaderboard

#### Types

**player.ts**
- `PlayerProfile`: Complete profile interface
- `PlayerAchievement`: Achievement interface
- `LeaderboardEntry`: Ranking entry interface
- `LeaderboardMetric`: Available metrics enum

### Database Migration

Migration file: `e1a2b3c4d5e6_add_player_profiles_and_achievements.py`

Creates:
- `player_profiles` table with indexes
- `player_achievements` table with indexes
- `achievement_type` enum
- Foreign key relationships

## Testing

### Backend Tests (21 tests)

**Test Coverage:**
- Statistics calculations (batting average, strike rate, bowling average, economy rate)
- Achievement type validation
- Leaderboard ranking logic
- Profile data completeness
- Edge cases (no dismissals, no balls faced, etc.)

Run tests:
```bash
cd backend
python -m pytest tests/test_player_profiles.py -v
```

### Frontend Tests

**Test Coverage:**
- Component rendering
- Loading and error states
- Data display
- Statistics formatting
- Achievement display
- Leaderboard sorting

Run tests:
```bash
cd frontend
npm run test:unit
```

## Usage Examples

### Creating a Player Profile

```python
from backend.sql_app.models import PlayerProfile

profile = PlayerProfile(
    player_id="player-001",
    player_name="Sachin Tendulkar",
    total_matches=50,
    total_runs_scored=2500,
    total_balls_faced=2000,
    times_out=40,
    # ... other stats
)
db.add(profile)
await db.commit()
```

### Awarding an Achievement

```python
from backend.sql_app.models import PlayerAchievement, AchievementType

achievement = PlayerAchievement(
    player_id="player-001",
    achievement_type=AchievementType.century,
    title="Century Master",
    description="Scored 150 runs in match #45",
    badge_icon="💯",
    achievement_metadata={"runs": 150, "balls": 120}
)
db.add(achievement)
await db.commit()
```

### Frontend Integration

```vue
<template>
  <router-link :to="`/players/${playerId}/profile`">
    View Player Profile
  </router-link>
</template>
```

## Demo Script

Run the demo script to create sample data and see the feature in action:

```bash
cd backend
python demo_player_profiles.py
```

This will:
1. Create 3 sample player profiles (Sachin, Warne, Kohli)
2. Add sample achievements
3. Display all profiles with statistics
4. Show leaderboards (runs, wickets, averages)
5. List all achievements

## Future Enhancements

Potential improvements for future iterations:

1. **Auto-Award Achievements**: Automatically award achievements after match completion
2. **Player Comparison**: Side-by-side comparison of two players
3. **Career Graphs**: Visual charts showing performance over time
4. **Social Features**: Share achievements on social media
5. **Player Search**: Search and filter players by name or stats
6. **Team Profiles**: Aggregate statistics for teams
7. **Historical Records**: Track all-time records and milestones
8. **Performance Trends**: Show recent form and trends
9. **Match-by-Match History**: Detailed performance in each match
10. **Custom Achievements**: Allow users to define custom achievements

## API Response Examples

### Player Profile Response
```json
{
  "player_id": "player-001",
  "player_name": "Sachin Tendulkar",
  "total_matches": 50,
  "total_runs_scored": 2500,
  "batting_average": 62.5,
  "strike_rate": 125.0,
  "total_wickets": 15,
  "bowling_average": 32.0,
  "economy_rate": 8.0,
  "achievements": [
    {
      "id": 1,
      "achievement_type": "century",
      "title": "Century Master",
      "description": "Scored 150 runs",
      "badge_icon": "💯",
      "earned_at": "2025-01-10T00:00:00Z"
    }
  ]
}
```

### Leaderboard Response
```json
{
  "metric": "total_runs",
  "entries": [
    {
      "rank": 1,
      "player_id": "player-001",
      "player_name": "Sachin Tendulkar",
      "value": 2500,
      "additional_stats": {
        "batting_average": 62.5,
        "strike_rate": 125.0
      }
    }
  ],
  "updated_at": "2025-01-15T12:00:00Z"
}
```

## Security Considerations

- ✅ No SQL injection vulnerabilities (using SQLAlchemy ORM)
- ✅ Input validation on all API endpoints
- ✅ Foreign key constraints enforce referential integrity
- ✅ No sensitive data exposed in player profiles
- ✅ CodeQL security scan passed with 0 alerts

## Performance Considerations

- Computed properties calculated on-demand (not stored)
- Database indexes on frequently queried fields:
  - player_id
  - total_runs_scored
  - total_wickets
  - batting average composite (runs, times_out)
- Leaderboard queries use SQL ORDER BY for efficiency
- Frontend uses pagination-ready components

## Accessibility

- Semantic HTML structure
- Proper ARIA labels
- Keyboard navigation support
- Responsive design for mobile
- High contrast text
- Screen reader friendly

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- ES6+ JavaScript support required
- CSS Grid and Flexbox support required

## Dependencies

### Backend
- FastAPI
- SQLAlchemy 2.0+
- Pydantic
- asyncpg (PostgreSQL driver)
- Alembic (migrations)

### Frontend
- Vue 3
- TypeScript
- Vue Router
- Pico CSS
- Vitest (testing)

## License

This feature is part of the Cricksy Scorer application, licensed under MIT.
