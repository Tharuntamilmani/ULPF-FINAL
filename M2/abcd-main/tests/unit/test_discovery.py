from app.discovery import UnknownSourceDiscoveryEngine


def test_unknown_source_discovery():
    engine = UnknownSourceDiscoveryEngine()
    raw_payload = """
device=ACME-FW-01
src_addr=10.0.0.5
dst_addr=8.8.8.8
src_prt=51234
dst_prt=443
decision=permit
    """.strip()

    res = engine.discover(raw_payload)

    assert res["discovery"]["format"] == "kv"
    assert res["discovery"]["confidence"] >= 0.80

    fields = res["detected_fields"]
    assert fields["device"] == "ACME-FW-01"
    assert fields["src_addr"] == "10.0.0.5"
    assert fields["dst_addr"] == "8.8.8.8"
    assert fields["src_prt"] == 51234
    assert fields["dst_prt"] == 443
    assert fields["decision"] == "permit"

    suggestions = res["suggestions"]
    assert suggestions["src_addr"] == "source.ip"
    assert suggestions["dst_addr"] == "destination.ip"
    assert suggestions["src_prt"] == "source.port"
    assert suggestions["dst_prt"] == "destination.port"
    assert suggestions["decision"] == "event.action"
