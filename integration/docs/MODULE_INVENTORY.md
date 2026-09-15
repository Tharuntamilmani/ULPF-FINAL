# ULPF Phase 0 — Comprehensive Module Forensic Inventory

**Document Version**: 1.0.0  
**Audit Date**: September 14, 2026  
**Status**: Verified against active implementations  

---

## Module 1 (M1): Ingestion Gateway & Immutable Raw Event Vault

- **Repository Path**: `E:\ULPF\M1\modules\m1-ingestion`
- **Responsibility**: Ingest raw untrusted byte streams across HTTP, UDP Syslog, TCP Syslog, and File Replay; compute exact SHA-256 integrity hash over untouched raw bytes; generate RFC 9562 UUIDv7 identifiers; persist raw compressed blobs into MinIO; emit standardized `RawEventEnvelope` to Kafka topic `ulpf.raw`.
- **Core Mental Model**: *"I know HOW an event arrived, WHERE it came from, WHEN we received it, WHAT its original bytes were, and HOW to retrieve it later. I do NOT know what the event means."*
- **Main Entrypoint**: `app/main.py` (`python -m app.main` or `uvicorn app.main:app`)
- **API Endpoints**:
  - `POST /v1/events` (Raw single or batch HTTP ingestion, token-authenticated)
  - `POST /v1/replay/file` (File upload replay endpoint)
  - `GET /health` (Liveness probe)
  - `GET /ready` (Readiness probe verifying MinIO & Kafka/Outbox connectivity)
  - `GET /metrics` (Prometheus metrics scrape)
- **Event Interfaces & Transports**:
  - Outbound: Apache Kafka topic `ulpf.raw` (key: `tenant_id:source_id`)
  - Outbox Fallback: Local SQLite queue (`outbox.db`) with retry background worker
  - Inbound Sockets: UDP socket on port 514, TCP socket on port 515
- **Databases & Datastores**:
  - MinIO (S3-compatible object storage), bucket `ulpf-raw`
  - Local SQLite (`outbox.db`) for crash-resilient store-and-forward spooling
- **External Dependencies**: MinIO, Apache Kafka (with local outbox fallback if Kafka is offline)
- **Configuration Mechanism**: Pydantic BaseSettings loading from `.env` (`app/config/settings.py`)
- **Security & Multi-Tenancy**:
  - Authentication: Static Bearer token verification (`verify_auth_token`)
  - Tenant Extraction: Extracted from `X-Tenant-ID` header (fallback to `settings.default_tenant_id`)
  - Vulnerability / Limitation: Single static token shared across tenants; headers can be spoofed by any authenticated client (`SEC-1.4`).
- **Health & Readiness**: Fully implemented with active ping checks to MinIO and Kafka.
- **Metrics**: Prometheus instrumentation via `prometheus_client` (`M1_INGESTED_EVENTS_TOTAL`, `M1_BYTES_TOTAL`, `M1_INGESTION_LATENCY_SECONDS`, `M1_OUTBOX_QUEUE_SIZE`, `M1_VAULT_FAILURES_TOTAL`).
- **Persistence**: Gzip-compressed raw payload in MinIO with object key format `tenant={tenant}/year={YYYY}/month={MM}/day={DD}/source={source}/event={uuidv7}`.
- **Test Suite**: 43 automated unit and integration tests (`pytest -v tests/`). 100% pass rate.
- **Known Limitations**:
  - In-memory accumulation in `replay_file()` causes excessive RAM usage on files $>50$ MB.
  - Multi-tenant token isolation is not cryptographically bound per tenant.

---

## Module 2 (M2): Format Classifier + Parser Engine + Discovery

- **Repository Path**: `E:\ULPF\M2\abcd-main`
- **Responsibility**: Inspect raw payload format (`json`, `syslog`, `cef`, `leef`, `csv`, `xml`, `kv`, `plain_text`); identify vendor source; execute registered declarative YAML parsers (Grok, Regex, CEF, LEEF, JSON, KV); route unparsed logs to Unknown-Source Discovery Engine; provide Parser Studio API for testing, versioning, and rollback.
- **Main Entrypoint**: `app/main.py` (`uvicorn app.main:app --port 8082`)
- **API Endpoints**:
  - `POST /v1/parse` (Primary parse endpoint; accepts `RawEventEnvelope`, emits `ParsedEvent`)
  - `POST /v1/discover` (Unknown source payload profiling & candidate field detection)
  - `POST /v1/parsers/validate` (Syntax & ReDoS validation for candidate parsers)
  - `POST /v1/parsers/test` (Dry-run parser execution against sample events)
  - `POST /v1/parsers` (Register new parser version)
  - `POST /v1/parsers/{id}/disable` / `enable` / `rollback` (Parser lifecycle management)
  - `POST /v1/replay` (Historical event replay through updated parsers)
  - `GET /health`, `GET /metrics`
- **Event Interfaces & Transports**:
  - Currently exposes HTTP REST API (`POST /v1/parse`).
  - Lacks an active, automated Kafka consumer daemon listening to `ulpf.raw`.
- **Databases & Datastores**:
  - In-memory `ParserRepository` loaded from YAML directory (`./parsers/`).
- **External Dependencies**: None (pure Python engine with `orjson`, `pygrok`, `regex`).
- **Configuration Mechanism**: Environment variable `PARSER_STORAGE_DIR`, loaded at application startup.
- **Security & Multi-Tenancy**:
  - API Key & Role-based access control (`app/auth.py`).
  - Tenant Scoping: Registered parsers can be scoped to specific `tenant_id` or `global`.
  - ReDoS Protection: Safe regular expression evaluator with bounded execution time.
- **Health & Readiness**: `/health` liveness probe and `/metrics` Prometheus telemetry.
- **Metrics**: `ulpf_parser_events_total`, `ulpf_parser_latency_seconds`, `ulpf_parser_confidence_score`, `ulpf_parser_registry_size`.
- **Persistence**: File-based YAML parser definitions in `./parsers/`.
- **Test Suite**: 52 unit, golden log, and performance benchmark tests. 100% pass rate.
- **Known Limitations**:
  - Does not currently unwrap M1's complex `RawEventEnvelope` object format (`payload.data`, `transport.protocol`).
  - Lacks an asynchronous Kafka consumer loop.

---

## Module 3 (M3): Canonical UES Normalization & Validation

- **Repository Path**: `E:\ULPF\M3`
- **Responsibility**: The semantic normalization core of ULPF. Converts `ParsedEvent` into validated Universal Event Schema (UES v1.0.0) format; executes declarative YAML field mappings; performs type conversions and enum normalization; preserves unmapped vendor attributes in `vendor.fields`; validates output against JSON Schema Draft 2020-12 and semantic Python invariants.
- **Main Entrypoint**: `app/main.py` (`uvicorn app.main:app --port 8083`), Frontend in `frontend/` (Vite on port 5173)
- **API Endpoints**:
  - `POST /v1/normalize` (Primary endpoint: `ParsedEvent` $\to$ `NormalizationResult`)
  - `POST /v1/validate` (Validate standalone UES document against JSON schema & semantic rules)
  - `GET /v1/schema` (Canonical JSON Schema Draft 2020-12)
  - `GET /v1/schema/version` (Schema version metadata)
  - `GET /health`, `GET /ready`, `GET /metrics`
- **Event Interfaces & Transports**:
  - Inbound: HTTP REST (`POST /v1/normalize`)
  - Outbound: HTTP response returning JSON `NormalizationResult`
- **Databases & Datastores**:
  - In-memory `MappingResolver` loading YAML mapping definitions from `mappings/`.
- **External Dependencies**: None for backend (frontend uses React, Vite, Tailwind CSS).
- **Configuration Mechanism**: Pydantic settings loading from `.env` (`app/config.py`).
- **Security & Multi-Tenancy**:
  - Request size limiter middleware (default 2 MB).
  - Multi-Tenancy Deficit: M3's `builder.py` and canonical `ULPFBlock` model omit `tenant_id`. Tenant context is lost during M3 transformation.
- **Health & Readiness**: `/health` liveness probe, `/ready` dependency probe, `/metrics` Prometheus counter/histograms.
- **Metrics**: `normalization_events_total`, `normalization_successes_total`, `normalization_partials_total`, `normalization_failures_total`, `normalization_latency_seconds`.
- **Persistence**: File-based YAML mapping files in `mappings/`.
- **Test Suite**: 248 unit, property-based (Hypothesis), schema, golden log, and performance benchmark tests. 100% pass rate.
- **Known Limitations**:
  - Root JSON schema encloses all fields inside `{"ulpf": { ... }}`, whereas downstream M4 and M5 expect flat canonical objects.
  - Omission of `tenant` object in `ULPFBlock`.

---

## Module 4 (M4): Contextual Enrichment + Provenance + Integrity

- **Repository Path**: `E:\ULPF\M4`
- **Responsibility**: Contextual and semantic enrichment (Local CMDB Asset lookup, Subnet GeoIP/ASN lookup, IOC Threat Intelligence indicator matching); strictly additive deterministic merge into `event.extensions["enrichment"]`; comprehensive provenance tracking for every provider; cryptographic integrity calculation and verification using deterministic RFC 8785 Canonical JSON (JCS) and SHA-256.
- **Main Entrypoint**: `app/main.py` (`uvicorn app.main:app --port 8004`)
- **API Endpoints**:
  - `POST /v1/enrich` (Accepts `EnrichmentRequest`, returns `EnrichmentResult`)
  - `POST /v1/verify` (Cryptographic verification of event digest against RFC 8785 canonical bytes)
  - `GET /v1/providers` (Enrichment provider metadata and status)
  - `POST /v1/config/reload` (Hot-reload declarative enrichment rules)
  - `GET /health`, `GET /ready`, `GET /metrics`
- **Event Interfaces & Transports**:
  - Inbound: HTTP REST (`POST /v1/enrich`)
  - Outbound: HTTP response returning `EnrichmentResult`
- **Databases & Datastores**:
  - Local in-memory LRU cache with tenant-keyed partitioning (`app/cache/lru.py`)
  - In-memory Asset, GeoIP, and Threat Intel databases
- **External Dependencies**: Optional outbound HTTP enrichment via `HardenedHttpProvider` (protected by `SSRFGuard`).
- **Configuration Mechanism**: Pydantic BaseSettings (`app/config/settings.py`) and declarative YAML enrichment configuration.
- **Security & Multi-Tenancy**:
  - Multi-Tenancy: `TenantGuard` enforces isolated cache keys (`tenant_id:provider_id:namespace:key`) and rejects cross-tenant submissions.
  - SSRF Protection: `SSRFGuard` blocks loopback, private IPv4/IPv6, link-local, carrier NAT, and cloud metadata (`169.254.169.254`).
  - Secret Sanitization: Recursive masking of bearer tokens, passwords, and sensitive keys.
- **Health & Readiness**: `/health` and `/ready` probes.
- **Metrics**: `m4_enrichment_events_total`, `m4_provider_duration_seconds`, `m4_integrity_verifications_total`, `m4_cache_hits_total`.
- **Persistence**: None (stateless enrichment and ephemeral caching).
- **Test Suite**: 122 unit, property-based (Hypothesis), security (SSRF, tenant traversal), and benchmark tests. 100% pass rate.
- **Known Limitations**:
  - Strict contract validation (`extra="forbid"`) rejects events if wrapped in `{"ulpf": { ... }}`.
  - Requires `tenant.tenant_id` at root of canonical event.

---

## Module 5 (M5): Policy Engine + Smart Routing + Multi-Destination Delivery

- **Repository Path**: `E:\ULPF\M5`
- **Responsibility**: High-throughput rule-based smart routing of enriched UES events; multi-destination delivery to SIEM (OpenSearch), Partitioned Data Lake (JSONL), AI Stream (Kafka `ulpf.ai.events`), and Webhooks (HTTP); retry engine with exponential backoff; local Dead Letter Queue (DLQ) promotion; tenant-isolated API event search.
- **Main Entrypoint**: `app/main.py` (`uvicorn app.main:app --port 8085`)
- **API Endpoints**:
  - `POST /v1/events/process` (Core event processing and smart routing)
  - `POST /api/v1/events` (Direct event ingestion with tenant context)
  - `GET /api/v1/events/{id}` (Event retrieval by event_id with tenant filtering)
  - `POST /api/v1/search` (Structured query search within tenant scope)
  - `GET /health`, `GET /ready`, `GET /metrics`
- **Event Interfaces & Transports**:
  - Inbound: HTTP REST (`POST /v1/events/process`)
  - Outbound Connectors:
    - SIEM: OpenSearch index `ulpf-events-v1-{tenant}`
    - Data Lake: Partitioned local filesystem (`./data/datalake/date=YYYY-MM-DD/tenant={tenant}/events.jsonl`)
    - AI Stream: Apache Kafka topic `ulpf.ai.events`
    - HTTP: Configurable webhook endpoints
- **Databases & Datastores**:
  - Local JSONL Data Lake with LRU deduplication
  - Local JSONL DLQ (`./data/dlq/dlq_events.jsonl`)
  - OpenSearch (mockable or live via connection settings)
- **External Dependencies**: OpenSearch, Apache Kafka (mock connectors enabled by default for resilient standalone operation).
- **Configuration Mechanism**: Environment variables and declarative YAML policies (`policies/default.yaml`).
- **Security & Multi-Tenancy**:
  - Multi-Tenancy: `TenantContext` verification, tenant-isolated data lake paths, tenant-isolated OpenSearch queries.
  - SmartRouter tenant extraction: checks `tenant.id` or root `tenant_id`.
- **Health & Readiness**: `/health` and `/ready` probes.
- **Metrics**: `ROUTING_EVENTS_TOTAL`, `POLICY_MATCHES_TOTAL`, `DELIVERY_SUCCESS_TOTAL`, `DELIVERY_FAILURE_TOTAL`, `DELIVERY_RETRIES_TOTAL`.
- **Persistence**: Partitioned local filesystem JSONL files.
- **Test Suite**: 44 unit, connector, failure, integration, and security scenarios. 100% pass rate.
- **Known Limitations**:
  - `SmartRouter.extract_tenant_id` looks for `tenant.id` or root `tenant_id`, missing M4's `tenant.tenant_id`.
  - Ingestion endpoint `/v1/events/process` lacks an asynchronous Kafka consumer daemon.

---

## Module 6 (M6): Control Plane + Registries + Observability

- **Repository Path**: `E:\ULPF\M6\M6-SIH-main`
- **Responsibility**: Platform administration, metadata, and observability hub. Manages source registries, parser lifecycle (DRAFT $\to$ ACTIVE), UES schema registry, field mapping registry, and routing policy configuration. Exposes JWT authentication, RBAC, append-only audit trail, inter-module health check polling, and centralized Prometheus metrics.
- **Main Entrypoint**: `backend/app/main.py` (`uvicorn backend.app.main:app`), Frontend in `frontend/` (React/Vite)
- **API Endpoints**:
  - `POST /api/v1/auth/login` (JWT token issuance)
  - `GET / POST / PUT / DELETE /api/v1/sources` (Log Source Registry)
  - `GET / POST / PUT /api/v1/parsers` (Parser Registry and version lifecycle)
  - `GET / POST /api/v1/schemas` (Schema Registry)
  - `GET / POST / PUT /api/v1/mappings` (Field Mapping Registry)
  - `GET / POST / PUT /api/v1/policies` (Routing Policy Registry)
  - `POST /api/v1/configuration/distribute` (Trigger config distribution to modules)
  - `GET /api/v1/audit` (Append-only audit trail query)
  - `GET /api/v1/health` (Aggregated platform health including M1–M5 probes)
  - `GET /metrics` (Centralized Prometheus telemetry)
- **Event Interfaces & Transports**:
  - HTTP client (`HttpModuleClient`) for health checking M1–M5.
  - Redis publisher and Kafka config topic client.
- **Databases & Datastores**:
  - PostgreSQL (relational tables for registries, users, versions, audit logs)
  - Redis (caching and configuration distribution keys)
- **External Dependencies**: PostgreSQL, Redis, Apache Kafka.
- **Configuration Mechanism**: Pydantic BaseSettings loading from `.env` (`backend/app/core/config.py`).
- **Security & Multi-Tenancy**:
  - JWT tokens with SHA-256 / bcrypt password hashing.
  - 4 RBAC roles: `ADMINISTRATOR`, `PARSER_DEVELOPER`, `SECURITY_ANALYST`, `VIEWER`.
  - Multi-Tenancy Deficit: User authentication is platform-global; audit log lacks mandatory `tenant_id` enforcement.
- **Health & Readiness**: Comprehensive system aggregation checking PostgreSQL, Redis, Kafka, and M1–M5 endpoints.
- **Metrics**: Exposes `ulpf_m6_*` metric namespace.
- **Persistence**: Relational database via SQLAlchemy 2.0 and Alembic migrations.
- **Test Suite**: 163 unit, contract, integration, and API tests. 100% pass rate.
- **Known Limitations**:
  - Configuration distribution requires an explicit manual trigger (`POST /api/v1/configuration/distribute`); no continuous synchronization loop exists.
  - Lacks ACK tracking to confirm whether downstream modules have successfully applied updated configurations.
