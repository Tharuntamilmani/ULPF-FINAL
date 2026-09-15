# ULPF Phase 1 — Master Integration Architecture & Implementation Plan

**Date**: September 14, 2026  
**Status**: Ready for Review & Execution  
**Guiding Architecture Principle**: Zero direct modifications to frozen modules M1–M6. Solve all contract discrepancies, transport gaps, security spoofing risks, and configuration disconnects in the dedicated `integration/` subsystem.

---

## 1. Target System Architecture

```
                               ┌─────────────────────────┐
                               │           M6            │
                               │  Control Plane Hub      │
                               │  PostgreSQL & Registries│
                               └────────────┬────────────┘
                                            │
                                 POST /config/apply
                                            │
                                            ▼
                        ┌───────────────────────────────────────┐
                        │     INTEGRATION CONFIG WORKER         │
                        │  Translates M6 configs & returns ACKs │
                        └─┬───────────┬───────────┬───────────┬─┘
                          │           │           │           │
                          ▼           ▼           ▼           ▼
                      M1 Config   M2 Parsers  M3 Mappings M4 Reload  M5 Policies
                       (Env/CLI)  (/v1/parsers)(mappings/) (/v1/config)(policies/)

───────────────────────────────────────────────────────────────────────────────────

   External Clients / Syslog
               │
               ▼
   ┌───────────────────────┐
   │ INGRESS GATEWAY       │  <-- Authenticates client, maps to authorized tenant,
   │ (integration/security)│      strips untrusted headers, injects trusted context
   └───────────┬───────────┘
               │
               ▼
   ┌───────────────────────┐
   │ M1: INGESTION GATEWAY │  <-- Ingests raw bytes, hashes SHA-256, stores in MinIO
   └───────────┬───────────┘
               │
               ▼ Kafka: ulpf.raw
   ┌────────────────────────────────────────────────────────┐
   │ M1 RAW CONSUMER & ADAPTER (integration/consumers)       │
   │ Consumes ulpf.raw, handles duplicates, unwraps payload │
   └───────────────────────────┬────────────────────────────┘
                               │ HTTP POST /v1/parse
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ M2: PARSER ENGINE (Port 8082)                          │
   │ Classifies format/vendor, parses fields -> ParsedEvent │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ M2 $\to$ M3 ADAPTER (integration/adapters)             │
   │ Maps flat sha256/raw_ref to nested integrity/raw       │
   └───────────────────────────┬────────────────────────────┘
                               │ HTTP POST /v1/normalize
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ M3: UES NORMALIZER (Port 8083)                         │
   │ Normalizes to canonical UES, validates Draft 2020-12    │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ M3 $\to$ M4 ADAPTER (integration/adapters)             │
   │ Unwraps {"ulpf":...}, re-attaches trusted tenant_id,   │
   │ sets schema_version="ues.v1"                           │
   └───────────────────────────┬────────────────────────────┘
                               │ HTTP POST /v1/enrich
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ M4: ENRICHMENT & INTEGRITY (Port 8004)                 │
   │ Enriches assets/GeoIP/threat intel, RFC 8785 SHA-256   │
   └───────────────────────────┬────────────────────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ M4 $\to$ M5 ADAPTER (integration/adapters)             │
   │ Passes result["event"] + integrity, maps tenant_id     │
   └───────────────────────────┬────────────────────────────┘
                               │ HTTP POST /v1/events/process
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │ M5: SMART ROUTER & DELIVERY (Port 8085)                │
   │ Evaluates policy, executes delivery with retries/DLQ   │
   └───────────┬─────────────────────┬──────────────────┬───┘
               │                     │                  │
               ▼                     ▼                  ▼
       [OpenSearch SIEM]      [JSONL Data Lake]  [Kafka AI Stream]
     ulpf-events-v1-{tenant}   ./data/datalake     ulpf.ai.events
```

---

## 2. Component Implementation Specifications

### 2.1 Component 1: `M1RawEnvelopeAdapter` (`integration/adapters/m1_raw_envelope_adapter.py`)
- **Input**: M1 `RawEventEnvelope` dictionary containing nested `payload: PayloadInfo`, `transport: TransportInfo`, `integrity: IntegrityInfo`, `raw_storage: RawStorageInfo`.
- **Output**: M2 `RawEventEnvelope` dictionary:
  - `payload = m1_event["payload"]["data"]`
  - `encoding = m1_event["payload"]["encoding"]`
  - `transport = m1_event["transport"]["protocol"]`
  - `sha256 = m1_event["integrity"]["hash"]` (Preserves M1 authoritative raw hash)
  - `raw_reference = f"s3://{m1_event['raw_storage']['bucket']}/{m1_event['raw_storage']['object_key']}"`
  - Preserves `schema_version`, `raw_event_id`, `tenant_id`, `source_id`, `received_at`.

### 2.2 Component 2: `M1RawConsumer` (`integration/consumers/m1_raw_consumer.py`)
- **Transport**: Subscribes to Kafka topic `ulpf.raw` (Group: `ulpf-m2-consumer-group`).
- **Resilience**:
  - Idempotency / Deduplication: In-memory bounded LRU tracking processed `raw_event_id`s to avoid redundant parse invocations under at-least-once Kafka replays.
  - Serialization: Unwraps JSON message via `M1RawEnvelopeAdapter`.
  - Handoff: Calls M2 `POST /v1/parse` with Bearer/API-key authentication.
  - Offset Commit: Commits Kafka offset only after receiving HTTP 200 OK from M2.

### 2.3 Component 3: `M2M3Adapter` (`integration/adapters/m2_m3_adapter.py`)
- **Input**: M2 `ParsedEvent` dictionary.
- **Output**: M3 `ParsedEvent` dictionary:
  - Embeds `sha256` into `integrity = {"hash": {"algorithm": "SHA-256", "value": m2_event["sha256"]}}`.
  - Embeds `raw_reference` into `raw = {"storage_ref": m2_event["raw_reference"], "encoding": "utf-8"}`.
  - Preserves `tenant_id` and `source_id` inside an integration envelope or metadata object.

### 2.4 Component 4: `M3M4Adapter` (`integration/adapters/m3_m4_adapter.py`)
- **Input**: M3 `NormalizationResult` containing `event["ulpf"]`.
- **Output**: M4 `EnrichmentRequest` containing `CanonicalEvent`:
  - Unwraps outer `ulpf` block.
  - Elevates inner canonical blocks (`event`, `observer`, `source`, `destination`, `network`, `host`, `identity`, `provenance`, `vendor`, `extensions`) to root level.
  - Re-attaches trusted tenant context: `tenant = {"tenant_id": trusted_tenant_id}`.
  - Sets root `schema_version = "ues.v1"`.
  - Preserves M1 raw SHA-256 in `provenance` / `raw` block.

### 2.5 Component 5: `M4M5Adapter` (`integration/adapters/m4_m5_adapter.py`)
- **Input**: M4 `EnrichmentResult`.
- **Output**: M5 Ingestion Payload:
  - Extracts `result["event"]`.
  - Attaches `result["integrity"]` and `result["provenance"]` into `event["extensions"]["integrity"]` and `event["provenance"]`.
  - Normalizes tenant identity: duplicates `event["tenant"]["tenant_id"]` into `event["tenant"]["id"]` and root `event["tenant_id"]`.

### 2.6 Component 6: Ingress Security Gateway (`integration/security/ingress_gateway.py`)
- **Purpose**: Solves M1 `SEC-1.4` tenant header spoofing risk without altering M1 source code.
- **Functionality**:
  - Exposes an external-facing proxy endpoint (`POST /ingest`).
  - Authenticates clients using tenant-scoped API keys (e.g. `X-API-Key: key_tenant_alpha`).
  - Resolves authorized tenant identity and strips untrusted client-supplied `X-Tenant-ID` headers.
  - Injects trusted `X-Tenant-ID: tenant-alpha` and trusted internal authorization token before proxying to M1.

### 2.7 Component 7: Configuration Synchronization Worker (`integration/config_sync/config_worker.py`)
- **Purpose**: Closes the M6 configuration operational loop.
- **Functionality**:
  - Implements the `POST /config/apply` endpoint expected by M6's `HttpModuleClient`.
  - Receives versioned configuration events from M6 (`sources`, `parsers`, `schemas`, `mappings`, `policies`).
  - Routes updates:
    - `parsers`: Calls M2 authenticated `POST /v1/parsers` API.
    - `mappings`: Materializes approved YAML files into M3's `mappings/` directory.
    - `enrichment rules`: Calls M4 `POST /v1/config/reload`.
    - `policies`: Writes to M5's `policies/default.yaml` and invokes reload.
  - Generates and returns a compliant `config_ack` payload (`status="APPLIED"`) to M6.

### 2.8 Component 8: Multi-Container Deployment & Port Arbitration (`integration/deployment/`)
- **Arbitrated Host Port Map**:
  - M1 Ingestion: Port `8001` (Host) $\to$ `8000` (Container)
  - M2 Parser: Port `8082`
  - M3 Normalizer Backend: Port `8083`
  - M3 UI Dashboard: Port `5174` (Host) $\to$ `5173` (Container)
  - M4 Enrichment: Port `8004`
  - M5 Smart Router: Port `8085`
  - M6 Control Plane Backend: Port `8086` (Host) $\to$ `8000` (Container)
  - M6 UI Dashboard: Port `5173` (Host) $\to$ `5173` (Container)
  - Integration Ingress Gateway: Port `8080`
  - Infrastructure: Kafka (`9092`), MinIO (`9000`/`9001`), PostgreSQL (`5432`), Redis (`6379`), OpenSearch (`9200`)

---

## 3. Test & Verification Plan

### 3.1 Executable Contract Tests (`integration/tests/contract/`)
- `test_m1_to_m2_contract.py`: Verifies real M1 serialized payloads are adapted and parsed by M2 with zero Pydantic errors.
- `test_m2_to_m3_contract.py`: Verifies M2 outputs normalize in M3 without dropping integrity or storage refs.
- `test_m3_to_m4_contract.py`: Verifies unwrapped M3 canonical outputs validate against M4's `extra="forbid"` schema.
- `test_m4_to_m5_contract.py`: Verifies M4 enriched events route in M5 with full tenant policy matching.

### 3.2 End-to-End Test Suite (`integration/tests/e2e/`)
1. **E2E-01**: Cisco ASA Firewall Syslog end-to-end trace.
2. **E2E-02**: Windows Security Event 4624 (XML) end-to-end trace.
3. **E2E-03**: Unknown proprietary key-value event (Discovery & Replay flow).
4. **E2E-04**: Malformed / truncated event (DLQ promotion).
5. **E2E-05**: Non-UTF8 binary byte stream (Base64 preservation).
6. **E2E-06**: Duplicate event delivery (At-least-once deduplication check in Data Lake).
7. **E2E-07**: Multi-tenant isolation (Tenant Alpha cannot view Tenant Beta events).
8. **E2E-08**: Provider timeout & failure isolation (Enrichment timeout degrades gracefully).
9. **E2E-09**: Crash & recovery (Restarting consumer preserves Kafka offset and resumes without data loss).
10. **E2E-10**: Configuration synchronization (Updating a policy in M6 propagates to M5 and alters routing).
