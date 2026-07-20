"""Prometheus metrics + OpenTelemetry tracing middleware.

Tracks request counts, duration, and creates distributed spans exported
via OTLP to the AI Observability Platform.
"""

from __future__ import annotations

import time

from fastapi import Request
from opentelemetry import trace
from opentelemetry.trace import SpanKind, Status, StatusCode
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from nim_gateway.core.config import settings
from nim_gateway.monitoring.otel import get_tracer

# ── Prometheus metrics ─────────────────────────────────────────────────

HTTP_REQUESTS_TOTAL = Counter(
    "nim_gw_http_requests_total",
    "Total HTTP requests",
    labelnames=["method", "endpoint", "status", "service_name"],
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
    """Record Prometheus metrics and OpenTelemetry spans for every request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        if not settings.gateway.metrics_enabled:
            return await call_next(request)

        method = request.method
        endpoint = request.url.path
        # Extract identifying headers from downstream services
        service_name = request.headers.get("X-Service-Name", "unknown")
        user_id = request.headers.get("X-User-Id", "")
        # Extract model from query params or request body (best-effort)
        model = ""

        start = time.monotonic()

        # ── OpenTelemetry span ──────────────────────────────────────
        tracer = get_tracer()
        span = None
        if tracer:
            span = tracer.start_span(
                name=f"{method} {endpoint}",
                kind=SpanKind.SERVER,
                attributes={
                    "http.method": method,
                    "http.route": endpoint,
                    "service_name": service_name,
                    "user_id": user_id,
                    "model": model,
                },
            )

        try:
            response = await call_next(request)
            duration_ms = (time.monotonic() - start) * 1000

            # Update span with response info
            if span:
                span.set_attribute("http.status_code", response.status_code)
                span.set_attribute("duration_ms", duration_ms)
                span.set_status(Status(StatusCode.OK if response.status_code < 500 else StatusCode.ERROR))

            # Prometheus metrics (with service_name label)
            HTTP_REQUESTS_TOTAL.labels(
                method=method, endpoint=endpoint,
                status=response.status_code, service_name=service_name,
            ).inc()
            HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(
                duration_ms / 1000.0
            )

            return response

        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            if span:
                span.set_attribute("http.status_code", 500)
                span.set_attribute("duration_ms", duration_ms)
                span.set_status(Status(StatusCode.ERROR, str(exc)))
                span.record_exception(exc)
            HTTP_REQUESTS_TOTAL.labels(
                method=method, endpoint=endpoint,
                status=500, service_name=service_name,
            ).inc()
            raise

        finally:
            if span:
                span.end()
