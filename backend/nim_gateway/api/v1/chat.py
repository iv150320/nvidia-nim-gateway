"""Chat Completions API — OpenAI-compatible ``/v1/chat/completions``."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel, Field

from nim_gateway.gateway.router import ModelNotFoundError, gateway_router
from nim_gateway.middleware.caching import MemoryCache

router = APIRouter(prefix="/v1", tags=["Chat Completions"])


# ── Request / Response schemas ─────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # system, user, assistant, tool
    content: str | List[Dict[str, Any]] | None = None
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    n: Optional[int] = None
    stream: Optional[bool] = False
    stop: Optional[List[str] | str] = None
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    logit_bias: Optional[Dict[str, float]] = None
    user: Optional[str] = None
    seed: Optional[int] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[str | Dict[str, Any]] = None


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"
    logprobs: Optional[Any] = None


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo


# ── Endpoint ───────────────────────────────────────────────────────────

@router.post("/chat/completions")
async def chat_completions(
    request: Request,
    body: ChatCompletionRequest,
):
    """OpenAI-compatible Chat Completions endpoint.

    Routes to the appropriate NVIDIA NIM provider based on the requested
    model name.
    """
    payload = body.model_dump(exclude_none=True)
    payload.pop("stream", None)

    if body.stream:
        return StreamingResponse(
            _stream_chat(body.model, payload),
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
            endpoint_type="chat/completions",
            payload=payload,
            stream=False,
        )
    except ModelNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        logger.error("Chat completion failed: {}", exc)
        raise HTTPException(status_code=502, detail=f"Upstream error: {exc}")

    return result


async def _stream_chat(
    model: str,
    payload: Dict[str, Any],
) -> AsyncGenerator[bytes, None]:
    """Stream chat completions as SSE events."""
    try:
        async for chunk in await gateway_router.route(
            model=model,
            endpoint_type="chat/completions",
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
