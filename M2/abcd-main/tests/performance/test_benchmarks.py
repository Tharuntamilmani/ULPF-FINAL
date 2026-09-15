import time
from app.classifier.detector import Classifier
from app.engine.kv import GenericKVParser


def test_classifier_performance_benchmark():
    classifier = Classifier()
    payload = "<189>Sep 12 04:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443"

    # Warmup
    for _ in range(10):
        classifier.classify(payload)

    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        classifier.classify(payload)
    total_sec = time.perf_counter() - start
    avg_ms = (total_sec / iterations) * 1000

    print(f"\nAverage Classification Latency: {avg_ms:.4f} ms")
    assert avg_ms < 1.0, (
        f"Classification latency exceeded 1 ms threshold: {avg_ms:.4f} ms"
    )


def test_kv_parsing_performance_benchmark():
    parser = GenericKVParser()
    payload = 'src_addr=192.168.1.1 dst_addr=8.8.8.8 src_port=51234 dst_port=443 decision="permit access" devname="FW-01" devid="FG100D"'
    event = {"payload": payload}

    iterations = 1000
    start = time.perf_counter()
    for _ in range(iterations):
        parser.parse(event)
    total_sec = time.perf_counter() - start
    avg_ms = (total_sec / iterations) * 1000

    print(f"\nAverage KV Parsing Latency: {avg_ms:.4f} ms")
    assert avg_ms < 2.0, f"Parsing latency exceeded 2 ms threshold: {avg_ms:.4f} ms"
