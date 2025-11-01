# AI Highlights API Documentation

## Overview

The AI Highlights feature automatically detects and generates highlight clips from cricket matches. It identifies key moments such as boundaries, wickets, milestones, and other exciting events during the game.

## Features

### Event Detection

The system automatically detects the following event types:

- **Boundaries (4s)**: Four runs scored off the bat
- **Sixes**: Maximum hits (6 runs)
- **Wickets**: All dismissal types (bowled, caught, lbw, run out, etc.)
- **Hat-tricks**: Three consecutive wickets by the same bowler
- **Milestones**: Batting milestones (50, 100, 150, 200+ runs)
- **Maiden Overs**: Complete overs with no runs conceded
- **Partnerships**: High-value partnerships between batters (coming soon)

### Video Generation

Each highlight event can be associated with a video clip (currently a placeholder URL that would integrate with a video generation service in production).

### Social Media Sharing

Built-in support for sharing highlights on:
- Twitter/X
- Facebook
- Instagram
- WhatsApp

## API Endpoints

### 1. Generate Highlights

Generate highlights for a completed or ongoing match.

**Endpoint:** `POST /highlights/games/{game_id}/generate`

**Parameters:**
- `game_id` (path): The unique identifier of the game

**Response:**
```json
{
  "highlights": [
    {
      "id": "highlight-uuid",
      "game_id": "game-uuid",
      "event_type": "six",
      "over_number": 5,
      "ball_number": 3,
      "inning": 1,
      "title": "SIX!",
      "description": "Maximum! Six runs",
      "player_id": "player-uuid",
      "player_name": "Player Name",
      "event_metadata": {
        "runs": 6,
        "bowler_id": "bowler-uuid",
        "shot_type": "pull"
      },
      "video_url": "/api/highlights/game-uuid/videos/highlight-uuid/six.mp4",
      "video_generated": false,
      "created_at": "2025-11-01T23:45:00Z"
    }
  ],
  "total": 1
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/highlights/games/abc123/generate"
```

### 2. Get Game Highlights

Retrieve all highlights for a specific game.

**Endpoint:** `GET /highlights/games/{game_id}`

**Parameters:**
- `game_id` (path): The unique identifier of the game

**Response:** Same structure as Generate Highlights

**Example:**
```bash
curl "http://localhost:8000/highlights/games/abc123"
```

### 3. Get Single Highlight

Retrieve a specific highlight by ID.

**Endpoint:** `GET /highlights/{highlight_id}`

**Parameters:**
- `highlight_id` (path): The unique identifier of the highlight

**Response:**
```json
{
  "id": "highlight-uuid",
  "game_id": "game-uuid",
  "event_type": "wicket",
  "over_number": 10,
  "ball_number": 4,
  "inning": 1,
  "title": "Wicket!",
  "description": "bowled",
  "player_id": "player-uuid",
  "player_name": "Batsman Name",
  "event_metadata": {
    "dismissal_type": "bowled",
    "bowler_id": "bowler-uuid",
    "fielder_id": null
  },
  "video_url": "/api/highlights/game-uuid/videos/highlight-uuid/wicket.mp4",
  "video_generated": false,
  "created_at": "2025-11-01T23:45:00Z"
}
```

**Example:**
```bash
curl "http://localhost:8000/highlights/xyz789"
```

### 4. Share Highlight

Generate a share URL for a highlight on social media.

**Endpoint:** `POST /highlights/share`

**Request Body:**
```json
{
  "highlight_id": "highlight-uuid",
  "platform": "twitter"
}
```

**Supported Platforms:**
- `twitter` - Twitter/X
- `facebook` - Facebook
- `instagram` - Instagram (app deep link)
- `whatsapp` - WhatsApp

**Response:**
```json
{
  "success": true,
  "share_url": "https://twitter.com/intent/tweet?url=https://cricksy-scorer.com/highlights/xyz789&text=Check%20out%20this%20cricket%20highlight!",
  "message": "Share URL generated for twitter"
}
```

**Example:**
```bash
curl -X POST "http://localhost:8000/highlights/share" \
  -H "Content-Type: application/json" \
  -d '{"highlight_id": "xyz789", "platform": "twitter"}'
```

### 5. Delete Highlight

Delete a specific highlight.

**Endpoint:** `DELETE /highlights/{highlight_id}`

**Parameters:**
- `highlight_id` (path): The unique identifier of the highlight

**Response:**
```json
{
  "message": "Highlight deleted successfully"
}
```

**Example:**
```bash
curl -X DELETE "http://localhost:8000/highlights/xyz789"
```

## Automatic Highlight Generation

Highlights are automatically generated when:

1. **Match Finalization**: When the `/gameplay/{game_id}/finalize` endpoint is called
2. **Manual Trigger**: By calling the `/highlights/games/{game_id}/generate` endpoint

## Event Metadata Structure

Each highlight event includes metadata specific to the event type:

### Boundary / Six
```json
{
  "runs": 4,
  "bowler_id": "bowler-uuid",
  "shot_type": "drive"
}
```

### Wicket
```json
{
  "dismissal_type": "caught",
  "bowler_id": "bowler-uuid",
  "fielder_id": "fielder-uuid"
}
```

### Hat-trick
```json
{
  "bowler_id": "bowler-uuid"
}
```

### Milestone
```json
{
  "milestone": 50,
  "total_runs": 52
}
```

### Maiden Over
```json
{
  "bowler_id": "bowler-uuid"
}
```

## Integration Guide

### Frontend Integration

To integrate highlights into your frontend application:

1. **Fetch highlights after match completion:**
```javascript
async function getMatchHighlights(gameId) {
  const response = await fetch(`/highlights/games/${gameId}`);
  const data = await response.json();
  return data.highlights;
}
```

2. **Display highlights in a carousel or list:**
```javascript
function displayHighlights(highlights) {
  highlights.forEach(highlight => {
    console.log(`${highlight.title}: ${highlight.description}`);
    // Render highlight card/video player
  });
}
```

3. **Share a highlight:**
```javascript
async function shareHighlight(highlightId, platform) {
  const response = await fetch('/highlights/share', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ highlight_id: highlightId, platform })
  });
  const data = await response.json();
  window.open(data.share_url, '_blank');
}
```

### Mobile Integration

For mobile apps, use deep links for social sharing:

```kotlin
// Android example
fun shareHighlight(highlightId: String, platform: String) {
    val intent = Intent(Intent.ACTION_VIEW).apply {
        data = Uri.parse("https://cricksy-scorer.com/highlights/$highlightId")
    }
    
    when(platform) {
        "twitter" -> intent.setPackage("com.twitter.android")
        "facebook" -> intent.setPackage("com.facebook.katana")
        "instagram" -> intent.setPackage("com.instagram.android")
        "whatsapp" -> intent.setPackage("com.whatsapp")
    }
    
    startActivity(intent)
}
```

## Video Generation (Future Enhancement)

The current implementation includes placeholder video URLs. To integrate with a video generation service:

1. Implement the video generation service integration in `highlights_service.py`
2. Update the `generate_video_url` method to call your video service
3. Set `video_generated` to `True` once the video is ready
4. Store the actual video URL in the `video_url` field

Example integration with a hypothetical video service:

```python
@staticmethod
async def generate_video_url(highlight: dict[str, Any], db: Any) -> str:
    # Call video generation service
    video_service = VideoGenerationService()
    
    video_id = await video_service.create_highlight_video(
        game_id=highlight['game_id'],
        start_time=highlight['timestamp'],
        duration=15  # 15 second clip
    )
    
    # Update highlight with video URL
    video_url = f"https://videos.cricksy.com/{video_id}.mp4"
    
    # Update database
    await db.execute(
        update(Highlight)
        .where(Highlight.id == highlight['id'])
        .values(video_url=video_url, video_generated=True)
    )
    await db.commit()
    
    return video_url
```

## Testing

The highlights feature includes comprehensive tests in `backend/tests/test_highlights.py`:

```bash
# Run all highlights tests
pytest tests/test_highlights.py -v

# Run specific test
pytest tests/test_highlights.py::TestHighlightsService::test_detect_boundary -v
```

## Database Schema

The highlights are stored in the `highlights` table:

```sql
CREATE TABLE highlights (
    id VARCHAR PRIMARY KEY,
    game_id VARCHAR REFERENCES games(id) ON DELETE CASCADE,
    event_type highlight_event_type NOT NULL,
    over_number INTEGER NOT NULL,
    ball_number INTEGER NOT NULL,
    inning INTEGER NOT NULL,
    title VARCHAR NOT NULL,
    description TEXT,
    player_id VARCHAR,
    player_name VARCHAR,
    event_metadata JSON NOT NULL,
    video_url TEXT,
    video_generated BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE INDEX ix_highlights_game_id ON highlights(game_id);
CREATE INDEX ix_highlights_event_type ON highlights(event_type);
CREATE INDEX ix_highlights_created_at ON highlights(created_at);
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- `200 OK` - Success
- `404 Not Found` - Game or highlight not found
- `500 Internal Server Error` - Server error

Errors are returned in JSON format:
```json
{
  "detail": "Game not found"
}
```

## Rate Limiting (Recommended)

For production deployment, consider implementing rate limiting on the highlights endpoints to prevent abuse:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/games/{game_id}/generate")
@limiter.limit("10/minute")
async def generate_highlights(game_id: str, db: AsyncSession):
    # ... implementation
```

## Performance Considerations

- Highlight generation is optimized to process deliveries in a single pass
- Database queries use indexes on `game_id`, `event_type`, and `created_at`
- Consider caching highlights for frequently accessed games
- Video generation (when implemented) should be done asynchronously

## Future Enhancements

- [ ] Real video generation integration
- [ ] Partnership detection
- [ ] Super over highlights
- [ ] Custom highlight filters (e.g., player-specific highlights)
- [ ] Highlight compilation for entire tournament
- [ ] AI-powered commentary generation
- [ ] Thumbnail generation for video clips
- [ ] Analytics on most popular highlights

## Support

For issues or questions about the highlights API, please contact the development team or open an issue on GitHub.
