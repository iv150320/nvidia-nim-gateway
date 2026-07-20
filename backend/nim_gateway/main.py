"""NVIDIA NIM Gateway — FastAPI application entry point.

Usage:
    uvicorn nim_gateway.main:app --reload
    # or
    python -m nim_gateway.main
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is on sys.path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from nim_gateway.api.v1 import chat, completions, embeddings, health, models
from nim_gateway.core.config import settings
from nim_gateway.middleware.auth import AuthMiddleware
from nim_gateway.middleware.caching import CachingMiddleware
from nim_gateway.middleware.logging import LoggingMiddleware
from nim_gateway.middleware.metrics import MetricsMiddleware
from nim_gateway.monitoring import otel, prometheus
from nim_gateway.provider.health_check import health_checker
from nim_gateway.provider.model_registry import model_registry


# ── Lifespan ───────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup / shutdown lifecycle."""
    # ── Startup ──────────────────────────────────────────────────────
    logger.info("═══ NVIDIA NIM Gateway v0.1.0 ═══")

    # Load model registry
    model_registry.load()
    logger.info("Models loaded: {}", list(model_registry.list_models().keys()))

    # Start health checker
    await health_checker.start()

    # Initialise OpenTelemetry
    otel.init()

    yield

    # ── Shutdown ─────────────────────────────────────────────────────
    await health_checker.stop()
    logger.info("Gateway shut down.")


# ── Application ────────────────────────────────────────────────────────

app = FastAPI(
    title="Universal NVIDIA NIM Gateway",
    description="Unified OpenAI-compatible gateway for NVIDIA NIM inference endpoints.",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── CORS ───────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Internal middleware (order matters) ─────────────────────────────────
# 1. Logging — first to capture everything
app.add_middleware(LoggingMiddleware)
# 2. Auth — validate API keys
app.add_middleware(AuthMiddleware)
# 3. Metrics — track request counts / durations
app.add_middleware(MetricsMiddleware)
# 4. Caching — cache non-streaming responses
app.add_middleware(CachingMiddleware)


# ── Routers ────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(models.router)
app.include_router(chat.router)
app.include_router(completions.router)
app.include_router(embeddings.router)


# ── Prometheus metrics ─────────────────────────────────────────────────

@app.get("/metrics", include_in_schema=False)
async def metrics(request: Request):
    return await prometheus.metrics_endpoint(request)


# ── Root ───────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "service": "NVIDIA NIM Gateway",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/health",
    }


# ── Error handlers ─────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on {} {}: {}", request.method, request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── CLI entry point ────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "nim_gateway.main:app",
        host=settings.gateway.host,
        port=settings.gateway.port,
        log_level=settings.gateway.log_level.lower(),
        reload=settings.gateway.reload,
    )
