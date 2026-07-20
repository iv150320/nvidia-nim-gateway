"""Authentication middleware — validates API key on every request (opt-in paths)."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from nim_gateway.core.config import settings
from nim_gateway.core.security import validate_api_key

# Paths that do NOT require authentication
PUBLIC_PATHS = {
    "/v1/health",
    "/health",
    "/",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/metrics",
}


class AuthMiddleware(BaseHTTPMiddleware):
    """Verify Bearer token on all non-public endpoints."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if not settings.gateway.api_key_enabled:
            return await call_next(request)

        path = request.url.path.rstrip("/")
        if path in PUBLIC_PATHS or path.startswith(("/docs", "/redoc", "/openapi.json")):
            return await call_next(request)

        try:
            key_label = validate_api_key(request, settings.gateway.api_keys)
            request.state.api_key_label = key_label
        except Exception as exc:
            return JSONResponse(
                status_code=401,
                content={"detail": str(exc) if hasattr(exc, "detail") else str(exc)},
            )

        return await call_next(request)
