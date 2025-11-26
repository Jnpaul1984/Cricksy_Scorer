#!/usr/bin/env python3
"""
Create or update a superuser in the application's database.

Usage:
  python backend/scripts/create_superuser.py --email admin@example.com
  (it will prompt for password)

This script works against whatever sqlalchemy async session is configured in
`backend.sql_app.database`. If you run with IN_MEMORY_DB enabled it will also
register the created user in the in-memory cache so auth works during dev.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import getpass
import sys

from sqlalchemy import select

# When this script is executed directly the package root may not be on sys.path
# (ModuleNotFoundError: No module named 'backend'). Ensure repository root
# is on sys.path so imports like `backend.config` work when running
# `python backend/scripts/create_superuser.py` from the repo root.
try:
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
except Exception:
    # best-effort only; if this fails the original import error will surface
    pass

from backend import security
from backend.config import settings
from backend.sql_app import models
from backend.sql_app.database import SessionLocal


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True, help="Email for the superuser")
    parser.add_argument("--password", help="Password (optional; will prompt if omitted)")
    args = parser.parse_args()

    email = args.email.strip().lower()
    pwd = args.password if args.password else getpass.getpass(f"Password for {email}: ")

    hashed = security.get_password_hash(pwd)

    async with SessionLocal() as session:
        stmt = select(models.User).where(models.User.email == email)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()
        if user:
            print(f"User exists, updating password & elevating to superuser: {email}")
            user.hashed_password = hashed
            user.is_superuser = True
            user.is_active = True
        else:
            print(f"Creating new superuser: {email}")
            user = models.User(
                email=email,
                hashed_password=hashed,
                is_active=True,
                is_superuser=True,
            )
            session.add(user)
        try:
            await session.commit()
            with contextlib.suppress(Exception):
                await session.refresh(user)
        except Exception as exc:
            await session.rollback()
            print("Database error while creating/updating user:", exc)
            return 2

    # If running with IN_MEMORY_DB enabled, also add to in-memory cache so the
    # application's in-memory auth fallback can find the user.
    try:
        if bool(getattr(settings, "IN_MEMORY_DB", False)):
            security.add_in_memory_user(user)
            print("Also registered user in in-memory cache (IN_MEMORY_DB enabled).")
    except Exception:
        pass

    print("Done. Superuser id:", getattr(user, "id", None))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
