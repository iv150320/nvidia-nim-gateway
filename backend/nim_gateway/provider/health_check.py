"""Periodic health checks for upstream NIM providers."""

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from loguru import logger

from nim_gateway.provider.model_registry import model_registry
from nim_gateway.provider.nvidia_nim import NIMClient


class HealthChecker:
    """Runs periodic health checks against all registered NIM providers."""

    def __init__(self, interval_seconds: int = 30) -> None:
        self._interval = interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._statuses: Dict[str, bool] = {}

    @property
    def statuses(self) -> Dict[str, bool]:
        return dict(self._statuses)

    async def check_all(self) -> Dict[str, bool]:
        """Run a single health check pass across all providers."""
        providers = model_registry.list_providers()
        results: Dict[str, bool] = {}

        for name in providers:
            clients = model_registry.get_clients_for_provider(name)
            for client in clients:
                ok = await client.health()
                results[name] = ok
                if ok:
                    logger.debug("Health: {!r} is UP", name)
                else:
                    logger.warning("Health: {!r} is DOWN", name)

        self._statuses = results
        return results

    async def start(self) -> None:
        """Start the background health-check loop."""
        if self._task is not None:
            return

        async def loop() -> None:
            while True:
                await self.check_all()
                await asyncio.sleep(self._interval)

        self._task = asyncio.create_task(loop(), name="health-checker")
        logger.info("Health checker started (interval={}s)", self._interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None
            logger.info("Health checker stopped")


# Singleton
health_checker = HealthChecker()
