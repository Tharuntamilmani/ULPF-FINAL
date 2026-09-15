# ULPF Phase 0 — Inter-Module Contract Compatibility Matrix

**Audit Date**: September 14, 2026  
**Status**: Forensic Analysis Complete  
**Methodology**: Direct source code comparison between producer output serializers and consumer input validators.

---

## 1. Master Compatibility Matrix

| Boundary | Producer | Consumer | Producer Emits | Consumer Expects | Versions | Compatible? | Severity | Required Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **M1 $\to$ M2** | M1 Ingestion | M2 Parser | `RawEventEnvelope` (M1 schema) with nested `payload`, `transport`, `integrity`, `raw_storage` objects | `RawEventEnvelope` (M2 schema) with flat `payload: str`, `transport: str`, `sha256: str`, `raw_reference: str` | `1.0.0` vs `1.0.0` | **NO** | **P0 (Critical)** | Deploy an integration adapter / serializer to unwrap `payload.data` to `payload`, extract `transport.protocol`, `integrity.hash`, and `raw_storage.object_key`. |
| **M2 $\to$ M3** | M2 Parser | M3 Normalizer | `ParsedEvent` (M2 schema) with `tenant_id`, `source_id`, `status`, `fields`, `sha256`, `raw_reference` | `ParsedEvent` (M3 schema) with `extra="allow"`. Accepts dict, but `builder.py` drops `tenant_id`, `source_id`, `sha256`, and `raw_reference` | `1.0.0` vs `1.0.0` | **PARTIAL** | **P1 (High)** | Adapter must preserve `tenant_id` and pass `integrity` and `raw` metadata in M3's nested structure (`{"integrity": {"hash": {"algorithm": "SHA-256", "value": ...}}, "raw": {"storage_ref": ...}}`). |
| **M3 $\to$ M4** | M3 Normalizer | M4 Enrichment | `NormalizationResult.event` wrapped in `{"ulpf": { "schema": ..., "event": ..., "source": ... }}`. Missing `tenant` block | `EnrichmentRequest` with flat `CanonicalEvent` (`extra="forbid"`), requiring root `schema_version`, `event`, `source`, `provenance`, and `tenant.tenant_id` | `1.0.0` vs `ues.v1` | **NO** | **P0 (Critical)** | Adapter must unwrap the outer `ulpf` key, elevate inner blocks (`event`, `source`, etc.) to top level, inject `tenant: {"tenant_id": ...}` preserved from M1/M2, and set `schema_version="ues.v1"`. |
| **M4 $\to$ M5** | M4 Enrichment | M5 Router | `EnrichmentResult` containing `event` (enriched `CanonicalEvent`), `provenance`, `diagnostics`, `integrity`. `event.tenant.tenant_id` | `POST /v1/events/process` expects flat event dict with `event.id`. `SmartRouter` looks for `tenant.id` or `tenant_id` (not `tenant.tenant_id`) | `1.0.0` vs `1.0.0` | **PARTIAL** | **P1 (High)** | Adapter must pass `result["event"]` to M5 with `result["integrity"]` attached, and duplicate `tenant.tenant_id` to `tenant.id` and `tenant_id` so M5's router correctly matches tenant policies. |
| **M6 $\to$ M1** | M6 Control | M1 Ingestion | HTTP health probe & JSON configuration distribution | M1 has `/health` and `/ready`, but NO dynamic configuration reload endpoint | `1.0.0` | **PARTIAL** | **P2 (Medium)** | Health check works. Dynamic config requires restart or integration reload hook. |
| **M6 $\to$ M2** | M6 Control | M2 Parser | M6 Parser Registry JSON / YAML format | M2 loads YAML parsers from filesystem or accepts `/v1/parsers` API; no Redis subscriber | `1.0.0` | **PARTIAL** | **P1 (High)** | Adapter / worker must sync approved parsers from M6 database to M2 filesystem or API. |
| **M6 $\to$ M3** | M6 Control | M3 Normalizer | M6 Mapping Registry JSON | M3 loads YAML mappings from `./mappings/` at startup; no HTTP reload API | `1.0.0` | **DISCONNECTED**| **P1 (High)** | Adapter / worker must materialize M6 field mappings into M3 mapping directory. |
| **M6 $\to$ M4** | M6 Control | M4 Enrichment | M6 Rule/Enrichment configuration | M4 exposes `POST /v1/config/reload`, but expects local YAML file | `1.0.0` | **PARTIAL** | **P1 (High)** | Adapter must trigger M4 reload endpoint when M6 distributes config. |
| **M6 $\to$ M5** | M6 Control | M5 Router | M6 Policy Registry JSON | M5 loads policies from `./policies/default.yaml` at startup; has internal reload | `1.0.0` | **PARTIAL** | **P1 (High)** | Adapter must synchronize M6 policies into M5 YAML format and call reload. |

---

## 2. In-Depth Boundary Forensic Analysis

### 2.1 Boundary: M1 (Ingestion) $\to$ M2 (Parser Engine)

#### The Actual Schema Discrepancy
In M1 (`app/envelope/models.py`), `RawEventEnvelope` is strictly typed with nested models:
```python
class RawEventEnvelope(BaseModel):
    schema_version: str = "1.0.0"
    raw_event_id: str                      # RFC 9562 UUIDv7
    tenant_id: str
    source_id: str
    source_type: str = "firewall"
    ingest_zone: str = "dmz"
    collector_id: str = "collector-01"
    received_at: str                       # ISO 8601 UTC
    transport: TransportInfo               # { protocol: "udp", port: 514 }
    payload: PayloadInfo                   # { encoding: "utf-8", format_hint: "syslog", data: "..." }
    integrity: IntegrityInfo               # { algorithm: "SHA-256", hash: "..." }
    raw_storage: RawStorageInfo            # { backend: "minio", bucket: "ulpf-raw", object_key: "..." }
```

In M2 (`app/models/envelope.py`), `RawEventEnvelope` expects flat primitive fields:
```python
class RawEventEnvelope(BaseModel):
    schema_version: str = "1.0.0"
    raw_event_id: str
    tenant_id: str = "tenant-default"
    source_id: Optional[str] = None
    received_at: str
    transport: str = "syslog"              # Primitive string!
    payload: str                           # Primitive string!
    encoding: str = "utf-8"
    sha256: Optional[str] = None           # Flat field!
    raw_reference: Optional[str] = None    # Flat field!
    source_ip: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
```

#### Empirical Incompatibility Demonstration
When M1 produces its envelope to Kafka topic `ulpf.raw` and M2 attempts to validate it:
- `payload` validation fails: M2 expects a string, receives `{"encoding": "utf-8", "format_hint": "syslog", "data": "..."}`.
- `transport` validation fails: M2 expects a string, receives `{"protocol": "udp", "port": 514}`.
- `sha256` is `None` in M2 unless recalculated because M1 nested it under `integrity.hash`.
- `raw_reference` is `None` in M2 because M1 nested it under `raw_storage.object_key`.

#### Severity: P0 (CRITICAL)
Direct pipeline connection without transformation results in 100% rejection of M1 events at the M2 input boundary.

---

### 2.2 Boundary: M2 (Parser Engine) $\to$ M3 (Normalizer)

#### The Actual Schema Discrepancy
In M2 (`app/models/parsed_event.py`), `ParsedEvent` emits:
```python
class ParsedEvent(BaseModel):
    schema_version: str = "1.0.0"
    raw_event_id: str
    tenant_id: str                         # e.g., "tenant-enterprise-1"
    source_id: Optional[str] = None        # e.g., "asa-firewall-01"
    status: str = "PARSED"
    classification: ClassificationResult   # { format, vendor, product, confidence }
    parser: ParserInfo                     # { id, name, version, confidence }
    fields: Dict[str, Any]                 # { srcip, dstip, action, ... }
    unmapped_fields: List[str]
    raw_reference: Optional[str] = None
    sha256: Optional[str] = None
    processing_time_ms: float
    metadata: Dict[str, Any]
```

In M3 (`app/models/parsed_event.py`), `ParsedEvent` defines:
```python
class ParsedEvent(BaseModel):
    model_config = ConfigDict(extra="allow")
    raw_event_id: str
    classification: ClassificationInfo | None = None
    parser: ParserInfo | None = None
    fields: dict[str, Any] = Field(default_factory=dict)
    unmapped_fields: list[str] = Field(default_factory=list)
    integrity: dict[str, Any] | None = None # Expects nested dict with "hash"
    raw: dict[str, Any] | None = None       # Expects nested dict with "storage_ref"
```

#### Empirical Incompatibility Demonstration
1. **Tenant ID Dropping**: M3's Pydantic model parses `tenant_id` because `extra="allow"`, but M3's `UESBuilder._construct_ues()` in `builder.py` **never reads** `event.tenant_id`. The resulting canonical `ULPFBlock` completely lacks tenant identity.
2. **Hash & Storage Reference Lost**: M2 passes `sha256` and `raw_reference` as flat top-level strings. M3 only checks `if event.integrity:` and `if event.raw:`. Consequently, `integrity_block` and `raw_block` in the canonical UES event remain `None`.

#### Severity: P1 (HIGH)
Events pass syntactically, but critical security and traceability metadata (`tenant_id`, `raw_reference`, `sha256`) is silently stripped from the pipeline.

---

### 2.3 Boundary: M3 (Normalizer) $\to$ M4 (Enrichment)

#### The Actual Schema Discrepancy
M3 returns `NormalizationResult` containing `UES`:
```json
{
  "success": true,
  "event": {
    "ulpf": {
      "schema": { "version": "1.0.0", "specification": "UES" },
      "event": { "id": "uuid", "timestamp": "...", "type": "network", ... },
      "source": { "ip": "192.168.1.1", "port": 51542 },
      "destination": { "ip": "8.8.8.8", "port": 443 },
      "provenance": { "raw_event_id": "raw-001" },
      "vendor": { "fields": { ... } }
    }
  }
}
```

M4 (`app/contracts/canonical_event.py`) expects `EnrichmentRequest`:
```python
class CanonicalEvent(BaseModel):
    model_config = ConfigDict(extra="forbid") # Rejects unexpected keys!
    schema_version: str = "ues.v1"
    event: EventMetadata                      # Must be at root
    observer: Observer
    source: Endpoint
    destination: Endpoint
    network: Network
    provenance: ProvenanceMetadata            # Must be at root
    tenant: TenantMetadata                    # Required: tenant.tenant_id
    extensions: dict[str, Any]
```

#### Empirical Incompatibility Demonstration
1. **Root Encapsulation Collision**: M3 encapsulates the canonical event under `"ulpf": { ... }`. M4 defines fields at root and specifies `extra="forbid"`. Submitting M3's payload to M4 yields:
   `pydantic_core._pydantic_core.ValidationError: Extra inputs are not permitted [key='ulpf']`.
2. **Missing Tenant Metadata**: M4 enforces `tenant.tenant_id` with `TenantGuard`. M3 output has no `tenant` object, triggering validation failure.
3. **Schema Version String**: M3 emits `schema: {version: "1.0.0"}`; M4 expects root `schema_version: "ues.v1"`.

#### Severity: P0 (CRITICAL)
100% of events emitted by M3 are rejected by M4's API validator.

---

### 2.4 Boundary: M4 (Enrichment) $\to$ M5 (Policy Engine & Router)

#### The Actual Schema Discrepancy
M4 returns `EnrichmentResult`:
```json
{
  "event": {
    "schema_version": "ues.v1",
    "event": { "id": "evt-001", "timestamp": "...", "severity": "high" },
    "source": { "ip": "192.168.1.100" },
    "tenant": { "tenant_id": "tenant-corp" },
    "extensions": { "enrichment": { ... } }
  },
  "status": "SUCCESS",
  "provenance": [ ... ],
  "diagnostics": { ... },
  "integrity": {
    "algorithm": "sha256",
    "digest": "abc123...",
    "canonicalization": "rfc8785",
    "phase": "enriched"
  }
}
```

M5 (`app/router/router.py`) evaluates the event:
```python
def extract_event_id(self, event: Dict[str, Any]) -> str:
    event_id = extract_field_value(event, "event.id")
    if not event_id:
        event_id = event.get("event_id") or event.get("id") or "unknown_event_id"
    return str(event_id)

def extract_tenant_id(self, event: Dict[str, Any]) -> Optional[str]:
    tenant_id = extract_field_value(event, "tenant.id")
    if not tenant_id:
        tenant_id = event.get("tenant_id") or extract_field_value(event, "tenant_id")
    return str(tenant_id) if tenant_id else None
```

#### Empirical Incompatibility Demonstration
1. **Payload Unpacking**: If the entire `EnrichmentResult` is forwarded, `extract_field_value(event, "source.ip")` returns `None` because `source` is located at `event["event"]["source"]["ip"]`. The outer envelope must be unwrapped, passing `result["event"]`.
2. **Tenant ID Key Mismatch**: M4 provides `event["tenant"]["tenant_id"]`. M5 checks `event["tenant"]["id"]` or `event["tenant_id"]`. It **does not check** `tenant.tenant_id`. Consequently, `extract_tenant_id()` returns `None`, breaking tenant-specific routing rules in M5.

#### Severity: P1 (HIGH)
Tenant routing rules fail silently, defaulting all events to un-tenanted routing.
