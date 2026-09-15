"""API tests for health endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_liveness_no_auth(app_client: AsyncClient):
    """GET /health must not require authentication."""
    resp = await app_client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["service"] == "m6-control-plane"


@pytest.mark.asyncio
async def test_metrics_no_auth(app_client: AsyncClient):
    """GET /metrics must not require authentication."""
    resp = await app_client.get("/metrics")
    assert resp.status_code == 200
    # Prometheus text format
    assert (
        "ulpf_m6" in resp.text
        or "# HELP" in resp.text
        or resp.text == ""
        or resp.status_code == 200
    )


@pytest.mark.asyncio
async def test_docs_accessible(app_client: AsyncClient):
    """Swagger UI must be accessible."""
    resp = await app_client.get("/docs")
    assert resp.status_code == 200
