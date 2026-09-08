from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import suppress
from functools import wraps
from time import perf_counter
from typing import Any, ParamSpec, TypeVar

import structlog

P = ParamSpec("P")
R = TypeVar("R")

logger = structlog.get_logger(__name__)


def _response_metadata(result: Any) -> dict[str, int]:
    metadata: dict[str, int] = {}
    if isinstance(result, list | tuple):
        metadata["item_count"] = len(result)
    pdf_size = getattr(result, "pdf_size_bytes", None)
    if isinstance(pdf_size, int) and pdf_size >= 0:
        metadata["payload_size_bytes"] = pdf_size
    return metadata


def _emit(
    operation: str, started_at: float, outcome: str, status_code: int, **metadata: int
) -> None:
    with suppress(Exception):
        logger.info(
            "coach_performance",
            operation=operation,
            layer="backend",
            duration_ms=round((perf_counter() - started_at) * 1000, 2),
            outcome=outcome,
            status=status_code,
            **metadata,
        )


def instrument_coach_operation(
    operation: str,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    def decorator(function: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(function)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            started_at = perf_counter()
            try:
                result = await function(*args, **kwargs)
            except Exception as exc:
                status_code = getattr(exc, "status_code", 500)
                _emit(operation, started_at, "failure", status_code)
                raise

            status_code = getattr(result, "status_code", 200)
            _emit(operation, started_at, "success", status_code, **_response_metadata(result))
            return result

        return wrapper

    return decorator
