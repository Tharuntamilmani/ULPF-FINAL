# ULPF Member 2 — Format Classifier + Parser Engine + Unknown-Source Discovery

Member 2 owns the **"Understand the Raw Event"** stage of the ULPF (Universal Log Processing Framework) pipeline. It takes an untouched `RawEventEnvelope` from Member 1 (M1), classifies its format and vendor source, executes the matching registered parser, or routes unknown events to the **Unknown-Source Discovery** engine for assisted onboarding and historical event replay.

---

## Architecture Overview

```
                      M1 (Raw Event Ingestion)
                                │
                                ▼
                        RawEventEnvelope
                                │
                                ▼
                    ┌───────────────────────┐
                    │  FORMAT CLASSIFIER    │
                    └───────────┬───────────┘
                                │
                 ┌──────────────┴──────────────┐
                 ▼                             ▼
            KNOWN SOURCE                 UNKNOWN SOURCE
                 │                             │
                 ▼                             ▼
         Registered Parser              Discovery Engine
                 │                             │
                 │                    Mapping Suggestions
                 │                             │
                 │                       Parser Studio
                 │                             │
                 │                    Validate & Test
                 │                             │
                 │                    Register New Parser
                 │                             │
                 │                      Replay Service
                 │                             │
                 └──────────────┬──────────────┘
                                ▼
                         FIELD EXTRACTION
                                │
                                ▼
                           ParsedEvent
                                │
                                ▼
                    M3 (Canonical Normalization)
```

---

## Directory Layout

```
modules/m2-parser/
├── app/
│   ├── main.py                    # FastAPI application & REST endpoints
│   ├── classifier/
│   │   ├── detector.py            # Unified 3-stage format & vendor classifier
│   │   ├── signatures.py          # Format regex signatures & vendor patterns
│   │   ├── format_detector.py     # Stage 1: Deterministic format detector
│   │   └── source_detector.py     # Stage 2: Vendor pattern & keyword matcher
│   ├── registry/
│   │   ├── models.py              # ParserDefinition & ParserStatus schemas
│   │   ├── repository.py          # Storage layer loading YAML & tracking versions
│   │   └── service.py             # Parser lifecycle, activation, rollback, matching
│   ├── engine/
│   │   ├── base.py                # BaseParser interface
│   │   ├── grok.py                # Grok pattern parsing engine
│   │   ├── regex.py               # ReDoS-safeguarded Regex parsing engine
│   │   ├── json_parser.py         # JSON parsing engine (orjson)
│   │   ├── cef.py                 # Common Event Format (CEF) state machine parser
│   │   ├── leef.py                # Log Event Extended Format (LEEF) parser
│   │   └── kv.py                  # Key-Value (kv) parser engine
│   ├── discovery/
│   │   ├── profiler.py            # Event payload profiler
│   │   ├── field_detector.py      # Unknown payload key-value extractor
│   │   ├── suggestion.py          # UES candidate target mapping suggestions
│   │   └── confidence.py          # Discovery confidence scoring
│   ├── studio/
│   │   ├── mappings.py            # Parser mapping builder
│   │   ├── validation.py          # Parser syntax & ReDoS safety validator
│   │   └── testing.py             # Dry-run test runner for candidate parsers
│   ├── replay/
│   │   └── service.py             # Replay engine for stored raw events
│   ├── models/
│   │   ├── envelope.py            # M1 RawEventEnvelope model
│   │   └── parsed_event.py        # M2 ParsedEvent output contract for M3
│   └── health/
│       └── health.py              # Prometheus metrics & health checks
├── parsers/                       # Declarative YAML Parsers
│   ├── cisco/asa.yaml             # Cisco ASA firewall parser
│   ├── fortinet/fortigate.yaml    # Fortinet FortiGate parser
│   ├── paloalto/panos.yaml        # Palo Alto PAN-OS parser
│   ├── linux/syslog.yaml          # Linux Syslog & Auth parser
│   └── generic/                   # Generic JSON, CEF, LEEF, Key-Value parsers
├── tests/
│   ├── unit/                      # Unit tests for classifier, engine, registry, discovery
│   ├── golden/                    # Golden log test suites
│   └── performance/               # Latency benchmark tests
├── Dockerfile                     # Docker container build script
├── requirements.txt               # Python package dependencies
├── .env.example                   # Environment configuration
├── openapi.json                   # Exported OpenAPI specification
├── demo_script.py                 # E2E demonstration script
└── README.md                      # Documentation
```

---

## Key Features

1. **Format Classification**: Detects `json`, `syslog`, `cef`, `leef`, `csv`, `xml`, `kv`, `plain_text`.
2. **Source / Vendor Identification**: Identifies Cisco, Fortinet, Palo Alto, Linux, Windows, AWS, Azure, etc.
3. **Declarative & Safe Parser Engine**: Grok, Regex, JSON, CEF, LEEF, Key=Value with ReDoS regex safeguards and payload size limits.
4. **Air-Gapped Unknown-Source Discovery**: Profiles unknown logs, extracts candidate fields, and generates candidate canonical target mapping suggestions completely offline.
5. **Parser Studio & Semantic Versioning**: Validate, test, register, disable, enable, and rollback parser versions (`1.0.0`, `1.1.0`).
6. **Historical Event Replay**: Re-processes stored raw envelopes through newly registered parser versions.
7. **Observability**: Prometheus metrics (`ulpf_parser_events_total`, `ulpf_parser_latency_seconds`, etc.).

---

## Quick Start & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run Test Suite & Benchmarks
```bash
pytest tests/unit tests/golden tests/performance -v
```

### 3. Run End-to-End Demo Script
```bash
python demo_script.py
```

### 4. Start REST API Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8082
```
Access Swagger UI at `http://localhost:8082/docs`.

### 5. Docker Deployment
```bash
docker build -t ulpf-m2-parser .
docker run -p 8082:8082 ulpf-m2-parser
```

---

## Performance Benchmark Results

- **Format & Vendor Classification Latency**: ~0.10 - 0.18 ms (Target < 1 ms)
- **Parser Execution Latency**: ~0.06 - 0.08 ms (Target < 2 ms)
