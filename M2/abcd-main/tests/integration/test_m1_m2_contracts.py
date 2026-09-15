import pytest
from app.models.envelope import RawEventEnvelope
from app.models.parsed_event import ParsedEvent
from app.classifier.detector import Classifier
from app.registry.repository import ParserRepository
from app.registry.service import ParserRegistryService


@pytest.fixture
def parser_setup():
    repo = ParserRepository()
    repo.load_from_directory("./parsers")
    service = ParserRegistryService(repo)
    classifier = Classifier()
    return service, classifier


def test_m1_contract_cisco_asa(parser_setup):
    service, classifier = parser_setup

    m1_envelope = RawEventEnvelope(
        schema_version="1.0.0",
        raw_event_id="m1_cisco_001",
        tenant_id="tenant-enterprise-1",
        source_id="asa-firewall-datacenter-east",
        received_at="2026-09-12T04:00:15.123Z",
        transport="syslog",
        payload="<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443",
        encoding="utf-8",
        sha256="c2e5645a4ebcdb79bbd279294e35ea0f3f260195ec0a58296eb4c5decf12e4f0",
        raw_reference="s3://lakehouse-raw/tenant-enterprise-1/2026/09/12/m1_cisco_001.bin",
        metadata={"collector": "rsyslog-01", "cluster": "us-east-1"},
    )

    classif = classifier.classify(m1_envelope)
    executable, defn = service.find_parser(
        classif, m1_envelope.model_dump(), tenant_id=m1_envelope.tenant_id
    )
    assert executable is not None
    assert defn is not None

    extracted = executable.parse(m1_envelope.model_dump())
    assert extracted["connection_id"] == 847392
    assert extracted["srcip"] == "192.168.10.25"
    assert extracted["dstip"] == "8.8.8.8"

    parsed_output = ParsedEvent(
        schema_version=m1_envelope.schema_version,
        raw_event_id=m1_envelope.raw_event_id,
        tenant_id=m1_envelope.tenant_id,
        source_id=m1_envelope.source_id,
        status="PARSED",
        classification=classif,
        parser={
            "id": defn.id,
            "name": defn.name,
            "version": defn.version,
            "confidence": 1.0,
        },
        fields=extracted,
        raw_reference=m1_envelope.raw_reference,
        sha256=m1_envelope.sha256,
        processing_time_ms=1.2,
        metadata=m1_envelope.metadata,
    )

    # Invariants Verification
    assert parsed_output.raw_event_id == m1_envelope.raw_event_id
    assert parsed_output.tenant_id == m1_envelope.tenant_id
    assert parsed_output.schema_version == m1_envelope.schema_version
    assert parsed_output.source_id == m1_envelope.source_id
    assert parsed_output.sha256 == m1_envelope.sha256
    assert parsed_output.raw_reference == m1_envelope.raw_reference
    assert parsed_output.status == "PARSED"


def test_m1_contract_windows_4624(parser_setup):
    service, classifier = parser_setup

    m1_windows = RawEventEnvelope(
        schema_version="1.0.0",
        raw_event_id="m1_win_4624",
        tenant_id="tenant-corp",
        source_id="win-dc-01",
        received_at="2026-09-12T04:05:00.000Z",
        transport="tcp",
        payload='{"EventID": 4624, "Computer": "DC01.corp.local", "SubjectUserName": "SYSTEM", "TargetUserName": "jdoe", "IpAddress": "10.10.0.50"}',
        encoding="utf-8",
    )

    classif = classifier.classify(m1_windows)
    assert classif.format == "json"
    executable, defn = service.find_parser(
        classif, m1_windows.model_dump(), tenant_id=m1_windows.tenant_id
    )
    assert executable is not None
    extracted = executable.parse(m1_windows.model_dump())
    assert extracted["EventID"] == 4624
    assert extracted["TargetUserName"] == "jdoe"


def test_m1_contract_unknown_event(parser_setup):
    service, classifier = parser_setup

    m1_unknown = RawEventEnvelope(
        schema_version="1.0.0",
        raw_event_id="m1_unk_001",
        tenant_id="tenant-corp",
        received_at="2026-09-12T04:10:00.000Z",
        transport="udp",
        payload="RANDOM GIBBERISH PROTOCOL PACKET 12345",
    )

    classif = classifier.classify(m1_unknown)
    executable, defn = service.find_parser(
        classif, m1_unknown.model_dump(), tenant_id=m1_unknown.tenant_id
    )
    assert executable is None
    assert defn is None


def test_m1_contract_malformed_event(parser_setup):
    service, classifier = parser_setup

    m1_malformed = RawEventEnvelope(
        schema_version="1.0.0",
        raw_event_id="m1_malformed_001",
        tenant_id="tenant-corp",
        received_at="2026-09-12T04:15:00.000Z",
        transport="http",
        payload="<broken xml json {[[ not valid",
    )

    classif = classifier.classify(m1_malformed)
    assert classif.format in ["plain_text", "syslog"]


def test_m1_contract_non_utf8_binary_payload():
    # Simulate payload containing non-ASCII / binary bytes decoded with replacement
    raw_bytes = b"\x80abc\xff\xfe123"
    decoded_payload = raw_bytes.decode("utf-8", errors="replace")

    envelope = RawEventEnvelope(
        raw_event_id="m1_bin_001",
        tenant_id="tenant-corp",
        transport="tcp",
        payload=decoded_payload,
    )
    assert envelope.sha256 is not None
    assert len(envelope.sha256) == 64
