// ── Auth ──────────────────────────────────────────────────────────────────────
export interface TokenResponse { access_token: string; token_type: string; expires_in: number }
export interface UserRole { id: string; name: string; description: string }
export interface User { id: string; username: string; email: string; is_active: boolean; is_superuser: boolean; roles: UserRole[]; created_at: string; updated_at: string }

// ── Paginated ─────────────────────────────────────────────────────────────────
export interface Paginated<T> { items: T[]; total: number; page: number; page_size: number; pages: number }

// ── Tenants ───────────────────────────────────────────────────────────────────
export type TenantStatus = 'ACTIVE' | 'SUSPENDED' | 'DISABLED'
export interface Tenant {
  id: string
  name: string
  slug: string
  status: TenantStatus
  created_at: string
  updated_at: string
}
export interface TenantCreate {
  name: string
  slug: string
  status?: TenantStatus
}
export interface TenantUpdate {
  name?: string
  status?: TenantStatus
}

// ── Sources ───────────────────────────────────────────────────────────────────
export type SourceStatus = 'active' | 'inactive' | 'disabled'
export interface Source { id: string; source_id: string; tenant_id: string; name: string; vendor: string; product: string; source_type: string; protocol: string; transport: string; port: number | null; zone: string | null; status: SourceStatus; parser_id: string | null; description: string | null; tags: string[] | null; created_at: string; updated_at: string; created_by: string | null }

// ── Parsers ───────────────────────────────────────────────────────────────────
export type ParserStatus = 'DRAFT' | 'PENDING_APPROVAL' | 'APPROVED' | 'ACTIVE' | 'DISABLED' | 'ROLLED_BACK'
export interface Parser { id: string; parser_id: string; name: string; vendor: string; product: string; format: string; version: string; status: ParserStatus; description: string | null; created_at: string; updated_at: string; created_by: string | null; approved_by: string | null }
export interface ParserVersion { id: string; parser_id: string; version: string; status: ParserStatus; changed_by: string | null; reason: string | null; created_at: string }

// ── Schemas ───────────────────────────────────────────────────────────────────
export interface SchemaVersion { id: string; schema_id: string; version: string; status: string; json_schema: object; changelog: string | null; created_at: string }
export interface Schema { id: string; name: string; description: string | null; versions: SchemaVersion[]; created_at: string; updated_at: string }

// ── Mappings ──────────────────────────────────────────────────────────────────
export interface Mapping { id: string; mapping_id: string; name: string; source_format: string; target_schema: string; target_version: string; version: string; fields: Record<string, string>; is_active: boolean; created_at: string; updated_at: string }

// ── Policies ──────────────────────────────────────────────────────────────────
export interface PolicyCondition { field: string; operator: string; value: unknown }
export interface Policy { id: string; policy_id: string; name: string; version: string; priority: number; conditions: PolicyCondition[]; destinations: string[]; is_enabled: boolean; description: string | null; created_at: string; updated_at: string }

// ── Services / Health ─────────────────────────────────────────────────────────
export type HealthStatus = 'HEALTHY' | 'DEGRADED' | 'UNHEALTHY' | 'UNAVAILABLE' | 'UNKNOWN'
export interface ServiceHealth { service: string; status: HealthStatus; latency_ms: number | null; checked_at: string; details: Record<string, unknown>; is_mock: boolean }
export interface AllServicesHealth { overall: string; services: Record<string, ServiceHealth>; m6_control_plane: string }

export interface ModuleHealthStatus {
  module: string
  healthy: boolean
  status_code: number | null
  latency_ms: number
  details: Record<string, unknown>
  error: string | null
}
export interface SystemHealthReport {
  status: 'HEALTHY' | 'DEGRADED' | 'UNAVAILABLE'
  modules: Record<string, ModuleHealthStatus>
  timestamp: string
}

// ── Audit ─────────────────────────────────────────────────────────────────────
export interface AuditLog { id: string; timestamp: string; actor: string; actor_role: string | null; action: string; resource_type: string; resource_id: string | null; version: string | null; result: string; reason: string | null; request_id: string | null }

// ── Replay ────────────────────────────────────────────────────────────────────
export type ReplayStatus = 'REQUESTED' | 'QUEUED' | 'PROCESSING' | 'SUCCESS' | 'FAILED'
export interface ReplayOperation { id: string; event_id: string; source: string | null; reason: string | null; requested_by: string; requested_at: string; status: ReplayStatus; error_message: string | null; completed_at: string | null; created_at: string }

// ── Configuration ─────────────────────────────────────────────────────────────
export interface ConfigSnapshot { sources: unknown[] | null; parsers: unknown[] | null; schemas: unknown | null; mappings: unknown[] | null; policies: unknown[] | null; version: string | null; updated_at: string | null; error?: string }

// ── Events Explorer ───────────────────────────────────────────────────────────
export interface UESEvent {
  event?: {
    id?: string
    timestamp?: string
    type?: string
    action?: string
    severity?: {
      value?: number
      label?: string
    }
  }
  tenant?: {
    id?: string
  }
  source?: {
    ip?: string
    port?: number
  }
  destination?: {
    ip?: string
    port?: number
  }
  network?: {
    transport?: string
  }
  raw?: {
    id?: string
    storage_ref?: string
    sha256?: string
  }
  [key: string]: unknown
}

export interface EventsQueryResponse {
  total: number
  count: number
  limit: number
  offset: number
  tenant_id: string
  events: UESEvent[]
}
