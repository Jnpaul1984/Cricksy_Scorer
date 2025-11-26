#!/usr/bin/env python
"""Run the FastAPI backend in in-memory mode for local CI/Cypress runs."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"

# Ensure both the project root and backend package are importable.
for path in (ROOT, BACKEND_DIR):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

# Force the backend to run with the light-weight in-memory CRUD layer.
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

import backend.main as backend_main  # type: ignore  # noqa: E402


def main() -> None:
    patch_module = getattr(backend_main.crud.create_game, "__module__", "")
    print(f"[run_backend_in_memory] using CRUD module: {patch_module}", flush=True)
    config = uvicorn.Config(
        "backend.main:app",
        host=os.getenv("BACKEND_HOST", "127.0.0.1"),
        port=int(os.getenv("BACKEND_PORT", "8000")),
        log_level=os.getenv("UVICORN_LOG_LEVEL", "warning"),
    )
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
