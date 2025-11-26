"""Instrumentation to trace where asyncpg pool/connect calls are made.

Enable by setting CRICKSY_DEBUG_ASYNCPG=1 in the environment before running
tests. This module monkeypatches asyncpg.create_pool and asyncpg.connect to
log the current asyncio loop id and a short stacktrace to
artifacts/asyncpg_trace.log when these functions are invoked.

This is a debugging aid only and is safe to import; when the env var is not
set this module is a no-op.
"""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import time
import traceback
from collections.abc import Callable
from typing import Any

_ENABLED = os.getenv("CRICKSY_DEBUG_ASYNCPG") == "1"

if _ENABLED:
    try:
        import asyncpg
    except Exception:  # pragma: no cover - best-effort diagnostic
        asyncpg = None  # nosec

    ARTIFACTS = pathlib.Path(__file__).resolve().parents[1] / "artifacts"
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    LOG = ARTIFACTS / "asyncpg_trace.log"

    def _write_log(
        kind: str, func_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> None:
        try:
            try:
                loop = asyncio.get_running_loop()
                loop_id = id(loop)
            except Exception:
                loop = None
                loop_id = None

            rec = {
                "ts": time.time(),
                "kind": kind,
                "func": func_name,
                "loop_id": loop_id,
                "args": [str(a)[:200] for a in args],
                "kwargs": {k: str(v)[:200] for k, v in kwargs.items()},
                "stack": traceback.format_stack()[-10:],
            }
            with LOG.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
        except Exception:
            # Never raise during diagnostics
            pass  # nosec

    def _wrap(name: str, fn: Callable[..., Any]) -> Callable[..., Any]:
        def _inner(*args: Any, **kwargs: Any) -> Any:
            _write_log("call", name, args, kwargs)
            return fn(*args, **kwargs)

        return _inner

    if asyncpg is not None:
        # Monkeypatch create_pool and connect (both sync-callables that return
        # awaitables/objects depending on usage in SQLAlchemy/asyncpg layers).
        if hasattr(asyncpg, "create_pool"):
            asyncpg.create_pool = _wrap("asyncpg.create_pool", asyncpg.create_pool)
        if hasattr(asyncpg, "connect"):
            asyncpg.connect = _wrap("asyncpg.connect", asyncpg.connect)
