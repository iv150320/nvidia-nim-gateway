"""Prometheus metrics middleware — track request counts, duration, errors."""

from __future__ import annotations

import time

from fastapi import Request
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from nim_gateway.core.config import settings

# ── Prometheus metrics ─────────────────────────────────────────────────

HTTP_REQUESTS_TOTAL = Counter(
    "nim_gw_http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "nim_gw_http_request_duration_seconds",
    "HTTP request duration in seconds",
    labelnames=["method", "endpoint"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
)

PROVIDER_REQUESTS_TOTAL = Counter(
    "nim_gw_provider_requests_total",
    "Total requests forwarded to upstream providers",
    labelnames=["provider", "endpoint"],
)

PROVIDER_REQUEST_DURATION = Histogram(
    "nim_gw_provider_request_duration_seconds",
    "Upstream provider request duration",
    labelnames=["provider", "endpoint"],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)

CIRCUIT_BREAKER_STATE = Counter(
    "nim_gw_circuit_breaker_state_changes_total",
    "Circuit breaker state transitions",
    labelnames=["provider", "state"],
)


class MetricsMiddleware(BaseHTTPMiddleware):
    """Record Prometheus metrics for every request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if not settings.gateway.metrics_enabled:
            return await call_next(request)

        method = request.method
        endpoint = request.url.path

        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, status=response.status_code).inc()
        HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

        return response
