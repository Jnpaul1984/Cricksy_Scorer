"""
Top-level pytest configuration imported early during collection.

This module sets Windows' selector event loop policy and forces AnyIO to
use the asyncio backend so asyncpg/SQLAlchemy don't end up using a different
event loop from pytest/anyio on Windows.

If you prefer to run tests in WSL or CI, you can remove this file.
"""

import asyncio
import contextlib
import os
import pathlib
import sys

import pytest
import pytest_asyncio

# Force AnyIO to use asyncio backend unless explicitly overridden.
os.environ.setdefault("ANYIO_BACKEND", "asyncio")

# Set test environment variables BEFORE importing backend modules
# Only use in-memory SQLite if DATABASE_URL is not already set (e.g. by CI or local env)
if "DATABASE_URL" not in os.environ:
    os.environ["CRICKSY_IN_MEMORY_DB"] = "1"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:?cache=shared"
    os.environ["APP_SECRET_KEY"] = "test-secret-key"  # noqa: S105

# Repo root = current directory
ROOT = pathlib.Path(__file__).resolve().parent
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

# On Windows, use the selector event loop policy which is compatible
# with some libraries (asyncpg, SQLAlchemy asyncpg dialect) that have
# known issues with the default ProactorEventLoop in certain test
# harnesses. Wrap in contextlib.suppress so test collection doesn't fail
# if this can't be set for any reason.
if sys.platform.startswith("win"):
    import asyncio as _asyncio

    with contextlib.suppress(Exception):
        _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop():
    """
    Create a session-scoped event loop for the entire test session.
    pytest-asyncio 0.23+ with asyncio_default_fixture_loop_scope="session"
    will use this loop for all async fixtures.
    """
    # Reset the database engine before creating the loop
    # This ensures engine will be created on this new loop
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
    This runs once at the start of the test session on the correct event loop.
    """
    from backend.sql_app.database import Base, get_engine

    engine = get_engine()

    # Create all tables once at session start
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Clean up at session end
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
