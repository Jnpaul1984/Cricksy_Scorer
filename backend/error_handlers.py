from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import ORJSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from starlette import status

__all__ = ["install_exception_handlers"]

_log = structlog.get_logger("errors")


def _req_id(request: Request) -> str | None:
    # Set by CorrelationIdMiddleware
    return getattr(request.state, "correlation_id", None)


def _json_error(
    request: Request,
    *,
    err_type: str,
    message: str,
    details: Any | None,
    status_code: int,
) -> ORJSONResponse:
    payload: dict[str, Any] = {
        "request_id": _req_id(request),
        "error": {
            "type": err_type,
            "message": message,
        },
    }
    if details is not None:
        payload["error"]["details"] = details  # type: ignore[index]

    return ORJSONResponse(payload, status_code=status_code)


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(  # type: ignore[reportUnusedFunction]
        request: Request, exc: RequestValidationError
    ) -> ORJSONResponse:
        # FastAPI validation (request body/query/path/etc.)
        _log.warning(
            "validation_error",
            path=str(request.url.path),
            method=request.method,
            request_id=_req_id(request),
            errors=exc.errors(),
        )
        return _json_error(
            request,
            err_type="validation_error",
            message="Invalid request.",
            details=exc.errors(),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(ValidationError)
    async def handle_pydantic_validation_error(  # type: ignore[reportUnusedFunction]
        request: Request, exc: ValidationError
    ) -> ORJSONResponse:
        # Pydantic model validation inside handlers/services
        try:
            details = exc.errors()  # pydantic v2
        except Exception:
            details = str(exc)
        _log.warning(
            "pydantic_validation_error",
            path=str(request.url.path),
            method=request.method,
            request_id=_req_id(request),
            errors=details,
        )
        return _json_error(
            request,
            err_type="validation_error",
            message="Invalid data.",
            details=details,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )

    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> ORJSONResponse:  # type: ignore[reportUnusedFunction]
        # Constraint violations, duplicates, FK errors, etc.
        # Keep response stable; log full exception for operators.
        _log.warning(
            "integrity_error",
            path=str(request.url.path),
            method=request.method,
            request_id=_req_id(request),
            error=str(getattr(exc, "orig", exc)),
        )
        # Optional hint extraction (best-effort)
        detail: Any | None = None
        try:
            orig = getattr(exc, "orig", None)
            # Some DBAPIs expose .diag or .detail; asyncpg exposes str()
            if orig is not None:
                detail = str(orig)
        except Exception:
            detail = None

        return _json_error(
            request,
            err_type="integrity_error",
            message="Request conflicts with existing data.",
            details=detail,
            status_code=status.HTTP_409_CONFLICT,
        )

    @app.exception_handler(Exception)
    async def handle_generic_error(request: Request, exc: Exception) -> ORJSONResponse:  # type: ignore[reportUnusedFunction]
        # Last-resort safety net
        _log.exception(
            "unhandled_exception",
            path=str(request.url.path),
            method=request.method,
            request_id=_req_id(request),
        )
        return _json_error(
            request,
            err_type="server_error",
            message="Internal server error.",
            details=None,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
