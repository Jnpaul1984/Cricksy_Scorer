from __future__ import annotations

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from collections.abc import AsyncGenerator
import os

# This is a base class that our table models will inherit from.
Base = declarative_base()

# Check if we're running in in-memory mode before creating engine
_IN_MEMORY_MODE = os.getenv("CRICKSY_IN_MEMORY_DB") == "1"

if _IN_MEMORY_MODE:
    # In memory mode: don't create real engine or session maker
    # The app.py will provide fake sessions via dependency overrides
    engine = None  # type: ignore[assignment]
    SessionLocal = None  # type: ignore[assignment]
else:
    # Normal mode: create real database engine and session maker
    # The database URL tells SQLAlchemy where our database is located.
    SQLALCHEMY_DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:RubyAnita2018@localhost:5555/cricksy_scorer",
    )

    # The engine is the main entry point for SQLAlchemy to talk to the DB.
    engine = create_async_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

    # A session is what we use to actually execute queries.
    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get a database session.
    In in-memory mode, this will be overridden by app.py.
    """
    if SessionLocal is None:
        # This should not happen if dependency overrides work correctly
        raise RuntimeError(
            "Database not configured. Set DATABASE_URL or use CRICKSY_IN_MEMORY_DB=1"
        )
    async with SessionLocal() as session:
        yield session
