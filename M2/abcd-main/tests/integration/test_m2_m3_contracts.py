from app.models.envelope import RawEventEnvelope
from app.models.parsed_event import ParsedEvent
from app.classifier.detector import Classifier
from app.registry.repository import ParserRepository
from app.registry.service import ParserRegistryService


def test_m2_to_m3_contract_consumption_and_invariants():
    repo = ParserRepository()
    repo.load_from_directory("./parsers")
    service = ParserRegistryService(repo)
    classifier = Classifier()

    raw_cisco = RawEventEnvelope(
        schema_version="1.0.0",
        raw_event_id="evt_m2_m3_001",
        tenant_id="tenant-security-ops",
        source_id="cisco-fw-core",
        received_at="2026-09-12T04:00:15.000Z",
        transport="syslog",
        payload="<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443",
        raw_reference="s3://lakehouse/evt_m2_m3_001.bin",
    )

    classif = classifier.classify(raw_cisco)
    executable, defn = service.find_parser(
        classif, raw_cisco.model_dump(), tenant_id=raw_cisco.tenant_id
    )
    assert executable is not None

    extracted = executable.parse(raw_cisco.model_dump())

    parsed_event = ParsedEvent(
        schema_version="1.0.0",
        raw_event_id=raw_cisco.raw_event_id,
        tenant_id=raw_cisco.tenant_id,
        source_id=raw_cisco.source_id,
        status="PARSED",
        classification=classif,
        parser={
            "id": defn.id,
            "name": defn.name,
            "version": defn.version,
            "confidence": 1.0,
        },
        fields=extracted,
        unmapped_fields=[],
        raw_reference=raw_cisco.raw_reference,
        sha256=raw_cisco.sha256,
        processing_time_ms=0.85,
    )

    # 1. Verify JSON serializability for M3 ingestion bus
    serialized = parsed_event.model_dump()
    assert isinstance(serialized, dict)

    # 2. Invariant checks for M3
    assert serialized["schema_version"] == "1.0.0"
    assert serialized["raw_event_id"] == "evt_m2_m3_001"
    assert serialized["tenant_id"] == "tenant-security-ops"
    assert serialized["source_id"] == "cisco-fw-core"
    assert serialized["status"] == "PARSED"
    assert serialized["parser"]["id"] == "parser-cisco-asa"
    assert serialized["parser"]["version"] == "1.2.0"
    assert serialized["raw_reference"] == "s3://lakehouse/evt_m2_m3_001.bin"
    assert serialized["sha256"] is not None

    # 3. VERIFY NO UES NORMALIZATION LEAKAGE
    # M2 must strictly emit un-normalized source-specific fields
    source_fields = serialized["fields"]
    assert "srcip" in source_fields
    assert "dstip" in source_fields
    assert "connection_id" in source_fields

    # Must NOT contain UES/ECS/OCSF normalized keys
    forbidden_normalized_keys = [
        "source.ip",
        "destination.ip",
        "network.transport",
        "event.action",
        "event.outcome",
        "event.category",
        "event.type",
        "event.dataset",
        "device.vendor",
        "device.product",
    ]
    for k in forbidden_normalized_keys:
        assert k not in source_fields, (
            f"UES leakage detected in M2 output! Key '{k}' must not exist in M2 fields"
        )
