import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Layout } from '../components/layout/Layout'
import { getSystemHealthReport } from '../api/endpoints'
import {
  pipelineEventStore,
  submitLogToPipeline,
  ProcessedPipelineEvent,
} from '../api/pipelineService'
import { PipelineGraph } from '../components/pipeline/PipelineGraph'
import { LiveEventInspector } from '../components/pipeline/LiveEventInspector'
import { SendEventModal } from '../components/pipeline/SendEventModal'
import { StageDetailDrawer } from '../components/pipeline/StageDetailDrawer'
import { PresentationMode } from '../components/pipeline/PresentationMode'
import {
  Send,
  Tv,
  RefreshCw,
  Zap,
} from 'lucide-react'
import toast from 'react-hot-toast'

export function EventPipelinePage() {
  const navigate = useNavigate()
  const [activeEvent, setActiveEvent] = useState<ProcessedPipelineEvent | null>(pipelineEventStore.get())
  const [animatingStage, setAnimatingStage] = useState<string | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [sendModalOpen, setSendModalOpen] = useState(false)
  const [presentationOpen, setPresentationOpen] = useState(false)
  const [isSending, setIsSending] = useState(false)

  const { data: systemHealth, refetch: refetchHealth } = useQuery({
    queryKey: ['system-health-telemetry'],
    queryFn: () => getSystemHealthReport().then(r => r.data).catch(() => null),
    refetchInterval: 5000,
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

  const runSequentialAnimation = (event: ProcessedPipelineEvent) => {
    setActiveEvent(event)
    pipelineEventStore.set(event)

    const stages = ['gateway', 'm1', 'kafka', 'm2', 'm3', 'm4', 'm5', 'destinations']
    let step = 0

    const interval = setInterval(() => {
      if (step < stages.length) {
        setAnimatingStage(stages[step])
        step++
      } else {
        clearInterval(interval)
        setAnimatingStage(null)
        toast.success(`Event ${event.eventId} successfully routed to OpenSearch SIEM!`)
      }
    }, 450)
  }

  const handleSendEvent = async (rawLog: string, templateId: string, tenantId: string, sourceId: string) => {
    setIsSending(true)
    try {
      const event = await submitLogToPipeline(rawLog, templateId, 'key-' + tenantId + '-prod', sourceId)
      setSendModalOpen(false)
      runSequentialAnimation(event)
    } finally {
      setIsSending(false)
    }
  }

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
        {/* Main Brand Header */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'flex-start',
            borderBottom: '1px solid var(--border)',
            paddingBottom: 16,
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div
                style={{
                  width: 38,
                  height: 38,
                  borderRadius: 8,
                  background: 'rgba(59, 130, 246, 0.15)',
                  border: '1px solid var(--accent)',
                  color: 'var(--accent)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Zap size={22} />
              </div>
              <div>
                <h1 style={{ fontSize: 22, fontWeight: 900, color: '#f8fafc', letterSpacing: '-0.02em' }}>
                  Live Event Processing Pipeline
                </h1>
                <p style={{ fontSize: 13, color: 'var(--text-muted)' }}>
                  Real-time ULPF Ingestion, Parsing, Normalization, Enrichment & Routing Mesh
                </p>
              </div>
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 8 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  padding: '4px 10px',
                  background: 'rgba(16, 185, 129, 0.15)',
                  border: '1px solid var(--green)',
                  borderRadius: 6,
                  color: 'var(--green)',
                  fontSize: 11,
                  fontWeight: 800,
                }}
              >
                <span className="status-dot green" />
                SYSTEM OPERATIONAL
              </div>

              <span
                style={{
                  padding: '4px 8px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  fontSize: 11,
                  fontWeight: 600,
                  color: 'var(--text-muted)',
                }}
              >
                Pipeline: <strong style={{ color: 'var(--cyan)' }}>UES v1.0.0</strong>
              </span>
            </div>

            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => setPresentationOpen(true)}
                style={{
                  padding: '8px 14px',
                  background: 'var(--bg-elevated)',
                  border: '1px solid var(--border)',
                  borderRadius: 6,
                  color: 'var(--text-primary)',
                  fontSize: 12,
                  fontWeight: 700,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  cursor: 'pointer',
                }}
              >
                <Tv size={14} /> PRESENTATION MODE
              </button>

              <button
                onClick={() => setSendModalOpen(true)}
                style={{
                  padding: '8px 18px',
                  background: 'var(--accent)',
                  border: 'none',
                  borderRadius: 6,
                  color: '#fff',
                  fontSize: 12,
                  fontWeight: 800,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6,
                  cursor: 'pointer',
                  boxShadow: '0 0 16px var(--accent-glow)',
                }}
              >
                <Send size={14} /> + SEND TEST EVENT
              </button>
            </div>
          </div>
        </div>

        {/* System Health Ribbon */}
        <div
          style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '10px 16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-dim)', letterSpacing: '0.05em' }}>
            SYSTEM HEALTH:
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 18, flexWrap: 'wrap' }}>
            {healthNodes.map(node => {
              const mod = modules[node.key]
              const isHealthy = mod ? mod.healthy : true
              return (
                <div key={node.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 600 }}>
                    {node.label}
                  </span>
                  <span
                    style={{
                      width: 7,
                      height: 7,
                      borderRadius: '50%',
                      background: isHealthy ? 'var(--green)' : 'var(--yellow)',
                      boxShadow: `0 0 6px ${isHealthy ? 'var(--green)' : 'var(--yellow)'}`,
                    }}
                  />
                  <span style={{ fontSize: 11, color: isHealthy ? 'var(--green)' : 'var(--yellow)', fontWeight: 700 }}>
                    {isHealthy ? 'Healthy' : 'Standby'}
                  </span>
                </div>
              )
            })}
          </div>

          <button
            onClick={() => refetchHealth()}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text-dim)',
              fontSize: 11,
              display: 'flex',
              alignItems: 'center',
              gap: 4,
              cursor: 'pointer',
            }}
          >
            <RefreshCw size={12} /> Sync
          </button>
        </div>

        {/* Hero Pipeline Graph */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
            <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--text-primary)', letterSpacing: '0.04em' }}>
              LIVE EVENT PIPELINE
            </div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              Click on any module card to inspect internal state & contracts
            </div>
          </div>

          <PipelineGraph
            activeEvent={activeEvent}
            selectedNodeId={selectedNodeId}
            onSelectNode={nodeId => setSelectedNodeId(nodeId)}
            animatingStage={animatingStage}
          />
        </div>

        {/* Lower Row: Event Inspector */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 20 }}>
          <LiveEventInspector
            event={activeEvent}
            onOpenRaw={() => navigate(`/raw-evidence?id=${activeEvent?.rawEventId}`)}
            onOpenTrace={() => navigate(`/events/${activeEvent?.eventId}/trace`)}
            onOpenUes={() => navigate(`/events/${activeEvent?.eventId}`)}
          />
        </div>

        {/* Modals and Drawers */}
        <SendEventModal
          isOpen={sendModalOpen}
          onClose={() => setSendModalOpen(false)}
          onSend={handleSendEvent}
          isSending={isSending}
        />

        <StageDetailDrawer
          nodeId={selectedNodeId}
          event={activeEvent}
          onClose={() => setSelectedNodeId(null)}
          onViewRaw={() => navigate(`/raw-evidence?id=${activeEvent?.rawEventId}`)}
        />

        <PresentationMode
          isOpen={presentationOpen}
          onClose={() => setPresentationOpen(false)}
          activeEvent={activeEvent}
          onOpenUes={() => {
            setPresentationOpen(false)
            if (activeEvent) navigate(`/events/${activeEvent.eventId}`)
          }}
          onOpenTrace={() => {
            setPresentationOpen(false)
            if (activeEvent) navigate(`/events/${activeEvent.eventId}/trace`)
          }}
          onOpenRaw={() => {
            setPresentationOpen(false)
            if (activeEvent) navigate(`/raw-evidence?id=${activeEvent.rawEventId}`)
          }}
        />
      </div>
    </Layout>
  )
}
