import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Table } from '../components/ui/Table'
import { Pagination } from '../components/ui/Pagination'
import { getMappings } from '../api/endpoints'
import type { Mapping } from '../types'

export function MappingsPage() {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useQuery({ queryKey: ['mappings', page], queryFn: () => getMappings({ page, page_size: 20 }).then(r => r.data) })

  const columns = [
    { key: 'mapping_id', label: 'Mapping ID' },
    { key: 'source_format', label: 'Source Format' },
    { key: 'target_schema', label: 'Target Schema' },
    { key: 'target_version', label: 'Version' },
    { key: 'fields', label: 'Fields', render: (r: Mapping) => <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>{Object.keys(r.fields).length} field mappings</span> },
    { key: 'is_active', label: 'Active', render: (r: Mapping) => <span style={{ color: r.is_active ? 'var(--green)' : 'var(--red)', fontSize: 12 }}>{r.is_active ? 'Yes' : 'No'}</span> },
  ]

  return (
    <Layout>
      <PageHeader title="Mappings" subtitle="Field mapping metadata registry" />
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
        <Table columns={columns as any} data={(data?.items ?? []) as any} loading={isLoading} emptyMessage="No mappings registered" />
        <div style={{ padding: '0 16px' }}><Pagination page={page} pages={data?.pages ?? 1} total={data?.total ?? 0} onPage={setPage} /></div>
      </div>
    </Layout>
  )
}
