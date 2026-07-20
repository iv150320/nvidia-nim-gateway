"""Prometheus metrics endpoint for the gateway itself.

Exposes ``/metrics`` for scraping by Prometheus.
"""

from __future__ import annotations

from prometheus_client import generate_latest, REGISTRY, CONTENT_TYPE_LATEST
from starlette.requests import Request
from starlette.responses import Response

from nim_gateway.core.config import settings


async def metrics_endpoint(request: Request) -> Response:
    """Serve Prometheus metrics."""
    if not settings.gateway.metrics_enabled:
        return Response(status_code=404, content="Metrics disabled")

    data = generate_latest(REGISTRY)
    return Response(
        content=data,
        media_type=CONTENT_TYPE_LATEST,
        headers={"Cache-Control": "no-cache"},
    )
