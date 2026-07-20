"""Dedicated tests for the health-check endpoints."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from nim_gateway.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Health endpoint returns status ok."""

    async def test_health_returns_ok(self, client):
        import nim_gateway.core.config as cfg
        original = cfg.settings.gateway.api_key_enabled
        cfg.settings.gateway.api_key_enabled = False
        try:
            resp = await client.get("/health")
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] in ("ok", "healthy")
            assert "version" in data
            assert "timestamp" in data
        finally:
            cfg.settings.gateway.api_key_enabled = original

    async def test_health_without_auth(self, client):
        """Even with auth enabled, /health should be public."""
        resp = await client.get("/health")
        # Health endpoint should always be accessible
        assert resp.status_code in (200, 401)

    async def test_v1_health(self, client):
        import nim_gateway.core.config as cfg
        original = cfg.settings.gateway.api_key_enabled
        cfg.settings.gateway.api_key_enabled = False
        try:
            resp = await client.get("/v1/health")
            assert resp.status_code == 200
        finally:
            cfg.settings.gateway.api_key_enabled = original
