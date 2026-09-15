# ULPF Phase 0 — Actual Dependency Graph & System Topology

**Audit Date**: September 14, 2026  
**Status**: Complete  
**Scope**: Code coupling, runtime network dependencies, persistence layers, and architectural violations.

---

## 1. Actual System Topology Diagram

```mermaid
graph TD
    subgraph Ingestion Layer [M1: Ingestion Gateway]
        M1[M1: Ingestion Engine<br/>Port 8000 / 514 / 515]
        MinIO[(MinIO S3 Vault<br/>ulpf-raw)]
        SQLiteOutbox[(SQLite Outbox<br/>outbox.db)]
        KafkaRaw[[Kafka Topic: ulpf.raw]]
        
        M1 -->|Raw Gzip Blob| MinIO
        M1 -->|Primary Event Stream| KafkaRaw
        M1 -.->|Offline Fallback| SQLiteOutbox
        SQLiteOutbox -.->|Replay On Reconnect| KafkaRaw
    end

    subgraph Parser Layer [M2: Parser Engine]
        KafkaRaw -.->|MISSING CONSUMER DAEMON| M2Adapter[M2 Adapter / Consumer]
        M2Adapter -->|HTTP POST /v1/parse| M2[M2: Parser Engine<br/>Port 8082]
        M2Yaml[(Local YAML Parsers<br/>parsers/)]
        M2 --> M2Yaml
    end

    subgraph Normalization Layer [M3: UES Semantic Layer]
        M2 -->|ParsedEvent (HTTP)| M3[M3: UES Normalizer<br/>Port 8083]
        M3Mappings[(Local YAML Mappings<br/>mappings/)]
        M3 --> M3Mappings
    end

    subgraph Enrichment Layer [M4: Contextual Security]
        M3 -->|CONTRACT MISMATCH: ulpf wrap| M4Adapter[M4 Envelope Unwrapper]
        M4Adapter -->|CanonicalEvent (HTTP /v1/enrich)| M4[M4: Enrichment Engine<br/>Port 8004]
        M4LRU[(In-Memory Cache<br/>Tenant Partitioned)]
        M4 --> M4LRU
    end

    subgraph Routing & Egress Layer [M5: Smart Router & Delivery]
        M4 -->|EnrichmentResult| M5Adapter[M5 Payload Resolver]
        M5Adapter -->|POST /v1/events/process| M5[M5: Smart Router<br/>Port 8085]
        M5Policies[(Local YAML Policies<br/>policies/default.yaml)]
        M5 --> M5Policies
        
        OpenSearch[(OpenSearch SIEM<br/>ulpf-events-v1-*)]
        DataLake[(Partitioned JSONL Lake<br/>./data/datalake)]
        KafkaAI[[Kafka Topic: ulpf.ai.events]]
        DLQ[(JSONL DLQ<br/>./data/dlq)]
        
        M5 -->|Index| OpenSearch
        M5 -->|Append| DataLake
        M5 -->|Stream| KafkaAI
        M5 -.->|On Exhaustion| DLQ
    end

    subgraph Control Plane [M6: Platform Operations]
        M6[M6: Control Plane<br/>Port 8086 / UI 5173]
        M6PG[(PostgreSQL<br/>Registries & Audit)]
        M6Redis[(Redis<br/>Config Cache)]
        M6Kafka[[Kafka Topic: ulpf.m6.config.updates]]
        
        M6 --> M6PG
        M6 --> M6Redis
        M6 --> M6Kafka
        
        M6 -.->|HTTP /health Polling| M1
        M6 -.->|HTTP /health Polling| M2
        M6 -.->|HTTP /health Polling| M3
        M6 -.->|HTTP /health Polling| M4
        M6 -.->|HTTP /health Polling| M5
    end
```

---

## 2. Forensic Code Coupling & Boundary Assessment

### 2.1 Direct Python Code Imports
- **Audit Finding**: **ZERO VIOLATIONS**.
- Verified across all repositories that no module imports Python source files or modules from any other module directory.
  - `M1` imports only standard libraries, FastAPI, Pydantic, aiokafka, and its internal `app.*`.
  - `M2` imports only its internal `app.*`.
  - `M3` imports only its internal `app.*`.
  - `M4` imports only its internal `app.*`.
  - `M5` imports only its internal `app.*`.
  - `M6` imports only its internal `backend.app.*`.

### 2.2 Shared Database Violations
- **Audit Finding**: **ZERO VIOLATIONS**.
- Each module retains exclusive, unshared control over its persistence mechanism:
  - `M1` exclusively owns the SQLite `outbox.db` and MinIO bucket `ulpf-raw`.
  - `M2` exclusively owns its internal parser memory cache.
  - `M3` exclusively owns its internal mapping resolver.
  - `M4` exclusively owns its LRU cache and mock provider databases.
  - `M5` exclusively owns its local JSONL files (`./data/datalake`, `./data/dlq`).
  - `M6` exclusively owns PostgreSQL tables and Redis cache keys.
- **Architectural Strength**: Complete data store independence; zero shared relational schemas or hidden SQL foreign keys between modules.

### 2.3 Filesystem Coupling
- **Audit Finding**: **CLEAN**.
- None of the modules read from or write to sibling repository filesystem paths.
- Each module's file operations are scoped to its local working directory.

### 2.4 Hardcoded Localhost & Port Assumptions
- **M1**: Ports 8000, 514, 515. Kafka `localhost:9092`. MinIO `localhost:9000`.
- **M2**: Port 8082. Configurable via command-line arguments.
- **M3**: Port 8083 (Backend), Port 5173 (Frontend).
- **M4**: Default `127.0.0.1:8004` (configurable via `M4_HOST` and `M4_PORT`).
- **M5**: Default `0.0.0.0:8085` (configurable via `HOST` and `PORT`).
- **M6**: Default `0.0.0.0:8000` (collides with M1 default in unconfigured environment).
- **Finding**: While all modules support environment variable overrides, running without an orchestration configuration results in a port 8000 collision between M1 and M6.

### 2.5 Transport Disconnection & Missing Consumers
- **Critical Architectural Gap**:
  - M1 produces messages to Kafka topic `ulpf.raw`.
  - M2 exposes an HTTP parsing endpoint `POST /v1/parse`, but **contains no Kafka consumer service** to read from `ulpf.raw`.
  - M3 exposes an HTTP endpoint `POST /v1/normalize`, but has no queue worker.
  - M4 exposes an HTTP endpoint `POST /v1/enrich`, but has no queue worker.
  - M5 exposes an HTTP endpoint `POST /v1/events/process`, but has no queue worker.
- **Conclusion**: The current modules are built primarily as REST microservices (with M1 having an async producer). An integration pipeline adapter or event loop is strictly necessary to route events between the stages.
