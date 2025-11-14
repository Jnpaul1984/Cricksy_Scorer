from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from backend.config import settings

# This is a base class that our table models will inherit from.
Base = declarative_base()

# Check if in-memory DB mode is enabled
USE_IN_MEMORY_DB = bool(getattr(settings, "IN_MEMORY_DB", False))

if USE_IN_MEMORY_DB:
    # In-memory SQLite for CI and testing
    DATABASE_URL = "sqlite+aiosqlite:///:memory:?cache=shared"
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        future=True,
    )
    SessionLocal = async_sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
else:
    # Production PostgreSQL database
    DATABASE_URL = settings.database_url
    engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


def get_database_url() -> str:
    """Get the synchronous database URL for Celery workers."""
    if USE_IN_MEMORY_DB:
        return "sqlite:///cricksy_scorer_test.db"
    else:
        # Convert asyncpg URL to psycopg2 URL for synchronous operations
        url = os.getenv(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:RubyAnita2018@localhost:5555/cricksy_scorer",
        )
        return url.replace("postgresql+asyncpg://", "postgresql://").replace("+asyncpg", "")
