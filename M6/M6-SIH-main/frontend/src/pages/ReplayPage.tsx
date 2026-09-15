import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Table } from '../components/ui/Table'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Pagination } from '../components/ui/Pagination'
import { getReplays, requestReplay } from '../api/endpoints'
import type { ReplayOperation } from '../types'

export function ReplayPage() {
  const [page, setPage] = useState(1)
  const [eventId, setEventId] = useState('')
  const [reason, setReason] = useState('')
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({ queryKey: ['replays', page], queryFn: () => getReplays({ page, page_size: 20 }).then(r => r.data) })

  const replayMut = useMutation({
    mutationFn: () => requestReplay(eventId, { reason }),
    onSuccess: () => { toast.success(`Replay requested for ${eventId}`); setEventId(''); setReason(''); qc.invalidateQueries({ queryKey: ['replays'] }) },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Request failed'),
  })

  const columns = [
    { key: 'event_id', label: 'Event ID' },
    { key: 'source', label: 'Source' },
    { key: 'requested_by', label: 'Requested By' },
    { key: 'requested_at', label: 'Requested At', render: (r: ReplayOperation) => new Date(r.requested_at).toLocaleString() },
    { key: 'status', label: 'Status', render: (r: ReplayOperation) => <StatusBadge status={r.status} /> },
    { key: 'reason', label: 'Reason', render: (r: ReplayOperation) => <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{r.reason ?? '—'}</span> },
  ]

  return (
    <Layout>
      <PageHeader title="Replay" subtitle="Request and track event replay operations" />

      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 16, marginBottom: 16 }}>
        <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 12 }}>Request Replay</div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-end' }}>
          <div><label style={labelStyle}>Event ID</label><input value={eventId} onChange={e => setEventId(e.target.value)} placeholder="event-uuid" style={inputStyle} /></div>
          <div><label style={labelStyle}>Reason (optional)</label><input value={reason} onChange={e => setReason(e.target.value)} placeholder="e.g. parser bug fix" style={inputStyle} /></div>
          <button onClick={() => replayMut.mutate()} disabled={!eventId || replayMut.isPending}
            style={{ padding: '8px 20px', background: 'var(--accent)', border: 'none', color: '#fff', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>
            {replayMut.isPending ? '…' : 'Request'}
          </button>
        </div>
      </div>

      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        <Table columns={columns as any} data={(data?.items ?? []) as any} loading={isLoading} emptyMessage="No replay operations" />
        <div style={{ padding: '0 16px' }}><Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} onPage={setPage} /></div>
      </div>
    </Layout>
  )
}

const labelStyle: React.CSSProperties = { display: 'block', marginBottom: 4, fontSize: 12, color: 'var(--text-muted)' }
const inputStyle: React.CSSProperties = { padding: '8px 12px', background: 'var(--bg-base)', border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-primary)', fontSize: 13 }
