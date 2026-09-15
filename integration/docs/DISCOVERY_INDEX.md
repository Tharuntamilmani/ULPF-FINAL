# ULPF Phase 0 — Module Discovery Index

**Date**: September 14, 2026  
**Status**: Complete  
**Scope**: Forensic inventory and discovery of all 6 independent ULPF member modules.

---

## 1. System Inventory Summary

| Module | Module Name | Repository / Filesystem Path | Git Branch / Commit | Main Entrypoint | Runtime | Default Port(s) | Main Technology Stack | Test Command | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M1** | Ingestion & Immutable Raw Event Vault | `E:\ULPF\M1\modules\m1-ingestion` | N/A (unversioned directory) | `app/main.py` (`uvicorn app.main:app`) | Python 3.12 (Dedicated `.venv`) | 8000 (HTTP), 514 (UDP), 515 (TCP) | FastAPI, AsyncIO Sockets, aiokafka, MinIO S3, UUIDv7, SQLite Outbox | `pytest -v tests/` | Verified (43/43 Pass) |
| **M2** | Format Classifier + Parser Engine + Discovery | `E:\ULPF\M2\abcd-main` | N/A (unversioned directory) | `app/main.py` (`uvicorn app.main:app`) | Python 3.12 (System Python) | 8082 (HTTP) | FastAPI, Regex/Grok, orjson, YAML Parsers, ReDoS Safeguards | `pytest -v tests/` | Verified (52/52 Pass) |
| **M3** | Canonical UES Normalization & Validation | `E:\ULPF\M3` | `main` / `4e40f82` | `app/main.py` (`uvicorn app.main:app`), `frontend/` (Vite) | Python 3.12 (System Python), Node.js 20 | 8083 (Backend), 5173 (Frontend) | FastAPI, Pydantic v2, JSON Schema Draft 2020-12, YAML Mappings, React/Vite | `pytest -v` | Verified (248/248 Pass) |
| **M4** | Contextual Enrichment + Provenance + Integrity | `E:\ULPF\M4` | N/A (unversioned directory) | `app/main.py` (`uvicorn app.main:app`) | Python 3.12 (System Python) | 8004 (HTTP) | FastAPI, Pydantic v2, RFC 8785 (JCS), SHA-256 Hashing, SSRFGuard, TenantGuard | `pytest -v` | Verified (122/122 Pass) |
| **M5** | Policy Routing + SIEM / Data Lake / AI Delivery | `E:\ULPF\M5` | N/A (unversioned directory) | `app/main.py` (`uvicorn app.main:app`) | Python 3.12 (System Python) | 8085 (HTTP) | FastAPI, OpenSearch, Kafka, Partitioned JSONL Data Lake, LRU Dedup, Retry/DLQ | `python run_tests.py` / `pytest -v` | Verified (44/44 Pass) |
| **M6** | Control Plane + Configuration + Observability | `E:\ULPF\M6\M6-SIH-main` | N/A (unversioned directory) | `backend/app/main.py`, `frontend/` (React) | Python 3.12 (Dedicated `.venv`), Node.js 20 | 8000 (Backend default), 5173 (Frontend) | FastAPI, SQLAlchemy (asyncpg), PostgreSQL, Redis, Kafka, JWT RBAC, React | `pytest -v tests` | Verified (163/163 Pass) |

---

## 2. Discovery Details & Observations

### 2.1 Workspace Root & Directory Layout
- **Root Directory**: `E:\ULPF`
- **Subdirectories**: `M1`, `M2`, `M3`, `M4`, `M5`, `M6`
- **Git State**:
  - `E:\ULPF` is **not** a Git repository.
  - Only `E:\ULPF\M3` is an active Git repository (Branch `main`, initial commit `4e40f82`).
  - `M1`, `M2`, `M4`, `M5`, `M6` are independent source directory trees unpacked without individual `.git` subdirectories.

### 2.2 Dedicated Virtual Environments
- `M1` contains its own dedicated virtual environment at `E:\ULPF\M1\modules\m1-ingestion\.venv` (Python 3.12.13).
- `M6` contains its own dedicated virtual environment at `E:\ULPF\M6\M6-SIH-main\.venv` (Python 3.12.13).
- `M2`, `M3`, `M4`, and `M5` execute successfully against host Python 3.12.10 with pre-installed enterprise packages.

### 2.3 Port Allocation & Conflicts
- `M1`: Port 8000 (HTTP API), Port 514 (UDP Syslog), Port 515 (TCP Syslog)
- `M2`: Port 8082 (HTTP API)
- `M3`: Port 8083 (Backend API), Port 5173 (Operations Dashboard)
- `M4`: Port 8004 (HTTP API)
- `M5`: Port 8085 (HTTP API)
- `M6`: Port 8000 (Backend API in `.env.example`), Port 5173 (Frontend UI)

> [!WARNING]
> **Port Collision Warning**:
> - **Port 8000**: Both M1 and M6 default to port 8000.
> - **Port 5173**: Both M3 Vite frontend and M6 React frontend default to port 5173.
> In the Phase 1 deployment plan, M6 backend must be assigned a non-conflicting port (e.g. 8086 or 8080) and UI ports must be partitioned.
