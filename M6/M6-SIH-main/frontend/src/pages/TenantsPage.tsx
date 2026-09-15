import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Card } from '../components/ui/Card'
import { StatusBadge } from '../components/ui/StatusBadge'
import { getTenants, createTenant, updateTenant } from '../api/endpoints'
import type { Tenant, TenantStatus } from '../types'
import { Plus, CheckCircle, PauseCircle, XCircle, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'

export function TenantsPage() {
  const queryClient = useQueryClient()
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [status, setStatus] = useState<TenantStatus>('ACTIVE')

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['tenants'],
    queryFn: () => getTenants().then(r => r.data),
    refetchInterval: 10000,
  })

  const createMutation = useMutation({
    mutationFn: () => createTenant({ name, slug, status }),
    onSuccess: () => {
      toast.success(`Tenant '${name}' created successfully`)
      setShowCreate(false)
      setName('')
      setSlug('')
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to create tenant')
    },
  })

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, newStatus }: { id: string; newStatus: TenantStatus }) =>
      updateTenant(id, { status: newStatus }),
    onSuccess: (_, vars) => {
      toast.success(`Tenant updated to ${vars.newStatus}`)
      queryClient.invalidateQueries({ queryKey: ['tenants'] })
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to update tenant status')
    },
  })

  const tenants = data?.items ?? []

  return (
    <Layout>
      <PageHeader
        title="Tenant Management"
        subtitle="Platform-level multi-tenant isolation, provisioning, and status control"
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => refetch()}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '8px 12px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                color: 'var(--text-primary)',
                cursor: 'pointer',
                fontSize: 13,
              }}
            >
              <RefreshCw size={14} /> Refresh
            </button>
            <button
              onClick={() => setShowCreate(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '8px 14px',
                background: 'var(--accent)',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 600,
                fontSize: 13,
              }}
            >
              <Plus size={15} /> Create Tenant
            </button>
          </div>
        }
      />

      <Card title={`Active Registered Tenants (${tenants.length})`}>
        {isLoading ? (
          <div style={{ padding: 20, textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading tenants from M6 database...
          </div>
        ) : tenants.length === 0 ? (
          <div style={{ padding: 30, textAlign: 'center', color: 'var(--text-muted)' }}>
            No tenants configured. Click "Create Tenant" to provision a tenant.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px 12px' }}>Name</th>
                  <th style={{ padding: '10px 12px' }}>Slug / ID</th>
                  <th style={{ padding: '10px 12px' }}>Status</th>
                  <th style={{ padding: '10px 12px' }}>Created At</th>
                  <th style={{ padding: '10px 12px', textAlign: 'right' }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {tenants.map((t: Tenant) => (
                  <tr key={t.id} style={{ borderBottom: '1px solid var(--border)' }}>
                    <td style={{ padding: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                      {t.name}
                    </td>
                    <td style={{ padding: '12px', fontFamily: 'monospace', color: 'var(--text-dim)' }}>
                      {t.slug || t.id}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <StatusBadge status={t.status} />
                    </td>
                    <td style={{ padding: '12px', color: 'var(--text-muted)' }}>
                      {new Date(t.created_at).toLocaleString()}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      <div style={{ display: 'flex', gap: 6, justifyContent: 'flex-end' }}>
                        {t.status !== 'ACTIVE' && (
                          <button
                            onClick={() => updateStatusMutation.mutate({ id: t.id, newStatus: 'ACTIVE' })}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 4,
                              padding: '4px 8px',
                              borderRadius: 4,
                              border: '1px solid var(--border)',
                              background: 'var(--bg-elevated)',
                              color: 'var(--green)',
                              cursor: 'pointer',
                              fontSize: 12,
                            }}
                            title="Activate tenant"
                          >
                            <CheckCircle size={12} /> Activate
                          </button>
                        )}
                        {t.status === 'ACTIVE' && (
                          <button
                            onClick={() => updateStatusMutation.mutate({ id: t.id, newStatus: 'SUSPENDED' })}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 4,
                              padding: '4px 8px',
                              borderRadius: 4,
                              border: '1px solid var(--border)',
                              background: 'var(--bg-elevated)',
                              color: 'var(--yellow)',
                              cursor: 'pointer',
                              fontSize: 12,
                            }}
                            title="Suspend tenant operations"
                          >
                            <PauseCircle size={12} /> Suspend
                          </button>
                        )}
                        {t.status !== 'DISABLED' && (
                          <button
                            onClick={() => updateStatusMutation.mutate({ id: t.id, newStatus: 'DISABLED' })}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 4,
                              padding: '4px 8px',
                              borderRadius: 4,
                              border: '1px solid var(--border)',
                              background: 'var(--bg-elevated)',
                              color: 'var(--red)',
                              cursor: 'pointer',
                              fontSize: 12,
                            }}
                            title="Disable tenant access"
                          >
                            <XCircle size={12} /> Disable
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Modal: Create Tenant */}
      {showCreate && (
        <div
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 100,
          }}
        >
          <div
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              padding: 24,
              width: '100%',
              maxWidth: 440,
            }}
          >
            <h3 style={{ fontSize: 16, fontWeight: 700, marginBottom: 16, color: 'var(--text-primary)' }}>
              Provision New Tenant
            </h3>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                  Tenant Name
                </label>
                <input
                  type="text"
                  placeholder="e.g. Cisco Systems"
                  value={name}
                  onChange={e => {
                    setName(e.target.value)
                    if (!slug) setSlug(e.target.value.toLowerCase().replace(/[^a-z0-9]+/g, '-'))
                  }}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                  Tenant Slug (ID)
                </label>
                <input
                  type="text"
                  placeholder="e.g. cisco-prod"
                  value={slug}
                  onChange={e => setSlug(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                    fontFamily: 'monospace',
                  }}
                />
              </div>

              <div>
                <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 4 }}>
                  Initial Status
                </label>
                <select
                  value={status}
                  onChange={e => setStatus(e.target.value as TenantStatus)}
                  style={{
                    width: '100%',
                    padding: '8px 10px',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    background: 'var(--bg-elevated)',
                    color: 'var(--text-primary)',
                    fontSize: 13,
                  }}
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="SUSPENDED">SUSPENDED</option>
                  <option value="DISABLED">DISABLED</option>
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
                <button
                  type="button"
                  onClick={() => setShowCreate(false)}
                  style={{
                    padding: '8px 14px',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    background: 'transparent',
                    color: 'var(--text-muted)',
                    cursor: 'pointer',
                    fontSize: 13,
                  }}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={!name || !slug || createMutation.isPending}
                  onClick={() => createMutation.mutate()}
                  style={{
                    padding: '8px 16px',
                    borderRadius: 6,
                    border: 'none',
                    background: 'var(--accent)',
                    color: '#fff',
                    fontWeight: 600,
                    cursor: 'pointer',
                    fontSize: 13,
                    opacity: !name || !slug || createMutation.isPending ? 0.6 : 1,
                  }}
                >
                  {createMutation.isPending ? 'Creating...' : 'Create Tenant'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </Layout>
  )
}
