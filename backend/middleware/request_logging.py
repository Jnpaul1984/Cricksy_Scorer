"""
Request logging middleware for FastAPI (read-only, no secrets/tokens stored)
"""
import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from backend.sql_app.database import get_db_session
from backend.sql_app import models
import os

LOG_REQUESTS = os.getenv("CRICKSY_REQUEST_LOGGING", "1") == "1"

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not LOG_REQUESTS:
            return await call_next(request)
        start = time.time()
        response = await call_next(request)
        try:
            # Only log after response
            db = get_db_session()
            # Do not log auth headers, cookies, tokens
            ip = request.client.host if request.client else None
            user_agent = request.headers.get("user-agent", "")[:200]
            user_id = getattr(request.state, "user_id", None)
            latency_ms = int((time.time() - start) * 1000)
            rl = models.RequestLog(
                ts=int(time.time()),
                method=request.method,
                path=request.url.path[:200],
                status=response.status_code,
                ip=ip,
                userAgent=user_agent,
                userId=user_id,
                latencyMs=latency_ms,
            )
            db.add(rl)
            db.commit()
        except Exception:
            pass  # Never block request
        return response
