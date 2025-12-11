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


@router.get("/health/admin")
async def health_admin(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Check admin user configuration (debug endpoint)."""
    try:
        result = await db.execute(
            text("SELECT email, LEFT(hashed_password, 20) as hash_prefix FROM users LIMIT 1")
        )
        row = result.fetchone()

        # Get alembic version
        version_result = await db.execute(text("SELECT version_num FROM alembic_version"))
        version_row = version_result.fetchone()
        alembic_version = version_row[0] if version_row else "unknown"

        if row:
            return {
                "status": "ok",
                "email": row[0],
                "hash_prefix": row[1],
                "hash_format": "pbkdf2"
                if ":" in row[1]
                else "bcrypt"
                if row[1].startswith("$")
                else "unknown",
                "alembic_version": alembic_version,
            }
        return {"status": "no_users", "alembic_version": alembic_version}
    except Exception as e:
        return {"status": "error", "error": str(e)}
