# ULPF M1 — FORENSIC IMPLEMENTATION AUDIT REPORT
## Ingestion Gateway + Immutable Raw Event Vault
**Audit Date**: September 13, 2026  
**Module Audited**: Universal Log Preprocessing Framework — Module 1 (M1 Ingestion Boundary)  
**Repository Path**: `modules/m1-ingestion`  
**Auditor**: Antigravity Autonomous Security & Architecture Evaluator  
**Audit Rule Adherence**: **AUDIT ONLY — REPOSITORY CODE UNTOUCHED**

---

## 1. Executive Summary

A comprehensive forensic audit of the **ULPF Member 1 (M1) Ingestion Gateway and Raw Event Vault** was conducted. M1's declared mission is to serve as the hardened, high-throughput front door for the Universal Log Preprocessing Framework: ingesting external log streams (HTTP, Syslog UDP, Syslog TCP, File Replay), capturing exact raw bytes, computing SHA-256 tamper-evident integrity hashes, persisting compressed raw evidence into MinIO object storage, and publishing standardized `RawEventEnvelope` messages to Apache Kafka (`ulpf.raw`) for downstream consumption by **M2 (Parser Engine)**.

### Verdict Summary
* **Final Verdict**: **NOT READY** (Grade: **C**)
* **Aggregate Maturity Score**: **5.0 / 10**
* **Finding Totals**: **6 P0** (Critical / Architecture-Breaking), **7 P1** (Serious Correctness / Reliability), **6 P2** (Significant Improvement), **4 P3** (Polish / Code Quality).

### Key Audit Findings
1. **P0 Ingestion Routing Defect**: The HTTP endpoint (`POST /v1/events`) specifies `body: Optional[EventPostPayload] = None` in its FastAPI signature. This enforces JSON parsing at the framework layer, causing **HTTP 422 Unprocessable Entity** for all plain text, raw syslog strings, and arbitrary cybersecurity JSON logs (e.g., CrowdStrike, AWS CloudTrail, Okta). The fallback `await request.body()` is **dead, unreachable code**.
2. **P0 Data Tampering on Syslog & File Replay**: Both `app/transports/tcp_syslog.py` (line 48) and `app/transports/file_replay.py` (line 54 & 104) execute `raw_bytes = line.rstrip(b"\r\n")`. Trailing line terminators are stripped **before** SHA-256 calculation and MinIO persistence. The original byte stream transmitted by the logging source is altered prior to capture.
3. **P0 Security & Tenant Spoofing**: M1 accepts arbitrary `X-Tenant-ID` headers without cross-referencing or validating against the bearer token's authorized tenant scope. Any authenticated client can inject data into arbitrary tenant storage partitions.
4. **P0 Lifespan Startup Bug**: `app/main.py` (line 60) invokes `await asyncio.wait_for(raw_vault.ensure_bucket(), timeout=2.0)`, but **fails to import `asyncio`**. A `NameError` occurs on startup and is silently swallowed by an overly broad `except Exception:`, leaving the MinIO bucket uninitialized.
5. **P0 Unbounded Resource Consumption**: No HTTP request size limit is enforced (a 10MB payload was accepted during adversarial testing), and UDP Syslog spawns an unconstrained `asyncio.create_task` per datagram without rate limits or queue bounds. Under downstream backpressure, memory growth is unbounded.
6. **P1 Lossy Payloads & Dual-Write Inconsistency**: Non-UTF-8 bytes undergo lossy replacement (`errors="replace"`) into Unicode `\ufffd` within the envelope JSON payload while the hash is calculated over raw bytes, creating an integrity contradiction. Furthermore, when Kafka is unavailable, payloads remain orphaned in MinIO with no rollback, retry queue, or DLQ routing.

---

## 2. Repository Architecture & Reconnaissance Map

### File Inventory & Responsibility Matrix

| File Path | Status | Primary Responsibility | Audit Evaluation |
| :--- | :--- | :--- | :--- |
| `app/main.py` | **INCORRECT** | FastAPI app entrypoint, lifespan startup/shutdown, secret scrubbing | Lifespan crashes with `NameError: name 'asyncio' is not defined` (swallowed by catch-all). Runs as root. |
| `app/api/http_ingest.py` | **INCORRECT** | HTTP route definitions (`/v1/events`, `/v1/replay/file`) | Route signature binds `EventPostPayload`, forcing 422 on arbitrary JSON and plain text. |
| `app/api/rate_limiter.py` | **PARTIALLY IMPLEMENTED** | Token-bucket rate limiter | Process-local only. Single global lock. No per-tenant or per-source limits. UDP/TCP bypass it completely. |
| `app/config/settings.py` | **IMPLEMENTED** | Pydantic BaseSettings environment loader | Correctly typed and loaded. Defaults to demo credentials. |
| `app/envelope/models.py` | **PARTIALLY IMPLEMENTED** | Pydantic v2 `RawEventEnvelope` data contract | Clean model structure, but lacks schema versioning and file-replay metadata. |
| `app/envelope/builder.py` | **INCORRECT** | Pure builder for `RawEventEnvelope` & MinIO key generator | Decodes non-UTF8 with `errors="replace"`, causing envelope data to mismatch SHA-256 hash. |
| `app/health/health.py` | **IMPLEMENTED** | `/health`, `/ready`, `/metrics` probe endpoints | Functional. Correctly returns 503 when dependencies fail. |
| `app/health/metrics.py` | **PARTIALLY IMPLEMENTED** | Prometheus metric definitions | Good baseline, but `tenant_id` label poses high cardinality leak. Missing active connection gauges. |
| `app/integrity/hashing.py` | **IMPLEMENTED** | SHA-256 hex digest computation over raw bytes | Correctly computes SHA-256 on byte inputs; raises `TypeError` on strings. |
| `app/integrity/ids.py` | **PARTIALLY IMPLEMENTED** | RFC 9562 UUIDv7 generator | Valid v7 format, 0 collisions in 100k, but lacks sub-millisecond counter (49.27% out-of-order within ms). |
| `app/messaging/kafka.py` | **PARTIALLY IMPLEMENTED** | `aiokafka` producer wrapper & partition affinity | Good partition key (`hash(tenant:source)`), but defaults to `acks=1`, `enable_idempotence=False`. |
| `app/storage/raw_vault.py` | **PARTIALLY IMPLEMENTED** | MinIO S3 client wrapper & Gzip object vault | Gzip compression works, but S3 object lock / WORM is neither configured nor enforced. |
| `app/transports/pipeline.py` | **INCORRECT** | Core ingestion pipeline (Bytes -> SHA-256 -> MinIO -> Kafka) | Dual-write anomaly: MinIO write succeeds, Kafka publish failure leaves orphaned objects with no DLQ/rollback. |
| `app/transports/http.py` | **INCORRECT** | HTTP request handler, token verification | Re-encodes `body.message`, discarding HTTP body. Arbitrary tenant header trusted without authorization. |
| `app/transports/tcp_syslog.py` | **INCORRECT** | Asyncio TCP stream listener (port 515) | Strips `\r\n` before hashing. Fails on lines >64KB (`LimitOverrunError`). No auth, no rate limiting. |
| `app/transports/udp_syslog.py` | **INCORRECT** | Asyncio UDP datagram listener (port 514) | Spawns unconstrained background tasks (`asyncio.create_task`). No rate limiting, no auth. |
| `app/transports/file_replay.py` | **INCORRECT** | File replay CLI & upload endpoint | Strips `\r\n`. Reads entire uploaded file into RAM. No speed control, no checkpointing. |
| `Dockerfile` | **INCORRECT** | Container packaging | Runs as `root` (no `USER` directive). |
| `docker-compose.yml` | **PARTIALLY IMPLEMENTED** | Local stack deployment (M1, KRaft Kafka, MinIO) | Functional for demo, but Kafka logs stored in ephemeral `/tmp`, MinIO lacks object locking. |
| `tests/` | **INCORRECT** | Unit & "integration" tests | 100% mocked storage and Kafka. Zero real service tests. TCP, UDP, Replay have 0% test coverage. |

---

## 3. Actual M1 Data Flow vs Conceptual Architecture

```
[EXTERNAL LOG SOURCES]
        │
        ├── HTTP/JSON: POST /v1/events (FastAPI) [Enforces {"message": "..."}; Rejects arbitrary JSON with 422]
        ├── Syslog TCP: Port 515 (Asyncio StreamReader) [Strips \r\n; Drops conn if line > 64KB]
        ├── Syslog UDP: Port 514 (Asyncio DatagramProtocol) [Unbounded asyncio.create_task; No rate limiting]
        └── File Replay: CLI & POST /v1/replay/file [Strips \r\n; In-memory buffering]
        │
        ▼
[INGESTION BOUNDARY EVALUATION]
        ├── Auth: Bearer Token verified on HTTP/Replay ONLY. Zero auth on TCP/UDP.
        ├── Tenant/Source Metadata: Client-provided X-Tenant-ID trusted unconditionally (Spoofable).
        ├── Rate Limiting: Process-local TokenBucket checked on HTTP ONLY. Bypassed on TCP/UDP.
        └── Payload Extraction: HTTP extracts `body.message.encode()`. TCP/File strips `\r\n`.
        │
        ▼
[RAW CAPTURE & ENVELOPE GENERATION]
        ├── UUIDv7 Generation: Generated via `os.urandom(10)` (No intra-millisecond monotonicity).
        ├── SHA-256 Hashing: Calculated over extracted/stripped bytes (NOT original transport wire bytes).
        ├── UTF-8 Lossy Decoding: Non-UTF8 replaced with \ufffd in `envelope.payload.data`.
        └── S3 Key Generation: `tenant={t}/year={Y}/month={m}/day={d}/source={s}/event={id}`
        │
        ▼
[DUAL-PERSISTENCE STAGE (NON-TRANSACTIONAL)]
        ├── Step 1: MinIO Raw Vault (`app/storage/raw_vault.py`)
        │     └── Compresses with Gzip -> PUT to bucket `ulpf-raw` (NO Object Lock / WORM).
        │     └── [IF MINIO FAILS] -> Aborts; 500 error returned; nothing published.
        │
        └── Step 2: Kafka Bus (`app/messaging/kafka.py`)
              └── Publishes `RawEventEnvelope` JSON to topic `ulpf.raw`.
              └── [IF KAFKA FAILS] -> MinIO object remains ORPHANED; no rollback; no DLQ.
              │
              ▼
             M2 (Parser Engine)
```

---

## 4. Ingestion Protocol Audit

### Protocol Capability Matrix

| Feature / Dimension | HTTP Ingestion | Syslog TCP | Syslog UDP | File Replay |
| :--- | :--- | :--- | :--- | :--- |
| **Endpoint / Binding** | `POST /v1/events` (:8000) | Port 515 (TCP) | Port 514 (UDP) | CLI & `POST /v1/replay/file` |
| **Framing** | HTTP 1.1 Request Body | Newline-delimited (`readline`) | Single Datagram per Event | Line-by-line (`\n`) |
| **Max Payload Size** | **Unbounded** (10MB+ accepted) | **64 KB** (StreamReader default) | **65,507 bytes** (UDP max) | **Unbounded** (Reads all into RAM) |
| **Authentication** | Bearer Token (Shared secret) | **None** | **None** | Bearer Token (Endpoint only) |
| **Rate Limiting** | Enforced (Process-local) | **Bypassed / None** | **Bypassed / None** | **Bypassed / None** |
| **Payload Preservation** | Discards JSON envelope; hashes `message` | Strips `\r\n` before hashing | Preserves datagram bytes | Strips `\r\n` before hashing |
| **Backpressure** | Fails fast via Rate Limiter | Unbounded stream buffering | **Unconstrained task spawning** | Unbounded memory buffering |
| **Error Signaling** | HTTP 401/403/422/429/500 | Silent connection abort | Silent packet drop | HTTP 401/403/500 |
| **Status** | **INCORRECT** | **INCORRECT** | **INCORRECT** | **INCORRECT** |

---

## 5. Raw Capture Order Audit

### Contract Requirement
The raw original bytes must be preserved untouched **before** any parser, decoder, or semantic transformation.

### Forensic Findings
1. **HTTP Ingestion**:
   When an external system transmits a JSON event:
   ```json
   {"message": "<134>Sep 12 09:30:15 FW-01 test log", "format_hint": "syslog"}
   ```
   FastAPI parses the JSON, instantiates `EventPostPayload`, and line 84 of `app/transports/http.py` runs:
   ```python
   raw_bytes = body.message.encode("utf-8")
   ```
   * What was transmitted: `b'{"message": "<134>Sep 12 09:30:15 FW-01 test log", "format_hint": "syslog"}'` (75 bytes)
   * What was captured and hashed: `b'<134>Sep 12 09:30:15 FW-01 test log'` (35 bytes)
   * **Result**: M1 parses the transport format and discards the client's outer envelope before raw preservation.
2. **TCP Syslog**:
   Line 48 of `app/transports/tcp_syslog.py` executes:
   ```python
   raw_bytes = line.rstrip(b"\r\n")
   ```
   If a firewall sends `<134>Sep 13 20:00:00 FW-01 test: hello\r\n`, M1 mutates the byte stream to `<134>Sep 13 20:00:00 FW-01 test: hello` before calculating SHA-256 and storing in MinIO.
3. **File Replay**:
   Line 54 of `app/transports/file_replay.py` executes `raw_bytes = line.rstrip(b"\r\n")`. In empirical testing against `samples/cisco_asa.log`, all 5 events had their trailing `\n` stripped. The stored object in MinIO and the SHA-256 hash did **not** match the exact bytes on disk.

---

## 6. SHA-256 Integrity Audit

### Test Results

| Test Case | Input | Computed SHA-256 Hash | Result |
| :--- | :--- | :--- | :--- |
| **Exact Payload 1** | `b"hello"` | `2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824` | **PASS** |
| **Exact Payload 2** | `b"hello\n"` | `5891b5b522d5df086d0ff0b110fbd9d21bb4fc7163af34d08286a2e846f6be03` | **PASS** (Distinct from `hello`) |
| **Exact Payload 3** | `b"hello\r\n"` | `cd2eca3535741f27a8ae40c31b0c41d4057a7a7b912b33b9aed86485d1c84676` | **PASS** (Distinct from `hello\n`) |
| **NFC Unicode** | `"\u00e9".encode("utf-8")` | `4a99557e4033c3539de2eb65472017cad5f9557f7a0625a09f1c3f6e2ba69c4c` | **PASS** |
| **NFD Unicode** | `"e\u0301".encode("utf-8")` | `bf12767b0f2a56b2190075bae8169f656e3ce8d6357d4aff184bc6c7ea48f9f6` | **PASS** (Distinct from NFC) |
| **Binary / Non-UTF8** | `b"\x80\x81\xff\xfe\x00\x01\x02 test"` | `7d521e32d6af9e479fbcb8957fd8609a5807df3fa759193360886681ff440b4f` | **PASS** (Hashed over raw bytes) |

### Critical Finding: Lossy UTF-8 Replacement in Envelope Payload
In `app/envelope/builder.py` (lines 74–79):
```python
try:
    decoded_data = raw_bytes.decode("utf-8")
    encoding = "utf-8"
except UnicodeDecodeError:
    decoded_data = raw_bytes.decode("utf-8", errors="replace")
    encoding = "utf-8-lossy"
```
When non-UTF-8 bytes are ingested, `envelope.payload.data` receives replacement characters `\ufffd`.
* Raw Byte Hash: `7d521e32...`
* Re-encoded `envelope.payload.data` Hash: `a2aa0262...`
* **Contradiction**: If downstream M2 verifies the integrity of the data string in Kafka, it fails. Downstream systems cannot trust `envelope.payload.data` for non-UTF-8 streams and are forced to fetch the raw object from MinIO.

---

## 7. Raw Event ID Audit (RFC 9562 UUIDv7)

### Empirical 100,000 ID Generation Stress Test
A test harness was executed generating 100,000 consecutive IDs:
* **Total Generated**: 100,000 IDs
* **Generation Rate**: 58,882 IDs/sec
* **Total Collisions**: **0 (Zero collisions observed)**
* **RFC 9562 Format Errors**: **0** (All valid Version 7, Variant 2)
* **Monotonicity Violations**: **49,268 out of 99,999 sequential pairs (49.27%)**

### Root Cause Analysis
In `app/integrity/ids.py`:
```python
timestamp_ms = int(time.time() * 1000)
rand_bytes = os.urandom(10)
raw_bytes[0:6] = timestamp_ms.to_bytes(6, byteorder="big")
raw_bytes[6] = (0x70) | (rand_bytes[0] & 0x0F)
raw_bytes[7] = rand_bytes[1]
raw_bytes[8] = (0x80) | (rand_bytes[2] & 0x3F)
raw_bytes[9:16] = rand_bytes[3:10]
```
The implementation uses RFC 9562 Method 3 (pseudo-random data in `rand_a` and `rand_b`) rather than Method 1 or 2 (dedicated counter). When generating multiple IDs within the **same millisecond**, random bits determine ordering. Approximately **50% of consecutive IDs within the same millisecond sort backwards**. While cross-millisecond ordering is monotonic, intra-millisecond monotonicity is completely absent.

---

## 8. Object Storage & Immutable Vault Audit

### Implementation Inspection (`app/storage/raw_vault.py`)
1. **Partitioning Layout**:
   `tenant={tenant_id}/year={YYYY}/month={MM}/day={DD}/source={source_id}/event={raw_event_id}`
   *Evaluation*: **IMPLEMENTED**. Follows standard S3 Hive-style date partitioning.
2. **Compression & Wire Format**:
   Payloads are compressed using Python `gzip.compress` and stored as `content_type="application/gzip"`.
   *Evaluation*: **IMPLEMENTED**. Reduces storage footprint.
3. **Object Lock / WORM Enforcement**:
   `app/storage/raw_vault.py` line 42 calls `self.client.make_bucket(bucket_name)` without enabling object locking. `docker-compose.yml` line 96 executes `/usr/bin/mc mb myminio/ulpf-raw` without `--with-lock`.
   *Evaluation*: **MISSING**. Storage immutability (WORM) is **NOT enforced**. Any client or service account with S3 write permissions can overwrite or delete raw evidence objects.
   *Official Verdict*: **"Integrity hash exists, but storage immutability is not proven."**
4. **S3 Object Metadata**:
   MinIO `put_object` does not attach `metadata={"sha256": ..., "raw_event_id": ...}` to the S3 object header. Verification requires downloading and decompressing the object.

---

## 9. Kafka / Message Bus Audit

### Configuration & Producer Inspection (`app/messaging/kafka.py`)
```python
self.producer = AIOKafkaProducer(
    bootstrap_servers=self.bootstrap_servers,
    value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    key_serializer=lambda k: k if isinstance(k, bytes) else str(k).encode("utf-8"),
)
```

### Audit Findings
1. **Partition Key Strategy**:
   `hashlib.sha256(f"{tenant_id}:{source_id}".encode("utf-8")).hexdigest().encode("utf-8")`
   *Evaluation*: **IMPLEMENTED**. Excellent partition key strategy ensuring strict per-source ordering while distributing load uniformly across partitions without hot spots.
2. **Delivery Guarantees (`acks`)**:
   `acks` is not explicitly set in `AIOKafkaProducer`. Defaults to **`acks=1`** (leader acknowledgement only). If the partition leader crashes before replication to in-sync replicas (ISRs), **silent event loss occurs**.
3. **Producer Idempotence**:
   `enable_idempotence` is not configured. Defaults to **`False`**. Network retries can produce duplicate Kafka records.
4. **Kafka Headers**:
   No transport headers (`tenant_id`, `raw_event_id`, `received_at`) are attached to Kafka record headers. Downstream consumers must fully deserialize the JSON payload to inspect metadata.
5. **Compression**:
   `compression_type` is not configured. Kafka messages are transmitted as uncompressed JSON.

---

## 10. Idempotency & Duplicate Handling Audit

### Empirical Test
Two identical HTTP POST requests containing payload `<134>Sep 13 20:10:00 FW-01 test duplicate event` were transmitted:
* Request 1 Generated Event ID: `01a09b51-06e2-7243-94e7-dddbad2ff378`
* Request 2 Generated Event ID: `01a09b51-06ec-7b62-943f-17b8d3341bb0`
* Stored MinIO Objects: **2 separate objects created**
* Published Kafka Messages: **2 separate messages published**

### Evaluation: MISSING
M1 has **zero idempotency or deduplication logic**:
* No deduplication window or sliding cache.
* No `Idempotency-Key` or `X-Event-Fingerprint` header support.
* Client retransmissions or network retries create duplicate raw events with different UUIDv7 IDs.

---

## 11. Authentication, Authorization & Tenant Isolation Audit

### Findings
1. **Bearer Token Authentication**:
   * Missing Token: Correctly returns **HTTP 401 Unauthorized**.
   * Invalid Token: Correctly returns **HTTP 403 Forbidden**.
   * Syslog TCP/UDP: **Zero authentication supported or enforced**.
2. **P0 Tenant Isolation Bypass (Header Spoofing)**:
   In `app/transports/http.py`:
   ```python
   metadata = {
       "tenant_id": x_tenant_id or settings.default_tenant_id,
       ...
   }
   ```
   The token validation function (`verify_bearer_token`) checks only that the token matches the global secret `api_auth_token`. It does not scope tokens to tenants.
   * **Vulnerability**: An authorized client for Tenant A can supply `X-Tenant-ID: victim-tenant-b` and inject data into Tenant B's MinIO storage partition and Kafka streams without restriction.
3. **Secret Scrubbing**:
   `SecretScrubbingMiddleware` in `app/main.py` scrubs `Authorization`, `x-api-key`, and `token` from HTTP debug logs.
   * *Limitation*: Only scrubs request headers. Does not scrub credentials passed in query parameters or request bodies.

---

## 12. Rate Limiting & Backpressure Audit

### Findings
1. **Architecture**:
   Implemented as `TokenBucketRateLimiter` in `app/api/rate_limiter.py`.
   * **Process-Local Only**: State is stored in memory (`self.tokens`). If M1 is scaled horizontally across 3 containers, aggregate throughput is multiplied 3x.
   * **Global Bucket**: A single bucket controls all traffic. There is no per-tenant or per-source quota. A single noisy tenant can completely starve all other tenants.
2. **Protocol Bypass**:
   Rate limiting is invoked in `handle_http_ingest` only. It is **never called** in:
   * `UdpSyslogServer`
   * `TcpSyslogServer`
   * `FileReplayServer`
3. **Backpressure Breakdown on UDP**:
   In `app/transports/udp_syslog.py` (lines 24–27):
   ```python
   def datagram_received(self, data: bytes, addr: Tuple[str, int]) -> None:
       if not data:
           return
       asyncio.create_task(self._process(data, addr))
   ```
   Every incoming UDP packet spawns an unconstrained background task. Under high packet volume or downstream Kafka/MinIO degradation, millions of coroutines accumulate in the asyncio event loop, leading to rapid memory exhaustion and process crash.

---

## 13. Payload Size Limits Audit

### Empirical Test
* Small Payload (100 bytes): Accepted (HTTP 202).
* Normal Payload (4 KB): Accepted (HTTP 202).
* Boundary Payload (64 KB): Accepted (HTTP 202).
* Massive Payload (10 MB JSON): **Accepted (HTTP 202)**.

### Findings
1. **HTTP Ingestion**: No `Content-Length` limit is enforced in FastAPI, Starlette middleware, or Uvicorn configuration. A client can transmit 50MB–100MB payloads, causing massive memory spikes and DoS.
2. **TCP Syslog**: Limited to 64 KB by `asyncio.StreamReader.readline()`. When exceeded, `LimitOverrunError` triggers an unhandled exception that silently closes the socket without returning an error.
3. **UDP Syslog**: Limited to 65,507 bytes (UDP datagram limit).
4. **File Replay**: The upload endpoint reads the entire uploaded file into memory (`content = await file.read()`). Uploading a 2GB log file will trigger an immediate OOM crash.

---

## 14. Failure Semantics & Resilience Matrix

| Failure Scenario | HTTP Transport Behavior | Syslog TCP Behavior | Syslog UDP Behavior | MinIO Impact | Kafka Impact | Recovery Behavior |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Kafka Down (MinIO Up)** | Unhandled `ConnectionError` -> HTTP 500 | Exception caught -> Socket closed | Task logs error | Object **persisted** in MinIO | **Failed** | **ORPHANED OBJECTS**. No retry, no DLQ, no rollback. |
| **MinIO Down (Kafka Up)** | Unhandled `ConnectionError` -> HTTP 500 | Exception caught -> Socket closed | Task logs error | **Failed** | Not reached | Pipeline aborts before Kafka. No event published. |
| **Both Down** | HTTP 500 / `/ready` returns 503 | Sockets accept connection then fail | Tasks fail in loop | None | None | Service reports `not_ready` via readiness probe. |
| **Invalid Auth** | HTTP 401 / 403 | N/A (No auth) | N/A (No auth) | None | None | Request dropped prior to processing. |
| **Rate Limit Exceeded**| HTTP 429 Too Many Requests | N/A (Bypassed) | N/A (Bypassed) | None | None | Client throttled. |
| **Payload > 64KB** | Processed (No limit) | Silent socket drop | IP fragmentation / Drop | Preserved (HTTP) | Published (HTTP)| Data lost on TCP without client notification. |
| **Malformed JSON** | HTTP 422 Unprocessable | N/A | N/A | None | None | Rejection prior to pipeline. |

---

## 15. Crash Recovery & Consistency Audit

### Dual-Write Failure Semantics
In `app/transports/pipeline.py`:
```python
# 2. Store untouched raw payload compressed in MinIO
await raw_vault.store_raw_event(...)

# 3. Publish RawEventEnvelope downstream to Kafka
await kafka_producer.publish_envelope(envelope)
```
M1 implements a two-phase write without transactional coordination:
1. **Crash between Step 2 and Step 3**:
   The raw object exists in MinIO, but the Kafka event is never published. M2 never discovers the event. The MinIO object is permanently orphaned.
2. **Process Restart**:
   M1 maintains no local journal, Write-Ahead Log (WAL), or local spool directory (e.g., SQLite or DiskQueue). Any events in-flight in memory during a crash or `SIGKILL` are **permanently lost**.

---

## 16. Observability Audit

### Metric Coverage Analysis

| Required Metric | Metric Name in Code | Type | Labels | Evaluation |
| :--- | :--- | :--- | :--- | :--- |
| Events Accepted | `ulpf_ingest_events_total` | Counter | `transport`, `status`, `tenant_id` | **IMPLEMENTED** (High cardinality risk on `tenant_id`) |
| Events Rejected | `ulpf_ingest_rejected_total` | Counter | `reason` | **IMPLEMENTED** |
| Bytes Ingested | `ulpf_ingest_bytes_total` | Counter | `transport` | **IMPLEMENTED** |
| Ingestion Latency | `ulpf_ingest_latency_seconds` | Histogram | `transport` | **IMPLEMENTED** |
| MinIO Writes | `ulpf_raw_vault_write_total` | Counter | `status` | **IMPLEMENTED** |
| Kafka Publishes | `ulpf_kafka_publish_total` | Counter | `topic` | **IMPLEMENTED** |
| Kafka Errors | `ulpf_kafka_publish_errors_total`| Counter | `topic` | **IMPLEMENTED** |
| Active Connections | *None* | Gauge | — | **MISSING** |
| Queue Depth | *None* | Gauge | — | **MISSING** |
| Dropped Events | *None* | Counter | — | **MISSING** (TCP/UDP socket drops not counted) |

### Health Endpoints
* `/health`: Liveness probe. Returns `{"status": "healthy"}` (HTTP 200).
* `/ready`: Readiness probe. Actively checks `raw_vault.is_healthy()` and `kafka_producer.is_healthy()`. Returns HTTP 503 if either dependency is unreachable. Verified functional.
* `/metrics`: Prometheus exporter exposing all registered metrics. Verified functional.

---

## 17. Security & Hardening Audit

### Findings
1. **Container Security**:
   * `Dockerfile` does not include a `USER` instruction. The application container runs as `root` (UID 0).
2. **Dependency Vulnerability Scan (`pip-audit`)**:
   Scan detected **28 known vulnerabilities** in 2 pinned packages:
   * `python-multipart==0.0.9`: Affected by 14 CVEs/PYSECs (e.g., PYSEC-2026-1851, PYSEC-2026-1852, PYSEC-2026-3036, PYSEC-2026-3037) relating to ReDoS and Denial of Service.
   * `starlette==0.36.3` (transitive via `fastapi==0.110.0`): Affected by 14 CVEs/PYSECs (e.g., PYSEC-2026-1941, PYSEC-2026-1943, PYSEC-2026-2280, PYSEC-2026-2281) relating to path traversal and resource exhaustion.
3. **Default Credentials**:
   `.env.example` and `docker-compose.yml` contain hardcoded demo credentials:
   * `API_AUTH_TOKEN=secret-ingest-token-123`
   * `MINIO_ROOT_USER=minioadmin` / `MINIO_ROOT_PASSWORD=minioadmin`
4. **Transport Encryption (TLS)**:
   M1 exposes plain HTTP (8000), plain TCP (515), and plain UDP (514). No TLS termination, certificates, or mTLS mutual authentication are configured.

---

## 18. Test Quality & Code Coverage Audit

### Code Quality Scan Results
1. **Linter (`ruff check .`)**:
   * **15 errors found across 6 files**.
   * Includes critical bug: `app/main.py:60:15: F821 Undefined name asyncio`.
   * Unused imports and redefinitions in `http_ingest.py`, `raw_vault.py`, `file_replay.py`, and `test_pipeline.py`.
2. **Formatter (`ruff format --check .`)**:
   * **13 files failed formatting check**.
3. **Type Checker (`mypy --strict app`)**:
   * **11 errors in 6 files**. Untyped function signatures across routes and handlers, plus missing library stubs.
4. **Test Coverage (`coverage report`)**:
   * **Total Coverage: 58%** (253 missing statements out of 600).
   * `app/transports/tcp_syslog.py`: **28% coverage** (0% integration test coverage).
   * `app/storage/raw_vault.py`: **32% coverage** (Real MinIO never tested).
   * `app/transports/file_replay.py`: **34% coverage**.
   * `app/messaging/kafka.py`: **35% coverage** (Real Kafka never tested).
   * `app/transports/udp_syslog.py`: **39% coverage**.
   * `app/main.py`: **42% coverage** (Lifespan never executed in test suite).

### False Confidence Analysis
All 9 passing tests in `tests/` operate against in-memory mocks (`MockRawVault`, `MockKafkaProducer`) or pure functions. **Zero tests execute against real MinIO, real Kafka, real network sockets, or concurrent traffic**.

---

## 19. Load & Sustainable Throughput Benchmark

### Methodology
M1 was subjected to multi-tier load testing using concurrent HTTP clients transmitting standard syslog events through the complete ingestion pipeline (FastAPI routing, token rate limiter, UUIDv7 generation, SHA-256 calculation, and Pydantic validation):

| Target Tier | Actual Sustained EPS | Throughput (MB/s) | p50 Latency (ms) | p95 Latency (ms) | p99 Latency (ms) | Process RAM | Error Rate |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **100 EPS** | 99.7 EPS | 0.011 MB/s | 200.16 ms | 281.35 ms | 300.51 ms | 73.1 MB | 0.0% |
| **500 EPS** | 128.2 EPS | 0.014 MB/s | 275.05 ms | 484.87 ms | 613.24 ms | 74.0 MB | 0.0% |
| **1,000 EPS** | 145.8 EPS | 0.016 MB/s | 239.34 ms | 404.27 ms | 619.94 ms | 74.2 MB | 0.0% |
| **2,500 EPS** | 165.8 EPS | 0.018 MB/s | 213.88 ms | 340.16 ms | 544.32 ms | 74.4 MB | 0.0% |
| **5,000 EPS** | 194.0 EPS | 0.021 MB/s | 173.85 ms | 322.69 ms | 410.72 ms | 74.7 MB | 0.0% |

### Throughput Findings
* **Single-Process Ceiling**: Maximum sustainable throughput is **~194 EPS (~0.021 MB/s)**.
* **Bottlenecks**: Synchronous Pydantic v2 envelope validation, synchronous `urandom` bit manipulation in UUIDv7, single-threaded asyncio event loop, and global `asyncio.Lock` contention in `TokenBucketRateLimiter`.
* **Stability**: Memory remained bounded at ~74.7 MB under test.

---

## 20. Deployment & Infrastructure Audit

1. **Docker Compose (`docker-compose.yml`)**:
   * Services: `m1-ingestion`, `kafka` (KRaft mode), `minio`, and `minio-init`.
   * **Ephemeral Kafka**: Kafka log directory is set to `/tmp/kraft-combined-logs` with **no persistent volume**. A container restart wipes all Kafka topics and consumer offsets.
   * **Resource Limits**: No `mem_limit`, `cpus`, or reservations defined for any container.
2. **Container Security**:
   * Container executes as `root`.
   * Healthchecks configured for Kafka and MinIO, but missing for `m1-ingestion`.

---

## 21. Air-Gapped Operation Audit

* **External Dependencies**: M1 does not invoke any third-party external SaaS or cloud endpoints. Kafka and MinIO run entirely on-premises.
* **Air-Gapped Compatibility**: **COMPLIANT AT RUNTIME**, provided that container images and Python wheels are pre-mirrored into local registries.

---

## 22. M1 → M2 Contract Audit

### Contract Alignment Matrix

| Contract Field | M2 Expectation | M1 Implementation | Alignment Evaluation |
| :--- | :--- | :--- | :--- |
| `raw_event_id` | Unique UUIDv7 string | Present (`generate_uuidv7()`) | **COMPLIANT** |
| `tenant_id` | Tenant partition key | Present (`tenant_id`) | **COMPLIANT** (Subject to spoofing) |
| `source_id` | Log source identifier | Present (`source_id`) | **COMPLIANT** |
| `source_type` | Device category | Present (`source_type`, default "firewall") | **COMPLIANT** |
| `received_at` | ISO 8601 UTC timestamp | Present (`YYYY-MM-DDTHH:MM:SS.mmmZ`) | **COMPLIANT** |
| `transport.protocol`| Protocol name (`http`, `tcp`, `udp`) | Present | **COMPLIANT** |
| `payload.data` | Untouched raw event text | Present (String) | **NON-COMPLIANT for non-UTF8** (Lossy `\ufffd`) |
| `integrity.hash` | SHA-256 hex digest | Present (64-char hex) | **COMPLIANT** |
| `raw_storage.object_key`| S3 retrieval path | Present (`tenant=.../event=...`) | **COMPLIANT** |
| `schema_version` | Version of envelope contract | **MISSING** | **NON-COMPLIANT** |

---

## 23. Architectural Boundary Audit

A codebase-wide symbol search for parser logic, regex vendor classifiers, CEF/RFC5424 field extractors, GeoIP, threat intelligence, and UES (Universal Event Schema) models was conducted.
* **Finding**: **0 boundary violations detected**.
* **Verdict**: M1 strictly adheres to boundary rules. It does not perform vendor parsing, normalization, enrichment, or classification.

---

## 24. P0 / P1 / P2 / P3 Classified Findings

### Priority 0 (Critical / Architecture-Breaking / Data Loss / Security)
* **P0-1: HTTP Gateway Rejects Arbitrary JSON and Plain Text with 422**. Route signature `body: Optional[EventPostPayload] = None` forces Pydantic validation expecting `{"message": "..."}`, rejecting standard cybersecurity logs. Fallback `request.body()` is dead code.
* **P0-2: Lifespan Startup Crash Bug**. `app/main.py` line 60 calls `asyncio.wait_for` without importing `asyncio`. Caught and swallowed by `except Exception:`, leaving MinIO bucket initialization failed.
* **P0-3: Tenant Isolation Bypass**. `X-Tenant-ID` header is trusted without authorization scoping against the bearer token.
* **P0-4: Data Tampering on Syslog TCP and File Replay**. Line ending stripping via `line.rstrip(b"\r\n")` mutates raw byte streams prior to hashing and vault persistence.
* **P0-5: Unbounded HTTP Request Body Size**. No max body size limit is configured. 10MB+ payloads are accepted, presenting an immediate Denial of Service (DoS) vulnerability.
* **P0-6: Unbounded Concurrency on UDP Syslog**. Every datagram invokes `asyncio.create_task` with zero queue bounds, task pooling, or rate limits, creating severe memory leakage under downstream latency.

### Priority 1 (Serious Correctness / Reliability / Security)
* **P1-1: Lossy Non-UTF-8 Envelope Decoding**. `builder.py` decodes invalid UTF-8 bytes using `errors="replace"`, producing an envelope payload that contradicts its own SHA-256 hash.
* **P1-2: Orphaned Storage Anomaly on Kafka Failure**. MinIO store precedes Kafka publish without rollback or DLQ fallback. Kafka broker failures result in orphaned MinIO objects and unhandled 500 exceptions.
* **P1-3: At-Risk Kafka Delivery Guarantees**. Producer lacks `acks="all"` and `enable_idempotence=True`, risking silent event loss on leader failure and duplicate messages on network retry.
* **P1-4: 28 Known CVEs in Dependencies**. Pinned dependencies `python-multipart==0.0.9` and `starlette==0.36.3` contain high-severity DoS and path traversal vulnerabilities.
* **P1-5: Root Container Execution**. Dockerfile lacks non-root user configuration.
* **P1-6: False Test Confidence**. 58% overall code coverage; storage and messaging layers tested solely with in-memory mocks; TCP, UDP, and File Replay listeners completely untested.
* **P1-7: Storage Immutability (WORM) Not Proven**. MinIO bucket is created without Object Lock / WORM retention policies.

### Priority 2 (Significant Improvements)
* **P2-1: UUIDv7 Monotonicity Violations**. Intra-millisecond random bit generation causes 49.27% of sequential IDs within the same millisecond to sort out of order.
* **P2-2: Process-Local Rate Limiter**. Single in-memory token bucket cannot scale horizontally and lacks per-tenant quotas.
* **P2-3: TCP Syslog Connection Drop on >64KB Lines**. Lines exceeding 64KB trigger `LimitOverrunError` and silent socket disconnect.
* **P2-4: Missing Contract Versioning**. `RawEventEnvelope` lacks a `schema_version` field.
* **P2-5: High-Cardinality Prometheus Metric Label**. `tenant_id` on `ulpf_ingest_events_total` allows metric explosion from spoofed headers.
* **P2-6: Ephemeral Kafka KRaft Storage**. Docker Compose Kafka service stores logs in `/tmp` without persistent volumes.

### Priority 3 (Minor Issues / Polish)
* **P3-1: 15 Ruff Lint Errors & 13 Formatting Violations**. Unused imports, bad import orders, and format inconsistencies.
* **P3-2: 11 Mypy Strict Errors**. Missing type annotations on route handlers.
* **P3-3: Dead Configuration Variables**. `KAFKA_TOPIC_DLQ` and `KAFKA_TOPIC_REPLAY` defined but never utilized.
* **P3-4: Missing File Replay Metadata**. File replay envelopes do not record source file name, byte offset, or line number.

---

## 25. Forensic Scorecard

| Category | Score (0–10) | Concrete Evidence |
| :--- | :---: | :--- |
| **1. Architecture Correctness** | **7 / 10** | Strict boundary separation maintained (no parser leaks), but crippled by dead fallback code in HTTP route and non-transactional dual writes. |
| **2. Raw Data Integrity** | **5 / 10** | Accurate SHA-256 over byte inputs, but negated by `rstrip` line mutations on TCP/Replay and lossy UTF-8 replacement in envelope payloads. |
| **3. Ingestion Correctness** | **4 / 10** | HTTP route fails with 422 on arbitrary JSON and plain text. TCP drops lines >64KB. UDP lacks validation. |
| **4. Protocol Support** | **5 / 10** | 4 transports present, but TCP lacks RFC 5424 octet counting and TLS; UDP lacks auth and rate limiting; HTTP lacks TLS. |
| **5. Security** | **3 / 10** | Tenant spoofing vulnerability, unbounded 10MB+ payload acceptance, root container execution, 28 dependency CVEs. |
| **6. Reliability** | **4 / 10** | Lifespan startup `NameError` swallowed. Downstream Kafka failure leaves orphaned MinIO objects with no DLQ or retry. |
| **7. Backpressure** | **3 / 10** | UDP spawns unconstrained background tasks. TCP lacks backpressure controls. Rate limiting is strictly process-local. |
| **8. Storage Durability** | **6 / 10** | Hive-style partitioning and Gzip compression work as designed, but WORM / Object Lock is unconfigured and unproven. |
| **9. Kafka Integration** | **6 / 10** | Excellent `hash(tenant:source)` partition key, but defaults to `acks=1`, disabled idempotence, and no headers. |
| **10. Idempotency** | **2 / 10** | No deduplication window or idempotency key support. Retransmissions create duplicate records. |
| **11. Observability** | **6 / 10** | Functional Prometheus `/metrics` and `/ready` probes, but missing active connection gauges and queue depth metrics. |
| **12. Testing** | **3 / 10** | 58% coverage. 100% mocked dependencies. Core network transports (TCP/UDP) have 0% test coverage. |
| **13. Performance** | **6 / 10** | Empirical sustainable throughput measured at ~194 EPS per process. Bounded memory under sustained load. |
| **14. Deployment Readiness**| **4 / 10** | Ephemeral Kafka storage in Docker Compose, hardcoded demo secrets, root container execution. |
| **15. M2 Readiness** | **6 / 10** | Contract models align well with M2 requirements, but missing schema versioning and HTTP 422 defects prevent end-to-end flow. |
| **TOTAL SCORE** | **5.0 / 10** | **Unsatisfactory for production or downstream M2 integration.** |

---

## 26. Final Verdict

# ❌ NOT READY FOR M2 INTEGRATION

**Justification**:
M1 cannot be approved for integration with M2 in its current state. The presence of **6 P0 critical defects** (specifically the HTTP gateway's inability to ingest plain text or arbitrary JSON logs, raw byte tampering via newline stripping, tenant spoofing vulnerabilities, lifespan startup failures, and unbounded memory consumption) directly breaks M1's fundamental contract as an immutable raw evidence preservation gateway.

---

## 27. Required Fixes (Prioritized Remediation Plan)

### Step 1: Fix Core HTTP Ingestion Routing (P0-1)
* Remove `body: Optional[EventPostPayload] = None` from `app/api/http_ingest.py`.
* Receive raw bytes directly using `raw_bytes = await request.body()` in the route handler.
* Inspect `Content-Type`: if JSON and matches wrapper schema, extract message; otherwise, treat the entire body as untouched raw bytes.

### Step 2: Fix Lifespan Startup Bug (P0-2)
* Add `import asyncio` to `app/main.py`.
* Eliminate catch-all `except Exception:` during startup to allow startup failures to fail fast rather than running in a degraded state.

### Step 3: Enforce True Raw Byte Preservation (P0-4)
* Remove `rstrip(b"\r\n")` from `app/transports/tcp_syslog.py` and `app/transports/file_replay.py`.
* Hash and persist the exact byte sequence received over the transport boundary.

### Step 4: Harden Authentication & Tenant Scoping (P0-3)
* Update `verify_bearer_token` to validate tenant permissions against token metadata. Reject requests where the token is unauthorized for the specified `X-Tenant-ID`.

### Step 5: Implement Request Size Limits & Bounded Queues (P0-5, P0-6)
* Add a Starlette middleware enforcing `MAX_PAYLOAD_BYTES` (e.g., 2 MB) returning HTTP 413 Payload Too Large.
* In `app/transports/udp_syslog.py`, replace `asyncio.create_task` with an `asyncio.Queue(maxsize=10000)` and a bounded worker pool.

### Step 6: Eliminate Dual-Write Inconsistencies (P1-2, P1-3)
* In `app/transports/pipeline.py`, wrap downstream publishing in an error handler: if Kafka publish fails, delete or mark the orphaned MinIO object and publish the envelope to a local disk spool or DLQ.
* Configure `AIOKafkaProducer` with `acks="all"` and `enable_idempotence=True`.

### Step 7: Fix Dependency CVEs & Container Security (P1-4, P1-5)
* Upgrade `python-multipart >= 0.0.32` and `fastapi >= 0.115.0` (which bumps `starlette >= 0.40.0`).
* Add a non-root `appuser` (UID 10001) in `Dockerfile`.

---

## 28. Optional Improvements

1. **RFC 9562 Method 1 Monotonic Counter**: Upgrade `app/integrity/ids.py` to maintain a 12-bit intra-millisecond sequence counter in `rand_a` to guarantee 100% sortable monotonicity within the same millisecond.
2. **MinIO Object Lock Configuration**: Update `_ensure_bucket_sync` and `docker-compose.yml` to enable S3 Object Locking and legal holds (`--with-lock`).
3. **Envelope Schema Versioning**: Add `schema_version: str = "1.0.0"` to `RawEventEnvelope`.
4. **Distributed Rate Limiting**: Migrate `TokenBucketRateLimiter` to a Redis-backed sliding window for horizontal scalability across multiple ingestion nodes.
5. **Kafka Headers & Compression**: Configure Snappy/Zstandard compression on the Kafka producer and propagate `tenant_id` and `raw_event_id` in Kafka record headers.
6. **Integration Test Suite**: Implement `testcontainers-python` to test M1 against live Kafka and MinIO containers in CI/CD.
