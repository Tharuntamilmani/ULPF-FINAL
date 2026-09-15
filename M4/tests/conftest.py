"""Pytest fixtures and configuration for ULPF M4 test suites."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from app.cache.memory_lru import MemoryLRUCache
from app.config.lifecycle import ConfigurationManager
from app.contracts.canonical_event import (
    Application,
    CanonicalEvent,
    Endpoint,
    EventMetadata,
    Host,
    Identity,
    Network,
    NormalizationMetadata,
    Observer,
    ParserMetadata,
    Process,
    ProvenanceMetadata,
    Security,
    TenantMetadata,
    VendorMetadata,
)
from app.enrichment.engine import EnrichmentEngine
from app.main import create_app
from app.models.tenant import TenantContext
from app.providers.asset_provider import LocalAssetProvider
from app.providers.geoip_provider import LocalGeoIPProvider
from app.providers.registry import ProviderRegistry
from app.providers.threat_intel_provider import LocalThreatIntelProvider


@pytest.fixture
def sample_canonical_event() -> CanonicalEvent:
    """Provide a standard fully-populated canonical UES event fixture."""
    return CanonicalEvent(
        schema_version="ues.v1",
        event=EventMetadata(
            id="EVT-20260914-0001",
            timestamp=datetime.now(UTC).isoformat(),
            kind="event",
            type=["network", "connection"],
            category=["network"],
            outcome="success",
        ),
        observer=Observer(
            hostname="sensor-edge-01",
            ip="192.168.10.1",
            type="network-tap",
            version="2.4.0",
        ),
        source=Endpoint(
            ip="10.100.1.5",
            port=54321,
            mac="00:1A:2B:3C:4D:5E",
        ),
        destination=Endpoint(
            ip="8.8.8.8",
            port=53,
            domain="evil-payload.example.com",
        ),
        network=Network(
            transport="udp",
            protocol="dns",
            direction="egress",
            bytes_in=128,
            bytes_out=64,
        ),
        host=Host(
            name="prod-sql-cluster-node1",
            hostname="prod-sql-node1.corp.internal",
            os="Linux",
        ),
        identity=Identity(
            user_id="USR-9901",
            username="service_account_db",
        ),
        application=Application(
            name="dns-resolver-app",
            version="1.0.0",
        ),
        process=Process(
            pid=4192,
            name="dns-resolver",
            executable="/usr/bin/dns-resolver",
        ),
        security=Security(
            severity="medium",
            risk_score=45.0,
        ),
        parser=ParserMetadata(
            name="parser-zeek-dns",
            version="1.2.0",
        ),
        normalization=NormalizationMetadata(
            schema_target="ues.v1",
            rule_version="1.0.0",
        ),
        provenance=ProvenanceMetadata(
            raw_event_id="RAW-LOG-STREAM-998811",
            ingestion_timestamp=datetime.now(UTC).isoformat(),
            pipeline_id="ulpf-ingress-01",
        ),
        vendor=VendorMetadata(
            name="zeek",
            product="zeek-sensor",
        ),
        extensions={},
        tenant=TenantMetadata(
            tenant_id="tenant_alpha",
        ),
    )


@pytest.fixture
def sample_tenant_context() -> TenantContext:
    """Provide a TenantContext matching sample_canonical_event."""
    return TenantContext(tenant_id="tenant_alpha", configuration_version="1.0.0")


@pytest.fixture
def fresh_registry() -> ProviderRegistry:
    """Provide a freshly initialized provider registry with standard first-party providers."""
    registry = ProviderRegistry()
    registry.register(LocalAssetProvider())
    registry.register(LocalGeoIPProvider())
    registry.register(LocalThreatIntelProvider())
    return registry


@pytest.fixture
def fresh_config_manager() -> ConfigurationManager:
    """Provide a fresh configuration manager."""
    return ConfigurationManager()


@pytest.fixture
def fresh_cache() -> MemoryLRUCache:
    """Provide a clean in-memory cache instance."""
    return MemoryLRUCache(max_size=1000)


@pytest.fixture
def fresh_engine(
    fresh_registry: ProviderRegistry,
    fresh_config_manager: ConfigurationManager,
    fresh_cache: MemoryLRUCache,
) -> EnrichmentEngine:
    """Provide a fresh EnrichmentEngine instance."""
    return EnrichmentEngine(
        registry=fresh_registry,
        config_manager=fresh_config_manager,
        cache=fresh_cache,
    )


@pytest.fixture
def test_client() -> TestClient:
    """FastAPI TestClient for API endpoint testing."""
    app = create_app()
    return TestClient(app)
