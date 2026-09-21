# ULPF — Hackathon Demo Guide

> **Duration**: 8–10 minutes
> **Prerequisites**: Complete stack running via `python run_stack.py --with-ui`

---

## Pre-Demo Checklist

Before starting the demonstration, verify:

- [ ] All Docker containers are running (`docker compose ps`)
- [ ] `run_stack.py --with-ui` reports `ULPF INTEGRATED PIPELINE READY`
- [ ] M6 Dashboard loads at http://127.0.0.1:5173
- [ ] Login works with `admin` / `Admin_Secure_Pass_2026!`

---

## Demo Script

### 00:00–00:30 — Introduction & Problem Statement

> **Talking Point**: "NCPOR manages polar expeditions with heterogeneous security appliances — Cisco firewalls, Fortinet devices, Windows servers — each generating logs in different formats. There's no unified view. ULPF solves this by normalizing all telemetry into a single schema."

### 00:30–01:00 — Login

1. Open http://127.0.0.1:5173
2. Enter credentials: `admin` / `Admin_Secure_Pass_2026!`
3. Click **Login**

> **Point out**: JWT-based authentication, RBAC with 5 role levels, multi-tenant architecture.

### 01:00–02:00 — Dashboard Overview

**Page**: `/dashboard`

1. Show the **Pipeline Status** indicators — all 6 modules green
2. Point out the **Event Processing Statistics** (throughput, latency)
3. Highlight the **Tenant Overview** section

> **Talking Point**: "This is the central command view. Operations staff see the health of every pipeline stage in real time. If M2 goes down, it immediately appears here."

### 02:00–03:00 — Event Pipeline Visualization

**Page**: `/pipeline`

1. Navigate to the **Pipeline** view
2. Show the animated flow: M1 → M2 → M3 → M4 → M5
3. Explain each processing stage

> **Talking Point**: "Each log event flows through 5 stages — ingestion, classification, normalization, enrichment, and routing. The pipeline is fully automated — no manual intervention required."

### 03:00–04:00 — Settings: Tenants & Sources

**Page**: `/settings`

1. Navigate to **Settings** → **Tenants** tab
2. Show existing tenant(s)
3. **Create a new tenant**: "Antarctic Expedition 44 — Maitri Station"
4. Switch to **Sources** tab
5. Show how log sources are registered per tenant

> **Talking Point**: "Each expedition operates in its own isolated namespace. Tenant isolation ensures Maitri Station's logs never leak to Bharati Station. This is enforced at the Ingress Gateway level."

### 04:00–05:00 — Parsers & Parser Studio

**Page**: `/parsers`

1. Navigate to **Parsers**
2. Show the list of registered parsers (Cisco ASA, Fortinet, etc.)
3. Open the **Parser Studio** tab
4. Demonstrate the regex builder with a sample Cisco ASA log:
   ```
   %ASA-4-106023: Deny tcp src outside:192.168.1.100/12345 dst inside:10.0.0.5/443
   ```
5. Show the parsed fields appearing in real time
6. Highlight the **ReDoS protection** — dangerous regex patterns are rejected

> **Talking Point**: "The Parser Studio lets security engineers build and test regex parsers safely. The ReDoS guard prevents denial-of-service through malicious regex backtracking — critical for expedition systems with limited compute."

### 05:00–06:00 — Events Explorer

**Page**: `/events`

1. Navigate to **Events**
2. Show the unified event list with:
   - **Raw** view (original syslog line)
   - **Parsed** view (extracted fields)
   - **UES** view (normalized canonical format)
3. Click on an event to open the **UES Viewer**
4. Show the full normalized event with provenance metadata

> **Talking Point**: "Every event preserves its full lineage — the original raw log, the parser that extracted fields, the mapping that normalized them, and the SHA-256 hash linking back to the immutable vault. This is the forensic chain of evidence."

### 06:00–07:00 — System Health & Services

**Page**: `/system`

1. Navigate to **System**
2. Show the **Health** tab — all modules HEALTHY with response times
3. Switch to **Services** tab — registered M1-M5 services
4. Switch to **Audit** tab — show the audit trail of administrative actions

> **Talking Point**: "Full operational observability. Every administrative action is audit-logged — who created a parser, who modified a routing policy, when, from where. This meets government compliance requirements for accountability."

### 07:00–08:00 — Architecture & Configuration

**Page**: `/architecture`

1. Show the built-in **Architecture** visualization
2. Navigate to **Settings** → **Mappings** tab — show vendor-to-UES mappings
3. Navigate to **Settings** → **Policies** tab — show routing policy definitions

> **Talking Point**: "Configuration changes — new parsers, updated mappings, modified routing policies — are atomically distributed to all pipeline modules via Redis. No manual restart required. This is critical for remote expedition sites where you can't SSH into each server."

### 08:00–09:00 — Demo Mode

**Page**: `/demo`

1. Navigate to **Demo Mode**
2. Activate the demo simulation
3. Show simulated events flowing through the pipeline in real time

> **Talking Point**: "For demonstration purposes, the system includes a simulation mode that generates realistic security events. In production, these would come from actual Cisco ASA firewalls, Fortinet devices, and Windows servers at polar stations."

### 09:00–09:30 — Summary

> **Talking Points**:
> - "ULPF provides the unified data infrastructure layer for NCPOR expedition operations"
> - "6 microservices processing logs through a 5-stage pipeline"
> - "Multi-tenant isolation per expedition with RBAC governance"
> - "Cryptographic evidence chain with SHA-256 hashing and immutable vault"
> - "Zero-touch automation from ingestion through routing"
> - "Full audit trail for government compliance"
> - "Built with production-grade technologies: FastAPI, PostgreSQL, Kafka, OpenSearch"

---

## Key Demo Points by Evaluator Interest

### If asked about "Smart Automation":

- **Automated pipeline**: Log events flow through 5 stages without human intervention
- **Automated configuration distribution**: Config changes propagate atomically to all modules
- **Self-healing delivery**: Failed event deliveries retry automatically with exponential backoff
- **Format auto-detection**: M2 automatically identifies the vendor format of incoming logs

### If asked about "Security":

- **SHA-256 forensic chain**: Every raw event is cryptographically hashed before any transformation
- **Immutable evidence vault**: Raw logs stored in MinIO — cannot be modified post-ingestion
- **Multi-tenant isolation**: Ingress Gateway enforces tenant boundaries
- **RBAC with 5 roles**: Super Admin → Tenant Admin → Parser Developer → Security Analyst → Viewer
- **Complete audit trail**: All administrative actions are logged with user, timestamp, and changes

### If asked about "Scalability":

- **Kafka message queue**: Decouples ingestion from processing — M1 can accept events faster than M2 processes them
- **Microservice architecture**: Each module can be independently scaled
- **Docker containerization**: Infrastructure services are containerized for consistent deployment
- **Horizontal scaling ready**: M1 (ingestion) and M5 (routing) are stateless and can be replicated

### If asked about "Offline/Remote Operation":

- **Durable outbox**: M1 uses a SQLite outbox for at-least-once delivery even during Kafka outages
- **Local DLQ**: M5 stores failed deliveries locally for later retry
- **Mock mode**: All M5 connectors support mock mode for development and offline testing

---

## URLs Reference

| Service | URL |
|:--|:--|
| M6 Dashboard | http://127.0.0.1:5173 |
| M3 Console | http://127.0.0.1:5174 |
| M6 API Docs | http://127.0.0.1:18086/docs |
| MinIO Console | http://127.0.0.1:9001 |
| Grafana | http://127.0.0.1:3000 |
| Prometheus | http://127.0.0.1:9090 |
| Health Aggregator | http://127.0.0.1:18090/health |
