# ULPF Phase 0 — Configuration Flow & Distribution Analysis

**Audit Date**: September 14, 2026  
**Status**: Complete  
**Scope**: Configuration governance, registry lifecycles, distribution channels, and synchronization disconnects.

---

## 1. Master Configuration Ownership Matrix

| Configuration Domain | Authoritative Owner (Design) | Runtime Consumer | Actual Implementation in Consumer | Distribution Method (Design) | Distribution Method (Actual Code) | Versioning Mechanism | Rollback Capability | ACK Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Log Source Catalog** | **M6 Control Plane** | M1 (Ingestion) | Static `.env` defaults (`settings.default_source_id`) | Redis / Kafka push | Manual trigger `POST /api/v1/configuration/distribute` | Versioned in M6 PostgreSQL | M6 status flag only | **NONE** (Fire-and-forget) |
| **Parser Definitions** | **M6 Control Plane** | M2 (Parser Engine) | Local filesystem YAML in `./parsers/` | Redis / Kafka / REST | M2 loads files at boot; API `POST /v1/parsers` available | Semantic Versioning (`1.0.0`, `1.1.0`) | Supported via M2 Parser Studio API | **NONE** |
| **UES Canonical Schema**| **M6 Control Plane** | M3 & M4 | M3 embeds Draft 2020-12 schema; M4 embeds Pydantic classes | MinIO bucket / REST | M3 serves `/v1/schema`; M4 hardcoded in `canonical_event.py` | Semantic Versioning (`1.0.0`) | Schema version table in M6 | **NONE** |
| **Field Mappings** | **M6 Control Plane** | M3 (Normalizer) | Local filesystem YAML in `mappings/` | Redis / File sync | Loaded at M3 startup; no dynamic reload endpoint | Version string in YAML mapping header | M6 mapping versions table | **NONE** |
| **Enrichment Rules** | **M6 Control Plane** | M4 (Enrichment) | In-memory rules loaded from local file | HTTP `POST /v1/config/reload` | M4 exposes `/v1/config/reload`, reads local YAML | Monotonic version integer / string | Supported via M4 `ConfigurationManager` | **NONE** |
| **Routing Policies** | **M6 Control Plane** | M5 (Smart Router)| Local YAML file `./policies/default.yaml` | HTTP / File sync | Loaded at M5 startup; internal `reload_policies()` method | Semantic version in policy header | Inactive policy flags in M6 | **NONE** |

---

## 2. Forensic Configuration Disconnects Discovered

### Disconnect 1: The Disconnected Operational Loop in M6
- **Architecture Specification**: M6 claims to act as the live configuration hub, distributing source, parser, mapping, schema, and routing policies to M1–M5 via Redis cache keys and Kafka topic `ulpf.m6.config.updates`.
- **Empirical Implementation**:
  - In M6 (`M6-SIH-main`), administrative changes made through the REST API are committed strictly to PostgreSQL tables.
  - **No automated event trigger** publishes updates to Kafka or Redis upon database commit.
  - Distribution occurs **only** when an external administrator manually invokes `POST /api/v1/configuration/distribute`.
  - Furthermore, M6 has **no acknowledgment or verification loop** to confirm whether downstream modules (M1–M5) received, validated, or applied the configuration.

### Disconnect 2: Static Bootstrapping in M1, M3, and M5
- **M1 (Ingestion)**: Operates entirely on static environment variables (`.env`). It does not poll Redis, subscribe to Kafka configuration topics, or expose a `/config/reload` endpoint. Updating an ingestion rate limit or default source requires an operating system process restart.
- **M3 (Normalizer)**: Loads parser-to-UES field mappings from `mappings/` during startup in `lifespan()`. It possesses no reload API. If M6 approves a new field mapping version, M3 cannot apply it without a full restart.
- **M5 (Router)**: Loads `policies/default.yaml` at application startup. While `PolicyEngine` has a Python method `reload_policies()`, there is no public REST endpoint exposed on `/v1/policies/reload` to trigger it externally.

### Disconnect 3: Divergent Schema Representations
- In M6's schema registry, schemas are stored as generic JSON objects in PostgreSQL.
- In M3, the canonical schema is enforced using JSON Schema Draft 2020-12 (`ues.schema.json`) requiring top-level `"ulpf"`.
- In M4, the canonical schema is compiled into static Python Pydantic models (`CanonicalEvent`) forbidding top-level `"ulpf"`.
- This divergence means schema changes distributed by M6 cannot be dynamically compiled by M4 without Python code redeployment.

---

## 3. Required Integration Synchronization Architecture

To bridge these configuration divides in Phase 1:
1. **Config Worker Daemon**: An integration configuration synchronization agent must listen to M6's distribution endpoint or PostgreSQL change events.
2. **File Materialization**: The agent must automatically materialize approved YAML parsers into M2's `./parsers/` directory, YAML mappings into M3's `mappings/` directory, and policies into M5's `policies/` directory.
3. **Trigger Signals**: Call M4's `POST /v1/config/reload` and invoke process reload signals on M1, M2, M3, and M5.
4. **ACK Collector**: Return execution status and applied configuration versions back to M6 for centralized operational visibility.
