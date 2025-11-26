# backend/tests/conftest.py
import pathlib
import sys
import os
import asyncio  # Add this

# Set test environment variables BEFORE importing backend modules
# Only use in-memory SQLite if DATABASE_URL is not already set (e.g. by CI or local env)
if "DATABASE_URL" not in os.environ:
    os.environ["CRICKSY_IN_MEMORY_DB"] = "1"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:?cache=shared"
    os.environ["APP_SECRET_KEY"] = "test-secret-key"

import pytest
from backend.sql_app.database import Base, engine

# Import models to ensure they are registered with Base.metadata
import backend.sql_app.models  # noqa: F401

# Repo root = two levels up from this file (Cricksy_Scorer/)
ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an instance of the default event loop for the test session.
    This prevents 'Task attached to a different loop' errors when using
    session-scoped fixtures or shared resources like the DB engine.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def reset_db():
    """Reset the database state before each test."""
    print("\n[DEBUG] reset_db: Starting DB reset...")

    # Import here to avoid circular imports if any
    import backend.security

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Clear in-memory user cache (critical for tests using IN_MEMORY_DB)
    backend.security._in_memory_users.clear()
    print("[DEBUG] reset_db: Cleared in-memory user cache.")

    print("[DEBUG] reset_db: DB reset complete.\n")
