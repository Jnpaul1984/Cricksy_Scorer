from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str | int | list[str]]:
    """Check database connectivity and list tables."""
    try:
        # Test basic connectivity
        result = await db.execute(text("SELECT 1"))
        result.scalar()

        # List all tables
        tables_result = await db.execute(
            text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)
        )
        tables = [row[0] for row in tables_result.fetchall()]

        # Check users table specifically
        users_count = 0
        if "users" in tables:
            count_result = await db.execute(text("SELECT COUNT(*) FROM users"))
            users_count = count_result.scalar() or 0

        return {
            "status": "ok",
            "tables": tables,
            "table_count": len(tables),
            "users_count": users_count,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "tables": [],
            "table_count": 0,
            "users_count": 0,
        }
