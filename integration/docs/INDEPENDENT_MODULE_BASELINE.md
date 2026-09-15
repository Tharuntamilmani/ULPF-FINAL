# ULPF Phase 0 — Independent Module Execution Baseline

**Audit Date**: September 14, 2026  
**Execution Environment**: Windows 11 Enterprise, Python 3.12.10 (Host), Python 3.12.13 (Venvs)  
**Methodology**: Direct command-line invocation of test suites, linters, typecheckers, and health checks with zero source modifications.

---

## 1. Summary of Empirical Test Results

| Module | Test Command | Tests Run | Tests Passed | Tests Failed | Exit Code | Duration | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M1** | `pytest -v tests/` | 43 | 43 | 0 | 0 | 5.73s | **PASSED** |
| **M2** | `pytest -v tests/` | 52 | 52 | 0 | 0 | 2.89s | **PASSED** |
| **M3** | `pytest -v` | 248 | 248 | 0 | 0 | 14.15s | **PASSED** |
| **M4** | `pytest -v` | 122 | 122 | 0 | 0 | 10.99s | **PASSED** |
| **M5** | `pytest -v` & `python run_tests.py` | 44 (pytest) / 20 (runner) | 44 / 20 | 0 | 0 | 2.46s | **PASSED** |
| **M6** | `pytest -v tests` | 163 | 163 | 0 | 0 | 425.91s | **PASSED** |
| **Total** | **Combined Execution** | **672 tests** | **672** | **0** | **0** | **462.13s** | **100% PASS** |

---

## 2. Forensic Module Baselines

### 2.1 Module 1: Ingestion & Raw Evidence Preservation
- **Execution Target**: `E:\ULPF\M1\modules\m1-ingestion`
- **Environment**: Dedicated `.venv` (Python 3.12.13)
- **Unit & Integration Tests**:
  - Command: `& .venv\Scripts\python.exe -m pytest -v tests/`
  - Output: `============================= 43 passed in 5.73s =============================`
  - Exit Code: `0`
  - Key Validations:
    - RFC 9562 UUIDv7 sortable ID generation and uniqueness verified.
    - Exact byte SHA-256 calculation verified for ASCII, LF, CRLF, UTF-8 Unicode, and arbitrary binary byte payloads.
    - Dual-write failure handling: verified graceful fallback to local SQLite outbox when Kafka is offline.
    - Request payload size boundary verified (2 MB accepted, 2 MB + 1 Byte rejected with HTTP 413).
- **Code Quality Gates**:
  - Linting: `ruff check .` $\to$ `All checks passed!` (0 errors).
  - Formatting: `ruff format --check .` $\to$ `44 files already formatted`.
- **Operational Endpoints**:
  - `/health`: Exposes JSON `{"status": "healthy"}`.
  - `/ready`: Reports connectivity to MinIO vault and Kafka producer.
  - `/metrics`: Emits Prometheus counters for bytes ingested, events processed, and outbox depth.

### 2.2 Module 2: Format Classifier & Parser Engine
- **Execution Target**: `E:\ULPF\M2\abcd-main`
- **Environment**: System Python 3.12.10
- **Unit & Integration Tests**:
  - Command: `python -m pytest -v tests/`
  - Output: `======================= 52 passed, 2 warnings in 2.89s ========================`
  - Exit Code: `0`
  - Key Validations:
    - Format detection: successfully classifies JSON, Syslog, CEF, LEEF, Key=Value, and plain text.
    - Golden log suites: 100% field extraction match for Cisco ASA, Fortinet FortiGate, Linux Auth, CEF, LEEF, and generic JSON.
    - Security: ReDoS regex vulnerability rejection verified; payload limits ($>1\text{ MB}$) rejected.
    - Multi-Tenancy: parser scoping by `tenant_id` verified.
- **Operational Endpoints**:
  - `/health`: Liveness probe returning `{"status": "healthy", "service": "m2-parser", "registry_size": 15}`.
  - `/metrics`: Emits `ulpf_parser_events_total`, `ulpf_parser_latency_seconds`, etc.

### 2.3 Module 3: Universal Event Schema (UES) Normalizer
- **Execution Target**: `E:\ULPF\M3`
- **Environment**: System Python 3.12.10
- **Unit & Property Tests**:
  - Command: `python -m pytest -v`
  - Output: `============================ 248 passed in 14.15s =============================`
  - Exit Code: `0`
  - Key Validations:
    - Property-based testing via Hypothesis: verified action and outcome normalizers never crash on arbitrary unicode inputs.
    - Structural validation: validated against JSON Schema Draft 2020-12 for all canonical event types (network, authentication, security, system).
    - Immutable provenance: verified `provenance.raw_event_id` is mandatory and cannot be empty or altered.
    - Vendor preservation: unmapped fields cleanly stored in `vendor.fields`.
- **Operational Endpoints**:
  - `/v1/schema`: Serves the complete canonical JSON schema.
  - `/health`: Verified liveness probe.
  - `/ready`: Verified readiness probe.
  - `/metrics`: Emits `normalization_events_total`, `normalization_successes_total`, etc.

### 2.4 Module 4: Enrichment, Provenance & Integrity
- **Execution Target**: `E:\ULPF\M4`
- **Environment**: System Python 3.12.10
- **Unit & Security Tests**:
  - Command: `python -m pytest -v`
  - Output: `============================ 122 passed in 10.99s =============================`
  - Exit Code: `0`
  - Key Validations:
    - Cryptographic Integrity: RFC 8785 Canonical JSON (JCS) determinism verified across 100 consecutive runs and different object key orders.
    - Preservation Invariants: Proves that `event.id`, `event.timestamp`, `provenance.raw_event_id`, and network endpoints cannot be modified by enrichment.
    - SSRF Guard: Verified that loopback, RFC 1918 subnets, cloud metadata (`169.254.169.254`), and non-HTTP protocols are blocked.
    - Tenant Isolation: Verified cache key partitioning (`tenant_id:provider_id:namespace:key`) and cross-tenant execution rejection.
- **Operational Endpoints**:
  - `/v1/enrich`: Core enrichment route.
  - `/v1/verify`: Cryptographic signature verification.
  - `/health`: Liveness probe.
  - `/metrics`: Emits `m4_enrichment_events_total`, `m4_integrity_verifications_total`.

### 2.5 Module 5: Smart Router & Multi-Destination Delivery
- **Execution Target**: `E:\ULPF\M5`
- **Environment**: System Python 3.12.10
- **Unit, Connector, & Integration Tests**:
  - Command: `python run_tests.py` & `python -m pytest -v`
  - Output: `============================= 44 passed in 2.46s ==============================`
  - Exit Code: `0`
  - Key Validations:
    - Policy Engine: verified multi-condition tree evaluation (`all`, `any`, nested expressions).
    - Multi-destination delivery: verified simultaneous routing to OpenSearch SIEM, Partitioned JSONL Data Lake, and Kafka AI stream.
    - Failure handling: verified retry loop with exponential backoff and DLQ promotion upon exhaustion.
    - Idempotency: verified duplicate event delivery does not duplicate data lake records (LRU deduplication).
- **Operational Endpoints**:
  - `/v1/events/process`: Main routing endpoint.
  - `/api/v1/search`: Tenant-isolated event search.
  - `/health`, `/ready`, `/metrics`: Comprehensive probes.

### 2.6 Module 6: Control Plane & Registries
- **Execution Target**: `E:\ULPF\M6\M6-SIH-main`
- **Environment**: Dedicated `.venv` (Python 3.12.13)
- **Unit, Contract & Integration Tests**:
  - Command: `& .venv\Scripts\python.exe -m pytest -v tests`
  - Output: `======================= 163 passed in 425.91s (0:07:05) =======================`
  - Exit Code: `0`
  - Code Coverage: 76% across 3,472 statements.
  - Key Validations:
    - Contract schemas: verified JSON Schema contracts in `contracts/` for M1, M2, M3, M4, M5.
    - Registries: Source, Parser, Schema, Mapping, and Policy registries tested with full CRUD operations.
    - Security & RBAC: JWT issuance and 4 RBAC role permission checks verified.
    - Config distribution: verified generation of distribution payload for downstream modules.
- **Operational Endpoints**:
  - `/api/v1/health`: Aggregated platform status.
  - `/metrics`: Centralized Prometheus metric exporter.

---

## 3. Independent Baseline Takeaway

Every individual ULPF module is robust, well-tested, and internally consistent within its isolated test harness.
**However**, as revealed in subsequent contract analysis, the modules were tested against *mocked assumptions* of neighboring contracts rather than the *actual implementations* of those neighbors. The individual pass rates do **not** imply system-level interoperability.
