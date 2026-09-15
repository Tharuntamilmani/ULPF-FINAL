from app.registry.repository import ParserRepository
from app.registry.service import ParserRegistryService
from app.registry.models import ParserDefinition
from app.studio import ParserValidator, StudioTestRunner
from app.replay import ReplayService
from app.models.envelope import RawEventEnvelope


def test_studio_validation_and_testing():
    repo = ParserRepository()
    service = ParserRegistryService(repo)

    config = {
        "id": "parser-studio-test",
        "name": "Studio Test",
        "patterns": ["src=%{IP:srcip}"],
    }
    valid, errors = ParserValidator.validate_parser_config(config)
    assert valid is True
    assert len(errors) == 0

    p_def = ParserDefinition(
        id="parser-studio-test",
        name="Studio Test Parser",
        vendor="Acme",
        product="Firewall",
        formats=["kv"],
        version="1.0.0",
        patterns=["src=%{IP:srcip} dst=%{IP:dstip}"],
    )

    runner = StudioTestRunner(service)
    samples = ["src=1.1.1.1 dst=2.2.2.2"]
    results = runner.test_parser(p_def, samples)
    assert len(results) == 1
    assert results[0]["success"] is True
    assert results[0]["extracted_fields"]["srcip"] == "1.1.1.1"


def test_replay_engine():
    repo = ParserRepository()
    service = ParserRegistryService(repo)
    replay = ReplayService(service)

    # Register parser
    p_def = ParserDefinition(
        id="parser-acme-fw",
        name="ACME FW Parser",
        vendor="Acme",
        product="Firewall",
        formats=["kv"],
        version="1.0.0",
        patterns=["src_addr=%{IP:srcip} dst_addr=%{IP:dstip}"],
    )
    service.register_parser(p_def)

    # Replay historical raw events
    envelope = RawEventEnvelope(
        raw_event_id="raw_1001", payload="src_addr=10.0.0.5 dst_addr=8.8.8.8"
    )

    parsed_events = replay.replay_events("parser-acme-fw", [envelope], version="1.0.0")
    assert len(parsed_events) == 1
    pe = parsed_events[0]
    assert pe.raw_event_id == "raw_1001"
    assert pe.parser.id == "parser-acme-fw"
    assert pe.fields["srcip"] == "10.0.0.5"
    assert pe.fields["dstip"] == "8.8.8.8"
