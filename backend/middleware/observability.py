from __future__ import annotations

import time
import uuid
from typing import TYPE_CHECKING

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

if TYPE_CHECKING:
    from starlette.types import ASGIApp


def _client_ip(request: Request) -> str | None:
    # Prefer X-Forwarded-For (first IP), then request.client.host
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    client = request.client
    return client.host if client else None


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Binds a correlation ID to the request/response lifecycle.

    - Reads X-Request-ID if provided; otherwise generates UUIDv4.
    - Binds request_id into structlog contextvars so all logs include it.
    - Echoes X-Request-ID in the response headers.
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Request-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(self.header_name) or str(uuid.uuid4())
        request.state.correlation_id = request_id  # available to handlers
        structlog.contextvars.bind_contextvars(request_id=request_id)
        try:
            response = await call_next(request)
        finally:
            # Avoid leaking across tasks
            structlog.contextvars.unbind_contextvars("request_id")
        response.headers[self.header_name] = request_id
        return response


class AccessLogMiddleware(BaseHTTPMiddleware):
    """
    Emits a structured access log for every request/response.
    """

    def __init__(self, app: ASGIApp, logger_name: str = "access") -> None:
        super().__init__(app)
        self._logger = structlog.get_logger(logger_name)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start = time.perf_counter()
        method = request.method
        path = request.url.path
        client_ip = _client_ip(request)
        user_agent = request.headers.get("user-agent", "")

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000.0
            # request_id is already in context via CorrelationIdMiddleware
            self._logger.exception(
                "request_failed",
                method=method,
                path=path,
                status=500,
                client_ip=client_ip,
                user_agent=user_agent,
                duration_ms=round(duration_ms, 2),
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000.0
        self._logger.info(
            "request",
            method=method,
            path=path,
            status=response.status_code,
            client_ip=client_ip,
            user_agent=user_agent,
            content_length=response.headers.get("content-length"),
            duration_ms=round(duration_ms, 2),
        )
        return response
