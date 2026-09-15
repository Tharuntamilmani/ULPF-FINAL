"""Unit tests for integration adapters — mock and HTTP."""

from __future__ import annotations

import pytest

from backend.app.integrations.http_module_client import HttpModuleClient
from backend.app.integrations.mock_module_client import MockModuleClient
from backend.app.integrations.module_client import HealthStatus


class TestMockModuleClient:
    """Mock adapter must always return UNAVAILABLE and mark itself as mock."""

    @pytest.fixture
    def client(self) -> MockModuleClient:
        return MockModuleClient("m1-ingestion")

    @pytest.mark.asyncio
    async def test_health_is_unavailable(self, client):
        result = await client.get_health()
        assert result.status == HealthStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_health_is_marked_mock(self, client):
        result = await client.get_health()
        assert result.is_mock is True

    @pytest.mark.asyncio
    async def test_readiness_is_unavailable(self, client):
        result = await client.get_readiness()
        assert result.status == HealthStatus.UNAVAILABLE

    @pytest.mark.asyncio
    async def test_metrics_returns_comment(self, client):
        metrics = await client.get_metrics()
        assert "MOCK" in metrics

    @pytest.mark.asyncio
    async def test_status_dict_has_is_mock(self, client):
        status = await client.get_status()
        assert status["is_mock"] is True
        assert status["status"] == HealthStatus.UNAVAILABLE.value

    def test_base_url_is_none(self, client):
        assert client.base_url is None

    def test_service_name(self, client):
        assert client.service_name == "m1-ingestion"


class TestHttpModuleClientNoServer:
    """HttpModuleClient with no reachable server must return UNAVAILABLE."""

    @pytest.fixture
    def client(self) -> HttpModuleClient:
        return HttpModuleClient("m1-ingestion", "http://localhost:19999")

    @pytest.mark.asyncio
    async def test_health_unavailable_on_refused(self, client):
        result = await client.get_health()
        assert result.status == HealthStatus.UNAVAILABLE
        assert result.is_mock is False

    @pytest.mark.asyncio
    async def test_metrics_empty_on_refused(self, client):
        metrics = await client.get_metrics()
        assert metrics == ""

    def test_no_base_url_returns_unavailable(self):
        c = HttpModuleClient("test-svc", None)
        # Synchronous check — base_url is None
        assert c.base_url is None

    @pytest.mark.asyncio
    async def test_no_base_url_health_unavailable(self):
        c = HttpModuleClient("test-svc", None)
        result = await c.get_health()
        assert result.status == HealthStatus.UNAVAILABLE
        assert "No base URL" in result.details.get("reason", "")


class TestM1ToM5ClientFactories:
    """Each factory returns mock adapter when USE_MOCK_ADAPTERS=true."""

    def test_m1_factory_returns_mock(self, monkeypatch):
        monkeypatch.setenv("USE_MOCK_ADAPTERS", "true")
        # Re-import to pick up env changes (use fresh settings)
        import backend.app.core.config as cfg

        cfg.get_settings.cache_clear()
        from backend.app.integrations.m1_client import get_m1_client

        client = get_m1_client()
        assert isinstance(client, MockModuleClient)
        cfg.get_settings.cache_clear()

    def test_m5_factory_returns_http_without_mock(self, monkeypatch):
        monkeypatch.setenv("USE_MOCK_ADAPTERS", "false")
        import backend.app.core.config as cfg

        cfg.get_settings.cache_clear()
        from backend.app.integrations.m5_client import get_m5_client

        client = get_m5_client()
        assert isinstance(client, HttpModuleClient)
        cfg.get_settings.cache_clear()
