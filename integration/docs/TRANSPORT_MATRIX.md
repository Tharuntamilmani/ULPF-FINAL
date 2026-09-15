# ULPF Phase 0 — Transport & Delivery Semantics Matrix

**Audit Date**: September 14, 2026  
**Status**: Complete  
**Scope**: Transport mechanisms, serialization protocols, acknowledgment semantics, and deduplication boundaries across the system.

---

## 1. Inter-Module Transport Matrix

| Boundary | Producer | Consumer | Implemented Transport | Endpoint / Topic | Serialization Format | Retry Behavior | ACK Mechanism | Delivery Semantics | Deduplication Location |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **External $\to$ M1** | Client / Syslog | M1 Ingestion | HTTP / UDP / TCP / File | `POST /v1/events`, Ports 514, 515 | Raw Bytes / UTF-8 / RFC5424 | Client-dependent | HTTP 202 / TCP close / UDP None | At-Least-Once (HTTP/TCP), Best-Effort (UDP) | None (M1 accepts all raw bytes) |
| **M1 $\to$ M2** | M1 Ingestion | M2 Parser | Apache Kafka (Primary) / SQLite Outbox | Topic: `ulpf.raw` (Key: `tenant:source`) | UTF-8 JSON (`RawEventEnvelope`) | Outbox worker exponential backoff | Kafka Broker ACK (`acks=all`) | **At-Least-Once (ALO)** | **M2 Ingestion Consumer (Required)** |
| **M2 $\to$ M3** | M2 Parser | M3 Normalizer | HTTP REST (Direct API) | `POST /v1/normalize` | UTF-8 JSON (`ParsedEvent`) | Synchronous HTTP caller retry | HTTP 200 OK (`NormalizationResult`) | At-Least-Once | M3 evaluates idempotent `raw_event_id` |
| **M3 $\to$ M4** | M3 Normalizer | M4 Enrichment | HTTP REST (Direct API) | `POST /v1/enrich` | UTF-8 JSON (`EnrichmentRequest`) | Synchronous HTTP caller retry | HTTP 200 OK (`EnrichmentResult`) | At-Least-Once | M4 verifies invariant `event.id` & `provenance.raw_event_id` |
| **M4 $\to$ M5** | M4 Enrichment | M5 Router | HTTP REST (Direct API) | `POST /v1/events/process` | UTF-8 JSON (`event` dict) | Synchronous HTTP caller retry | HTTP 200 OK (`decision`) | At-Least-Once | **M5 Data Lake Writer (LRU Dedup on `event.id`)** |
| **M5 $\to$ SIEM** | M5 Router | OpenSearch | OpenSearch REST API | Index: `ulpf-events-v1-{tenant}` | JSON Document | 3 retries with exp. backoff | HTTP 200/201 from OpenSearch | At-Least-Once (Idempotent via doc ID) | OpenSearch doc ID (`event.id`) |
| **M5 $\to$ Lake**| M5 Router | Local / S3 File | Append File Stream | Path: `date=.../tenant=.../events.jsonl` | JSONL (Newline-delimited JSON) | File lock & IO retries | OS Filesystem sync | **Exactly-Once Semantics (via LRU Dedup)** | M5 `DataLakeWriter` LRU cache |
| **M5 $\to$ AI Stream**| M5 Router | Kafka Broker | Apache Kafka | Topic: `ulpf.ai.events` | UTF-8 JSON | aiokafka producer retries | Kafka Broker ACK (`acks=all`) | At-Least-Once | Downstream AI consumer responsibility |
| **M5 $\to$ DLQ** | M5 Delivery | Dead Letter Sink | Local File / In-memory | Path: `./data/dlq/dlq_events.jsonl` | JSONL | Immediate append | Local write ACK | At-Least-Once | Forensic operator review |
| **M6 $\to$ M1-M5** | M6 Control | M1-M5 Services | HTTP / Redis / Kafka | Health: `/health`, Config: `ulpf.m6.config.updates` | JSON Payload | Polling retries (health checks) | HTTP 200 / None on pub/sub | Best-Effort (No distributed ACK) | None |

---

## 2. Forensic Analysis of Delivery Semantics & Deduplication

### 2.1 The Inherent At-Least-Once Nature of M1
M1's architecture incorporates an explicit dual-write pattern:
1. When Kafka is available, it produces with `acks=all` and idempotent producer settings (`enable_idempotence=True`).
2. When Kafka is temporarily unavailable, M1 commits the message to a persistent SQLite `outbox.db` table with `status="PENDING"`.
3. When connectivity recovers, an asynchronous background outbox worker scans pending rows and flushes them to Kafka.
4. **Failure State & Duplication**: If the outbox worker publishes a message to Kafka, but crashes or network partitions before marking the SQLite row as `status="COMMITTED"`, the message **will be re-published upon worker restart**.
5. **Conclusion**: Downstream pipeline stages **MUST** anticipate duplicate deliveries of the same `raw_event_id`.

### 2.2 Where Deduplication Must Occur
- **M2 Layer**: When an integration consumer pulls from `ulpf.raw`, it can maintain an ephemeral bloom filter or redis/memory sliding window of `raw_event_id`s to suppress duplicate parser invocations.
- **M3 Layer**: M3 is naturally functional and stateless. Normalizing the same `raw_event_id` twice produces identical deterministic outputs.
- **M4 Layer**: M4's cache keys are scoped to `tenant_id:provider_id:namespace:key`. Re-evaluating the same event will hit warm cache, yielding identical deterministic enrichment and identical RFC 8785 SHA-256 digests.
- **M5 Layer (Authoritative Deduplication)**:
  - M5's `DataLakeWriter` (`app/datalake/writer.py`) implements a high-throughput, memory-bounded LRU deduplication cache (`seen_event_ids`).
  - If an identical `event.id` is received twice, M5 logs:
    `[Data Lake] Duplicate event_id {id} skipped (idempotent write)`
    and skips appending duplicate lines to the partition JSONL file.
  - In OpenSearch, M5 uses `event.id` as the Elasticsearch document `_id`. Re-indexing the same `_id` is natively idempotent in Lucene.

### 2.3 Critical Transport Gap
The primary system transport disconnect is that **M1 writes to Kafka**, while **M2 through M5 expect HTTP REST calls**.
There is currently no event-driven broker consumer linking Kafka topic `ulpf.raw` to M2's `/v1/parse` endpoint. An integration consumer adapter must bridge this gap.
