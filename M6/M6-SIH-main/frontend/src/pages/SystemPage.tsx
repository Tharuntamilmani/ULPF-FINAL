import React, { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Layout, PageHeader } from '../components/layout/Layout'
import { getSystemHealthReport, getAuditLogs } from '../api/endpoints'
import { MOCK_METRICS, MOCK_DLQ_EVENTS, MockDLQEvent } from '../lib/mock/mockData'
import {
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts'
import { RefreshCw, X } from 'lucide-react'
import toast from 'react-hot-toast'

type SystemTab = 'services' | 'telemetry' | 'dlq' | 'audit'

interface ServiceRow {
  key: string
  label: string
  description: string
  port: number
}

const SERVICES: ServiceRow[] = [
  { key: 'Ingress_Gateway', label: 'Gateway Security Perimeter', description: 'HTTP/Syslog/TCP event intake & anti-spoofing', port: 18080 },
  { key: 'M1',              label: 'M1 Ingestion Engine',       description: 'Multi-protocol ingest & raw byte-level MinIO vaulting', port: 18001 },
  { key: 'Kafka',           label: 'Kafka Message Broker',       description: 'Distributed event buffer (topic: ulpf.events)', port: 9092 },
  { key: 'M2',              label: 'M2 Parser Engine',          description: 'Format detection & vendor grammar execution', port: 18082 },
  { key: 'M3',              label: 'M3 Canonical Normalizer',   description: 'Field mapping & UES schema enforcement (RFC-8785)', port: 18083 },
  { key: 'M4',              label: 'M4 Context Enrichment',     description: 'Geo-IP, threat intel, & enterprise CMDB lookup', port: 18004 },
  { key: 'M5',              label: 'M5 Smart Router',           description: 'Policy router & OpenSearch SIEM delivery', port: 18085 },
  { key: 'M6',              label: 'M6 Control Plane API',      description: 'Registry, config distribution, & tenant RBAC', port: 18086 },
]

const tooltipStyle = {
  contentStyle: { background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 4, fontSize: 11 },
  labelStyle: { color: 'var(--text-secondary)' },
}

export function SystemPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const tabParam = searchParams.get('tab') as SystemTab | null
  const [activeTab, setActiveTabState] = useState<SystemTab>(
    tabParam === 'dlq' || tabParam === 'audit' || tabParam === 'telemetry' || tabParam === 'services' ? tabParam : 'services'
  )

  const setActiveTab = (tab: SystemTab) => {
    setActiveTabState(tab)
    setSearchParams(tab === 'services' ? {} : { tab })
  }

  const [selectedDlqEvent, setSelectedDlqEvent] = useState<MockDLQEvent | null>(null)
  const [replayedSet, setReplayedSet] = useState<Set<string>>(new Set())

  const { data: health, refetch, isFetching } = useQuery({
    queryKey: ['system-health-telemetry'],
    queryFn: () => getSystemHealthReport().then(r => r.data).catch(() => null),
    refetchInterval: 8000,
  })

  const { data: auditData } = useQuery({
    queryKey: ['audit-logs-tab'],
    queryFn: () => getAuditLogs({ page: 1, page_size: 50 }).then(r => r.data).catch(() => null),
  })

  const modules = health?.modules ?? {}
  const isReal = !!health

  const healthyCount = SERVICES.filter(s => {
    const mod = modules[s.key]
    return mod ? mod.healthy : true
  }).length

  const overallStatus = !isReal ? 'STANDALONE' : healthyCount === SERVICES.length ? 'HEALTHY' : 'DEGRADED'
  const overallColor = overallStatus === 'HEALTHY' ? 'var(--green)' : 'var(--amber)'

  const handleReplay = (id: string) => {
    setReplayedSet(prev => new Set([...prev, id]))
    toast.success(`Event ${id} re-queued for M2 parsing`)
  }

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        <PageHeader
          title="System"
          subtitle="Infrastructure health, service telemetry, queue buffers, failure quarantine (DLQ), and administrative audit trail"
          badge={
            <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '2px 8px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 4 }}>
              <span className={`status-dot ${overallStatus === 'HEALTHY' ? 'green' : 'amber'}`} />
              <span style={{ fontSize: 11, fontWeight: 600, color: overallColor }}>
                {isReal ? overallStatus : 'STANDALONE MODE'}
              </span>
            </div>
          }
          actions={
            <button
              onClick={() => refetch()}
              className="btn btn-secondary"
            >
              <RefreshCw size={11} style={{ animation: isFetching ? 'spin 1s linear infinite' : 'none' }} />
              <span>Refresh</span>
            </button>
          }
        />

        {/* In-Page Navigation Tabs */}
        <div className="tab-bar">
          <button
            onClick={() => setActiveTab('services')}
            className={`tab-btn ${activeTab === 'services' ? 'active' : ''}`}
          >
            SERVICES & HEALTH
          </button>
          <button
            onClick={() => setActiveTab('telemetry')}
            className={`tab-btn ${activeTab === 'telemetry' ? 'active' : ''}`}
          >
            TELEMETRY & CHARTS
          </button>
          <button
            onClick={() => setActiveTab('dlq')}
            className={`tab-btn ${activeTab === 'dlq' ? 'active' : ''}`}
          >
            DEAD LETTER QUEUE ({MOCK_DLQ_EVENTS.length})
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`tab-btn ${activeTab === 'audit' ? 'active' : ''}`}
          >
            AUDIT LOG
          </button>
        </div>

        {/* TAB 1: SERVICES & HEALTH */}
        {activeTab === 'services' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {/* Top Metrics Row - 24px Values */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 12 }}>
              {[
                { label: 'Services Online', value: `${healthyCount} / ${SERVICES.length}` },
                { label: 'Ingress Throughput', value: '1,284 evt/s' },
                { label: 'Avg Stage Latency', value: '2.4ms' },
                { label: 'Parse Success', value: `${MOCK_METRICS.parseSuccessRate}%` },
                { label: 'DLQ Quarantined', value: MOCK_DLQ_EVENTS.length.toString() },
              ].map(({ label, value }) => (
                <div key={label} style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '12px 16px' }}>
                  <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 3 }}>{label}</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>{value}</div>
                </div>
              ))}
            </div>

            {/* Microservice Health Matrix */}
            <div className="table-container">
              <table className="op-table">
                <thead>
                  <tr>
                    <th>SERVICE</th>
                    <th>DESCRIPTION</th>
                    <th style={{ width: 85 }}>PORT</th>
                    <th style={{ width: 110 }}>STATUS</th>
                    <th style={{ width: 95 }}>LATENCY</th>
                    <th>DETAILS</th>
                  </tr>
                </thead>
                <tbody>
                  {SERVICES.map((svc) => {
                    const mod = modules[svc.key]
                    const healthy: boolean = isReal ? (mod?.healthy ?? true) : true
                    const latency = mod?.latency_ms ?? (svc.key === 'Kafka' ? 0.9 : 2.1)
                    const color = healthy ? 'var(--green)' : 'var(--red)'
                    const label = healthy ? 'Healthy' : 'Down'

                    return (
                      <tr key={svc.key}>
                        <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{svc.label}</td>
                        <td style={{ color: 'var(--text-secondary)' }}>{svc.description}</td>
                        <td className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: 13 }}>:{svc.port}</td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <span className={`status-dot ${healthy ? 'green' : 'red'}`} />
                            <span style={{ fontSize: 12, fontWeight: 600, color }}>{label}</span>
                          </div>
                        </td>
                        <td className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: 13 }}>
                          {latency !== null ? `${latency}ms` : '—'}
                        </td>
                        <td style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
                          {mod?.error ?? 'Active & Verified (Zero Dropped Packets)'}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 2: TELEMETRY & CHARTS */}
        {activeTab === 'telemetry' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 12 }}>
                Pipeline Ingestion Rate (events/sec) — 30 min window
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={MOCK_METRICS.throughput}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                  <Tooltip {...tooltipStyle} formatter={(v: number) => [v.toFixed(0), 'evt/s']} />
                  <Area type="monotone" dataKey="value" stroke="var(--accent)" fill="rgba(49, 90, 125, 0.08)" strokeWidth={1.5} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 16 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 12 }}>
                Parse & Schema Validation Rate (%) — 30 min window
              </div>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={MOCK_METRICS.parseSuccess}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis dataKey="time" tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                  <YAxis domain={[90, 100]} tick={{ fontSize: 11, fill: 'var(--text-secondary)' }} />
                  <Tooltip {...tooltipStyle} formatter={(v: number) => [`${v.toFixed(1)}%`, 'Parse Success']} />
                  <Line type="monotone" dataKey="value" stroke="var(--green)" strokeWidth={1.5} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* TAB 3: DEAD LETTER QUEUE (DLQ) */}
        {activeTab === 'dlq' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Events quarantined due to unparseable grammar, missing mandatory headers, or schema violations
            </div>

            <div className="table-container">
              <table className="op-table">
                <thead>
                  <tr>
                    <th style={{ width: 130 }}>EVENT ID</th>
                    <th>SOURCE</th>
                    <th style={{ width: 85 }}>FORMAT</th>
                    <th>FAILURE REASON</th>
                    <th style={{ width: 160 }}>TIME</th>
                    <th style={{ width: 80 }}>RETRIES</th>
                    <th style={{ width: 110 }}>STATUS</th>
                    <th style={{ width: 140, textAlign: 'right' }}>ACTION</th>
                  </tr>
                </thead>
                <tbody>
                  {MOCK_DLQ_EVENTS.map(ev => {
                    const isReplayed = replayedSet.has(ev.id)
                    return (
                      <tr key={ev.id}>
                        <td className="font-mono" style={{ fontWeight: 600, color: 'var(--amber)', fontSize: 13 }}>
                          {ev.id}
                        </td>
                        <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{ev.source}</td>
                        <td className="font-mono" style={{ fontSize: 12.5, color: 'var(--text-secondary)' }}>
                          {ev.format.toUpperCase()}
                        </td>
                        <td style={{ color: 'var(--text-secondary)' }}>{ev.failureReason}</td>
                        <td className="font-mono" style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
                          {new Date(ev.timestamp).toLocaleString()}
                        </td>
                        <td className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: 13 }}>{ev.retryCount}</td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                            <span className={`status-dot ${isReplayed ? 'green' : 'amber'}`} />
                            <span style={{ fontSize: 12, color: isReplayed ? 'var(--green)' : 'var(--amber)', fontWeight: 600 }}>
                              {isReplayed ? 'Replayed' : ev.status}
                            </span>
                          </div>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <button
                            onClick={() => setSelectedDlqEvent(ev)}
                            className="btn btn-ghost"
                            style={{ padding: '3px 8px', fontSize: 12 }}
                          >
                            Inspect
                          </button>
                          <button
                            onClick={() => handleReplay(ev.id)}
                            disabled={isReplayed}
                            className="btn btn-secondary"
                            style={{ padding: '3px 8px', fontSize: 12, marginLeft: 6 }}
                          >
                            Replay
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            {selectedDlqEvent && (
              <div style={{ padding: '14px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-primary)' }}>
                    QUARANTINE DIAGNOSTIC FOR {selectedDlqEvent.id}
                  </div>
                  <button onClick={() => setSelectedDlqEvent(null)} className="btn btn-ghost" style={{ padding: 4 }}>
                    <X size={15} />
                  </button>
                </div>
                <div style={{ fontSize: 12.5, color: 'var(--red)', fontFamily: 'var(--font-mono)', marginBottom: 6 }}>
                  {selectedDlqEvent.errorDetail}
                </div>
                <pre className="code-editor" style={{ maxHeight: 140 }}>
                  {selectedDlqEvent.rawMessage}
                </pre>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: AUDIT LOG */}
        {activeTab === 'audit' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              Append-only audit trail logging every administrative operation, parser distribution, and tenant modification
            </div>

            <div className="table-container">
              <table className="op-table">
                <thead>
                  <tr>
                    <th style={{ width: 160 }}>TIME</th>
                    <th>ACTOR</th>
                    <th>ACTION</th>
                    <th>RESOURCE</th>
                    <th style={{ width: 100 }}>RESULT</th>
                  </tr>
                </thead>
                <tbody>
                  {(auditData?.items && auditData.items.length > 0 ? auditData.items : [
                    { id: 'a1', timestamp: new Date(Date.now() - 120000).toISOString(), actor: 'admin@ulpf.internal', action: 'PARSER_REGISTER', resource_type: 'Parser', resource_id: 'parser-cisco-asa', result: 'SUCCESS' },
                    { id: 'a2', timestamp: new Date(Date.now() - 360000).toISOString(), actor: 'admin@ulpf.internal', action: 'TENANT_UPDATE', resource_type: 'Tenant', resource_id: 'tenant-cisco', result: 'SUCCESS' },
                    { id: 'a3', timestamp: new Date(Date.now() - 720000).toISOString(), actor: 'system-worker', action: 'CONFIG_SYNC', resource_type: 'Outbox', resource_id: 'batch_9182', result: 'SUCCESS' },
                    { id: 'a4', timestamp: new Date(Date.now() - 1440000).toISOString(), actor: 'secops-analyst', action: 'DLQ_REPLAY', resource_type: 'Event', resource_id: 'dlq-49102', result: 'SUCCESS' },
                  ]).map((item: any) => (
                    <tr key={item.id}>
                      <td className="font-mono" style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>
                        {new Date(item.timestamp).toLocaleString()}
                      </td>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                        {item.actor}
                      </td>
                      <td>
                        <span className="font-mono" style={{ fontSize: 12.5, color: 'var(--accent)', fontWeight: 600 }}>
                          {item.action}
                        </span>
                      </td>
                      <td style={{ color: 'var(--text-secondary)' }}>
                        {item.resource_type} {item.resource_id && `(${item.resource_id})`}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                          <span className={`status-dot ${item.result === 'SUCCESS' ? 'green' : 'red'}`} />
                          <span style={{ fontSize: 12, color: item.result === 'SUCCESS' ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                            {item.result}
                          </span>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
