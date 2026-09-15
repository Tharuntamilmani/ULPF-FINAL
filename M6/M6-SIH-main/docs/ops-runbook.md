# M6 Control Plane — Operations Runbook

## Day-0 Setup

### Generate secrets

```bash
# JWT signing key
openssl rand -hex 32

# Database password — use a strong random value
openssl rand -base64 24

# Admin password — minimum 12 chars, mixed case + symbols
```

### Required `.env` values

```
SECRET_KEY=<32+ char hex>
POSTGRES_PASSWORD=<strong password>
ADMIN_PASSWORD=<strong password>
REDIS_PASSWORD=<if Redis auth is enabled>
MINIO_SECRET_KEY=<if MinIO auth is changed>
GRAFANA_PASSWORD=<strong password>
```

---

## Day-1 Operations

### Check overall health

```bash
curl http://localhost:8000/health     # liveness
curl http://localhost:8000/ready      # readiness
curl http://localhost:8000/metrics    # Prometheus
```

### Check all service status

```bash
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/v1/services
```

### Push updated configuration

After changing sources, parsers, schemas, mappings, or policies — push to Redis:

```bash
curl -X POST -H "Authorization: Bearer <admin-token>" \
  http://localhost:8000/api/v1/configuration/distribute
```

Or push a single key:

```bash
curl -X POST -H "Authorization: Bearer <admin-token>" \
  http://localhost:8000/api/v1/configuration/distribute/sources
```

---

## Alerts and Escalation

| Alert | Condition | Action |
|---|---|---|
| M6 not ready | `/ready` returns 503 | Check PostgreSQL and Redis |
| PostgreSQL down | pg_isready fails | Restart postgres container |
| Redis down | redis-cli ping fails | Restart redis container |
| Config version stale | No distribution in 1h | Run distribute manually |
| Kafka unavailable | Broker unreachable | Check kafka container logs |
| M1–M5 UNAVAILABLE | External service down | Contact M1–M5 team |

---

## Database Operations

### View recent audit logs

```bash
docker compose exec postgres psql -U m6user -d m6_control_plane \
  -c "SELECT actor, action, resource_type, resource_id, timestamp FROM audit_logs ORDER BY timestamp DESC LIMIT 20;"
```

### Check configuration versions

```bash
docker compose exec postgres psql -U m6user -d m6_control_plane \
  -c "SELECT config_key, version, status, created_at FROM configuration_versions ORDER BY created_at DESC LIMIT 10;"
```

### Backup database

```bash
docker compose exec postgres pg_dump -U m6user m6_control_plane \
  | gzip > backup-$(date +%Y%m%d-%H%M%S).sql.gz
```

### Restore database

```bash
gunzip -c backup-*.sql.gz | docker compose exec -T postgres \
  psql -U m6user m6_control_plane
```

---

## Redis Operations

### Inspect config keys

```bash
docker compose exec redis redis-cli KEYS "config:*"
docker compose exec redis redis-cli GET config:version
docker compose exec redis redis-cli GET config:sources
```

### Force-expire a config key (forces re-publish on next distribute)

```bash
docker compose exec redis redis-cli DEL config:sources
```

---

## Log Analysis

M6 logs are JSON. Use `docker compose logs` or ship to a log aggregator.

```bash
# Follow API logs
docker compose logs -f m6-api

# Filter for errors
docker compose logs m6-api 2>&1 | grep '"level":"error"'

# Filter for a specific request_id
docker compose logs m6-api 2>&1 | grep '"request_id":"<id>"'
```

---

## Scaling

For production, increase API workers:

```bash
# In docker-compose.yml, override CMD:
command: ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

Or set `APP_WORKERS=4` and update the Dockerfile CMD.

---

## Upgrades

```bash
# Pull latest image
docker compose pull m6-api

# Rolling restart (zero-downtime if behind a load balancer)
docker compose up -d --no-deps --build m6-api

# Run any new migrations
docker compose exec m6-api python -m alembic -c backend/alembic.ini upgrade head
```

---

## Connecting M1–M5 (post-deployment)

1. Confirm M1–M5 services expose `/health`, `/ready`, `/metrics`
2. Set env vars in M6's `.env`:
   ```
   M1_BASE_URL=http://m1-host:8001
   ```
3. Restart M6 API:
   ```bash
   docker compose restart m6-api
   ```
4. Verify in dashboard: M1 should now show its real status
5. Push configuration so M1 reads from Redis:
   ```bash
   POST /api/v1/configuration/distribute
   ```
6. Provision Kafka topics:
   ```bash
   POST /api/v1/kafka/topics/provision
   ```
