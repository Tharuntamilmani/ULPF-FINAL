# Universal Log Pre-processing Framework (ULPF)
### High-Throughput, Multi-Tenant Telemetry Normalization & Control-Plane Architecture

> **Working Prototype Status: FULLY OPERATIONAL**  
> All 6 microservice engines (M1–M6), the Kafka event pipeline, the Ingress Gateway, the Health Aggregator, and both Web User Interfaces are integrated, tested end-to-end, and runnable via a unified deployment supervisor.

## Architecture Overview

ULPF is designed to ingest raw enterprise security logs (Syslog, JSON, Windows Events, Cisco ASA, Fortinet, Palo Alto), preserve immutable cryptographic evidence, classify formats, parse fields, normalize into the **Universal Event Schema (UES v1.0.0)**, enrich context, and route dynamically to downstream destinations (OpenSearch, S3 Data Lake, Kafka).

```
External Security Client / Syslog Source
               │
               ▼
   [ Ingress Security Gateway ] (:18080)
   - Tenant Boundary Enforcement & Anti-Spoofing
               │
               ▼
   [ M1: Ingestion & Raw Vault Boundary ] (:18001)
   - Cryptographic Hashing (SHA-256)
   - MinIO Object Storage Cold Vault (:9000)
   - Durable SQLite Outbox
               │
               ▼
        [ Apache Kafka ] (:9092)
        - Topic: ulpf.raw (Partitioned)
               │
               ▼
   [ M1 → M2 Consumer Bridge ]
   - At-Least-Once Delivery & Idempotency Filter
               │
               ▼
   [ M2: Format Classifier & Parser Engine ] (:18082)
   - Regex Engines & ReDoS Polynomial Backtracking Guard
   - Dynamic Parser Studio & Sandbox Test Runner
               │
               ▼
   [ M3: UES Canonical Normalizer ] (:18083)
   - Universal Event Schema v1.0.0 Synthesis
   - Preserved Vendor Fields & Provenance Tracing
               │
               ▼
   [ M4: Context Enrichment Engine ] (:18004)
   - GeoIP, Asset Metadata & Threat Intelligence
               │
               ▼
   [ M5: Smart Router & Delivery Engine ] (:18085)
   - Routing Policy Evaluation & DLQ Retries
   - OpenSearch Hot Storage (:9200) & S3 Cold Archival
```

### Control Plane & Observability
```
       [ M6: Central Control Plane ] (:18086)
       - PostgreSQL Multi-Tenant DB (:5432)
       - Tenant, Source, Parser, Mapping, & Policy CRUD
       - RBAC (Admin, Analyst, Viewer) & Audit Logging
                         │
                         ▼
        [ ConfigurationSync Worker ] (:18081)
        - Redis Distributed Bus (:6379)
        - Atomic Version Distribution to M1–M5

       [ System Health Aggregator ] (:18090)
       - Probes Live Telemetry Across All 8 Services
```

## Web User Interfaces

ULPF provides two dedicated web consoles:

| Application | Port | Technology | Primary Role |
| :--- | :---: | :--- | :--- |
| **M6 Control Plane Dashboard** | `5173` | React 18, TypeScript, TailwindCSS, Vite | Security operations, tenant administration, pipeline monitor, configuration deployment, and live event explorer. |
| **M3 Developer Normalizer Console**| `5174` | React 18, TypeScript, Vite | Parser and mapping developer workspace, live raw syslog test console, and Canonical UES inspector. |

### Web Access & Default Credentials
- **M6 Admin Control Plane**: [http://127.0.0.1:5173](http://127.0.0.1:5173)
  - **Username**: `admin`
  - **Password**: `Admin_Secure_Pass_2026!`
- **M3 Normalizer Console**: [http://127.0.0.1:5174](http://127.0.0.1:5174)

---

## Quickstart: Launching the Prototype

### Prerequisites
1. **Docker Desktop** (running with Linux containers)
2. **Python 3.12+**
3. **Node.js 20+** and **npm**
4. **PostgreSQL 16+** (Local port 5432 with database `ulpf_m6`)

### Launch Complete Stack (Backend + Infrastructure + Web UIs)
Run the automated supervisor:
```powershell
python run_stack.py --with-ui
```
The supervisor sequentially executes:
1. Docker container initialization and readiness probing (Kafka, ZooKeeper, MinIO, Redis, OpenSearch).
2. PostgreSQL database schema verification.
3. Microservice startup (M6, ConfigSync, M1, M2, M3, M4, M5, Gateway, Health Aggregator).
4. M1→M2 Kafka consumer bridge activation.
5. Web frontend dev server launch with reverse proxy bindings.
6. Probes all health endpoints and reports `ULPF INTEGRATED PIPELINE READY`.

### Stop All Services Cleanly
```powershell
python run_stack.py --stop
```

## Automated Verification & Testing

Execute the end-to-end verification suite:
```powershell
python integration/scratch/verify_web_e2e.py
```
This suite verifies:
- Web UIs served on ports `5173` and `5174`
- OAuth2 login and JWT session validation
- Real tenant querying and isolation
- System Health Aggregator reporting all 8 modules `HEALTHY`
- M2 Regex parsing of live raw Cisco ASA logs
- M3 Normalization into Canonical UES v1.0.0
- Live event injection through Ingress Gateway into Kafka and OpenSearch


## Repository Structure

```
E:\ULPF
├── M1/               # Ingestion Boundary, UDP/TCP Syslog, MinIO Vault, Outbox
├── M2/               # Format Classifier, Parser Engine, ReDoS Validator
├── M3/               # Universal Event Schema (UES v1.0.0) Normalizer & Frontend
├── M4/               # Context Enrichment Engine
├── M5/               # Smart Router, Delivery Connectors, OpenSearch Client
├── M6/               # Admin Control Plane Backend & Frontend Dashboard
├── integration/      # Security Gateway, ConfigSync, Health Aggregator, Bridge
├── run_stack.py      # Unified Deployment Supervisor & Process Orchestrator
└── README.md         # Architecture, Overview, and Quickstart
```


## License & Purpose
This codebase is developed as an integrated prototype for the **Universal Log Pre-processing Framework (ULPF)**. It demonstrates high-throughput log ingestion, semantic normalization, multi-tenant isolation, and central control-plane governance.
