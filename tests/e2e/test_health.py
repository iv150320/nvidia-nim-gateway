"""E2E health check — validate all docker-compose services are up."""

from __future__ import annotations

import httpx


def test_gateway_health():
    """Gateway /health returns 200 when running in docker-compose."""
    resp = httpx.get("http://localhost:8000/health", timeout=5.0)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
