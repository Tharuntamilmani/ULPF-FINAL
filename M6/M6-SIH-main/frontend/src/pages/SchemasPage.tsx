import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Table } from '../components/ui/Table'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Pagination } from '../components/ui/Pagination'
import { getSchemas } from '../api/endpoints'
import type { Schema } from '../types'

export function SchemasPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery({ queryKey: ['schemas', page], queryFn: () => getSchemas({ page, page_size: 20 }).then(r => r.data) })

  const columns = [
    { key: 'name', label: 'Name' },
    { key: 'versions', label: 'Versions', render: (r: Schema) => (
      <div style={{ display: 'flex', gap: 4 }}>
        {r.versions.map(v => <span key={v.id} style={{ padding: '2px 6px', background: 'var(--bg-elevated)', borderRadius: 4, fontSize: 11, fontFamily: 'monospace' }}>{v.version} <StatusBadge status={v.status} /></span>)}
      </div>
    )},
    { key: 'description', label: 'Description', render: (r: Schema) => <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{r.description ?? '—'}</span> },
    { key: 'created_at', label: 'Created', render: (r: Schema) => new Date(r.created_at).toLocaleDateString() },
  ]

  return (
    <Layout>
      <PageHeader title="Schemas" subtitle="UES and event schema registry" />
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        <Table columns={columns as any} data={(data?.items ?? []) as any} loading={isLoading} emptyMessage="No schemas registered" />
        <div style={{ padding: '0 16px' }}><Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} onPage={setPage} /></div>
      </div>
    </Layout>
  )
}
