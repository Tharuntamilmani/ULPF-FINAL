# M6 Control Plane — Architecture Document

> **ULPF — Universal Log Processing Framework**
> Module 6: Control Plane + Observability + Deployment + Final Integration

---

## 1. Position in the System

```
                 ┌─────────────────────────────────────────┐
                 │           M6 CONTROL PLANE              │
                 │                                         │
                 │  Configuration Registry                 │
                 │  Parser Registry                        │
                 │  Schema Registry                        │
                 │  Mapping Registry                       │
                 │  Routing Policy Management              │
                 │  Authentication / RBAC                  │
                 │  Audit Trail                            │
                 │  Health Monitoring                      │
                 │  Prometheus Metrics                     │
                 │  Configuration Distribution (Redis)     │
                 │  Replay Management                      │
                 │  Deployment & CI/CD                     │
                 └─────────────┬───────────────────────────┘
                               │ HTTP / Kafka (config change events)
              ┌────────────────┼────────────────┬──────────────┐
              │                │                │              │
              ▼                ▼                ▼              ▼
           M1 (ext)         M2 (ext)         M3 (ext)      M4 (ext)
         Ingestion          Parser         Normalizer     Enrichment
                                                              │
                                                              ▼
                                                          M5 (ext)
                                                        SIEM Delivery

Infrastructure (owned/observed by M6):
  PostgreSQL · Redis · Kafka · MinIO · OpenSearch · Prometheus · Grafana
```

M6 is the **operator** of the platform. It does not process events.

---

## 2. Independence Contract

| Concern | Owner | M6 role |
|---|---|---|
| Event ingestion | M1 | Store source metadata only |
| Event parsing | M2 | Store parser metadata + lifecycle |
| Event normalisation | M3 | Store UES schema + distribute |
| Event enrichment | M4 | Store mapping metadata |
| SIEM delivery | M5 | Store routing policies |
| Infrastructure health | Infra | Observe + report |
| Configuration distribution | **M6** | Own + publish |
| Audit & RBAC | **M6** | Own |
| Replay coordination | **M6** | Own request lifecycle |

---

## 3. Backend Layer Architecture

```
HTTP Request
     │
     ▼
FastAPI Router (thin — validates input, calls service)
     │
     ▼
Service Layer (business logic, state machines, audit calls)
     │
     ├──► Repository (SQLAlchemy async, PostgreSQL)
     │
     ├──► Integration Adapter (external M1–M5 via HTTP)
     │         └── Real adapter   (production)
     │         └── Mock adapter   (dev / test / CI)
     │
     ├──► Redis client (config distribution)
     │
     └──► Kafka client (config-change events, replay requests)
```

---

## 4. Database Ownership

M6 PostgreSQL database: `m6_control_plane`

Tables owned exclusively by M6:

| Table | Purpose |
|---|---|
| `users` | Auth identities |
| `roles` | RBAC role definitions |
| `user_roles` | Many-to-many assignment |
| `sources` | Log source metadata |
| `parsers` | Parser metadata |
| `parser_versions` | Parser version history |
| `schemas` | UES/event schema metadata |
| `schema_versions` | Schema version history |
| `mappings` | Field mapping metadata |
| `mapping_versions` | Mapping version history |
| `policies` | Routing policy configuration |
| `policy_versions` | Policy version history |
| `services` | Known external services |
| `configuration_versions` | Config distribution history |
| `audit_logs` | Append-only audit trail |
| `replay_operations` | Replay request tracking |

M1–M5 do NOT access this database.

---

## 5. Redis Key Namespace

Published by M6, consumed by M1–M5 via their own client libraries:

```
config:sources        JSON array of active sources
config:parsers        JSON array of active parsers
config:schemas        JSON map name→version→schema
config:mappings       JSON array of active mappings
config:policies       JSON array of active policies
```

Version metadata:

```
config:version        Current monotonic config version
config:updated_at     ISO-8601 timestamp
```

---

## 6. Kafka Topics

| Topic | Producer | Consumer |
|---|---|---|
| `ulpf.raw` | M1 | M2 |
| `ulpf.parsed` | M2 | M3 |
| `ulpf.normalized` | M3 | M4 |
| `ulpf.enriched` | M4 | M5 |
| `ulpf.ai.events` | M4 | AI consumers |
| `ulpf.replay` | **M6** | M1/M2 |
| `ulpf.parser.dlq` | M2 | Ops |
| `ulpf.validation.dlq` | M3 | Ops |
| `ulpf.delivery.dlq` | M5 | Ops |
| `ulpf.m6.config.updates` | **M6** | M1–M5 |

M6 only produces to `ulpf.replay` and `ulpf.m6.config.updates`.

---

## 7. Parser Lifecycle State Machine

```
DRAFT
  │
  ▼
PENDING_APPROVAL  ◄── (reviewer rejects → back to DRAFT)
  │
  ▼
APPROVED
  │
  ▼
ACTIVE  ──────────────────────────────────────► ROLLED_BACK
  │
  ▼
DISABLED
```

Valid transitions:

| From | To | Action |
|---|---|---|
| DRAFT | PENDING_APPROVAL | submit |
| PENDING_APPROVAL | APPROVED | approve |
| PENDING_APPROVAL | DRAFT | reject |
| APPROVED | ACTIVE | activate |
| ACTIVE | DISABLED | disable |
| ACTIVE | ROLLED_BACK | rollback |
| ROLLED_BACK | ACTIVE | re-activate |
| DISABLED | ACTIVE | re-activate |

---

## 8. RBAC Matrix

| Permission | ADMINISTRATOR | PARSER_DEVELOPER | SECURITY_ANALYST | VIEWER |
|---|:---:|:---:|:---:|:---:|
| Create/update sources | ✓ | | | |
| View sources | ✓ | ✓ | ✓ | ✓ |
| Manage parsers | ✓ | ✓ | | |
| View parsers | ✓ | ✓ | ✓ | ✓ |
| Approve parsers | ✓ | | | |
| Manage schemas | ✓ | ✓ | | |
| Manage mappings | ✓ | ✓ | | |
| View mappings | ✓ | ✓ | ✓ | ✓ |
| Manage policies | ✓ | | | |
| View policies | ✓ | ✓ | ✓ | ✓ |
| View audit logs | ✓ | ✓ | ✓ | ✓ |
| View service health | ✓ | ✓ | ✓ | ✓ |
| Manage users | ✓ | | | |
| Request replay | ✓ | ✓ | ✓ | |

---

## 9. Health Status Model

M6 never fabricates health. Statuses:

| Status | Meaning |
|---|---|
| `HEALTHY` | Service responded OK within timeout |
| `DEGRADED` | Service responded but with warnings |
| `UNHEALTHY` | Service responded with error |
| `UNAVAILABLE` | Connection refused / timeout |
| `UNKNOWN` | Not yet checked |

---

## 10. External M1–M5 Integration Contract

Any M1–M5 team must expose:

```
GET /health   → HealthResponse (see contracts/health/v1/schema.json)
GET /ready    → ReadinessResponse
GET /metrics  → Prometheus text format
```

M6 reads `M{n}_BASE_URL` from environment.

No source-code change in M6 is needed to connect a new M1–M5 implementation.

See `docs/external-integration-guide.md` for the full onboarding procedure.

---

## 11. Secrets Management

All secrets come from environment variables. No hard-coded credentials.

Required secrets:

```
SECRET_KEY         JWT signing key
POSTGRES_PASSWORD  Database password
REDIS_PASSWORD     Redis auth
ADMIN_PASSWORD     Bootstrap admin (seed only)
MINIO_SECRET_KEY   Object storage
```

For production, integrate with HashiCorp Vault or AWS Secrets Manager by
overriding the `Settings` loader in `backend/app/core/config.py`.

---

## 12. Dependency Graph

```
m6-api
  ├── PostgreSQL   (required — readiness fails without it)
  ├── Redis        (required — readiness fails without it)
  ├── Kafka        (optional — config publish skipped if unavailable)
  ├── MinIO        (optional — contract storage)
  ├── OpenSearch   (optional — audit index)
  ├── Prometheus   (optional — scrape target)
  ├── Grafana      (optional — dashboard)
  ├── M1–M5        (optional — health reported as UNAVAILABLE if absent)
  └── Prometheus   (optional)
```
