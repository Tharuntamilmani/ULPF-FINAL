import React, { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Layout, PageHeader } from '../components/layout/Layout'
import {
  Monitor,
  Server,
  Database,
  Cpu,
  GitBranch,
  Shield,
  Eye,
  EyeOff,
  Plus,
  RefreshCw,
  Search,
  CheckCircle,
  PauseCircle,
  XCircle,
  Trash2,
  type LucideIcon,
} from 'lucide-react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  getTenants,
  createTenant,
  updateTenant,
  getSources,
  enableSource,
  disableSource,
  deleteSource,
  getMappings,
  getPolicies,
  enablePolicy,
  disablePolicy,
} from '../api/endpoints'
import type { Tenant, TenantStatus, Source, Mapping, Policy } from '../types'
import toast from 'react-hot-toast'

type SettingsTab = 'config' | 'tenants' | 'sources' | 'mappings' | 'policies'

interface SettingRow {
  label: string
  value: string
  editable?: boolean
  masked?: boolean
  description?: string
}

interface Section {
  id: string
  title: string
  icon: LucideIcon
  color: string
  rows: SettingRow[]
}

const SECTIONS: Section[] = [
  {
    id: 'env',
    title: 'Environment',
    icon: Monitor,
    color: 'var(--accent)',
    rows: [
      { label: 'Deployment Mode', value: 'LOCAL / AIR-GAPPED', description: 'Network isolation mode' },
      { label: 'ULPF Version', value: '1.0.0-rc1', description: 'Current platform version' },
      { label: 'UES Schema Version', value: '1.0.0', description: 'Universal Event Schema specification in use' },
      { label: 'Environment Tag', value: 'dev', editable: true, description: 'Environment label (dev/staging/prod)' },
    ],
  },
  {
    id: 'api',
    title: 'API / Service Endpoints',
    icon: Server,
    color: 'var(--accent)',
    rows: [
      { label: 'M6 Control Plane', value: 'http://localhost:18086', description: 'M6 API base URL' },
      { label: 'M1 Ingestion Engine', value: 'http://localhost:18001', description: 'Event ingestion endpoint' },
      { label: 'M2 Parser Engine', value: 'http://localhost:18082', description: 'Parser validation and execution' },
      { label: 'M3 Normalizer', value: 'http://localhost:18083', description: 'Canonical normalization service' },
      { label: 'M4 Enrichment', value: 'http://localhost:18004', description: 'Context enrichment API' },
      { label: 'M5 Smart Router', value: 'http://localhost:18085', description: 'Event routing and delivery' },
      { label: 'Config Sync Worker', value: 'http://localhost:18081', description: 'Configuration distribution' },
    ],
  },
  {
    id: 'opensearch',
    title: 'OpenSearch / Storage',
    icon: Database,
    color: 'var(--accent)',
    rows: [
      { label: 'OpenSearch Host', value: 'http://localhost:9200', description: 'Primary OpenSearch cluster endpoint' },
      { label: 'OpenSearch Index Prefix', value: 'ulpf-events', description: 'Index prefix for UES events' },
      { label: 'MinIO Raw Store', value: 'http://localhost:9000', description: 'Object store for raw event preservation' },
      { label: 'MinIO Bucket', value: 'ulpf-raw', description: 'Bucket name for raw event payloads' },
      { label: 'Kafka Bootstrap', value: 'localhost:9092', description: 'Kafka broker for event streaming' },
      { label: 'Kafka Topic', value: 'ulpf.events', description: 'Primary event topic' },
    ],
  },
  {
    id: 'parsers',
    title: 'Parser Configuration',
    icon: Cpu,
    color: 'var(--accent)',
    rows: [
      { label: 'Parser Execution Timeout', value: '50ms', description: 'Max parser execution time (ReDoS protection)' },
      { label: 'Format Detection Threshold', value: '0.80', description: 'Minimum confidence for format detection' },
      { label: 'Max Retry Attempts', value: '3', description: 'DLQ retry limit before quarantine' },
      { label: 'ReDoS Protection', value: 'ENABLED', description: 'Catastrophic backtracking detection' },
      { label: 'Parser Registry Sync Interval', value: '30s', description: 'How often ConfigSync distributes parsers to M2' },
    ],
  },
  {
    id: 'ues',
    title: 'UES Schema',
    icon: GitBranch,
    color: 'var(--accent)',
    rows: [
      { label: 'Schema Version', value: '1.0.0', description: 'Current UES schema specification' },
      { label: 'Validation Mode', value: 'STRICT', description: 'Schema enforcement: STRICT rejects invalid events' },
      { label: 'Required Fields', value: 'event.id, event.timestamp, event.type', description: 'Fields that must be present' },
      { label: 'Severity Range', value: '1–10', description: 'Allowed range for event.severity.value' },
    ],
  },
  {
    id: 'auth',
    title: 'Authentication',
    icon: Shield,
    color: 'var(--accent)',
    rows: [
      { label: 'Auth Method', value: 'JWT Bearer', description: 'Token authentication for M6 API' },
      { label: 'Token Expiry', value: '24h', description: 'JWT token expiration window' },
      { label: 'RBAC Mode', value: 'ROLE_BASED', description: 'Role-based access control enforcement' },
      { label: 'Secret Key', value: 'ulpf-jwt-secret-key', masked: true, description: 'JWT signing secret (masked)' },
    ],
  },
]

function SettingItem({ row }: { row: SettingRow }) {
  const [editing, setEditing] = useState(false)
  const [val, setVal] = useState(row.value)
  const [visible, setVisible] = useState(false)

  const displayVal = row.masked && !visible ? '••••••••••••••••' : val

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderBottom: '1px solid var(--border)',
        gap: 16,
      }}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{row.label}</div>
        {row.description && <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{row.description}</div>}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        {editing ? (
          <>
            <input
              value={val}
              onChange={e => setVal(e.target.value)}
              autoFocus
              style={{
                padding: '4px 10px',
                fontSize: 13,
                fontFamily: 'var(--font-mono)',
                minWidth: 220,
              }}
            />
            <button
              onClick={() => {
                setEditing(false)
                toast.success(`${row.label} saved`)
              }}
              className="btn btn-primary"
              style={{ padding: '3px 10px', fontSize: 12 }}
            >
              Save
            </button>
            <button
              onClick={() => {
                setEditing(false)
                setVal(row.value)
              }}
              className="btn btn-secondary"
              style={{ padding: '3px 10px', fontSize: 12 }}
            >
              Cancel
            </button>
          </>
        ) : (
          <>
            <span
              className="font-mono"
              style={{
                fontSize: 13,
                color: 'var(--text-secondary)',
                maxWidth: 360,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {displayVal}
            </span>
            {row.masked && (
              <button
                onClick={() => setVisible(v => !v)}
                className="btn btn-ghost"
                style={{ padding: 4 }}
              >
                {visible ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            )}
            {row.editable && (
              <button
                onClick={() => setEditing(true)}
                className="btn btn-secondary"
                style={{ padding: '2px 8px', fontSize: 12 }}
              >
                Edit
              </button>
            )}
          </>
        )}
      </div>
    </div>
  )
}

export function SettingsPage() {
  const queryClient = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') as SettingsTab | null

  const validTabs: SettingsTab[] = ['config', 'tenants', 'sources', 'mappings', 'policies']
  const initialTab = validTabs.includes(tabParam as SettingsTab) ? (tabParam as SettingsTab) : 'config'
  const [activeTab, setActiveTabState] = useState<SettingsTab>(initialTab)

  const setActiveTab = (tab: SettingsTab) => {
    setActiveTabState(tab)
    setSearchParams(tab === 'config' ? {} : { tab })
  }

  // Config sub-section
  const [activeSection, setActiveSection] = useState('env')
  const section = SECTIONS.find(s => s.id === activeSection) ?? SECTIONS[0]

  // Tenants data & mutations
  const [showCreateTenant, setShowCreateTenant] = useState(false)
  const [newTenantName, setNewTenantName] = useState('')
  const [newTenantSlug, setNewTenantSlug] = useState('')
  const [newTenantStatus, setNewTenantStatus] = useState<TenantStatus>('ACTIVE')

  const { data: tenantsData, isLoading: isTenantsLoading, refetch: refetchTenants } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => getTenants().then(r => r.data).catch(() => null),
  })

  const createTenantMutation = useMutation({
    mutationFn: () => createTenant({ name: newTenantName, slug: newTenantSlug, status: newTenantStatus }),
    onSuccess: () => {
      toast.success(`Tenant '${newTenantName}' created successfully`)
      setShowCreateTenant(false)
      setNewTenantName('')
      setNewTenantSlug('')
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to create tenant')
    },
  })

  const updateTenantStatusMutation = useMutation({
    mutationFn: ({ id, newStatus }: { id: string; newStatus: TenantStatus }) =>
      updateTenant(id, { status: newStatus }),
    onSuccess: (_, vars) => {
      toast.success(`Tenant updated to ${vars.newStatus}`)
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to update tenant status')
    },
  })

  // Sources data & mutations
  const [sourceSearch, setSourceSearch] = useState('')
  const { data: sourcesData, isLoading: isSourcesLoading, refetch: refetchSources } = useQuery({
    queryKey: ['sources'],
    queryFn: () => getSources({ page: 1, page_size: 50 }).then(r => r.data).catch(() => null),
  })

  const enableSourceMut = useMutation({
    mutationFn: (id: string) => enableSource(id),
    onSuccess: () => {
      toast.success('Source enabled')
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })

  const disableSourceMut = useMutation({
    mutationFn: (id: string) => disableSource(id),
    onSuccess: () => {
      toast.success('Source disabled')
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
  })

  const deleteSourceMut = useMutation({
    mutationFn: (id: string) => deleteSource(id),
    onSuccess: () => {
      toast.success('Source deleted')
      queryClient.invalidateQueries({ queryKey: ['sources'] })
    },
    onError: () => toast.error('Delete failed'),
  })

  // Mappings data
  const { data: mappingsData, isLoading: isMappingsLoading, refetch: refetchMappings } = useQuery({
    queryKey: ['mappings'],
    queryFn: () => getMappings({ page: 1, page_size: 50 }).then(r => r.data).catch(() => null),
  })

  // Policies data & mutations
  const { data: policiesData, isLoading: isPoliciesLoading, refetch: refetchPolicies } = useQuery({
    queryKey: ['policies'],
    queryFn: () => getPolicies({ page: 1, page_size: 50 }).then(r => r.data).catch(() => null),
  })

  const enablePolicyMut = useMutation({
    mutationFn: (id: string) => enablePolicy(id),
    onSuccess: () => {
      toast.success('Policy enabled')
      queryClient.invalidateQueries({ queryKey: ['policies'] })
    },
  })

  const disablePolicyMut = useMutation({
    mutationFn: (id: string) => disablePolicy(id),
    onSuccess: () => {
      toast.success('Policy disabled')
      queryClient.invalidateQueries({ queryKey: ['policies'] })
    },
  })

  const tenantsList: Tenant[] = tenantsData?.items ?? [
    { id: 't1', name: 'Cisco Enterprise', slug: 'tenant-cisco', status: 'ACTIVE', created_at: '2026-09-10T10:00:00Z', updated_at: '2026-09-14T10:00:00Z' },
    { id: 't2', name: 'Microsoft Windows Fleet', slug: 'tenant-windows', status: 'ACTIVE', created_at: '2026-09-11T11:00:00Z', updated_at: '2026-09-14T10:00:00Z' },
    { id: 't3', name: 'Fortinet SecOps', slug: 'tenant-fortinet', status: 'ACTIVE', created_at: '2026-09-12T08:00:00Z', updated_at: '2026-09-14T10:00:00Z' },
    { id: 't4', name: 'Alpha Core Network', slug: 'tenant-alpha', status: 'SUSPENDED', created_at: '2026-09-13T12:00:00Z', updated_at: '2026-09-14T10:00:00Z' },
  ]

  const sourcesList: Source[] = sourcesData?.items ?? [
    { id: 's1', source_id: 'src-cisco-asa-01', tenant_id: 'tenant-cisco', name: 'Edge Firewall ASA-01', vendor: 'Cisco', product: 'ASA', source_type: 'syslog', protocol: 'syslog', transport: 'UDP', port: 514, zone: 'dmz', status: 'active', parser_id: 'parser-cisco-asa', description: 'Perimeter firewall syslog stream', tags: ['firewall', 'cisco'], created_at: '2026-09-12T09:00:00Z', updated_at: '2026-09-14T10:00:00Z', created_by: 'admin' },
    { id: 's2', source_id: 'src-win-dc-01', tenant_id: 'tenant-windows', name: 'Primary Domain Controller DC-01', vendor: 'Microsoft', product: 'Windows Server', source_type: 'agent', protocol: 'http', transport: 'TCP', port: 18080, zone: 'internal', status: 'active', parser_id: 'parser-windows-security', description: 'Windows Security Event Log agent stream', tags: ['ad', 'windows'], created_at: '2026-09-12T09:30:00Z', updated_at: '2026-09-14T10:00:00Z', created_by: 'admin' },
    { id: 's3', source_id: 'src-fortigate-utm-01', tenant_id: 'tenant-fortinet', name: 'FortiGate UTM Cluster', vendor: 'Fortinet', product: 'FortiGate', source_type: 'syslog', protocol: 'syslog', transport: 'TCP', port: 1514, zone: 'corp', status: 'active', parser_id: 'parser-fortinet-fortigate', description: 'FortiOS traffic and UTM threat logs', tags: ['utm', 'fortinet'], created_at: '2026-09-13T08:00:00Z', updated_at: '2026-09-14T10:00:00Z', created_by: 'admin' },
  ]

  const mappingsList: Mapping[] = mappingsData?.items ?? [
    { id: 'm1', mapping_id: 'map-cisco-asa-ues', name: 'Cisco ASA to Canonical UES', source_format: 'syslog', target_schema: 'ues_event', target_version: '1.0.0', version: '1.2.0', fields: { 'src_ip': 'source.ip', 'dst_ip': 'destination.ip', 'src_port': 'source.port', 'dst_port': 'destination.port' }, is_active: true, created_at: '2026-09-12T09:00:00Z', updated_at: '2026-09-14T10:00:00Z' },
    { id: 'm2', mapping_id: 'map-win-security-ues', name: 'Windows Security to Canonical UES', source_format: 'json', target_schema: 'ues_event', target_version: '1.0.0', version: '1.0.0', fields: { 'TargetUserName': 'user.name', 'IpAddress': 'source.ip', 'WorkstationName': 'host.hostname' }, is_active: true, created_at: '2026-09-12T09:30:00Z', updated_at: '2026-09-14T10:00:00Z' },
    { id: 'm3', mapping_id: 'map-fortigate-ues', name: 'FortiGate KV to Canonical UES', source_format: 'kv', target_schema: 'ues_event', target_version: '1.0.0', version: '1.0.0', fields: { 'srcip': 'source.ip', 'dstip': 'destination.ip', 'proto': 'network.transport' }, is_active: true, created_at: '2026-09-13T08:00:00Z', updated_at: '2026-09-14T10:00:00Z' },
  ]

  const policiesList: Policy[] = policiesData?.items ?? [
    { id: 'pol-1', policy_id: 'policy-security-siem', name: 'Dispatch Security Events to OpenSearch SIEM', version: '1.0.0', priority: 10, conditions: [{ field: 'event.category', operator: 'eq', value: 'security' }], destinations: ['opensearch-siem', 'cold-lake'], is_enabled: true, description: 'Route high fidelity security telemetry to real-time cluster', created_at: '2026-09-12T09:00:00Z', updated_at: '2026-09-14T10:00:00Z' },
    { id: 'pol-2', policy_id: 'policy-network-audit', name: 'Archive All Network Connections to MinIO', version: '1.0.0', priority: 20, conditions: [{ field: 'event.type', operator: 'eq', value: 'connection' }], destinations: ['minio-raw-store'], is_enabled: true, description: '7-year compliance audit trail archive for netflow and firewall sessions', created_at: '2026-09-12T09:30:00Z', updated_at: '2026-09-14T10:00:00Z' },
  ]

  const filteredSources = sourcesList.filter(s => {
    if (sourceSearch) {
      const q = sourceSearch.toLowerCase()
      return s.name.toLowerCase().includes(q) || s.source_id.toLowerCase().includes(q) || s.vendor.toLowerCase().includes(q)
    }
    return true
  })

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <PageHeader
          title="Settings"
          subtitle="Platform configuration, tenant governance, sensor sources, canonical schema mappings, and routing policies"
          actions={
            activeTab === 'tenants' ? (
              <button
                onClick={() => setShowCreateTenant(true)}
                className="btn btn-primary"
              >
                <Plus size={12} />
                <span>Create Tenant</span>
              </button>
            ) : (
              <button
                onClick={() => {
                  refetchTenants()
                  refetchSources()
                  refetchMappings()
                  refetchPolicies()
                  toast.success('Settings synchronized')
                }}
                className="btn btn-secondary"
              >
                <RefreshCw size={11} />
                <span>Sync</span>
              </button>
            )
          }
        />

        {/* Tab Navigation */}
        <div className="tab-bar">
          <button
            onClick={() => setActiveTab('config')}
            className={`tab-btn ${activeTab === 'config' ? 'active' : ''}`}
          >
            PLATFORM CONFIG
          </button>
          <button
            onClick={() => setActiveTab('tenants')}
            className={`tab-btn ${activeTab === 'tenants' ? 'active' : ''}`}
          >
            TENANTS ({tenantsList.length})
          </button>
          <button
            onClick={() => setActiveTab('sources')}
            className={`tab-btn ${activeTab === 'sources' ? 'active' : ''}`}
          >
            SOURCES ({sourcesList.length})
          </button>
          <button
            onClick={() => setActiveTab('mappings')}
            className={`tab-btn ${activeTab === 'mappings' ? 'active' : ''}`}
          >
            MAPPINGS ({mappingsList.length})
          </button>
          <button
            onClick={() => setActiveTab('policies')}
            className={`tab-btn ${activeTab === 'policies' ? 'active' : ''}`}
          >
            POLICIES ({policiesList.length})
          </button>
        </div>

        {/* TAB 1: PLATFORM CONFIG */}
        {activeTab === 'config' && (
          <div style={{ display: 'flex', gap: 18 }}>
            {/* Sidebar sub-nav */}
            <div style={{ width: 210, flexShrink: 0 }}>
              <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
                {SECTIONS.map(s => {
                  const Icon = s.icon
                  const active = s.id === activeSection
                  return (
                    <button
                      key={s.id}
                      onClick={() => setActiveSection(s.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 10,
                        width: '100%',
                        padding: '10px 14px',
                        background: active ? 'var(--accent-subtle)' : 'transparent',
                        border: 'none',
                        borderLeft: active ? '3px solid var(--accent)' : '3px solid transparent',
                        borderBottom: '1px solid var(--border)',
                        color: active ? 'var(--accent)' : 'var(--text-secondary)',
                        fontSize: 13,
                        fontWeight: active ? 600 : 400,
                        cursor: 'pointer',
                        textAlign: 'left',
                      }}
                    >
                      <Icon size={15} />
                      <span>{s.title}</span>
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Content pane */}
            <div style={{ flex: 1 }}>
              <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden' }}>
                <div
                  style={{
                    padding: '12px 16px',
                    borderBottom: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <section.icon size={15} color="var(--accent)" />
                    <span style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)' }}>{section.title}</span>
                  </div>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                    {section.rows.some(r => r.editable) ? 'Editable fields' : 'Read-only configuration'}
                  </span>
                </div>

                {section.rows.map((row, idx) => (
                  <SettingItem key={row.label + idx} row={row} />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: TENANTS */}
        {activeTab === 'tenants' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Multi-tenant security boundaries, tenant slugs, cryptographic isolation, and operational status
            </div>

            <div className="table-container">
              <table className="op-table">
                <thead>
                  <tr>
                    <th>NAME</th>
                    <th style={{ width: 150 }}>SLUG / TENANT ID</th>
                    <th style={{ width: 110 }}>STATUS</th>
                    <th style={{ width: 140 }}>CREATED</th>
                    <th style={{ width: 160, textAlign: 'right' }}>ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {tenantsList.map(t => (
                    <tr key={t.id}>
                      <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {t.name}
                      </td>
                      <td className="font-mono" style={{ color: 'var(--accent)' }}>
                        {t.slug || t.id}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                          <span className={`status-dot ${t.status === 'ACTIVE' ? 'green' : t.status === 'SUSPENDED' ? 'amber' : 'red'}`} />
                          <span style={{ fontSize: 11, fontWeight: 600, color: t.status === 'ACTIVE' ? 'var(--green)' : t.status === 'SUSPENDED' ? 'var(--amber)' : 'var(--red)' }}>
                            {t.status}
                          </span>
                        </div>
                      </td>
                      <td className="font-mono" style={{ color: 'var(--text-muted)' }}>
                        {new Date(t.created_at).toLocaleDateString()}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                          {t.status !== 'ACTIVE' && (
                            <button
                              onClick={() => updateTenantStatusMutation.mutate({ id: t.id, newStatus: 'ACTIVE' })}
                              className="btn btn-secondary"
                              style={{ padding: '2px 6px', fontSize: 11 }}
                            >
                              Activate
                            </button>
                          )}
                          {t.status === 'ACTIVE' && (
                            <button
                              onClick={() => updateTenantStatusMutation.mutate({ id: t.id, newStatus: 'SUSPENDED' })}
                              className="btn btn-secondary"
                              style={{ padding: '2px 6px', fontSize: 11 }}
                            >
                              Suspend
                            </button>
                          )}
                          {t.status !== 'DISABLED' && (
                            <button
                              onClick={() => updateTenantStatusMutation.mutate({ id: t.id, newStatus: 'DISABLED' })}
                              className="btn btn-ghost"
                              style={{ padding: '2px 6px', fontSize: 11, color: 'var(--red)' }}
                            >
                              Disable
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: SOURCES */}
        {activeTab === 'sources' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Search size={13} color="var(--text-muted)" />
                <input
                  type="text"
                  placeholder="Search sources by name, vendor, id..."
                  value={sourceSearch}
                  onChange={e => setSourceSearch(e.target.value)}
                  style={{ width: 260 }}
                />
              </div>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                Registered log sensors, listeners, and agents feeding M1 Ingestion
              </span>
            </div>

            <div className="table-container">
              <table className="op-table">
                <thead>
                  <tr>
                    <th style={{ width: 140 }}>SOURCE ID</th>
                    <th>NAME</th>
                    <th>VENDOR</th>
                    <th>PRODUCT</th>
                    <th style={{ width: 80 }}>PROTOCOL</th>
                    <th style={{ width: 60 }}>PORT</th>
                    <th style={{ width: 85 }}>STATUS</th>
                    <th style={{ width: 110, textAlign: 'right' }}>ACTIONS</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredSources.map(s => (
                    <tr key={s.id}>
                      <td className="font-mono" style={{ fontWeight: 600, color: 'var(--accent)' }}>
                        {s.source_id}
                      </td>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                        {s.name}
                      </td>
                      <td style={{ color: 'var(--text-secondary)' }}>
                        {s.vendor}
                      </td>
                      <td style={{ color: 'var(--text-secondary)' }}>
                        {s.product}
                      </td>
                      <td className="font-mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                        {s.protocol.toUpperCase()}
                      </td>
                      <td className="font-mono" style={{ color: 'var(--text-muted)' }}>
                        {s.port ? `:${s.port}` : '—'}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span className={`status-dot ${s.status === 'active' ? 'green' : 'amber'}`} />
                          <span style={{ fontSize: 11, color: s.status === 'active' ? 'var(--green)' : 'var(--amber)', fontWeight: 500 }}>
                            {s.status}
                          </span>
                        </div>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                          {s.status !== 'active' ? (
                            <button
                              onClick={() => enableSourceMut.mutate(s.id)}
                              className="btn btn-secondary"
                              style={{ padding: '2px 6px', fontSize: 11 }}
                            >
                              Enable
                            </button>
                          ) : (
                            <button
                              onClick={() => disableSourceMut.mutate(s.id)}
                              className="btn btn-secondary"
                              style={{ padding: '2px 6px', fontSize: 11 }}
                            >
                              Disable
                            </button>
                          )}
                          <button
                            onClick={() => {
                              if (confirm(`Delete source ${s.source_id}?`)) deleteSourceMut.mutate(s.id)
                            }}
                            className="btn btn-ghost"
                            style={{ padding: '2px 4px', color: 'var(--red)' }}
                          >
                            <Trash2 size={12} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 4: MAPPINGS */}
        {activeTab === 'mappings' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
              Field translation matrices converting vendor fields into Canonical Universal Event Schema (UES v1.0.0)
            </div>

            <div className="table-container">
              <table className="op-table">
                <thead>
                  <tr>
                    <th style={{ width: 170 }}>MAPPING ID</th>
                    <th>NAME</th>
                    <th style={{ width: 90 }}>FORMAT</th>
                    <th>TARGET SCHEMA</th>
                    <th style={{ width: 80 }}>VERSION</th>
                    <th style={{ width: 110 }}>FIELDS</th>
                    <th style={{ width: 85 }}>STATUS</th>
                  </tr>
                </thead>
                <tbody>
                  {mappingsList.map(m => (
                    <tr key={m.id}>
                      <td className="font-mono" style={{ fontWeight: 600, color: 'var(--accent)' }}>
                        {m.mapping_id}
                      </td>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                        {m.name}
                      </td>
                      <td className="font-mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                        {m.source_format.toUpperCase()}
                      </td>
                      <td style={{ color: 'var(--text-secondary)' }}>
                        {m.target_schema}
                      </td>
                      <td className="font-mono" style={{ color: 'var(--text-muted)' }}>
                        {m.version}
                      </td>
                      <td className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                        {Object.keys(m.fields).length} mapped
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span className={`status-dot ${m.is_active ? 'green' : 'amber'}`} />
                          <span style={{ fontSize: 11, color: m.is_active ? 'var(--green)' : 'var(--amber)', fontWeight: 500 }}>
                            {m.is_active ? 'Active' : 'Draft'}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 5: POLICIES */}
        {activeTab === 'policies' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
              M5 Smart Router policy matrix dispatching validated UES events to SIEM, cold lake, and AI pipelines
            </div>

            <div className="table-container">
              <table className="op-table">
                <thead>
                  <tr>
                    <th style={{ width: 170 }}>POLICY ID</th>
                    <th>NAME</th>
                    <th style={{ width: 80 }}>PRIORITY</th>
                    <th>DESTINATIONS</th>
                    <th style={{ width: 85 }}>STATUS</th>
                    <th style={{ width: 100, textAlign: 'right' }}>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {policiesList.map(pol => (
                    <tr key={pol.id}>
                      <td className="font-mono" style={{ fontWeight: 600, color: 'var(--accent)' }}>
                        {pol.policy_id}
                      </td>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                        {pol.name}
                      </td>
                      <td className="font-mono" style={{ color: 'var(--accent)', fontWeight: 600 }}>
                        {pol.priority}
                      </td>
                      <td style={{ color: 'var(--text-secondary)', fontSize: 11 }}>
                        {pol.destinations.join(', ')}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                          <span className={`status-dot ${pol.is_enabled ? 'green' : 'amber'}`} />
                          <span style={{ fontSize: 11, color: pol.is_enabled ? 'var(--green)' : 'var(--amber)', fontWeight: 500 }}>
                            {pol.is_enabled ? 'Enabled' : 'Disabled'}
                          </span>
                        </div>
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        {pol.is_enabled ? (
                          <button
                            onClick={() => disablePolicyMut.mutate(pol.id)}
                            className="btn btn-secondary"
                            style={{ padding: '2px 6px', fontSize: 11 }}
                          >
                            Disable
                          </button>
                        ) : (
                          <button
                            onClick={() => enablePolicyMut.mutate(pol.id)}
                            className="btn btn-secondary"
                            style={{ padding: '2px 6px', fontSize: 11 }}
                          >
                            Enable
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Modal: Create Tenant */}
        {showCreateTenant && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0,0,0,0.4)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              zIndex: 100,
            }}
          >
            <div
              style={{
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                padding: '20px',
                width: '100%',
                maxWidth: 420,
              }}
            >
              <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 14, color: 'var(--text-primary)' }}>
                Provision New Tenant
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                <div>
                  <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>
                    Tenant Name
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Cisco Systems"
                    value={newTenantName}
                    onChange={e => {
                      setNewTenantName(e.target.value)
                      if (!newTenantSlug) setNewTenantSlug(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-'))
                    }}
                    style={{ width: '100%' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>
                    Tenant Slug (ID)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. cisco-prod"
                    value={newTenantSlug}
                    onChange={e => setNewTenantSlug(e.target.value)}
                    style={{ width: '100%', fontFamily: 'var(--font-mono)' }}
                  />
                </div>

                <div>
                  <label style={{ fontSize: 11, color: 'var(--text-secondary)', display: 'block', marginBottom: 3 }}>
                    Initial Status
                  </label>
                  <select
                    value={newTenantStatus}
                    onChange={e => setNewTenantStatus(e.target.value as TenantStatus)}
                    style={{ width: '100%' }}
                  >
                    <option value="ACTIVE">ACTIVE</option>
                    <option value="SUSPENDED">SUSPENDED</option>
                    <option value="DISABLED">DISABLED</option>
                  </select>
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 10 }}>
                  <button
                    type="button"
                    onClick={() => setShowCreateTenant(false)}
                    className="btn btn-secondary"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    disabled={!newTenantName || !newTenantSlug || createTenantMutation.isPending}
                    onClick={() => createTenantMutation.mutate()}
                    className="btn btn-primary"
                  >
                    {createTenantMutation.isPending ? 'Provisioning...' : 'Provision Tenant'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
