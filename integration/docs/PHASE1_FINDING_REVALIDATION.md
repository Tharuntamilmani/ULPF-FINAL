# ULPF Phase 1 — Finding Revalidation Report

**Audit Date**: September 14, 2026  
**Auditor**: Antigravity Autonomous Systems Engineering & Forensic Integration Team  
**Methodology**: Direct code inspection and live Python AST/model reproduction against active repositories with zero source modifications.

---

## 1. Executive Revalidation Summary

Before initiating the integration layer design and implementation, each P0 and P1 finding identified in Phase 0 was subjected to empirical revalidation against the current repository source code.

All findings were successfully reproduced, and the perceived contradiction regarding M6's configuration distribution has been definitively resolved.

| Finding ID | Domain | Phase 0 Classification | Revalidation Result | Empirical Confirmation |
| :--- | :--- | :--- | :--- | :--- |
| **P0-1** | M1 $\to$ M2 Contract | Serialization Mismatch | **CONFIRMED (P0)** | M1 nested dicts for `payload` & `transport` fail M2 string validation with 2 errors. |
| **P0-2** | M3 $\to$ M4 Contract | Root Encapsulation Mismatch | **CONFIRMED (P0)** | M3 `{"ulpf": ...}` fails M4 `CanonicalEvent` with 3 validation errors (`extra_forbidden`). |
| **P0-3** | M1 $\to$ M2 Transport | Kafka $\to$ HTTP Chasm | **CONFIRMED (P0)** | M1 publishes to `ulpf.raw`; M2 has zero Kafka consumer dependencies or loop. |
| **P1-1** | M3 Semantic Layer | Tenant Metadata Stripped | **CONFIRMED (P1)** | M3 `UESBuilder` parses `tenant_id` via `extra="allow"`, but drops it from `ULPFBlock`. |
| **P1-2** | M4 $\to$ M5 Contract | Tenant Key Mismatch | **CONFIRMED (P1)** | M4 emits `tenant.tenant_id`; M5 router checks `tenant.id` / `tenant_id`, extracting `None`. |
| **P1-3** | M1 Ingress Security | Shared Token Spoofing | **CONFIRMED (P1)** | M1 trusts `X-Tenant-ID` under a single shared `settings.api_auth_token`. |
| **P1-4** | M6 Control Plane | Config Distribution Loop | **RESOLVED & CONFIRMED** | M6 implements transactional outbox, but expects `POST /config/apply` on target modules. |

---

## 2. Empirical Reproductions & Technical Evidence

### 2.1 P0-1: M1 $\to$ M2 Serialization Incompatibility
- **Code Locations**:
  - M1: `M1/modules/m1-ingestion/app/envelope/models.py` (`RawEventEnvelope`)
  - M2: `M2/abcd-main/app/models/envelope.py` (`RawEventEnvelope`)
- **Live Reproduction Command**:
  ```python
  from m1_models import RawEventEnvelope as M1Envelope, PayloadInfo, TransportInfo
  from m2_models import RawEventEnvelope as M2Envelope

  m1_data = M1Envelope(
      schema_version="1.0.0",
      raw_event_id="0191eb54-3e91-723a-8b5e-17cf3b2a8190",
      tenant_id="tenant-alpha",
      source_id="cisco-fw-01",
      received_at="2026-09-14T10:00:00Z",
      transport=TransportInfo(protocol="udp", port=514),
      payload=PayloadInfo(encoding="utf-8", format_hint="syslog", data="<134>test log"),
      integrity={"algorithm": "SHA-256", "hash": "e3b0c44..."},
      raw_storage={"backend": "minio", "bucket": "ulpf-raw", "object_key": "..."}
  ).model_dump()

  M2Envelope.model_validate(m1_data)
  ```
- **Observed Result**:
  ```
  pydantic_core._pydantic_core.ValidationError: 2 validation errors for RawEventEnvelope
  transport
    Input should be a valid string [type=string_type, input_value={'protocol': 'udp', 'port': 514}]
  payload
    Input should be a valid string [type=string_type, input_value={'encoding': 'utf-8', 'format_hint': 'syslog', 'data': '<134>test log'}]
  ```
- **Finding**: Absolute functional blocker. Without an adapter transforming `payload.data` $\to$ `payload` and `transport.protocol` $\to$ `transport`, M2 rejects 100% of M1 messages.

---

### 2.2 P0-2: M3 $\to$ M4 Root Encapsulation & Validation Failure
- **Code Locations**:
  - M3: `M3/schema/ues/v1.0.0/ues.schema.json` & `M3/app/normalizer/builder.py`
  - M4: `M4/app/contracts/canonical_event.py` (`CanonicalEvent`)
- **Live Reproduction Command**:
  ```python
  from m4_canon import CanonicalEvent

  m3_output = {
      "ulpf": {
          "schema": {"version": "1.0.0", "specification": "UES"},
          "event": {"id": "evt_001", "timestamp": "2026-09-14T10:00:00Z", "kind": "event", "type": "network"},
          "source": {"ip": "192.168.1.1", "port": 51542},
          "provenance": {"raw_event_id": "0191eb54-3e91-723a-8b5e-17cf3b2a8190"}
      }
  }

  CanonicalEvent.model_validate(m3_output)
  ```
- **Observed Result**:
  ```
  pydantic_core._pydantic_core.ValidationError: 3 validation errors for CanonicalEvent
  event
    Field required [type=missing]
  provenance
    Field required [type=missing]
  ulpf
    Extra inputs are not permitted [type=extra_forbidden]
  ```
- **Finding**: Absolute functional blocker. M3 encapsulates canonical fields inside an outer `"ulpf"` key, whereas M4's model enforces `extra="forbid"` and requires top-level keys.

---

### 2.3 P0-3: M1 Kafka $\to$ M2 HTTP Transport Chasm
- **Code Locations**:
  - M1: `M1/modules/m1-ingestion/app/transports/pipeline.py` (Publishes to `ulpf.raw`)
  - M2: `M2/abcd-main/requirements.txt` & `app/main.py`
- **Inspection Result**:
  - Ripgrep search across M2 for `KafkaConsumer`, `AIOKafkaConsumer`, or Kafka subscription logic yields **zero results**.
  - `M2/abcd-main/requirements.txt` contains no Kafka libraries.
  - M2 operates exclusively as an HTTP server exposing `POST /v1/parse`.
- **Finding**: Events emitted by M1 to Kafka topic `ulpf.raw` remain unconsumed unless an integration consumer daemon bridges Kafka $\to$ M2.

---

### 2.4 P1-1: Tenant Metadata Lost in M3 Normalization
- **Code Locations**:
  - `M3/app/models/parsed_event.py`
  - `M3/app/normalizer/builder.py:563-584`
- **Live Reproduction Command**:
  ```python
  from app.models.parsed_event import ParsedEvent, ParserInfo, ClassificationInfo
  from app.normalizer.builder import UESBuilder
  from app.mapping.resolver import MappingResolver

  resolver = MappingResolver(Path("mappings"))
  builder = UESBuilder(resolver)

  parsed = ParsedEvent(
      raw_event_id="0191eb54-3e91-723a-8b5e-17cf3b2a8190",
      tenant_id="tenant-alpha",
      source_id="cisco-fw-01",
      parser=ParserInfo(id="parser-cisco-asa", name="Cisco ASA", version="1.2.0", confidence=1.0),
      classification=ClassificationInfo(format="syslog", vendor="Cisco", product="ASA", confidence=0.99),
      fields={"timestamp": datetime.now(timezone.utc).isoformat(), "srcip": "192.168.1.1", "dstip": "8.8.8.8", "action": "allow", "protocol": "TCP", "connection_id": 892341}
  )

  result = builder.build(parsed)
  print("Is tenant in ulpf?", "tenant" in result.event["ulpf"])
  ```
- **Observed Result**:
  ```
  Success: True
  Keys in result.event.ulpf: ['schema', 'event', 'observer', 'source', 'destination', 'network', 'parser', 'normalization', 'provenance', 'vendor']
  Is tenant in ulpf? False
  ```
- **Finding**: M3 discards `tenant_id`. The integration layer must retain the original authenticated tenant context and re-attach it to the canonical event.

---

### 2.5 P1-2: M4 $\to$ M5 Tenant Key Mismatch
- **Code Locations**:
  - M4: `M4/app/contracts/canonical_event.py:182` (`TenantMetadata.tenant_id`)
  - M5: `M5/app/router/router.py:41-44` (`SmartRouter.extract_tenant_id`)
- **Live Reproduction Command**:
  ```python
  from app.router.router import SmartRouter

  router = SmartRouter()
  m4_event = {
      "event": {"id": "evt_001"},
      "tenant": {"tenant_id": "tenant-alpha"}
  }

  print("Tenant extracted by M5:", router.extract_tenant_id(m4_event))
  ```
- **Observed Result**:
  ```
  Tenant extracted by M5: None
  ```
- **Finding**: M5 only checks `event["tenant"]["id"]` or root `event["tenant_id"]`. It fails to read `event["tenant"]["tenant_id"]`. The integration layer must duplicate `tenant_id` to `tenant.id` and root `tenant_id`.

---

### 2.6 P1-3: M1 Ingress Tenant Header Spoofing
- **Code Reference**: `M1/modules/m1-ingestion/app/transports/http.py:52`
  ```python
  tenant_id = request.headers.get("X-Tenant-ID", settings.default_tenant_id)
  ```
- **Finding**: Authentication relies on a static secret (`settings.api_auth_token`). Any client with this token can specify an arbitrary `X-Tenant-ID: victim-tenant`. An integration ingress gateway is required to authenticate client identities and enforce authorized tenant scopes before hitting M1.

---

### 2.7 P1-4: Resolution of the M6 Configuration Contradiction
- **The Apparent Contradiction**:
  - Phase 0 Report: *"Configuration distribution is disconnected; updates are only committed to PostgreSQL."*
  - Prior Audit Record: *"Transactional distribution outbox is implemented with ACK validation."*
- **Forensic Source Inspection**:
  - `M6/backend/app/services/config_service.py` implements:
    1. `create_outbox_event()`: Atomically commits `ConfigurationVersion` and `DistributionTargetState` (PENDING) in PostgreSQL.
    2. `dispatch_targets()`: Calls `HttpModuleClient.push_configuration()` for target modules.
    3. `process_ack()`: Processes and validates `ModuleAckRequest` against `config_ack.schema.json`.
  - **However**, `HttpModuleClient.push_configuration()` (`http_module_client.py:138`) executes:
    ```python
    url = f"{self._base_url}/config/apply"
    resp = await client.post(url, json=event)
    ```
    M6 expects downstream modules to expose `POST /config/apply` and return a structured ACK!
  - In reality:
    - **M1**: Has no `/config/apply`.
    - **M2**: Has `POST /v1/parsers`.
    - **M3**: Has no `/config/apply`.
    - **M4**: Has `POST /v1/config/reload`.
    - **M5**: Has no `/config/apply`.
- **Conclusion**: M6's transactional distribution engine **is fully implemented**, but downstream modules do not implement the expected `POST /config/apply` contract.
- **Architectural Solution**: The integration layer configuration worker will serve as the `/config/apply` target or subscribe to M6's distribution stream, translating and routing configuration updates to M1, M2, M3, M4, and M5, and returning valid ACKs back to M6's `POST /api/v1/configuration/ack`.

---

## 3. Approval to Proceed to Implementation

With all findings empirically revalidated and the M6 configuration model clarified, Phase 1 integration design and implementation may now proceed.
