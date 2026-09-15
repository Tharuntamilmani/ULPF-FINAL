# External M1–M5 Integration Guide

## Overview

M6 is designed so that any M1–M5 implementation can be connected **without modifying M6 source code**.

The only things M6 needs from an external module team are:
1. A running HTTP service with `/health`, `/ready`, and `/metrics` endpoints
2. The service's base URL configured in M6's environment
3. Compliance with the contracts in `contracts/`

---

## Step 1: Implement the Health Contract

Every M1–M5 service **must** expose these endpoints matching `contracts/health/v1/schema.json`:

```
GET /health   → HealthResponse
GET /ready    → HealthResponse
GET /metrics  → Prometheus text format
```

### Minimum HealthResponse

```json
{
  "service": "m1-ingestion",
  "status": "HEALTHY",
  "version": "1.0.0",
  "timestamp": "2026-01-01T00:00:00Z"
}
```

Status values M6 understands:
- `HEALTHY` — service is fully operational
- `DEGRADED` — service is running but with warnings
- `UNHEALTHY` — service is running but has errors
- `UNAVAILABLE` — connection refused / timeout (M6 sets this itself)
- `UNKNOWN` — not yet checked

---

## Step 2: Configure M6 with Service URLs

In your `.env` (or environment):

```bash
M1_BASE_URL=http://m1-ingestion-host:8001
M2_BASE_URL=http://m2-parser-host:8002
M3_BASE_URL=http://m3-normalizer-host:8003
M4_BASE_URL=http://m4-enrichment-host:8004
M5_BASE_URL=http://m5-delivery-host:8005
```

Restart M6 (or reload env). No code changes.

M6 will immediately start calling `/health` on each configured URL and reporting results in:
- `GET /api/v1/services` — health dashboard
- `GET /metrics` — `ulpf_m6_service_health_status{service="m1-ingestion"}` gauge

If a URL is empty, M6 reports `UNAVAILABLE` with `reason: No base URL configured`.

---

## Step 3: Read Configuration from Redis

M6 pushes all configuration to Redis. External services should read from these keys:

```
config:sources     JSON array of active source metadata
config:parsers     JSON array of active parser metadata
config:schemas     Map of schema_name → version → JSON Schema
config:mappings    JSON array of active mappings
config:policies    JSON array of enabled policies (priority-sorted)
config:version     Current config version (integer)
config:updated_at  ISO-8601 last-updated timestamp
```

### Subscribe to config changes (Kafka)

M6 publishes a message to `ulpf.m6.config.updates` every time config is distributed:

```json
{
  "event": "config_updated",
  "config_key": "sources",
  "version": 1704067200000,
  "timestamp": "2026-01-01T00:00:00Z"
}
```

External services should listen on this topic and refresh their Redis cache when a message arrives.

---

## Step 4: Use the Contract Schemas

All inter-module data formats are defined in `contracts/`. External services **must** produce and consume data matching these schemas.

### Pipeline flow

```
M1 produces → contracts/raw_event/v1/schema.json
M2 consumes → contracts/raw_event/v1/schema.json
M2 produces → contracts/parsed_event/v1/schema.json
M3 consumes → contracts/parsed_event/v1/schema.json
M3 produces → contracts/ues/v1.0.0/schema.json  (or v1.1.0 / v2.0.0)
M4 consumes → contracts/ues/v1.0.0/schema.json
M4 produces → contracts/enrichment/v1/schema.json
M5 consumes → contracts/enrichment/v1/schema.json
M5 reads    → contracts/routing/v1/schema.json  (from Redis config:policies)
```

### Validate your output

```bash
# Install jsonschema
pip install jsonschema

python - << 'EOF'
import json, jsonschema
schema = json.load(open("contracts/raw_event/v1/schema.json"))
payload = { ... }   # your event
jsonschema.validate(instance=payload, schema=schema)
print("Valid!")
EOF
```

---

## Step 5: Replay Support

M6 publishes replay requests to the `ulpf.replay` Kafka topic matching `contracts/replay/v1/schema.json`:

```json
{
  "replay_id": "rpl-001",
  "event_id": "evt-abc123",
  "source": "cisco-fw-01",
  "reason": "parser bug fix",
  "requested_by": "admin",
  "requested_at": "2026-01-01T00:00:00Z"
}
```

M1 and M2 should consume this topic and re-process the specified event.

---

## Kafka Topics Reference

| Topic | Producer | Consumer |
|---|---|---|
| `ulpf.raw` | M1 | M2 |
| `ulpf.parsed` | M2 | M3 |
| `ulpf.normalized` | M3 | M4 |
| `ulpf.enriched` | M4 | M5 |
| `ulpf.ai.events` | M4 | AI consumers |
| `ulpf.replay` | **M6** | M1, M2 |
| `ulpf.parser.dlq` | M2 | Ops |
| `ulpf.validation.dlq` | M3 | Ops |
| `ulpf.delivery.dlq` | M5 | Ops |
| `ulpf.m6.config.updates` | **M6** | M1–M5 |

Provision all topics:
```bash
curl -X POST http://localhost:8000/api/v1/kafka/topics/provision \
  -H "Authorization: Bearer <admin-token>"
```

---

## Integration Checklist

Before declaring an M1–M5 service integrated:

- [ ] `GET /health` returns valid `HealthResponse`
- [ ] `GET /ready` returns valid `HealthResponse`
- [ ] `GET /metrics` returns Prometheus text format
- [ ] `M{n}_BASE_URL` configured in M6 `.env`
- [ ] M6 `/api/v1/services` shows the service as `HEALTHY`
- [ ] Service reads its config from Redis `config:*` keys
- [ ] Service subscribes to `ulpf.m6.config.updates`
- [ ] Output events validate against the relevant contract schema
- [ ] Service consumes `ulpf.replay` (M1/M2 only)
- [ ] `make contract-test` passes

---

## Replacing a Module

Any M1–M5 module can be replaced without changing M6 code:

1. Deploy the replacement service
2. Update `M{n}_BASE_URL` in M6's `.env`
3. Ensure the replacement exposes `/health`, `/ready`, `/metrics`
4. Ensure it reads config from Redis and produces contract-compliant events
5. Restart M6 (or wait for the next health-check cycle)

M6 will immediately start reporting the new service's health.
