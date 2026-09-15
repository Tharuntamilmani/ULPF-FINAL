import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Table } from '../components/ui/Table'
import { Pagination } from '../components/ui/Pagination'
import { getPolicies, enablePolicy, disablePolicy } from '../api/endpoints'
import type { Policy } from '../types'

export function PoliciesPage() {
  const [page, setPage] = useState(1)
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['policies', page], queryFn: () => getPolicies({ page, page_size: 20 }).then(r => r.data) })

  const enable = useMutation({ mutationFn: (id: string) => enablePolicy(id), onSuccess: () => { toast.success('Policy enabled'); qc.invalidateQueries({ queryKey: ['policies'] }) } })
  const disable = useMutation({ mutationFn: (id: string) => disablePolicy(id), onSuccess: () => { toast.success('Policy disabled'); qc.invalidateQueries({ queryKey: ['policies'] }) } })

  const columns = [
    { key: 'policy_id', label: 'Policy ID' },
    { key: 'name', label: 'Name' },
    { key: 'priority', label: 'Priority', render: (r: Policy) => <span style={{ fontFamily: 'monospace', color: 'var(--accent)' }}>{r.priority}</span> },
    { key: 'destinations', label: 'Destinations', render: (r: Policy) => r.destinations.join(', ') },
    { key: 'is_enabled', label: 'Enabled', render: (r: Policy) => <span style={{ color: r.is_enabled ? 'var(--green)' : 'var(--red)', fontWeight: 600, fontSize: 12 }}>{r.is_enabled ? 'Yes' : 'No'}</span> },
    { key: 'actions', label: '', render: (r: Policy) => (
      r.is_enabled
        ? <button onClick={() => disable.mutate(r.id)} style={btnStyle('var(--yellow)')}>Disable</button>
        : <button onClick={() => enable.mutate(r.id)} style={btnStyle('var(--green)')}>Enable</button>
    )},
  ]

  return (
    <Layout>
      <PageHeader title="Policies" subtitle="Routing policy configuration" />
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        <Table columns={columns as any} data={(data?.items ?? []) as any} loading={isLoading} emptyMessage="No policies configured" />
        <div style={{ padding: '0 16px' }}><Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} onPage={setPage} /></div>
      </div>
    </Layout>
  )
}

const btnStyle = (color: string): React.CSSProperties => ({ padding: '3px 8px', background: 'transparent', border: `1px solid ${color}`, color, borderRadius: 4, fontSize: 11, cursor: 'pointer' })
