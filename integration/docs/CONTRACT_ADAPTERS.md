# ULPF Phase 1 — Contract Adapters Specification & Verification

## 1. Overview & Adapter Inventory

To integrate frozen modules M1 through M5 without modifying their internal codebases or collapsing them into a monolith, four dedicated boundary adapters were designed, implemented, and verified in `integration/adapters/`.

| Adapter | Source File | Boundary | Blockers Resolved | Test Coverage |
| :--- | :--- | :--- | :--- | :--- |
| **`M1RawEnvelopeAdapter`** | `integration/adapters/m1_raw_envelope_adapter.py` | M1 $\to$ M2 | **P0-1** (Nested vs flat fields) | `test_m1_to_m2_contract.py` (4/4 passed) |
| **`M2M3Adapter`** | `integration/adapters/m2_m3_adapter.py` | M2 $\to$ M3 | Structural schema compatibility | `test_m2_to_m3_contract.py` (2/2 passed) |
| **`M3M4Adapter`** | `integration/adapters/m3_m4_adapter.py` | M3 $\to$ M4 | **P0-2** (Root mismatch) & **P1-1** (Tenant loss) | `test_m3_to_m4_contract.py` (2/2 passed) |
| **`M4M5Adapter`** | `integration/adapters/m4_m5_adapter.py` | M4 $\to$ M5 | **P1-2** (`tenant_id` vs `id` mismatch) | `test_m4_to_m5_contract.py` (1/1 passed) |

---

## 2. P0-1 Adapter: `M1RawEnvelopeAdapter` (M1 $\to$ M2)

### 2.1 Problem Statement
M1 emits a deeply nested Pydantic model (`RawEventEnvelope`) with dictionary-nested submodels:
- `payload: {"data": str, "encoding": str, "size_bytes": int}`
- `transport: {"protocol": str, "client_ip": str, "port": int}`
- `integrity: {"algorithm": str, "hash": str}`
- `raw_storage: {"vault": str, "bucket": str, "object_key": str}`

M2's input contract (`RawEventEnvelope`) expects flattened primitive fields:
- `payload: str`
- `transport: str`
- `sha256: Optional[str]`
- `raw_reference: Optional[str]`

Directly sending M1's output to M2 triggers `Input should be a valid string [type=string_type]` validation errors on `payload` and `transport`.

### 2.2 Field Transformation Matrix

| M1 Source Field | M2 Target Field | Transformation Rule |
| :--- | :--- | :--- |
| `payload.data` | `payload` | Extracted as untouched string. |
| `payload.encoding` | `encoding` | Extracted string (default `"utf-8"`). |
| `transport.protocol` | `transport` | Extracted string (default `"syslog"`). |
| `integrity.hash` | `sha256` | **Authoritative raw digest preserved without recomputation.** |
| `raw_storage.object_key` | `raw_reference` | Preserved as object storage key URI. |
| `raw_event_id` | `raw_event_id` | Identity preserved identically. |
| `tenant_id` | `tenant_id` | Injected from trusted `TenantContext` or preserved from payload. |
| `source_id` | `source_id` | Preserved from payload or `TenantContext`. |
| `received_at` | `received_at` | Preserved ISO timestamp. |
| `metadata` | `metadata` | Preserved dictionary. |

### 2.3 Empirical Verification
```bash
integration/tests/contract/test_m1_to_m2_contract.py::test_m1_to_m2_contract_transformation PASSED
integration/tests/contract/test_m1_to_m2_contract.py::test_m1_to_m2_contract_preserves_raw_hash_authoritative PASSED
integration/tests/contract/test_m1_to_m2_contract.py::test_m1_to_m2_contract_with_tenant_context PASSED
integration/tests/contract/test_m1_to_m2_contract.py::test_m1_to_m2_contract_rejects_missing_raw_event_id PASSED
```

---

## 3. Structural Adapter: `M2M3Adapter` (M2 $\to$ M3)

### 3.1 Problem Statement
M2 emits a flat `ParsedEvent` model where cryptographic hashes and storage references are top-level keys (`sha256`, `raw_reference`). M3's `ParsedEvent` contract requires nested metadata blocks:
- `integrity.hash.algorithm: str`
- `integrity.hash.value: str`
- `raw.storage_ref: str`
- `raw.format: str`

### 3.2 Field Transformation Matrix

| M2 Source Field | M3 Target Field | Transformation Rule |
| :--- | :--- | :--- |
| `raw_event_id` | `raw_event_id` | Preserved identically. |
| `tenant_id` | `tenant_id` | Preserved from M2 or trusted `TenantContext`. |
| `source_id` | `source_id` | Preserved from M2 or trusted `TenantContext`. |
| `classification` | `classification` | Mapped to `ClassificationInfo(format, vendor, product, confidence)`. |
| `parser` | `parser` | Mapped to `ParserInfo(id, name, version, confidence)`. |
| `fields` | `fields` | Un-normalized extracted fields passed through untouched. |
| `sha256` | `integrity.hash.value` | Mapped to nested structure with `algorithm="sha256"`. |
| `sha256` | `integrity.raw_hash` | Exposed for downstream provenance. |
| `raw_reference` | `raw.storage_ref` | Storage URI mapped into M3 raw block. |

### 3.3 Empirical Verification
```bash
integration/tests/contract/test_m2_to_m3_contract.py::test_m2_to_m3_contract_transformation PASSED
integration/tests/contract/test_m2_to_m3_contract.py::test_m2_to_m3_contract_preserves_tenant PASSED
```

---

## 4. P0-2 & P1-1 Adapter: `M3M4Adapter` (M3 $\to$ M4)

### 4.1 Problem Statement
1. **P0-2 Root Encapsulation Mismatch**: M3's `NormalizationResult` encapsulates the normalized UES event inside `{"event": {"ulpf": { ... }}}`. M4's `CanonicalEvent` model enforces `model_config = ConfigDict(extra="forbid")` and requires top-level keys (`event`, `source`, `destination`, `provenance`, etc.). Submitting M3 output directly produces `extra_forbidden: Extra inputs are not permitted [type=extra_forbidden, input_value={'ulpf': ...}]`.
2. **P1-1 Tenant Metadata Loss**: M3's `builder.py` and `ULPFBlock` JSON schema completely drop `tenant_id` during normalization. Downstream M4 requires `tenant.tenant_id` via `TenantGuard`. Without adaptation, events are rejected with tenant scoping errors.

### 4.2 Transformation Logic
`M3M4Adapter` executes the following atomic operations:
1. Validates `NormalizationResult.success is True`.
2. Extracts inner canonical dictionary from `m3_result["event"]["ulpf"]`.
3. Elevates all inner semantic blocks (`event`, `observer`, `source`, `destination`, `network`, `host`, `identity`, `application`, `process`, `security`, `parser`, `normalization`, `provenance`) to root level.
4. Enforces `schema_version = "ues.v1"`.
5. **Restores Trusted Tenant Context**: Injects `tenant: {"tenant_id": tenant_context.tenant_id, "scope": {"source_id": tenant_context.source_id}}`.
6. Preserves authoritative M1 raw SHA-256 digest in `extensions.raw_integrity = {"algorithm": "sha256", "raw_hash": raw_hash, "storage_ref": storage_ref}`.
7. Wraps into an M4 `EnrichmentRequest` payload.

### 4.3 Empirical Verification
```bash
integration/tests/contract/test_m3_to_m4_contract.py::test_m3_to_m4_contract_resolves_p0_2_and_p1_1 PASSED
integration/tests/contract/test_m3_to_m4_contract.py::test_m3_to_m4_contract_rejects_missing_tenant_context PASSED
```

---

## 5. P1-2 Adapter: `M4M5Adapter` (M4 $\to$ M5)

### 5.1 Problem Statement
1. M4 returns an `EnrichmentResult` wrapper: `{"event": CanonicalEvent, "status": "SUCCESS", "provenance": [...], "diagnostics": {...}, "integrity": {...}}`. M5 expects the canonical UES event dictionary directly.
2. **P1-2 Tenant Key Mismatch**: M4 defines the canonical tenant identifier at `event["tenant"]["tenant_id"]`. M5's `SmartRouter.extract_tenant_id` specifically inspects `extract_field_value(event, "tenant.id")` or `event.get("tenant_id")`. Because M4 emits `tenant_id` rather than `id`, M5 returns `None`, silently bypassing tenant-scoped policy rules.

### 5.2 Transformation Logic
`M4M5Adapter`:
1. Unwraps `result["event"]`.
2. Harmonizes tenant identifiers:
   ```python
   tenant_id = event["tenant"]["tenant_id"]
   event["tenant"]["id"] = tenant_id          # Satisfies M5 SmartRouter
   event["tenant"]["tenant_id"] = tenant_id   # Preserves M4 canonical contract
   event["tenant_id"] = tenant_id             # Root fallback for backward compatibility
   ```
3. Preserves M4 RFC-8785 enriched digest in `event["integrity"]`.
4. Attaches enrichment provenance and diagnostics into `event["extensions"]`.

### 5.3 Empirical Verification
```bash
integration/tests/contract/test_m4_to_m5_contract.py::test_m4_to_m5_contract_resolves_p1_2 PASSED
```
SmartRouter successfully extracts `tenant_id = "tenant-cisco"` and evaluates tenant-specific routing rules deterministically.
