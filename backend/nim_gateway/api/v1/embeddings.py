"""Embeddings API — ``/v1/embeddings`` (OpenAI-compatible)."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import BaseModel

from nim_gateway.gateway.router import ModelNotFoundError, gateway_router
from nim_gateway.core.config import settings

router = APIRouter(prefix="/v1", tags=["Embeddings"])

# Deterministic mock embedding dimension (compatible with common NIM models)
_MOCK_EMBED_DIM = 1024


def _mock_embeddings(body: EmbeddingRequest) -> dict:
    """Canned embeddings used when NIM_GW_MOCK_MODE=1 (no upstream call)."""
    inputs = body.input if isinstance(body.input, list) else [body.input]
    data = []
    for i, item in enumerate(inputs):
        # Deterministic pseudo-embedding from input hash
        seed = abs(hash(str(item))) % 1000
        vec = [float((seed + j) % 100) / 100.0 for j in range(_MOCK_EMBED_DIM)]
        data.append({"object": "embedding", "index": i, "embedding": vec})
    return {
        "object": "list",
        "data": data,
        "model": body.model,
        "usage": {"prompt_tokens": sum(len(str(x).split()) for x in inputs), "total_tokens": 0},
    }


class EmbeddingRequest(BaseModel):
    model: str
    input: str | List[str] | List[int] | List[List[int]]
    encoding_format: Optional[str] = "float"  # float or base64
    user: Optional[str] = None


@router.post("/embeddings")
async def embeddings(
    request: Request,
    body: EmbeddingRequest,
):
    """OpenAI-compatible Embeddings endpoint."""
    if settings.mock_mode:
        return _mock_embeddings(body)

    payload = body.model_dump(exclude_none=True)

    try:
        result = await gateway_router.route(
            model=body.model,
            endpoint_type="embeddings",
            payload=payload,
            stream=False,
        )
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Embeddings failed: {}", exc)
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    return result
