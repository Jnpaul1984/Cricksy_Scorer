# Cricksy Scorer - AI Coding Instructions

## Project Overview
Cricket scoring application with a **FastAPI + Socket.IO backend** (Python 3.12) and **Vue 3 + Vite frontend** (TypeScript). PostgreSQL for production, SQLite in-memory for testing.

## Architecture

### Backend Structure (`backend/`)
- **Entry point**: `main.py` → `app.py:create_app()` builds FastAPI + Socket.IO ASGI app
- **Routes**: `routes/*.py` - REST endpoints organized by domain (gameplay, games, tournaments, ai, etc.)
- **Services**: `services/*.py` - Business logic (scoring_service, prediction_service, live_bus)
- **Models/Schemas**: `sql_app/models.py` (SQLAlchemy ORM), `sql_app/schemas.py` (Pydantic DTOs)
- **Real-time**: `socket_handlers.py` + `services/live_bus.py` for WebSocket presence/updates
- **Domain rules**: `domain/constants.py` - Cricket-specific rules (dismissal types, extras)

### Frontend Structure (`frontend/src/`)
- **State**: `stores/gameStore.ts` (Pinia) - central game state, Socket.IO event handlers
- **Views**: `views/*.vue` - page components
- **Components**: `components/*.vue` - reusable UI components
- **API**: `utils/api.ts`, `services/api.ts` - typed API client

### Data Flow
1. Scorer submits delivery → `POST /games/{id}/deliveries`
2. `scoring_service.score_one()` updates game state
3. `live_bus.emit_state_update()` broadcasts via Socket.IO
4. All clients receive `state:update` event → Pinia store updates UI

## Development Commands

### Backend
```powershell
# Set PYTHONPATH (CRITICAL - backend uses absolute imports like `from backend.sql_app import models`)
$env:PYTHONPATH = "C:\Users\Hp\Cricksy_Scorer"

# Run tests (in-memory SQLite)
$env:CRICKSY_IN_MEMORY_DB = "1"
cd backend; pytest tests/ -q

# Run server locally
uvicorn backend.main:app --reload --port 8000

# Database migrations
cd backend; alembic upgrade head
cd backend; alembic revision --autogenerate -m "description"
```

### Frontend
```powershell
cd frontend
npm install
npm run dev          # Vite dev server
npm run test:unit    # Vitest
npm run build        # Production build with type-check
```

### Docker (Full Stack)
```powershell
docker compose up -d db backend   # Postgres on :5555, API on :8000
docker compose logs -f backend
```

## Coding Conventions

### Python Backend
- **Imports**: Use absolute paths (`from backend.sql_app import models`, not relative)
- **Async**: All DB operations use `async/await` with `AsyncSession`
- **Linting**: Ruff + mypy (see `pyproject.toml`), ignore B008 for FastAPI `Depends()`
- **Type hints**: Required on public functions; use `Any` sparingly with type casts
- **Tests**: Use `pytest-asyncio`; fixtures in `conftest.py` handle DB reset per test

### TypeScript Frontend
- **State**: Pinia stores with Composition API (`defineStore` + `ref/computed`)
- **Socket events**: Typed via `ServerEvents` interface in gameStore
- **API calls**: Use typed functions from `utils/api.ts`

## Key Patterns

### Scoring a Delivery
```python
# services/scoring_service.py
from backend.domain.constants import CREDIT_BOWLER, norm_extra

def score_one(g, striker_id, bowler_id, runs, extra, is_wicket, ...):
    extra_code = norm_extra(extra)  # Normalize "wide" → "wd"
    # ... update batting/bowling scorecards, handle strike rotation
```

### Real-time Updates
```python
# After scoring, emit to all clients in game room:
from backend.services.live_bus import emit_state_update
await emit_state_update(game_id, snapshot)
```

### Testing with In-Memory DB
```python
# conftest.py sets up SQLite automatically when CRICKSY_IN_MEMORY_DB=1
@pytest_asyncio.fixture(autouse=True)
async def reset_db(_setup_db):
    # Drops and recreates all tables before each test
```

## Environment Variables
| Variable | Purpose | Test Value |
|----------|---------|------------|
| `DATABASE_URL` | Postgres connection | `sqlite+aiosqlite:///:memory:?cache=shared` |
| `CRICKSY_IN_MEMORY_DB` | Enable SQLite mode | `1` |
| `APP_SECRET_KEY` | JWT signing | `test-secret-key` |
| `PYTHONPATH` | Import resolution | Repo root path |

## Common Pitfalls
- **Windows async**: Uses `WindowsSelectorEventLoopPolicy` for asyncpg compatibility
- **Pydantic v2**: Use `.model_dump()` not `.dict()`
- **Socket.IO room**: Clients join via `join` event with `{game_id, role, name}`
- **Overs calculation**: 6 legal balls = 1 over; wides/no-balls don't count as legal

## File References
- Core scoring logic: `backend/services/scoring_service.py`
- Game state model: `backend/sql_app/models.py:Game`
- API routes: `backend/routes/gameplay.py`
- Frontend store: `frontend/src/stores/gameStore.ts`
- Test fixtures: `conftest.py` (root) and `backend/conftest.py`
