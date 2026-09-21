# ULPF — API Reference

> M6 Control Plane REST API (FastAPI)
>
> **Base URL**: `http://127.0.0.1:18086`
> **Interactive Docs**: [Swagger UI](http://127.0.0.1:18086/docs) · [ReDoc](http://127.0.0.1:18086/redoc) · [OpenAPI JSON](http://127.0.0.1:18086/openapi.json)

---

## Authentication

All endpoints under `/api/v1/` (except `/api/v1/auth/login`) require a JWT Bearer token.

### Login

```
POST /api/v1/auth/login
Content-Type: application/x-www-form-urlencoded

username=admin&password=Admin_Secure_Pass_2026!
```

**Response (200)**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Using the Token

Include the token in the `Authorization` header:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Refresh Token

```
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

## Health & Metrics

| Method | Endpoint | Auth | Description |
|:-------|:---------|:----:|:------------|
| `GET` | `/health` | ❌ | Service health status |
| `GET` | `/metrics` | ❌ | Prometheus metrics (text/plain) |

### GET /health

**Response (200)**:
```json
{
  "status": "healthy",
  "service": "m6-control-plane",
  "version": "1.0.0",
  "timestamp": "2026-09-21T12:00:00Z"
}
```

---

## Tenants

| Method | Endpoint | Auth | Role | Description |
|:-------|:---------|:----:|:----:|:------------|
| `GET` | `/api/v1/tenants` | ✅ | Any | List all tenants |
| `POST` | `/api/v1/tenants` | ✅ | Admin | Create tenant |
| `GET` | `/api/v1/tenants/{id}` | ✅ | Any | Get tenant by ID |
| `PUT` | `/api/v1/tenants/{id}` | ✅ | Admin | Update tenant |
| `DELETE` | `/api/v1/tenants/{id}` | ✅ | Admin | Delete tenant |

### POST /api/v1/tenants

**Request**:
```json
{
  "name": "Antarctic Expedition 2026",
  "slug": "antarctic-exp-2026",
  "metadata": {
    "station": "Maitri",
    "expedition_number": "44"
  }
}
```

**Response (201)**:
```json
{
  "id": "a1b2c3d4-...",
  "name": "Antarctic Expedition 2026",
  "slug": "antarctic-exp-2026",
  "status": "ACTIVE",
  "metadata": { "station": "Maitri", "expedition_number": "44" },
  "created_at": "2026-09-21T12:00:00Z"
}
```

---

## Sources

| Method | Endpoint | Auth | Role | Description |
|:-------|:---------|:----:|:----:|:------------|
| `GET` | `/api/v1/sources` | ✅ | Any | List sources |
| `POST` | `/api/v1/sources` | ✅ | Admin | Register source |
| `GET` | `/api/v1/sources/{id}` | ✅ | Any | Get source |
| `PUT` | `/api/v1/sources/{id}` | ✅ | Admin | Update source |
| `DELETE` | `/api/v1/sources/{id}` | ✅ | Admin | Delete source |

### POST /api/v1/sources

**Request**:
```json
{
  "name": "Maitri Firewall",
  "source_type": "firewall",
  "tenant_id": "a1b2c3d4-...",
  "metadata": {
    "vendor": "Cisco",
    "model": "ASA 5525-X",
    "location": "Maitri Station, Antarctica"
  }
}
```

---

## Parsers

| Method | Endpoint | Auth | Role | Description |
|:-------|:---------|:----:|:----:|:------------|
| `GET` | `/api/v1/parsers` | ✅ | Any | List parsers |
| `POST` | `/api/v1/parsers` | ✅ | Admin/Dev | Create parser |
| `GET` | `/api/v1/parsers/{id}` | ✅ | Any | Get parser |
| `PUT` | `/api/v1/parsers/{id}` | ✅ | Admin/Dev | Update parser |
| `DELETE` | `/api/v1/parsers/{id}` | ✅ | Admin | Delete parser |
| `POST` | `/api/v1/parsers/{id}/test` | ✅ | Any | Test parser |
| `GET` | `/api/v1/parsers/{id}/versions` | ✅ | Any | List parser versions |

### POST /api/v1/parsers

**Request**:
```json
{
  "name": "Cisco ASA Deny Parser",
  "format_type": "cisco_asa",
  "tenant_id": "a1b2c3d4-...",
  "regex_pattern": "^%ASA-\\d-(?P<message_id>\\d+): (?P<action>\\w+) (?P<protocol>\\w+) src (?P<src_interface>\\w+):(?P<src_ip>[\\d.]+)/(?P<src_port>\\d+).*",
  "description": "Parses Cisco ASA deny messages"
}
```

### POST /api/v1/parsers/{id}/test

**Request**:
```json
{
  "sample_log": "%ASA-4-106023: Deny tcp src outside:192.168.1.100/12345 dst inside:10.0.0.5/443"
}
```

**Response (200)**:
```json
{
  "matched": true,
  "fields": {
    "message_id": "106023",
    "action": "Deny",
    "protocol": "tcp",
    "src_interface": "outside",
    "src_ip": "192.168.1.100",
    "src_port": "12345"
  }
}
```

---

## Schemas

| Method | Endpoint | Auth | Role | Description |
|:-------|:---------|:----:|:----:|:------------|
| `GET` | `/api/v1/schemas` | ✅ | Any | List UES schemas |
| `POST` | `/api/v1/schemas` | ✅ | Admin/Dev | Create schema |
| `GET` | `/api/v1/schemas/{id}` | ✅ | Any | Get schema |
| `PUT` | `/api/v1/schemas/{id}` | ✅ | Admin/Dev | Update schema |
| `DELETE` | `/api/v1/schemas/{id}` | ✅ | Admin | Delete schema |

---

## Mappings

| Method | Endpoint | Auth | Role | Description |
|:-------|:---------|:----:|:----:|:------------|
| `GET` | `/api/v1/mappings` | ✅ | Any | List field mappings |
| `POST` | `/api/v1/mappings` | ✅ | Admin/Dev | Create mapping |
| `GET` | `/api/v1/mappings/{id}` | ✅ | Any | Get mapping |
| `PUT` | `/api/v1/mappings/{id}` | ✅ | Admin/Dev | Update mapping |
| `DELETE` | `/api/v1/mappings/{id}` | ✅ | Admin | Delete mapping |

---

## Policies

| Method | Endpoint | Auth | Role | Description |
|:-------|:---------|:----:|:----:|:------------|
| `GET` | `/api/v1/policies` | ✅ | Any | List routing policies |
| `POST` | `/api/v1/policies` | ✅ | Admin | Create policy |
| `GET` | `/api/v1/policies/{id}` | ✅ | Any | Get policy |
| `PUT` | `/api/v1/policies/{id}` | ✅ | Admin | Update policy |
| `DELETE` | `/api/v1/policies/{id}` | ✅ | Admin | Delete policy |

---

## Services

| Method | Endpoint | Auth | Role | Description |
|:-------|:---------|:----:|:----:|:------------|
| `GET` | `/api/v1/services` | ✅ | Any | List registered pipeline services with health |

### GET /api/v1/services

**Response (200)**:
```json
[
  {
    "id": "...",
    "name": "M1_Ingestion_Vault",
    "url": "http://127.0.0.1:18001",
    "status": "HEALTHY",
    "last_checked_at": "2026-09-21T12:00:00Z"
  },
  {
    "id": "...",
    "name": "M2_Parser_Engine",
    "url": "http://127.0.0.1:18082",
    "status": "HEALTHY",
    "last_checked_at": "2026-09-21T12:00:00Z"
  }
]
```

---

## Audit

| Method | Endpoint | Auth | Role | Description |
|:-------|:---------|:----:|:----:|:------------|
| `GET` | `/api/v1/audit` | ✅ | Admin/Analyst | Query audit log |

### GET /api/v1/audit

**Query Parameters**: `?action=CREATE&entity_type=parser&limit=50&offset=0`

**Response (200)**:
```json
{
  "items": [
    {
      "id": "...",
      "action": "CREATE",
      "entity_type": "parser",
      "entity_id": "...",
      "user_id": "...",
      "changes": { "name": "Cisco ASA Parser" },
      "result": "SUCCESS",
      "created_at": "2026-09-21T12:00:00Z"
    }
  ],
  "total": 1
}
```

---

## Replay

| Method | Endpoint | Auth | Role | Description |
|:-------|:---------|:----:|:----:|:------------|
| `POST` | `/api/v1/replay` | ✅ | Admin | Trigger event replay |
| `GET` | `/api/v1/replay` | ✅ | Any | List replay operations |
| `GET` | `/api/v1/replay/{id}` | ✅ | Any | Get replay status |

---

## Configuration

| Method | Endpoint | Auth | Role | Description |
|:-------|:---------|:----:|:----:|:------------|
| `POST` | `/api/v1/configuration/deploy` | ✅ | Admin | Deploy config to M1-M5 |
| `GET` | `/api/v1/configuration/versions` | ✅ | Any | List config versions |
| `GET` | `/api/v1/configuration/versions/{id}` | ✅ | Any | Get config version details |

---

## Kafka

| Method | Endpoint | Auth | Role | Description |
|:-------|:---------|:----:|:----:|:------------|
| `GET` | `/api/v1/kafka/topics` | ✅ | Admin | List Kafka topics |

---

## Error Responses

All errors follow a consistent structure:

```json
{
  "detail": "Error description",
  "error_code": "ENTITY_NOT_FOUND",
  "status_code": 404
}
```

### HTTP Status Codes

| Code | Meaning |
|:-----|:--------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient role) |
| 404 | Entity not found |
| 409 | Conflict (duplicate entity) |
| 422 | Validation error (Pydantic) |
| 500 | Internal server error |
| 503 | Service unavailable |

---

## Other Module APIs

### M1 Ingestion (Port 18001)

| Method | Endpoint | Auth | Description |
|:-------|:---------|:----:|:------------|
| `GET` | `/health` | ❌ | Health check |
| `GET` | `/ready` | ❌ | Readiness (Kafka + MinIO) |
| `POST` | `/v1/events` | Token | Ingest raw event |

### M2 Parser (Port 18082)

| Method | Endpoint | Auth | Description |
|:-------|:---------|:----:|:------------|
| `GET` | `/health` | ❌ | Health check |
| `POST` | `/v1/parse` | ❌ | Parse a raw log line |
| `GET` | `/v1/parsers` | ❌ | List parsers |

### M3 Normalizer (Port 18083)

| Method | Endpoint | Auth | Description |
|:-------|:---------|:----:|:------------|
| `GET` | `/health` | ❌ | Health check |
| `POST` | `/v1/normalize` | ❌ | Normalize parsed event to UES |

### M4 Enrichment (Port 18004)

| Method | Endpoint | Auth | Description |
|:-------|:---------|:----:|:------------|
| `GET` | `/health` | ❌ | Health check |
| `POST` | `/v1/enrich` | ❌ | Enrich normalized event |

### M5 Smart Router (Port 18085)

| Method | Endpoint | Auth | Description |
|:-------|:---------|:----:|:------------|
| `GET` | `/health` | ❌ | Health check |
| `POST` | `/v1/route` | ❌ | Route enriched event |
| `GET` | `/v1/dlq` | ❌ | List DLQ entries |

### Gateway (Port 18080)

| Method | Endpoint | Auth | Description |
|:-------|:---------|:----:|:------------|
| `GET` | `/health` | ❌ | Health check |
| `POST` | `/v1/ingest` | API Key | Ingest event (tenant-validated) |

### Health Aggregator (Port 18090)

| Method | Endpoint | Auth | Description |
|:-------|:---------|:----:|:------------|
| `GET` | `/live` | ❌ | Liveness check |
| `GET` | `/health` | ❌ | Aggregated health of all services |
