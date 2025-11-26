# backend/tests/conftest.py
import pathlib
import sys
import os

# Set test environment variables BEFORE importing backend modules
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


@pytest.fixture(autouse=True)
async def reset_db():
    """Reset the database state before each test."""
    print("\n[DEBUG] reset_db: Starting DB reset...")

    # Check user count before reset
    from backend.sql_app.database import SessionLocal
    from backend.sql_app import models
    from sqlalchemy import select

    try:
        async with SessionLocal() as session:
            result = await session.execute(select(models.User))
            users = result.scalars().all()
            print(f"[DEBUG] Users before reset: {len(users)}")
    except Exception as e:
        print(f"[DEBUG] Could not count users before reset: {e}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Check user count after reset
    try:
        async with SessionLocal() as session:
            result = await session.execute(select(models.User))
            users = result.scalars().all()
            print(f"[DEBUG] Users after reset: {len(users)}")
    except Exception as e:
        print(f"[DEBUG] Could not count users after reset: {e}")

    # Clear in-memory user cache (critical for tests using IN_MEMORY_DB)
    import backend.security

    backend.security._in_memory_users.clear()
    print("[DEBUG] reset_db: Cleared in-memory user cache.")

    print("[DEBUG] reset_db: DB reset complete.\n")
