# ULPF — Complete Setup Guide

> **Target Audience**: A developer who has never seen this project and needs to get it running from a fresh Windows machine.

---

## Table of Contents

1. [Overview](#1-overview)
2. [System Requirements](#2-system-requirements)
3. [Repository Setup](#3-repository-setup)
4. [Infrastructure Setup (Docker)](#4-infrastructure-setup-docker)
5. [PostgreSQL Database Setup](#5-postgresql-database-setup)
6. [Python Environment Setup](#6-python-environment-setup)
7. [Frontend Setup](#7-frontend-setup)
8. [Environment Configuration](#8-environment-configuration)
9. [Database Migrations & Seeding](#9-database-migrations--seeding)
10. [Running the Complete Stack](#10-running-the-complete-stack)
11. [Manual Service Startup](#11-manual-service-startup)
12. [Verification](#12-verification)
13. [API Testing](#13-api-testing)
14. [Demo Account](#14-demo-account)
15. [Troubleshooting](#15-troubleshooting)
16. [Clean Reset](#16-clean-reset)
17. [Production Notes](#17-production-notes)

---

## 1. Overview

ULPF is a microservice-based log processing pipeline with the following architecture:

| Component | Count | Technology |
|:--|:--|:--|
| **Backend Microservices** | 9 (M1-M6, Gateway, ConfigSync, Health Aggregator) | Python 3.12 + FastAPI |
| **Kafka Consumer Bridge** | 1 | Python (aiokafka) |
| **Web Frontends** | 2 (M6 Dashboard, M3 Console) | React 18 + TypeScript + Vite |
| **Infrastructure Services** | 6 (PostgreSQL, Redis, Kafka, MinIO, OpenSearch, ZooKeeper) | Docker containers |
| **Monitoring** | 2 (Prometheus, Grafana) | Docker containers |

The **recommended deployment method** is using the `run_stack.py` unified orchestrator, which automates infrastructure verification, service startup, and health probing.

---

## 2. System Requirements

### Required Software

| Software | Minimum Version | Verification Command | Download |
|:--|:--|:--|:--|
| **Windows** | 10/11 (64-bit) | — | — |
| **Git** | 2.40+ | `git --version` | [git-scm.com](https://git-scm.com/) |
| **Python** | 3.12+ | `python --version` | [python.org](https://www.python.org/) |
| **pip** | 23+ | `pip --version` | Bundled with Python |
| **Node.js** | 20+ (LTS) | `node --version` | [nodejs.org](https://nodejs.org/) |
| **npm** | 10+ | `npm --version` | Bundled with Node.js |
| **Docker Desktop** | 4.25+ | `docker --version` | [docker.com](https://www.docker.com/) |
| **Docker Compose** | 2.20+ (V2) | `docker compose version` | Bundled with Docker Desktop |
| **PostgreSQL** | 16+ | `psql --version` | [postgresql.org](https://www.postgresql.org/) |

### Hardware Recommendations

| Resource | Minimum | Recommended |
|:--|:--|:--|
| **RAM** | 8 GB | 16 GB |
| **CPU** | 4 cores | 8 cores |
| **Disk** | 10 GB free | 20 GB free |

### Port Requirements

Ensure the following ports are available before starting:

| Port | Service | Used By |
|:--|:--|:--|
| 2181 | ZooKeeper | Kafka coordination (Docker) |
| 3000 | Grafana | Monitoring dashboards (Docker) |
| 5173 | M6 Frontend | Control Plane Dashboard (Vite) |
| 5174 | M3 Frontend | Normalizer Console (Vite) |
| 5432 | PostgreSQL | M6 Control Plane database |
| 6379 | Redis | Configuration distribution bus (Docker) |
| 9000 | MinIO API | Object storage (Docker) |
| 9001 | MinIO Console | Object storage admin UI (Docker) |
| 9090 | Prometheus | Metrics collection (Docker) |
| 9092 | Kafka | Message streaming (Docker) |
| 9200 | OpenSearch | Event indexing (Docker) |
| 18001 | M1 | Ingestion & Raw Vault |
| 18004 | M4 | Context Enrichment |
| 18080 | Gateway | Ingress Security Gateway |
| 18081 | ConfigSync | Configuration Sync Worker |
| 18082 | M2 | Format Classifier & Parser |
| 18083 | M3 | UES Normalizer |
| 18085 | M5 | Smart Router |
| 18086 | M6 | Control Plane API |
| 18090 | Health Aggregator | System health monitoring |
| 18514 | M1 (UDP) | Syslog UDP listener |
| 18515 | M1 (TCP) | Syslog TCP listener |

---

## 3. Repository Setup

### Clone the Repository

```powershell
git clone <repository-url>
cd ULPF
```

### Verify Structure

```powershell
# Check that all module directories exist
Get-ChildItem -Directory | Select-Object Name
```

Expected output should include: `M1`, `M2`, `M3`, `M4`, `M5`, `M6`, `integration`

---

## 4. Infrastructure Setup (Docker)

### Step 4.1 — Start Docker Desktop

Ensure Docker Desktop is running with **Linux containers** (not Windows containers).

Verify Docker is ready:
```powershell
docker info
```

### Step 4.2 — Pull Infrastructure Images (Optional Pre-pull)

```powershell
docker pull postgres:16-alpine
docker pull redis:7-alpine
docker pull apache/kafka:3.7.0
docker pull quay.io/minio/minio:latest
docker pull opensearchproject/opensearch:2.14.0
docker pull prom/prometheus:v2.52.0
docker pull grafana/grafana:10.4.4
```

### Step 4.3 — Start Infrastructure via Docker Compose

```powershell
cd M6/M6-SIH-main

# Create .env first (see Section 8)
copy .env.example .env
# Edit .env to set required values: SECRET_KEY, ADMIN_PASSWORD, POSTGRES_PASSWORD

# Start all infrastructure services
docker compose up -d
```

### Step 4.4 — Verify Infrastructure Containers

```powershell
docker compose ps
```

All services should show `running` or `healthy`:

| Container | Status |
|:--|:--|
| `m6-postgres` | healthy |
| `m6-redis` | healthy |
| `m6-kafka` | healthy |
| `m6-minio` | healthy |
| `m6-opensearch` | healthy |
| `m6-prometheus` | healthy |
| `m6-grafana` | healthy |

> **Note**: Kafka may take 30-60 seconds to become healthy. Check with `docker compose logs kafka` if needed.

---

## 5. PostgreSQL Database Setup

The ULPF stack uses **two PostgreSQL configurations**:

1. **Docker Compose PostgreSQL** (container `m6-postgres`): Used when running M6 via Docker Compose standalone. Database: `m6_control_plane`, User: `m6user`.
2. **Local PostgreSQL**: Used by the `run_stack.py` orchestrator. Database: `ulpf_m6`, User: `ulpf_admin`.

### For `run_stack.py` Orchestrator (Recommended)

Create the required database and user in your local PostgreSQL:

```powershell
# Connect to PostgreSQL as superuser
psql -U postgres
```

```sql
-- Create the ULPF user
CREATE USER ulpf_admin WITH PASSWORD 'ulpf_secure_password';

-- Create the database
CREATE DATABASE ulpf_m6 OWNER ulpf_admin;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE ulpf_m6 TO ulpf_admin;

-- Exit
\q
```

### Verify Connection

```powershell
psql -U ulpf_admin -d ulpf_m6 -h localhost -c "SELECT 1;"
```

---

## 6. Python Environment Setup

### Step 6.1 — Root-Level Dependencies

The `run_stack.py` orchestrator requires several Python packages:

```powershell
cd E:\ULPF

# Install orchestrator dependencies
pip install httpx psutil psycopg2-binary redis minio aiokafka
```

### Step 6.2 — M6 Control Plane Virtual Environment

```powershell
cd E:\ULPF\M6\M6-SIH-main

# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\Activate.ps1

# Install all dependencies
pip install -r requirements.txt

# Deactivate when done
deactivate
```

### Step 6.3 — M1 Ingestion Virtual Environment

```powershell
cd E:\ULPF\M1\modules\m1-ingestion

# Create virtual environment
python -m venv .venv

# Activate it
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Deactivate
deactivate
```

### Step 6.4 — Other Modules (M2, M3, M4, M5)

These modules use the system Python or the root-level environment. Install their dependencies:

```powershell
# M2 Parser Engine
cd E:\ULPF\M2\abcd-main
pip install -r requirements.txt

# M3 Normalizer
cd E:\ULPF\M3
pip install -r requirements.txt

# M5 Smart Router
cd E:\ULPF\M5
pip install -r requirements.txt
```

> **Note**: M4 uses `pyproject.toml` for dependencies. Install with:
> ```powershell
> cd E:\ULPF\M4
> pip install -e .
> ```

---

## 7. Frontend Setup

### Step 7.1 — M6 Control Plane Dashboard

```powershell
cd E:\ULPF\M6\M6-SIH-main\frontend

# Install npm dependencies
npm install
```

### Step 7.2 — M3 Normalizer Console

```powershell
cd E:\ULPF\M3\frontend

# Install npm dependencies
npm install
```

---

## 8. Environment Configuration

### M6 Control Plane (.env)

```powershell
cd E:\ULPF\M6\M6-SIH-main

# Copy the example configuration
copy .env.example .env
```

Edit `.env` and set these **required** values:

```env
# REQUIRED — Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=<your-generated-64-char-hex-string>

# REQUIRED — Initial admin password (min 8 characters)
ADMIN_PASSWORD=Admin_Secure_Pass_2026!

# REQUIRED — PostgreSQL password
POSTGRES_PASSWORD=ulpf_secure_password
```

### M1 Ingestion (.env)

```powershell
cd E:\ULPF\M1\modules\m1-ingestion
copy .env.example .env
```

### M3 Normalizer (.env)

```powershell
cd E:\ULPF\M3
copy .env.example .env
```

### M5 Smart Router (.env)

```powershell
cd E:\ULPF\M5
copy .env.example .env
```

---

## 9. Database Migrations & Seeding

### Run Alembic Migrations

```powershell
cd E:\ULPF\M6\M6-SIH-main\backend

# Ensure the M6 virtualenv is active
..\..\.venv\Scripts\Activate.ps1  # If running from M6-SIH-main

# Apply all migrations
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 0001, initial_schema
INFO  [alembic.runtime.migration] Running upgrade 0001 -> 0002, add_tenants_and_distribution_states
```

### Seed Initial Data

```powershell
cd E:\ULPF\M6\M6-SIH-main

# Run the seed script
python scripts/seed.py
```

This creates:
- Default admin user (`admin` / password from `ADMIN_PASSWORD` env)
- Default tenant
- System roles (SUPER_ADMIN, TENANT_ADMIN, PARSER_DEVELOPER, SECURITY_ANALYST, VIEWER)

---

## 10. Running the Complete Stack

### Option A: Automated Orchestrator (Recommended)

```powershell
cd E:\ULPF

# Start everything: infrastructure + backends + web UIs
python run_stack.py --with-ui
```

**What it does** (in order):

1. Kills any processes on ULPF ports from previous runs
2. Verifies Docker is available
3. Ensures Docker containers are running (starts them if stopped)
4. Probes infrastructure readiness:
   - ZooKeeper (:2181) — 15s timeout
   - Kafka (:9092) — 45s timeout, creates `ulpf.raw` topic if missing
   - MinIO (:9000) — 20s timeout, creates `ulpf-raw` bucket if missing
   - Redis (:6379) — 15s timeout
   - OpenSearch (:9200) — 25s timeout
   - PostgreSQL (:5432) — 15s timeout
5. Starts microservices sequentially with health verification:
   - M6 Control Plane (:18086)
   - ConfigSync Worker (:18081)
   - M1 Ingestion Vault (:18001) + Kafka producer readiness
   - M2 Parser Engine (:18082)
   - M3 UES Normalizer (:18083)
   - M4 Enrichment (:18004)
   - M5 Smart Router (:18085)
   - Ingress Security Gateway (:18080)
   - Health Aggregator (:18090)
6. Starts M1→M2 Kafka Consumer Bridge with liveness verification
7. Starts web frontends:
   - M6 Dashboard (:5173)
   - M3 Console (:5174)
8. Enters continuous supervision loop (auto-restarts on crashes)

**Success output**:
```
============================================
ULPF INTEGRATED PIPELINE READY
M6 Admin UI : http://127.0.0.1:5173
M3 Dev UI   : http://127.0.0.1:5174
============================================
ALL ULPF INTEGRATED SERVICES ARE HEALTHY AND RUNNING!
```

### Option B: PowerShell Wrappers

```powershell
# Start
.\start_ulpf.ps1

# Stop
.\stop_ulpf.ps1
```

### Other Orchestrator Modes

```powershell
# Backend only (no web UIs)
python run_stack.py

# Infrastructure verification only
python run_stack.py --infra-only

# Start, verify, then return (no supervision loop)
python run_stack.py --check-only

# Stop all running ULPF services
python run_stack.py --stop
```

---

## 11. Manual Service Startup

If you prefer to start services individually (for development/debugging):

### Start Infrastructure

```powershell
cd E:\ULPF\M6\M6-SIH-main
docker compose up -d
```

### Start M6 Control Plane

```powershell
cd E:\ULPF\M6\M6-SIH-main
.venv\Scripts\Activate.ps1
uvicorn backend.app.main:app --host 127.0.0.1 --port 18086 --reload
```

### Start M6 Frontend

```powershell
cd E:\ULPF\M6\M6-SIH-main\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

### Start M1 Ingestion

```powershell
cd E:\ULPF\M1\modules\m1-ingestion
.venv\Scripts\Activate.ps1
uvicorn app.main:app --host 127.0.0.1 --port 18001
```

### Start M2 Parser

```powershell
cd E:\ULPF\M2\abcd-main
python -c "from app.main import app; import uvicorn; uvicorn.run(app, host='127.0.0.1', port=18082)"
```

### Start M3 Normalizer

```powershell
cd E:\ULPF\M3
python -c "from app.main import app; import uvicorn; uvicorn.run(app, host='127.0.0.1', port=18083)"
```

### Start M3 Frontend

```powershell
cd E:\ULPF\M3\frontend
npm run dev -- --host 127.0.0.1 --port 5174
```

---

## 12. Verification

### Infrastructure Checks

```powershell
# Docker containers
docker compose -f E:\ULPF\M6\M6-SIH-main\docker-compose.yml ps

# PostgreSQL
psql -U ulpf_admin -d ulpf_m6 -h localhost -c "SELECT 1"

# Redis
redis-cli ping

# Kafka
docker exec m6-kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list

# MinIO
curl http://localhost:9000/minio/health/ready

# OpenSearch
curl http://localhost:9200/_cluster/health
```

### Service Health Checks

```powershell
# M6 Control Plane
curl http://127.0.0.1:18086/health

# M1 Ingestion (with Kafka/MinIO readiness)
curl http://127.0.0.1:18001/ready

# M2 Parser Engine
curl http://127.0.0.1:18082/health

# M3 Normalizer
curl http://127.0.0.1:18083/health

# M4 Enrichment
curl http://127.0.0.1:18004/health

# M5 Smart Router
curl http://127.0.0.1:18085/health

# Ingress Gateway
curl http://127.0.0.1:18080/health

# ConfigSync Worker
curl http://127.0.0.1:18081/health

# Health Aggregator
curl http://127.0.0.1:18090/live
```

### Web UI Checks

- Open http://127.0.0.1:5173 — M6 Dashboard should load the login page
- Open http://127.0.0.1:5174 — M3 Console should load

### Full E2E Verification

```powershell
python integration/scratch/verify_web_e2e.py
```

---

## 13. API Testing

### Swagger UI

Navigate to: http://127.0.0.1:18086/docs

### Authenticate via API

```powershell
# Login
$response = Invoke-RestMethod -Uri "http://127.0.0.1:18086/api/v1/auth/login" `
  -Method POST `
  -ContentType "application/x-www-form-urlencoded" `
  -Body "username=admin&password=Admin_Secure_Pass_2026!"

$token = $response.access_token

# Use the token for authenticated requests
$headers = @{ Authorization = "Bearer $token" }

# List tenants
Invoke-RestMethod -Uri "http://127.0.0.1:18086/api/v1/tenants" -Headers $headers

# List parsers
Invoke-RestMethod -Uri "http://127.0.0.1:18086/api/v1/parsers" -Headers $headers

# Check services
Invoke-RestMethod -Uri "http://127.0.0.1:18086/api/v1/services" -Headers $headers
```

### Linux/macOS (curl)

```bash
# Login
TOKEN=$(curl -s -X POST http://127.0.0.1:18086/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=Admin_Secure_Pass_2026!" | jq -r .access_token)

# List tenants
curl -s http://127.0.0.1:18086/api/v1/tenants -H "Authorization: Bearer $TOKEN"
```

---

## 14. Demo Account

| Field | Value |
|:--|:--|
| **URL** | http://127.0.0.1:5173 |
| **Username** | `admin` |
| **Password** | `Admin_Secure_Pass_2026!` |
| **Role** | SUPER_ADMIN |

---

## 15. Troubleshooting

### Common Issues

| Problem | Likely Cause | Solution |
|:--------|:-------------|:---------|
| `run_stack.py` fails at PostgreSQL probe | Local PostgreSQL not running or `ulpf_m6` database doesn't exist | Create database per Section 5 |
| `CRITICAL: Docker is not available` | Docker Desktop not running or not in Linux container mode | Start Docker Desktop, switch to Linux containers |
| Kafka fails readiness probe | ZooKeeper not ready, or Kafka container restarted | Wait 30-60s; check `docker logs m6-kafka` |
| `SECRET_KEY is required` error | `.env` file missing or `SECRET_KEY` not set | Copy `.env.example` to `.env`, set required values |
| Port already in use | Previous ULPF instance still running | Run `python run_stack.py --stop` first |
| M6 API returns 500 on login | Database not migrated or seeded | Run `alembic upgrade head` then `python scripts/seed.py` |
| Frontend cannot reach API | Vite proxy target mismatch | Ensure M6 API is running on :18086 (Vite proxies to this) |
| CORS error in browser | Frontend origin not in CORS allowlist | Add `http://localhost:5173` to `CORS_ORIGINS` in `.env` |
| M1 `/ready` fails | Kafka or MinIO not accessible | Verify Kafka on :9092 and MinIO on :9000 are healthy |
| `npm install` fails on Windows | Node.js not in PATH or version too old | Verify `node --version` returns 20+ |
| Import errors when starting services | Python dependencies not installed | Install requirements per Section 6 |

### Diagnostic Commands

```powershell
# Check what's using a specific port
netstat -ano | findstr :18086

# View orchestrator logs
Get-Content E:\ULPF\integration\scratch\deployment_logs\M6_Control_Plane.log -Tail 50

# View all orchestrator service logs
Get-ChildItem E:\ULPF\integration\scratch\deployment_logs\*.log

# Check Docker container logs
docker logs m6-postgres --tail 50
docker logs m6-kafka --tail 50
docker logs m6-redis --tail 50

# Kill all ULPF processes
python run_stack.py --stop
```

---

## 16. Clean Reset

### Full Reset (remove all data)

```powershell
# Stop all services
python run_stack.py --stop

# Remove Docker volumes (deletes all data!)
cd M6/M6-SIH-main
docker compose down -v

# Drop and recreate database
psql -U postgres -c "DROP DATABASE IF EXISTS ulpf_m6;"
psql -U postgres -c "CREATE DATABASE ulpf_m6 OWNER ulpf_admin;"

# Re-run migrations and seed
cd M6/M6-SIH-main/backend
alembic upgrade head
cd ..
python scripts/seed.py

# Restart infrastructure
docker compose up -d

# Restart full stack
cd E:\ULPF
python run_stack.py --with-ui
```

### Soft Reset (keep infrastructure, reset app state)

```powershell
python run_stack.py --stop

# Re-seed database
cd M6/M6-SIH-main
python scripts/seed.py

# Restart
cd E:\ULPF
python run_stack.py --with-ui
```

---

## 17. Production Notes

> ⚠️ ULPF is currently configured as a **development/prototype** deployment. The following changes are required for production:

### Mandatory for Production

1. **HTTPS/TLS**: Add a reverse proxy (nginx, Traefik, or Caddy) with TLS certificates
2. **Change all default credentials**: SECRET_KEY, admin password, PostgreSQL password, MinIO credentials
3. **Disable debug mode**: Set `APP_ENV=production`, `APP_DEBUG=false`
4. **Disable mock adapters**: Ensure `USE_MOCK_ADAPTERS=false`
5. **Enable PostgreSQL SSL**: Configure `sslmode=require` in database connection
6. **Network segmentation**: Place infrastructure services behind a firewall
7. **API rate limiting**: Add rate limiting middleware to FastAPI

### Recommended for Production

1. Run M6 API with multiple Uvicorn workers: `APP_WORKERS=4`
2. Use managed PostgreSQL (RDS, Cloud SQL) instead of local instance
3. Configure Kafka with replication factor > 1
4. Enable OpenSearch security plugin
5. Set up log rotation for service logs
6. Implement container health monitoring and auto-restart
7. Add CI/CD pipeline with automated testing
