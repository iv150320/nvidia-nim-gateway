"""OpenTelemetry instrumentation setup.

Export traces and metrics to any OTLP-compatible backend (Jaeger, Grafana
Tempo, SigNoz, etc.).  In the Enterprise AI Platform, the destination is
the AI Observability Platform on port 4318.
"""

from __future__ import annotations

from typing import Optional

from loguru import logger
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader, MetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from nim_gateway.core.config import settings


def _build_resource() -> Resource:
    return Resource.create(
        attributes={
            "service.name": settings.gateway.service_name,
            "service.version": "0.1.0",
            "deployment.environment": "production",
        }
    )


def setup_otel_traces(endpoint: str) -> Optional[trace.Tracer]:
    """Initialise the OTLP trace exporter and return a tracer."""
    resource = _build_resource()
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=endpoint)
    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer(settings.gateway.service_name)
    logger.info("OTel trace exporter initialised → {}", endpoint)
    return tracer


def setup_otel_metrics(endpoint: str) -> None:
    """Initialise the OTLP metric exporter (delta/pre-aggregated)."""
    resource = _build_resource()
    exporter: MetricExporter = OTLPMetricExporter(endpoint=endpoint)
    reader = PeriodicExportingMetricReader(exporter, export_interval_millis=10_000)
    provider = MeterProvider(resource=resource, metric_readers=[reader])
    metrics.set_meter_provider(provider)
    logger.info("OTel metric exporter initialised → {}", endpoint)


def setup_otel() -> Optional[trace.Tracer]:
    """Initialise OpenTelemetry if an OTLP endpoint is configured.

    Returns a tracer instance (or None if disabled).
    """
    endpoint = settings.gateway.otlp_endpoint
    if not endpoint:
        logger.info("OpenTelemetry disabled (no OTLP endpoint configured)")
        return None

    # Traces
    tracer = setup_otel_traces(endpoint)

    # Metrics (same endpoint, different path inferred by the exporter)
    metrics_endpoint = endpoint.replace("/v1/traces", "/v1/metrics")
    setup_otel_metrics(metrics_endpoint)

    logger.info("OpenTelemetry fully initialised, exporting to {}", endpoint)
    return tracer


# Tracer instance (lazy-initialised)
_tracer: Optional[trace.Tracer] = None


def get_tracer() -> Optional[trace.Tracer]:
    return _tracer


def init() -> None:
    global _tracer
    _tracer = setup_otel()
