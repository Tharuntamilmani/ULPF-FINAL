import pytest
from packaging.version import parse as parse_version
from app.engine.grok import GrokParser
from app.registry.models import ParserDefinition
from app.registry.repository import ParserRepository
from app.registry.service import ParserRegistryService
from app.classifier.detector import ClassificationResult, Classifier
from app.models.envelope import RawEventEnvelope


def test_grok_payload_boundaries():
    parser = GrokParser(
        parser_id="test-grok",
        name="Test Grok",
        version="1.0.0",
        patterns=["^MSG %{WORD:msg}"],
        max_payload_bytes=100_000,
    )

    # 1. Exactly 100,000 bytes boundary accepted
    header = "MSG "
    filler = "a" * (100_000 - len(header))
    payload_exact = header + filler
    assert len(payload_exact.encode("utf-8")) == 100_000
    res = parser.parse({"payload": payload_exact})
    assert res["msg"] == filler

    # 2. 100,001 bytes rejected
    payload_oversized = payload_exact + "x"
    assert parser.can_parse({"payload": payload_oversized}) is False
    with pytest.raises(ValueError, match="exceeds maximum allowed 100000 bytes"):
        parser.parse({"payload": payload_oversized})

    # 3. 5MB payload rejected safely without hanging
    payload_5mb = "MSG " + ("A" * 5_000_000)
    assert parser.can_parse({"payload": payload_5mb}) is False
    with pytest.raises(ValueError, match="exceeds maximum allowed"):
        parser.parse({"payload": payload_5mb})


def test_grok_malicious_redos_rejected():
    with pytest.raises(
        ValueError, match="Potentially unsafe ReDoS regex pattern detected"
    ):
        GrokParser(
            parser_id="redos-grok",
            name="ReDoS Grok",
            version="1.0.0",
            patterns=["(a+)+$"],
        )


def test_semantic_versioning_and_rollback():
    repo = ParserRepository()
    service = ParserRegistryService(repo)

    # Register version 1.9.0
    p_19 = ParserDefinition(
        id="parser-version-test",
        name="Version Test v1.9",
        vendor="Corp",
        product="App",
        formats=["syslog"],
        version="1.9.0",
        patterns=["v1.9: %{WORD:data}"],
    )
    service.register_parser(p_19)

    # Register version 1.10.0
    p_110 = ParserDefinition(
        id="parser-version-test",
        name="Version Test v1.10",
        vendor="Corp",
        product="App",
        formats=["syslog"],
        version="1.10.0",
        patterns=["v1.10: %{WORD:data}"],
    )
    service.register_parser(p_110)

    # Register version 1.11.0
    p_111 = ParserDefinition(
        id="parser-version-test",
        name="Version Test v1.11",
        vendor="Corp",
        product="App",
        formats=["syslog"],
        version="1.11.0",
        patterns=["v1.11: %{WORD:data}"],
    )
    service.register_parser(p_111)

    # Verify semver ordering: 1.11.0 > 1.10.0 > 1.9.0
    assert parse_version("1.11.0") > parse_version("1.10.0") > parse_version("1.9.0")

    # Verify active parser is 1.11.0 (highest semver, NOT lexicographic 1.9.0)
    active = repo.get("parser-version-test")
    assert active.version == "1.11.0"
    assert active.name == "Version Test v1.11"

    # Rollback to 1.10.0
    rolled_back = service.rollback_parser("parser-version-test", "1.10.0")
    assert rolled_back is not None
    assert rolled_back.version == "1.10.0"
    assert repo.get("parser-version-test").version == "1.10.0"


def test_null_vendor_handling_regression():
    repo = ParserRepository()
    repo.load_from_directory("./parsers")
    service = ParserRegistryService(repo)

    # Test with classification where vendor and product are None
    classif_null = ClassificationResult(
        format="json", vendor=None, product=None, confidence=0.95
    )
    json_event = {"payload": '{"service": "auth", "user": "alice", "active": true}'}

    # Must NOT crash with AttributeError: 'NoneType' object has no attribute 'lower'
    executable, defn = service.find_parser(classif_null, json_event)
    assert executable is not None
    assert defn is not None
    assert defn.vendor == "Generic"
    extracted = executable.parse(json_event)
    assert extracted["user"] == "alice"

    # Test with KV and null vendor
    classif_kv_null = ClassificationResult(
        format="kv", vendor=None, product=None, confidence=0.85
    )
    kv_event = {"payload": "key1=val1 key2=123"}
    executable_kv, defn_kv = service.find_parser(classif_kv_null, kv_event)
    assert executable_kv is not None
    assert defn_kv is not None
    extracted_kv = executable_kv.parse(kv_event)
    assert extracted_kv["key1"] == "val1"
    assert extracted_kv["key2"] == 123


def test_deterministic_parser_resolution_repeatability():
    repo = ParserRepository()
    repo.load_from_directory("./parsers")
    service = ParserRegistryService(repo)
    classifier = Classifier()

    envelope = RawEventEnvelope(
        raw_event_id="repeat_001",
        tenant_id="tenant-repeat",
        payload="<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443",
    )

    baseline_classif = classifier.classify(envelope)
    base_exec, base_defn = service.find_parser(
        baseline_classif, envelope.model_dump(), tenant_id="tenant-repeat"
    )
    assert base_defn is not None
    expected_id = base_defn.id
    expected_fields = base_exec.parse(envelope.model_dump())

    # Run 100 identical repetitions
    for _ in range(100):
        c = classifier.classify(envelope)
        ex, df = service.find_parser(
            c, envelope.model_dump(), tenant_id="tenant-repeat"
        )
        assert df.id == expected_id
        res = ex.parse(envelope.model_dump())
        assert res == expected_fields
