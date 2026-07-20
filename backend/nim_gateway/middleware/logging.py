"""Request/response logging middleware with structured output."""

from __future__ import annotations

import time
import uuid

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


class LoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, duration, and request ID."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        method = request.method
        path = request.url.path
        query = str(request.url.query) if request.url.query else ""
        full_path = f"{path}?{query}" if query else path

        start = time.monotonic()

        logger.info("[{}] → {} {}", request_id, method, full_path)

        response = await call_next(request)

        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "[{}] ← {} {} ({}ms)",
            request_id,
            response.status_code,
            full_path,
            f"{duration_ms:.1f}",
        )

        response.headers["X-Request-ID"] = request_id
        return response
