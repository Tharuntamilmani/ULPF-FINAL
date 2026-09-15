import React, { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Card, StatCard } from '../components/ui/Card'
import { StatusBadge } from '../components/ui/StatusBadge'
import { getSystemHealthReport, getAllServicesHealth, postTestIngestEvent, getLiveEvents } from '../api/endpoints'
import { ArrowRight, Send, RefreshCw, CheckCircle2, AlertTriangle, Layers } from 'lucide-react'
import toast from 'react-hot-toast'

export function EventPipelinePage() {
  const [testPayload, setTestPayload] = useState(
    '<166>Sep 14 11:22:33 cisco-asa %ASA-6-302013: Built inbound TCP connection 99201 for outside:192.168.1.50/443 to inside:10.0.0.5/8080'
  )
  const [lastAcceptedId, setLastAcceptedId] = useState<string | null>(null)

  const { data: systemHealth, refetch: refetchHealth } = useQuery({
    queryKey: ['system-health-telemetry'],
    queryFn: () => getSystemHealthReport().then(r => r.data),
    refetchInterval: 5000,
  })

  const { data: m6Services } = useQuery({
    queryKey: ['services-health'],
    queryFn: () => getAllServicesHealth().then(r => r.data),
    refetchInterval: 10000,
  })

  const { data: liveEvents, refetch: refetchEvents } = useQuery({
    queryKey: ['live-events-summary'],
    queryFn: () => getLiveEvents({ limit: 5 }).then(r => r.data),
    refetchInterval: 5000,
  })

  const ingestMutation = useMutation({
    mutationFn: () => postTestIngestEvent(testPayload),
    onSuccess: (res) => {
      const eventId = res.data?.raw_event_id
      setLastAcceptedId(eventId)
      toast.success(`Event accepted by Ingress Gateway! ID: ${eventId?.slice(0, 8)}...`)
      setTimeout(() => {
        refetchEvents()
      }, 1500)
    },
    onError: (err: any) => {
      toast.error(err.response?.data?.detail || 'Failed to ingest event through gateway')
    },
  })

  const modules = systemHealth?.modules ?? {}
  const getModHealthy = (key: string) => modules[key]?.healthy ?? false
  const getModLatency = (key: string) => modules[key]?.latency_ms ?? null

  const pipelineStages = [
    { key: 'Ingress_Gateway', label: 'Ingress Gateway', port: 18080, role: 'Tenant Auth & Header Injection' },
    { key: 'M1', label: 'M1 Ingestion', port: 18001, role: 'Raw Vault & Kafka Publish' },
    { key: 'Kafka', label: 'Kafka Broker', port: 9092, role: 'Topic ulpf.raw / Group ulpf-m1-m2-bridge', isInfra: true },
    { key: 'M2', label: 'M2 Parser Engine', port: 18082, role: 'Classifier & Pattern Matching' },
    { key: 'M3', label: 'M3 UES Normalizer', port: 18083, role: 'Canonical UES v1.0.0 Synthesis' },
    { key: 'M4', label: 'M4 Enrichment', port: 18004, role: 'GeoIP, Threat Intel & Provenance' },
    { key: 'M5', label: 'M5 Smart Router', port: 18085, role: 'Policy Routing & Delivery' },
    { key: 'OpenSearch', label: 'OpenSearch SIEM', port: 9200, role: 'Storage & Event Analytics', isInfra: true },
  ]

  return (
    <Layout>
      <PageHeader
        title="Event Pipeline Dashboard"
        subtitle="End-to-end telemetry and event streaming through the ULPF processing chain"
        actions={
          <button
            onClick={() => {
              refetchHealth()
              refetchEvents()
            }}
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
        }
      />

      {/* Overview Stat Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(170px, 1fr))', gap: 12, marginBottom: 24 }}>
        <StatCard
          label="Pipeline Status"
          value={systemHealth?.status ?? 'CHECKING'}
          color={systemHealth?.status === 'HEALTHY' ? 'var(--green)' : 'var(--yellow)'}
        />
        <StatCard label="Live Indexed Events" value={liveEvents?.total ?? '0'} color="var(--accent)" />
        <StatCard label="Ingress Gateway" value={getModHealthy('Ingress_Gateway') ? 'ONLINE' : 'DOWN'} />
        <StatCard label="M1→M2 Bridge" value={getModHealthy('M1') && getModHealthy('M2') ? 'ACTIVE' : 'DEGRADED'} />
        <StatCard label="M5 Router" value={getModHealthy('M5') ? 'ACTIVE' : 'DOWN'} />
      </div>

      {/* Visual Pipeline Topology */}
      <Card title="Live Pipeline Architecture & Stream Status">
        <div style={{ padding: '16px 0', overflowX: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', minWidth: 960, gap: 8 }}>
            {pipelineStages.map((stage, idx) => {
              const isHealthy = stage.isInfra
                ? m6Services?.services?.[stage.key.toLowerCase()]?.status === 'HEALTHY'
                : getModHealthy(stage.key)
              const latency = stage.isInfra ? null : getModLatency(stage.key)

              return (
                <React.Fragment key={stage.key}>
                  <div
                    style={{
                      flex: 1,
                      padding: 12,
                      background: 'var(--bg-elevated)',
                      border: `1px solid ${isHealthy ? 'var(--border)' : 'var(--red)'}`,
                      borderRadius: 8,
                      position: 'relative',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                      <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent)' }}>:{stage.port}</span>
                      <StatusBadge status={isHealthy ? 'HEALTHY' : 'DOWN'} />
                    </div>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>
                      {stage.label}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.3 }}>
                      {stage.role}
                    </div>
                    {latency !== null && (
                      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 6 }}>
                        Latency: {latency}ms
                      </div>
                    )}
                  </div>
                  {idx < pipelineStages.length - 1 && (
                    <ArrowRight size={16} style={{ color: 'var(--text-dim)', flexShrink: 0 }} />
                  )}
                </React.Fragment>
              )
            })}
          </div>
        </div>
      </Card>

      {/* Live Event Test Injector */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginTop: 20 }}>
        <Card title="Live Event Ingestion Simulator">
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 10 }}>
            Dispatch a real raw syslog string through Ingress Gateway (:18080) with client credentials. The event will be verified, vaulted in MinIO, streamed over Kafka, parsed, normalized to UES, enriched, and routed to OpenSearch.
          </p>

          <textarea
            value={testPayload}
            onChange={e => setTestPayload(e.target.value)}
            rows={4}
            style={{
              width: '100%',
              padding: 10,
              borderRadius: 6,
              border: '1px solid var(--border)',
              background: 'var(--bg-base)',
              color: 'var(--text-primary)',
              fontFamily: 'monospace',
              fontSize: 12,
              marginBottom: 12,
            }}
          />

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              Auth: <code>key-tenant-cisco-prod</code> (tenant-cisco)
            </span>
            <button
              onClick={() => ingestMutation.mutate()}
              disabled={ingestMutation.isPending || !testPayload.trim()}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                padding: '8px 16px',
                background: 'var(--accent)',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                fontWeight: 600,
                fontSize: 13,
                cursor: 'pointer',
                opacity: ingestMutation.isPending ? 0.6 : 1,
              }}
            >
              <Send size={14} /> {ingestMutation.isPending ? 'Ingesting...' : 'Send Live Event'}
            </button>
          </div>

          {lastAcceptedId && (
            <div style={{ marginTop: 12, padding: 8, background: 'var(--bg-elevated)', borderRadius: 4, fontSize: 12, color: 'var(--green)' }}>
              <CheckCircle2 size={14} style={{ display: 'inline', marginRight: 4 }} />
              Ingress accepted! Raw Event ID: <code>{lastAcceptedId}</code>
            </div>
          )}
        </Card>

        {/* Live Event Stream Monitor */}
        <Card title="Live UES Output Stream (M5 Delivery)">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {liveEvents?.events && liveEvents.events.length > 0 ? (
              liveEvents.events.map((ev, i) => (
                <div
                  key={i}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 6,
                    background: 'var(--bg-elevated)',
                    border: '1px solid var(--border)',
                    fontSize: 12,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ fontWeight: 600, color: 'var(--accent)' }}>
                      {ev.event?.type || 'network.flow'}
                    </span>
                    <span style={{ color: 'var(--text-dim)', fontSize: 11 }}>
                      {ev.event?.timestamp ? new Date(ev.event.timestamp).toLocaleTimeString() : 'Recent'}
                    </span>
                  </div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                    Tenant: <code>{ev.tenant?.id || 'tenant-cisco'}</code> • Source: {ev.source?.ip || '192.168.1.50'} → Dest: {ev.destination?.ip || '10.0.0.5'}
                  </div>
                </div>
              ))
            ) : (
              <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)', fontSize: 12 }}>
                No events currently in the buffer. Click "Send Live Event" to push an event through the pipeline.
              </div>
            )}
          </div>
        </Card>
      </div>
    </Layout>
  )
}
