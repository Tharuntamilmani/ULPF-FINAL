# ULPF — Live Demo Control Center & SOC Prototype UI Demonstration Guide
## Smart India Hackathon (SIH) Jury Presentation Playbook

---

## 1. Executive Summary & Core Value Proposition

The **Universal Log Pre-processing Framework (ULPF)** solves the foundational challenge of multi-tenant enterprise SOCs:
> **"Different raw logs enter ULPF and become trusted, normalized, enriched, and routed Universal Events — with 100% cryptographic traceability back to the original raw evidence."**

This user interface was built to make this concept immediately obvious to judges within **10 seconds** of viewing.

---

## 2. Architecture: Data Plane vs. Control Plane

The interface visually enforces the architectural separation:

```
                              ┌────────────────────────────────────────┐
                              │           M6 CONTROL PLANE             │
                              │ (Tenant Governance, Parsers, Policies) │
                              └───────────────────┬────────────────────┘
                                                  │ ConfigurationSync (:18081)
                   ┌──────────────────────────────┴──────────────────────────────┐
                   │                                                             │
RAW LOG ──► INGRESS GATEWAY ──► M1 INGESTION ──► KAFKA ──► M2 PARSER ──► M3 NORMALIZER ──► M4 ENRICHMENT ──► M5 ROUTING ──► DESTINATIONS
(:Wire)          (:18080)          (:18001)     (:9092)   (:18082)       (:18083)         (:18004)       (:18085)     (OpenSearch :9200)
              Tenant Auth &      MinIO Vault &   Topic:   Vendor Regex    Canonical UES     GeoIP, CMDB,   Policy Match  Cold Lake (MinIO)
              Anti-Spoofing      Raw SHA-256    ulpf.raw  Grok Parser       v1.0.0          Threat Intel    Multiplex     AI Anomaly Stream
```

---

## 3. How to Start the UI

### Step 1: Start the Frontend Dev Server
In PowerShell:
```powershell
cd E:\ULPF\M6\M6-SIH-main\frontend
npm run dev -- --host 127.0.0.1 --port 5173
```
*The dev server is now active at: `http://127.0.0.1:5173/`*

### Step 2 (Optional for full live backend): Start the Microservice Stack
In a separate terminal:
```powershell
cd E:\ULPF
python run_stack.py
```

> [!NOTE]
> **Resilient Presentation Guarantee**: If the backend microservice stack is offline or recovering, the UI functions autonomously in high-fidelity **DEMO MODE**. All golden events, UES schema transformations, and SHA-256 verifications compute deterministically using client-side Web Crypto and contract specifications. When the backend is online, real live endpoints (`/gateway-api`, `/events-api`, `/system-health`, `/m2-api`) are queried automatically.

---

## 4. Port & Service Directory

| Service | Component | Port | Health Endpoint | Responsibility |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend UI** | React + Vite + TypeScript | `5173` | `http://127.0.0.1:5173` | SOC Dark Dashboard & Demonstration Cockpit |
| **Ingress Gateway** | FastAPI Boundary | `18080` | `http://127.0.0.1:18080/health` | Tenant Authentication & Anti-Spoofing |
| **M1 Ingestion** | Raw Evidence Vault | `18001` | `http://127.0.0.1:18001/health` | Authoritative SHA-256 & MinIO object store |
| **Kafka Broker** | Event Stream | `9092` | TCP `localhost:9092` | Decoupled streaming queue (`ulpf.raw`) |
| **M2 Parser Engine** | Pattern Classifier | `18082` | `http://127.0.0.1:18082/health` | Vendor regex/grok & ReDoS analysis |
| **M3 Normalizer** | Canonical UES | `18083` | `http://127.0.0.1:18083/health` | Canonical UES v1.0.0 schema normalization |
| **M4 Enrichment** | Context Intelligence | `18004` | `http://127.0.0.1:18004/health` | GeoIP, CMDB, Threat Intel & RFC-8785 digest |
| **M5 Smart Router** | Policy Evaluator | `18085` | `http://127.0.0.1:18085/health` | Routing engine & OpenSearch dispatcher |
| **M6 Control Plane** | Central Governance | `18086` | `http://127.0.0.1:18086/health` | Parser registry, outbox sync & tenant CRUD |
| **Health Aggregator** | System Observer | `18090` | `http://127.0.0.1:18090/live` | Multi-node live latency and health probe |
| **OpenSearch SIEM** | Datastore | `9200` | `http://127.0.0.1:9200` | Event analytics & indexing |

---

## 5. Live Demo Script for SIH Judges (11-Step Walkthrough)

### Step 1: Open the Application & 1-Click Access
1. Open browser to: **`http://127.0.0.1:5173/`**
2. On the login screen, click the prominent green button: **`[ 🛡️ 1-CLICK SIH JURY ACCESS ]`**
3. The dashboard opens instantly with authenticated evaluator credentials.

---

### Step 2: Explain the Hero Dashboard & Health Ribbon
1. Point to the **System Health Ribbon** at the top:
   - Gateway, M1, Kafka, M2, M3, M4, M5, M6 all showing live health and millisecond latencies.
2. Point to the **Hero Pipeline**:
   - Upper Tier: `M6 Control Plane` governing schemas and policies.
   - Lower Tier: Flowing horizontal data plane from raw wire logs to output destinations.
3. Announce to judges:
   > *"Notice how the architecture separates the high-throughput Data Plane from the central M6 Control Plane."*

---

### Step 3: Send a Real Cisco ASA Firewall Event
1. Click the primary blue button: **`[ + SEND TEST EVENT ]`**
2. In the modal:
   - Template: **`Cisco ASA Firewall (Built Connection)`** is selected.
   - Target Tenant: **`tenant-cisco`**
   - Source Sensor: **`cisco-asa-fw01`**
   - Inbound Payload: Real RFC-5424 syslog text:
     `<166>Sep 14 10:00:15 cisco-asa %ASA-6-302013: Built inbound TCP connection 847392 for outside:192.168.10.25/51542 to inside:8.8.8.8/443`
3. Click **`[ SEND EVENT ]`**
4. **Watch the live visual animation**:
   - The pulse glows sequentially across each stage:
     `Gateway (AUTH OK) → M1 (VAULT SHA-256) → Kafka (STREAMED) → M2 (PARSED) → M3 (CANONICAL UES) → M4 (ENRICHED) → M5 (ROUTED) → Destinations (INDEXED)`.
5. Point to the right-side **Live Event Inspector**:
   - Event ID generated (e.g., `evt_...`).
   - M1 Authoritative SHA-256 displayed.
   - All 7 processing hops completed in under 30ms.

---

### Step 4: Show Stage Details (Deep-Dive Inspection)
1. Click the **`M1 INGESTION`** card in the pipeline:
   - Drawer slides open.
   - Show judges: Raw Event ID, Payload Size (136 bytes), MinIO S3 Vault Path (`raw/tenant-cisco/...dat`), and Authoritative SHA-256.
2. Click the **`M2 PARSER`** card:
   - Show: Parser ID (`parser-cisco-asa`), extracted fields (`srcip: 192.168.10.25`, `dstip: 8.8.8.8`, `protocol: TCP`, `action: allow`).
3. Click the **`M3 NORMALIZER`** card:
   - Show: Conformance to Canonical UES v1.0.0 with `VALID_STRICT` badge.
4. Click the **`M4 ENRICHMENT`** card:
   - Show: GeoIP attached (City: Dallas, US), CMDB Asset context, and RFC-8785 canonical JSON digest.
5. Click the **`M5 ROUTING`** card:
   - Show: Policy match (`policy-security-alerts`), and concurrent dispatch to OpenSearch SIEM, Cold Data Lake, and AI Stream.
6. Close the drawer.

---

### Step 5: Show the Canonical Universal Event (UES) Viewer
1. Click **`[ VIEW UES ]`** in the inspector or navigate to **`/events/:id`**.
2. Point out the 3-column structured layout:
   - **Left**: Event ID, Timestamp, Category (`network`), Action (`built`), Outcome (`success`), Severity Level 2.
   - **Middle**: Normalized Source (`192.168.10.25:51542`), Destination (`8.8.8.8:443`), Transport (`TCP`), Bytes (1,450).
   - **Right**: Parser ID, Normalizer validation, Enrichment providers, and Raw Vault reference.
3. Click the **`[ UES JSON ]`** tab:
   - Show the clean, syntax-highlighted canonical JSON document.
   - Click **`[ COPY JSON ]`** to demonstrate developer-friendly tooling.

---

### Step 6: The "Showstopper" — Event Traceability & Forensic Lineage
1. Click the **`[ LINEAGE TRACE ]`** tab or click **`[ TRACE EVENT ]`** in the navigation.
2. Announce to the judges:
   > *"Now for the most important feature of ULPF: Lossless Forensic Lineage. Even though the log was parsed, normalized, and enriched, we can trace all the way back to the exact wire evidence."*
3. Show the vertical lineage graph:
   - `M5 Routed Event` ↓
   - `M4 Enriched Event (RFC-8785 Digest)` ↓
   - `M3 Universal Event (UES v1.0.0)` ↓
   - `M2 Parsed Event (Cisco ASA)` ↓
   - `M1 Raw Envelope (MinIO Vault)` ↓
   - `Original Raw Bytes (Wire Payload)`
4. Point to the bottom **Forensic Integrity Seal**:
   - `✓ CRYPTOGRAPHIC INTEGRITY VERIFIED (Lossless)`
   - Authoritative SHA-256 Checksum: `c8307d...`

---

### Step 7: Live Cryptographic Verification of Raw Evidence
1. Click **`[ VIEW ORIGINAL RAW EVENT ]`** to open `/raw-evidence`.
2. Show the untouched raw ASCII wire text.
3. Click the interactive button: **`[ VERIFY INTEGRITY ]`**
4. The browser re-computes the SHA-256 hash in real-time over the exact string using the Web Crypto API.
5. Watch the banner light up green:
   > **`✓ HASH MATCH: 100% EVIDENCE INTEGRITY VERIFIED`**
6. Announce:
   > *"This mathematically proves in front of your eyes that not a single byte was corrupted or lost."*

---

### Step 8: Demonstrate the M6 Control Plane & Configuration Lifecycle
1. Click **`CONTROL PLANE` → `Parsers`** in the sidebar (or `/parsers`).
2. Point out the visual **Configuration Distribution Pipeline**:
   - `M6 Outbox → Validate (ReDoS) → Version → Distribute → M2 Engine → ACK → ACTIVE`
3. Click **`[ + REGISTER PARSER ]`**:
   - Show the ReDoS Static Vulnerability check button.
   - Click **`[ TEST REDOS ]`** to show static regex complexity analysis.
   - Explain that M6 distributes hot updates to M2 without restarting the ingestion pipeline.

---

### Step 9: Show System Architecture Topology
1. Click **`OPERATIONS` → `Architecture`** in the sidebar.
2. Walk through the complete technical blueprint:
   - Control Plane Tier (M6 + ConfigSync)
   - Data Plane Tier (Ingress Gateway, M1, Kafka, M2, M3, M4, M5, Outputs)
   - Infrastructure Datastores (PostgreSQL, Redis, Kafka, MinIO, OpenSearch)

---

### Step 10: Show Fault Tolerance & Zero-Loss Failure Recovery
1. Click **`DEMO` → `Demo Mode (Cockpit)`** in the sidebar.
2. Click **`[ SHOW RECOVERY ]`** to reveal the **Zero-Loss Failure Recovery Simulation**:
3. Select **`Simulate M2 Parser Unavailable`** and click **`[ RUN SIMULATION ]`**:
   - Step 1: M1 stores event in vault and publishes to Kafka.
   - Step 2: M2 returns HTTP 503 during reload.
   - Step 3: Kafka offset is **NOT** committed; bridge holds message and enters exponential backoff.
   - Step 4: M2 process health probe passes (200 OK).
   - Step 5: Bridge resumes, M2 acknowledges 200 OK, offset committed, zero logs lost.

---

### Step 11: Switch to Fullscreen Presentation Mode (For Stage / Projector)
1. Click **`[ 🖥️ PRESENTATION MODE (HUD) ]`** at the top right.
2. The UI switches into a high-contrast, large-font projector mode:
   - Clean, uncluttered layout readable from several meters away.
   - Shows live event transit, status badges, and quick CTA buttons (`[ VIEW UES ]`, `[ TRACE EVENT ]`, `[ VIEW RAW ]`).
3. Press `[ EXIT FULLSCREEN ]` or `ESC` to return to standard SOC view.

---

## 6. Real API vs. Demo Simulation Distinction

In compliance with strict technical honesty guidelines:
- When the backend stack (`run_stack.py`) is running, all health, ingest, and event queries communicate with real microservice endpoints.
- When backend microservices are offline or in test environments, the UI clearly displays:
  - `DEMO SIMULATION` pill in the Live Event Inspector.
  - `DEMO METRICS` in the Observability dashboard.
- Real API data and simulated data are never conflated.

---

## 7. Troubleshooting

- **Port 5173 already in use**:
  Kill existing Vite process:
  ```powershell
  Stop-Process -Name node -Force -ErrorAction SilentlyContinue
  npm run dev -- --host 127.0.0.1 --port 5173
  ```
- **Login screen prompts for credentials**:
  Click **`[ 1-CLICK SIH JURY ACCESS ]`** or enter `admin` / `Admin_Secure_Pass_2026!`.
- **Backend API proxy 502/504 errors**:
  Expected if `python run_stack.py` is not active. The frontend automatically falls back to local deterministic contracts without crashing.
