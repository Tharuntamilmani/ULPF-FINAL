import React from 'react'
import { ProcessedPipelineEvent } from '../../api/pipelineService'
import { X, CheckCircle2, ArrowRight, ShieldCheck, FileText, GitBranch, Key } from 'lucide-react'

interface PresentationModeProps {
  isOpen: boolean
  onClose: () => void
  activeEvent: ProcessedPipelineEvent | null
  onOpenUes?: () => void
  onOpenTrace?: () => void
  onOpenRaw?: () => void
}

export function PresentationMode({
  isOpen,
  onClose,
  activeEvent,
  onOpenUes,
  onOpenTrace,
  onOpenRaw,
}: PresentationModeProps) {
  if (!isOpen) return null

  const stages = [
    { label: 'Gateway', role: 'Perimeter Auth', status: '✓' },
    { label: 'M1 Ingestion', role: 'Raw Vault', status: '✓' },
    { label: 'Kafka', role: 'Stream Broker', status: '✓' },
    { label: 'M2 Parser', role: 'Vendor Match', status: '✓' },
    { label: 'M3 Normalizer', role: 'Canonical UES', status: '✓' },
    { label: 'M4 Enrichment', role: 'Threat Context', status: '✓' },
    { label: 'M5 Router', role: 'Policy Dispatch', status: '✓' },
    { label: 'OpenSearch', role: 'SIEM Store', status: '✓' },
  ]

  return (
    <div className="presentation-container">
      {/* Header Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 40 }}>
        <div>
          <div style={{ fontSize: 13, fontWeight: 800, color: 'var(--accent)', letterSpacing: '0.1em' }}>
            ULPF PRESENTATION DISPLAY
          </div>
          <h1 style={{ fontSize: 32, fontWeight: 900, color: '#f8fafc', letterSpacing: '-0.02em', marginTop: 4 }}>
            Universal Log Pre-processing Framework
          </h1>
          <div style={{ fontSize: 15, color: 'var(--text-muted)', marginTop: 4 }}>
            Universal Security Event Processing & Cryptographic Traceability Platform
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 20 }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 10,
              padding: '8px 16px',
              background: 'rgba(16, 185, 129, 0.15)',
              border: '1px solid var(--green)',
              borderRadius: 8,
              color: 'var(--green)',
              fontSize: 14,
              fontWeight: 800,
            }}
          >
            <span className="status-dot green" />
            SYSTEM OPERATIONAL
          </div>

          <button
            onClick={onClose}
            style={{
              padding: '10px 16px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 8,
              color: 'var(--text-primary)',
              fontSize: 14,
              fontWeight: 700,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              cursor: 'pointer',
            }}
          >
            <X size={18} /> EXIT FULLSCREEN
          </button>
        </div>
      </div>

      {/* Main Focus Card */}
      <div
        style={{
          flex: 1,
          background: 'radial-gradient(ellipse at center, #161e30 0%, #0c101a 100%)',
          border: '1px solid #2e3c59',
          borderRadius: 16,
          padding: '48px 40px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          boxShadow: '0 24px 60px rgba(0,0,0,0.7)',
        }}
      >
        {activeEvent ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 36, textAlign: 'center' }}>
            {/* Event Identifier Banner */}
            <div>
              <div style={{ fontSize: 16, fontWeight: 800, color: 'var(--cyan)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                ACTIVE LIVE SECURITY EVENT
              </div>
              <div style={{ fontSize: 40, fontWeight: 900, color: '#ffffff', fontFamily: 'var(--font-mono)', marginTop: 8 }}>
                {activeEvent.eventId}
              </div>
              <div style={{ fontSize: 18, color: 'var(--text-muted)', marginTop: 8 }}>
                Tenant: <strong style={{ color: '#fff' }}>{activeEvent.tenantId}</strong> • Source: <strong style={{ color: '#fff' }}>{activeEvent.sourceId}</strong>
              </div>
            </div>

            {/* Horizontal Enlarged Flow */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 12, flexWrap: 'wrap' }}>
              {stages.map((st, i) => (
                <React.Fragment key={i}>
                  <div
                    style={{
                      background: 'rgba(19, 23, 34, 0.85)',
                      border: '2px solid var(--accent)',
                      borderRadius: 12,
                      padding: '20px 24px',
                      minWidth: 140,
                      boxShadow: '0 0 20px var(--accent-glow)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, color: 'var(--green)', fontSize: 18, fontWeight: 800 }}>
                      <CheckCircle2 size={20} />
                      {st.status}
                    </div>
                    <div style={{ fontSize: 16, fontWeight: 800, color: '#f8fafc', marginTop: 8 }}>
                      {st.label}
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>
                      {st.role}
                    </div>
                  </div>

                  {i < stages.length - 1 && (
                    <ArrowRight size={24} color="var(--accent)" />
                  )}
                </React.Fragment>
              ))}
            </div>

            {/* Status & Forensic Checksum */}
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 12 }}>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10, padding: '8px 24px', background: 'rgba(16, 185, 129, 0.2)', border: '1px solid var(--green)', borderRadius: 30, color: 'var(--green)', fontSize: 16, fontWeight: 800 }}>
                <CheckCircle2 size={20} />
                STATUS: PROCESSED & VERIFIED
              </div>
              <div style={{ fontFamily: 'var(--font-mono)', fontSize: 14, color: 'var(--cyan)' }}>
                Authoritative Raw SHA-256: {activeEvent.rawHash}
              </div>
            </div>

            {/* Quick Large CTA Buttons */}
            <div style={{ display: 'flex', justifyContent: 'center', gap: 20, marginTop: 12 }}>
              <button
                onClick={onOpenUes}
                style={{
                  padding: '14px 28px',
                  background: 'var(--bg-elevated)',
                  border: '2px solid var(--accent)',
                  borderRadius: 10,
                  color: 'var(--accent)',
                  fontSize: 16,
                  fontWeight: 800,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  cursor: 'pointer',
                }}
              >
                <FileText size={20} />
                VIEW UES
              </button>

              <button
                onClick={onOpenTrace}
                style={{
                  padding: '14px 28px',
                  background: 'var(--bg-elevated)',
                  border: '2px solid #a855f7',
                  borderRadius: 10,
                  color: '#c4b5fd',
                  fontSize: 16,
                  fontWeight: 800,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  cursor: 'pointer',
                }}
              >
                <GitBranch size={20} />
                TRACE EVENT
              </button>

              <button
                onClick={onOpenRaw}
                style={{
                  padding: '14px 28px',
                  background: 'var(--bg-elevated)',
                  border: '2px solid var(--cyan)',
                  borderRadius: 10,
                  color: 'var(--cyan)',
                  fontSize: 16,
                  fontWeight: 800,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  cursor: 'pointer',
                }}
              >
                <Key size={20} />
                VIEW RAW EVIDENCE
              </button>
            </div>
          </div>
        ) : (
          <div style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
            <div style={{ fontSize: 24, fontWeight: 700, color: '#f8fafc', marginBottom: 10 }}>
              WAITING FOR EVENT DISPATCH
            </div>
            <div style={{ fontSize: 16 }}>
              Dispatch a security event from the dashboard to display the live projector transit.
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
