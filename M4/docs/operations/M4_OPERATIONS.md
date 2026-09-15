# ULPF Module M4 — Operations & Deployment Guide

## 1. Running the Service

### Run Local Development Server
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8004 --reload
```

### Production Execution
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8004 --workers 4
```

---

## 2. API Endpoints Reference

| Method | Path | Description | Required Roles |
|---|---|---|---|
| `GET` | `/health` | Kubernetes Liveness Probe | Public |
| `GET` | `/ready` | Kubernetes Readiness Probe | Public |
| `GET` | `/metrics` | Prometheus Metrics Exposition | Public / Scraper |
| `POST` | `/v1/enrich` | Enrich canonical UES event | `event_processing`, `admin` |
| `POST` | `/v1/verify` | Verify cryptographic digest | `event_processing`, `analyst_read`, `admin` |
| `GET` | `/v1/providers` | List registered providers | `analyst_read`, `admin` |
| `GET` | `/v1/configuration` | Get active configuration | `analyst_read`, `admin` |

---

## 3. Configuration Management

### Settings Environment Variables
- `M4_HOST`: Bind address (default: `127.0.0.1`)
- `M4_PORT`: Port number (default: `8004`)
- `M4_LOG_LEVEL`: Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`)
- `M4_CACHE_MAX_SIZE`: Max LRU entries (default: `10000`)
- `M4_DEFAULT_CACHE_TTL_SECONDS`: Default TTL (default: `300`)
- `M4_DEFAULT_PROVIDER_TIMEOUT_SECONDS`: Execution timeout per provider (default: `2.0`)

---

## 4. Observability & Telemetry

### Key Prometheus Metrics
- `m4_events_received_total`: Counter of total received events.
- `m4_events_enriched_total{status}`: Counter partitioned by `SUCCESS`, `PARTIAL`, `FAILED`, `SKIPPED`, `TIMEOUT`, `NOT_FOUND`.
- `m4_provider_calls_total{provider, status}`: Counter of individual provider execution outcomes.
- `m4_provider_latency_seconds{provider}`: Latency histogram for provider executions.
- `m4_cache_operations_total{provider, result}`: Cache hits vs misses.
- `m4_integrity_verifications_total{result}`: Valid vs invalid digest checks.
