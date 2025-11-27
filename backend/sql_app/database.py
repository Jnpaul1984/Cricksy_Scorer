from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from backend.config import settings

# This is a base class that our table models will inherit from.
Base = declarative_base()

# Check if in-memory DB mode is enabled
USE_IN_MEMORY_DB = bool(getattr(settings, "IN_MEMORY_DB", False))

# Engine and SessionLocal will be created lazily or can be overridden for tests
_engine: AsyncEngine | None = None
_SessionLocal: async_sessionmaker[AsyncSession] | None = None


def _create_engine_and_session() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create engine and session maker based on configuration."""
    import os

    # Check if we're in a testing environment
    is_testing = os.environ.get("PYTEST_CURRENT_TEST") is not None

    if USE_IN_MEMORY_DB:
        # In-memory SQLite for CI and testing
        database_url = "sqlite+aiosqlite:///:memory:?cache=shared"
        eng = create_async_engine(
            database_url,
            connect_args={"check_same_thread": False},
            future=True,
        )
        session_local = async_sessionmaker(
            bind=eng,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    else:
        # Production or test PostgreSQL database
        database_url = settings.database_url

        # Use NullPool when testing to avoid event loop issues with asyncpg
        # NullPool creates a new connection for each request and closes it after,
        # which prevents "Future attached to a different loop" errors when
        # Starlette's TestClient creates its own event loop.
        if is_testing:
            eng = create_async_engine(
                database_url,
                poolclass=NullPool,
                echo=False,
            )
        else:
            eng = create_async_engine(database_url, pool_pre_ping=True)

        session_local = async_sessionmaker(autocommit=False, autoflush=False, bind=eng)

    return eng, session_local


def get_engine() -> AsyncEngine:
    """Get or create the database engine."""
    global _engine, _SessionLocal
    if _engine is None:
        _engine, _SessionLocal = _create_engine_and_session()
    return _engine


def get_session_local() -> async_sessionmaker[AsyncSession]:
    """Get or create the session maker."""
    global _engine, _SessionLocal
    if _SessionLocal is None:
        _engine, _SessionLocal = _create_engine_and_session()
    return _SessionLocal


def reset_engine() -> None:
    """Reset the engine - useful for tests to create engine on correct event loop."""
    global _engine, _SessionLocal
    _engine = None
    _SessionLocal = None


# Keep module-level access for backward compatibility
# These will be lazily initialized on first access
class _LazyEngine:
    """Lazy proxy for engine to maintain backward compatibility."""

    def __getattr__(self, name: str) -> Any:
        return getattr(get_engine(), name)

    def begin(self) -> Any:
        """Proxy for engine.begin() - commonly used method."""
        return get_engine().begin()

    async def dispose(self) -> None:
        """Proxy for engine.dispose() - commonly used method."""
        await get_engine().dispose()


class _LazySessionLocal:
    """Lazy proxy for SessionLocal to maintain backward compatibility."""

    def __call__(self, *args: Any, **kwargs: Any) -> AsyncSession:
        return get_session_local()(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(get_session_local(), name)


# Replace module-level variables with lazy proxies
engine: _LazyEngine = _LazyEngine()
SessionLocal: _LazySessionLocal = _LazySessionLocal()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_local()() as session:
        yield session
