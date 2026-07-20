"""Model fallback chain — try providers in order, skip failing ones."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

from loguru import logger

from nim_gateway.gateway.circuit_breaker import CircuitBreakerOpen
from nim_gateway.provider.nvidia_nim import NIMClient


class FallbackChain:
    """Execute a request across a chain of providers with fallback.

    On failure (network error, 5xx, circuit open) the chain moves to the
    next available provider.
    """

    def __init__(self, providers: List[NIMClient]) -> None:
        if not providers:
            raise ValueError("FallbackChain requires at least one provider.")
        self._providers = providers

    async def execute(
        self,
        endpoint_type: str,
        payload: Dict[str, Any],
        stream: bool = False,
    ) -> Union[Dict[str, Any], AsyncGenerator[bytes, None]]:
        """Try each provider in order until one succeeds.

        Returns the response dict or an async generator for streaming.
        """
        last_error: Exception | None = None

        for idx, client in enumerate(self._providers):
            provider_name = client.name
            try:
                if stream:
                    return self._stream_with_fallback(client, endpoint_type, payload)
                return await client.request(endpoint_type, payload)
            except CircuitBreakerOpen:
                logger.warning(
                    "Fallback: circuit open for {!r}, trying next provider",
                    provider_name,
                )
                last_error = CircuitBreakerOpen(provider_name)
                continue
            except Exception as exc:
                logger.error(
                    "Fallback: provider {!r} failed: {}",
                    provider_name,
                    exc,
                )
                last_error = exc
                continue

        # All providers exhausted
        logger.error(
            "All {} providers failed for endpoint {!r}. Last error: {}",
            len(self._providers),
            endpoint_type,
            last_error,
        )
        raise FallbackExhausted(
            f"All {len(self._providers)} providers exhausted. "
            f"Last error: {last_error}"
        ) from last_error

    async def _stream_with_fallback(
        self,
        client: NIMClient,
        endpoint_type: str,
        payload: Dict[str, Any],
    ) -> AsyncGenerator[bytes, None]:
        """Stream from a single provider (fallback on failure during streaming)."""
        try:
            async for chunk in client.stream(endpoint_type, payload):
                yield chunk
        except Exception as exc:
            logger.error("Stream error on {!r}: {}", client.name, exc)
            # For streaming we raise immediately — the client can retry
            raise

    @property
    def providers(self) -> List[NIMClient]:
        return list(self._providers)

    def __len__(self) -> int:
        return len(self._providers)


class FallbackExhausted(Exception):
    """All providers in the fallback chain failed."""
