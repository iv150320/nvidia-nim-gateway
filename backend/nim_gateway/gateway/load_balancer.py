"""Weighted round-robin load balancer for equivalent NIM providers."""

from __future__ import annotations

import itertools
import random
from typing import Dict, List, Optional

from nim_gateway.provider.nvidia_nim import NIMClient


class LoadBalancer:
    """Distributes requests across providers of the **same** model group.

    Providers with higher *weight* receive proportionally more traffic.
    """

    def __init__(self, clients: List[NIMClient]) -> None:
        if not clients:
            raise ValueError("LoadBalancer requires at least one provider client.")

        self._clients = clients

        # Build weighted rotation
        weights = [max(1, c.weight) for c in clients]
        pool: list[NIMClient] = []
        for client, w in zip(clients, weights):
            pool.extend([client] * w)
        random.shuffle(pool)
        self._pool = pool
        self._iterator = itertools.cycle(pool)

    @property
    def clients(self) -> List[NIMClient]:
        return list(self._clients)

    def next(self) -> NIMClient:
        """Return the next provider client (round-robin with weights)."""
        return next(self._iterator)

    def available_clients(self) -> List[NIMClient]:
        """Return clients whose circuit breaker is not OPEN."""
        return [c for c in self._clients if c.circuit_breaker.state.name != "OPEN"]

    def __len__(self) -> int:
        return len(self._clients)

    def __repr__(self) -> str:
        return f"LoadBalancer({[c.name for c in self._clients]})"
