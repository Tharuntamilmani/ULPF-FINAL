import React, { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { useQuery } from '@tanstack/react-query'
import { getSystemHealthReport } from '../../api/endpoints'

const PAGE_TITLES: Record<string, { title: string; breadcrumb: string[] }> = {
  '/dashboard':     { title: 'Operations Dashboard', breadcrumb: ['ULPF', 'Dashboard'] },
  '/live-events':   { title: 'Live Events Stream', breadcrumb: ['ULPF', 'Events', 'Live Events'] },
  '/raw-events':    { title: 'Raw Evidence Store', breadcrumb: ['ULPF', 'Events', 'Raw Events'] },
  '/ues-events':    { title: 'UES Event Catalog', breadcrumb: ['ULPF', 'Events', 'UES Events'] },
  '/events':        { title: 'Events', breadcrumb: ['ULPF', 'Events'] },
  '/traceability':  { title: 'Traceability', breadcrumb: ['ULPF', 'Traceability'] },
  '/raw-evidence':  { title: 'Raw Wire Evidence', breadcrumb: ['ULPF', 'Events', 'Raw Evidence'] },
  '/parsers':       { title: 'Parsers', breadcrumb: ['ULPF', 'Parsers'] },
  '/parser-studio': { title: 'Parser Studio', breadcrumb: ['ULPF', 'Parsers', 'Studio'] },
  '/system':        { title: 'System', breadcrumb: ['ULPF', 'System'] },
  '/dlq':           { title: 'Dead Letter Queue', breadcrumb: ['ULPF', 'System', 'Dead Letter Queue'] },
  '/replay':        { title: 'Replay History', breadcrumb: ['ULPF', 'System', 'Replay'] },
  '/health':        { title: 'System', breadcrumb: ['ULPF', 'System'] },
  '/observability': { title: 'Observability', breadcrumb: ['ULPF', 'System', 'Observability'] },
  '/audit':         { title: 'Audit Log', breadcrumb: ['ULPF', 'System', 'Audit'] },
  '/control-plane': { title: 'Control Plane Overview', breadcrumb: ['ULPF', 'Control Plane', 'Overview'] },
  '/tenants':       { title: 'Tenant Governance', breadcrumb: ['ULPF', 'Control Plane', 'Tenants'] },
  '/sources':       { title: 'Source Registry', breadcrumb: ['ULPF', 'Control Plane', 'Sources'] },
  '/mappings':      { title: 'Schema Mappings', breadcrumb: ['ULPF', 'Control Plane', 'Mappings'] },
  '/policies':      { title: 'Routing Policies', breadcrumb: ['ULPF', 'Control Plane', 'Policies'] },
  '/configuration': { title: 'Configuration Distribution', breadcrumb: ['ULPF', 'Control Plane', 'Configuration'] },
  '/settings':      { title: 'Platform Settings', breadcrumb: ['ULPF', 'Configuration', 'Settings'] },
  '/pipeline':      { title: 'Live Pipeline', breadcrumb: ['ULPF', 'Overview', 'Pipeline'] },
  '/demo':          { title: 'Demo Cockpit', breadcrumb: ['ULPF', 'Operations', 'Demo Cockpit'] },
}

export function Layout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false)
  const location = useLocation()

  const page = PAGE_TITLES[location.pathname] ??
    (location.pathname.startsWith('/events/')
      ? { title: 'Event Inspection', breadcrumb: ['ULPF', 'Events', 'Detail'] }
      : { title: 'Operations Console', breadcrumb: ['ULPF', 'Console'] })

  const { data: health } = useQuery({
    queryKey: ['system-health-telemetry'],
    queryFn: () => getSystemHealthReport().then(r => r.data).catch(() => null),
    refetchInterval: 8000,
    staleTime: 4000,
  })

  const isApiHealthy = !!health
  const modules = health?.modules ?? {}
  const m5Healthy = modules['M5']?.healthy ?? true

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden', background: 'var(--bg-base)' }}>
      <Sidebar collapsed={collapsed} onToggle={() => setCollapsed(c => !c)} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 }}>
        {/* Minimal Enterprise Top Bar - 40px Height */}
        <header
          style={{
            height: 40,
            background: 'var(--bg-surface)',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 20px',
            flexShrink: 0,
            gap: 16,
            fontSize: 12.5,
          }}
        >
          {/* Left: Breadcrumb (12-13px) */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, overflow: 'hidden' }}>
            <span style={{ color: 'var(--text-secondary)', fontSize: 12.5, letterSpacing: '0.01em', fontWeight: 500 }}>
              {page.breadcrumb.join(' / ')}
            </span>
          </div>

          {/* Right: Operational Metadata */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 16, flexShrink: 0, color: 'var(--text-secondary)', fontSize: 12.5 }}>
            <span style={{ color: 'var(--text-muted)' }}>
              Environment: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>LOCAL / AIR-GAPPED</span>
            </span>

            <span style={{ color: 'var(--border)' }}>•</span>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className={`status-dot ${isApiHealthy ? 'green' : 'amber'}`} />
              <span>API: {isApiHealthy ? 'Healthy' : 'Standalone'}</span>
            </div>

            <span style={{ color: 'var(--border)' }}>•</span>

            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span className={`status-dot ${m5Healthy ? 'green' : 'green'}`} />
              <span>OpenSearch: Connected</span>
            </div>
          </div>
        </header>

        {/* Main Content Area - Full screen intelligent width for 1366, 1440 & 1920 */}
        <main style={{ flex: 1, overflowY: 'auto', background: 'var(--bg-base)' }}>
          <div style={{ padding: '16px 24px', width: '100%', boxSizing: 'border-box' }}>
            {children}
          </div>
        </main>
      </div>
    </div>
  )
}

export function PageHeader({
  title,
  subtitle,
  actions,
  badge,
}: {
  title: string
  subtitle?: string
  actions?: React.ReactNode
  badge?: React.ReactNode
}) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'space-between',
        marginBottom: 16,
        paddingBottom: 12,
        borderBottom: '1px solid var(--border)',
        gap: 16,
      }}
    >
      <div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 3 }}>
          <h1 style={{ fontSize: 23, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.015em', lineHeight: 1.25 }}>
            {title}
          </h1>
          {badge}
        </div>
        {subtitle && (
          <div style={{ color: 'var(--text-secondary)', fontSize: 13.5, lineHeight: 1.4 }}>
            {subtitle}
          </div>
        )}
      </div>
      {actions && (
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {actions}
        </div>
      )}
    </div>
  )
}
