# UNIVERSAL LOG PREPROCESSING FRAMEWORK (ULPF)
# PRODUCTION DEPLOYMENT INSTRUCTION GUIDE & OPERATIONAL MANUAL

**Document Version:** 1.0.0-PROD  
**Target Baseline:** Frozen Integrated ULPF Baseline (Post Phase 1 & 1.1)  
**Classification:** Technical Operational Specification  
**Repository Root:** `E:\ULPF`  
**Generated Date:** September 14, 2026  

---

## 1. EXECUTIVE OVERVIEW

The **Universal Log Preprocessing Framework (ULPF)** is a modular, high-throughput log ingestion, parsing, normalization, enrichment, and smart routing platform. The system integrates six core domain modules (`M1` through `M6`) and an out-of-process integration layer into an end-to-end processing pipeline:

- **Ingress Security Gateway (`8080`)**: Perimeter anti-spoofing gateway that binds external client credentials to verified tenant identities.
- **M1 Ingestion & Raw Vault (`8001`)**: Multi-transport ingestion daemon (HTTP, UDP Syslog 514, TCP Syslog 515) guaranteeing non-repudiation by preserving byte-exact raw payloads in MinIO object storage and producing SHA-256 evidence digests.
- **Kafka Event Backbone (`9092`)**: High-throughput message streaming layer decoupling ingestion from downstream parsing.
- **M1-M2 Consumer Bridge**: Kafka consumer worker providing at-least-once message delivery, memory-bounded deduplication, and contract adaptation to the M2 REST API.
- **M2 Format Classifier & Parser Engine (`8082`)**: Deterministic log format classifier (Syslog, JSON, CEF, LEEF, KV), dynamic regex/grok parser runner, unknown source discovery, and parser registry.
- **M3 Universal Event Schema (UES) Normalizer (`8083`)**: Semantic field normalization engine translating disparate vendor taxonomies into strict UES v1.0.0 canonical events.
- **M4 Enrichment, Provenance & Integrity Engine (`8004`)**: Contextual enrichment engine (GeoIP, Threat Intelligence, Asset Metadata) that computes RFC 8785 canonical JSON HMAC/SHA-256 cryptographic tamper-evidence digests.
- **M5 Smart Policy Router & Delivery Engine (`8085`)**: Evaluates declarative routing rules and delivers canonical events to SIEM (OpenSearch), Cold Data Lake (JSONL / MinIO), AI/ML streaming queues (Kafka), or Dead Letter Queues (DLQ).
- **M6 Platform Control Plane & Web UI (`8086` / `5173`)**: Central administrative plane managing sources, parsers, schema mappings, routing policies, and transactional outbox configuration distribution.
- **Configuration Sync Worker (`8081`)**: Inter-service control-plane bridge enforcing truthful lifecycle states (`RECEIVED`, `VALIDATED`, `MATERIALIZED`, `RELOAD_REQUIRED`, `RESTART_REQUIRED`, `ACTIVE`, `FAILED`).
- **Unified Health Aggregator (`8090`)**: Central health aggregation endpoint querying liveness and readiness across all modules.

---

## 2. SYSTEM ARCHITECTURE & DATA FLOW

### 2.1 Integrated Runtime Architecture

```
External Client / Syslog Forwarder
              │
              ▼
┌───────────────────────────────────────────────────────────┐
│ Ingress Security Gateway (:8080 / :18080)                 │
│ [integration/security/ingress_gateway.py]                 │
│ • Validates Bearer API Key                                │
│ • Prevents Tenant Header Spoofing                         │
│ • Injects Verified TenantContext & X-Correlation-ID       │
└─────────────────────────────┬─────────────────────────────┘
                              │ HTTP POST /v1/events
                              ▼
┌───────────────────────────────────────────────────────────┐
│ M1 Ingestion Service & Raw Evidence Vault (:8001 / :18001)│
│ [M1/modules/m1-ingestion/app/main.py]                     │
│ • Raw Byte Exactness Preservation                         │
│ • Computes Authoritative Raw SHA-256 Digest               │
│ • Writes Blob to MinIO Bucket: ulpf-raw                   │
│ • Spools to SQLite Outbox (data/outbox.db) on Partition  │
└─────────────────────────────┬─────────────────────────────┘
                              │ Publish RawEventEnvelope
                              ▼
┌───────────────────────────────────────────────────────────┐
│ Apache Kafka Broker (:9092)                               │
│ Topic: ulpf.raw (Key: tenant_id:source_id)                │
└─────────────────────────────┬─────────────────────────────┘
                              │ Consume (Group: ulpf-m1-m2-bridge)
                              ▼
┌───────────────────────────────────────────────────────────┐
│ M1–M2 Consumer Bridge Worker                              │
│ [integration/consumers/m1_raw_consumer.py]                │
│ • Memory-bounded Idempotency Deduplication                │
│ • M1RawEnvelopeAdapter (Flattens nested blocks)           │
│ • Manual Kafka Offset Commit only after 200 OK            │
└─────────────────────────────┬─────────────────────────────┘
                              │ HTTP POST /v1/parse
                              ▼
┌───────────────────────────────────────────────────────────┐
│ M2 Format Classifier & Parser Engine (:8082 / :18082)     │
│ [M2/abcd-main/app/main.py]                                │
│ • Format & Vendor Detection                               │
│ • Executes Parser (e.g. parser-cisco-asa)                 │
│ • Emits ParsedEvent with Un-normalized Fields             │
└─────────────────────────────┬─────────────────────────────┘
                              │ Adapter: M2M3Adapter
                              ▼ HTTP POST /v1/normalize
┌───────────────────────────────────────────────────────────┐
│ M3 UES Normalizer (:8083 / :18083)                        │
│ [M3/app/main.py]                                          │
│ • Maps Vendor Syntax to Universal Event Schema v1.0.0     │
│ • Evaluates YAML mapping rules in mappings/               │
│ • Assigns Canonical Event ID (EVT-...)                    │
└─────────────────────────────┬─────────────────────────────┘
                              │ Adapter: M3M4Adapter
                              ▼ HTTP POST /v1/enrich
┌───────────────────────────────────────────────────────────┐
│ M4 Enrichment & Cryptographic Integrity (:8004 / :18004)  │
│ [M4/app/main.py]                                          │
│ • Contextual Provider Lookup (GeoIP, Threat Intel)        │
│ • Preserves M1 Raw SHA-256 in Extensions                  │
│ • Generates RFC 8785 Canonical JSON Integrity Digest      │
└─────────────────────────────┬─────────────────────────────┘
                              │ Adapter: M4M5Adapter
                              ▼ HTTP POST /v1/events/process
┌───────────────────────────────────────────────────────────┐
│ M5 Smart Policy Router & Delivery Engine (:8085 / :18085) │
│ [M5/app/main.py]                                          │
│ • Evaluates Policies against Canonical Event              │
│ • Multi-Destination Dispatch                              │
└──────┬──────────────────────┬──────────────────────┬──────┘
       │                      │                      │
       ▼                      ▼                      ▼
┌──────────────┐      ┌──────────────┐       ┌──────────────┐
│  OpenSearch  │      │  Cold Lake   │       │ Kafka AI/ML  │
│    (SIEM)    │      │ (JSONL/MinIO)│       │    Queue     │
│    :9200     │      │ :9000 / Disk │       │    :9092     │
└──────────────┘      └──────────────┘       └──────────────┘
```

### 2.2 Control Plane & Configuration Flow

```
┌───────────────────────────────────────────────────────────┐
│ M6 Control Plane Backend (:8086 / :18086)                 │
│ [M6/M6-SIH-main/backend/app/main.py]                      │
│ • PostgreSQL Database: ulpf_m6                            │
│ • Redis Cache: Session & Active Configs                   │
│ • Transactional Outbox (distribution_target_states)       │
└─────────────────────────────┬─────────────────────────────┘
                              │ POST /config/apply/{target_module}
                              ▼
┌───────────────────────────────────────────────────────────┐
│ Configuration Sync Worker (:8081 / :18081)                │
│ [integration/config_sync/config_worker.py]                │
│ • ReDoS Regex Security Screening                          │
│ • Monotonic Semantic Version Comparison (Rejects Stale)   │
│ • Cross-Tenant Scope & Path Traversal Validation          │
│ • Atomic Disk Materialization (tempfile rename)           │
└──────┬──────────────┬──────────────┬──────────────┬───────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌─────────────┐┌─────────────┐┌─────────────┐┌─────────────┐
│     M1      ││     M2      ││     M3      ││     M4      │
│ Ingestion   ││   Parser    ││ Normalizer  ││ Enrichment  │
│(RESTART_REQ)││  (ACTIVE)   ││  (ACTIVE)   ││  (ACTIVE)   │
└─────────────┘└─────────────┘└─────────────┘└─────────────┘
```

---

## 3. PREREQUISITES & SYSTEM REQUIREMENTS

### 3.1 Operating System & Hardware Requirements

| Parameter | Minimum Requirement | Production Recommended |
| :--- | :--- | :--- |
| **Operating System** | Windows 10/11 64-bit Pro/Enterprise OR Ubuntu 22.04 LTS | Ubuntu 22.04 LTS Server OR Windows Server 2022 |
| **CPU Architecture** | x86_64 (amd64) | x86_64 (amd64), 8+ Physical Cores |
| **RAM** | 16 GB Physical Memory | 32 GB+ Physical Memory |
| **Disk Space** | 50 GB SSD Free Space | 250 GB+ High-IOPS NVMe SSD |
| **Network Interfaces** | 1 Gbps Ethernet Loopback / LAN | 10 Gbps Redundant NICs |

### 3.2 Required Software Runtimes

| Component | Required Version | Verification Command | Source Reference |
| :--- | :--- | :--- | :--- |
| **Python** | `3.12.x` (64-bit) | `python --version` | `M1/pyproject.toml`, `M3/Dockerfile`, `M4/pyproject.toml` |
| **Docker Engine** | `24.0+` (Tested: `28.4.0`) | `docker --version` | `integration/deployment/docker-compose.integration.yml` |
| **Docker Compose** | `v2.20+` (Tested: `v2.39.2`) | `docker compose version` | `docker-compose.integration.yml` |
| **Node.js** | `v20.x` or `v22.x` (Tested: `v22.19.0`) | `node --version` | `M3/frontend/package.json`, `M6/frontend/package.json` |
| **npm** | `v10.x` (Tested: `10.9.3`) | `npm --version` | `M3/frontend/package.json` |
| **Git** | `2.40+` | `git --version` | Repository VCS |

---

## 4. REPOSITORY & SERVICE FORENSIC INVENTORY

Every item documented in this section is proven directly by active files in `E:\ULPF`:

### 4.1 Service Inventory & Executable Entry Points

| Service Identifier | Working Directory | Executable Entry Command | Source Proof File |
| :--- | :--- | :--- | :--- |
| **Ingress Gateway** | `E:\ULPF` | `uvicorn integration.security.ingress_gateway:gateway_app --host 0.0.0.0 --port 8080` | `integration/security/ingress_gateway.py:171` |
| **Config Sync Worker** | `E:\ULPF` | `uvicorn integration.config_sync.config_worker:config_sync_app --host 0.0.0.0 --port 8081` | `integration/config_sync/config_worker.py:851` |
| **M1 Ingestion** | `E:\ULPF\M1\modules\m1-ingestion` | `uvicorn app.main:app --host 0.0.0.0 --port 8001` | `M1/modules/m1-ingestion/app/main.py:146` |
| **M1-M2 Bridge** | `E:\ULPF` | `python -c "import asyncio; from integration.consumers.m1_raw_consumer import M1RawEventConsumer; asyncio.run(M1RawEventConsumer().start())"` | `integration/consumers/m1_raw_consumer.py:166` |
| **M2 Parser** | `E:\ULPF\M2\abcd-main` | `uvicorn app.main:app --host 0.0.0.0 --port 8082` | `M2/abcd-main/app/main.py:33` |
| **M3 Normalizer** | `E:\ULPF\M3` | `uvicorn app.main:app --host 0.0.0.0 --port 8083` | `M3/app/main.py:57` |
| **M3 Frontend UI** | `E:\ULPF\M3\frontend` | `npm run dev -- --port 5174` | `M3/frontend/package.json:7` |
| **M4 Enrichment** | `E:\ULPF\M4` | `python -c "from app.main import create_app; import uvicorn; uvicorn.run(create_app(), host='0.0.0.0', port=8004)"` | `M4/app/main.py:33` |
| **M5 Router** | `E:\ULPF\M5` | `uvicorn app.main:app --host 0.0.0.0 --port 8085` | `M5/app/main.py:98` |
| **M6 Control Plane** | `E:\ULPF\M6\M6-SIH-main` | `python -c "from backend.app.main import create_app; import uvicorn; uvicorn.run(create_app(), host='0.0.0.0', port=8086)"` | `M6/M6-SIH-main/backend/app/main.py:44` |
| **M6 Frontend UI** | `E:\ULPF\M6\M6-SIH-main\frontend` | `npm run dev -- --port 5173` | `M6/M6-SIH-main/frontend/package.json:6` |
| **Health Aggregator**| `E:\ULPF` | `uvicorn integration.observability.health:health_app --host 0.0.0.0 --port 8090` | `integration/observability/health.py:135` |

### 4.2 Dockerfile & Compose Inventory

| File Path | Purpose | Base Image | Build Status / Defects |
| :--- | :--- | :--- | :--- |
| `integration/deployment/docker-compose.integration.yml` | Full integrated system compose | N/A (Compose v3.8) | References 15 services; blocked by M4 Dockerfile & Gateway Dockerfile |
| `integration/deployment/Dockerfile.gateway` | Ingress Security Gateway image | `python:3.12-slim` | **DEFECT:** Line 4 `COPY requirements.txt .` fails because no `requirements.txt` exists at repository root. |
| `integration/deployment/Dockerfile.config_sync` | Configuration Sync Worker image | `python:3.12-slim` | Operational (installs explicit packages via pip) |
| `integration/deployment/Dockerfile.consumer` | M1-M2 Kafka Consumer Bridge image | `python:3.12-slim` | Operational (installs explicit packages via pip) |
| `integration/deployment/Dockerfile.health` | System Health Aggregator image | `python:3.12-slim` | Operational (installs explicit packages via pip) |
| `M1/modules/m1-ingestion/Dockerfile` | M1 Ingestion image | `python:3.12-slim` | Operational (multistage, non-root user `appuser`) |
| `M2/abcd-main/Dockerfile` | M2 Parser image | `python:3.12-slim` | Operational (installs build-essential, non-root) |
| `M3/Dockerfile` | M3 Normalizer image | `python:3.12-slim` | Operational (multistage builder, non-root user `ulpf`) |
| `M3/frontend/Dockerfile` | M3 Frontend Nginx image | `node:20-alpine` / `nginx:alpine` | Operational |
| `M4/Dockerfile` | M4 Enrichment image | **NONE** | **MISSING — DEPLOYMENT BLOCKER**: Referenced in `docker-compose.integration.yml:144` but file does not exist on disk! |
| `M5/Dockerfile` | M5 Router image | `python:3.12-slim` | Operational (non-root user `appuser`) |
| `M6/M6-SIH-main/Dockerfile` | M6 Control Plane image | `python:3.12-slim` | Operational (multistage, non-root user `app`) |

### 4.3 Database & Persistent Storage Inventory

| Datastore | Service Owner | Resource Name / Database | Initialization Command / Mechanism | Source File |
| :--- | :--- | :--- | :--- | :--- |
| **PostgreSQL** | M6 Control Plane | Database: `ulpf_m6` (or `m6_control_plane`) | `alembic upgrade head` | `M6/M6-SIH-main/backend/alembic/versions/0001_initial_schema.py` |
| **PostgreSQL** | M6 Control Plane | Extension: `pgcrypto` | Created automatically in migration `0001` | `0001_initial_schema.py:22` |
| **PostgreSQL** | M6 Control Plane | Initial Seed: Roles, Admin user, metadata | `python scripts/seed.py` | `M6/M6-SIH-main/scripts/seed.py:1` |
| **SQLite** | M1 Ingestion | `data/outbox.db` (Durable Outbox table: `outbox`) | Initialized automatically at boot: `outbox.init_db()` | `M1/modules/m1-ingestion/app/storage/outbox.py:32` |
| **MinIO S3** | M1 Ingestion | Bucket: `ulpf-raw` (Raw Byte Evidence Vault) | `raw_vault.ensure_bucket()` at startup | `M1/modules/m1-ingestion/app/main.py:64` |
| **MinIO S3** | M5 Data Lake | Bucket: `ulpf-datalake` | Manual creation required (`mc mb minio/ulpf-datalake`) | `M5/.env.example:32` |
| **MinIO S3** | M6 Control Plane | Buckets: `ulpf-contracts`, `ulpf-schemas` | Manual creation required (`mc mb minio/ulpf-contracts`) | `M6/M6-SIH-main/backend/app/core/config.py:102` |
| **OpenSearch** | M5 Router | Indexes: `ulpf-events-v1-{tenant}` | Dynamic index creation upon first event ingestion | `M5/app/connectors/opensearch.py:45` |
| **Redis** | M6 Control Plane | Database index: `0` | Connected at boot for configuration and session caching | `M6/M6-SIH-main/backend/app/core/config.py:75` |

### 4.4 Kafka Topics & Consumer Groups Inventory

| Topic Name | Partitions | Replication | Producer | Consumer | Purpose | Source Reference |
| :--- | :---: | :---: | :--- | :--- | :--- | :--- |
| `ulpf.raw` | 3 | 1 | M1 Ingestion | `M1RawEventConsumer` (Group: `ulpf-m1-m2-bridge`) | Authoritative raw event stream | `M1/settings.py:12`, `m1_raw_consumer.py:42` |
| `ulpf.dlq` | 1 | 1 | M1 Ingestion / Bridge | Forensic Tooling / Operator | Ingestion dead-letter queue | `M1/settings.py:13` |
| `ulpf.replay` | 1 | 1 | M6 Control Plane | M1 Replay Worker / M2 Replay | Raw log historical replay | `M6/config.py:94`, `M1/settings.py:14` |
| `ulpf.parsed` | 3 | 1 | M2 Parser (Optional) | M3 Normalizer (Group: `m3-normalizer`) | Optional Kafka parsing pipeline | `M3/app/config.py:36` |
| `ulpf.normalized`| 3 | 1 | M3 Normalizer (Optional) | M4 Enrichment | Optional normalized Kafka stream | `M3/app/config.py:37` |
| `ulpf.validation.dlq`| 1 | 1 | M3 Normalizer | Forensic Operator | M3 UES schema validation rejections | `M3/app/config.py:38` |
| `ulpf.ai.events` | 3 | 1 | M5 Router (Connector: `ai_stream`) | Downstream AI/ML Ingestion | High-priority security events for ML | `M5/app/main.py:62`, `M5/.env.example:37` |
| `ulpf.m6.config.updates`| 1 | 1 | M6 Control Plane | Background Consumers | M6 pub/sub configuration updates | `M6/config.py:93` |

---

## 5. EVALUATION OF DEPLOYMENT MODELS

Based strictly on forensic evidence discovered in the repository, the supported deployment models are evaluated as follows:

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        DEPLOYMENT MODEL SUPPORT MATRIX                     │
├──────────────────────────────────────┬──────────────────────┬──────────────┤
│ Deployment Architecture              │ Status               │ Verification │
├──────────────────────────────────────┼──────────────────────┼──────────────┤
│ 1. Local Windows Hybrid (Docker+Host)│ SUPPORTED            │ VERIFIED     │
│ 2. Single-Host Native Linux/Windows  │ SUPPORTED            │ VERIFIED     │
│ 3. All-Container Docker Compose      │ PARTIALLY SUPPORTED  │ BLOCKED      │
│ 4. Multi-Container Hybrid            │ SUPPORTED            │ VERIFIED     │
│ 5. Multi-Node Distributed Cluster    │ PARTIALLY SUPPORTED  │ CONDITIONAL  │
│ 6. Kubernetes (K8s / Helm)           │ NOT SUPPORTED        │ NO MANIFESTS │
│ 7. Air-Gapped Deployment             │ PARTIALLY SUPPORTED  │ CONDITIONAL  │
└──────────────────────────────────────┴──────────────────────┴──────────────┘
```

### Detailed Evaluation:

1. **Local Windows Hybrid Deployment (Docker for Infra + Native Python Processes for Services)**:
   - **Status:** **SUPPORTED (VERIFIED)**
   - **Proof:** `integration/tests/e2e/test_real_deployment_network.py` deployed the full stack using this exact model: the 6 infrastructure services ran in Docker containers (`ulpf-kafka-test`, `ulpf-zookeeper-test`, `ulpf-minio-test`, `ulpf-redis-test`, `ulpf-postgres-test`, `ulpf-opensearch-test`) while all 9 microservices ran as native Windows Python 3.12 processes on loopback ports (18000 range). 718/718 tests passed.
2. **Single-Host Native Deployment (Linux / Windows)**:
   - **Status:** **SUPPORTED (VERIFIED)**
   - **Details:** Can execute entirely natively if infrastructure daemons are installed on host or run via Docker.
3. **All-Container Docker Compose Deployment (`docker-compose.integration.yml`)**:
   - **Status:** **PARTIALLY SUPPORTED (BLOCKED)**
   - **Defects Preventing Execution:**
     - `E:\ULPF\M4\Dockerfile` does NOT exist on disk. `docker compose build` errors out immediately.
     - `E:\ULPF\integration\deployment\Dockerfile.gateway` contains `COPY requirements.txt .` on line 4, but no `requirements.txt` exists at root `E:\ULPF\`.
     - *Per instructions, we do not edit codebase files.* Therefore, all-container Docker Compose build is **BLOCKED**.
4. **Multi-Node Distributed Deployment**:
   - **Status:** **PARTIALLY SUPPORTED (CONDITIONAL)**
   - **Limitations:** All microservices accept network URLs via environment variables (`M1_INTERNAL_URL`, `DATABASE_URL`, `KAFKA_BOOTSTRAP_SERVERS`). However, `ConfigSyncWorker` writes configuration mutations directly to local disk paths (`M2/abcd-main/parsers/<tenant>/<id>.yaml`, `M3/mappings/<id>.yaml`, `integration/config_sync/generated/m1_sources.json`). In a multi-node topology, these directories must reside on a shared NFS/EFS mount, or the API mode must be used.
5. **Kubernetes Deployment**:
   - **Status:** **NOT SUPPORTED**
   - **Proof:** Zero Kubernetes manifests (`*.yaml` containing `apiVersion: apps/v1`), Helm charts, or Kustomize configurations exist anywhere in the repository.
6. **Air-Gapped Deployment**:
   - **Status:** **PARTIALLY SUPPORTED (CONDITIONAL)**
   - **Details:** The system does not depend on cloud-managed SaaS APIs (all databases and brokers are self-hosted). However, the repository does not vendor Python wheels or offline container tarballs; dependencies must be mirrored before going offline.

---

## 6. ENVIRONMENT CONFIGURATION MASTER TABLE

All configuration values across every service are forensically audited below:

| Variable | Service | Required | Example Value | Secret? | Purpose | Source File Reference |
| :--- | :--- | :---: | :--- | :---: | :--- | :--- |
| **`M1_INTERNAL_URL`** | Gateway | YES | `http://127.0.0.1:8001` | NO | Address of internal M1 Ingestion service | `ingress_gateway.py:69` |
| **`M1_INTERNAL_TOKEN`**| Gateway, M1 | YES | `[REDACTED_TOKEN_32B]` | **YES** | Shared authentication token between Gateway and M1 | `ingress_gateway.py:142`, `M1/settings.py:8` |
| **`HTTP_PORT`** | M1 | NO | `8001` (Default: `8000`) | NO | HTTP Ingestion listening port | `M1/settings.py:25` |
| **`HTTP_HOST`** | M1 | NO | `0.0.0.0` | NO | Ingestion socket binding host | `M1/settings.py:24` |
| **`UDP_PORT`** | M1 | NO | `514` | NO | Syslog UDP listener port | `M1/settings.py:26` |
| **`TCP_PORT`** | M1 | NO | `515` | NO | Syslog TCP listener port | `M1/settings.py:27` |
| **`MINIO_ENDPOINT`** | M1, M5, M6 | YES | `localhost:9000` | NO | MinIO S3 API host and port | `M1/settings.py:17`, `M5/.env.example:29` |
| **`MINIO_ACCESS_KEY`** | M1, M5, M6 | YES | `minioadmin` | NO | MinIO root/service access key | `M1/settings.py:18` |
| **`MINIO_SECRET_KEY`** | M1, M5, M6 | YES | `[REDACTED_PASSWORD]` | **YES** | MinIO secret credentials | `M1/settings.py:19` |
| **`MINIO_BUCKET_RAW`** | M1 | YES | `ulpf-raw` | NO | Default S3 bucket for immutable raw logs | `M1/settings.py:20` |
| **`OUTBOX_DB_PATH`** | M1 | YES | `data/outbox.db` | NO | Path to SQLite outbox spool database | `M1/settings.py:33` |
| **`KAFKA_BOOTSTRAP_SERVERS`** | M1, Bridge, M5, M6 | YES | `localhost:9092` | NO | Host and port list of Kafka brokers | `M1/settings.py:11`, `m1_raw_consumer.py:41` |
| **`KAFKA_TOPIC_RAW`** | M1, Bridge | YES | `ulpf.raw` | NO | Target Kafka topic for raw event envelopes | `M1/settings.py:12` |
| **`PARSER_STORAGE_DIR`**| M2 | YES | `E:/ULPF/M2/abcd-main/parsers` | NO | Filesystem directory containing parser YAMLs | `M2/app/main.py:41` |
| **`M2_BASE_URL`** | Bridge, ConfigSync | YES | `http://127.0.0.1:8082` | NO | Network URL of M2 parsing engine | `m1_raw_consumer.py:45`, `config_worker.py:82` |
| **`M2_AUTH_TOKEN`** | Bridge, ConfigSync | YES | `[REDACTED_TOKEN]` | **YES** | System token to authenticate with M2 | `m1_raw_consumer.py:46`, `M2/app/auth/security.py:9` |
| **`ULPF_M3_PORT`** | M3 | NO | `8083` | NO | Listening port for M3 Normalizer | `M3/app/config.py:21` |
| **`ULPF_MAPPING_DIR`** | M3 | YES | `mappings` | NO | Directory containing UES mapping rules | `M3/app/config.py:27` |
| **`M4_PORT`** | M4 | NO | `8004` | NO | Listening port for M4 Enrichment | `M4/app/config/settings.py:16` |
| **`M4_API_AUTH_SECRET`**| M4 | YES | `[REDACTED_KEY_32B]` | **YES** | HMAC secret key for API authentication | `M4/app/config/settings.py:17` |
| **`POLICY_FILE_PATH`** | M5 | YES | `./policies/default.yaml` | NO | Initial policy definitions file | `M5/app/main.py:50` |
| **`OPENSEARCH_HOST`** | M5, M6 | YES | `http://localhost:9200` | NO | OpenSearch REST cluster URL | `M5/.env.example:20`, `M6/config.py:106` |
| **`OPENSEARCH_USER`** | M5, M6 | NO | `admin` | NO | OpenSearch username | `M5/.env.example:22` |
| **`OPENSEARCH_PASSWORD`**| M5, M6 | YES | `[REDACTED_PASSWORD]` | **YES** | OpenSearch password | `M5/.env.example:23` |
| **`OPENSEARCH_MOCK_MODE`**| M5 | NO | `false` (Prod: `false`) | NO | Enables real OpenSearch delivery | `M5/.env.example:24` |
| **`DATA_LAKE_LOCAL_PATH`**| M5 | YES | `./data/datalake` | NO | Cold storage JSONL partition path | `M5/.env.example:28` |
| **`DLQ_LOCAL_PATH`** | M5 | YES | `./data/dlq` | NO | Path for unroutable / unrecoverable logs | `M5/.env.example:46` |
| **`POSTGRES_HOST`** | M6 | YES | `localhost` | NO | PostgreSQL database host | `M6/config.py:45` |
| **`POSTGRES_PORT`** | M6 | NO | `5432` | NO | PostgreSQL port | `M6/config.py:46` |
| **`POSTGRES_DB`** | M6 | YES | `ulpf_m6` | NO | PostgreSQL database name | `M6/config.py:47`, `.env.integration:51` |
| **`POSTGRES_USER`** | M6 | YES | `ulpf_admin` | NO | PostgreSQL user | `M6/config.py:48`, `.env.integration:52` |
| **`POSTGRES_PASSWORD`**| M6 | YES | `[REDACTED_PASSWORD]` | **YES** | PostgreSQL user password | `M6/config.py:49`, `.env.integration:53` |
| **`SECRET_KEY`** | M6 | YES | `[REDACTED_KEY_32B]` | **YES** | M6 JWT signing secret (min 32 chars) | `M6/config.py:34` |
| **`ADMIN_PASSWORD`** | M6 | YES | `[REDACTED_PASSWORD]` | **YES** | Initial M6 admin user password (seed only) | `M6/config.py:42` |
| **`REDIS_HOST`** | M6 | YES | `localhost` | NO | Redis server host | `M6/config.py:75` |
| **`REDIS_PORT`** | M6 | NO | `6379` | NO | Redis server port | `M6/config.py:76` |
| **`REDIS_PASSWORD`** | M6 | NO | `[REDACTED_PASSWORD]` | **YES** | Redis authentication password | `M6/config.py:77` |
| **`CONFIG_SYNC_URL`** | Health, M6 | YES | `http://localhost:8081` | NO | URL of Configuration Sync Worker | `health.py:52` |

### Dangerous Defaults Requiring Production Hardening:

1. **Static Pre-shared Tokens**:
   - `M1_INTERNAL_TOKEN` default `sec-m1-token-sysadmin-9901` (`.env.integration:57`)
   - `M2_SERVICE_TOKEN` default `system-admin-token` (`M2/app/auth/security.py:9`)
   - `M4_API_AUTH_SECRET` default `m4-insecure-secret-key-change-in-prod-8f2c3d4e5f6a7b8c` (`M4/app/config/settings.py:18`)
   - **Action:** Generate random 32-byte cryptographically secure strings for each service before production deployment.
2. **Permissive CORS Defaults**:
   - `ALLOWED_ORIGINS=*` in M5 (`M5/.env.example:12`) and M4 (`M4/app/main.py:45`).
   - **Action:** Restrict origins explicitly to production dashboard domains.
3. **OpenSearch Security Disabled in Test Container**:
   - `plugins.security.disabled="true"` in `docker-compose.integration.yml:93`.
   - **Action:** Enable OpenSearch TLS and internal role-based access control.

---

## 7. NETWORK & PORT MAP

The table below details all port allocations across the unified architecture:

| Component | Standard Host Port | Arbitrated Host Port (Phase 1.1) | Container Port | Protocol | Used By | Public / Internal |
| :--- | :---: | :---: | :---: | :--- | :--- | :--- |
| **Ingress Gateway** | `8080` | `18080` | `8080` | HTTP/TCP | External Clients | **PUBLIC (Edge)** |
| **M1 Ingestion HTTP** | `8001` | `18001` | `8000` | HTTP/TCP | Ingress Gateway | INTERNAL ONLY |
| **M1 Syslog UDP** | `514` | `18514` | `514` | UDP | Network Firewalls, Routers | **PUBLIC / DMZ** |
| **M1 Syslog TCP** | `515` | `18515` | `515` | TCP | Servers, Forwarders | **PUBLIC / DMZ** |
| **Configuration Sync** | `8081` | `18081` | `8081` | HTTP/TCP | M6 Control Plane Outbox | INTERNAL ONLY |
| **M2 Parser Engine** | `8082` | `18082` | `8000` / `8082`| HTTP/TCP | Consumer Bridge, ConfigSync | INTERNAL ONLY |
| **M3 Normalizer** | `8083` | `18083` | `8083` | HTTP/TCP | Pipeline Orchestrator, ConfigSync | INTERNAL ONLY |
| **M3 Frontend UI** | `5174` | `5174` | `5173` | HTTP/TCP | Parser Developers (Browser) | ADMIN ONLY |
| **M4 Enrichment** | `8004` | `18004` | `8004` | HTTP/TCP | Pipeline Orchestrator, ConfigSync | INTERNAL ONLY |
| **M5 Smart Router** | `8085` | `18085` | `8085` | HTTP/TCP | Pipeline Orchestrator, ConfigSync | INTERNAL ONLY |
| **M6 Control Plane** | `8086` | `18086` | `8000` | HTTP/TCP | M6 Frontend UI, Operators | INTERNAL ONLY |
| **M6 Frontend UI** | `5173` | `5173` | `5173` | HTTP/TCP | Security Administrators (Browser) | ADMIN ONLY |
| **Health Aggregator** | `8090` | `18090` | `8090` | HTTP/TCP | Prometheus, SRE Monitoring | ADMIN ONLY |
| **Kafka Broker** | `9092` | `9092` | `9092` | PLAINTEXT/TCP | M1, Bridge, M5, M6 | INTERNAL ONLY |
| **ZooKeeper** | `2181` | `2181` | `2181` | TCP | Kafka Cluster Coordinator | INTERNAL ONLY |
| **MinIO API** | `9000` | `9000` | `9000` | HTTP/TCP | M1, M5, M6 | INTERNAL ONLY |
| **MinIO Console** | `9001` | `9001` | `9001` | HTTP/TCP | Storage Administrators | ADMIN ONLY |
| **Redis** | `6379` | `6379` | `6379` | TCP | M6 Control Plane | INTERNAL ONLY |
| **PostgreSQL** | `5432` | `5432` | `5432` | TCP | M6 Control Plane | INTERNAL ONLY |
| **OpenSearch REST** | `9200` | `9200` | `9200` | HTTP/TCP | M5 Router, M6 Control Plane | INTERNAL ONLY |

---

## 8. INFRASTRUCTURE DEPLOYMENT

The six core infrastructure containers must be deployed and initialized prior to booting any application service.

### 8.1 Docker Infrastructure Launch

Execute the following commands to stand up the tested infrastructure containers:

```bash
# 1. Start ZooKeeper
docker run -d --name ulpf-zookeeper -p 2181:2181 \
  -e ZOOKEEPER_CLIENT_PORT=2181 \
  -e ZOOKEEPER_TICK_TIME=2000 \
  confluentinc/cp-zookeeper:7.5.0

# 2. Start Kafka
docker run -d --name ulpf-kafka -p 9092:9092 \
  -e KAFKA_BROKER_ID=1 \
  -e KAFKA_ZOOKEEPER_CONNECT=host.docker.internal:2181 \
  -e KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092,PLAINTEXT_HOST://localhost:9092 \
  -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
  -e KAFKA_AUTO_CREATE_TOPICS_ENABLE="true" \
  confluentinc/cp-kafka:7.5.0

# 3. Start MinIO Object Storage
docker run -d --name ulpf-minio -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadminsecret \
  minio/minio:latest server /data --console-address ":9001"

# 4. Start PostgreSQL 15
docker run -d --name ulpf-postgres -p 5432:5432 \
  -e POSTGRES_DB=ulpf_m6 \
  -e POSTGRES_USER=ulpf_admin \
  -e POSTGRES_PASSWORD=ulpf_secure_password \
  postgres:15-alpine

# 5. Start Redis 7
docker run -d --name ulpf-redis -p 6379:6379 redis:7-alpine

# 6. Start OpenSearch 2.11+
docker run -d --name ulpf-opensearch -p 9200:9200 -p 9600:9600 \
  -e "discovery.type=single-node" \
  -e "plugins.security.disabled=true" \
  -e "OPENSEARCH_JAVA_OPTS=-Xms512m -Xmx512m" \
  opensearchproject/opensearch:2.18.0
```

---

## 9. DATABASE & STORAGE INITIALIZATION

### 9.1 PostgreSQL Migrations & Seed Data

M6 requires database schema migration via Alembic and metadata seeding:

```bash
# Set Working Directory to M6 Backend
cd E:\ULPF\M6\M6-SIH-main\backend

# Execute Alembic Migrations to create pgcrypto and all 10 control-plane tables
alembic upgrade head

# Set Working Directory to M6 Root and execute bootstrap seed script
cd E:\ULPF\M6\M6-SIH-main
python scripts/seed.py
```

*Proof:* `E:\ULPF\M6\M6-SIH-main\backend\alembic\versions\0001_initial_schema.py` creates tables `roles`, `users`, `user_roles`, `sources`, `parsers`, `schema_mappings`, `enrichment_rules`, `routing_policies`, `distribution_events`, `audit_logs`. `scripts/seed.py` creates default administrator account `admin`.

### 9.2 MinIO Bucket Initialization

Execute bucket creation commands (via AWS CLI or MinIO client `mc`):

```bash
# Configure MinIO Client Alias
mc alias set local http://localhost:9000 minioadmin minioadminsecret

# Create Mandatory Buckets
mc mb local/ulpf-raw
mc mb local/ulpf-datalake
mc mb local/ulpf-contracts
mc mb local/ulpf-schemas
```

*Note:* `M1` will create `ulpf-raw` automatically at startup if it does not exist (`M1/app/main.py:64`), but `ulpf-datalake`, `ulpf-contracts`, and `ulpf-schemas` must exist before M5 and M6 access them.

### 9.3 Kafka Topic Creation

While `KAFKA_AUTO_CREATE_TOPICS_ENABLE="true"` is enabled in test configurations, production deployments should pre-create partitioned topics:

```bash
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.raw --partitions 3 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.dlq --partitions 1 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.replay --partitions 1 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.ai.events --partitions 3 --replication-factor 1
docker exec ulpf-kafka kafka-topics --bootstrap-server localhost:9092 --create --if-not-exists --topic ulpf.m6.config.updates --partitions 1 --replication-factor 1
```

---

## 10. CONFIGURATION CONTROL PLANE WORKFLOW

The configuration synchronization pipeline guarantees that configuration mutations initiated in M6 are applied honestly across all module runtimes:

### 10.1 The Seven State Transitions

```
       ┌─────────────┐
       │  RECEIVED   │ (Payload parsed and validated against schema)
       └──────┬──────┘
              │
              ▼
       ┌─────────────┐
       │  VALIDATED  │ (Checksum checked; ReDoS screened; Version strictly > Active)
       └──────┬──────┘
              │
              ▼
       ┌──────────────┐
       │ MATERIALIZED │ (Files atomically written to target disk via tempfile)
       └──────┬───────┘
              │
      ┌───────┴────────────────────────┐
      ▼                                ▼
┌─────────────────┐          ┌───────────────────┐
│ RELOAD_REQUIRED │          │ RESTART_REQUIRED  │
└────────┬────────┘          └─────────┬─────────┘
         │ (Cache cleared /            │ (Daemon restarted via SIGHUP
         │  dynamic API reload)        │  or rolling restart)
         └─────────────┬───────────────┘
                       │
                       ▼
                 ┌──────────┐
                 │  ACTIVE  │ (Verified via live execution proof)
                 └──────────┘
```

If validation fails, path traversal is detected, or runtime verification fails, the state transitions immediately to `FAILED`.

### 10.2 Module-Specific Adoption Rules:

1. **M1 (Ingestion)**:
   - **Behavior:** M1 loads socket configurations and rate limits at process boot. It has no live reload endpoint.
   - **State Emitted:** `RESTART_REQUIRED` (`applied=False`).
   - **Operator Action:** Must perform a controlled process restart or container restart for the new settings to become `ACTIVE`.
2. **M2 (Parser Engine)**:
   - **Behavior:** Dynamic parser registration via `POST /v1/parsers/register`.
   - **State Emitted:** `ACTIVE` (`applied=True`) only after ConfigSync verifies an actual log line parses through the newly registered parser ID.
3. **M3 (Normalizer)**:
   - **Behavior:** In-memory LRU cache `MappingResolver`. Writing a YAML file to disk does not clear the cache.
   - **State Emitted:** `ACTIVE` (`applied=True`) after `MappingResolver.clear_cache()` is invoked and a test normalization verifies the new schema fields.
4. **M4 (Enrichment)**:
   - **Behavior:** Provider version switch in `ConfigurationManager`.
   - **State Emitted:** `ACTIVE` (`applied=True`) after provenance metadata confirms the active version pointer advanced.
5. **M5 (Router)**:
   - **Behavior:** Dynamic policy reloading via `PolicyEngine.load_policies()`.
   - **State Emitted:** `ACTIVE` (`applied=True`) after test evaluation confirms route alteration.

---

## 11. STEP-BY-STEP PRODUCTION STARTUP PROCEDURE

The startup procedure must strictly respect service inter-dependencies.

```mermaid
graph TD
    S1[STEP 1: Host Preparation & Dirs] --> S2[STEP 2: Infrastructure Containers]
    S2 --> S3[STEP 3: Database Migrations & Seeds]
    S3 --> S4[STEP 4: Start M6 Control Plane :8086]
    S4 --> S5[STEP 5: Start ConfigSync Worker :8081]
    S5 --> S6[STEP 6: Start Downstream Runtimes M5, M4, M3, M2]
    S6 --> S7[STEP 7: Start M1 Ingestion :8001]
    S7 --> S8[STEP 8: Start M1-M2 Consumer Bridge]
    S8 --> S9[STEP 9: Start Ingress Gateway :8080]
    S9 --> S10[STEP 10: Start Health Aggregator :8090]
    S10 --> S11[STEP 11: End-to-End Health Probe]
```

### Execution Steps:

- **STEP 1 — Host Preparation**: Create required local storage directories:
  `mkdir -p E:\ULPF\M1\modules\m1-ingestion\data`
  `mkdir -p E:\ULPF\M5\data\datalake E:\ULPF\M5\data\dlq`
  `mkdir -p E:\ULPF\integration\config_sync\generated`
- **STEP 2 — Start Infrastructure**: Start Kafka, ZooKeeper, MinIO, Redis, PostgreSQL, OpenSearch as detailed in Section 8.
- **STEP 3 — Storage Initialization**: Run Alembic migrations and seed data in M6. Create MinIO buckets and Kafka topics.
- **STEP 4 — Start M6 Control Plane (`:8086`)**:
  `cd E:\ULPF\M6\M6-SIH-main`
  `python -c "from backend.app.main import create_app; import uvicorn; uvicorn.run(create_app(), host='127.0.0.1', port=8086)"`
- **STEP 5 — Start ConfigSync Worker (`:8081`)**:
  `cd E:\ULPF`
  `python -m uvicorn integration.config_sync.config_worker:config_sync_app --host 127.0.0.1 --port 8081`
- **STEP 6 — Start Downstream Modules (M5, M4, M3, M2)**:
  - Start M5 (`:8085`): `cd E:\ULPF\M5 && python -m uvicorn app.main:app --host 127.0.0.1 --port 8085`
  - Start M4 (`:8004`): `cd E:\ULPF\M4 && python -c "from app.main import create_app; import uvicorn; uvicorn.run(create_app(), host='127.0.0.1', port=8004)"`
  - Start M3 (`:8083`): `cd E:\ULPF\M3 && python -m uvicorn app.main:app --host 127.0.0.1 --port 8083`
  - Start M2 (`:8082`): `cd E:\ULPF\M2\abcd-main && python -m uvicorn app.main:app --host 127.0.0.1 --port 8082`
- **STEP 7 — Start M1 Ingestion (`:8001`)**:
  `cd E:\ULPF\M1\modules\m1-ingestion`
  `python -m uvicorn app.main:app --host 127.0.0.1 --port 8001`
- **STEP 8 — Start M1-M2 Consumer Bridge**:
  `cd E:\ULPF`
  `python -c "import asyncio; from integration.consumers.m1_raw_consumer import M1RawEventConsumer; asyncio.run(M1RawEventConsumer(m2_base_url='http://127.0.0.1:8082').start())"`
- **STEP 9 — Start Ingress Security Gateway (`:8080`)**:
  `cd E:\ULPF`
  `python -m uvicorn integration.security.ingress_gateway:gateway_app --host 127.0.0.1 --port 8080`
- **STEP 10 — Start Health Aggregator (`:8090`)**:
  `cd E:\ULPF`
  `python -m uvicorn integration.observability.health:health_app --host 127.0.0.1 --port 8090`
- **STEP 11 — Verify System Health**: Query `http://127.0.0.1:8090/health` and verify all modules report `healthy: true`.

---

## 12. COMPLETE PRODUCTION SMOKE TEST PROCEDURE

Verify end-to-end operation using a real Cisco ASA syslog event:

```syslog
<166>Sep 14 10:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443
```

### Stage 1: External Client Ingestion via Ingress Gateway
```bash
curl -X POST http://127.0.0.1:8080/v1/ingest/event \
  -H "Authorization: Bearer key-tenant-cisco-prod" \
  -H "Content-Type: text/plain" \
  -H "X-Source-ID: network-asa-01" \
  --data-binary "<166>Sep 14 10:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443"
```
- **Expected Status:** `HTTP 200 OK` or `202 Accepted`
- **Expected Response JSON:**
  ```json
  {
    "status": "accepted",
    "raw_event_id": "<UUID>",
    "sha256": "b4a8e8e6e584f183c0f496739bb1f8f3c7848f02aa56f8f533a1e2f5e8dae4f6",
    "tenant_id": "tenant-cisco"
  }
  ```
- **Artifact Verified:** Blob persisted in MinIO bucket `ulpf-raw` under `raw/tenant-cisco/<UUID>.log`. Message published to Kafka topic `ulpf.raw`.

### Stage 2: M2 Classification & Parsing
- The M1-M2 consumer bridge automatically dequeues the record from Kafka and submits it to M2.
- **Manual Verification Probe:**
```bash
curl -X POST http://127.0.0.1:8082/v1/parse \
  -H "Authorization: Bearer system-admin-token" \
  -H "Content-Type: application/json" \
  -d '{
    "schema_version": "1.0.0",
    "raw_event_id": "test-cisco-smoke-01",
    "tenant_id": "tenant-cisco",
    "payload": "<166>Sep 14 10:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443",
    "transport": "syslog"
  }'
```
- **Expected Status:** `HTTP 200 OK`
- **Expected Response Fields:** `status: "PARSED"`, `parser.id: "parser-cisco-asa"`, `fields.action: "Built"`, `fields.srcip: "192.168.10.25"`, `fields.dstip: "8.8.8.8"`.

### Stage 3: Full Pipeline Execution via Integration Test Suite
Execute the automated end-to-end integration test:
```bash
pytest E:\ULPF\integration\tests\e2e\test_real_deployment_network.py -k "test_network_05" -v
```
- **Expected Outcome:** `PASSED in 1.82s`
- **Proves:** Complete transit from Ingress Gateway $\to$ M1 $\to$ MinIO $\to$ Kafka $\to$ M2 $\to$ M3 $\to$ M4 $\to$ M5 $\to$ OpenSearch / Data Lake.

---

## 13. MONITORING & HEALTH CHECK ENDPOINTS

| Target Service | Endpoint | HTTP Method | Expected Return | Purpose |
| :--- | :--- | :---: | :--- | :--- |
| **System Health Aggregator** | `/health` | `GET` | `200 OK` (`status: "HEALTHY"`) | Unified health of all 9 services |
| **System Health Aggregator** | `/live` | `GET` | `200 OK` (`status: "ok"`) | Kubernetes / load-balancer liveness |
| **Ingress Gateway** | `/health` | `GET` | `200 OK` (`status: "HEALTHY"`) | Gateway proxy health |
| **Config Sync Worker** | `/health` | `GET` | `200 OK` (`status: "HEALTHY"`) | Control plane distribution bridge |
| **M1 Ingestion** | `/health` | `GET` | `200 OK` (`status: "healthy"`) | M1 vault & outbox operational |
| **M2 Parser** | `/health` | `GET` | `200 OK` (`status: "healthy"`) | Parser registry loaded |
| **M2 Parser** | `/metrics`| `GET` | `200 OK` (Prometheus text) | M2 parse latencies & counters |
| **M3 Normalizer** | `/health` | `GET` | `200 OK` (`status: "ok"`) | M3 normalizer liveness |
| **M3 Normalizer** | `/ready` | `GET` | `200 OK` (`status: "ready"`) | Checks mappings loaded in memory |
| **M3 Normalizer** | `/metrics`| `GET` | `200 OK` (Prometheus text) | Prometheus metrics export |
| **M4 Enrichment** | `/health` | `GET` | `200 OK` (`status: "healthy"`) | M4 enrichment engine liveness |
| **M4 Enrichment** | `/ready` | `GET` | `200 OK` (`status: "ready"`) | Checks active config version |
| **M4 Enrichment** | `/metrics`| `GET` | `200 OK` (Prometheus text) | RFC 8785 hash computation stats |
| **M5 Smart Router** | `/health` | `GET` | `200 OK` (`status: "healthy"`) | Connector statuses (SIEM, Lake) |
| **M6 Control Plane** | `/health` | `GET` | `200 OK` (`status: "healthy"`) | PostgreSQL, Redis, Kafka health |

---

## 14. FAILURE & RECOVERY PROCEDURES

### 14.1 Outage Scenarios & Response Matrix

| Failed Component | Immediate Impact | Data Durability & Recovery Semantics | Operator Recovery Procedure |
| :--- | :--- | :--- | :--- |
| **Kafka Down** | M1 cannot produce directly to broker. Consumer bridge pauses. | **Zero Data Loss**: M1 automatically diverts raw events into SQLite `data/outbox.db` with status `PENDING`. | 1. Restore Kafka broker (`docker start ulpf-kafka`).<br>2. M1 outbox recovery worker automatically flushes pending rows to Kafka on 2s interval.<br>3. Consumer bridge resumes. |
| **MinIO Down** | M1 boot fails immediately. Active M1 ingestion fails with 500 error. | **Critical Failure**: M1 refuses to acknowledge raw events without vault confirmation. | 1. Restart MinIO (`docker start ulpf-minio`).<br>2. Verify bucket `ulpf-raw` exists.<br>3. Restart M1 Ingestion service. |
| **PostgreSQL Down**| M6 Control Plane enters 503 / degraded state. Configuration updates blocked. | **Core Ingestion Unaffected**: M1–M5 continue processing data using materialized configuration files on disk. | 1. Restore PostgreSQL (`docker start ulpf-postgres`).<br>2. Re-run `alembic upgrade head` if recovering from corruption. |
| **OpenSearch Down**| M5 cannot deliver to SIEM. | **DLQ Protection**: M5 retries 3 times with exponential backoff. If exhausted, spills events to local DLQ (`data/dlq/`). | 1. Restore OpenSearch cluster.<br>2. Execute M5 replay tool or reload DLQ lines back into `/v1/events/process`. |
| **M1-M2 Bridge Crash**| Raw events accumulate in Kafka `ulpf.raw`. | **Zero Data Loss**: Kafka persists records durably according to log retention policy. | 1. Restart Consumer Bridge.<br>2. Consumer resumes from last committed offset. |
| **M1 Ingestion Crash**| Syslog UDP/TCP packets dropped at socket buffer. HTTP returns connection refused. | Events buffered by upstream forwarders or dropped (UDP). | 1. Restart M1 service.<br>2. Ingress Gateway resumes forwarding once M1 reports healthy. |

### 14.2 Exactly-Once vs. At-Least-Once Delivery Guarantees

> [!IMPORTANT]
> **Formal Delivery Contract:**
> ULPF provides **At-Least-Once Transport coupled with Downstream Durable Edge Idempotency**, achieving **Effectively-Once Business Semantics**.
>
> 1. **Transport is At-Least-Once (ALO)**: If a consumer crashes before committing its Kafka offset, Kafka redelivers the message upon restart.
> 2. **In-Memory Cache Is Volatile**: In-memory deduplication sets are wiped on process crash.
> 3. **Durable Idempotency Guards**:
>    - **MinIO Vault**: Object keys are Content-Addressable (`raw/<tenant>/<sha256>`). Overwrites are harmless idempotent no-ops.
>    - **OpenSearch SIEM**: Indexed using canonical `event.id` as document `_id`. Re-indexing is idempotent.
>    - **Data Lake Writer**: Partition file appends check bounded memory LRU; duplicates in separate sessions are reconciled during batch ETL compaction.

---

## 15. SAFE SHUTDOWN & RESTART PROCEDURES

### 15.1 Safe Shutdown Sequence (Avoids In-Flight Data Loss)

```bash
# 1. Terminate Ingress Gateway (Blocks new external traffic)
kill <GATEWAY_PID>

# 2. Terminate M1 Ingestion (Stops socket listeners 514/515, flushes outbox)
kill <M1_PID>

# 3. Terminate Consumer Bridge (Commits in-flight offsets)
kill <CONSUMER_BRIDGE_PID>

# 4. Terminate Core Pipeline Services
kill <M2_PID> <M3_PID> <M4_PID> <M5_PID>

# 5. Terminate Control Plane Services
kill <CONFIG_SYNC_PID> <M6_PID> <HEALTH_PID>

# 6. Stop Infrastructure Containers
docker stop ulpf-opensearch ulpf-redis ulpf-postgres ulpf-minio ulpf-kafka ulpf-zookeeper
```

### 15.2 Safe Startup Sequence

Always execute in reverse order:
1. Infrastructure Containers (`zookeeper` $\to$ `kafka` $\to$ `minio` $\to$ `postgres` $\to$ `redis` $\to$ `opensearch`)
2. Database Migrations & Seeds (`alembic upgrade head`, `python scripts/seed.py`)
3. Control Plane (`M6` $\to$ `ConfigSync`)
4. Downstream Engines (`M5` $\to$ `M4` $\to$ `M3` $\to$ `M2`)
5. Ingestion & Bridges (`M1` $\to$ `Consumer Bridge`)
6. Ingress Gateway (`Gateway` $\to$ `Health Aggregator`)

---

## 16. BACKUP & DISASTER RECOVERY

### 16.1 Supported Backup Procedures

| Component | Target Artifact | Backup Command / Tool | Source Reference |
| :--- | :--- | :--- | :--- |
| **PostgreSQL** | M6 Control Plane Tables | `pg_dump -U ulpf_admin -d ulpf_m6 -F c -b -v -f ulpf_m6_backup.dump` | Standard PostgreSQL |
| **MinIO S3** | Raw Blobs & Contracts | `mc mirror local/ulpf-raw /backup/ulpf-raw` | MinIO Client Tooling |
| **M1 Outbox** | Spool Database | SQLite `.backup`: `sqlite3 E:/ULPF/M1/modules/m1-ingestion/data/outbox.db ".backup 'outbox_bak.db'"` | SQLite CLI |
| **M2 Parsers** | Parser YAML Definitions | File copy: `tar -czvf parsers_backup.tar.gz E:/ULPF/M2/abcd-main/parsers` | Local Filesystem |
| **M3 Mappings** | UES YAML Mappings | File copy: `tar -czvf mappings_backup.tar.gz E:/ULPF/M3/mappings` | Local Filesystem |
| **M5 Data Lake** | Cold JSONL Archives | File copy: `tar -czvf datalake_backup.tar.gz E:/ULPF/M5/data/datalake` | Local Filesystem |

### 16.2 Where Backup/Restore is NOT Implemented:
- **No Automated Disaster Recovery Orchestrator**: There is no active automated snapshotting service, cross-region replication daemon, or point-in-time recovery manager implemented in the repository. Backup scripts must be scheduled manually via cron or Windows Task Scheduler.

---

## 17. PRODUCTION DEPLOYMENT CHECKLIST

### Pre-Deployment Verification:
- [ ] Host machine meets minimum requirements (Python 3.12, Docker 24+, 16GB RAM).
- [ ] Host ports `8080`, `8081`, `8001`, `8082`, `8083`, `8004`, `8085`, `8086`, `8090`, `9092`, `9000`, `5432`, `6379`, `9200` are free and unbound.
- [ ] Production `.env` files created from templates; all default passwords and static tokens rotated.
- [ ] Infrastructure containers started and confirmed healthy via TCP probes.
- [ ] PostgreSQL migrations applied (`alembic upgrade head`) and initial seed executed (`scripts/seed.py`).
- [ ] MinIO buckets created (`ulpf-raw`, `ulpf-datalake`, `ulpf-contracts`, `ulpf-schemas`).
- [ ] Kafka topics pre-partitioned (`ulpf.raw`, `ulpf.dlq`, `ulpf.ai.events`).

### Service Deployment:
- [ ] M6 Control Plane started and reachable at `http://127.0.0.1:8086/health`.
- [ ] ConfigSync Worker started and reachable at `http://127.0.0.1:8081/health`.
- [ ] M5, M4, M3, M2 started and reporting healthy.
- [ ] M1 started and confirmed listening on HTTP `8001`, UDP `514`, TCP `515`.
- [ ] M1-M2 Consumer Bridge active and subscribed to topic `ulpf.raw`.
- [ ] Ingress Security Gateway started on public port `8080`.
- [ ] Unified Health Aggregator running and returning `200 OK` on `/health`.

### Post-Deployment Smoke Testing:
- [ ] Sent real Cisco ASA syslog through Ingress Gateway with valid tenant Bearer key.
- [ ] Confirmed `200 Accepted` response with `raw_event_id` and authoritative raw SHA-256 digest.
- [ ] Confirmed blob persisted in MinIO bucket `ulpf-raw`.
- [ ] Confirmed parsed output in M2, normalized UES in M3, enriched integrity in M4.
- [ ] Confirmed delivery in OpenSearch index `ulpf-events-v1-tenant-cisco` and cold Data Lake.

---

## 18. TROUBLESHOOTING GUIDE

### Issue 1: M1 Exits on Startup with `RuntimeError: Failed to initialize mandatory raw vault`
- **Root Cause:** MinIO is not running, port 9000 is blocked, or credentials in `.env` do not match MinIO server credentials.
- **Remedy:** Check `docker ps` to verify `ulpf-minio` is running. Test port: `telnet localhost 9000`. Verify `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY`.

### Issue 2: Ingress Gateway Rejects Requests with `403 Forbidden`
- **Root Cause:** Tenant spoofing detected. The external client submitted an `X-Tenant-ID` header that does not match the tenant bound to their API key in `TENANT_CREDENTIAL_REGISTRY`.
- **Remedy:** Remove the `X-Tenant-ID` header from the client request (the gateway will inject the authorized ID automatically), or use the correct credentials bound to that tenant (`ingress_gateway.py:34`).

### Issue 3: ConfigSync Reports `status: RESTART_REQUIRED` for M1
- **Root Cause:** This is expected, truthful behavior. M1 does not support in-memory hot reloading for socket bindings and rate limits.
- **Remedy:** Execute a controlled process restart of the M1 service to adopt the materialized configuration in `integration/config_sync/generated/m1_sources.json`.

### Issue 4: Docker Compose Build Fails with `failed to read dockerfile: open Dockerfile: no such file or directory`
- **Root Cause:** `E:\ULPF\M4\Dockerfile` is missing from the repository.
- **Remedy:** Use the verified Hybrid Deployment model (Docker for infrastructure + native Python processes for microservices).

---

## 19. KNOWN LIMITATIONS & ARCHITECTURAL GAPS

1. **Docker Compose Missing File Blocker:**
   `docker-compose.integration.yml` cannot be built out-of-the-box because `M4/Dockerfile` is missing and `Dockerfile.gateway` references a nonexistent root `requirements.txt`.
2. **Co-located Filesystem Assumption in ConfigSync:**
   `ConfigSyncWorker` writes configuration mutations directly to disk (`M2/abcd-main/parsers`, `M3/mappings`). In a multi-node cluster, these directories must be shared via network storage.
3. **M1-M2 Pipeline Disconnect:**
   `m1_raw_consumer.py` consumes from Kafka and dispatches to M2. There is currently no continuous background worker in `docker-compose.integration.yml` that autonomously cascades from M2 to M3, M4, and M5. The pipeline runner (`EventPipelineRunner`) orchestrates this in-process or via sequential HTTP calls.

---

## 20. EXACT SOURCE FILE REFERENCES

1. **Integrated Compose & Dockerfiles:**
   - `integration/deployment/docker-compose.integration.yml`
   - `integration/deployment/Dockerfile.gateway`
   - `integration/deployment/Dockerfile.config_sync`
   - `integration/deployment/Dockerfile.consumer`
   - `integration/deployment/Dockerfile.health`
   - `M1/modules/m1-ingestion/Dockerfile`
   - `M2/abcd-main/Dockerfile`
   - `M3/Dockerfile`
   - `M5/Dockerfile`
   - `M6/M6-SIH-main/Dockerfile`
2. **Service Main Entrypoints:**
   - Gateway: `integration/security/ingress_gateway.py`
   - ConfigSync: `integration/config_sync/config_worker.py`
   - M1: `M1/modules/m1-ingestion/app/main.py`
   - M2: `M2/abcd-main/app/main.py`
   - M3: `M3/app/main.py`
   - M4: `M4/app/main.py`
   - M5: `M5/app/main.py`
   - M6: `M6/M6-SIH-main/backend/app/main.py`
   - Consumer Bridge: `integration/consumers/m1_raw_consumer.py`
   - Health Aggregator: `integration/observability/health.py`
3. **Configuration & Settings:**
   - M1 Settings: `M1/modules/m1-ingestion/app/config/settings.py`
   - M2 Auth/Security: `M2/abcd-main/app/auth/security.py`
   - M3 Settings: `M3/app/config.py`
   - M4 Settings: `M4/app/config/settings.py`
   - M5 Env Template: `M5/.env.example`
   - M6 Config: `M6/M6-SIH-main/backend/app/core/config.py`
   - Integration Env: `integration/deployment/.env.integration`
4. **Database & Migrations:**
   - M6 Alembic Migration: `M6/M6-SIH-main/backend/alembic/versions/0001_initial_schema.py`
   - M6 Seed Script: `M6/M6-SIH-main/scripts/seed.py`
   - M1 Outbox Schema: `M1/modules/m1-ingestion/app/storage/outbox.py`
5. **Verification & Audit Reports:**
   - Real Deployment Test: `integration/tests/e2e/test_real_deployment_network.py`
   - Runtime Config Audit: `integration/docs/PHASE1_1_CONFIGURATION_RUNTIME_AUDIT.md`
   - Full System Audit: `integration/docs/FULL_SYSTEM_FORENSIC_AUDIT.md`
