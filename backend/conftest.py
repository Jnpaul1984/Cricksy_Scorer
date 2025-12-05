# backend/conftest.py
"""
Backend-specific pytest configuration.

This file imports the shared fixtures from the root conftest.py and makes them
available to all tests in the backend directory.
"""

import asyncio
import contextlib
import os
import sys

import pytest
import pytest_asyncio

# Force AnyIO to use asyncio backend unless explicitly overridden.
os.environ.setdefault("ANYIO_BACKEND", "asyncio")

# Set test environment variables BEFORE importing backend modules
if "DATABASE_URL" not in os.environ:
    os.environ["CRICKSY_IN_MEMORY_DB"] = "1"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:?cache=shared"
    os.environ["APP_SECRET_KEY"] = "test-secret-key"

# On Windows, use the selector event loop policy
if sys.platform.startswith("win"):
    with contextlib.suppress(Exception):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop():
    """
    Create a session-scoped event loop for the entire test session.
    """
    from backend.sql_app.database import reset_engine

    reset_engine()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def _setup_db():
    """
    Session-scoped fixture to set up the database engine and create tables.
    """
    from backend.sql_app.database import Base, get_engine

    engine = get_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def reset_db(_setup_db):
    """Reset the database state before each test."""
    import backend.security
    from backend.sql_app.database import Base, get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Clear in-memory user cache (critical for tests using IN_MEMORY_DB)
    backend.security._in_memory_users.clear()
