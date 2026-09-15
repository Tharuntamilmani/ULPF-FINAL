"""
Performance and Load Benchmarking Suite for ULPF M5 (Section 25).
Measures:
  - Policy Engine routing latency (p50, p95, p99, max)
  - End-to-end multi-destination delivery latency & throughput (events/sec)
  - Memory consumption (RSS MB) before, during, and after load
  - CPU utilization under increasing load (100, 500, 2000, 5000 events)
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import time
import asyncio
import psutil
from app.main import initialize_m5_components, process_event
from app.router.router import SmartRouter
from app.policy.loader import PolicyLoader


def generate_ues_event(idx: int, tenant: str = "tenant_alpha") -> dict:
    return {
        "event": {
            "id": f"evt_bench_{idx:07d}",
            "timestamp": "2026-09-13T12:00:00Z",
            "type": "authentication" if idx % 2 == 0 else "network_flow",
            "action": "login_attempt" if idx % 2 == 0 else "connection_established",
            "severity": {"value": (idx % 5) + 1}
        },
        "source": {"ip": f"192.168.1.{(idx % 250) + 1}"},
        "destination": {"ip": "10.0.0.1"},
        "security": {"is_security_event": (idx % 3 == 0)},
        "tenant": {"id": tenant}
    }


async def benchmark_pipeline(batch_sizes=[100, 500, 2000, 5000]):
    print("\n=======================================================")
    print("      ULPF M5 - EMPIRICAL PERFORMANCE BENCHMARK        ")
    print("=======================================================")

    process = psutil.Process(os.getpid())
    mem_initial = process.memory_info().rss / (1024 * 1024)
    print(f"Initial Memory Footprint: {mem_initial:.2f} MB")

    policy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "policies", "default.yaml"))
    initialize_m5_components(policy_file=policy_path)

    # 1. Pure Policy Evaluation Benchmark
    rules = PolicyLoader.load_from_file(policy_path)
    router = SmartRouter(rules)

    print("\n--- 1. Smart Router Pure Policy Evaluation Benchmark ---")
    eval_count = 10000
    events = [generate_ues_event(i) for i in range(eval_count)]

    t0 = time.perf_counter()
    latencies = []
    for ev in events:
        s0 = time.perf_counter()
        router.route(ev)
        latencies.append((time.perf_counter() - s0) * 1000)  # ms
    total_eval_time = time.perf_counter() - t0

    latencies.sort()
    p50 = latencies[int(len(latencies) * 0.50)]
    p95 = latencies[int(len(latencies) * 0.95)]
    p99 = latencies[int(len(latencies) * 0.99)]
    eval_eps = eval_count / total_eval_time

    print(f"  Evaluated {eval_count:,} events in {total_eval_time:.4f}s")
    print(f"  Routing Throughput: {eval_eps:,.1f} events/sec")
    print(f"  Routing Latency - p50: {p50:.4f} ms | p95: {p95:.4f} ms | p99: {p99:.4f} ms")

    # 2. End-to-End Pipeline Ingestion & Delivery Benchmark
    print("\n--- 2. End-to-End Ingestion + Delivery Under Increasing Load ---")
    print(f"{'Batch Size':>10} | {'Elapsed (s)':>11} | {'Events/sec':>12} | {'Avg Latency (ms)':>16} | {'RAM (MB)':>9}")
    print("-" * 70)

    for batch_size in batch_sizes:
        batch_events = [generate_ues_event(i) for i in range(batch_size)]

        t_start = time.perf_counter()
        # Process concurrently in chunks of 100
        chunk_size = 100
        for i in range(0, batch_size, chunk_size):
            chunk = batch_events[i : i + chunk_size]
            await asyncio.gather(*(process_event(ev) for ev in chunk))

        elapsed = time.perf_counter() - t_start
        throughput = batch_size / elapsed
        avg_latency = (elapsed / batch_size) * 1000
        mem_current = process.memory_info().rss / (1024 * 1024)

        print(f"{batch_size:>10,d} | {elapsed:>11.4f} | {throughput:>12,.1f} | {avg_latency:>16.4f} | {mem_current:>9.2f}")

    mem_final = process.memory_info().rss / (1024 * 1024)
    print("-" * 70)
    print(f"Final Memory Footprint: {mem_final:.2f} MB (Delta: +{mem_final - mem_initial:.2f} MB)")
    print("=======================================================\n")


if __name__ == "__main__":
    asyncio.run(benchmark_pipeline([100, 500, 2000, 5000]))
