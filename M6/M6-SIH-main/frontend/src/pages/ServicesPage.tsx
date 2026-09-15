import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layout, PageHeader } from '../components/layout/Layout'
import { StatusBadge } from '../components/ui/StatusBadge'
import { getAllServicesHealth } from '../api/endpoints'
import type { ServiceHealth } from '../types'

export function ServicesPage() {
  const { data, isLoading, refetch } = useQuery({
    queryKey: ['services-all'],
    queryFn: () => getAllServicesHealth().then(r => r.data),
    refetchInterval: 30000,
  })

  const services = data?.services ?? {}

  return (
    <Layout>
      <PageHeader title="Services" subtitle="Real-time health of all ULPF platform services"
        actions={<button onClick={() => refetch()} style={btnStyle}>Refresh</button>} />

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 12 }}>
        {Object.entries(services).map(([name, svc]) => (
          <ServiceCard key={name} name={name} svc={svc as ServiceHealth} />
        ))}
        {isLoading && <div style={{ color: 'var(--text-muted)', padding: 20 }}>Loading service health…</div>}
      </div>
    </Layout>
  )
}

function ServiceCard({ name, svc }: { name: string; svc: ServiceHealth }) {
  const isMock = svc.is_mock
  return (
    <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: '14px 16px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 13 }}>{name}</div>
          {isMock && <div style={{ fontSize: 10, color: 'var(--orange)', marginTop: 2 }}>⚠ MOCK ADAPTER</div>}
        </div>
        <StatusBadge status={svc.status} />
      </div>
      {svc.latency_ms != null && (
        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>Latency: {svc.latency_ms}ms</div>
      )}
      {svc.details && Object.keys(svc.details).length > 0 && (
        <div style={{ marginTop: 8, padding: '6px 8px', background: 'var(--bg-elevated)', borderRadius: 4, fontSize: 11, color: 'var(--text-muted)', fontFamily: 'monospace' }}>
          {JSON.stringify(svc.details, null, 0).slice(0, 120)}
        </div>
      )}
      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 6 }}>
        Checked: {svc.checked_at ? new Date(svc.checked_at).toLocaleTimeString() : '—'}
      </div>
    </div>
  )
}

const btnStyle: React.CSSProperties = { padding: '6px 14px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text-primary)', borderRadius: 6, cursor: 'pointer', fontSize: 13 }
