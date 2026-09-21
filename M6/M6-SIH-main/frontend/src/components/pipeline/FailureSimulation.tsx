import React, { useState } from 'react'
import { AlertTriangle, RefreshCw, CheckCircle2, Play, ShieldAlert, ArrowDown } from 'lucide-react'

interface FailureScenario {
  id: string
  title: string
  service: string
  description: string
  timeline: Array<{
    stage: string
    status: 'failed' | 'retained' | 'recovered' | 'success'
    detail: string
  }>
}

const SCENARIOS: FailureScenario[] = [
  {
    id: 'm2-unavailable',
    title: 'Simulate M2 Parser Unavailable',
    service: 'M2 Parser Engine (:18082)',
    description: 'When the parser crashes or encounters transient HTTP 503, M1 persists the event in MinIO raw vault and Kafka retains the uncommitted message offset. The bridge retries with exponential backoff until M2 recovers, guaranteeing zero data loss.',
    timeline: [
      { stage: 'M1 Ingestion & Vault', status: 'success', detail: 'Event ingested, SHA-256 computed, stored in MinIO vault, published to Kafka topic ulpf.raw' },
      { stage: 'M2 Parser Dispatch', status: 'failed', detail: 'HTTP 503 Service Unavailable: M2 process unresponsive during scheduled parser re-index' },
      { stage: 'Kafka Bridge Retention', status: 'retained', detail: 'Kafka offset NOT committed; message preserved in queue; exponential backoff active (100ms, 200ms, 400ms)' },
      { stage: 'M2 Process Recovery', status: 'recovered', detail: 'M2 service health probe passes (200 OK); bridge resumes message dispatch' },
      { stage: 'Event Processed & Offset Committed', status: 'success', detail: 'M2 acknowledges 200 OK; Kafka offset committed; event proceeds to M3 UES Normalizer' },
    ],
  },
  {
    id: 'm5-unavailable',
    title: 'Simulate M5 Smart Router Unavailable',
    service: 'M5 Smart Router (:18085)',
    description: 'When M5 policy evaluation is unreachable, M4 holds the enriched event with RFC-8785 canonical digest in the delivery buffer without dropping evidence.',
    timeline: [
      { stage: 'M4 Enriched Digest', status: 'success', detail: 'Context attached, RFC-8785 canonical digest generated' },
      { stage: 'M5 Router Dispatch', status: 'failed', detail: 'Connection refused on port :18085; router process recycling policy rules' },
      { stage: 'Backpressure Buffering', status: 'retained', detail: 'Retry policy engaged with jitter; event retained in delivery queue' },
      { stage: 'M5 Service Restored', status: 'recovered', detail: 'M5 router initialized; policy rules reloaded from M6 cache' },
      { stage: 'Delivery Dispatched', status: 'success', detail: 'Policy matched; event delivered concurrently to OpenSearch SIEM and MinIO Data Lake' },
    ],
  },
  {
    id: 'opensearch-unavailable',
    title: 'Simulate OpenSearch SIEM Outage',
    service: 'OpenSearch Datastore (:9200)',
    description: 'When OpenSearch cluster is in red status or indexing queues are full, M5 buffers messages in the Dead-Letter Queue (DLQ) with raw storage pointers intact, enabling one-click replay.',
    timeline: [
      { stage: 'Policy Evaluation', status: 'success', detail: 'M5 matched policy rule: policy-fw-security-alerts' },
      { stage: 'OpenSearch Delivery', status: 'failed', detail: 'Circuit Breaker Exception: 429 Too Many Requests (Bulk indexing buffer full)' },
      { stage: 'DLQ Routing & Evidence Isolation', status: 'retained', detail: 'Event routed to ulpf.dlq with raw_event_id and storage_ref preserved' },
      { stage: 'Cluster Health Restored', status: 'recovered', detail: 'OpenSearch cluster status returns to GREEN' },
      { stage: 'M6 One-Click Replay', status: 'success', detail: 'M6 triggers /replay operation; DLQ events re-ingested from raw storage without loss' },
    ],
  },
]

export function FailureSimulation() {
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>('m2-unavailable')
  const [running, setRunning] = useState<boolean>(false)
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(-1)

  const activeScenario = SCENARIOS.find(s => s.id === selectedScenarioId) || SCENARIOS[0]

  const handleRunSimulation = () => {
    setRunning(true)
    setCurrentStepIndex(0)

    const interval = setInterval(() => {
      setCurrentStepIndex(prev => {
        if (prev >= activeScenario.timeline.length - 1) {
          clearInterval(interval)
          setRunning(false)
          return prev
        }
        return prev + 1
      })
    }, 1200)
  }

  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 24, display: 'flex', flexDirection: 'column', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--yellow)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              RESILIENCE & FAULT TOLERANCE
            </span>
            <span style={{ fontSize: 9, fontWeight: 700, padding: '2px 6px', background: 'rgba(245, 158, 11, 0.15)', color: 'var(--yellow)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: 4 }}>
              DEMO SIMULATION
            </span>
          </div>
          <h3 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', marginTop: 4 }}>
            Zero-Loss Failure Recovery Demonstration
          </h3>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4, maxWidth: 620 }}>
            Demonstrates ULPF's core architectural guarantee: network drops, parser panics, and datastore saturation never result in silent log drops or lost evidence.
          </p>
        </div>

        <button
          onClick={handleRunSimulation}
          disabled={running}
          style={{
            padding: '10px 18px',
            background: 'var(--accent)',
            border: 'none',
            borderRadius: 6,
            color: '#fff',
            fontSize: 12,
            fontWeight: 700,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            cursor: 'pointer',
            boxShadow: '0 0 12px var(--accent-glow)',
            opacity: running ? 0.7 : 1,
          }}
        >
          {running ? <RefreshCw size={14} className="anim-pulse" style={{ animation: 'spin 1s linear infinite' }} /> : <Play size={14} />}
          {running ? 'Simulating Transit…' : 'RUN SIMULATION'}
        </button>
      </div>

      {/* Scenario Tabs */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
        {SCENARIOS.map(scenario => {
          const isSelected = scenario.id === selectedScenarioId
          return (
            <div
              key={scenario.id}
              onClick={() => {
                if (!running) {
                  setSelectedScenarioId(scenario.id)
                  setCurrentStepIndex(-1)
                }
              }}
              style={{
                padding: '12px 14px',
                background: isSelected ? 'rgba(59, 130, 246, 0.12)' : 'var(--bg-surface)',
                border: `1px solid ${isSelected ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: 'var(--radius)',
                cursor: running ? 'not-allowed' : 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 700, color: isSelected ? '#fff' : 'var(--text-primary)' }}>
                {scenario.title}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 4 }}>
                Target: {scenario.service}
              </div>
            </div>
          )
        })}
      </div>

      {/* Narrative Box */}
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 14 }}>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>
          {activeScenario.description}
        </div>
      </div>

      {/* Timeline Steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {activeScenario.timeline.map((step, idx) => {
          const isCurrent = running && currentStepIndex === idx
          const isPassed = currentStepIndex >= idx
          const statusColor =
            step.status === 'failed'
              ? 'var(--red)'
              : step.status === 'retained'
              ? 'var(--yellow)'
              : step.status === 'recovered'
              ? 'var(--cyan)'
              : 'var(--green)'

          return (
            <div
              key={idx}
              style={{
                padding: '12px 16px',
                background: isCurrent ? 'rgba(59, 130, 246, 0.15)' : 'var(--bg-surface)',
                border: `1px solid ${isCurrent ? 'var(--accent)' : isPassed ? statusColor : 'var(--border)'}`,
                borderRadius: 6,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                transition: 'all 0.25s ease',
                opacity: currentStepIndex >= 0 && !isPassed ? 0.4 : 1,
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div
                  style={{
                    width: 24,
                    height: 24,
                    borderRadius: '50%',
                    background: 'var(--bg-base)',
                    border: `1px solid ${statusColor}`,
                    color: statusColor,
                    fontSize: 11,
                    fontWeight: 700,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {idx + 1}
                </div>
                <div>
                  <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
                    {step.stage}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>
                    {step.detail}
                  </div>
                </div>
              </div>

              <div
                style={{
                  fontSize: 10,
                  fontWeight: 800,
                  padding: '3px 8px',
                  borderRadius: 4,
                  background: `rgba(${step.status === 'failed' ? '239,68,68' : step.status === 'retained' ? '245,158,11' : '16,185,129'}, 0.15)`,
                  color: statusColor,
                  textTransform: 'uppercase',
                }}
              >
                {step.status}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
