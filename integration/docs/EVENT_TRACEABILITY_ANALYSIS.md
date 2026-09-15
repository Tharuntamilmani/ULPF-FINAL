# ULPF Phase 0 — End-to-End Event Traceability Analysis

**Audit Date**: September 14, 2026  
**Status**: Complete  
**Scope**: Field survival, lineage integrity, and corruption analysis across representative event archetypes from raw ingress to multi-destination delivery.

---

## 1. Field Survival & Lineage Tracking Matrix

The table below tracks the survival of critical canonical fields across all module boundaries:

| Pipeline Stage / Boundary | `raw_event_id` | `event.id` | `tenant_id` | `schema_version` | `source_id` | Timestamps (`received_at`, `event.timestamp`) | Parser Identity (`id`, `version`) | Normalization Identity (`mapping_version`) | Provenance Lineage | Integrity Digest (`sha256`) | Enriched Attributes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Ingress $\to$ M1** | Generated (UUIDv7) | Not yet created | Extracted from Header / Default | `"1.0.0"` | Extracted from Header / Default | `received_at` generated (UTC) | None | None | Stored in MinIO vault key | Calculated over exact raw bytes | None |
| **M1 $\to$ M2 Boundary** | **SURVIVES** | Not yet created | **SURVIVES** | **SURVIVES** | **SURVIVES** | **SURVIVES** (`received_at`) | None | None | MinIO object key in `raw_storage` | Present in `integrity.hash` | None |
| **M2 Execution** | **SURVIVES** | Not yet created | **SURVIVES** | **SURVIVES** | **SURVIVES** | Extracted from log or fallback to `received_at` | Attached (`parser.id`, `parser.version`) | None | Preserved in `raw_reference` | Preserved in `sha256` | None |
| **M2 $\to$ M3 Boundary** | **SURVIVES** | Not yet created | **DROPPED BY M3 BUILDER** ⚠️ | Schema converted to UES 1.0.0 | **DROPPED BY M3 BUILDER** ⚠️ | `event.timestamp` converted to RFC3339 | `parser.id`, `parser.version` preserved | Created (`mapping_version`) | Preserved in `provenance.raw_event_id` | **LOST / NOT MAPPED** ⚠️ | None |
| **M3 Execution** | **SURVIVES** | Generated (UUIDv4) | **MISSING IN UES BLOCK** ⚠️ | `"1.0.0"` inside `ulpf.schema` | **MISSING** ⚠️ | `timestamp`, `received_at` present | Preserved in `ulpf.parser` | Preserved in `ulpf.normalization` | Preserved in `ulpf.provenance` | `ulpf.integrity` is `null` ⚠️ | None |
| **M3 $\to$ M4 Boundary** | **SURVIVES** | **SURVIVES** | **REJECTED (Missing)** ⚠️ | Mismatch (`1.0.0` vs `ues.v1`) ⚠️ | **MISSING** | **SURVIVES** | **SURVIVES** | **SURVIVES** | **SURVIVES** | **LOST** | Pre-enrichment |
| **M4 Execution** | **SURVIVES** | **SURVIVES (Immutable)** | Present (injected by adapter/context) | `"ues.v1"` | Injected / preserved | **SURVIVES (Immutable)** | **SURVIVES** | **SURVIVES** | Appends M4 provider provenance | Attached (RFC 8785 SHA-256 over enriched event) | Added to `extensions.enrichment` |
| **M4 $\to$ M5 Boundary** | **SURVIVES** | **SURVIVES** | Key mismatch (`tenant.tenant_id` vs `tenant.id`) ⚠️ | `"ues.v1"` | Available | **SURVIVES** | **SURVIVES** | **SURVIVES** | **SURVIVES** | Attached in `result.integrity` | **SURVIVES** |
| **M5 Delivery (SIEM / Lake)**| Indexed / Logged | Primary Deduplication Key | Path Partition Key | Logged in metadata | Indexed | Event & routing timestamps logged | Preserved in record | Preserved in record | Preserved in record | Stored with event payload | Fully delivered |

---

## 2. Forensic Trace of Five Representative Event Archetypes

### Archetype 1: Cisco ASA Firewall Syslog (Known Network Security Event)

#### Raw Ingress Payload
```syslog
<134>Sep 12 09:30:15 FW-EDGE-01 %ASA-6-302013: Built inbound TCP connection 892341 for outside:192.168.1.100/49152 (192.168.1.100/49152) to inside:10.0.0.5/80 (10.0.0.5/80)
```

#### Step-by-Step Lifecycle Trace
1. **M1 Ingestion**:
   - Ingested via UDP Port 514. Header defaults: `tenant_id="tenant-alpha"`, `source_id="fw-edge-01"`.
   - Raw bytes hashed: SHA-256 = `5b02b5fc0bcad3672aedc0086478ee016cf89497554f2423188e63e271a3de76`.
   - ID generated: `raw_event_id="0191eb54-3e91-723a-8b5e-17cf3b2a8190"` (UUIDv7).
   - Saved to MinIO: `ulpf-raw/tenant=tenant-alpha/year=2026/month=09/day=12/source=fw-edge-01/event=0191eb54-3e91-723a-8b5e-17cf3b2a8190.gz`.
   - Emitted to Kafka `ulpf.raw`.
2. **M2 Format Classification & Parsing**:
   - Classification: Format `syslog`, Vendor `Cisco`, Product `ASA`, Confidence `0.99`.
   - Parser matched: `parser-cisco-asa` (v1.2.0).
   - Fields extracted: `action="allow"`, `srcip="192.168.1.100"`, `srcport=49152"`, `dstip="10.0.0.5"`, `dstport=80`, `protocol="tcp"`, `connection_id="892341"`.
   - Emitted `ParsedEvent`.
3. **M3 Canonical Normalization**:
   - Target mapping resolved: `parser-cisco-asa.yaml`.
   - Normalized fields:
     - `event.kind="event"`, `event.type="network"`, `event.action="allow"`, `event.outcome="success"`
     - `source.ip="192.168.1.100"`, `source.port=49152`
     - `destination.ip="10.0.0.5"`, `destination.port=80`
     - `network.transport="TCP"`, `network.protocol.transport="TCP"`
   - `provenance.raw_event_id="0191eb54-3e91-723a-8b5e-17cf3b2a8190"`.
   - **Traceability Breach**: `tenant_id="tenant-alpha"` is **dropped** by M3 builder; not present in `ULPFBlock`.
4. **M4 Enrichment & Cryptographic Integrity**:
   - Re-injected `tenant_id="tenant-alpha"`.
   - Contextual lookups executed:
     - `LocalAssetProvider`: matches destination `10.0.0.5` $\to$ Hostname `PROD-WEB-01`, Criticality `HIGH`.
     - `LocalGeoIPProvider`: source `192.168.1.100` $\to$ Private network (RFC 1918).
     - `LocalThreatIntelProvider`: clean.
   - Enriched data injected into `extensions.enrichment.asset` and `extensions.enrichment.geoip`.
   - Cryptographic Integrity: JCS RFC 8785 serialized byte stream hashed with SHA-256, attaching `IntegrityMetadata`.
5. **M5 Policy Routing & Multi-Destination Delivery**:
   - Smart Router evaluated: matches `default-firewall-rule` and `data-lake-archive`.
   - Delivered to:
     - OpenSearch: indexed in `ulpf-events-v1-tenant-alpha`.
     - Data Lake: appended to `./data/datalake/date=2026-09-12/tenant=tenant-alpha/events.jsonl`.
     - AI Stream: Kafka topic `ulpf.ai.events`.

---

### Archetype 2: Windows Security Audit Event 4624 (XML Authentication Event)

#### Raw Ingress Payload
```xml
<Event xmlns="http://schemas.microsoft.com/win/2004/08/events/event">
  <System>
    <Provider Name="Microsoft-Windows-Security-Auditing" Guid="{54849625-5478-4994-A5BA-3E3B0328C30D}" />
    <EventID>4624</EventID>
    <TimeCreated SystemTime="2026-09-12T04:00:15.123456Z" />
  </System>
  <EventData>
    <Data Name="TargetUserName">svc_backup</Data>
    <Data Name="TargetDomainName">CORP</Data>
    <Data Name="LogonType">3</Data>
    <Data Name="IpAddress">10.0.2.50</Data>
    <Data Name="IpPort">58492</Data>
  </EventData>
</Event>
```

#### Step-by-Step Lifecycle Trace
1. **M1**: Ingested via HTTP `POST /v1/events` with header `X-Tenant-ID: corp-it`. UUIDv7 generated, raw XML compressed in MinIO vault, SHA-256 computed.
2. **M2**: Classifier identifies format `xml`, source `Windows`. XML parser extracts `EventID=4624`, `TargetUserName="svc_backup"`, `TargetDomainName="CORP"`, `LogonType=3`, `IpAddress="10.0.2.50"`.
3. **M3**: Normalized to `event.type="authentication"`, `event.action="logon"`, `event.outcome="success"`, `identity.user.username="svc_backup"`, `identity.user.domain="CORP"`, `source.ip="10.0.2.50"`. Unmapped XML metadata preserved in `vendor.fields`.
4. **M4**: `LocalAssetProvider` enriches `svc_backup` with user role `SERVICE_ACCOUNT`; computes canonical RFC 8785 SHA-256 digest.
5. **M5**: Evaluates `windows-auth-policy`, routes to OpenSearch and Data Lake.

---

### Archetype 3: Unknown Proprietary Event (Discovery & Replay Flow)

#### Raw Ingress Payload
```text
DEVICE_SN=XY9021;STATUS=WARN;TEMP_C=84.2;FIRMWARE=3.1.2;SRC=172.16.50.4;MSG=Thermal threshold exceeded
```

#### Step-by-Step Lifecycle Trace
1. **M1**: Accepted as raw text via TCP syslog listener. Raw hash computed, UUIDv7 assigned, stored in MinIO. Emitted to Kafka.
2. **M2**: Classifier detects format `kv` but vendor `Unknown`.
   - No registered parser matches.
   - Event status set to `UNPARSED`.
   - Forwarded to Unknown-Source Discovery Engine (`profiler.py`).
   - Discovery extracts candidate fields: `DEVICE_SN`, `STATUS`, `TEMP_C`, `SRC`, `MSG`.
   - Parser Studio suggests Grok/KV mapping with candidate confidence 0.82.
3. **M3**: Standard M3 receives `ParsedEvent` with `parser.id="generic"`.
   - Maps `SRC` to `source.ip="172.16.50.4"`.
   - Remaining fields stored in `vendor.fields` (`TEMP_C`, `DEVICE_SN`, etc.). Normalization status: `partial`.
4. **M4 & M5**: Enriched with private subnet GeoIP and routed to default fallback data lake archive.
5. **Replay Loop**: Once administrator registers parser `iot-sensor-xy90` in M2 Parser Studio, M2 `ReplayService` fetches raw payload from M1 MinIO vault and re-parses with status `PARSED`.

---

### Archetype 4: Malformed Payload (Truncated / Corrupted Frame)

#### Raw Ingress Payload
```text
<134>Sep 12 09:30:15 FW-EDGE-01 %ASA-6-302013: Built inbound TCP connection [TRUNCATED AT EOF
```

#### Step-by-Step Lifecycle Trace
1. **M1**: Accepts exact bytes. Computes SHA-256 over truncated stream. Durably writes to MinIO.
2. **M2**: Recognizes Cisco ASA prefix, but regex parsing fails due to missing connection details.
   - Status set to `FAILED`. `unmapped_fields=["raw_payload"]`.
   - Emits `ParsedEvent` with raw text preserved.
3. **M3**: Normalizer detects unparsed status.
   - Retains `provenance.raw_event_id`.
   - Populates `event.kind="event"`, `event.type="unknown"`, `event.outcome="unknown"`.
   - Normalization status set to `failed`. Raw text preserved in `raw.message_preview`.
4. **M4**: Bypasses contextual enrichment (no IPs or domains available). Attaches provenance and RFC 8785 integrity digest over failed canonical structure.
5. **M5**: Matches DLQ routing policy; routed to Dead Letter Queue for forensic investigation.

---

### Archetype 5: Non-UTF-8 / Raw Binary Event

#### Raw Ingress Payload
`\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR...` or arbitrary binary telemetry bytes (`0xDEADBEEF01020304`).

#### Step-by-Step Lifecycle Trace
1. **M1**:
   - Ingested via TCP stream.
   - UTF-8 decoding throws `UnicodeDecodeError`.
   - Ingestion pipeline automatically switches encoding: `payload.encoding="base64"`, `payload.data=base64(raw_bytes)`.
   - Exact SHA-256 computed over original binary bytes.
   - Stored in MinIO vault.
2. **M2**:
   - Inspects `encoding="base64"`.
   - Classifies format as `binary` / `plain_text`.
   - Zero parsing applied. Status: `UNPARSED`.
3. **M3**:
   - Stored in `raw.encoding="base64"`.
   - Preserves `provenance.raw_event_id`.
4. **M4 & M5**:
   - Cryptographically hashed and routed to cold Data Lake storage.
   - Zero silent data loss or crash.
