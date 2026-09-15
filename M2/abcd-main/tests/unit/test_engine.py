from app.engine.json_parser import GenericJSONParser
from app.engine.kv import GenericKVParser
from app.engine.cef import CEFParser
from app.engine.leef import LEEFParser
from app.engine.grok import GrokParser


def test_json_parser():
    parser = GenericJSONParser()
    event = {"payload": '{"user": {"id": 123, "name": "alice"}, "action": "login"}'}
    assert parser.can_parse(event)
    fields = parser.parse(event)
    assert fields["user.id"] == 123
    assert fields["user.name"] == "alice"
    assert fields["action"] == "login"


def test_kv_parser():
    parser = GenericKVParser()
    event = {
        "payload": 'src_addr=192.168.1.1 dst_addr=8.8.8.8 src_port=51234 dst_port=443 decision="permit access"'
    }
    assert parser.can_parse(event)
    fields = parser.parse(event)
    assert fields["src_addr"] == "192.168.1.1"
    assert fields["dst_addr"] == "8.8.8.8"
    assert fields["src_port"] == 51234
    assert fields["dst_port"] == 443
    assert fields["decision"] == "permit access"


def test_cef_parser():
    parser = CEFParser()
    event = {
        "payload": "CEF:0|CheckPoint|Firewall|R80|300|Packet Filter|High|src=1.2.3.4 dst=5.6.7.8 spt=1234 dpt=80 act=drop"
    }
    assert parser.can_parse(event)
    fields = parser.parse(event)
    assert fields["device_vendor"] == "CheckPoint"
    assert fields["src"] == "1.2.3.4"
    assert fields["dst"] == "5.6.7.8"
    assert fields["act"] == "drop"


def test_leef_parser():
    parser = LEEFParser()
    event = {
        "payload": "LEEF:1.0|Microsoft|MSExchange|2016|1001|src=10.0.0.5 dst=10.0.0.10 action=allow"
    }
    assert parser.can_parse(event)
    fields = parser.parse(event)
    assert fields["vendor"] == "Microsoft"
    assert fields["src"] == "10.0.0.5"
    assert fields["action"] == "allow"


def test_grok_parser():
    pattern = (
        "%{IP:srcip}:%{INT:srcport} -> %{IP:dstip}:%{INT:dstport} action=%{WORD:action}"
    )
    parser = GrokParser(
        parser_id="grok-test", name="Grok Test", version="1.0.0", patterns=[pattern]
    )
    event = {"payload": "192.168.10.5:51234 -> 8.8.8.8:443 action=permit"}
    assert parser.can_parse(event)
    fields = parser.parse(event)
    assert fields["srcip"] == "192.168.10.5"
    assert fields["srcport"] == 51234
    assert fields["dstip"] == "8.8.8.8"
    assert fields["dstport"] == 443
    assert fields["action"] == "permit"
