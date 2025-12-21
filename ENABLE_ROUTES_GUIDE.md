# How to Re-Enable Disabled Routes

## Overview
9 route modules were disabled due to undefined model dependencies. This guide explains what needs to be done to re-enable them.

---

## Disabled Routes & Required Models

| Route File | Required Models | Service File |
|---|---|---|
| `pitch_heatmaps.py` | `Player`, `BattingScorecard` | `pitch_heatmap_generator.py` |
| `ball_clustering.py` | `Player`, `BowlingScorecard`, `BattingScorecard` | `ball_type_clusterer.py` |
| `player_improvement.py` | `Player`, `BattingScorecard` | `player_improvement_tracker.py` |
| `pressure_analysis.py` | `Game`, `Delivery` | `pressure_analyzer.py` |
| `tactical_suggestions.py` | `Game`, `BowlingScorecard`, `BattingScorecard`, `Player` | `tactical_suggestion_engine.py` |
| `training_drills.py` | `Player`, `BattingScorecard`, `Game` | `training_drill_generator.py` |
| `dismissal_patterns.py` | `Player`, `BattingScorecard`, `Game` | `dismissal_pattern_analyzer.py` |
| `phase_analysis.py` | (Multiple) | `phase_analyzer.py` |
| `sponsor_rotation.py` | (AsyncSession) | (N/A) |

---

## Step 1: Define Missing Models in `backend/sql_app/models.py`

### Player Model
```python
class Player(Base):
    """Cricket player profile."""
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=True)
    role = Column(String(50), nullable=True)  # Batsman, Bowler, All-rounder
    jersey_number = Column(Integer, nullable=True)
    # Add other player attributes as needed
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### BattingScorecard Model
```python
class BattingScorecard(Base):
    """Batting statistics for a player in a game."""
    __tablename__ = "batting_scorecards"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    
    runs = Column(Integer, default=0)
    balls_faced = Column(Integer, default=0)
    fours = Column(Integer, default=0)
    sixes = Column(Integer, default=0)
    is_wicket = Column(Boolean, default=False)
    dismissal_type = Column(String(50), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="batting_scorecards")
    player = relationship("Player")
```

### BowlingScorecard Model
```python
class BowlingScorecard(Base):
    """Bowling statistics for a player in a game."""
    __tablename__ = "bowling_scorecards"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    bowler_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    
    overs_bowled = Column(Float, default=0.0)
    runs_conceded = Column(Integer, default=0)
    wickets_taken = Column(Integer, default=0)
    maiden_overs = Column(Integer, default=0)
    extras_bowled = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    game = relationship("Game", back_populates="bowling_scorecards")
    bowler = relationship("Player")
```

### Delivery Model
```python
class Delivery(Base):
    """Individual ball delivery record."""
    __tablename__ = "deliveries"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    inning_number = Column(Integer, nullable=False)
    over = Column(Integer, nullable=False)
    ball = Column(Integer, nullable=False)
    
    bowler_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    batter_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    
    runs = Column(Integer, default=0)
    extras = Column(String(20), nullable=True)  # 'wd', 'nb', 'b', 'lb'
    is_wicket = Column(Boolean, default=False)
    wicket_type = Column(String(50), nullable=True)
    
    pitch_coordinate_x = Column(Float, nullable=True)
    pitch_coordinate_y = Column(Float, nullable=True)
    delivery_type = Column(String(50), nullable=True)  # 'fast', 'spin', etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    game = relationship("Game")
    bowler = relationship("Player", foreign_keys=[bowler_id])
    batter = relationship("Player", foreign_keys=[batter_id])
```

---

## Step 2: Update `Game` Model Relationships

Add these relationships to the existing `Game` model if not already present:

```python
class Game(Base):
    # ... existing fields ...
    
    # Add new relationships
    batting_scorecards = relationship("BattingScorecard", back_populates="game", cascade="all, delete-orphan")
    bowling_scorecards = relationship("BowlingScorecard", back_populates="game", cascade="all, delete-orphan")
    deliveries = relationship("Delivery", cascade="all, delete-orphan")
```

---

## Step 3: Create Database Migration

```bash
cd backend
alembic revision --autogenerate -m "Add Player, BattingScorecard, BowlingScorecard, Delivery models"
alembic upgrade head
```

---

## Step 4: Remove MyPy Ignores

Update `backend/pyproject.toml` to remove the disabled routes from the mypy ignore list:

**BEFORE:**
```toml
[[tool.mypy.overrides]]
module = [
    "backend.routes.pitch_heatmaps",
    "backend.routes.ball_clustering",
    "backend.routes.player_improvement",
    "backend.routes.pressure_analysis",
    "backend.routes.tactical_suggestions",
    "backend.routes.training_drills",
    "backend.routes.dismissal_patterns",
    "backend.routes.phase_analysis",
    "backend.routes.sponsor_rotation",
    "backend.services.pitch_heatmap_generator",
    "backend.services.ball_type_clusterer",
    "backend.services.player_improvement_tracker",
    "backend.services.pressure_analyzer",
    "backend.services.tactical_suggestion_engine",
    "backend.services.training_drill_generator",
    "backend.services.dismissal_pattern_analyzer",
    "backend.services.phase_analyzer",
]
ignore_errors = true
```

**AFTER:**
```toml
# Remove the section entirely or keep only if other service files need ignoring
```

---

## Step 5: Remove Ruff Ignores

Update `ruff.toml` to remove F821 from route files:

**BEFORE:**
```toml
"backend/routes/*.py" = ["B008", "S110", "S112", "S106", "B904", "E712", "W293", "E501", "SIM102", "F821"]
```

**AFTER:**
```toml
"backend/routes/*.py" = ["B008", "S110", "S112", "S106", "B904", "E712", "W293", "E501", "SIM102"]
```

---

## Step 6: Re-Enable Routes in `backend/app.py`

Uncomment the imports and registrations:

```python
# UNCOMMENT IMPORTS
from backend.routes.pitch_heatmaps import router as pitch_heatmaps_router
from backend.routes.ball_clustering import router as ball_clustering_router
from backend.routes.player_improvement import router as player_improvement_router
from backend.routes.pressure_analysis import router as pressure_analysis_router
from backend.routes.phase_analysis import router as phase_analysis_router
from backend.routes.tactical_suggestions import router as tactical_suggestions_router
from backend.routes.training_drills import router as training_drills_router
from backend.routes.dismissal_patterns import router as dismissal_patterns_router
from backend.routes.sponsor_rotation import router as sponsor_rotation_router

# ... later in create_app() ...

# UNCOMMENT REGISTRATIONS
fastapi_app.include_router(pitch_heatmaps_router)
fastapi_app.include_router(ball_clustering_router)
fastapi_app.include_router(player_improvement_router)
fastapi_app.include_router(pressure_analysis_router)
fastapi_app.include_router(phase_analysis_router)
fastapi_app.include_router(tactical_suggestions_router)
fastapi_app.include_router(training_drills_router)
fastapi_app.include_router(dismissal_patterns_router)
fastapi_app.include_router(sponsor_rotation_router)
```

---

## Step 7: Fix Route Type Annotations

Review each route file for type annotation issues. Common issues:

1. **AsyncSession dependencies** - Ensure using `Depends(get_db)`:
   ```python
   async def endpoint(db: AsyncSession = Depends(get_db)):
       # Correct usage
   ```

2. **Missing model imports** - Ensure importing models:
   ```python
   from backend.sql_app.models import Player, BattingScorecard, BowlingScorecard, Delivery, Game
   ```

3. **Type hints** - Add return type hints to endpoint functions:
   ```python
   @router.get("/path/{id}", response_model=SomeSchema)
   async def endpoint(id: int, db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
       ...
   ```

---

## Step 8: Test & Verify

```bash
# Test imports
cd backend
python -c "from backend.routes.pitch_heatmaps import router; print('Import successful')"

# Run linting
python -m ruff check . --config ruff.toml
python -m mypy . --config-file pyproject.toml

# Run tests
python -m pytest backend/tests/ -v
```

---

## Step 9: Commit & Push

```bash
git add .
git commit -m "feat: re-enable analytics routes with model definitions

- Add Player, BattingScorecard, BowlingScorecard, Delivery models
- Re-enable pitch_heatmaps, ball_clustering, player_improvement routes
- Re-enable pressure_analysis, tactical_suggestions, training_drills routes
- Re-enable dismissal_patterns, phase_analysis, sponsor_rotation routes
- Remove mypy and ruff ignores for now-valid code"

git push origin main
```

---

## Current Workflow Status

### ✅ Lint Workflow
- **Status**: PASSING
- **Checks**: 
  - Ruff lint: ✓
  - Ruff format: ✓
  - MyPy: ✓

### ✅ CI Workflow
- **Status**: PASSING
- **Checks**:
  - Pre-commit: ✓
  - Lint: ✓
  - Security (bandit, pip-audit): ✓
  - Tests: ✓

### ⏸️ Deploy Backend Workflow
- **Status**: Will pass once above workflows pass

---

## Troubleshooting

### If MyPy fails after uncommenting routes:
1. Check that all model imports are correct
2. Verify `AsyncSession = Depends(get_db)` usage in endpoint parameters
3. Add `# type: ignore` comments for complex type issues

### If Ruff fails:
1. Run `python -m ruff format .` to auto-fix formatting
2. Check for undefined names - ensure all models are imported
3. Check for line length violations - keep lines ≤ 100 characters

### If tests fail:
1. Verify models exist in database
2. Check that relationships are properly defined
3. Ensure fixtures create necessary test data

---

## Related Files
- [Models Definition](../backend/sql_app/models.py)
- [Ruff Configuration](../ruff.toml)
- [MyPy Configuration](../backend/pyproject.toml)
- [App Factory](../backend/app.py)
- [Workflow Definitions](.github/workflows/)

