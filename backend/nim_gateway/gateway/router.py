"""Request router — maps model names to provider(s) and delegates execution."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional, Union

from loguru import logger

from nim_gateway.core.config import settings
from nim_gateway.gateway.fallback import FallbackChain
from nim_gateway.gateway.load_balancer import LoadBalancer
from nim_gateway.provider.model_registry import model_registry
from nim_gateway.provider.nvidia_nim import NIMClient


class GatewayRouter:
    """Central router that selects the right provider chain for each request.

    Resolution order:
      1. Look up the requested model in the model registry.
      2. Build ordered list of NIMClient instances (respecting load balancers).
      3. Execute via FallbackChain.
    """

    async def route(
        self,
        *,
        model: str,
        endpoint_type: str,
        payload: Dict[str, Any],
        stream: bool = False,
    ) -> Union[Dict[str, Any], AsyncGenerator[bytes, None]]:
        """Route a request to the appropriate provider chain."""
        clients = self._resolve_clients(model)
        logger.debug("Routing model={!r} to providers={}", model, [c.name for c in clients])

        chain = FallbackChain(clients)
        return await chain.execute(endpoint_type, payload, stream=stream)

    def _resolve_clients(self, model: str) -> List[NIMClient]:
        """Get ordered list of NIMClient instances for a model.

        Falls back to a direct-match provider name if the model is not
        in the registry.
        """
        # 1. Check model registry routes
        route = model_registry.get_route(model)
        if route:
            return [
                client
                for provider_name in route.providers
                for client in model_registry.get_clients_for_provider(provider_name)
            ]

        # 2. Check if the model itself is a provider alias
        direct = model_registry.get_provider(model)
        if direct:
            return [NIMClient(direct)]

        # 3. Try default provider
        default = model_registry.default_provider
        if default:
            logger.info("Model {!r} not found; routing to default provider {!r}", model, default.name)
            return [NIMClient(default)]

        raise ModelNotFoundError(
            f"Model '{model}' is not registered and no default provider is configured. "
            f"Available models: {list(model_registry.list_models().keys())}"
        )

    def list_models(self) -> Dict[str, Any]:
        """Return all available models with their provider mapping."""
        return model_registry.list_models()


# Singleton
gateway_router = GatewayRouter()


class ModelNotFoundError(Exception):
    """Raised when the requested model is unknown."""
