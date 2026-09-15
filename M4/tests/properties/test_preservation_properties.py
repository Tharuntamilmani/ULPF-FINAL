"""Property-based tests for preservation invariants and determinism using Hypothesis."""

import random
from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st

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
from app.contracts.enrichment_contract import EnrichmentRequest
from app.enrichment.engine import EnrichmentEngine
from app.integrity.canonicalizer import canonicalize
from app.integrity.verifier import calculate_integrity, verify_integrity
from app.models.tenant import TenantContext
from app.providers.asset_provider import LocalAssetProvider
from app.providers.geoip_provider import LocalGeoIPProvider
from app.providers.registry import ProviderRegistry
from app.providers.threat_intel_provider import LocalThreatIntelProvider


def build_canonical_event() -> CanonicalEvent:
    """Helper creating a fresh canonical event for property tests."""
    return CanonicalEvent(
        schema_version="ues.v1",
        event=EventMetadata(
            id="EVT-PROP-001",
            timestamp=datetime.now(UTC).isoformat(),
            kind="event",
            type=["network"],
            category=["network"],
            outcome="success",
        ),
        observer=Observer(hostname="sensor-01"),
        source=Endpoint(ip="10.100.1.5", port=54321),
        destination=Endpoint(ip="8.8.8.8", port=53, domain="evil-payload.example.com"),
        network=Network(protocol="dns"),
        host=Host(name="db-host"),
        identity=Identity(user_id="usr-1"),
        application=Application(name="app", version="1.0"),
        process=Process(pid=100),
        security=Security(severity="medium"),
        parser=ParserMetadata(),
        normalization=NormalizationMetadata(),
        provenance=ProvenanceMetadata(raw_event_id="RAW-001"),
        vendor=VendorMetadata(),
        extensions={},
        tenant=TenantMetadata(tenant_id="tenant_alpha"),
    )


def make_engine() -> EnrichmentEngine:
    reg = ProviderRegistry()
    reg.register(LocalAssetProvider())
    reg.register(LocalGeoIPProvider())
    reg.register(LocalThreatIntelProvider())
    return EnrichmentEngine(reg, ConfigurationManager(), MemoryLRUCache())


@given(
    event_id=st.from_regex(r"^[a-zA-Z0-9_\-\.]{1,32}$", fullmatch=True),
    raw_id=st.from_regex(r"^[a-zA-Z0-9_\-\.]{1,32}$", fullmatch=True),
    tenant_id=st.from_regex(r"^[a-zA-Z0-9_\-\.]{1,32}$", fullmatch=True),
    source_ip=st.sampled_from(["10.100.1.5", "8.8.8.8", "192.168.1.50", "1.1.1.1"]),
)
@settings(max_examples=25)
def test_property_preservation_invariants(
    event_id: str,
    raw_id: str,
    tenant_id: str,
    source_ip: str,
) -> None:
    """Property: enrich(event) preserves event.id, raw_event_id, tenant_id, and source.ip."""
    event = build_canonical_event()
    event.event.id = event_id
    event.provenance.raw_event_id = raw_id
    event.tenant.tenant_id = tenant_id
    event.source.ip = source_ip

    engine = make_engine()
    tenant_ctx = TenantContext(tenant_id=tenant_id)
    req = EnrichmentRequest(event=event, tenant_context=tenant_ctx)
    result = engine.process(req)

    # Invariants
    assert result.event.event.id == event_id
    assert result.event.provenance.raw_event_id == raw_id
    assert result.event.tenant.tenant_id == tenant_id
    assert result.event.source.ip == source_ip


@given(
    sample_val=st.text(min_size=1, max_size=50),
    sample_num=st.integers(min_value=-10000, max_value=10000),
)
@settings(max_examples=25)
def test_property_canonicalization_key_order_independence(sample_val: str, sample_num: int) -> None:
    """Property: Shuffling dictionary insertion order produces byte-identical canonical JSON."""
    items = [
        ("key_a", sample_val),
        ("key_b", sample_num),
        ("key_c", True),
        ("key_d", None),
        ("key_e", [1, 2, 3]),
    ]

    dict_original = dict(items)
    bytes_original = canonicalize(dict_original)

    # Shuffle and verify
    shuffled_items = list(items)
    random.shuffle(shuffled_items)
    dict_shuffled = dict(shuffled_items)
    bytes_shuffled = canonicalize(dict_shuffled)

    assert bytes_original == bytes_shuffled


@given(
    event_id=st.from_regex(r"^[a-zA-Z0-9_\-\.]{1,20}$", fullmatch=True),
)
@settings(max_examples=20)
def test_property_integrity_roundtrip(event_id: str) -> None:
    """Property: calculate_integrity followed by verify_integrity always evaluates to True."""
    event = build_canonical_event()
    event.event.id = event_id

    meta = calculate_integrity(event)
    event.integrity = meta

    assert verify_integrity(event) is True


@given(
    mutated_port=st.integers(min_value=1, max_value=65535),
)
@settings(max_examples=20)
def test_property_tampering_always_detected(mutated_port: int) -> None:
    """Property: Modifying any field after digest calculation makes verify_integrity return False."""
    event = build_canonical_event()
    meta = calculate_integrity(event)
    event.integrity = meta

    tampered = event.model_copy(deep=True)
    tampered.source.port = mutated_port if event.source.port != mutated_port else 9999

    assert verify_integrity(tampered, expected_digest=meta.digest) is False
