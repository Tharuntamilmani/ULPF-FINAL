# ULPF Member 1 (M1) - Ingestion + Raw Evidence Preservation Boundary

Member 1 (M1) is the ingestion boundary and front door of the **Universal Log Preprocessing Framework (ULPF)** — a high-performance cybersecurity log-normalization pipeline built across 6 modular pipeline stages (M1–M6).

M1 receives raw events over multiple transport interfaces, calculates SHA-256 integrity hashes, durably stores compressed raw payloads in MinIO, and hands off standardized `RawEventEnvelope` JSON messages downstream to **M2 (Parser Engine)** via Apache Kafka topic `ulpf.raw`. M1's job ends at this handoff boundary.

> [!IMPORTANT]
> **Demo & Local Dev Credentials Notice**: The credentials specified in `docker-compose.yml` (`minioadmin` / `minioadmin`) and the default API token in `.env.example` are strictly intended for **local development and demonstration purposes only**. You **MUST** change all tokens, passwords, and access keys before deploying M1 to any non-local, staging, or production environment.

---

## 🎯 Mental Model & Core Boundary

> **"I know HOW an event arrived, WHERE it came from, WHEN we received it, WHAT its original bytes were, and HOW to retrieve it later. I do NOT know what the event means."**

M1 operates strictly at the raw-evidence-preservation layer:
* **In Scope**: Receiving raw log streams over multiple transports (HTTP, UDP Syslog, TCP Syslog, File Replay), calculating SHA-256 integrity hashes over untouched raw bytes, generating time-sortable RFC 9562 UUIDv7 event IDs, durably storing compressed raw payloads in MinIO, and publishing `RawEventEnvelope` messages to Kafka topic `ulpf.raw`.
* **Explicitly Out of Scope**: Zero log parsing (Cisco, Fortinet, CEF, RFC5424 field extraction), zero field normalization, zero event schema mapping, zero threat intelligence/GeoIP lookup, and zero UI components.

---

## 🛠 Tech Stack

| Component | Technology |
| :--- | :--- |
| **Language** | Python 3.12+ |
| **HTTP API** | FastAPI |
| **TCP/UDP Listeners** | Python `asyncio` (raw socket-level byte capture) |
| **Message Bus** | Apache Kafka |
| **Kafka Client** | `aiokafka` |
| **Raw Object Storage** | MinIO (S3-compatible) |
| **Hashing** | `hashlib` (SHA-256 over exact untouched raw bytes) |
| **Event ID** | RFC 9562 UUIDv7 (time-sortable) |
| **Schema & Config** | Pydantic v2 & Pydantic Settings |
| **Containerization** | Docker & Docker Compose |
| **Testing** | `pytest` + `pytest-asyncio` |
| **Metrics** | `prometheus-client` |
| **Logging** | `structlog` (with automatic secret scrubbing) |

---

## 📂 Repository Structure

```
modules/m1-ingestion/
├── app/
│   ├── main.py                 # FastAPI app entrypoint & asyncio listener startup
│   ├── config/
│   │   └── settings.py         # Pydantic BaseSettings loading from .env
│   ├── api/
│   │   ├── http_ingest.py      # HTTP routes: POST /v1/events, POST /v1/replay/file
│   │   └── rate_limiter.py     # Token-bucket rate limiter implementation
│   ├── transports/
│   │   ├── pipeline.py         # Core ingestion pipeline (Bytes -> SHA256/UUIDv7 -> MinIO -> Kafka)
│   │   ├── http.py             # HTTP ingestion driver & auth header verification
│   │   ├── udp_syslog.py       # Asyncio UDP datagram listener (port 514)
│   │   ├── tcp_syslog.py       # Asyncio TCP stream listener (port 515)
│   │   └── file_replay.py      # File replay CLI & endpoint driver
│   ├── envelope/
│   │   ├── models.py           # RawEventEnvelope Pydantic v2 contract models
│   │   └── builder.py          # Envelope construction & MinIO key generator
│   ├── integrity/
│   │   ├── hashing.py          # SHA-256 calculator over untouched bytes
│   │   └── ids.py              # RFC 9562 UUIDv7 generator
│   ├── storage/
│   │   └── raw_vault.py        # MinIO S3 client wrapper & Gzip object vault
│   ├── messaging/
│   │   └── kafka.py            # aiokafka producer wrapper & partition affinity
│   └── health/
│       ├── health.py           # /health, /ready, /metrics endpoints
│       └── metrics.py          # Prometheus counters and histograms
├── tests/
│   ├── unit/                   # UUIDv7, SHA-256, Envelope, Key Gen, Rate Limiter tests
│   ├── integration/            # Full pipeline and SHA-256 roundtrip storage tests
│   └── fixtures/               # Sample test payloads
├── samples/
│   └── cisco_asa.log           # Sample Cisco ASA syslog lines for replay demo
├── scripts/
│   └── demo_consumer.py        # CLI helper to consume & view ulpf.raw Kafka messages
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
└── README.md
```

---

## 📜 The Core Contract: `RawEventEnvelope`

This is the exact JSON structure published downstream to Kafka topic `ulpf.raw`:

```json
{
  "raw_event_id": "019958c3-2d44-7c7f-b3f1-5f1234567890",
  "tenant_id": "demo-tenant",
  "source_id": "cisco-fw-01",
  "source_type": "firewall",
  "ingest_zone": "dmz",
  "collector_id": "collector-01",
  "received_at": "2026-09-12T05:00:15.450Z",
  "transport": { "protocol": "udp", "port": 514 },
  "payload": {
    "encoding": "utf-8",
    "format_hint": "syslog",
    "data": "<134>Sep 12 09:30:15 FW-EDGE-01 %ASA-6-302013: Built inbound TCP connection..."
  },
  "integrity": {
    "algorithm": "SHA-256",
    "hash": "a8f5f167f44f4964e6c998dee827110c7324151a141a0e05ee7a306466f28b49"
  },
  "raw_storage": {
    "backend": "minio",
    "bucket": "ulpf-raw",
    "object_key": "tenant=demo-tenant/year=2026/month=09/day=12/source=cisco-fw-01/event=019958c3-2d44-7c7f-b3f1-5f1234567890"
  }
}
```

---

## 🚀 Quick Start & Running Locally

### Option A: Local Python Execution

1. Create a Python 3.12 virtual environment and install requirements:
   ```bash
   cd modules/m1-ingestion
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Copy environment file:
   ```bash
   cp .env.example .env
   ```

3. Execute tests:
   ```bash
   pytest -v tests/
   ```

4. Launch M1 service:
   ```bash
   python -m app.main
   ```

---

### Option B: Running with Docker Compose

Launch M1 service alongside Kafka and MinIO:
```bash
cd modules/m1-ingestion
docker-compose up --build -d
```

Service Endpoints:
* **HTTP Ingestion & API**: `http://localhost:8000`
* **UDP Syslog Port**: `514`
* **TCP Syslog Port**: `515`
* **MinIO Web Console**: `http://localhost:9001` (User: `minioadmin`, Password: `minioadmin`)
* **Kafka Broker**: `localhost:9092`

---

## 🎥 End-to-End Demo Walkthrough Script

Follow these steps to demonstrate M1's ingestion, raw evidence preservation, SHA-256 hashing, and Kafka publishing end-to-end.

### Step 1: Start Downstream Kafka Consumer
In a terminal, start the demo consumer script listening on topic `ulpf.raw`:
```bash
python scripts/demo_consumer.py localhost:9092
```

### Step 2: Ingest Sample Cisco Syslog Event via HTTP
In a second terminal, send a raw Cisco ASA syslog message:
```bash
curl -X POST http://localhost:8000/v1/events \
  -H "Authorization: Bearer secret-ingest-token-123" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-Source-ID: cisco-fw-01" \
  -H "Content-Type: application/json" \
  -d '{"message": "<134>Sep 12 09:30:15 FW-EDGE-01 %ASA-6-302013: Built inbound TCP connection 892341 for outside:192.168.1.100/49152 to inside:10.0.0.5/80"}'
```

**Expected Response (202 Accepted)**:
```json
{
  "status": "accepted",
  "raw_event_id": "019958c3-2d44-7c7f-b3f1-5f1234567890",
  "tenant_id": "demo-tenant",
  "source_id": "cisco-fw-01",
  "sha256": "a8f5f167f44f4964e6c998dee827110c7324151a141a0e05ee7a306466f28b49"
}
```

### Step 3: Stream Cisco Log File via File Replay CLI
Replay a log file line-by-line through the same pipeline:
```bash
python -m app.transports.file_replay samples/cisco_asa.log --tenant demo-tenant --source cisco-fw-01
```

### Step 4: Verify Raw Object Preservation in MinIO
1. Open the MinIO Console in your browser: [http://localhost:9001](http://localhost:9001)
2. Log in with `minioadmin` / `minioadmin`.
3. Open bucket `ulpf-raw`.
4. Navigate down the partition path: `tenant=demo-tenant/year=YYYY/month=MM/day=DD/source=cisco-fw-01/`.
5. Observe the stored object `event=019958c3...`. Download and decompress it to confirm the raw bytes are identical and its SHA-256 matches the original message.

### Step 5: Verify Downstream Kafka Handoff
Observe the consumer terminal output from Step 1. Notice the complete `RawEventEnvelope` JSON printed with matching `raw_event_id`, SHA-256 `hash`, and MinIO `object_key`.

> 🏁 **"M2 would now consume this envelope to begin parsing — M1's job ends here."**

---

## 🔒 Security & Operational Considerations

1. **Token Authentication**: HTTP requests require `Authorization: Bearer <API_AUTH_TOKEN>`. Unauthorized requests receive `401` or `403`.
2. **Rate Limiting**: Integrated token-bucket rate limiter enforces `MAX_EVENTS_PER_SECOND` and `BURST_SIZE`. Excess traffic receives `429`.
3. **Secret Scrubbing**: Middleware scrubs sensitive headers (`Authorization`, `x-api-key`) before writing to structured JSON logs.
