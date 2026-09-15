"""Additional property-based tests for integrity and idempotence."""

from datetime import UTC, datetime

from hypothesis import given, settings
from hypothesis import strategies as st

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
from app.integrity.canonicalizer import canonicalize
from app.integrity.hasher import hash_canonical_sha256
from app.integrity.verifier import calculate_integrity, verify_integrity


def build_canonical_event() -> CanonicalEvent:
    return CanonicalEvent(
        schema_version="ues.v1",
        event=EventMetadata(
            id="EVT-PROP-002",
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


@given(
    tag=st.text(min_size=1, max_size=30),
    confidence=st.floats(min_value=0.0, max_value=1.0),
)
@settings(max_examples=25)
def test_property_deterministic_hash_across_runs(tag: str, confidence: float) -> None:
    """Property: Hash of identical structure is 100% deterministic across multiple evaluations."""
    data = {"tag": tag, "confidence": round(confidence, 4), "active": True}
    h1 = hash_canonical_sha256(data)
    h2 = hash_canonical_sha256(data)
    assert h1 == h2


@given(
    domain=st.from_regex(r"^[a-z0-9\-]{1,20}\.example\.com$", fullmatch=True),
)
@settings(max_examples=20)
def test_property_destination_domain_tampering(domain: str) -> None:
    """Property: Any change to destination.domain causes integrity mismatch."""
    event = build_canonical_event()
    meta = calculate_integrity(event)
    event.integrity = meta

    tampered = event.model_copy(deep=True)
    tampered.destination.domain = domain
    if domain != event.destination.domain:
        assert verify_integrity(tampered, expected_digest=meta.digest) is False


@given(
    extra_field=st.from_regex(r"^[a-z_]{3,15}$", fullmatch=True),
    extra_value=st.integers(),
)
@settings(max_examples=20)
def test_property_extension_addition_tampering(extra_field: str, extra_value: int) -> None:
    """Property: Appending arbitrary extra keys into extensions invalidates digest."""
    event = build_canonical_event()
    meta = calculate_integrity(event)
    event.integrity = meta

    tampered = event.model_dump(mode="json")
    tampered["extensions"][extra_field] = extra_value

    assert verify_integrity(tampered, expected_digest=meta.digest) is False


@given(
    int_val=st.integers(min_value=-1000000, max_value=1000000),
)
@settings(max_examples=25)
def test_property_canonical_number_encoding_stability(int_val: int) -> None:
    """Property: Number canonicalization produces stable ASCII representation."""
    b = canonicalize(int_val)
    assert b.decode("utf-8") == str(int_val)


@given(
    str_val=st.text(min_size=0, max_size=100),
)
@settings(max_examples=25)
def test_property_canonical_string_roundtrip(str_val: str) -> None:
    """Property: String canonicalization is UTF-8 encoded and wrapped in quotes."""
    b = canonicalize(str_val)
    s = b.decode("utf-8")
    assert s.startswith('"') and s.endswith('"')


@given(
    raw_id=st.from_regex(r"^[A-Z0-9_\-]{5,20}$", fullmatch=True),
)
@settings(max_examples=20)
def test_property_provenance_raw_id_tampering(raw_id: str) -> None:
    """Property: Tampering with raw_event_id causes verification failure."""
    event = build_canonical_event()
    meta = calculate_integrity(event)
    event.integrity = meta

    tampered = event.model_copy(deep=True)
    tampered.provenance.raw_event_id = raw_id
    if raw_id != event.provenance.raw_event_id:
        assert verify_integrity(tampered, expected_digest=meta.digest) is False
