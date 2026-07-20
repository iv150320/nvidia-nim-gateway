"""Models listing API — ``GET /v1/models`` (OpenAI-compatible)."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import BaseModel

from nim_gateway.gateway.router import gateway_router
from nim_gateway.provider.model_registry import model_registry

router = APIRouter(prefix="/v1", tags=["Models"])


class ModelPermission(BaseModel):
    id: str = "modelperm-0"
    object: str = "model_permission"
    created: int = int(time.time())
    allow_create_engine: bool = False
    allow_sampling: bool = True
    allow_logprobs: bool = True
    allow_search_indices: bool = False
    allow_view: bool = True
    allow_fine_tuning: bool = False
    organization: str = "*"
    group: Optional[str] = None
    is_blocking: bool = False


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str = "nvidia-nim"
    permission: List[ModelPermission] = [ModelPermission()]


class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[ModelInfo]


@router.get("/models")
async def list_models(request: Request) -> ModelListResponse:
    """List all available models with their metadata."""
    models = gateway_router.list_models()

    data: List[ModelInfo] = []
    for model_name, providers in models.items():
        data.append(
            ModelInfo(
                id=model_name,
                created=int(time.time()),
                owned_by="nvidia-nim",
            )
        )

    # Also include raw provider names for direct access
    for provider_name in model_registry.list_providers():
        if not any(m.id == provider_name for m in data):
            data.append(
                ModelInfo(
                    id=provider_name,
                    created=int(time.time()),
                    owned_by="nvidia-nim",
                )
            )

    return ModelListResponse(data=data)
