# ULPF Phase 0 — Inter-Module Test Gap Matrix

**Audit Date**: September 14, 2026  
**Status**: Complete  
**Scope**: Coverage evaluation across all system boundaries for contract, integration, end-to-end, failure, security, multi-tenancy, and performance testing.

---

## 1. Boundary Test Coverage Evaluation

| Boundary | Contract Tests Exist? | Integration Tests Exist? | E2E Tests Exist? | Failure & Chaos Tests Exist? | Security / Adversarial Tests Exist? | Multi-Tenant Isolation Tests Exist? | Performance Benchmarks Exist? | Overall Test Maturity |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M1 $\to$ M2** | **MOCK ONLY** (Tests use idealized M2 models) | **NO** (No live Kafka consumer tested) | **NO** | **NO** (Kafka outage tested inside M1 only) | **PARTIAL** (Raw byte integrity tested in M1) | **NO** (Header spoofing not tested across boundary) | **NO** | **CRITICAL GAP** |
| **M2 $\to$ M3** | **MOCK ONLY** (Tests construct artificial ParsedEvent) | **NO** (Tested in isolation) | **NO** | **NO** | **NO** | **NO** (Tenant dropping not caught by tests) | **NO** | **CRITICAL GAP** |
| **M3 $\to$ M4** | **NONE** (Zero shared contract tests) | **NO** | **NO** | **NO** | **NO** (SSRF tested inside M4 only) | **NO** (Missing tenant not tested) | **NO** | **CRITICAL GAP** |
| **M4 $\to$ M5** | **NONE** (Zero shared contract tests) | **NO** | **NO** | **NO** (DLQ tested inside M5 only) | **NO** | **NO** (Tenant key mismatch not tested) | **NO** | **CRITICAL GAP** |
| **M6 $\to$ M1-M5** | **MOCK ONLY** (M6 tests mock HTTP client) | **NO** (Never tested against live M1–M5) | **NO** | **NO** | **NO** | **NO** | **NO** | **CRITICAL GAP** |

---

## 2. Detailed Gap Analysis by Test Category

### 2.1 Contract Tests
- **Current State**: Modules test contracts against internal Pydantic models. For example, M2's `test_m1_m2_contracts.py` imports `M2.app.models.envelope.RawEventEnvelope`, creating a mock event with `transport="syslog"` and `payload="string"`. It never imports or serializes against `M1.app.envelope.models.RawEventEnvelope` (which has nested dicts for `transport` and `payload`).
- **Gap**: Zero live cross-module serialization/deserialization verification.

### 2.2 Integration & E2E Pipeline Tests
- **Current State**: Not a single test file in the entire repository ingests an event into M1, routes it through M2, normalizes it through M3, enriches it through M4, and verifies its delivery to OpenSearch or the Data Lake in M5.
- **Gap**: Total absence of an automated end-to-end integration test harness.

### 2.3 Failure & Resilience Tests
- **Current State**:
  - M1 tests Kafka outage with its SQLite outbox fallback.
  - M5 tests OpenSearch failure with retry and DLQ promotion.
- **Gap**: No tests verify what happens when an intermediate microservice crashes (e.g. M3 down while M2 is processing, or M4 timeout while M3 is streaming).

### 2.4 Multi-Tenant Boundary Tests
- **Current State**:
  - M1 has `SEC-1.4` (header spoofing) documented as an audit finding.
  - M2 tests parser lookup by tenant.
  - M4 tests cache isolation by tenant.
  - M5 tests query isolation by tenant.
- **Gap**: No test verifies end-to-end tenant preservation (`Tenant A` at M1 remaining `Tenant A` in M5's data lake partition). This allowed the critical bug where M3 drops `tenant_id` to remain undetected.

### 2.5 Performance & Throughput Tests
- **Current State**:
  - M1 benchmarked file replay memory (tracemalloc).
  - M2 benchmarked regex classification (~0.15 ms).
  - M3 benchmarked normalization latency (~1.5 ms).
  - M4 benchmarked concurrent threadpool throughput.
  - M5 benchmarked policy routing throughput (~17,652 events/sec).
- **Gap**: No end-to-end pipeline throughput or latency benchmark exists under realistic streaming load.
