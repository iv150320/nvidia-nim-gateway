"""OpenTelemetry instrumentation setup.

Export traces and metrics to any OTLP-compatible backend (Jaeger, Grafana
Tempo, SigNoz, etc.).
"""

from __future__ import annotations

from typing import Optional

from loguru import logger
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from nim_gateway.core.config import settings


def setup_otel() -> Optional[trace.Tracer]:
    """Initialise OpenTelemetry if an OTLP endpoint is configured.

    Returns a tracer instance (or None if disabled).
    """
    endpoint = settings.gateway.otlp_endpoint
    if not endpoint:
        logger.info("OpenTelemetry disabled (no OTLP endpoint configured)")
        return None

    resource = Resource.create(
        attributes={
            "service.name": settings.gateway.service_name,
            "service.version": "0.1.0",
            "deployment.environment": "production",
        }
    )

    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(settings.gateway.service_name)

    logger.info("OpenTelemetry initialised, exporting to {}", endpoint)
    return tracer


# Tracer instance (lazy-initialised)
_tracer: Optional[trace.Tracer] = None


def get_tracer() -> Optional[trace.Tracer]:
    return _tracer


def init() -> None:
    global _tracer
    _tracer = setup_otel()
