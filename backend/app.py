from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import suppress
from pathlib import Path
from typing import Any
import asyncio

import socketio  # type: ignore[import-not-found]
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# DB dependency and in-memory wiring
# sqlalchemy AsyncSession is provided by database.get_db dependency when needed

from backend.config import settings as default_settings
from backend.error_handlers import install_exception_handlers  # NEW

# Observability and error handling (install on FastAPI app, not ASGI wrapper)
from backend.middleware.observability import (
    AccessLogMiddleware,
    CorrelationIdMiddleware,
)  # NEW
from backend.routes.dls import router as dls_router
from backend.routes.game_admin import router as game_admin_router
from backend.routes.gameplay import get_db as gameplay_get_db
from backend.routes.gameplay import router as gameplay_router  # type: ignore[attr-defined]
from backend.routes.games_core import router as games_core_router  # NEW
from backend.routes.games_dls import router as games_dls_router

# Routers
from backend.routes.games_router import router as games_router
from backend.routes.health import router as health_router
from backend.routes.interruptions import router as interruptions_router
from backend.routes.players import router as players_router
from backend.routes.prediction import router as prediction_router
from backend.routes.sponsors import router as sponsors_router
from backend.routes.tournaments import router as tournaments_router
from backend.services.live_bus import set_socketio_server as _set_bus_sio

# Socket handlers and live bus
from backend.socket_handlers import register_sio
from backend.sql_app import database as db
from backend.sql_app.database import get_db as db_get_db  # type: ignore[unused-ignore]

__all__ = ["create_app"]

# Optional in-memory CRUD support
InMemoryCrudRepoClass: Any | None = None
enable_in_memory_crud_fn: Any | None = None
_memory_repo: Any | None = None
try:
    from backend.testsupport.in_memory_crud import (
        InMemoryCrudRepository as _IMRepo,
    )
    from backend.testsupport.in_memory_crud import (
        enable_in_memory_crud as _enable_fn,
    )

    InMemoryCrudRepoClass = _IMRepo
    enable_in_memory_crud_fn = _enable_fn
except Exception:
    InMemoryCrudRepoClass = None
    enable_in_memory_crud_fn = None


# Minimal no-op async session & result for in-memory mode safety
class _FakeResult:
    def scalars(self) -> _FakeResult:
        return self

    def all(self) -> list[Any]:
        # synchronous .all() to match SQLAlchemy's Result.scalars().all()
        return []

    def first(self) -> Any | None:
        return None

    def scalar_one_or_none(self) -> Any | None:
        return None


class _MemoryExecResult(_FakeResult):
    """Result wrapper used by the in-memory session to return async .all() values.

    The wrapper implements async all() and keeps scalars() returning itself so
    callers can do `await res.scalars().all()` or `await res.all()`.
    """

    def __init__(self, fetcher: Any):
        # fetcher should be a callable that returns an awaitable returning a list
        self._fetcher = fetcher

    def all(self) -> Any:
        """Return an object that is both awaitable and iterable/list-like.

        - Awaiting it runs the underlying async fetcher and returns the list.
        - Iterating over it (or accessing like a list) will attempt to fetch the
          data synchronously when possible; if the fetcher is async and the
          event loop is running, iteration will fall back to an empty list to
          avoid runtime errors.
        """

        fetcher = self._fetcher

        class _MaybeAwaitableList:
            def __init__(self, fetcher: Any):
                self._fetcher = fetcher
                self._value: list[Any] | None = None

            def _ensure_sync(self) -> list[Any]:
                if self._value is not None:
                    return self._value
                try:
                    val = self._fetcher()
                except TypeError:
                    val = self._fetcher

                if hasattr(val, "__await__"):
                    # If the loop is not running we can run the coroutine.
                    try:
                        loop = asyncio.get_event_loop()
                    except RuntimeError:
                        loop = None

                    if loop is None or not loop.is_running():
                        # Safe to run synchronously
                        try:
                            self._value = asyncio.get_event_loop().run_until_complete(val)
                        except Exception:
                            self._value = []
                    else:
                        # We're inside an event loop; can't run coroutine synchronously
                        self._value = []
                else:
                    self._value = val

                return self._value if self._value is not None else []

            # Make it awaitable
            def __await__(self):
                try:
                    val = self._fetcher()
                except TypeError:
                    val = self._fetcher

                if hasattr(val, "__await__"):
                    return val.__await__()

                async def _wrap():
                    return val

                return _wrap().__await__()

            # list-like methods
            def __iter__(self):
                return iter(self._ensure_sync())

            def __len__(self):
                return len(self._ensure_sync())

            def __getitem__(self, idx: int):
                return self._ensure_sync()[idx]

            def __repr__(self) -> str:  # pragma: no cover - convenience
                return repr(self._ensure_sync())

        return _MaybeAwaitableList(fetcher)


class _FakeSession:
    def add(self, obj: Any) -> None:
        pass

    def add_all(self, seq: list[Any]) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def refresh(self, obj: Any) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def execute(self, *args: Any, **kwargs: Any) -> _FakeResult:
        # Patch: If the query is for games with results, return those from in-memory CRUD
        # use the repo class configured at module import time (tests support)
        repo_class = InMemoryCrudRepoClass
        # Detect query for games with result
        if args and hasattr(args[0], "whereclause") and "result" in str(args[0].whereclause):
            repo = globals().get("_memory_repo")
            if repo is None and repo_class is not None:
                repo = repo_class()
                globals()["_memory_repo"] = repo
            if repo is not None:
                # return an execution result whose .scalars().all() is awaitable
                return _MemoryExecResult(lambda: repo.list_games_with_result())
        if args and "from games" in str(args[0]).lower():
            repo = globals().get("_memory_repo")
            if repo is None and repo_class is not None:
                repo = repo_class()
                globals()["_memory_repo"] = repo
            if repo is not None:
                # return all stored games (sync list wrapped in async fetcher)
                return _MemoryExecResult(lambda: list(repo._games.values()))
        return _FakeResult()

    # ADD THIS: emulate AsyncSession.scalar(...) for in-memory mode
    async def scalar(self, *args: Any, **kwargs: Any) -> Any | None:
        # We don't have a real DB in in-memory mode; returning None lets routes 404 cleanly
        return None


def create_app(
    settings_override: Any | None = None,
) -> tuple[socketio.ASGIApp, FastAPI]:
    settings = settings_override or default_settings

    logging.basicConfig(
        level=getattr(logging, str(settings.LOG_LEVEL).upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    _sio = socketio.AsyncServer(
        async_mode="asgi", cors_allowed_origins=settings.SIO_CORS_ALLOWED_ORIGINS
    )  # type: ignore[call-arg]
    sio = _sio
    fastapi_app = FastAPI(title="Cricksy Scorer API")
    fastapi_app.state.sio = sio

    # Install middlewares and exception handlers on FastAPI app (not ASGI wrapper)
    fastapi_app.add_middleware(CorrelationIdMiddleware)  # ensures request_id for error payloads
    fastapi_app.add_middleware(AccessLogMiddleware)
    install_exception_handlers(fastapi_app)

    STATIC_ROOT: Path = settings.STATIC_ROOT
    fastapi_app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_sio(sio)
    _set_bus_sio(sio)

    # Include routers
    fastapi_app.include_router(games_dls_router)
    fastapi_app.include_router(interruptions_router)
    fastapi_app.include_router(games_router)
    fastapi_app.include_router(gameplay_router)
    fastapi_app.include_router(dls_router)
    fastapi_app.include_router(game_admin_router)
    fastapi_app.include_router(health_router)
    fastapi_app.include_router(sponsors_router)
    fastapi_app.include_router(games_core_router)
    fastapi_app.include_router(prediction_router)
    fastapi_app.include_router(players_router)
    fastapi_app.include_router(tournaments_router)

    # In-process database startup/shutdown hooks.
    # TestClient and other in-process runners create pools on the same event loop.
    @fastapi_app.on_event("startup")  # type: ignore[reportDeprecated]
    async def _init_db_event() -> None:  # type: ignore[reportUnusedFunction]
        # Initialise engine/sessionmaker (sync function)
        import contextlib

        with contextlib.suppress(Exception):
            # Engine is already initialized in the database module
            pass

    @fastapi_app.on_event("shutdown")  # type: ignore[reportDeprecated]
    async def _shutdown_db_event() -> None:  # type: ignore[reportUnusedFunction]
        # Best-effort engine disposal
        import contextlib

        with contextlib.suppress(Exception):
            # Dispose the engine if needed
            await db.engine.dispose()

    # Honor both settings.IN_MEMORY_DB and CRICKSY_IN_MEMORY_DB=1
    use_in_memory = bool(getattr(settings, "IN_MEMORY_DB", False)) or (
        os.getenv("CRICKSY_IN_MEMORY_DB") == "1"
    )

    if use_in_memory:

        async def _in_memory_get_db() -> AsyncGenerator[_FakeSession, None]:
            yield _FakeSession()

        fastapi_app.dependency_overrides[db_get_db] = _in_memory_get_db  # type: ignore[index]
        with suppress(Exception):
            fastapi_app.dependency_overrides[gameplay_get_db] = _in_memory_get_db  # type: ignore[index]
        # Debugging: indicate in-memory wiring status
        try:
            print("DEBUG: create_app detected in-memory mode")
            print("DEBUG: enable_in_memory_crud_fn is", bool(enable_in_memory_crud_fn))
            print("DEBUG: InMemoryCrudRepoClass is", bool(InMemoryCrudRepoClass))
        except Exception:
            pass
        if enable_in_memory_crud_fn is not None and InMemoryCrudRepoClass is not None:
            global _memory_repo
            if _memory_repo is None:
                _memory_repo = InMemoryCrudRepoClass()  # type: ignore[operator]
            enable_in_memory_crud_fn(_memory_repo)  # type: ignore[call-arg]

    asgi_app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
    return asgi_app, fastapi_app
