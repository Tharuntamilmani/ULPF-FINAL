import React from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Card } from '../components/ui/Card'
import { getConfiguration, distributeAll, distributeKey } from '../api/endpoints'

const KEYS = ['sources', 'parsers', 'schemas', 'mappings', 'policies']

export function ConfigurationPage() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['configuration'], queryFn: () => getConfiguration().then(r => r.data), refetchInterval: 30000 })

  const distributeAllMut = useMutation({
    mutationFn: distributeAll,
    onSuccess: () => { toast.success('All config distributed to Redis'); qc.invalidateQueries({ queryKey: ['configuration'] }) },
    onError: () => toast.error('Distribution failed'),
  })

  const distributeKeyMut = useMutation({
    mutationFn: (key: string) => distributeKey(key),
    onSuccess: () => { toast.success('Config key distributed'); qc.invalidateQueries({ queryKey: ['configuration'] }) },
    onError: () => toast.error('Distribution failed'),
  })

  return (
    <Layout>
      <PageHeader title="Configuration" subtitle="Redis configuration distribution and version tracking"
        actions={
          <button onClick={() => distributeAllMut.mutate()} disabled={distributeAllMut.isPending}
            style={{ padding: '7px 16px', background: 'var(--accent)', border: 'none', color: '#fff', borderRadius: 6, cursor: 'pointer', fontWeight: 600, fontSize: 13 }}>
            {distributeAllMut.isPending ? 'Distributing…' : 'Distribute All'}
          </button>
        }
      />

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        <Card title="Config Snapshot">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <Row label="Version" value={data?.version ?? '—'} />
            <Row label="Last Updated" value={data?.updated_at ? new Date(data.updated_at).toLocaleString() : '—'} />
            {data?.error && <div style={{ color: 'var(--red)', fontSize: 12, marginTop: 6 }}>Redis error: {data.error}</div>}
          </div>
        </Card>

        <Card title="Key Distribution">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {KEYS.map(key => {
              const val = (data as any)?.[key]
              const count = Array.isArray(val) ? val.length : val ? Object.keys(val).length : 0
              return (
                <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                  <span style={{ flex: 1, fontSize: 13, textTransform: 'capitalize' }}>{key}</span>
                  <span style={{ color: count > 0 ? 'var(--green)' : 'var(--text-dim)', fontSize: 13, fontWeight: 600 }}>{isLoading ? '…' : count}</span>
                  <button onClick={() => distributeKeyMut.mutate(key)}
                    style={{ padding: '3px 10px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text-primary)', borderRadius: 4, fontSize: 11, cursor: 'pointer' }}>
                    Push
                  </button>
                </div>
              )
            })}
          </div>
        </Card>
      </div>

      {/* Raw snapshot */}
      <Card title="Raw Redis Snapshot" style={{ marginTop: 16 }}>
        <pre style={{ fontSize: 11, color: 'var(--text-muted)', overflowX: 'auto', maxHeight: 300 }}>
          {JSON.stringify(data, null, 2)}
        </pre>
      </Card>
    </Layout>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>{label}</span>
      <span style={{ fontSize: 13, fontFamily: 'monospace' }}>{value}</span>
    </div>
  )
}
