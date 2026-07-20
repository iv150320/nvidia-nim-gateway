"""Model registry — maps model names to provider chains.

Loaded from ``config/models.yaml`` at startup.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from loguru import logger

from nim_gateway.core.config import NIMProviderConfig, settings
from nim_gateway.gateway.circuit_breaker import CircuitBreaker
from nim_gateway.gateway.load_balancer import LoadBalancer
from nim_gateway.provider.nvidia_nim import NIMClient


class ModelRegistry:
    """Central registry of models and their backing providers."""

    def __init__(self) -> None:
        self._providers: Dict[str, NIMProviderConfig] = {}
        self._clients: Dict[str, NIMClient] = {}
        self._routes: Dict[str, LoadBalancer] = {}
        self._default_provider: Optional[NIMProviderConfig] = None

    # ── Lifecycle ──────────────────────────────────────────────────────

    def load(self) -> None:
        """Load providers and routes from settings (models.yaml)."""
        models_cfg = settings.models

        # 1. Build provider configs
        self._providers = dict(models_cfg.providers)

        # 2. Build NIMClient instances per provider
        for provider_name, pcfg in self._providers.items():
            cb = CircuitBreaker(
                name=provider_name,
                failure_threshold=settings.gateway.circuit_breaker_failure_threshold,
                recovery_timeout=settings.gateway.circuit_breaker_recovery_timeout,
                half_open_max_calls=settings.gateway.circuit_breaker_half_open_max_calls,
            )
            self._clients[provider_name] = NIMClient(pcfg, circuit_breaker=cb)

        # 3. Build route → LoadBalancer mappings
        for model_name, route in models_cfg.routes.items():
            clients = []
            for provider_name in route.providers:
                client = self._clients.get(provider_name)
                if client:
                    clients.append(client)
                else:
                    logger.warning(
                        "Route {!r} references unknown provider {!r}",
                        model_name,
                        provider_name,
                    )

            if not clients:
                logger.warning("Route {!r} has no valid providers; skipping", model_name)
                continue

            if len(clients) == 1:
                # Single provider — wrap in single-element LoadBalancer
                self._routes[model_name] = LoadBalancer(clients)
            else:
                # Multiple equivalent providers — load balance across them
                self._routes[model_name] = LoadBalancer(clients)

        # 4. Pick a default
        if self._providers:
            first_name = next(iter(self._providers))
            self._default_provider = self._providers[first_name]

        logger.info(
            "Registry loaded: {} providers, {} routes",
            len(self._providers),
            len(self._routes),
        )

    # ── Lookups ────────────────────────────────────────────────────────

    def get_route(self, model: str) -> Optional[LoadBalancer]:
        """Return the load balancer for a public model name."""
        return self._routes.get(model)

    def get_provider(self, name: str) -> Optional[NIMProviderConfig]:
        """Return provider config by name."""
        return self._providers.get(name)

    def get_clients_for_provider(self, provider_name: str) -> List[NIMClient]:
        """Return NIMClient(s) for a provider name."""
        client = self._clients.get(provider_name)
        return [client] if client else []

    @property
    def default_provider(self) -> Optional[NIMProviderConfig]:
        return self._default_provider

    def list_models(self) -> Dict[str, List[str]]:
        """Return {model_name: [provider_names]} for all registered routes."""
        result: Dict[str, List[str]] = {}
        for model_name, lb in self._routes.items():
            result[model_name] = [c.name for c in lb.clients]
        return result

    def list_providers(self) -> Dict[str, NIMProviderConfig]:
        """Return all configured providers."""
        return dict(self._providers)


# Singleton
model_registry = ModelRegistry()
