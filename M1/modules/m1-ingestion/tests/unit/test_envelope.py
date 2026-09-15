import hashlib
from datetime import datetime, timezone

from app.envelope.builder import build_envelope, generate_object_key
from app.envelope.models import RawEventEnvelope


def test_generate_object_key_format():
    dt = datetime(2026, 9, 12, 5, 0, 15, tzinfo=timezone.utc)
    key = generate_object_key(
        tenant_id="demo-tenant",
        source_id="cisco-fw-01",
        raw_event_id="019958c3-2d44-7c7f-b3f1-5f1234567890",
        dt=dt,
    )

    expected = (
        "tenant=demo-tenant/"
        "year=2026/"
        "month=09/"
        "day=12/"
        "source=cisco-fw-01/"
        "event=019958c3-2d44-7c7f-b3f1-5f1234567890"
    )
    assert key == expected


def test_build_envelope_structure_and_validation():
    payload_bytes = b"<134>Sep 12 09:30:15 FW-EDGE-01 ASA log event sample"
    metadata = {
        "tenant_id": "test-tenant",
        "source_id": "test-source-01",
        "source_type": "firewall",
        "ingest_zone": "dmz",
        "collector_id": "collector-99",
    }

    envelope = build_envelope(
        raw_bytes=payload_bytes,
        metadata=metadata,
        transport_protocol="udp",
        transport_port=514,
        format_hint="syslog",
    )

    assert isinstance(envelope, RawEventEnvelope)
    assert envelope.tenant_id == "test-tenant"
    assert envelope.source_id == "test-source-01"
    assert envelope.transport.protocol == "udp"
    assert envelope.transport.port == 514
    assert envelope.integrity.algorithm == "SHA-256"
    assert envelope.integrity.hash == hashlib.sha256(payload_bytes).hexdigest()
    assert envelope.payload.data == payload_bytes.decode("utf-8")
    assert envelope.raw_storage.bucket == "ulpf-raw"
    assert "tenant=test-tenant" in envelope.raw_storage.object_key
