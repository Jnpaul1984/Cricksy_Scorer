"""
Top-level pytest configuration imported early during collection.

This module sets Windows' selector event loop policy and forces AnyIO to
use the asyncio backend so asyncpg/SQLAlchemy don't end up using a different
event loop from pytest/anyio on Windows.

If you prefer to run tests in WSL or CI, you can remove this file.
"""

import os
import sys
import contextlib

# Force AnyIO to use asyncio backend unless explicitly overridden.
os.environ.setdefault("ANYIO_BACKEND", "asyncio")

# On Windows, use the selector event loop policy which is compatible
# with some libraries (asyncpg, SQLAlchemy asyncpg dialect) that have
# known issues with the default ProactorEventLoop in certain test
# harnesses. Wrap in contextlib.suppress so test collection doesn't fail
# if this can't be set for any reason.
if sys.platform.startswith("win"):
    import asyncio as _asyncio

    with contextlib.suppress(Exception):
        _asyncio.set_event_loop_policy(_asyncio.WindowsSelectorEventLoopPolicy())
