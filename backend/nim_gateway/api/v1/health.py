"""Health check endpoint — ``GET /v1/health`` and ``GET /health``."""

from __future__ import annotations

import time
from typing import Dict, List

from fastapi import APIRouter
from loguru import logger

from nim_gateway.provider.health_check import health_checker
from nim_gateway.provider.model_registry import model_registry

router = APIRouter(tags=["Health"])


@router.get("/health")
@router.get("/v1/health")
async def health() -> Dict:
    """Health check — returns overall gateway status and per-provider health."""
    provider_statuses = health_checker.statuses or await _check_providers()

    all_healthy = all(provider_statuses.values()) if provider_statuses else True

    status = {
        "status": "healthy" if all_healthy else "degraded",
        "version": "0.1.0",
        "timestamp": time.time(),
        "providers": {
            name: "up" if ok else "down"
            for name, ok in provider_statuses.items()
        },
        "models_available": len(model_registry.list_models()),
        "providers_count": len(provider_statuses),
    }

    return status


async def _check_providers() -> Dict[str, bool]:
    """Run an immediate health check on all providers."""
    return await health_checker.check_all()
