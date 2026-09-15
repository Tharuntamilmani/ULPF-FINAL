# ULPF Phase 1 — Configuration Synchronization Specification

## 1. M6 Outbox Distribution Contradiction Resolution

During Phase 0 forensic analysis, a contradiction was identified:
- An earlier audit claimed that M6 transactional configuration distribution was implemented and operational.
- The Phase 0 forensic assessment flagged **P1-4: Configuration Synchronization Gap**, stating that configuration distribution was completely disconnected from M1–M5.

### Forensic Source Inspection
Direct code inspection of current M6 source code (`E:\ULPF\M6\M6-SIH-main\backend\app\services\config_service.py` and `backend\app\integrations\http_module_client.py`) revealed the true state:
1. **M6 Outbox Logic is Fully Implemented**:
   - M6 implements a robust transactional outbox model using `DistributionTargetState`, `ConfigurationVersion`, and `ConfigDistributionService.dispatch_targets()`.
   - The outbox records pending events inside a database transaction, invokes `HttpModuleClient.push_configuration()`, and processes ACKs asynchronously.
2. **The Disconnect was at the Receiving Boundary**:
   - `HttpModuleClient.push_configuration()` dispatches an HTTP request:
     `POST {module_base_url}/config/apply` with payload `event: dict[str, Any]`
   - It expects a strict JSON ACK response with `status == "APPLIED"` or `"SUCCESS"`.
   - **However, none of M1, M2, M3, M4, or M5 expose a `/config/apply` endpoint.** Calling them directly returned 404 Not Found or connection refused.

### The Architectural Solution
Rather than modifying the frozen modules, the integration layer implemented **`ConfigurationSyncWorker`** (`integration/config_sync/config_worker.py`), exposing the exact `/config/apply` contract expected by M6 and translating updates into each module's native configuration mechanism.

---

## 2. Configuration Domains & Module Dispatch Strategy

```
                          ┌───────────────────────────┐
                          │            M6             │
                          │ ConfigDistributionService │
                          └─────────────┬─────────────┘
                                        │
                               POST /config/apply
                                        │
                                        ▼
                      ┌───────────────────────────────────┐
                      │    ConfigurationSyncWorker        │
                      │    (Integration Subsystem)        │
                      └─────────────────┬─────────────────┘
                                        │
         ┌───────────────┬──────────────┼──────────────┬───────────────┐
         │               │              │              │               │
    (M1: Sources)   (M2: Parsers)  (M3: Mappings) (M4: Rules)    (M5: Policies)
         │               │              │              │               │
         ▼               ▼              ▼              ▼               ▼
   Atomic Manifest  POST /v1/parsers  Atomic YAML    Atomic JSON   Atomic YAML
   sources.json     /register API     mappings/      rules.json    policies/
```

### Module Configuration Handling Strategies

| Module | Configuration Domain | Mechanism Selected | Rationale & Safety |
| :--- | :--- | :--- | :--- |
| **M1** | Ingestion Sources | Controlled atomic manifest write (`m1_sources.json`) | M1 has no dynamic configuration API. Modifying live process memory or unverified file mutation is prohibited. Controlled manifest with atomic write ensures zero partial reads. |
| **M2** | Parser Definitions | M2 Authenticated Parser API (`POST /v1/parsers/register`) | M2 natively provides a secure, role-verified parser registration endpoint with validation. Config worker authenticates with system token and calls the API. |
| **M3** | UES Semantic Mappings | Atomic YAML materialization (`mappings/{id}.yaml`) | M3 loads mappings from its `mappings/` directory. Config worker validates YAML syntax, writes atomically via temporary file replacement, preventing race conditions. |
| **M4** | Enrichment Rules | Configuration lifecycle management | M4 supports versioned configurations in draft/active states. Config worker materializes verified rule sets. |
| **M5** | Delivery Policies | Atomic policy file materialization (`policies/{id}.yaml`) | M5's `PolicyLoader` parses YAML rules into `PolicyRule` objects. Config worker validates rules against schema, writes atomically, and triggers router reload. |

---

## 3. Transactional Outbox & ACK Contract

### 3.1 Outbound Payload (Sent by M6)
```json
{
  "schema_version": "1.0.0",
  "distribution_id": "d8a1c02e-9f33-4f9e-a89c-36a87b1c4021",
  "config_type": "policies",
  "entity_id": "policy_cisco_soc",
  "version": "2.1.0",
  "tenant_id": "tenant-cisco",
  "operation": "CREATE",
  "payload": {
    "policies": [
      {
        "id": "policy_cisco_soc",
        "name": "Cisco ASA SOC High Priority Route",
        "tenant_id": "tenant-cisco",
        "destinations": ["soc_high_priority"],
        "priority": 100
      }
    ]
  },
  "timestamp": "2026-09-14T10:30:00Z",
  "correlation_id": "corr-config-dist-99"
}
```

### 3.2 Inbound Compliant ACK (Returned by ConfigurationSyncWorker)
```json
{
  "distribution_id": "d8a1c02e-9f33-4f9e-a89c-36a87b1c4021",
  "config_id": "policy_cisco_soc",
  "version": "2.1.0",
  "module": "M5",
  "status": "APPLIED",
  "timestamp": "2026-09-14T10:30:00.123456Z",
  "correlation_id": "corr-config-dist-99",
  "applied_at": "2026-09-14T10:30:00.123456Z",
  "details": {
    "action": "MATERIALIZED_POLICY",
    "path": "E:/ULPF/M5/policies/policy_cisco_soc.yaml"
  }
}
```

---

## 4. Atomic File Persistence Mechanics

To guarantee that file updates never expose partially-written or corrupted configuration files to reading processes:
1. Target directory is ensured (`os.makedirs(exist_ok=True)`).
2. A temporary file is allocated in the **same directory** as the target:
   `tempfile.NamedTemporaryFile("w", dir=target_dir, delete=False)`.
3. Configuration content is serialized, written, and flushed to disk (`f.flush()`).
4. On Windows and POSIX systems, `os.replace(temp_path, target_path)` replaces the destination atomically in a single filesystem inode operation.
5. In the event of any exception during serialization or write, the temporary file is removed cleanly (`os.remove()`).

---

## 5. Empirical Verification

Configuration synchronization was verified via test `E2E-10`:
```bash
integration/tests/e2e/test_e2e_scenarios.py::test_e2e_10_configuration_update PASSED
```
The test dispatched an M6 configuration event, validated atomic persistence, verified target module assignment (`M5`), and confirmed the compliant `APPLIED` acknowledgment.
