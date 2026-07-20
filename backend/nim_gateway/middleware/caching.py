"""In-memory response caching middleware (TTL-based).

For production, swap with Redis-backed cache (see docker-compose.yml).
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, Optional, Tuple

from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import StreamingResponse
from starlette.types import ASGIApp

from nim_gateway.core.config import settings


class MemoryCache:
    """Simple TTL-based in-memory cache (dict)."""

    def __init__(self, ttl: int = 300, max_size: int = 512) -> None:
        self._ttl = ttl
        self._max_size = max_size
        self._store: Dict[str, Tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any) -> None:
        if len(self._store) >= self._max_size:
            try:
                oldest = min(self._store, key=lambda k: self._store[k][0])
                del self._store[oldest]
            except ValueError:
                pass
        self._store[key] = (time.monotonic() + self._ttl, value)

    def invalidate(self, pattern: Optional[str] = None) -> int:
        if pattern is None:
            count = len(self._store)
            self._store.clear()
            return count
        keys = [k for k in self._store if k.startswith(pattern)]
        for k in keys:
            del self._store[k]
        return len(keys)


# Global cache instance
_cache = MemoryCache(
    ttl=settings.gateway.cache_ttl_seconds,
    max_size=settings.gateway.cache_max_size,
)


async def _extract_model_name(request: Request) -> str:
    """Extract the model name from the request body, if present."""
    try:
        body = await request.body()
        payload = json.loads(body)
        return payload.get("model", "") or ""
    except (json.JSONDecodeError, TypeError, RuntimeError):
        return ""


def _build_cache_key(method: str, path: str, query: str, model: str) -> str:
    raw = f"{method}:{path}:{query}:{model}"
    return hashlib.sha256(raw.encode()).hexdigest()


class CachingMiddleware(BaseHTTPMiddleware):
    """Cache non-streaming POST responses for configured TTL."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if not settings.gateway.cache_enabled:
            return await call_next(request)

        # Only cache POST requests
        if request.method != "POST":
            return await call_next(request)

        # Only cache known endpoints
        if not any(p in request.url.path for p in ("/v1/chat/completions", "/v1/completions", "/v1/embeddings")):
            return await call_next(request)

        model = await _extract_model_name(request)
        if not model:
            return await call_next(request)

        # Don't cache streaming requests
        try:
            body = await request.body()
            payload = json.loads(body)
            if payload.get("stream", False):
                return await call_next(request)
        except (json.JSONDecodeError, TypeError, RuntimeError):
            pass

        key = _build_cache_key(
            request.method,
            request.url.path,
            str(request.url.query),
            model,
        )

        cached = _cache.get(key)
        if cached is not None:
            logger.debug("Cache HIT: model={} path={}", model, request.url.path)
            from starlette.responses import JSONResponse
            return JSONResponse(content=cached)

        response = await call_next(request)

        # Streaming responses have no inspectable body — never cache them
        if isinstance(response, StreamingResponse):
            return response

        if 200 <= response.status_code < 300:
            try:
                _cache.set(key, json.loads(response.body))
            except (json.JSONDecodeError, TypeError):
                pass

        return response
