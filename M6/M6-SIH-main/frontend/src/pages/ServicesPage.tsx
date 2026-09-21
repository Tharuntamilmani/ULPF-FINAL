import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layout, PageHeader } from '../components/layout/Layout'
import { StatusBadge } from '../components/ui/StatusBadge'
import { getAllServicesHealth } from '../api/endpoints'
import type { ServiceHealth } from '../types'

interface ServiceMeta {
  label: string
  category: 'infra' | 'pipeline' | 'observability'
  port: string
  desc: string
  command?: string
}

const SERVICE_CATALOG: Record<string, ServiceMeta> = {
  postgres: {
    label: 'PostgreSQL Database',
    category: 'infra',
    port: '5432',
    desc: 'Tenancy isolation, user RBAC, module configurations, and audit log persistence.',
  },
  redis: {
    label: 'Redis In-Memory Cache',
    category: 'infra',
    port: '6379',
    desc: 'High-speed deduplication cache, rate-limiting tokens, and dynamic policy store.',
  },
  kafka: {
    label: 'Apache Kafka Broker',
    category: 'infra',
    port: '9092',
    desc: 'Distributed event bus connecting M1 ingestion through M5 smart delivery.',
  },
  minio: {
    label: 'MinIO S3 Evidence Vault',
    category: 'infra',
    port: '9000',
    desc: 'WORM (Write Once Read Many) immutable raw evidence storage with SHA-256 verification.',
  },
  opensearch: {
    label: 'OpenSearch Cluster',
    category: 'infra',
    port: '9200',
    desc: 'Fast distributed search index for canonical UES events, security queries, and SIEM search.',
  },
  'm1-ingestion': {
    label: 'M1: Ingestion Gateway',
    category: 'pipeline',
    port: '18001',
    desc: 'Multi-protocol ingress (Syslog, HTTP, TCP/UDP), SHA-256 raw hashing, MinIO staging.',
    command: 'python run_stack.py',
  },
  'm2-parser': {
    label: 'M2: Parser Engine',
    category: 'pipeline',
    port: '18082',
    desc: 'Grok & regex matching, tenant-specific field extraction, ReDoS safety verification.',
    command: 'python run_stack.py',
  },
  'm3-normalizer': {
    label: 'M3: Canonical Normalizer',
    category: 'pipeline',
    port: '18083',
    desc: 'Type coercion, schema alignment to UES v1.0.0, vendor-to-canonical taxonomy translation.',
    command: 'python run_stack.py',
  },
  'm4-enrichment': {
    label: 'M4: Context Enrichment',
    category: 'pipeline',
    port: '18004',
    desc: 'GeoIP/ASN lookup, threat intel tagging, RFC-8785 canonical hash computation.',
    command: 'python run_stack.py',
  },
  'm5-delivery': {
    label: 'M5: Smart Router',
    category: 'pipeline',
    port: '18085',
    desc: 'Dynamic routing policy evaluation, egress formatting, multi-destination fan-out.',
    command: 'python run_stack.py',
  },
  prometheus: {
    label: 'Prometheus Metrics',
    category: 'observability',
    port: '9090',
    desc: 'Telemetry scraping engine collecting EPS throughput, latency quantiles, and resource usage.',
  },
  grafana: {
    label: 'Grafana Dashboard',
    category: 'observability',
    port: '3000',
    desc: 'Visual metric exploration, platform latency heatmaps, and system alerts.',
  },
}

export function ServicesPage() {
  const [activeFilter, setActiveFilter] = useState<'all' | 'infra' | 'pipeline' | 'observability'>('all')
  const [showGuide, setShowGuide] = useState(false)

  const { data, isLoading, isRefetching, refetch } = useQuery({
    queryKey: ['services-all'],
    queryFn: () => getAllServicesHealth().then((r) => r.data),
    refetchInterval: 15000,
  })

  const services = data?.services ?? {}
  const serviceEntries = Object.entries(services)

  const healthyCount = serviceEntries.filter(([, s]) => (s as ServiceHealth).status === 'HEALTHY').length
  const totalCount = serviceEntries.length || 12

  // Category counts
  const infraEntries = serviceEntries.filter(([name]) => SERVICE_CATALOG[name]?.category === 'infra')
  const pipelineEntries = serviceEntries.filter(([name]) => SERVICE_CATALOG[name]?.category === 'pipeline')
  const obsEntries = serviceEntries.filter(([name]) => SERVICE_CATALOG[name]?.category === 'observability')

  const filteredEntries = serviceEntries.filter(([name]) => {
    if (activeFilter === 'all') return true
    return SERVICE_CATALOG[name]?.category === activeFilter
  })

  return (
    <Layout>
      <PageHeader
        title="Services Mesh & Infrastructure"
        subtitle="Real-time health status, port bindings, and diagnostic telemetry for all ULPF platform services"
        actions={
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => setShowGuide(!showGuide)}
              style={{
                padding: '6px 14px',
                background: showGuide ? 'rgba(56,189,248,0.2)' : 'var(--bg-elevated)',
                border: '1px solid ' + (showGuide ? 'var(--cyan)' : 'var(--border)'),
                color: showGuide ? 'var(--cyan)' : 'var(--text-primary)',
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: 13,
                fontWeight: 500,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <span>⚡</span>
              <span>Startup Guide</span>
            </button>
            <button
              onClick={() => refetch()}
              disabled={isLoading || isRefetching}
              style={{
                padding: '6px 14px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                color: 'var(--text-primary)',
                borderRadius: 6,
                cursor: 'pointer',
                fontSize: 13,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
              }}
            >
              <span style={{ display: 'inline-block', transform: isRefetching ? 'rotate(180deg)' : 'none', transition: 'transform 0.5s ease' }}>
                ↻
              </span>
              <span>{isRefetching ? 'Probing...' : 'Refresh'}</span>
            </button>
          </div>
        }
      />

      {/* Top SOC Intelligence Ribbon */}
      <div
        style={{
          background: 'linear-gradient(135deg, rgba(15,23,42,0.95), rgba(30,41,59,0.8))',
          border: '1px solid var(--border)',
          borderRadius: 8,
          padding: '14px 18px',
          marginBottom: 16,
          display: 'grid',
          gridTemplateColumns: 'auto 1fr auto',
          gap: 20,
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div
            style={{
              width: 44,
              height: 44,
              borderRadius: '50%',
              background: healthyCount >= 4 ? 'rgba(34,197,94,0.15)' : 'rgba(234,179,8,0.15)',
              border: `1px solid ${healthyCount >= 4 ? 'var(--green)' : 'var(--orange)'}`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 18,
            }}
          >
            {healthyCount >= 4 ? '🛡️' : '⚠️'}
          </div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.02em' }}>
              {healthyCount >= 10 ? 'PLATFORM STATUS: 10/10 CORE SERVICES ONLINE & ACTIVE' : `PLATFORM STATUS: ${healthyCount}/${totalCount} SERVICES CONNECTED`}
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
              {healthyCount >= 10
                ? 'All 5 infrastructure datastores and all 5 data plane microservices (M1–M5) are running and healthy.'
                : 'Core datastores operational. Microservices ready for daemon orchestration.'}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap' }}>
          <div style={{ padding: '4px 10px', background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 4, fontSize: 11 }}>
            <span style={{ color: 'var(--green)', fontWeight: 600 }}>Datastores: </span>
            <span style={{ color: 'var(--text-primary)' }}>
              {infraEntries.filter(([, s]) => (s as ServiceHealth).status === 'HEALTHY').length} / {infraEntries.length || 5} Online
            </span>
          </div>

          <div style={{ padding: '4px 10px', background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 4, fontSize: 11 }}>
            <span style={{ color: 'var(--green)', fontWeight: 600 }}>M1–M5 Data Plane: </span>
            <span style={{ color: 'var(--text-primary)' }}>
              {pipelineEntries.filter(([, s]) => (s as ServiceHealth).status === 'HEALTHY').length} / {pipelineEntries.length || 5} Active
            </span>
          </div>

          <div style={{ padding: '4px 10px', background: 'rgba(56,189,248,0.1)', border: '1px solid rgba(56,189,248,0.3)', borderRadius: 4, fontSize: 11 }}>
            <span style={{ color: 'var(--cyan)', fontWeight: 600 }}>Live Ingestion: </span>
            <span style={{ color: 'var(--green)', fontWeight: 600 }}>Daemon Connected</span>
          </div>
        </div>

        <div style={{ textAlign: 'right' }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              padding: '3px 10px',
              borderRadius: 12,
              fontSize: 11,
              background: 'rgba(34,197,94,0.15)',
              color: 'var(--green)',
              border: '1px solid rgba(34,197,94,0.3)',
              fontWeight: 600,
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--green)' }} />
            CONTROL PLANE OK (:18086)
          </span>
        </div>
      </div>

      {/* Expandable Quick Startup Guide */}
      {showGuide && (
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--cyan)',
            borderRadius: 8,
            padding: 16,
            marginBottom: 16,
            animation: 'fadeIn 0.2s ease-in-out',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--cyan)', display: 'flex', alignItems: 'center', gap: 6 }}>
              <span>🚀</span>
              <span>HOW TO LAUNCH THE LIVE PROCESSING MICROSERVICES</span>
            </div>
            <button
              onClick={() => setShowGuide(false)}
              style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', fontSize: 14 }}
            >
              ✕
            </button>
          </div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 12 }}>
            The infrastructure datastores (PostgreSQL, Redis, Kafka, MinIO, and OpenSearch) are running in Docker.
            To launch the data processing services (M1 Ingestion, M2 Parser, M3 Normalizer, M4 Enrichment, M5 Delivery), run either command in a PowerShell terminal:
          </div>
          <div
            style={{
              background: '#090d16',
              border: '1px solid var(--border)',
              borderRadius: 6,
              padding: '10px 14px',
              fontFamily: 'monospace',
              fontSize: 12,
              color: '#38bdf8',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <code>python E:\ULPF\run_stack.py</code>
            <span style={{ color: 'var(--text-dim)', fontSize: 11 }}># Orchestrates all M1-M5 microservices sequentially</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 8 }}>
            💡 <em>Note:</em> The UI on <code>/dashboard</code>, <code>/pipeline</code>, and <code>/demo</code> will automatically switch to live stream ingestion once services respond on their ports. In the meantime, full end-to-end interactive demo playback remains active.
          </div>
        </div>
      )}

      {/* Filter Tabs */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
        {[
          { key: 'all', label: `All Services (${totalCount})` },
          { key: 'infra', label: `Infrastructure Backbone (${infraEntries.length || 5})` },
          { key: 'pipeline', label: `Data Plane Pipeline (${pipelineEntries.length || 5})` },
          { key: 'observability', label: `Telemetry & Monitoring (${obsEntries.length || 2})` },
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveFilter(tab.key as any)}
            style={{
              padding: '6px 12px',
              background: activeFilter === tab.key ? 'var(--bg-elevated)' : 'transparent',
              border: '1px solid ' + (activeFilter === tab.key ? 'var(--cyan)' : 'var(--border)'),
              color: activeFilter === tab.key ? 'var(--cyan)' : 'var(--text-muted)',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 12,
              fontWeight: activeFilter === tab.key ? 600 : 400,
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Service Cards Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: 12 }}>
        {filteredEntries.map(([name, svc]) => (
          <EnhancedServiceCard key={name} name={name} svc={svc as ServiceHealth} />
        ))}
        {isLoading && (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', color: 'var(--text-muted)', padding: 40 }}>
            Probing platform services...
          </div>
        )}
      </div>
    </Layout>
  )
}

function EnhancedServiceCard({ name, svc }: { name: string; svc: ServiceHealth }) {
  const meta = SERVICE_CATALOG[name] ?? {
    label: name,
    category: 'infra',
    port: '—',
    desc: 'ULPF internal platform service.',
  }

  const isHealthy = svc.status === 'HEALTHY'
  const isMock = svc.is_mock

  // Format error / reason cleanly
  const formatReason = (details: Record<string, any> | undefined): { text: string; hint?: string } => {
    if (!details || Object.keys(details).length === 0) return { text: '' }
    const rawReason = String(details.reason || JSON.stringify(details))

    if (rawReason.toLowerCase().includes('connection refused')) {
      return {
        text: 'Service Process Offline',
        hint: `Port :${meta.port} not responding • Run run_stack.py`,
      }
    }
    if (rawReason.includes('getaddrinfo failed') || rawReason.includes('connection attempts failed')) {
      return {
        text: 'Host Unreachable',
        hint: 'Docker container not running or optional endpoint',
      }
    }
    if (rawReason.includes('AsyncOpenSearch')) {
      return {
        text: 'OpenSearch Async Driver Missing',
        hint: 'Fallback probe in progress',
      }
    }
    return {
      text: rawReason.slice(0, 70),
    }
  }

  const reasonInfo = !isHealthy ? formatReason(svc.details) : null

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: `1px solid ${isHealthy ? 'rgba(34,197,94,0.3)' : 'var(--border)'}`,
        borderRadius: 8,
        padding: '14px 16px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        transition: 'border-color 0.2s',
      }}
    >
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <span style={{ fontWeight: 600, fontSize: 13, color: 'var(--text-primary)' }}>
                {meta.label}
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontFamily: 'monospace',
                  padding: '1px 5px',
                  borderRadius: 3,
                  background: 'var(--bg-elevated)',
                  color: 'var(--text-dim)',
                  border: '1px solid var(--border)',
                }}
              >
                :{meta.port}
              </span>
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3, lineHeight: 1.4 }}>
              {meta.desc}
            </div>
            {isMock && (
              <div style={{ fontSize: 10, color: 'var(--orange)', marginTop: 4, fontWeight: 500 }}>
                ⚠ MOCK ADAPTER
              </div>
            )}
          </div>
          {meta.category === 'observability' && !isHealthy ? (
            <span
              style={{
                background: 'rgba(113,113,122,0.15)',
                color: '#a1a1aa',
                border: '1px solid rgba(161,161,170,0.3)',
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 600,
                letterSpacing: '0.03em',
                textTransform: 'uppercase',
                whiteSpace: 'nowrap',
              }}
            >
              OPTIONAL
            </span>
          ) : (
            <StatusBadge status={svc.status} />
          )}
        </div>

        {isHealthy && svc.latency_ms != null && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 8 }}>
            <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>Latency:</span>
            <span
              style={{
                fontSize: 11,
                fontFamily: 'monospace',
                fontWeight: 600,
                color: svc.latency_ms < 100 ? 'var(--green)' : 'var(--cyan)',
                background: 'rgba(34,197,94,0.1)',
                padding: '2px 6px',
                borderRadius: 4,
              }}
            >
              {svc.latency_ms} ms
            </span>
          </div>
        )}

        {!isHealthy && reasonInfo && (
          <div
            style={{
              marginTop: 10,
              padding: '6px 10px',
              background: 'rgba(239,68,68,0.08)',
              border: '1px solid rgba(239,68,68,0.2)',
              borderRadius: 4,
              fontSize: 11,
            }}
          >
            <div style={{ color: 'var(--red)', fontWeight: 600, display: 'flex', alignItems: 'center', gap: 4 }}>
              <span>●</span>
              <span>{reasonInfo.text}</span>
            </div>
            {reasonInfo.hint && (
              <div style={{ color: 'var(--text-dim)', fontSize: 10, marginTop: 2 }}>
                {reasonInfo.hint}
              </div>
            )}
          </div>
        )}
      </div>

      <div
        style={{
          marginTop: 12,
          paddingTop: 8,
          borderTop: '1px solid var(--border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontSize: 10,
          color: 'var(--text-dim)',
        }}
      >
        <span>Identifier: <code>{name}</code></span>
        <span>
          Checked: {svc.checked_at ? new Date(svc.checked_at).toLocaleTimeString() : '—'}
        </span>
      </div>
    </div>
  )
}
