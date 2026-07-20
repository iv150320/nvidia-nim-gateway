"""Tests for the weighted round-robin load balancer."""

from unittest.mock import MagicMock

import pytest

from nim_gateway.gateway.load_balancer import LoadBalancer
from nim_gateway.provider.nvidia_nim import NIMClient


@pytest.fixture
def mock_client():
    """Create a minimal mock NIMClient."""
    client = MagicMock(spec=NIMClient)
    client.name = "test-provider"
    client.weight = 1
    client.circuit_breaker.state.name = "CLOSED"
    return client


class TestLoadBalancer:
    """Load balancer tests."""

    def test_single_provider(self, mock_client):
        lb = LoadBalancer([mock_client])
        client = lb.next()
        assert client.name == "test-provider"

    def test_round_robin(self):
        clients = []
        for i in range(3):
            c = MagicMock(spec=NIMClient)
            c.name = f"provider-{i}"
            c.weight = 1
            c.circuit_breaker.state.name = "CLOSED"
            clients.append(c)

        lb = LoadBalancer(clients)
        seen = set()
        for _ in range(6):
            seen.add(lb.next().name)

        assert seen == {"provider-0", "provider-1", "provider-2"}

    def test_weighted_distribution(self):
        clients = []
        # Provider A has weight 3, provider B has weight 1
        c_a = MagicMock(spec=NIMClient)
        c_a.name = "weighted-a"
        c_a.weight = 3
        c_a.circuit_breaker.state.name = "CLOSED"

        c_b = MagicMock(spec=NIMClient)
        c_b.name = "weighted-b"
        c_b.weight = 1
        c_b.circuit_breaker.state.name = "CLOSED"

        lb = LoadBalancer([c_a, c_b])

        # Over many iterations, A should appear ~3x more than B
        counts = {"weighted-a": 0, "weighted-b": 0}
        for _ in range(400):
            client = lb.next()
            counts[client.name] += 1

        ratio = counts["weighted-a"] / counts["weighted-b"]
        assert 2.0 < ratio < 5.0, f"Expected ~3:1 ratio, got {ratio:.2f}:1"

    def test_available_clients_filters_open(self):
        c_open = MagicMock(spec=NIMClient)
        c_open.name = "open-provider"
        c_open.weight = 1
        c_open.circuit_breaker.state.name = "OPEN"

        c_closed = MagicMock(spec=NIMClient)
        c_closed.name = "closed-provider"
        c_closed.weight = 1
        c_closed.circuit_breaker.state.name = "CLOSED"

        lb = LoadBalancer([c_open, c_closed])
        available = lb.available_clients()

        assert len(available) == 1
        assert available[0].name == "closed-provider"

    def test_empty_providers_raises(self):
        with pytest.raises(ValueError, match="requires at least one"):
            LoadBalancer([])

    def test_len(self, mock_client):
        lb = LoadBalancer([mock_client])
        assert len(lb) == 1

    def test_clients_property(self, mock_client):
        lb = LoadBalancer([mock_client])
        assert len(lb.clients) == 1
        assert lb.clients[0].name == "test-provider"
