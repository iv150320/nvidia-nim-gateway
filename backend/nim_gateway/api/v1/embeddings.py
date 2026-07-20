"""Embeddings API — ``/v1/embeddings`` (OpenAI-compatible)."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException, Request
from loguru import logger
from pydantic import BaseModel

from nim_gateway.gateway.router import ModelNotFoundError, gateway_router

router = APIRouter(prefix="/v1", tags=["Embeddings"])


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
