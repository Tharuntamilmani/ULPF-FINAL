import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Table } from '../components/ui/Table'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Pagination } from '../components/ui/Pagination'
import { getSources, enableSource, disableSource, deleteSource } from '../api/endpoints'
import type { Source } from '../types'

export function SourcesPage() {
  const [page, setPage] = useState(1)
  const [q, setQ] = useState('')
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['sources', page, q],
    queryFn: () => getSources({ page, page_size: 20, q: q || undefined }).then(r => r.data),
  })

  const enableMut = useMutation({ mutationFn: (id: string) => enableSource(id), onSuccess: () => { toast.success('Source enabled'); qc.invalidateQueries({ queryKey: ['sources'] }) } })
  const disableMut = useMutation({ mutationFn: (id: string) => disableSource(id), onSuccess: () => { toast.success('Source disabled'); qc.invalidateQueries({ queryKey: ['sources'] }) } })
  const deleteMut = useMutation({
    mutationFn: (id: string) => deleteSource(id),
    onSuccess: () => { toast.success('Source deleted'); qc.invalidateQueries({ queryKey: ['sources'] }) },
    onError: () => toast.error('Delete failed'),
  })

  const columns = [
    { key: 'source_id', label: 'Source ID' },
    { key: 'name', label: 'Name' },
    { key: 'vendor', label: 'Vendor' },
    { key: 'product', label: 'Product' },
    { key: 'protocol', label: 'Protocol' },
    { key: 'status', label: 'Status', render: (r: Source) => <StatusBadge status={r.status} /> },
    { key: 'actions', label: '', render: (r: Source) => (
      <div style={{ display: 'flex', gap: 6 }}>
        {r.status !== 'active' && <Btn onClick={() => enableMut.mutate(r.id)} color="var(--green)">Enable</Btn>}
        {r.status === 'active' && <Btn onClick={() => disableMut.mutate(r.id)} color="var(--yellow)">Disable</Btn>}
        <Btn onClick={() => { if (confirm(`Delete ${r.source_id}?`)) deleteMut.mutate(r.id) }} color="var(--red)">Delete</Btn>
      </div>
    )},
  ]

  return (
    <Layout>
      <PageHeader title="Sources" subtitle="Log source metadata registry" />
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border)', display: 'flex', gap: 10 }}>
          <input value={q} onChange={e => { setQ(e.target.value); setPage(1) }} placeholder="Search sources…" style={searchStyle} />
        </div>
        <Table columns={columns as any} data={(data?.items ?? []) as any} loading={isLoading} emptyMessage="No sources registered" />
        <div style={{ padding: '0 16px' }}>
          <Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} onPage={setPage} />
        </div>
      </div>
    </Layout>
  )
}

const Btn = ({ onClick, color, children }: { onClick: () => void; color: string; children: string }) => (
  <button onClick={onClick} style={{ padding: '3px 8px', background: 'transparent', border: `1px solid ${color}`, color, borderRadius: 4, fontSize: 11, cursor: 'pointer' }}>{children}</button>
)
const searchStyle: React.CSSProperties = { padding: '6px 12px', background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 13, width: 280 }
