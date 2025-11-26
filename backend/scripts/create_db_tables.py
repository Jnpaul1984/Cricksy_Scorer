#!/usr/bin/env python3
"""
Create database tables from SQLAlchemy metadata for the configured DATABASE_URL.

Usage:
  $env:DATABASE_URL='sqlite+aiosqlite:///./dev.db'; python backend/scripts/create_db_tables.py

This will run Base.metadata.create_all() against the async engine.
"""

from __future__ import annotations

import asyncio
import sys

# Ensure repo root is on sys.path when executed directly
try:
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
except Exception:
    pass  # nosec

from backend.sql_app.database import engine
from backend.sql_app.models import Base


async def main():
    async with engine.begin() as conn:
        # run_sync bridges to the synchronous create_all
        await conn.run_sync(Base.metadata.create_all)
    print("OK: Created tables (if they did not exist)")


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
