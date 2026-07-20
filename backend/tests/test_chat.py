"""Integration tests for the chat completions endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient

from nim_gateway.main import app


@pytest.fixture
async def client():
    """Async HTTP test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
class TestHealthEndpoint:
    """Health check endpoint tests."""

    async def test_health_returns_status(self, client):
        response = await client.get("/health")
        assert response.status_code in (200, 401)  # may need API key

        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["version"] == "0.1.0"

    async def test_v1_health(self, client):
        response = await client.get("/v1/health")
        assert response.status_code in (200, 401)


@pytest.mark.asyncio
class TestModelsEndpoint:
    """Models listing endpoint tests."""

    async def test_models_list(self, client):
        response = await client.get("/v1/models")
        assert response.status_code in (200, 401)

        if response.status_code == 200:
            data = response.json()
            assert data["object"] == "list"
            assert isinstance(data["data"], list)


@pytest.mark.asyncio
class TestChatEndpoint:
    """Chat completions endpoint tests."""

    async def test_chat_requires_auth(self, client):
        response = await client.post(
            "/v1/chat/completions",
            json={
                "model": "meta/llama-3.1-8b-instruct",
                "messages": [{"role": "user", "content": "Hello"}],
            },
        )
        # Without API key, should get 401
        assert response.status_code == 401

    async def test_chat_unknown_model(self, client):
        """With API key disabled in settings, test unknown model."""
        # Disable auth for this test
        import nim_gateway.core.config as cfg
        original = cfg.settings.gateway.api_key_enabled
        cfg.settings.gateway.api_key_enabled = False
        try:
            response = await client.post(
                "/v1/chat/completions",
                json={
                    "model": "nonexistent-model",
                    "messages": [{"role": "user", "content": "Hello"}],
                },
            )
            assert response.status_code == 404
        finally:
            cfg.settings.gateway.api_key_enabled = original

    async def test_chat_validation(self, client):
        """Request without model should fail validation."""
        import nim_gateway.core.config as cfg
        original = cfg.settings.gateway.api_key_enabled
        cfg.settings.gateway.api_key_enabled = False
        try:
            response = await client.post(
                "/v1/chat/completions",
                json={"messages": [{"role": "user", "content": "Hello"}]},
            )
            assert response.status_code == 422
        finally:
            cfg.settings.gateway.api_key_enabled = original

    async def test_root_endpoint(self, client):
        import nim_gateway.core.config as cfg
        original = cfg.settings.gateway.api_key_enabled
        cfg.settings.gateway.api_key_enabled = False
        try:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "NVIDIA NIM Gateway"
        finally:
            cfg.settings.gateway.api_key_enabled = original
