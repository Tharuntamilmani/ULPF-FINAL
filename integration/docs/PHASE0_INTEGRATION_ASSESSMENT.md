# ULPF Phase 0 — Comprehensive Integration Assessment Report

**System**: Universal Log Preprocessing Framework (ULPF)  
**Modules Audited**: M1, M2, M3, M4, M5, M6  
**Auditor**: Antigravity Autonomous Systems Engineering & Forensic Integration Team  
**Date**: September 14, 2026  
**Status**: Phase 0 Complete — Awaiting Phase 1 Integration Plan Approval  

---

## Executive Summary

The Universal Log Preprocessing Framework (ULPF) comprises six independently developed, specialized cybersecurity pipeline modules:
- **M1**: Ingestion Gateway & Immutable Raw Evidence Vault
- **M2**: Format Classifier, Parser Engine & Unknown-Source Discovery
- **M3**: Canonical Universal Event Schema (UES v1.0.0) Normalizer & Validator
- **M4**: Contextual Enrichment, Provenance Lineage & RFC 8785 Cryptographic Integrity
- **M5**: Policy Engine, Smart Router & Multi-Destination Egress Delivery
- **M6**: Control Plane, Registry Hub, RBAC & Observability

In Phase 0, a strict, non-destructive forensic audit and independent execution baseline was conducted across all six repositories. **Zero source code modifications, refactoring, package merging, or premature integration adapters were introduced.**

### Independent Quality vs. System Interoperability
Independently, each module is an exceptionally high-quality software component. All **672 individual module tests pass with a 100% success rate** (M1: 43/43, M2: 52/52, M3: 248/248, M4: 122/122, M5: 44/44, M6: 163/163).

**However, the live end-to-end system is currently completely inoperable without an integration layer.**
The individual test suites passed because every module was tested against *mocked assumptions* of its neighbors' contracts rather than the *actual live implementations*. The audit uncovered **three critical P0 contract blockers**, **four high P1 functional/security gaps**, and a **transport protocol disconnect** that prevent direct event flow.

---

## 1. System Architecture Discovered

The runtime event pipeline follows a 5-stage sequential processing flow supervised by a centralized control plane:

```
[External Sources]
       │ (HTTP, UDP:514, TCP:515, File Replay)
       ▼
   ┌───────┐
   │  M1   │──(Raw Gzip Blobs)──► [MinIO S3 Vault: ulpf-raw]
   └───┬───┘
       │ (Kafka: ulpf.raw) [DISCONNECT: M2 has no Kafka consumer daemon]
       ▼
   ┌───────┐
   │  M2   │──(Parser Studio / Discovery)
   └───┬───┘
       │ (HTTP POST /v1/normalize)
       ▼
   ┌───────┐
   │  M3   │──(UES Draft 2020-12 Validation)
   └───┬───┘
       │ (HTTP POST /v1/enrich) [BLOCKER: M3 wraps in {"ulpf":...}, M4 forbids extra keys]
       ▼
   ┌───────┐
   │  M4   │──(RFC 8785 JCS + SHA-256 Digest)
   └───┬───┘
       │ (HTTP POST /v1/events/process) [GAP: Tenant key mismatch tenant_id vs id]
       ▼
   ┌───────┐
   │  M5   │──► [OpenSearch SIEM: ulpf-events-v1-{tenant}]
   └───┬───┘──► [Data Lake: ./data/datalake/.../events.jsonl]
       │      ──► [Kafka AI Stream: ulpf.ai.events]
       └──────► [Dead Letter Queue: ./data/dlq/dlq_events.jsonl]

   ┌───────────────────────────────────────────────────────────┐
   │                   M6 CONTROL PLANE                        │
   │  PostgreSQL (Registries) · Redis (Cache) · JWT Auth/RBAC  │
   │  Polls /health of M1–M5 · Manual Config Distribute        │
   └───────────────────────────────────────────────────────────┘
```

---

## 2. Module Inventory

| Module | Filesystem Path | Primary Role | Tech Stack | Default Port | Internal DB | Baseline Test Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M1** | `E:\ULPF\M1\modules\m1-ingestion` | Raw Byte Ingestion & Vault | Python 3.12, FastAPI, aiokafka, MinIO, SQLite | 8000, 514, 515 | MinIO, SQLite | 43 / 43 Pass (5.73s) |
| **M2** | `E:\ULPF\M2\abcd-main` | Classification & Parsing | Python 3.12, FastAPI, Grok, Regex, orjson | 8082 | In-memory YAML | 52 / 52 Pass (2.89s) |
| **M3** | `E:\ULPF\M3` | Canonical Normalization | Python 3.12, FastAPI, JSON Schema, React/Vite | 8083 (API), 5173 (UI) | In-memory YAML | 248 / 248 Pass (14.15s)|
| **M4** | `E:\ULPF\M4` | Contextual Enrichment & JCS | Python 3.12, FastAPI, RFC 8785, SSRFGuard | 8004 | In-memory LRU | 122 / 122 Pass (10.99s)|
| **M5** | `E:\ULPF\M5` | Smart Routing & SIEM Egress | Python 3.12, FastAPI, OpenSearch, Kafka | 8085 | JSONL Lake, DLQ | 44 / 44 Pass (2.46s) |
| **M6** | `E:\ULPF\M6\M6-SIH-main` | Control Plane & Registries | Python 3.12, FastAPI, PostgreSQL, Redis, React | 8000 (API), 5173 (UI) | PostgreSQL, Redis | 163 / 163 Pass (425.9s)|

---

## 3. Actual Contracts Extracted

### 3.1 M1 Emitted Contract: `RawEventEnvelope`
- `schema_version`: `"1.0.0"`
- `raw_event_id`: UUIDv7 string (e.g. `0191eb54-3e91-723a-8b5e-17cf3b2a8190`)
- `tenant_id`: string
- `source_id`: string
- `source_type`: string (`firewall`)
- `received_at`: ISO 8601 UTC string
- `transport`: `{"protocol": "udp", "port": 514}` (Object)
- `payload`: `{"encoding": "utf-8", "format_hint": "syslog", "data": "..."}` (Object)
- `integrity`: `{"algorithm": "SHA-256", "hash": "..."}` (Object)
- `raw_storage`: `{"backend": "minio", "bucket": "ulpf-raw", "object_key": "..."}` (Object)

### 3.2 M2 Expected Contract: `RawEventEnvelope` vs Emitted Contract: `ParsedEvent`
- **Expected Inbound**: Flat structure: `payload: str`, `transport: str`, `sha256: str`, `raw_reference: str`.
- **Emitted Outbound (`ParsedEvent`)**:
  - `schema_version`: `"1.0.0"`
  - `raw_event_id`: string
  - `tenant_id`: string
  - `source_id`: Optional[str]
  - `status`: `"PARSED"` | `"UNPARSED"` | `"FAILED"`
  - `classification`: `{"format": "syslog", "vendor": "Cisco", "product": "ASA", "confidence": 0.99}`
  - `parser`: `{"id": "parser-cisco-asa", "name": "...", "version": "1.2.0", "confidence": 1.0}`
  - `fields`: `{"srcip": "192.168.1.100", "dstip": "10.0.0.5", "action": "allow", ...}`
  - `unmapped_fields`: list[str]
  - `sha256`: Optional[str]
  - `raw_reference`: Optional[str]

### 3.3 M3 Expected Contract: `ParsedEvent` vs Emitted Contract: `UES`
- **Expected Inbound**: `ParsedEvent` with `raw_event_id`, `classification`, `parser`, `fields`. Accepts extra keys (`extra="allow"`).
- **Emitted Outbound (`NormalizationResult.event`)**:
  - Encapsulated strictly under top-level key `"ulpf"`:
  ```json
  {
    "ulpf": {
      "schema": { "version": "1.0.0", "specification": "UES" },
      "event": { "id": "uuid", "timestamp": "...", "kind": "event", "type": "network", ... },
      "observer": { "vendor": "Cisco", "product": "ASA" },
      "source": { "ip": "192.168.1.100", "port": 49152 },
      "destination": { "ip": "10.0.0.5", "port": 80 },
      "network": { "transport": "TCP" },
      "provenance": { "raw_event_id": "0191eb54..." },
      "vendor": { "fields": { ... } }
    }
  }
  ```
  - **Notice**: Contains **no `tenant` property**.

### 3.4 M4 Expected Contract: `EnrichmentRequest` vs Emitted Contract: `EnrichmentResult`
- **Expected Inbound (`CanonicalEvent`)**:
  - Flat model with `extra="forbid"`:
    - `schema_version`: `"ues.v1"`
    - `event`: `EventMetadata` (`id`, `timestamp`, `kind`, `type`, `outcome`)
    - `source`, `destination`, `network`, `observer`, `host`, `identity`
    - `provenance`: `ProvenanceMetadata` (`raw_event_id`)
    - `tenant`: `TenantMetadata` (`tenant_id`)
- **Emitted Outbound (`EnrichmentResult`)**:
  - `event`: Enriched `CanonicalEvent` with added `extensions.enrichment`
  - `provenance`: Array of provider lineage objects
  - `diagnostics`: Execution timing and cache hit metrics
  - `integrity`: `IntegrityMetadata` (`algorithm="sha256"`, `digest="64-hex"`, `canonicalization="rfc8785"`)

### 3.5 M5 Expected Contract: Ingestion Payload
- Endpoint `POST /v1/events/process` accepts JSON dictionary.
- Evaluates policy against `event.id`, `event.severity`, `source.ip`, `network.protocol`, `security.*`.
- Extracts tenant via `event["tenant"]["id"]` or root `event["tenant_id"]`.

---

## 4. Contract Compatibility & Breaking Discrepancies

| Boundary | Status | Conflict Description | Impact |
| :--- | :--- | :--- | :--- |
| **M1 $\to$ M2** | **INCOMPATIBLE (P0)** | M1 emits nested objects for `payload` and `transport`. M2 Pydantic validator expects primitive strings (`payload: str`, `transport: str`). | 100% Pydantic validation failure upon ingestion into M2. |
| **M2 $\to$ M3** | **DATA LOSS (P1)** | M2 sends `tenant_id`, `source_id`, `sha256`, `raw_reference`. M3 accepts the model but completely drops all four attributes during canonical UES construction. | Tenant context and cryptographic raw hash lost at normalization. |
| **M3 $\to$ M4** | **INCOMPATIBLE (P0)** | M3 wraps output in `{"ulpf": { ... }}` and omits `tenant`. M4 enforces `extra="forbid"` and mandatory `tenant.tenant_id`. | 100% Pydantic validation failure upon ingestion into M4. |
| **M4 $\to$ M5** | **MISMATCH (P1)** | M4 provides `tenant.tenant_id`. M5 router extracts `tenant.id` or root `tenant_id`. | Tenant-specific routing policies fail to match in M5. |

---

## 5. Dependency Graph Findings

1. **Zero Direct Code Coupling**: None of the six modules import Python code from sibling modules.
2. **Zero Shared Databases**: Every module controls its own storage; no shared relational schemas or cross-module SQL joins exist.
3. **Port Collisions**:
   - Port 8000: M1 HTTP Ingestion defaults to 8000; M6 Control Plane backend defaults to 8000 in `.env.example`.
   - Port 5173: M3 Vite UI and M6 React UI both default to 5173.

---

## 6. Transport Architecture Disconnect

1. **The Kafka $\to$ HTTP Chasm**:
   - M1 publishes envelopes asynchronously to Kafka topic `ulpf.raw`.
   - M2 is implemented as a synchronous FastAPI web server (`POST /v1/parse`).
   - **Critical Gap**: There is no active consumer process reading from Kafka topic `ulpf.raw` and forwarding events to M2.
2. **Synchronous Chain**:
   - M2 $\to$ M3 $\to$ M4 $\to$ M5 are currently designed as synchronous HTTP REST microservices.
   - If M4 encounters a network timeout, the entire upstream chain blocks unless buffered by a queue.

---

## 7. Tenant Flow & Isolation Findings

1. **Ingress Vulnerability (M1 `SEC-1.4`)**: Static token authentication allows any authenticated client to spoof `X-Tenant-ID` headers, polluting other tenants' partitions.
2. **Normalization Drop (M3)**: M3 drops `tenant_id` completely.
3. **Enrichment Defense (M4)**: M4's `TenantGuard` correctly partitions cache keys and blocks cross-tenant execution, but will reject M3 events if tenant context is missing.
4. **Router Key Mismatch (M5)**: M5 fails to read `tenant.tenant_id`, dropping tenant-scoped routing rules.
5. **Control Plane Leakage (M6)**: `GET /api/v1/sources` without a tenant parameter returns all sources across all tenants to users with `VIEWER` permissions.

---

## 8. Configuration Flow & Operational Loop Findings

1. **Disconnected M6 Control Loop**:
   - M6 saves source, parser, mapping, schema, and policy updates strictly to PostgreSQL.
   - There is no automatic push to Redis or Kafka upon database commit.
   - Configuration distribution only executes when an administrator triggers `POST /api/v1/configuration/distribute`.
2. **Static Bootstrapping in Downstream Modules**:
   - M1, M3, and M5 load configurations from local files or environment variables at startup and do not subscribe to dynamic configuration topics.
3. **Missing Acknowledgment Loop**:
   - M6 has no mechanism to collect ACKs confirming that M1–M5 have successfully applied new configurations.

---

## 9. Security Trust Boundaries

1. **Boundary 1 (External $\to$ M1)**: Untrusted boundary. Enforces payload size limits (2 MB) and token check. Vulnerable to tenant spoofing.
2. **Boundary 2 (M1 $\to$ M2)**: Internal network boundary. Relies on Kafka ACLs.
3. **Boundary 3 (M2 $\to$ M3)**: Internal REST boundary. ReDoS protection active in M2; request size limits active in M3.
4. **Boundary 4 (M3 $\to$ M4)**: High-security boundary. M4 strictly validates input schemas, protects outbound HTTP lookups with `SSRFGuard`, and enforces `TenantGuard`.
5. **Boundary 5 (M4 $\to$ M5)**: Internal delivery boundary. M5 enforces tenant isolation on search and audit logs.
6. **Boundary 6 (M6 $\to$ Modules)**: Administrative control boundary. Protected by JWT and 4 RBAC roles.

---

## 10. Database Ownership

| Module | Persistence Technology | State Stored | External Access Status |
| :--- | :--- | :--- | :--- |
| **M1** | MinIO (Object Storage) & SQLite | Raw compressed blobs & pending outbox rows | Exclusive to M1 |
| **M2** | In-Memory / File YAML | Parser definitions & AST cache | Exclusive to M2 |
| **M3** | In-Memory / File YAML | UES mapping definitions | Exclusive to M3 |
| **M4** | In-Memory LRU Cache | Tenant enrichment cache & CMDB assets | Exclusive to M4 |
| **M5** | Local Filesystem JSONL | Partitioned Data Lake & Dead Letter Queue | Exclusive to M5 |
| **M6** | PostgreSQL & Redis | Relational registries, users, audit trails | Exclusive to M6 |

**Finding**: Database ownership is clean and uncoupled. No cross-database queries occur.

---

## 11. Observability Gap Analysis

1. **Prometheus Telemetry**:
   - M1, M2, M3, M4, and M5 all expose functioning `/metrics` endpoints.
   - M6 declares Prometheus metrics, but application logic in earlier versions did not increment them.
2. **Correlation & Distributed Tracing**:
   - `raw_event_id` is passed through M1 $\to$ M2 $\to$ M3 $\to$ M4 $\to$ M5, providing a natural event correlation trace ID.
   - However, HTTP headers (`X-Correlation-ID`, W3C Trace Context `traceparent`) are not standardized across HTTP calls.

---

## 12. Deployment Model Analysis

1. **Docker Containerization**:
   - M1, M2, M3, M5, and M6 each contain individual `Dockerfile` and `docker-compose.yml` configurations.
   - M4 contains local packaging files (`pyproject.toml`).
2. **Missing Unified Deployment**:
   - There is no root orchestrator bringing up the 6 modules alongside shared Kafka, MinIO, PostgreSQL, Redis, and OpenSearch services.
3. **Port Clashes**:
   - Port 8000 must be arbitrated between M1 and M6.

---

## 13. Test Gap Matrix

1. **No End-to-End Pipeline Tests**: Zero tests verify an event traveling through M1 $\to$ M2 $\to$ M3 $\to$ M4 $\to$ M5.
2. **No Real Cross-Module Contract Tests**: Existing contract tests utilize mock fixtures that hide the P0 serialization incompatibilities.
3. **No Cross-Stage Chaos / Resilience Tests**: Outage of intermediate services (e.g. M3 down while M2 is processing) is not tested.

---

## 14. Conflicts & Incompatibilities Summary

1. **M1 vs M2 Envelope Structure**: M1 outputs nested dicts; M2 expects primitive strings.
2. **M3 vs M4 Canonical Format**: M3 wraps fields inside `{"ulpf": { ... }}`; M4 forbids extra keys and requires flat fields.
3. **Tenant Key Divergence**: M4 emits `tenant.tenant_id`; M5 checks `tenant.id` or `tenant_id`.
4. **Tenant Dropping in M3**: M3 strips `tenant_id` during UES assembly.

---

## 15. P0 Findings (Critical Blockers — Must Solve Before Ingestion Works)

1. **P0-1: M1 $\to$ M2 Contract Serialization Failure**  
   *Root Cause*: M1 `RawEventEnvelope` outputs nested `payload` and `transport` models. M2 `RawEventEnvelope` expects flat string types.  
   *Result*: 100% of M1 events are rejected by M2 Pydantic validation.
2. **P0-2: M3 $\to$ M4 Root Encapsulation & Extra Fields Rejection**  
   *Root Cause*: M3 encapsulates canonical fields in `{"ulpf": { ... }}`. M4 `CanonicalEvent` specifies `extra="forbid"`.  
   *Result*: 100% of M3 events are rejected by M4 Pydantic validation.
3. **P0-3: M1 Kafka Output to M2 HTTP Input Transport Disconnect**  
   *Root Cause*: M1 publishes to Kafka topic `ulpf.raw`. M2 has no Kafka consumer service, only an HTTP endpoint `POST /v1/parse`.  
   *Result*: Events published to Kafka accumulate indefinitely without being consumed by M2.

---

## 16. P1 Findings (High Priority — Functional, Security & Data Integrity Risks)

1. **P1-1: Tenant Loss in M3 Normalization**  
   *Root Cause*: M3's `builder.py` and `ULPFBlock` JSON schema omit tenant metadata.  
   *Result*: Normalized events lose tenant identity, breaking multi-tenant isolation and causing M4's `TenantGuard` to reject them.
2. **P1-2: Tenant Key Mismatch between M4 and M5**  
   *Root Cause*: M4 uses `tenant.tenant_id`. M5 router checks `tenant.id` or root `tenant_id`.  
   *Result*: M5 router cannot resolve tenant identity, causing tenant-specific routing rules to fail.
3. **P1-3: Cross-Tenant Header Spoofing at M1 Ingestion Gateway**  
   *Root Cause*: M1 verifies a shared static API token without authenticating the tenant specified in `X-Tenant-ID`.  
   *Result*: Authenticated clients can forge tenant IDs, writing data into other tenants' partitions.
4. **P1-4: Disconnected Configuration Synchronization Loop in M6**  
   *Root Cause*: M6 commits configuration changes to PostgreSQL without an automated trigger to Kafka/Redis or downstream modules.  
   *Result*: Configuration updates in M6 are not dynamically applied by M1–M5.

---

## 17. P2 Findings (Medium Priority — Operational & Packaging Enhancements)

1. **P2-1: Port Allocation Collisions**  
   *Root Cause*: M1 and M6 default to port 8000; M3 and M6 frontends default to port 5173.  
   *Result*: Cannot start all services simultaneously on a single host without environment port overrides.
2. **P2-2: Large File Replay Memory Spikes in M1**  
   *Root Cause*: `replay_file()` accumulates Pydantic models in memory rather than streaming them.  
   *Result*: Process out-of-memory risk on files $>50$ MB.
3. **P2-3: Raw Hash & Storage Reference Not Propagated by M3**  
   *Root Cause*: M2 emits flat `sha256` and `raw_reference`, while M3 expects nested `integrity.hash` and `raw.storage_ref`.  
   *Result*: Raw byte hash and MinIO object references are omitted from M3's canonical UES output.

---

## 18. Recommended Integration Architecture (Phase 1 Target)

In accordance with Phase 0 rules (**Zero direct modifications to frozen modules**), all contract incompatibilities and transport chasms will be resolved via a clean, dedicated **Integration Layer**:

```
integration/
  ├── adapters/
  │   ├── m1_m2_adapter.py       # Kafka consumer on ulpf.raw -> unwraps payload/transport -> calls M2
  │   ├── m2_m3_adapter.py       # Preserves tenant_id/raw_hash -> formats into M3 ParsedEvent -> calls M3
  │   ├── m3_m4_adapter.py       # Unwraps {"ulpf":...} -> injects preserved tenant_id -> calls M4
  │   └── m4_m5_adapter.py       # Unwraps result["event"] -> maps tenant.tenant_id to tenant.id -> calls M5
  ├── orchestration/
  │   └── pipeline_runner.py     # High-throughput asynchronous event pipeline orchestrator
  ├── config/
  │   └── sync_worker.py         # M6 config watcher -> materializes YAML configs & triggers reloads
  ├── deployment/
  │   └── docker-compose.yml     # Unified multi-container deployment with arbitrated ports
  └── tests/
      ├── contract/              # Real live cross-module serialization contract tests
      └── e2e/                   # End-to-end multi-tenant pipeline tests (Cisco, Windows, Unknown)
```

### Key Integration Principles
1. **Preserve Raw Evidence & Invariants**: `raw_event_id` and M1 raw SHA-256 hash are immutably preserved end-to-end.
2. **Restore Tenant Lineage**: Integration adapters ensure `tenant_id` is carried across every boundary.
3. **Non-Invasive Transformation**: Adapters handle serialization mismatches without altering the source code of frozen modules.
4. **Idempotent Delivery**: Take advantage of M1's UUIDv7 and M5's LRU deduplication to guarantee exactly-once data lake delivery.

---

## 19. Phase 0 Exit Gate Verification

- [x] All six repositories located (`M1`, `M2`, `M3`, `M4`, `M5`, `M6`)
- [x] All six implementations forensically inspected
- [x] Independent test baselines captured (672 tests passed, 0 failed)
- [x] Actual entrypoints and default ports documented
- [x] Actual contracts extracted and compared
- [x] Contract compatibility verified and gaps identified
- [x] Dependencies and system topology mapped
- [x] Transport mechanisms and delivery semantics mapped
- [x] Tenant flow and isolation vulnerabilities mapped
- [x] Configuration flow and synchronization gaps mapped
- [x] Database ownership verified (zero cross-database violations)
- [x] Security trust boundaries documented
- [x] Deployment models analyzed
- [x] Test gaps identified
- [x] Integration blockers classified (3 P0s, 4 P1s, 3 P2s)
- [x] `PHASE0_INTEGRATION_ASSESSMENT.md` generated

---

## PHASE 0 COMPLETE — READY FOR INTEGRATION DESIGN REVIEW
