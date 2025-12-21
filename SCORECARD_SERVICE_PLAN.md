# Complete Service Layer Implementation Plan

## Overview
We have 9 scorecard routes that need service layer logic. The good news: **`scoring_service.score_one()` already exists** and handles most of the complex cricket logic! We need to wire it into the new models and routes.

---

## Phase 1: Understand Current State

### ✅ What Already Exists
- **`scoring_service.score_one()`** - Handles:
  - Strike rotation
  - Wicket logic
  - Extra runs (wides, no-balls, byes, leg-byes)
  - Batting/bowling scorecard updates
  - Over completion detection
  - Dismissal type validation
  
- **Game State Updates** - Already updates `total_runs`, `overs_completed`, etc.

- **Live Bus** - `live_bus.emit_state_update()` broadcasts to all clients

### ❌ What Needs to Be Built
- **Delivery Model Persistence** - Store each ball in database (currently only in Game.deliveries JSON)
- **Player/Scorecard Models** - New normalized tables
- **Route Service Functions** - Wrapper functions that integrate `score_one()` with database operations

---

## Phase 2: Implementation Breakdown

### **Group 1: Player Management** (Foundation)
Routes:
- `POST /players` - Create player
- `GET /players/{id}` - Get player
- `GET /players` - List players

**Service Logic Needed:**
```python
class PlayerService:
    async def create_player(db, name: str, jersey_number: int, role: str) -> Player
    async def get_player(db, player_id: int) -> Player
    async def list_players(db, skip: int, limit: int) -> List[Player]
    async def get_or_create_player(db, name: str) -> Player  # Helper
```

**Complexity:** Low - Just CRUD operations
**Dependencies:** None

---

### **Group 2: Recording Delivery** (Core - Most Complex)
Route:
- `POST /games/{game_id}/deliveries` - Record one ball

**Service Logic Needed:**
```python
class DeliveryService:
    async def record_delivery(
        db: AsyncSession,
        game_id: int,
        batter_id: int,
        bowler_id: int,
        non_striker_id: int,
        runs: int,
        extra_type: str | None,
        is_wicket: bool,
        dismissal_type: str | None,
        fielder_id: int | None,
        dismissed_player_id: int | None,
    ) -> Delivery:
        """
        1. Load the Game from database
        2. Call scoring_service.score_one() to get new state
        3. Create Delivery record in database
        4. Update BattingScorecard and BowlingScorecard
        5. Update Game object
        6. Emit Socket.IO event
        7. Return Delivery object
        """
```

**Complexity:** **VERY HIGH**
- Needs to atomically update multiple records
- Must handle complex dismissal logic
- Must update Game state AND scorecard tables
- Must emit real-time events

**Dependencies:** Player records must exist first

---

### **Group 3: Querying Scorecards** (Simple - Read-Only)
Routes:
- `GET /games/{game_id}/batting-scorecards` - Get all batters' stats
- `GET /games/{game_id}/bowling-scorecards` - Get all bowlers' stats
- `GET /games/{game_id}/deliveries` - Get all balls

**Service Logic Needed:**
```python
class ScorecardService:
    async def get_batting_scorecards(db, game_id: int) -> List[BattingScorecard]
    async def get_bowling_scorecards(db, game_id: int) -> List[BowlingScorecard]
    async def get_deliveries(db, game_id: int, inning: int = None) -> List[Delivery]
    
    # Optional: Calculated fields
    async def get_batting_summary(db, game_id: int) -> dict  # Strike rate, avg, etc.
    async def get_bowling_summary(db, game_id: int) -> dict  # Economy, avg wickets, etc.
```

**Complexity:** Low - Just queries
**Dependencies:** Deliveries must be recorded first

---

### **Group 4: Updating Scorecards** (Medium - Complex Logic)
Routes:
- `POST /games/{game_id}/batting-scorecards` - Manual record
- `POST /games/{game_id}/bowling-scorecards` - Manual record

**Service Logic Needed:**
```python
class ScorecardService:
    async def create_batting_scorecard(
        db, game_id, player_id, runs, balls_faced, fours, sixes, dismissal_type
    ) -> BattingScorecard
    
    async def create_bowling_scorecard(
        db, game_id, player_id, overs, runs_conceded, wickets
    ) -> BowlingScorecard
```

**Complexity:** Medium
- Need to validate cricket stats (e.g., fours ≤ runs)
- Need to handle dismissal types (LBW, caught, etc.)
- Optional: Calculate derived fields (economy rate, strike rate)

**Dependencies:** Players must exist

---

## Phase 3: Implementation Order

### **Step 1: Create Service Layer File**
File: `backend/services/scorecard_service.py`

```python
from sqlalchemy.ext.asyncio import AsyncSession
from backend.sql_app.models import Player, BattingScorecard, BowlingScorecard, Delivery, Game
from backend.services import scoring_service
from backend.services.live_bus import emit_state_update

class PlayerService:
    @staticmethod
    async def create_player(db: AsyncSession, name: str, jersey_number: int, role: str) -> Player:
        player = Player(name=name, jersey_number=jersey_number, role=role)
        db.add(player)
        await db.commit()
        await db.refresh(player)
        return player
    
    # ... more methods

class DeliveryService:
    @staticmethod
    async def record_delivery(db: AsyncSession, game_id: int, delivery_data: dict):
        # This is the complex one - explained below
        ...

class ScorecardService:
    @staticmethod
    async def get_batting_scorecards(db: AsyncSession, game_id: int):
        # Simple query
        ...
```

### **Step 2: Update Routes to Use Services**
File: `backend/routes/scorecards.py`

```python
from backend.services.scorecard_service import PlayerService, DeliveryService

@router.post("/players")
async def create_player(player_data: PlayerCreate, db: AsyncSession):
    return await PlayerService.create_player(
        db=db,
        name=player_data.name,
        jersey_number=player_data.jersey_number,
        role=player_data.role
    )

@router.post("/games/{game_id}/deliveries")
async def record_delivery(game_id: int, delivery: DeliveryCreate, db: AsyncSession):
    return await DeliveryService.record_delivery(
        db=db,
        game_id=game_id,
        delivery_data=delivery.dict()
    )
```

### **Step 3: Create Tests**
File: `backend/tests/test_scorecard_service.py`

Test each service function independently:
- Create player
- Record delivery
- Query scorecards
- Validate cricket logic (e.g., wickets increment correctly)

---

## Phase 4: Deep Dive - Record Delivery Logic

This is the most complex. Here's pseudo-code for `DeliveryService.record_delivery()`:

```python
async def record_delivery(db: AsyncSession, game_id: int, delivery_data: dict):
    # 1. Load game and validate
    game = await db.get(Game, game_id)
    assert game, "Game not found"
    
    # 2. Get player objects
    batter = await db.get(Player, delivery_data["batter_id"])
    bowler = await db.get(Player, delivery_data["bowler_id"])
    non_striker = await db.get(Player, delivery_data["non_striker_id"])
    assert all([batter, bowler, non_striker]), "Player not found"
    
    # 3. Call scoring_service.score_one() to mutate game state
    score_result = scoring_service.score_one(
        g=game,  # This mutates the game object!
        striker_id=batter.id,
        non_striker_id=non_striker.id,
        bowler_id=bowler.id,
        runs_scored=delivery_data["runs"],
        extra=delivery_data.get("extra_type"),
        is_wicket=delivery_data.get("is_wicket", False),
        dismissal_type=delivery_data.get("dismissal_type"),
        dismissed_player_id=delivery_data.get("dismissed_player_id"),
    )
    
    # 4. Create Delivery record
    delivery = Delivery(
        game_id=game_id,
        inning_number=game.current_inning,
        over_number=score_result["over_number"],
        ball_number=score_result["ball_number"],
        bowler_id=bowler.id,
        batter_id=batter.id,
        non_striker_id=non_striker.id,
        runs=score_result["runs_scored"],
        runs_off_bat=score_result["runs_off_bat"],
        extra_type=score_result["extra_type"],
        extra_runs=score_result["extra_runs"],
        is_wicket=score_result["is_wicket"],
        wicket_type=score_result["dismissal_type"],
        is_legal=not score_result["is_extra"],
    )
    db.add(delivery)
    
    # 5. Update or create BattingScorecard
    batting_card = await db.query(BattingScorecard).filter_by(
        game_id=game_id,
        player_id=batter.id
    ).first()
    if batting_card:
        # Update existing
        batting_card.runs += score_result["runs_scored"]
        batting_card.balls_faced += (0 if score_result["is_extra"] else 1)
        if score_result["runs_off_bat"] >= 4:
            if score_result["runs_off_bat"] == 4:
                batting_card.fours += 1
            elif score_result["runs_off_bat"] == 6:
                batting_card.sixes += 1
        if score_result["is_wicket"]:
            batting_card.is_out = True
            batting_card.dismissal_type = score_result["dismissal_type"]
    else:
        # Create new
        batting_card = BattingScorecard(
            game_id=game_id,
            player_id=batter.id,
            runs=score_result["runs_scored"],
            balls_faced=0 if score_result["is_extra"] else 1,
            # ... etc
        )
        db.add(batting_card)
    
    # 6. Update or create BowlingScorecard
    bowling_card = await db.query(BowlingScorecard).filter_by(
        game_id=game_id,
        player_id=bowler.id
    ).first()
    if bowling_card:
        bowling_card.runs_conceded += score_result["extra_runs"]
        if score_result["is_wicket"] and score_result["dismissal_type"] in CREDIT_BOWLER:
            bowling_card.wickets_taken += 1
    else:
        bowling_card = BowlingScorecard(
            game_id=game_id,
            player_id=bowler.id,
            runs_conceded=score_result["extra_runs"],
            wickets_taken=1 if score_result["is_wicket"] else 0,
        )
        db.add(bowling_card)
    
    # 7. Update game object
    game.total_runs = getattr(game, "total_runs", 0) + score_result["runs_scored"]
    
    # 8. Commit all changes atomically
    await db.commit()
    
    # 9. Emit real-time update
    await emit_state_update(game_id, game)
    
    return delivery
```

---

## Phase 5: Implementation Checklist

### Week 1: Foundation
- [ ] Create `scorecard_service.py` with Player service
- [ ] Update `/players` routes
- [ ] Write tests for Player CRUD

### Week 2: Delivery Recording
- [ ] Create `DeliveryService.record_delivery()` (the big one)
- [ ] Update `POST /games/{id}/deliveries` route
- [ ] Test delivery recording with various wicket types
- [ ] Integrate with Socket.IO `state:update` event

### Week 3: Scorecard Queries
- [ ] Create scorecard query methods
- [ ] Update GET routes
- [ ] Add pagination/filtering (over ranges, specific players)

### Week 4: Manual Scorecard Creation
- [ ] Create methods for manual entry
- [ ] Add validation
- [ ] Update PUT/POST routes for scorecards

### Week 5: Testing & Documentation
- [ ] E2E tests for full delivery workflow
- [ ] API documentation
- [ ] Edge case tests (no-balls, wides, all dismissal types)

---

## Key Files to Touch

1. **New:** `backend/services/scorecard_service.py` - Main service logic
2. **Update:** `backend/routes/scorecards.py` - Use new services
3. **Update:** `backend/app.py` - Already includes scorecards router
4. **New:** `backend/tests/test_scorecard_service.py` - Unit tests
5. **Update:** `backend/services/scoring_service.py` - May need minor tweaks
6. **Update:** `backend/sql_app/models.py` - Already updated

---

## Critical Dependencies & Gotchas

### ✅ Models Ready
- Player, BattingScorecard, BowlingScorecard, Delivery are all in models.py

### ⚠️ Need to Handle
1. **Dismissal Types** - Must match cricket rules (LBW, caught, etc.)
   - Reference: `backend/domain/constants.py`
   
2. **Strike Rotation** - `score_one()` handles this, but we need to persist `current_striker_id`, `current_non_striker_id`
   
3. **Over Completion** - When 6 legal balls complete, swap ends
   
4. **Inning Transitions** - When all-out (10 wickets), switch innings
   
5. **Atomic Updates** - All scorecard updates must happen together (use transaction)

---

## Ready to Start?

Which phase would you like to tackle first?

1. **Player Service** (simple, foundation)
2. **Delivery Recording Service** (complex, core)
3. **Query Service** (simple, read-only)
4. **Full Implementation** (all at once)
