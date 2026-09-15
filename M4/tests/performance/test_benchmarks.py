"""Performance and latency benchmark tests for ULPF M4."""

import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from app.cache.memory_lru import MemoryLRUCache
from app.config.lifecycle import ConfigurationManager
from app.contracts.canonical_event import CanonicalEvent
from app.contracts.enrichment_contract import EnrichmentRequest
from app.enrichment.engine import EnrichmentEngine
from app.models.tenant import TenantContext
from app.providers.asset_provider import LocalAssetProvider
from app.providers.geoip_provider import LocalGeoIPProvider
from app.providers.registry import ProviderRegistry
from app.providers.threat_intel_provider import LocalThreatIntelProvider


def build_perf_engine() -> EnrichmentEngine:
    reg = ProviderRegistry()
    reg.register(LocalAssetProvider())
    reg.register(LocalGeoIPProvider())
    reg.register(LocalThreatIntelProvider())
    return EnrichmentEngine(reg, ConfigurationManager(), MemoryLRUCache(max_size=20000))


def test_perf_single_event_latency(sample_canonical_event: CanonicalEvent) -> None:
    """Benchmark single event enrichment latency (target: < 25ms cold)."""
    engine = build_perf_engine()
    ctx = TenantContext(tenant_id="tenant_alpha")
    req = EnrichmentRequest(event=sample_canonical_event, tenant_context=ctx)

    start = time.perf_counter()
    result = engine.process(req)
    duration_ms = (time.perf_counter() - start) * 1000.0

    assert result.status.value == "SUCCESS"
    assert duration_ms < 50.0  # Generous upper bound for single event cold run


def test_perf_batch_100_events_throughput(sample_canonical_event: CanonicalEvent) -> None:
    """Benchmark throughput and P50/P95/P99 latency across 100 sequential events."""
    engine = build_perf_engine()
    ctx = TenantContext(tenant_id="tenant_alpha")

    latencies: list[float] = []
    start_all = time.perf_counter()

    for i in range(100):
        evt = sample_canonical_event.model_copy(deep=True)
        evt.event.id = f"EVT-BATCH-100-{i:04d}"
        req = EnrichmentRequest(event=evt, tenant_context=ctx)

        t0 = time.perf_counter()
        res = engine.process(req)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        assert res.status.value == "SUCCESS"

    total_time = time.perf_counter() - start_all
    throughput = 100 / total_time
    p50 = float(np.percentile(latencies, 50))
    p95 = float(np.percentile(latencies, 95))
    p99 = float(np.percentile(latencies, 99))

    assert throughput > 50.0  # Must exceed 50 events/sec sequentially
    assert p50 < 15.0
    assert p95 < 30.0
    assert p99 < 50.0


def test_perf_batch_1000_events_warm_cache(sample_canonical_event: CanonicalEvent) -> None:
    """Benchmark high-throughput warm cache performance across 1,000 events."""
    engine = build_perf_engine()
    ctx = TenantContext(tenant_id="tenant_alpha")

    # Prime cache
    req_prime = EnrichmentRequest(event=sample_canonical_event, tenant_context=ctx)
    engine.process(req_prime)

    start_all = time.perf_counter()
    for i in range(1000):
        evt = sample_canonical_event.model_copy(deep=True)
        evt.event.id = f"EVT-WARM-1000-{i:04d}"
        req = EnrichmentRequest(event=evt, tenant_context=ctx)
        res = engine.process(req)
        assert res.status.value == "SUCCESS"

    total_time = time.perf_counter() - start_all
    throughput = 1000 / total_time
    # Warm cache should achieve very high throughput (> 200 events/sec)
    assert throughput > 200.0


def test_perf_concurrent_threadpool_stress(sample_canonical_event: CanonicalEvent) -> None:
    """Stress test engine with 8 concurrent threads processing 200 events total."""
    engine = build_perf_engine()
    ctx = TenantContext(tenant_id="tenant_alpha")

    def worker(idx: int) -> bool:
        evt = sample_canonical_event.model_copy(deep=True)
        evt.event.id = f"EVT-CONCURRENT-{idx:04d}"
        req = EnrichmentRequest(event=evt, tenant_context=ctx)
        res = engine.process(req)
        return res.status.value == "SUCCESS"

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(worker, range(200)))

    assert all(results)
    assert len(results) == 200


def test_perf_memory_stability_leak_check(sample_canonical_event: CanonicalEvent) -> None:
    """Verify memory stability across repeated pipeline cycles."""
    engine = build_perf_engine()
    ctx = TenantContext(tenant_id="tenant_alpha")

    tracemalloc.start()
    # Warm up
    for _ in range(50):
        evt = sample_canonical_event.model_copy(deep=True)
        engine.process(EnrichmentRequest(event=evt, tenant_context=ctx))

    snapshot1 = tracemalloc.take_snapshot()

    # Process 300 events
    for i in range(300):
        evt = sample_canonical_event.model_copy(deep=True)
        evt.event.id = f"EVT-MEM-{i:04d}"
        engine.process(EnrichmentRequest(event=evt, tenant_context=ctx))

    snapshot2 = tracemalloc.take_snapshot()
    tracemalloc.stop()

    top_stats = snapshot2.compare_to(snapshot1, "lineno")
    total_diff_kb = sum(stat.size_diff for stat in top_stats) / 1024.0

    # Memory growth should be contained (less than 20MB for 300 events)
    assert total_diff_kb < 20480.0
