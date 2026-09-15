# ULPF Phase 0 — Responsibility & Field Ownership Matrix

**Audit Date**: September 14, 2026  
**Status**: Complete  
**Scope**: Identification of authoritative field owners, mutability lifecycle, and cross-module boundary conflicts.

---

## 1. Authoritative Domain & Field Ownership

| Conceptual Domain / Field | Authoritative Owner | Generating Module | Mutability After Generation | Prohibited Modules | Enforcement Mechanism |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Raw Bytes & Storage** | Ingestion Boundary | **M1** | **IMMUTABLE** (Never altered) | M2, M3, M4, M5, M6 | MinIO S3 Object Lock & SHA-256 validation |
| **Raw SHA-256 Hash** | Cryptographic Integrity | **M1** | **IMMUTABLE** | M2, M3, M4, M5, M6 | Computed strictly over raw socket/HTTP bytes |
| **`raw_event_id`** | Raw Event Identity | **M1** (UUIDv7) | **IMMUTABLE** | M2, M3, M4, M5, M6 | Pydantic validation & preservation invariants |
| **Format Classification** | Source Understanding | **M2** | Immutable once parsed | M1, M3, M4, M5, M6 | `Classifier` signatures & confidence scoring |
| **Vendor & Product ID** | Source Understanding | **M2** | Immutable once parsed | M1, M3, M4, M5, M6 | M2 Vendor Pattern Matcher |
| **Raw Field Extraction** | Parser Engine | **M2** | Immutable once parsed | M1, M3, M4, M5, M6 | Declarative YAML parsers (Grok/Regex/KV) |
| **`event.id`** | Canonical Event ID | **M3** (or M1 passthrough) | **IMMUTABLE** | M4, M5, M6 | M4 `PreservationInvariant` assertion |
| **`event.action`** | Semantic Action | **M3** | **IMMUTABLE** | M1, M2, M4, M5, M6 | M3 `SemanticMapper` |
| **`event.outcome`** | Semantic Outcome | **M3** | **IMMUTABLE** | M1, M2, M4, M5, M6 | M3 `SemanticMapper` |
| **Canonical Endpoints** (`source.ip`, etc.) | Network Semantics | **M3** | **IMMUTABLE** | M1, M2, M4, M5, M6 | M4 `PreservationInvariant` assertion |
| **Vendor Fields (`vendor.fields`)** | Unmapped Preservation | **M3** | Append-only / Preserved | M1, M2, M4, M5, M6 | M3 `VendorPreserver` |
| **Contextual Enrichment** | Semantic Augmentation | **M4** | Additive only | M1, M2, M3, M5, M6 | Injected strictly into `extensions.enrichment` |
| **Enrichment Provenance** | Lineage & Audit | **M4** | Append-only | M1, M2, M3, M5, M6 | `ProvenanceTracker` |
| **Post-Enrichment Integrity** | Cryptographic Verification | **M4** | Recomputed on merge | M1, M2, M3, M5, M6 | RFC 8785 JCS + SHA-256 digest |
| **Routing Decision** | Policy Evaluation | **M5** | Ephemeral evaluation | M1, M2, M3, M4, M6 | `SmartRouter` condition tree |
| **Destination Delivery & Retries** | Egress Delivery | **M5** | Internal delivery state | M1, M2, M3, M4, M6 | `RetryEngine` + `DeadLetterQueue` |
| **Tenant & Source Catalog** | Platform Administration | **M6** | Versioned CRUD | M1, M2, M3, M4, M5 | PostgreSQL Registry Tables |
| **Parser Lifecycle State** | Platform Administration | **M6** | Versioned CRUD | M1, M2, M3, M4, M5 | M6 Parser Registry (`DRAFT` $\to$ `ACTIVE`) |

---

## 2. Ownership Conflicts & Boundary Violations Discovered

### Conflict 1: `event.id` Ownership & Generation
- **Owner Conflict**: M1 assigns a time-sortable RFC 9562 UUIDv7 (`raw_event_id`). M2 preserves it. M3, however, generates a *new* UUIDv4 in `builder.py:347` (`event_id = ev.get("id") or str(uuid.uuid4())`) unless `fields` already contained an `id`.
- **Architectural Risk**: Disconnect between the raw evidence identifier (`raw_event_id`) and the canonical event identifier (`event.id`).
- **Resolution Principle**: `raw_event_id` is the immutable raw anchor. M3 must use `raw_event_id` as the default basis or deterministically derive `event.id` from `raw_event_id` so that downstream tracking across M4 and M5 remains deterministic.

### Conflict 2: Multi-Tenancy Identity & Dropped Propagation
- **Owner Conflict**: M1 receives `tenant_id` from client headers. M2 records `tenant_id` in `ParsedEvent`. M3 completely omits `tenant_id` from its canonical `ULPFBlock` schema. M4 expects `tenant.tenant_id`. M5 expects `tenant.id` or root `tenant_id`.
- **Architectural Risk**: Broken chain of custody for tenant context. In multi-tenant environments, events from Tenant A risk being processed in an un-tenanted scope or rejected by M4's `TenantGuard`.
- **Resolution Principle**: Tenant identity belongs to the event throughout its entire lifecycle. The integration adapter must elevate and preserve `tenant_id` at every boundary.

### Conflict 3: Integrity Digest Duality (Raw vs Enriched)
- **Owner Conflict**: M1 computes SHA-256 over exact untouched wire bytes. M4 strips the `integrity` block, serializes the canonical model via RFC 8785 JCS, and computes a new SHA-256 digest over the normalized/enriched data.
- **Architectural Risk**: If downstream systems confuse M1's `raw_hash` with M4's `enriched_digest`, tamper verification fails.
- **Resolution Principle**: Clear separation of concerns:
  - `raw_hash` (M1 domain): Guarantees the raw bytes in MinIO were not tampered with.
  - `canonical_digest` (M4 domain): Guarantees canonical UES fields were not tampered with post-enrichment. Both must be preserved under explicit keys.

### Conflict 4: Database Independence (Zero Cross-Database Violations)
- **Audit Result**: **PASSED**.
- Static AST inspections confirm that:
  - No module directly connects to another module's internal database (M6 does not query M1's SQLite outbox; M5 does not inspect M6's PostgreSQL).
  - All inter-module communication is designed via API contracts or message bus topics.
