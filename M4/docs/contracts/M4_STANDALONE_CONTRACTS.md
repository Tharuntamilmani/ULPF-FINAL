# ULPF Module M4 — Standalone Contracts Specification

## 1. Internal Canonical UES v1 Contract
Module M4 defines a standalone canonical contract representing the Universal Event Schema (UES v1).

### Schema Version
`ues.v1`

### Key Model Definition (`CanonicalEvent`)
- **`schema_version`** (`string`, mandatory): `"ues.v1"`
- **`event`** (`object`, mandatory):
  - `id`: Unique event string `^[a-zA-Z0-9_\-\.]+$`
  - `timestamp`: ISO 8601 UTC string
  - `kind`: Category classification (e.g. `"event"`, `"alert"`)
  - `type`: Array of strings
  - `category`: Array of strings
  - `outcome`: `"success"`, `"failure"`, `"unknown"`
- **`provenance`** (`object`, mandatory):
  - `raw_event_id`: Immutable upstream raw identifier
  - `ingestion_timestamp`: Upstream timestamp
  - `pipeline_id`: Ingress pipeline identifier
- **`source`** / **`destination`** (`object`):
  - `ip`, `port`, `mac`, `nat_ip`, `domain`, `user`
- **`network`**, **`host`**, **`identity`**, **`application`**, **`process`**, **`security`**, **`parser`**, **`normalization`**, **`vendor`**: Authoritative upstream subsystems.
- **`extensions`** (`object`):
  - User-defined or module-specific data. Enrichment is strictly merged into `extensions["enrichment"]`.
- **`tenant`** (`object`):
  - `tenant_id`: Mandatory tenant string

---

## 2. Enrichment Request Contract (`EnrichmentRequest`)
```json
{
  "event": { ... },
  "tenant_context": {
    "tenant_id": "tenant_alpha",
    "scope": {},
    "configuration_version": "1.0.0"
  },
  "configuration_version": "1.0.0",
  "options": {
    "bypass_cache": false
  }
}
```

---

## 3. Enrichment Result Contract (`EnrichmentResult`)
```json
{
  "event": { ... },
  "status": "SUCCESS",
  "provenance": [
    {
      "provider_id": "asset-local-cmdb",
      "provider_version": "1.0.0",
      "enrichment_type": "asset",
      "lookup_timestamp": "2026-09-14T04:13:21.000Z",
      "confidence": 0.95,
      "result_status": "SUCCESS",
      "source_reference": "cmdb://shared/ASSET-PROD-DB-01",
      "configuration_version": "1.0.0",
      "cache_status": "MISS"
    }
  ],
  "diagnostics": {
    "total_duration_ms": 3.45,
    "providers_attempted": 3,
    "providers_succeeded": 3,
    "providers_failed": 0,
    "providers_timed_out": 0,
    "providers_not_found": 0,
    "provider_diagnostics": [ ... ]
  },
  "integrity": {
    "algorithm": "sha256",
    "digest": "64_character_hex_string",
    "canonicalization": "rfc8785",
    "generated_at": "2026-09-14T04:13:21.000Z",
    "phase": "enriched"
  }
}
```

---

## 4. Integrity Metadata Contract (`IntegrityMetadata`)
- `algorithm`: `"sha256"`
- `digest`: Hexadecimal SHA-256 string (64 characters lowercase)
- `canonicalization`: `"rfc8785"`
- `generated_at`: ISO 8601 UTC timestamp
- `phase`: `"raw"`, `"canonical"`, or `"enriched"`
