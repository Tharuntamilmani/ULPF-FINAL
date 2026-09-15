"""
Integration adapter tests.

These tests use MockModuleClient so they run completely without M1-M5.
They verify the adapter contract interface is properly implemented.

For real integration tests against live M1-M5 services, set:
  USE_MOCK_ADAPTERS=false
  M1_BASE_URL=http://m1-host:8001
  ... etc.
and run: pytest tests/integration/ -v -s
"""

from __future__ import annotations

import pytest

from backend.app.integrations.m1_client import get_m1_client
from backend.app.integrations.m2_client import get_m2_client
from backend.app.integrations.m3_client import get_m3_client
from backend.app.integrations.m4_client import get_m4_client
from backend.app.integrations.m5_client import get_m5_client
from backend.app.integrations.mock_module_client import MockModuleClient
from backend.app.integrations.module_client import HealthStatus, ModuleClient


@pytest.mark.parametrize(
    "factory", [get_m1_client, get_m2_client, get_m3_client, get_m4_client, get_m5_client]
)
def test_all_factories_return_module_client(factory):
    client = factory()
    assert isinstance(client, ModuleClient)


@pytest.mark.parametrize(
    "factory,name",
    [
        (get_m1_client, "m1-ingestion"),
        (get_m2_client, "m2-parser"),
        (get_m3_client, "m3-normalizer"),
        (get_m4_client, "m4-enrichment"),
        (get_m5_client, "m5-delivery"),
    ],
)
def test_service_names(factory, name):
    client = factory()
    assert client.service_name == name


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "factory", [get_m1_client, get_m2_client, get_m3_client, get_m4_client, get_m5_client]
)
async def test_mock_health_returns_unavailable(factory):
    """
    In standalone mode (USE_MOCK_ADAPTERS=true), all external services
    must return UNAVAILABLE — never HEALTHY.
    This is the correct behaviour that the demo dashboard shows.
    """
    client = factory()
    assert isinstance(client, MockModuleClient)
    result = await client.get_health()
    assert result.status == HealthStatus.UNAVAILABLE
    assert result.is_mock is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "factory", [get_m1_client, get_m2_client, get_m3_client, get_m4_client, get_m5_client]
)
async def test_mock_status_dict_structure(factory):
    client = factory()
    status = await client.get_status()
    assert "service" in status
    assert "status" in status
    assert "is_mock" in status
    assert "checked_at" in status
    assert status["status"] == HealthStatus.UNAVAILABLE.value


@pytest.mark.asyncio
async def test_health_aggregation_with_mocks():
    """
    get_all_service_health() must aggregate results from all services.
    With mock adapters, M1-M5 are UNAVAILABLE — infra may also be unavailable in test.
    The result must never fabricate HEALTHY for mock services.
    """
    from backend.app.integrations.health_client import get_all_service_health

    result = await get_all_service_health()
    assert "services" in result
    assert "overall" in result
    assert "m6_control_plane" in result
    assert result["m6_control_plane"] == "HEALTHY"

    # All module clients must be mock / unavailable
    for module_key in [
        "m1-ingestion",
        "m2-parser",
        "m3-normalizer",
        "m4-enrichment",
        "m5-delivery",
    ]:
        if module_key in result["services"]:
            svc = result["services"][module_key]
            assert (
                svc["status"] == HealthStatus.UNAVAILABLE.value
            ), f"{module_key} reported {svc['status']} but should be UNAVAILABLE in standalone mode"
