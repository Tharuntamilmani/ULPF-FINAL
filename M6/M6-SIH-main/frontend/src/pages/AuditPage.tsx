import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Table } from '../components/ui/Table'
import { Pagination } from '../components/ui/Pagination'
import { getAuditLogs } from '../api/endpoints'
import type { AuditLog } from '../types'
import { formatDistanceToNow } from 'date-fns'

export function AuditPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery({
    queryKey: ['audit', page],
    queryFn: () => getAuditLogs({ page, page_size: 50 }).then(r => r.data),
    refetchInterval: 15000,
  })

  const columns = [
    { key: 'timestamp', label: 'Time', render: (r: AuditLog) => <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{formatDistanceToNow(new Date(r.timestamp), { addSuffix: true })}</span> },
    { key: 'actor', label: 'Actor', render: (r: AuditLog) => <span>{r.actor} {r.actor_role && <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>({r.actor_role})</span>}</span> },
    { key: 'action', label: 'Action', render: (r: AuditLog) => <code style={{ fontSize: 11, color: 'var(--accent)', background: 'var(--bg-elevated)', padding: '2px 5px', borderRadius: 3 }}>{r.action}</code> },
    { key: 'resource_type', label: 'Resource', render: (r: AuditLog) => <span>{r.resource_type}{r.resource_id && ` / ${r.resource_id}`}</span> },
    { key: 'result', label: 'Result', render: (r: AuditLog) => (
      <span style={{ color: r.result === 'SUCCESS' ? 'var(--green)' : 'var(--red)', fontSize: 11, fontWeight: 600 }}>{r.result}</span>
    )},
  ]

  return (
    <Layout>
      <PageHeader title="Audit Trail" subtitle="Append-only log of all administrative actions" />
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        <Table columns={columns as any} data={(data?.items ?? []) as any} loading={isLoading} emptyMessage="No audit events" />
        <div style={{ padding: '0 16px' }}><Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} onPage={setPage} /></div>
      </div>
    </Layout>
  )
}
