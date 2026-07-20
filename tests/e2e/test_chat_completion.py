"""E2E test — chat completion through the running gateway."""

from __future__ import annotations

import httpx


def test_chat_completion():
    """POST /v1/chat/completions returns 401 without API key."""
    resp = httpx.post(
        "http://localhost:8000/v1/chat/completions",
        json={
            "model": "meta/llama-3.1-8b-instruct",
            "messages": [{"role": "user", "content": "Hello"}],
        },
        timeout=5.0,
    )
    # Without API key we expect 401
    assert resp.status_code == 401


def test_models_list():
    """GET /v1/models returns 401 without API key."""
    resp = httpx.get("http://localhost:8000/v1/models", timeout=5.0)
    assert resp.status_code == 401
