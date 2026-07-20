"""Low-level HTTP client for NVIDIA NIM API (OpenAI-compatible)."""

from __future__ import annotations

import json
from typing import Any, AsyncGenerator, Dict, Optional

import httpx
from loguru import logger

from nim_gateway.core.config import NIMProviderConfig
from nim_gateway.gateway.circuit_breaker import CircuitBreaker, CircuitBreakerOpen


class NIMClient:
    """Stateless HTTP client for a single NIM provider endpoint."""

    def __init__(
        self,
        config: NIMProviderConfig,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ) -> None:
        self._config = config
        self._cb = circuit_breaker or CircuitBreaker(name=config.name)

        # Reusable transport with connection pooling
        self._client = httpx.AsyncClient(
            base_url=config.base_url.rstrip("/"),
            timeout=config.timeout,
            limits=httpx.Limits(
                max_keepalive_connections=20,
                max_connections=100,
            ),
        )

    # ── Public properties ──────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def base_url(self) -> str:
        return self._config.base_url

    @property
    def weight(self) -> int:
        return self._config.weight or 1

    @property
    def circuit_breaker(self) -> CircuitBreaker:
        return self._cb

    @property
    def enabled(self) -> bool:
        return self._config.enabled

    # ── Request methods ────────────────────────────────────────────────

    async def request(
        self,
        endpoint_type: str,
        payload: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Send a non-streaming request through the circuit breaker.

        *endpoint_type* is one of: chat/completions, completions, embeddings.
        """
        return await self._cb.call(
            self._do_request,
            endpoint_type,
            payload,
            stream=False,
        )

    async def stream(
        self,
        endpoint_type: str,
        payload: Dict[str, Any],
    ) -> AsyncGenerator[bytes, None]:
        """Send a streaming request through the circuit breaker."""
        # We cannot wrap an async generator in _cb.call easily, so we
        # check the circuit breaker state manually before starting.
        if self._cb.state.name == "OPEN":
            raise CircuitBreakerOpen(self.name)

        try:
            async for chunk in self._do_stream(endpoint_type, payload):
                yield chunk
        except Exception:
            self._cb._record_failure()
            raise

        self._cb._record_success()

    # ── Internal ───────────────────────────────────────────────────────

    async def _do_request(
        self,
        endpoint_type: str,
        payload: Dict[str, Any],
        stream: bool = False,
    ) -> Dict[str, Any]:
        url = self._build_url(endpoint_type)
        headers = self._build_headers()

        body = {**payload}
        if stream:
            body["stream"] = True

        logger.debug("NIM request [{}] {} ({} tokens?)", self.name, url, len(str(body)))

        response = await self._client.post(url, json=body, headers=headers)
        response.raise_for_status()
        return response.json()

    async def _do_stream(
        self,
        endpoint_type: str,
        payload: Dict[str, Any],
    ) -> AsyncGenerator[bytes, None]:
        url = self._build_url(endpoint_type)
        headers = self._build_headers()
        body = {**payload, "stream": True}

        async with self._client.stream("POST", url, json=body, headers=headers) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk

    def _build_url(self, endpoint_type: str) -> str:
        return f"/v1/{endpoint_type}"

    def _build_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {self._config.api_key}"
        return headers

    async def health(self) -> bool:
        """Quick health check — GET /v1/health or /health."""
        try:
            for path in ("/v1/health", "/health", "/v1/models"):
                resp = await self._client.get(path, timeout=5.0)
                if resp.status_code < 500:
                    return True
        except Exception:
            pass
        return False

    async def close(self) -> None:
        await self._client.aclose()


async def create_client(config: NIMProviderConfig) -> NIMClient:
    """Factory helper."""
    return NIMClient(config)
