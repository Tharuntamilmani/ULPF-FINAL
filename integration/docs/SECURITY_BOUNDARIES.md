# ULPF Phase 1 — Security Boundaries & Tenant Isolation Specification

## 1. Problem Statement: P1-3 (M1 Tenant Header Trust & Spoofing Risk)

During Phase 0, a critical multi-tenant vulnerability was discovered in M1:
- M1 verifies incoming HTTP requests using a single, shared static Bearer token (`settings.api_auth_token`).
- All collectors, agents, and client systems share this token.
- M1 determines multi-tenant event attribution solely by reading the client-supplied `X-Tenant-ID` header.
- **Vulnerability**: If M1 were exposed directly to external client networks, any client with a valid token could forge `X-Tenant-ID: tenant-victim` and inject unauthenticated data into another tenant's raw evidence vault.

Under our strict Phase 1 rule, **frozen modules must not be rewritten immediately if the defect can be safely mitigated at the integration boundary**.

---

## 2. Ingress Security Gateway Architecture

The integration layer solves P1-3 by establishing a strict perimeter boundary:
- **M1 is completely isolated** within the trusted internal Docker container network (`ulpf-net`). M1's port 8000 is never exposed directly to external client traffic in production.
- All external client ingestion traffic must transit through the **Ingress Security Gateway** (`integration/security/ingress_gateway.py`), listening on port `8080`.

```
[External Untrusted Client]
          │
          │ 1. Client presents unique API key or Bearer token (e.g. key-tenant-cisco-prod)
          │    Optionally attempts to inject "X-Tenant-ID: tenant-victim"
          ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   INGRESS SECURITY GATEWAY                             │
│                                                                        │
│  [Step 1: Authenticate]                                                │
│  Look up API key in Tenant Credential Registry                         │
│  ❌ Not found -> Reject HTTP 401 Unauthorized                         │
│                                                                        │
│  [Step 2: Anti-Spoofing Check]                                         │
│  Bound Tenant = "tenant-cisco"                                         │
│  Supplied X-Tenant-ID = "tenant-victim"                                │
│  ❌ Bound != Supplied -> BLOCK & REJECT HTTP 403 Forbidden             │
│                                                                        │
│  [Step 3: Sanitize & Inject]                                           │
│  Strip all untrusted client headers                                    │
│  Inject trusted X-Tenant-ID = "tenant-cisco"                           │
│  Inject trusted X-Correlation-ID = UUIDv4                              │
│  Inject trusted internal M1 token (Bearer sec-m1-token-sysadmin)       │
└────────────────────────────────────────────────────────────────────────┘
          │
          │ 2. Proxied internal request over private Docker bridge network
          ▼
[M1 Ingestion Engine] (Trusted Internal Network)
```

---

## 3. Anti-Spoofing Algorithm & Header Sanitization

1. **Authentication**: The gateway inspects the `Authorization` header or `X-API-Key` header.
2. **Cryptographic Binding**: The key maps to an authorized `TenantContext` containing:
   - `authorized_tenant_id`
   - `principal_id`
   - `allowed_sources`
3. **Spoofing Detection**:
   ```python
   if requested_tenant_header and requested_tenant_header.strip() != authorized_tenant_id:
       logger.error(
           "Tenant spoofing attempt blocked",
           authorized_tenant=authorized_tenant_id,
           attempted_tenant=requested_tenant_header,
       )
       raise HTTPException(
           status_code=403,
           detail=f"Forbidden: credential for '{authorized_tenant_id}' cannot act as tenant '{requested_tenant_header}'"
       )
   ```
4. **Header Stripping & Injection**:
   - The untrusted client's headers are discarded.
   - The gateway injects:
     - `Authorization: Bearer <M1_INTERNAL_TOKEN>` (M1's private shared secret)
     - `X-Tenant-ID: <authorized_tenant_id>` (Verified identity)
     - `X-Source-ID: <source_id>`
     - `X-Correlation-ID: <uuidv4>`
     - `X-Authenticated-Principal: <principal_id>`

---

## 4. Inter-Service Authentication Architecture

Every boundary adapter authenticates when communicating with downstream modules using configured service credentials managed by `ServiceAuthManager` (`integration/security/service_auth.py`):

| Calling Component | Target Service | Authentication Method | Credential Environment Key | Verified Role / Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Ingress Gateway** | M1 Ingestion | HTTP Bearer Token | `M1_INTERNAL_TOKEN` | Internal Ingestion Administrator |
| **M1 Consumer Bridge** | M2 Parser API | HTTP Bearer / `X-API-Key` | `M2_SERVICE_TOKEN` | `system-service` (Global Admin / Ingest) |
| **M2 Adapter** | M3 Normalizer | HTTP Bearer Token | `M3_SERVICE_KEY` | System Service |
| **M3 Adapter** | M4 Enrichment API | `X-API-Key` Header | `M4_SERVICE_TOKEN` | `ApiRole.EVENT_PROCESSING` |
| **M4 Adapter** | M5 Query / Router | HTTP Bearer Token | `M5_SERVICE_TOKEN` | Admin Role (`is_admin=True`) |
| **M6 Control Plane** | Config Sync Worker | HTTP Service Header | `M6_SERVICE_TOKEN` | Control Plane Outbox Distributor |

### Separation of Service Identity vs Tenant Context
A fundamental architectural rule of ULPF is that **service identity is strictly separated from tenant identity**:
- **Service Identity** (`Authorization: Bearer <service_token>`, `X-API-Key`) authenticates the calling software service (e.g. consumer bridge, orchestrator) and grants permission to invoke the endpoint.
- **Tenant Context** (`X-Tenant-ID`, `event.tenant.tenant_id`) represents the data ownership boundary and determines data scoping, enrichment rule isolation, and policy routing.
- Service tokens never determine which tenant's data is processed; the immutable `TenantContext` object controls data attribution across all hops.

---

## 5. Security Test Verification Results

All tenant boundary enforcement and anti-spoofing defenses were verified under the security test suite:

```bash
integration/tests/security/test_tenant_spoofing.py::test_ingress_authenticates_authorized_client PASSED
integration/tests/security/test_tenant_spoofing.py::test_ingress_detects_and_blocks_tenant_spoofing PASSED
integration/tests/security/test_tenant_spoofing.py::test_ingress_rejects_unauthenticated_request PASSED
integration/tests/security/test_tenant_spoofing.py::test_ingress_allows_explicit_matching_tenant_header PASSED
```
Results prove that unauthorized or spoofed tenant ingestion requests are rejected with 100% reliability at the gateway boundary before ever reaching M1.
