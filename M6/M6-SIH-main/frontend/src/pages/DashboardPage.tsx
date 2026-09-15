import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layout, PageHeader } from '../components/layout/Layout'
import { StatCard, Card } from '../components/ui/Card'
import { StatusBadge } from '../components/ui/StatusBadge'
import {
  getAllServicesHealth,
  getSystemHealthReport,
  getSources,
  getParsers,
  getPolicies,
  getConfiguration,
  getTenants,
  getLiveEvents,
} from '../api/endpoints'

export function DashboardPage() {
  const { data: health } = useQuery({
    queryKey: ['services-health'],
    queryFn: () => getAllServicesHealth().then(r => r.data),
    refetchInterval: 10000,
  })

  const { data: systemHealth } = useQuery({
    queryKey: ['system-health-telemetry'],
    queryFn: () => getSystemHealthReport().then(r => r.data),
    refetchInterval: 5000,
  })

  const { data: tenants } = useQuery({
    queryKey: ['tenants-count'],
    queryFn: () => getTenants({ page_size: 1 }).then(r => r.data),
  })

  const { data: sources } = useQuery({
    queryKey: ['sources'],
    queryFn: () => getSources({ page_size: 1 }).then(r => r.data),
  })

  const { data: parsers } = useQuery({
    queryKey: ['parsers'],
    queryFn: () => getParsers({ page_size: 1 }).then(r => r.data),
  })

  const { data: policies } = useQuery({
    queryKey: ['policies'],
    queryFn: () => getPolicies({ page_size: 1 }).then(r => r.data),
  })

  const { data: config } = useQuery({
    queryKey: ['configuration'],
    queryFn: () => getConfiguration().then(r => r.data),
  })

  const { data: liveEvents } = useQuery({
    queryKey: ['live-events-count'],
    queryFn: () => getLiveEvents({ limit: 1 }).then(r => r.data),
    refetchInterval: 10000,
  })

  const services = health?.services ?? {}
  const infra = ['postgres', 'redis', 'kafka', 'opensearch', 'minio']
  const liveModules = systemHealth?.modules ?? {}
  const pipelineHealthy = systemHealth?.status === 'HEALTHY'

  return (
    <Layout>
      <PageHeader
        title="Control Plane Overview"
        subtitle="Live platform state, service mesh telemetry, and pipeline health"
      />

      {/* Stats row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 12, marginBottom: 24 }}>
        <StatCard
          label="Pipeline Status"
          value={systemHealth?.status ?? (health?.overall || 'UNKNOWN')}
          color={pipelineHealthy ? 'var(--green)' : 'var(--yellow)'}
        />
        <StatCard label="Tenants" value={tenants?.total ?? '—'} />
        <StatCard label="Sources" value={sources?.total ?? '—'} />
        <StatCard label="Parsers" value={parsers?.total ?? '—'} />
        <StatCard label="Policies" value={policies?.total ?? '—'} />
        <StatCard label="Live Events" value={liveEvents?.total ?? '0'} color="var(--accent)" />
        <StatCard label="Config Version" value={config?.version ?? '—'} color="var(--green)" />
      </div>

      {/* Service health */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 24 }}>
        <Card title="Infrastructure Datastores (M6 Monitored)">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {infra.map(svc => {
              const s = services[svc]
              return (
                <div
                  key={svc}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 0',
                    borderBottom: '1px solid var(--border)',
                  }}
                >
                  <span style={{ fontSize: 13, textTransform: 'capitalize', fontWeight: 500 }}>{svc}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {s?.latency_ms != null && (
                      <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.latency_ms}ms</span>
                    )}
                    <StatusBadge status={s?.status ?? 'UNKNOWN'} />
                  </div>
                </div>
              )
            })}
          </div>
        </Card>

        <Card title="Live Microservice Mesh (Health Aggregator :18090)">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {Object.keys(liveModules).length > 0 ? (
              Object.entries(liveModules).map(([name, mod]) => (
                <div
                  key={name}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '8px 0',
                    borderBottom: '1px solid var(--border)',
                  }}
                >
                  <div>
                    <div style={{ fontSize: 13, fontWeight: 500 }}>{name}</div>
                    {mod.latency_ms > 0 && (
                      <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>Probe: {mod.latency_ms}ms</div>
                    )}
                  </div>
                  <StatusBadge status={mod.healthy ? 'HEALTHY' : 'DOWN'} />
                </div>
              ))
            ) : (
              <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
                Querying live mesh telemetry from Health Aggregator...
              </div>
            )}
          </div>
        </Card>
      </div>

      {/* Redis Configuration State */}
      <Card title="Redis Active Configuration Materialization">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))', gap: 10 }}>
          {['sources', 'parsers', 'schemas', 'mappings', 'policies'].map(key => {
            const val = (config as any)?.[key]
            const count = Array.isArray(val) ? val.length : val ? Object.keys(val).length : 0
            return (
              <div key={key} style={{ background: 'var(--bg-elevated)', borderRadius: 6, padding: '10px 12px', textAlign: 'center' }}>
                <div style={{ fontSize: 20, fontWeight: 700, color: count > 0 ? 'var(--green)' : 'var(--text-dim)' }}>
                  {config ? count : '—'}
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2, textTransform: 'capitalize' }}>
                  {key}
                </div>
              </div>
            )
          })}
        </div>
        {config?.updated_at && (
          <div style={{ marginTop: 10, fontSize: 11, color: 'var(--text-dim)' }}>
            Snapshot timestamp: {new Date(config.updated_at).toLocaleString()}
          </div>
        )}
      </Card>
    </Layout>
  )
}
