# backend/tests/conftest.py
import asyncio
import os
import pathlib
import sys
import threading
import time
from urllib.parse import urlparse

import pytest
import requests
import uvicorn

# Repo root = two levels up from this file (Cricksy_Scorer/)
ROOT = pathlib.Path(__file__).resolve().parents[2]
ROOT_STR = str(ROOT)
if ROOT_STR not in sys.path:
    sys.path.insert(0, ROOT_STR)

from backend.main import fastapi_app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _ensure_live_server() -> None:
    """Spin up the FastAPI app on localhost so smoke tests can hit /health."""

    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    parsed = urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    if parsed.port:
        port = parsed.port
    elif parsed.scheme == "https":
        port = 443
    else:
        port = 8000

    config = uvicorn.Config(
        fastapi_app,
        host=host,
        port=port,
        log_level=os.getenv("UVICORN_TEST_LOG_LEVEL", "warning"),
        lifespan="on",
    )
    server = uvicorn.Server(config)

    def _run_server() -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())

    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()

    health_url = f"{parsed.scheme or 'http'}://{host}:{port}/health"
    for _ in range(50):
        try:
            response = requests.get(health_url, timeout=0.5)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(0.2)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("Timed out waiting for FastAPI test server to start")

    try:
        yield
    finally:
        server.should_exit = True
        thread.join(timeout=5)
