"""Text Completions API — ``/v1/completions`` (OpenAI-compatible)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

from nim_gateway.gateway.router import ModelNotFoundError, gateway_router

router = APIRouter(prefix="/v1", tags=["Completions"])


class CompletionRequest(BaseModel):
    model: str
    prompt: str | List[str] | List[int] | List[List[int]]
    suffix: Optional[str] = None
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    stream: Optional[bool] = False
    logprobs: Optional[int] = None
    echo: Optional[bool] = False
    stop: Optional[List[str] | str] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    best_of: Optional[int] = 1
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None


@router.post("/completions")
async def completions(
    request: Request,
    body: CompletionRequest,
):
    """OpenAI-compatible Text Completions endpoint."""
    payload = body.model_dump(exclude_none=True)
    payload.pop("stream", None)

    if body.stream:
        return StreamingResponse(
            _stream_completions(body.model, payload),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    try:
        result = await gateway_router.route(
            model=body.model,
            endpoint_type="completions",
            payload=payload,
            stream=False,
        )
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Completions failed: {}", exc)
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    return result


async def _stream_completions(
    model: str,
    payload: Dict[str, Any],
):
    """Stream text completions as SSE events."""
    import json

    try:
        async for chunk in await gateway_router.route(
            model=model,
            endpoint_type="completions",
            payload=payload,
            stream=True,
        ):
            yield b"data: " + chunk + b"\n\n"
    except ModelNotFoundError as exc:
        yield b"data: " + json.dumps({"error": str(exc)}).encode() + b"\n\n"
    except Exception as exc:
        logger.error("Stream error for model={}: {}", model, exc)
        yield b"data: " + json.dumps({"error": str(exc)}).encode() + b"\n\n"
    finally:
        yield b"data: [DONE]\n\n"
