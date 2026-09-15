from app.classifier.detector import Classifier


def test_classifier_json():
    classifier = Classifier()
    payload = '{"event": "login", "user": "admin", "src_ip": "10.0.0.1"}'
    res = classifier.classify(payload)
    assert res.format == "json"
    assert res.confidence >= 0.70


def test_classifier_cisco_asa():
    classifier = Classifier()
    payload = "<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443"
    res = classifier.classify(payload)
    assert res.format == "syslog"
    assert res.vendor == "Cisco"
    assert res.product == "ASA"
    assert res.confidence >= 0.85


def test_classifier_fortinet():
    classifier = Classifier()
    payload = 'date=2026-09-12 time=04:00:15 devname="FG100D" devid="FG100D3G15000001" type=traffic action="allow" srcip=192.168.1.5 dstip=8.8.8.8'
    res = classifier.classify(payload)
    assert res.format == "kv"
    assert res.vendor == "Fortinet"
    assert res.product == "FortiGate"
    assert res.confidence >= 0.85


def test_classifier_cef():
    classifier = Classifier()
    payload = "CEF:0|Security|ThreatManager|1.0|100|Worm Detected|10|src=10.0.0.1 dst=10.0.0.2 act=blocked"
    res = classifier.classify(payload)
    assert res.format == "cef"
    assert res.confidence >= 0.70


def test_classifier_leef():
    classifier = Classifier()
    payload = (
        "LEEF:2.0|Vendor|Product|1.0|1001|\t|src=10.0.0.1\tdst=10.0.0.2\taction=allow"
    )
    res = classifier.classify(payload)
    assert res.format == "leef"
    assert res.confidence >= 0.70
