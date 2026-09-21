import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Layout } from '../components/layout/Layout'
import { getSystemHealthReport } from '../api/endpoints'
import {
  pipelineEventStore,
  submitLogToPipeline,
  ProcessedPipelineEvent,
  GOLDEN_TEMPLATES,
} from '../api/pipelineService'
import { PipelineGraph } from '../components/pipeline/PipelineGraph'
import { SendEventModal } from '../components/pipeline/SendEventModal'
import { StageDetailDrawer } from '../components/pipeline/StageDetailDrawer'
import { MOCK_UES_EVENTS } from '../lib/mock/mockData'
import toast from 'react-hot-toast'

interface OperationalEventRow {
  time: string
  eventId: string
  source: string
  vendor: string
  format: string
  parser: string
  eventType: string
  severity: string
  status: string
  integrityStatus?: 'VERIFIED' | 'UNVERIFIED'
  latency: string
  rawEventId?: string
}

export function DashboardPage() {
  const navigate = useNavigate()
  const [activeEvent, setActiveEvent] = useState<ProcessedPipelineEvent | null>(pipelineEventStore.get())
  const [animatingStage, setAnimatingStage] = useState<string | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [sendModalOpen, setSendModalOpen] = useState(false)
  const [isSending, setIsSending] = useState(false)
  const [lastUpdated, setLastUpdated] = useState('18:03:24')
  const [eventsProcessedCount, setEventsProcessedCount] = useState(1284912)
  const animTimerRef = React.useRef<any>(null)

  React.useEffect(() => {
    return () => {
      if (animTimerRef.current) {
        clearInterval(animTimerRef.current)
        animTimerRef.current = null
      }
    }
  }, [])

  // Convert mock UES events to operational table rows
  const [tableEvents, setTableEvents] = useState<OperationalEventRow[]>(() => {
    return MOCK_UES_EVENTS.map(ev => {
      const d = new Date(ev.timestamp)
      const timeStr = d.toTimeString().split(' ')[0]
      const isUnverified = ev.status === 'UNVERIFIED' || ev.integrityStatus === 'UNVERIFIED' || ev.validation === 'FAILED'
      return {
        time: timeStr,
        eventId: ev.id,
        source: ev.source,
        vendor: ev.vendor,
        format: ev.format.toUpperCase(),
        parser: ev.parser,
        eventType: ev.eventType,
        severity: ev.severity.toUpperCase(),
        status: isUnverified ? 'Unverified' : (ev.status === 'INDEXED' ? 'Validated' : ev.status),
        integrityStatus: isUnverified ? 'UNVERIFIED' : 'VERIFIED',
        latency: `${ev.processingTimeMs.toFixed(1)}ms`,
        rawEventId: ev.rawEventId,
      }
    })
  })

  // Live System Health Query
  const { data: systemHealth, refetch: refetchHealth, isFetching } = useQuery({
    queryKey: ['system-health-telemetry'],
    queryFn: () => getSystemHealthReport().then(r => r.data).catch(() => null),
    refetchInterval: 8000,
  })

  const modules = systemHealth?.modules ?? {}

  const healthNodes = [
    { label: 'Gateway', key: 'Ingress_Gateway' },
    { label: 'M1', key: 'M1' },
    { label: 'Kafka', key: 'Kafka', defaultHealthy: true },
    { label: 'M2', key: 'M2' },
    { label: 'M3', key: 'M3' },
    { label: 'M4', key: 'M4' },
    { label: 'M5', key: 'M5' },
    { label: 'M6', key: 'M6' },
  ]

  const handleManualRefresh = () => {
    const now = new Date()
    setLastUpdated(now.toTimeString().split(' ')[0])
    refetchHealth()
    toast.success('Telemetry refreshed')
  }

  const STAGES_SEQUENCE = [
    'raw',
    'gateway',
    'm1',
    'kafka',
    'm2',
    'm3',
    'm4',
    'm5',
    'destinations',
  ] as const

  const startPipelineAnimation = (
    event: ProcessedPipelineEvent,
    newRow: OperationalEventRow
  ) => {
    // 9. If user sends another event, restart animation from RAW LOGS
    if (animTimerRef.current) {
      clearInterval(animTimerRef.current)
      animTimerRef.current = null
    }

    const stageDurationMs = 550 // 550ms per stage (total 9 * 550ms = 4,950ms) for smooth, deliberate visual observation
    let currentStep = 0

    // Immediately activate stage 0: RAW LOGS
    setAnimatingStage(STAGES_SEQUENCE[0])

    animTimerRef.current = setInterval(() => {
      currentStep++
      if (currentStep < STAGES_SEQUENCE.length) {
        setAnimatingStage(STAGES_SEQUENCE[currentStep])
      } else {
        // After DESTINATIONS:
        if (animTimerRef.current) {
          clearInterval(animTimerRef.current)
          animTimerRef.current = null
        }

        // 7. Stop animation & keep all stages healthy
        setAnimatingStage(null)

        // 7. Update Events Processed
        setEventsProcessedCount(prev => prev + 1)

        // 7. Update Recent Events with newly submitted event
        setTableEvents(prev => [newRow, ...prev.filter(r => r.eventId !== newRow.eventId).slice(0, 19)])

        // 7. Show newly submitted event & keep all stages healthy
        setActiveEvent(event)

        toast.success(`Event ${event.eventId} successfully delivered & indexed in OpenSearch`)
      }
    }, stageDurationMs)
  }

  const handleSendEvent = async (templateId: string, customPayload?: string) => {
    setIsSending(true)
    try {
      const template = GOLDEN_TEMPLATES.find(t => t.id === templateId) || GOLDEN_TEMPLATES[0]
      const event = await submitLogToPipeline(
        customPayload || template.rawLog,
        templateId,
        template.tenantId,
        template.sourceId
      )

      const now = new Date()
      const newRow: OperationalEventRow = {
        time: now.toTimeString().split(' ')[0],
        eventId: event.eventId,
        source: event.sourceId,
        vendor: (event.templateName || event.stages?.m2?.vendor || event.sourceId).split(' ')[0],
        format: event.transport.toUpperCase(),
        parser: event.stages.m2.parserId,
        eventType: event.finalUes.event?.category || 'network',
        severity: (event.finalUes.event?.severity?.label || event.finalUes.event?.severity || 'HIGH').toUpperCase(),
        status: event.status === 'UNVERIFIED' || event.integrityStatus === 'UNVERIFIED' ? 'Unverified' : 'Validated',
        integrityStatus: event.status === 'UNVERIFIED' || event.integrityStatus === 'UNVERIFIED' ? 'UNVERIFIED' : 'VERIFIED',
        latency: `${(event.totalProcessingTimeMs ?? 28.4).toFixed(1)}ms`,
        rawEventId: event.rawEventId,
      }

      // Close modal immediately and start pipeline animation from RAW LOGS
      setSendModalOpen(false)
      toast.success(`Injected ${template.name} into Ingress Gateway`)
      startPipelineAnimation(event, newRow)
    } finally {
      setIsSending(false)
    }
  }

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        {/* Page Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            paddingBottom: 10,
            borderBottom: '1px solid var(--border)',
          }}
        >
          <div>
            <h1 style={{ fontSize: 23, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '-0.015em' }}>
              ULPF Operations
            </h1>
            <div style={{ fontSize: 13.5, color: 'var(--text-secondary)', marginTop: 2 }}>
              Universal Log Pre-Processing Framework
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
              Last updated {lastUpdated}
            </span>

            <button
              onClick={handleManualRefresh}
              className="btn btn-secondary"
            >
              <span>Refresh</span>
            </button>

            <button
              onClick={() => setSendModalOpen(true)}
              className="btn btn-primary"
            >
              <span>+ Send Test Event</span>
            </button>
          </div>
        </div>

        {/* 8. SYSTEM STATUS: Compact Horizontal Strip */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '10px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: 13,
          }}
        >
          <div style={{ fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em', fontSize: 12, textTransform: 'uppercase' }}>
            SYSTEM STATUS
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
            {healthNodes.map(node => {
              const mod = modules[node.key]
              const isHealthy = mod ? mod.healthy : true
              return (
                <div key={node.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ color: 'var(--text-primary)', fontWeight: 500, fontSize: 13 }}>{node.label}</span>
                  <span className={`status-dot ${isHealthy ? 'green' : 'amber'}`} />
                  <span style={{ color: isHealthy ? 'var(--green)' : 'var(--amber)', fontSize: 12, fontWeight: 500 }}>
                    {isHealthy ? 'Healthy' : 'Standby'}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* 9. KEY METRICS: Restrained 5-column metrics row (24px Values) */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(5, 1fr)',
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
          }}
        >
          {[
            { label: 'INGESTION RATE', value: '1,284 evt/s' },
            { label: 'EVENTS PROCESSED', value: eventsProcessedCount.toLocaleString() },
            { label: 'PARSE SUCCESS', value: '98.7%' },
            { label: 'VALIDATION SUCCESS', value: '99.2%' },
            { label: 'DLQ', value: '14' },
          ].map((m, idx) => (
            <div
              key={m.label}
              style={{
                padding: '12px 18px',
                borderRight: idx < 4 ? '1px solid var(--border-subtle)' : 'none',
              }}
            >
              <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', letterSpacing: '0.04em', marginBottom: 3 }}>
                {m.label}
              </div>
              <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
                {m.value}
              </div>
            </div>
          ))}
        </div>

        {/* 10. EVENT PROCESSING PIPELINE */}
        <div>
          <div style={{ marginBottom: 8 }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              EVENT PROCESSING PIPELINE
            </span>
          </div>

          <PipelineGraph
            activeEvent={activeEvent}
            selectedNodeId={selectedNodeId}
            onSelectNode={nodeId => setSelectedNodeId(nodeId)}
            animatingStage={animatingStage}
            stageDurationMs={550}
          />
        </div>

        {/* 11. RECENT EVENTS: Real Operational Table */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em', textTransform: 'uppercase' }}>
              RECENT EVENTS
            </span>

            <button
              onClick={() => navigate('/live-events')}
              className="btn btn-ghost"
              style={{ fontSize: 12.5, padding: '4px 8px', color: 'var(--accent)', fontWeight: 600 }}
            >
              Open Live Events →
            </button>
          </div>

          <div className="table-container">
            <table className="op-table">
              <thead>
                <tr>
                  <th style={{ width: 95 }}>TIME</th>
                  <th style={{ width: 170 }}>EVENT ID</th>
                  <th>SOURCE</th>
                  <th>VENDOR</th>
                  <th style={{ width: 85 }}>FORMAT</th>
                  <th>PARSER</th>
                  <th>EVENT TYPE</th>
                  <th style={{ width: 105 }}>SEVERITY</th>
                  <th style={{ width: 110 }}>STATUS</th>
                  <th style={{ width: 85 }}>LATENCY</th>
                  <th style={{ width: 110, textAlign: 'right' }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {tableEvents.map((row, idx) => {
                  const isHighlighted = activeEvent?.eventId === row.eventId
                  return (
                    <tr
                      key={row.eventId + idx}
                      style={{
                        background: isHighlighted ? 'var(--accent-subtle)' : undefined,
                      }}
                    >
                      <td className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                        {row.time}
                      </td>
                      <td className="font-mono" style={{ fontWeight: 600, color: 'var(--accent)' }}>
                        {row.eventId}
                      </td>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                        {row.source}
                      </td>
                      <td style={{ color: 'var(--text-secondary)' }}>
                        {row.vendor}
                      </td>
                      <td className="font-mono" style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
                        {row.format}
                      </td>
                      <td className="font-mono" style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                        {row.parser}
                      </td>
                      <td style={{ color: 'var(--text-secondary)' }}>
                        {row.eventType}
                      </td>
                      <td>
                        <span
                          style={{
                            fontSize: 12,
                            fontWeight: 600,
                            color:
                              row.severity === 'CRITICAL' || row.severity === 'HIGH'
                                ? 'var(--red)'
                                : row.severity === 'MEDIUM'
                                ? 'var(--amber)'
                                : 'var(--text-secondary)',
                          }}
                        >
                          {row.severity}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                          <span className={`status-dot ${row.integrityStatus === 'UNVERIFIED' || row.status === 'Unverified' ? 'red' : 'green'}`} />
                          <span
                            style={{
                              fontSize: 12,
                              color: row.integrityStatus === 'UNVERIFIED' || row.status === 'Unverified' ? 'var(--red)' : 'var(--green)',
                              fontWeight: 600,
                            }}
                          >
                            {row.status}
                          </span>
                        </div>
                      </td>
                      <td className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                        {row.latency}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', gap: 8 }}>
                          <button
                            onClick={() => navigate(`/events/${row.eventId}`)}
                            className="btn btn-ghost"
                            style={{ padding: '2px 6px', fontSize: 12, color: 'var(--accent)', fontWeight: 600 }}
                            title="Inspect in Event Explorer"
                          >
                            UES
                          </button>
                          <button
                            onClick={() => navigate(`/events/${row.eventId}/trace`)}
                            className="btn btn-ghost"
                            style={{ padding: '2px 6px', fontSize: 12, color: 'var(--text-secondary)' }}
                            title="Trace Lineage"
                          >
                            Trace
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Send Event Modal */}
        <SendEventModal
          isOpen={sendModalOpen}
          onClose={() => setSendModalOpen(false)}
          onSend={handleSendEvent}
          isSending={isSending}
        />

        {/* Stage Inspection Drawer */}
        <StageDetailDrawer
          nodeId={selectedNodeId}
          event={activeEvent}
          onClose={() => setSelectedNodeId(null)}
        />
      </div>
    </Layout>
  )
}
