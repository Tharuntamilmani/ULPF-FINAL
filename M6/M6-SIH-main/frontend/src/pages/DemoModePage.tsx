import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout, PageHeader } from '../components/layout/Layout'
import {
  pipelineEventStore,
  submitLogToPipeline,
  GOLDEN_TEMPLATES,
  ProcessedPipelineEvent,
  buildSyntheticPipelineEvent,
} from '../api/pipelineService'
import { PipelineGraph } from '../components/pipeline/PipelineGraph'
import { LiveEventInspector } from '../components/pipeline/LiveEventInspector'
import { StageDetailDrawer } from '../components/pipeline/StageDetailDrawer'
import { FailureSimulation } from '../components/pipeline/FailureSimulation'
import { PresentationMode } from '../components/pipeline/PresentationMode'
import {
  Send,
  Sparkles,
  GitBranch,
  ShieldCheck,
  Key,
  Layers,
  CheckCircle2,
  Tv,
  ArrowRight,
  Play,
  RotateCcw,
} from 'lucide-react'
import toast from 'react-hot-toast'

export function DemoModePage() {
  const navigate = useNavigate()
  const [activeEvent, setActiveEvent] = useState<ProcessedPipelineEvent | null>(pipelineEventStore.get())
  const [animatingStage, setAnimatingStage] = useState<string | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [presentationOpen, setPresentationOpen] = useState<boolean>(false)
  const [showFailureSim, setShowFailureSim] = useState<boolean>(false)

  const runPipelineAnimation = (event: ProcessedPipelineEvent) => {
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
        toast.success(`Event ${event.eventId} fully routed to OpenSearch SIEM and Data Lake!`)
      }
    }, 500)
  }

  const handleSendCisco = async () => {
    const tpl = GOLDEN_TEMPLATES[0]
    toast('Dispatching Cisco ASA connection log to Ingress Gateway...', { icon: '🚀' })
    const ev = await submitLogToPipeline(tpl.rawLog, tpl.id)
    runPipelineAnimation(ev)
  }

  const handleSendWindows = async () => {
    const tpl = GOLDEN_TEMPLATES[1]
    toast('Dispatching Windows 4624 Logon event...', { icon: '🚀' })
    const ev = await submitLogToPipeline(tpl.rawLog, tpl.id)
    runPipelineAnimation(ev)
  }

  const handleSendFortigate = async () => {
    const tpl = GOLDEN_TEMPLATES[2]
    toast('Dispatching Fortinet FortiGate Key-Value event...', { icon: '🚀' })
    const ev = await submitLogToPipeline(tpl.rawLog, tpl.id)
    runPipelineAnimation(ev)
  }

  const handleSendGeneric = async () => {
    const tpl = GOLDEN_TEMPLATES[3]
    toast('Dispatching Linux Syslog event...', { icon: '🚀' })
    const ev = await submitLogToPipeline(tpl.rawLog, tpl.id)
    runPipelineAnimation(ev)
  }

  const handleShowNormalization = () => {
    if (activeEvent) {
      setSelectedNodeId('m3')
    } else {
      handleSendCisco().then(() => setSelectedNodeId('m3'))
    }
  }

  const handleShowEnrichment = () => {
    if (activeEvent) {
      setSelectedNodeId('m4')
    } else {
      handleSendCisco().then(() => setSelectedNodeId('m4'))
    }
  }

  const handleShowRouting = () => {
    if (activeEvent) {
      setSelectedNodeId('m5')
    } else {
      handleSendCisco().then(() => setSelectedNodeId('m5'))
    }
  }

  const handleShowTraceability = () => {
    if (activeEvent) {
      navigate(`/events/${activeEvent.eventId}/trace`)
    } else {
      handleSendCisco().then(() => {
        setTimeout(() => navigate('/events/evt_demo/trace'), 1000)
      })
    }
  }

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
        <PageHeader
          title="DEMO COCKPIT & LIVE DEMONSTRATOR"
          subtitle="Single-click presentation controls optimized for live SIH jury demonstration"
          actions={
            <button
              onClick={() => setPresentationOpen(true)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 18px',
                background: 'var(--accent)',
                border: 'none',
                borderRadius: 6,
                color: '#fff',
                fontSize: 13,
                fontWeight: 700,
                cursor: 'pointer',
                boxShadow: '0 0 16px var(--accent-glow)',
              }}
            >
              <Tv size={16} /> PRESENTATION MODE (HUD)
            </button>
          }
        />

        {/* Action Controls Ribbon */}
        <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', padding: 20 }}>
          <div style={{ fontSize: 11, fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 12 }}>
            ONE-CLICK PRESENTATION TRIGGERS
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 12 }}>
            <button
              onClick={handleSendCisco}
              style={{
                padding: '12px 14px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--accent)',
                borderRadius: 6,
                color: '#fff',
                fontSize: 12,
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                cursor: 'pointer',
              }}
            >
              <Play size={14} color="var(--accent)" />
              SEND CISCO ASA EVENT
            </button>

            <button
              onClick={handleSendWindows}
              style={{
                padding: '12px 14px',
                background: 'var(--bg-surface)',
                border: '1px solid #38bdf8',
                borderRadius: 6,
                color: '#fff',
                fontSize: 12,
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                cursor: 'pointer',
              }}
            >
              <Play size={14} color="#38bdf8" />
              SEND WINDOWS 4624
            </button>

            <button
              onClick={handleSendFortigate}
              style={{
                padding: '12px 14px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--purple)',
                borderRadius: 6,
                color: '#fff',
                fontSize: 12,
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                cursor: 'pointer',
              }}
            >
              <Play size={14} color="var(--purple)" />
              SEND FORTIGATE EVENT
            </button>

            <button
              onClick={handleSendGeneric}
              style={{
                padding: '12px 14px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--cyan)',
                borderRadius: 6,
                color: '#fff',
                fontSize: 12,
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 8,
                cursor: 'pointer',
              }}
            >
              <Play size={14} color="var(--cyan)" />
              SEND GENERIC SYSLOG
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
            <button
              onClick={handleShowNormalization}
              style={{
                padding: '10px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                color: 'var(--text-primary)',
                fontSize: 11,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                cursor: 'pointer',
              }}
            >
              <Sparkles size={13} color="var(--green)" />
              SHOW NORMALIZATION
            </button>

            <button
              onClick={handleShowEnrichment}
              style={{
                padding: '10px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                color: 'var(--text-primary)',
                fontSize: 11,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                cursor: 'pointer',
              }}
            >
              <ShieldCheck size={13} color="var(--cyan)" />
              SHOW ENRICHMENT
            </button>

            <button
              onClick={handleShowRouting}
              style={{
                padding: '10px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                color: 'var(--text-primary)',
                fontSize: 11,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                cursor: 'pointer',
              }}
            >
              <ArrowRight size={13} color="var(--accent)" />
              SHOW ROUTING
            </button>

            <button
              onClick={handleShowTraceability}
              style={{
                padding: '10px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 6,
                color: 'var(--text-primary)',
                fontSize: 11,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                cursor: 'pointer',
              }}
            >
              <GitBranch size={13} color="#c4b5fd" />
              SHOW TRACEABILITY
            </button>

            <button
              onClick={() => setShowFailureSim(!showFailureSim)}
              style={{
                padding: '10px',
                background: showFailureSim ? 'rgba(245, 158, 11, 0.15)' : 'var(--bg-elevated)',
                border: `1px solid ${showFailureSim ? 'var(--yellow)' : 'var(--border)'}`,
                borderRadius: 6,
                color: showFailureSim ? 'var(--yellow)' : 'var(--text-primary)',
                fontSize: 11,
                fontWeight: 700,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                cursor: 'pointer',
              }}
            >
              <RotateCcw size={13} />
              {showFailureSim ? 'HIDE RECOVERY' : 'SHOW RECOVERY'}
            </button>
          </div>
        </div>

        {/* Live Hero Pipeline */}
        <PipelineGraph
          activeEvent={activeEvent}
          selectedNodeId={selectedNodeId}
          onSelectNode={nodeId => setSelectedNodeId(nodeId)}
          animatingStage={animatingStage}
        />

        {/* Lower Split: Inspector & Failure Simulation */}
        <div style={{ display: 'grid', gridTemplateColumns: showFailureSim ? '1fr 1fr' : '1fr', gap: 20 }}>
          <LiveEventInspector
            event={activeEvent}
            onOpenRaw={() => navigate(`/raw-evidence?id=${activeEvent?.rawEventId}`)}
            onOpenTrace={() => navigate(`/events/${activeEvent?.eventId}/trace`)}
            onOpenUes={() => navigate(`/events/${activeEvent?.eventId}`)}
          />

          {showFailureSim && <FailureSimulation />}
        </div>

        {/* Stage Detail Drawer */}
        <StageDetailDrawer
          nodeId={selectedNodeId}
          event={activeEvent}
          onClose={() => setSelectedNodeId(null)}
          onViewRaw={() => navigate(`/raw-evidence?id=${activeEvent?.rawEventId}`)}
        />

        {/* Fullscreen Presentation Mode HUD */}
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
