# ULPF M6 — Control Plane

> **This repository implements Module 6 (M6) only.**
>
> M1 (Ingestion), M2 (Parser), M3 (Normalizer), M4 (Enrichment), and M5 (SIEM Delivery)
> are **external services**. They do not exist in this repository and are not required
> to run M6. When absent, M6 correctly reports them as `UNAVAILABLE`.

---

## What is M6?

M6 is the **control tower** of the Universal Log Processing Framework (ULPF). It answers:

> *"How do we operate, configure, observe, secure, test, and deploy the entire ULPF platform?"*

M6 owns:

| Responsibility | Detail |
|---|---|
| **Source Registry** | Metadata for every log source (vendor, protocol, transport, parser assignment) |
| **Parser Registry** | Parser lifecycle management: DRAFT → PENDING_APPROVAL → APPROVED → ACTIVE |
| **Schema Registry** | UES v1.0.0 / v1.1.0 / v2.0.0 schema storage and distribution |
| **Mapping Registry** | Field-mapping metadata (source format → UES target) |
| **Policy Management** | Routing policy configuration with priority + conditions |
| **Configuration Distribution** | PostgreSQL → M6 → Redis → M1–M5 (one-way push) |
| **Authentication + RBAC** | JWT, bcrypt, 4 roles (ADMINISTRATOR, PARSER_DEVELOPER, SECURITY_ANALYST, VIEWER) |
| **Audit Trail** | Append-only log of every administrative action |
| **Health Monitoring** | Real-time status for M1–M5 + all infrastructure services |
| **Prometheus Metrics** | Full `ulpf_m6_*` metric namespace exposed at `/metrics` |
| **Grafana Dashboards** | Pre-provisioned dashboard via Docker Compose |
| **Replay Management** | Kafka-based replay request lifecycle |
| **Contract Validation** | JSON Schema contracts for all inter-module data formats |
| **Docker Compose** | M6 + PostgreSQL + Redis + Kafka + MinIO + OpenSearch + Prometheus + Grafana |
| **CI/CD** | GitHub Actions — lint, test, Docker build, Trivy scan, GHCR push |
| **Air-gap Deployment** | Offline image bundle + import scripts |

M6 does **NOT** own: event ingestion, parsing, normalisation, enrichment, or SIEM delivery. Those belong to M1–M5.

---

## Architecture

```
                 ┌──────────────────────────────────────────┐
                 │            M6 CONTROL PLANE              │
                 │  FastAPI · PostgreSQL · Redis · Kafka     │
                 │                                          │
                 │  Registries  Config Distribution         │
                 │  Auth/RBAC   Audit Trail                 │
                 │  Health      Metrics   Replay            │
                 └─────────────────┬────────────────────────┘
                                   │  HTTP health checks
                                   │  Redis config keys
                                   │  Kafka config events
                 ┌─────────────────┼──────────────────────┐
                 │                 │                        │
           M1 (ext)          M2 (ext)               M3 (ext)
         Ingestion            Parser               Normalizer
                                   │
                             M4 (ext)
                            Enrichment
                                   │
                             M5 (ext)
                           SIEM Delivery

Infrastructure (observed by M6):
  PostgreSQL · Redis · Kafka · MinIO · OpenSearch · Prometheus · Grafana
```

---

## Quick Start (Standalone — no M1–M5 needed)

### Prerequisites

- Docker Engine 24+
- Docker Compose v2
- Python 3.12+ (for local dev / migrations)
- Node.js 20+ (for frontend dev)

### 1. Clone and configure

```bash
git clone <this-repo> m6-control-plane
cd m6-control-plane
cp .env.example .env
```

Edit `.env` — at minimum set these:

```bash
SECRET_KEY=$(openssl rand -hex 32)          # REQUIRED
POSTGRES_PASSWORD=your_postgres_password     # REQUIRED
ADMIN_PASSWORD=YourAdmin@Password123         # REQUIRED
```

### 2. Start the stack

```bash
docker compose up -d
```

This starts: `m6-api`, `postgres`, `redis`, `kafka`, `minio`, `opensearch`, `prometheus`, `grafana`.

M1–M5 are **not** started. They will appear as `UNAVAILABLE` in the dashboard — which is the correct, expected behaviour.

### 3. Wait for health checks

```bash
docker compose ps
# All services should show "healthy" within ~60 seconds
```

### 4. Run database migrations

```bash
docker compose exec m6-api python -m alembic -c backend/alembic.ini upgrade head
```

### 5. Seed bootstrap data

```bash
docker compose exec m6-api python scripts/seed.py
```

### 6. Access the platform

| Service | URL | Credentials |
|---|---|---|
| M6 API | http://localhost:8000 | — |
| Swagger UI | http://localhost:8000/docs | — |
| Grafana | http://localhost:3000 | admin / `GRAFANA_PASSWORD` |
| Prometheus | http://localhost:9090 | — |
| MinIO Console | http://localhost:9001 | minioadmin / `MINIO_SECRET_KEY` |
| Frontend (dev) | http://localhost:5173 | Run `make dev-frontend` |

Login to the API:

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=admin&password=YourAdmin@Password123"
```

---

## Folder Structure

```
m6-control-plane/
├── backend/
│   ├── app/
│   │   ├── api/            Route handlers (thin — delegate to services)
│   │   ├── core/           Config, security, logging, exceptions, RBAC, deps
│   │   ├── db/             SQLAlchemy engine, base, session
│   │   ├── models/         ORM models (16 tables — M6 only)
│   │   ├── schemas/        Pydantic request/response models
│   │   ├── repositories/   Data-access layer (async SQLAlchemy)
│   │   ├── services/       Business logic (config distribution, replay)
│   │   ├── registry/       Source/Parser/Schema/Mapping/Policy registries
│   │   ├── audit/          Append-only audit service
│   │   ├── health/         Health aggregation
│   │   ├── metrics/        Prometheus metrics registry
│   │   └── integrations/   M1–M5 adapters, Kafka, Redis, OpenSearch, MinIO
│   └── alembic/            Database migrations
├── frontend/               React + TypeScript + Vite dashboard
├── contracts/              JSON Schema contracts (interface definitions only)
├── deployment/
│   ├── airgapped/          Air-gap export/import/package scripts
│   ├── prometheus/         Prometheus scrape config
│   └── grafana/            Dashboard provisioning
├── tests/
│   ├── unit/               Registry, auth, audit, adapter unit tests
│   ├── api/                HTTP endpoint tests (httpx + FastAPI test client)
│   ├── integration/        Adapter integration tests (mock-based)
│   ├── contract/           JSON schema contract validation tests
│   └── fixtures/           Shared test payloads
├── scripts/
│   ├── seed.py             Bootstrap database with demo data
│   └── verify_imports.py   Dependency check
├── docs/
│   ├── architecture.md     Architecture documentation
│   ├── external-integration-guide.md
│   └── sih-demo.md
├── .github/workflows/
│   ├── ci.yml              Main CI pipeline
│   └── integration-tests.yml  Optional M1–M5 integration tests
├── docker-compose.yml
├── Dockerfile
├── Makefile
├── pyproject.toml
├── requirements.txt
└── .env.example
```

---

## Environment Variables

See [`.env.example`](.env.example) for the full list. Critical variables:

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | JWT signing key — minimum 32 chars |
| `POSTGRES_PASSWORD` | ✅ | PostgreSQL password |
| `ADMIN_PASSWORD` | ✅ | Initial admin user password (seed only) |
| `M1_BASE_URL` | Optional | M1 Ingestion base URL — leave empty if not deployed |
| `M2_BASE_URL` | Optional | M2 Parser base URL |
| `M3_BASE_URL` | Optional | M3 Normalizer base URL |
| `M4_BASE_URL` | Optional | M4 Enrichment base URL |
| `M5_BASE_URL` | Optional | M5 SIEM Delivery base URL |
| `USE_MOCK_ADAPTERS` | Dev/CI | `true` = use mock adapters (never call real M1–M5) |
| `KAFKA_ENABLED` | Optional | `false` to disable Kafka publish |

---

## API Reference

Full interactive docs: **http://localhost:8000/docs**

### Core endpoints

```
GET  /health                        Liveness probe
GET  /ready                         Readiness probe (PostgreSQL + Redis)
GET  /metrics                       Prometheus metrics

POST /api/v1/auth/login             Authenticate → JWT token
GET  /api/v1/auth/me                Current user

GET  /api/v1/sources                List sources (paginated, filterable)
POST /api/v1/sources                Register source
GET  /api/v1/sources/{id}           Get source
PUT  /api/v1/sources/{id}           Update source
DELETE /api/v1/sources/{id}         Delete source
POST /api/v1/sources/{id}/enable    Enable source
POST /api/v1/sources/{id}/disable   Disable source

GET  /api/v1/parsers                List parsers
POST /api/v1/parsers                Register parser
GET  /api/v1/parsers/{id}           Get parser
PUT  /api/v1/parsers/{id}           Update parser
POST /api/v1/parsers/{id}/submit    DRAFT → PENDING_APPROVAL
POST /api/v1/parsers/{id}/approve   PENDING_APPROVAL → APPROVED
POST /api/v1/parsers/{id}/activate  APPROVED → ACTIVE
POST /api/v1/parsers/{id}/disable   ACTIVE → DISABLED
POST /api/v1/parsers/{id}/rollback  ACTIVE → ROLLED_BACK
GET  /api/v1/parsers/{id}/history   Version history

GET  /api/v1/schemas                List schemas
POST /api/v1/schemas                Create schema
GET  /api/v1/schemas/{name}         Get schema with all versions
GET  /api/v1/schemas/{name}/{ver}   Get specific version

GET  /api/v1/mappings               List mappings
POST /api/v1/mappings               Create mapping
GET  /api/v1/mappings/{id}          Get mapping
PUT  /api/v1/mappings/{id}          Update mapping

GET  /api/v1/policies               List policies
POST /api/v1/policies               Create policy
GET  /api/v1/policies/{id}          Get policy
PUT  /api/v1/policies/{id}          Update policy
POST /api/v1/policies/{id}/enable   Enable policy
POST /api/v1/policies/{id}/disable  Disable policy

GET  /api/v1/services               All service health (M1–M5 + infra)
GET  /api/v1/services/{service}     Single service health

GET  /api/v1/audit                  Audit log (paginated, filterable)

POST /api/v1/replay/{event_id}      Request event replay
GET  /api/v1/replay                 List replay operations
GET  /api/v1/replay/{id}            Get replay operation

GET  /api/v1/configuration          Current Redis config snapshot
POST /api/v1/configuration/distribute      Push all config to Redis
POST /api/v1/configuration/distribute/{key} Push one key

GET  /api/v1/kafka/topics           List Kafka topics
POST /api/v1/kafka/topics/provision Provision ULPF topics
GET  /api/v1/kafka/health           Kafka health
```

---

## Authentication and RBAC

### Login

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=Admin@12345"
# Returns: {"access_token": "...", "token_type": "bearer", "expires_in": 3600}
```

Use the token in subsequent requests:

```bash
curl http://localhost:8000/api/v1/sources \
  -H "Authorization: Bearer <token>"
```

### Roles

| Role | Permissions |
|---|---|
| `ADMINISTRATOR` | Full control — all operations |
| `PARSER_DEVELOPER` | Manage parsers, mappings; view everything |
| `SECURITY_ANALYST` | View services, configs, audits; request replays |
| `VIEWER` | Read-only access to all registries |

---

## Database Setup

M6 uses its own PostgreSQL database. It does **not** create or access M1–M5 databases.

### Run migrations

```bash
# Via Docker Compose (recommended)
docker compose exec m6-api python -m alembic -c backend/alembic.ini upgrade head

# Local (requires DATABASE_URL in environment)
cd backend && alembic upgrade head
```

### Rollback

```bash
docker compose exec m6-api python -m alembic -c backend/alembic.ini downgrade -1
```

---

## Redis Configuration Distribution

M6 pushes configuration to Redis so M1–M5 can read it without querying M6's database directly.

### Keys published

```
config:sources     → Active source metadata (JSON array)
config:parsers     → Active parser metadata (JSON array)
config:schemas     → Schema map name→version→json_schema
config:mappings    → Active mapping metadata (JSON array)
config:policies    → Enabled policies (JSON array, priority-sorted)
config:version     → Monotonic version number
config:updated_at  → ISO-8601 last-updated timestamp
```

### Push all config

```bash
curl -X POST http://localhost:8000/api/v1/configuration/distribute \
  -H "Authorization: Bearer <admin-token>"
```

### Read from Redis directly

```bash
docker compose exec redis redis-cli GET config:sources
docker compose exec redis redis-cli GET config:version
```

---

## Kafka

M6 publishes to two topics:

| Topic | Purpose |
|---|---|
| `ulpf.m6.config.updates` | Notify M1–M5 of configuration changes |
| `ulpf.replay` | Dispatch replay requests to M1/M2 |

M6 does **not** consume any event-processing topics (`ulpf.raw`, `ulpf.parsed`, etc.).

### Provision ULPF topics

```bash
curl -X POST http://localhost:8000/api/v1/kafka/topics/provision \
  -H "Authorization: Bearer <admin-token>"
```

---

## Prometheus Metrics

Available at `GET /metrics` (no authentication required).

Key metrics:

| Metric | Type | Description |
|---|---|---|
| `ulpf_m6_api_requests_total` | Counter | API requests by method/endpoint/status |
| `ulpf_m6_api_request_latency_seconds` | Histogram | Request latency |
| `ulpf_m6_registry_operations_total` | Counter | Registry CRUD ops |
| `ulpf_m6_configuration_changes_total` | Counter | Config distribution events |
| `ulpf_m6_audit_events_total` | Counter | Audit events |
| `ulpf_m6_replay_operations_total` | Counter | Replay requests |
| `ulpf_m6_service_health_status` | Gauge | 1=HEALTHY, 0=not healthy per service |
| `ulpf_m6_postgres_health` | Gauge | PostgreSQL health |
| `ulpf_m6_redis_health` | Gauge | Redis health |
| `ulpf_m6_kafka_health` | Gauge | Kafka health |

---

## Grafana

Pre-provisioned dashboard at **http://localhost:3000** (admin / `GRAFANA_PASSWORD`).

Dashboard: `ULPF M6 Control Plane` — includes API request rate, p95 latency, service health table, config version.

---

## Contracts

JSON Schema contracts for all inter-module data formats are in `contracts/`.

```
contracts/
├── raw_event/v1/schema.json       RawEventEnvelope (M1 → M2)
├── parsed_event/v1/schema.json    ParsedEvent (M2 → M3)
├── ues/v1.0.0/schema.json         UES v1.0.0 (M3 → M4)
├── ues/v1.1.0/schema.json         UES v1.1.0 (backward compatible)
├── ues/v2.0.0/schema.json         UES v2.0.0 (breaking: severity required)
├── enrichment/v1/schema.json      EnrichedUES (M4 → M5)
├── routing/v1/schema.json         RoutingConfig (M6 → M5 via Redis)
├── health/v1/schema.json          HealthResponse (M1–M5 must expose)
├── replay/v1/schema.json          ReplayRequest (M6 → Kafka)
├── audit/v1/schema.json           AuditEvent
└── configuration/v1/schema.json   ConfigurationUpdate (Kafka message)
```

Run contract tests:

```bash
make contract-test
# or
python -m pytest tests/contract/ -v
```

---

## Testing

```bash
# All tests (unit + API + integration + contract)
make test

# Unit tests only
make test-unit

# API tests only
make test-api

# Contract tests only
make contract-test

# Integration tests (uses mock adapters — no M1–M5 needed)
make integration-test
```

Tests use SQLite in-memory for speed. No PostgreSQL or Redis required for `make test`.

---

## Development

```bash
# Install Python deps
make install

# Start local dev server (requires .env)
make dev

# Start frontend dev server
make dev-frontend

# Code quality
make lint
make format
make typecheck
```

---

## Docker

```bash
# Build image
make build

# Start full stack
make up

# View logs
make logs
make logs-api

# Stop
make down

# Stop + remove volumes
make down-volumes
```

---

## CI/CD

GitHub Actions pipeline (`.github/workflows/ci.yml`):

1. **Lint** — Ruff lint + format check + mypy
2. **Contract Tests** — JSON schema validation (no services needed)
3. **Unit + API Tests** — pytest with SQLite in-memory
4. **Frontend Build** — `npm run build`
5. **Docker Build + Trivy** — security scan
6. **Push to GHCR** — on `main` branch only

M6 CI never requires M1–M5 source code.

---

## Air-gapped Deployment

```bash
# On a networked machine:
make airgap
# Creates: deployment/airgapped/ulpf-m6-airgap-<timestamp>.tar.gz

# Transfer to air-gapped host, then:
tar -xzf ulpf-m6-airgap-*.tar.gz
cd ulpf-m6-airgap-*/
bash deployment/airgapped/import-images.sh images/
cp .env.airgap .env && vim .env   # Fill in secrets
docker compose up -d

# Verify
bash deployment/airgapped/verify-airgap.sh
```

---

## Troubleshooting

**M6 API not starting**
```bash
docker compose logs m6-api
# Common: missing SECRET_KEY or POSTGRES_PASSWORD in .env
```

**PostgreSQL not ready**
```bash
docker compose logs postgres
# Wait 30s for first-time initialization
```

**Kafka startup slow**
```bash
docker compose logs kafka
# Normal: Kafka KRaft mode takes up to 60s on first boot
```

**M1–M5 show UNAVAILABLE**
This is correct when M1–M5 are not deployed. Set `M1_BASE_URL` etc. in `.env` when those services are running.

**Reset everything**
```bash
make down-volumes   # removes all volumes
make db-reset       # down + up + migrate + seed
```

---

## Security Notes

- All secrets come from environment variables — never hard-coded
- JWT tokens expire in 60 minutes by default (configurable)
- Passwords hashed with bcrypt
- All SQL queries use SQLAlchemy parameterisation
- CORS configured via `CORS_ORIGINS` env var
- `USE_MOCK_ADAPTERS=true` must never be set in production
- Run `make trivy` to scan the Docker image for vulnerabilities

---

## External M1–M5 Integration

See [`docs/external-integration-guide.md`](docs/external-integration-guide.md) for the full onboarding procedure.

**TL;DR**: Set the `M{n}_BASE_URL` environment variables. No M6 code changes needed.

---

## SIH Demo

See [`docs/sih-demo.md`](docs/sih-demo.md) for the complete step-by-step demo procedure.
