from __future__ import annotations

from typing import Any, cast
from collections.abc import AsyncGenerator
from pathlib import Path
import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import socketio  # type: ignore[import-not-found]

from backend.config import settings as default_settings
from contextlib import suppress

# Routers
from backend.routes.games_router import router as games_router
from backend.routes.gameplay import router as gameplay_router, get_db as gameplay_get_db  # type: ignore[attr-defined]
from backend.routes.games_dls import router as games_dls_router
from backend.routes.dls import router as dls_router
from backend.routes.game_admin import router as game_admin_router
from backend.routes.interruptions import router as interruptions_router
from backend.routes.health import router as health_router
from backend.routes.sponsors import router as sponsors_router
from backend.routes.games_core import router as games_core_router  # NEW

# DB dependency and in-memory wiring
from sqlalchemy.ext.asyncio import AsyncSession
from backend.sql_app.database import get_db as db_get_db, SessionLocal  # type: ignore[unused-ignore]

# Socket handlers and live bus
from backend.socket_handlers import register_sio
from backend.services.live_bus import set_socketio_server as _set_bus_sio

# Observability and error handling (install on FastAPI app, not ASGI wrapper)
from backend.middleware.observability import (
    CorrelationIdMiddleware,
    AccessLogMiddleware,
)  # NEW
from backend.error_handlers import install_exception_handlers  # NEW

# Optional in-memory CRUD support
InMemoryCrudRepository: Any | None
enable_in_memory_crud_fn: Any | None
try:
    from backend.testsupport.in_memory_crud import (
        InMemoryCrudRepository as _IMRepo,
        enable_in_memory_crud as _enable_fn,
    )

    InMemoryCrudRepository = _IMRepo
    enable_in_memory_crud_fn = _enable_fn
except Exception:
    InMemoryCrudRepository = None
    enable_in_memory_crud_fn = None


# Minimal no-op async session & result for in-memory mode safety
class _FakeResult:
    def scalars(self) -> _FakeResult:
        return self

    def all(self) -> list[Any]:
        return []

    def first(self) -> Any | None:
        return None

    def scalar_one_or_none(self) -> Any | None:
        return None


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
        return _FakeResult()


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
    sio = cast("socketio.AsyncServer", _sio)
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

    # Standard DB dependency
    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        async with SessionLocal() as session:  # type: ignore[misc]
            yield session

    # Honor both settings.IN_MEMORY_DB and CRICKSY_IN_MEMORY_DB=1
    use_in_memory = bool(getattr(settings, "IN_MEMORY_DB", False)) or (
        os.getenv("CRICKSY_IN_MEMORY_DB") == "1"
    )

    if use_in_memory:

        async def _in_memory_get_db() -> AsyncGenerator[object, None]:
            yield _FakeSession()

        fastapi_app.dependency_overrides[db_get_db] = _in_memory_get_db  # type: ignore[index]
        with suppress(Exception):
            fastapi_app.dependency_overrides[gameplay_get_db] = _in_memory_get_db  # type: ignore[index]
        if enable_in_memory_crud_fn is not None and InMemoryCrudRepository is not None:
            _memory_repo = InMemoryCrudRepository()  # type: ignore[operator]
            enable_in_memory_crud_fn(_memory_repo)  # type: ignore[call-arg]

    asgi_app = socketio.ASGIApp(sio, other_asgi_app=fastapi_app)
    return asgi_app, fastapi_app
