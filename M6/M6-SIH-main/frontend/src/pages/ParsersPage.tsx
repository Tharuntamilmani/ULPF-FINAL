import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Table } from '../components/ui/Table'
import { StatusBadge } from '../components/ui/StatusBadge'
import { Pagination } from '../components/ui/Pagination'
import { getParsers, approveParser, activateParser, disableParser, rollbackParser, submitParser } from '../api/endpoints'
import type { Parser } from '../types'

const LIFECYCLE: Record<string, { label: string; action: (id: string) => Promise<any>; color: string }[]> = {
  DRAFT:            [{ label: 'Submit',   action: submitParser,   color: 'var(--accent)' }],
  PENDING_APPROVAL: [{ label: 'Approve',  action: approveParser,  color: 'var(--green)' }],
  APPROVED:         [{ label: 'Activate', action: activateParser, color: 'var(--green)' }],
  ACTIVE:           [{ label: 'Disable',  action: disableParser,  color: 'var(--yellow)' }, { label: 'Rollback', action: rollbackParser, color: 'var(--red)' }],
  DISABLED:         [{ label: 'Activate', action: activateParser, color: 'var(--green)' }],
  ROLLED_BACK:      [{ label: 'Activate', action: activateParser, color: 'var(--green)' }],
}

export function ParsersPage() {
  const [page, setPage] = useState(1)
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['parsers', page], queryFn: () => getParsers({ page, page_size: 20 }).then(r => r.data) })

  const act = useMutation({
    mutationFn: ({ fn, id }: { fn: (id: string) => Promise<any>; id: string }) => fn(id),
    onSuccess: () => { toast.success('Action completed'); qc.invalidateQueries({ queryKey: ['parsers'] }) },
    onError: (e: any) => toast.error(e.response?.data?.detail ?? 'Action failed'),
  })

  const columns = [
    { key: 'parser_id', label: 'Parser ID' },
    { key: 'name', label: 'Name' },
    { key: 'vendor', label: 'Vendor' },
    { key: 'format', label: 'Format' },
    { key: 'version', label: 'Version' },
    { key: 'status', label: 'Status', render: (r: Parser) => <StatusBadge status={r.status} /> },
    { key: 'actions', label: '', render: (r: Parser) => (
      <div style={{ display: 'flex', gap: 5 }}>
        {(LIFECYCLE[r.status] ?? []).map(({ label, action, color }) => (
          <button key={label} onClick={() => act.mutate({ fn: action, id: r.id })}
            style={{ padding: '3px 8px', background: 'transparent', border: `1px solid ${color}`, color, borderRadius: 4, fontSize: 11, cursor: 'pointer' }}>
            {label}
          </button>
        ))}
      </div>
    )},
  ]

  return (
    <Layout>
      <PageHeader title="Parsers" subtitle="Parser metadata registry + lifecycle management" />
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        <Table columns={columns as any} data={(data?.items ?? []) as any} loading={isLoading} emptyMessage="No parsers registered" />
        <div style={{ padding: '0 16px' }}><Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} onPage={setPage} /></div>
      </div>
    </Layout>
  )
}
