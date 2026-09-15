import pytest
from app.classifier.detector import Classifier
from app.engine.regex import SafeRegexParser
from app.engine.json_parser import GenericJSONParser


def test_corrupted_json_payload():
    parser = GenericJSONParser()
    event = {"payload": '{"user": "alice", "action": "login" ... corrupted'}
    assert parser.can_parse(event) is False


def test_malicious_redos_regex():
    with pytest.raises(ValueError, match="Potentially unsafe ReDoS regex"):
        SafeRegexParser(
            parser_id="malicious-regex",
            name="Malicious ReDoS",
            version="1.0.0",
            patterns=[r"(a+)+$"],
        )


def test_payload_size_limit():
    parser = SafeRegexParser(
        parser_id="size-limit-test",
        name="Size Limit Test",
        version="1.0.0",
        patterns=[r"test"],
        max_payload_bytes=100,
    )
    huge_payload = "a" * 500
    event = {"payload": huge_payload}
    assert parser.can_parse(event) is False
    with pytest.raises(ValueError, match="Payload size exceeds"):
        parser.parse(event)


def test_unknown_corrupted_format():
    classifier = Classifier()
    res = classifier.classify("!!!???CORRUPTED_RAW_TEXT_XYZ123???!!!")
    assert res.format == "plain_text"
    assert res.vendor == "Unknown"
    assert res.confidence < 0.50
