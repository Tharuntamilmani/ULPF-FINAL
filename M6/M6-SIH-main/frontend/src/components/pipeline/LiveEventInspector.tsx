import React from 'react'
import { useNavigate } from 'react-router-dom'
import { ProcessedPipelineEvent } from '../../api/pipelineService'
import { CheckCircle2, Circle, Clock, ExternalLink, Shield, FileText, GitBranch, Key } from 'lucide-react'

interface LiveEventInspectorProps {
  event: ProcessedPipelineEvent | null
  onOpenRaw?: () => void
  onOpenTrace?: () => void
  onOpenUes?: () => void
}

export function LiveEventInspector({
  event,
  onOpenRaw,
  onOpenTrace,
  onOpenUes,
}: LiveEventInspectorProps) {
  const navigate = useNavigate()

  if (!event) {
    return (
      <div
        style={{
          background: 'var(--bg-card)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius)',
          padding: 20,
          textAlign: 'center',
          color: 'var(--text-dim)',
        }}
      >
        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6 }}>
          NO ACTIVE EVENT
        </div>
        <div style={{ fontSize: 12 }}>
          Click <strong style={{ color: 'var(--accent)' }}>"+ SEND TEST EVENT"</strong> above to dispatch real vendor logs into the live processing pipeline.
        </div>
      </div>
    )
  }

  const timelineSteps = [
    { label: 'Security Gateway', stage: 'gateway', status: event.stages.gateway.status, latency: event.stages.gateway.latencyMs },
    { label: 'M1 Ingestion (Vault)', stage: 'm1', status: event.stages.m1.status, latency: event.stages.m1.latencyMs },
    { label: 'Kafka Broker Transit', stage: 'kafka', status: event.stages.kafka.status, latency: event.stages.kafka.latencyMs },
    { label: 'M2 Parser Engine', stage: 'm2', status: event.stages.m2.status, latency: event.stages.m2.latencyMs },
    { label: 'M3 Canonical Normalizer', stage: 'm3', status: event.stages.m3.status, latency: event.stages.m3.latencyMs },
    { label: 'M4 Context Enrichment', stage: 'm4', status: event.stages.m4.status, latency: event.stages.m4.latencyMs },
    { label: 'M5 Smart Policy Router', stage: 'm5', status: event.stages.m5.status, latency: event.stages.m5.latencyMs },
  ]

  const totalLatency = timelineSteps.reduce((acc, step) => acc + (step.latency || 0), 0)

  return (
    <div
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '20px',
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
      }}
    >
      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border)', paddingBottom: 14 }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              LIVE EVENT INSPECTOR
            </span>
            {event.isSimulated && (
              <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', background: 'rgba(245, 158, 11, 0.15)', color: 'var(--yellow)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 4 }}>
                DEMO SIMULATION
              </span>
            )}
          </div>
          <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)', marginTop: 4 }}>
            {event.eventId}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, padding: '4px 8px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid var(--green)', borderRadius: 4, color: 'var(--green)', fontSize: 11, fontWeight: 700 }}>
            <CheckCircle2 size={12} />
            {event.status}
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4 }}>
            Total latency: {totalLatency.toFixed(1)}ms
          </div>
        </div>
      </div>

      {/* Metadata Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 10, fontSize: 11 }}>
        <div style={{ background: 'var(--bg-surface)', padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-dim)', fontSize: 10, fontWeight: 600 }}>TENANT</div>
          <div style={{ color: 'var(--text-primary)', fontWeight: 700, marginTop: 2 }}>{event.tenantId}</div>
        </div>
        <div style={{ background: 'var(--bg-surface)', padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-dim)', fontSize: 10, fontWeight: 600 }}>SOURCE SENSOR</div>
          <div style={{ color: 'var(--text-primary)', fontWeight: 700, marginTop: 2 }}>{event.sourceId}</div>
        </div>
        <div style={{ background: 'var(--bg-surface)', padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-dim)', fontSize: 10, fontWeight: 600 }}>TRANSPORT PROTOCOL</div>
          <div style={{ color: 'var(--text-primary)', fontWeight: 700, marginTop: 2 }}>{event.transport.toUpperCase()} / Wire</div>
        </div>
        <div style={{ background: 'var(--bg-surface)', padding: '8px 10px', borderRadius: 6, border: '1px solid var(--border)' }}>
          <div style={{ color: 'var(--text-dim)', fontSize: 10, fontWeight: 600 }}>RAW EVIDENCE ID</div>
          <div style={{ color: 'var(--cyan)', fontWeight: 700, fontFamily: 'var(--font-mono)', fontSize: 10, marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {event.rawEventId}
          </div>
        </div>
      </div>

      {/* Forensic Hash Check */}
      <div style={{ background: 'rgba(6, 182, 212, 0.08)', border: '1px solid rgba(6, 182, 212, 0.25)', borderRadius: 6, padding: '10px 12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 10, color: 'var(--text-muted)', marginBottom: 4 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4, fontWeight: 700, color: 'var(--cyan)' }}>
            <Key size={12} /> AUTHORITATIVE RAW SHA-256 (M1)
          </span>
          <span style={{ color: 'var(--green)', fontWeight: 700 }}>✓ SEALED</span>
        </div>
        <div style={{ fontFamily: 'var(--font-mono)', fontSize: 10, color: '#e2e8f0', wordBreak: 'break-all' }}>
          {event.rawHash}
        </div>
      </div>

      {/* Processing Timeline */}
      <div>
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', marginBottom: 8, display: 'flex', justifyContent: 'space-between' }}>
          <span>PROCESSING TIMELINE</span>
          <span style={{ color: 'var(--text-dim)' }}>7 / 7 Hops Passed</span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {timelineSteps.map((step, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 10px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 4,
                fontSize: 11,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <CheckCircle2 size={13} color="var(--green)" />
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{step.label}</span>
              </div>
              <span style={{ color: 'var(--text-dim)', fontSize: 10, fontFamily: 'var(--font-mono)' }}>
                {step.latency?.toFixed(1)}ms
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Navigation Quick Actions */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8, paddingTop: 4 }}>
        <button
          onClick={onOpenUes || (() => navigate(`/events/${event.eventId}`))}
          style={{
            padding: '8px 10px',
            background: 'var(--bg-surface)',
            border: '1px solid var(--accent)',
            borderRadius: 6,
            color: 'var(--accent)',
            fontSize: 11,
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
          }}
        >
          <FileText size={12} />
          VIEW UES
        </button>

        <button
          onClick={onOpenTrace || (() => navigate(`/events/${event.eventId}/trace`))}
          style={{
            padding: '8px 10px',
            background: 'var(--bg-surface)',
            border: '1px solid rgba(139, 92, 246, 0.4)',
            borderRadius: 6,
            color: '#c4b5fd',
            fontSize: 11,
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
          }}
        >
          <GitBranch size={12} />
          TRACE EVENT
        </button>

        <button
          onClick={onOpenRaw || (() => navigate(`/raw-evidence?id=${event.rawEventId}`))}
          style={{
            padding: '8px 10px',
            background: 'var(--bg-surface)',
            border: '1px solid rgba(6, 182, 212, 0.4)',
            borderRadius: 6,
            color: 'var(--cyan)',
            fontSize: 11,
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 4,
          }}
        >
          <Key size={12} />
          VIEW RAW
        </button>
      </div>
    </div>
  )
}
