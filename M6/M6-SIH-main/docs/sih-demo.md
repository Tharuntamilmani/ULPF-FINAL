# SIH 2026 — ULPF M6 Control Plane Demo Procedure

> This document describes the complete demonstration procedure for the
> Smart India Hackathon (SIH) 2026 presentation of the M6 Control Plane.

---

## Pre-Demo Setup (run before the presentation)

```bash
cd m6-control-plane

# 1. Copy and configure environment
cp .env.example .env
# Set: SECRET_KEY, POSTGRES_PASSWORD, ADMIN_PASSWORD

# 2. Start the full stack
docker compose up -d

# 3. Wait for all services to be healthy (~60s)
docker compose ps

# 4. Run migrations
docker compose exec m6-api python -m alembic -c backend/alembic.ini upgrade head

# 5. Seed demo data
docker compose exec m6-api python scripts/seed.py

# 6. Start frontend (separate terminal)
cd frontend && npm install && npm run dev
```

Keep these tabs open in your browser:
- M6 Dashboard: http://localhost:5173
- Swagger UI: http://localhost:8000/docs
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

---

## DEMO SCRIPT

### Step 1 — Login

**Browser**: Navigate to http://localhost:5173

Demonstrate the login page.

```
Username: admin
Password: <ADMIN_PASSWORD from .env>
```

**Narration**: "M6 uses JWT-based authentication with bcrypt password hashing. No credentials are hard-coded — everything comes from environment variables."

---

### Step 2 — Dashboard Overview

Navigate to the **Dashboard** page.

**Point out**:
- M6 Control Plane status: `HEALTHY`
- PostgreSQL: `HEALTHY`
- Redis: `HEALTHY`
- Kafka: `HEALTHY` (or `DEGRADED` — Kafka takes time)
- **M1 through M5: `UNAVAILABLE`**

**Narration**: "This is the correct, expected state. M1–M5 are external services not deployed in this repository. M6 accurately reports them as UNAVAILABLE — it never fabricates HEALTHY status for missing services."

**Key point**: "The dashboard will show UNAVAILABLE with a clear label. This is by design — M6 is honest about what it can and cannot reach."

---

### Step 3 — PostgreSQL and Redis healthy

**Swagger**: `GET /ready`

```json
{
  "ready": true,
  "checks": {
    "postgres": { "service": "postgres", "status": "HEALTHY", "latency_ms": 2.1 },
    "redis":    { "service": "redis",    "status": "HEALTHY", "latency_ms": 0.8 }
  }
}
```

**Narration**: "The readiness probe validates PostgreSQL and Redis — M6's two required dependencies. Only when both are healthy does M6 report ready."

---

### Step 4 — Create a Source

**Browser**: Navigate to **Sources → (or use Swagger)**

**Swagger**: `POST /api/v1/sources`

```json
{
  "source_id": "demo-fw-live",
  "tenant_id": "demo-tenant",
  "name": "Live Demo Firewall",
  "vendor": "Cisco",
  "product": "ASA",
  "source_type": "firewall",
  "protocol": "syslog",
  "transport": "udp",
  "port": 514,
  "zone": "dmz",
  "parser_id": "parser-cisco-asa"
}
```

**Narration**: "M6 stores log source metadata only. It does not ingest events from this source — that is M1's job. M6 assigns a parser_id here, and M1 will read this assignment from Redis."

---

### Step 5 — Register and Lifecycle a Parser

**Swagger**: `POST /api/v1/parsers`

```json
{
  "parser_id": "parser-demo-live",
  "name": "Live Demo Parser",
  "vendor": "Demo",
  "product": "Demo FW",
  "format": "syslog",
  "version": "1.0.0"
}
```

Walk through the lifecycle:

```bash
# Submit for review
POST /api/v1/parsers/{id}/submit

# Approve
POST /api/v1/parsers/{id}/approve

# Activate
POST /api/v1/parsers/{id}/activate
```

**Browser**: Show the parser status changing: DRAFT → PENDING_APPROVAL → APPROVED → ACTIVE

**Narration**: "Parser lifecycle is enforced by a state machine. Invalid transitions — like trying to activate a DRAFT parser — are rejected with a 400 error. This prevents misconfiguration from reaching production."

Show invalid transition:

```bash
# This will fail: "Cannot transition from DRAFT to ACTIVE"
POST /api/v1/parsers/{new-draft-id}/activate
```

---

### Step 6 — Schema Registry

**Browser**: Navigate to **Schemas**

Show pre-seeded UES v1.0.0 schema.

**Narration**: "M6 maintains the Universal Event Schema. Multiple versions can coexist. M3 reads the active schema from Redis — M6 distributes it, M3 uses it."

Show the contract file:

```bash
cat contracts/ues/v1.0.0/schema.json
```

**Key point**: "UES v2.0.0 introduces a breaking change — `event.severity` becomes required. M6's contract tests catch this automatically."

---

### Step 7 — Create Mapping and Policy

**Swagger**: `POST /api/v1/mappings`

```json
{
  "mapping_id": "demo-fw-ues-v1",
  "name": "Demo FW → UES v1",
  "source_format": "demo-fw",
  "target_schema": "ues",
  "target_version": "1.0.0",
  "fields": {
    "srcip": "source.ip",
    "dstip": "destination.ip",
    "action": "event.action"
  }
}
```

**Swagger**: `POST /api/v1/policies`

```json
{
  "policy_id": "demo-critical",
  "name": "Demo Critical Events",
  "version": "1.0.0",
  "priority": 100,
  "conditions": [
    { "field": "event.severity.value", "operator": ">=", "value": 7 }
  ],
  "destinations": ["siem", "data_lake"],
  "is_enabled": true
}
```

---

### Step 8 — Push Configuration to Redis

**Browser**: Navigate to **Configuration**

Click **"Distribute All"** button.

**Swagger** (equivalent):

```bash
POST /api/v1/configuration/distribute
```

**Browser**: Show the Redis snapshot updating — version number increments, item counts appear.

**Redis CLI** (terminal):

```bash
docker compose exec redis redis-cli GET config:sources
docker compose exec redis redis-cli GET config:version
```

**Narration**: "M6 pushes configuration to Redis. M1 through M5 read from Redis directly — they never query M6's database. This one-way push model decouples the modules."

---

### Step 9 — Audit Trail

**Browser**: Navigate to **Audit**

Show all actions performed during the demo appear in the audit log.

**Narration**: "Every administrative mutation produces an append-only audit entry. The audit log cannot be modified — only appended to. This is critical for SOC compliance."

Highlight entries for: SOURCE_CREATED, PARSER_REGISTERED, PARSER_ACTIVATED, CONFIGURATION_DISTRIBUTED.

---

### Step 10 — Prometheus Metrics

**Browser**: Navigate to http://localhost:9090

Query: `ulpf_m6_api_requests_total`

Query: `ulpf_m6_service_health_status`

**Narration**: "M6 exposes a full Prometheus metrics namespace. Every API request, every registry operation, every config distribution, and every health check is tracked."

Also show: `GET /metrics` directly in browser: http://localhost:8000/metrics

---

### Step 11 — Grafana Dashboard

**Browser**: Navigate to http://localhost:3000

Log in (admin / GRAFANA_PASSWORD).

Open: **ULPF M6 Control Plane** dashboard.

Show: API request rate, p95 latency, service health table.

**Narration**: "The Grafana dashboard is auto-provisioned via Docker Compose — no manual setup required. In production, this gives the SOC team a real-time view of the entire ULPF platform health."

---

### Step 12 — Replay Request

**Browser**: Navigate to **Replay**

Enter event ID: `evt-demo-001`, reason: `SIH demo replay request`

Click **Request**.

**Swagger** (equivalent):

```bash
POST /api/v1/replay/evt-demo-001
{
  "source": "demo-fw-live",
  "reason": "SIH demo — re-process after parser fix"
}
```

Show status: `REQUESTED` → `QUEUED` (if Kafka is healthy).

**Narration**: "When a parser bug is fixed and activated, operators can request re-processing of historical events. M6 publishes a replay request to the ulpf.replay Kafka topic. M1 and M2 consume this and re-process the event — M6 just coordinates."

---

### Step 13 — Role Restrictions Demo

Open a second browser tab in incognito.

Create a VIEWER user via Swagger:

```bash
POST /api/v1/auth/users
{
  "username": "demo-viewer",
  "email": "viewer@demo.local",
  "password": "Viewer@12345",
  "role": "VIEWER"
}
```

Log in as `demo-viewer`.

Try to create a source:

```bash
POST /api/v1/sources  →  403 PERMISSION_DENIED
```

Try to list sources:

```bash
GET /api/v1/sources   →  200 OK
```

**Narration**: "RBAC is enforced at the API level. VIEWERs can read everything but cannot create or modify. Only ADMINISTRATORs can approve parsers. This follows the principle of least privilege."

---

### Step 14 — Contract Tests

```bash
# Run contract tests
python -m pytest tests/contract/ -v

# Or
make contract-test
```

Show output — all tests pass without any M1–M5 service running.

**Narration**: "Contract tests validate the JSON schemas that define how M1–M5 communicate. A breaking change — like removing a required field from the UES schema — automatically fails these tests. This catches integration issues before any M1–M5 code is deployed."

---

### Step 15 — Service Failure Demonstration

Stop PostgreSQL:

```bash
docker compose stop postgres
```

Check readiness:

```bash
curl http://localhost:8000/ready
# Returns 503 — postgres: error
```

**Narration**: "When PostgreSQL goes down, M6 readiness probe immediately reflects this. The dashboard shows the dependency as UNAVAILABLE. M6 does not silently ignore failures."

Restart PostgreSQL:

```bash
docker compose start postgres
# Wait 10s
curl http://localhost:8000/ready
# Returns 200 — recovered
```

**Narration**: "M6 self-heals automatically. No restart required — it reconnects when the dependency recovers."

---

### Step 16 — Air-gap Demo (optional)

```bash
# Show the package script
cat deployment/airgapped/package-airgap.sh

# Show what's in a bundle
ls deployment/airgapped/
```

**Narration**: "For environments without internet access — such as classified SOC deployments — M6 ships as a self-contained bundle. All Docker images, configs, contracts, and scripts are packaged together. The receiving host needs only Docker."

---

### Step 17 — CI/CD

Show `.github/workflows/ci.yml` in the repo.

**Narration**: "The CI pipeline runs six jobs: lint, contract tests, unit/API tests, frontend build, Docker build, and Trivy security scan. Every job runs independently of M1–M5. The pipeline passes on a fresh repository with only M6 code."

Show Trivy output (from a previous run, or run locally):

```bash
make trivy
```

---

## Summary Points for Judges

1. **M6 runs completely standalone** — no M1–M5 code, no M1–M5 services, no M1–M5 databases
2. **Accurate health reporting** — UNAVAILABLE means unavailable, never HEALTHY
3. **Enforced parser lifecycle** — state machine prevents invalid transitions
4. **Append-only audit trail** — every admin action is logged, nothing is overwritten
5. **Contract-first integration** — JSON schemas define all inter-module data formats
6. **Zero M6 code changes needed** to connect M1–M5 — only environment variables
7. **Air-gap ready** — fully packaged for offline deployment
8. **CI/CD works independently** — no external dependencies required to run the pipeline
