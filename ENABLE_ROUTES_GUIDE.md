# How to Re-Enable Disabled Routes

## Status: Models ✅ ADDED | Routes ⏸️ DISABLED

### Current Progress
**COMPLETED:**
- ✅ Added all 4 required models (Player, BattingScorecard, BowlingScorecard, Delivery)
- ✅ Updated Game model with relationships
- ✅ Models ready for production database migration
- ✅ App initializes successfully with models

**IN PROGRESS:**
- ⏳ Route endpoints need type annotation fixes (AsyncSession dependency, return types)
- ⏳ Database migration generation pending

**PENDING:**
- Routes enabled after endpoint fixes

---

## Overview
9 route modules are currently disabled due to incomplete endpoint implementations. This guide explains what needs to be done to re-enable them.

**Current Status:** Models created, routes awaiting endpoint implementation fixes.

---

## Disabled Routes & Required Models

| Route File | Status | Required Models | Service File |
|---|---|---|---|
| `pitch_heatmaps.py` | ⏸️ Disabled | `Player`, `BattingScorecard` | `pitch_heatmap_generator.py` |
| `ball_clustering.py` | ⏸️ Disabled | `Player`, `BowlingScorecard`, `BattingScorecard` | `ball_type_clusterer.py` |
| `player_improvement.py` | ⏸️ Disabled | `Player`, `BattingScorecard` | `player_improvement_tracker.py` |
| `pressure_analysis.py` | ⏸️ Disabled | `Game`, `Delivery` | `pressure_analyzer.py` |
| `tactical_suggestions.py` | ⏸️ Disabled | `Game`, `BowlingScorecard`, `BattingScorecard`, `Player` | `tactical_suggestion_engine.py` |
| `training_drills.py` | ⏸️ Disabled | `Player`, `BattingScorecard`, `Game` | `training_drill_generator.py` |
| `dismissal_patterns.py` | ⏸️ Disabled | `Player`, `BattingScorecard`, `Game` | `dismissal_pattern_analyzer.py` |
| `phase_analysis.py` | ⏸️ Disabled | (Multiple) | `phase_analyzer.py` |
| `sponsor_rotation.py` | ⏸️ Disabled | (AsyncSession) | (N/A) |

---

## Step 1: Define Missing Models in `backend/sql_app/models.py`

### ✅ COMPLETED - Player Model
```python
class Player(Base):
    """Cricket player profile."""
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    country = Column(String(100), nullable=True)
    role = Column(String(50), nullable=True)  # Batsman, Bowler, All-rounder
    jersey_number = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### ✅ COMPLETED - BattingScorecard Model
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

### ✅ COMPLETED - BowlingScorecard Model
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

### ✅ COMPLETED - Delivery Model
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

### ✅ COMPLETED
Added these relationships to the existing `Game` model:

```python
class Game(Base):
    # ... existing fields ...

    # New relationships for analytics routes
    batting_scorecards = relationship("BattingScorecard", back_populates="game", cascade="all, delete-orphan")
    bowling_scorecards = relationship("BowlingScorecard", back_populates="game", cascade="all, delete-orphan")
```

---

## Step 3: ⏳ NEXT - Fix Route Endpoint Signatures

The disabled routes have endpoint implementations that need fixes:

### Required Changes for Each Route

1. **Import Statements** - Add these imports:
   ```python
   from fastapi import Depends
   from backend.sql_app.database import get_db
   from backend.sql_app.models import Player, BattingScorecard, BowlingScorecard, Delivery, Game
   ```

2. **Fix AsyncSession Parameters** - Change from:
   ```python
   async def get_monthly_stats(player_id: str, db: AsyncSession | None = None)
   ```
   To:
   ```python
   async def get_monthly_stats(player_id: str, db: AsyncSession = Depends(get_db))
   ```

3. **Add Return Type Hints** - All endpoints should have explicit return types:
   ```python
   async def get_monthly_stats(...) -> dict[str, Any]:
   ```

### Routes Needing Fixes

- **player_improvement.py** - Needs AsyncSession dependency fixes + type hints
- **pressure_analysis.py** - Needs AsyncSession dependency fixes + type hints
- **phase_analysis.py** - Needs AsyncSession dependency fixes + type hints
- **tactical_suggestions.py** - Needs AsyncSession dependency fixes + type hints
- **training_drills.py** - Needs AsyncSession dependency fixes + type hints
- **dismissal_patterns.py** - Needs AsyncSession dependency fixes + type hints
- **pitch_heatmaps.py** - Needs AsyncSession dependency fixes + type hints
- **ball_clustering.py** - Needs AsyncSession dependency fixes + type hints
- **sponsor_rotation.py** - Needs AsyncSession dependency fixes + type hints

---

## Step 4: Create Database Migration

Once endpoint fixes are complete:

```bash
cd backend
alembic revision --autogenerate -m "Add Player, BattingScorecard, BowlingScorecard, Delivery models"
alembic upgrade head
```

---

## Step 5: Remove MyPy Ignores

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

## Step 6: Remove Ruff Ignores

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

## Step 7: Re-Enable Routes in `backend/app.py`

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

### ✅ Models Status
- **Status**: READY FOR MIGRATION
- **Created**:
  - Player model ✓
  - BattingScorecard model ✓
  - BowlingScorecard model ✓
  - Delivery model ✓
- **Game model relationships**: ✓ Added

### ⏸️ Routes Status
- **Awaiting**: Endpoint type annotation fixes
- **Blocked by**: AsyncSession dependency injection cleanup

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
- [Models Definition](backend/sql_app/models.py) - ✅ Updated
- [Ruff Configuration](ruff.toml) - Ready for cleanup
- [MyPy Configuration](backend/pyproject.toml) - Ready for cleanup
- [App Factory](backend/app.py) - Routes disabled, awaiting fixes
- [Workflow Definitions](.github/workflows/)
