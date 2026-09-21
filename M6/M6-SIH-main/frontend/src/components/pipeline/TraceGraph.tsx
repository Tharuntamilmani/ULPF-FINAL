import React from 'react'
import { ProcessedPipelineEvent } from '../../api/pipelineService'
import { Copy, Check } from 'lucide-react'
import toast from 'react-hot-toast'

interface TraceGraphProps {
  event: ProcessedPipelineEvent
  onViewRaw?: () => void
}

export function TraceGraph({ event, onViewRaw }: TraceGraphProps) {
  const [copied, setCopied] = React.useState(false)

  const handleCopyHash = () => {
    navigator.clipboard.writeText(event.rawHash)
    setCopied(true)
    toast.success('SHA-256 hash copied')
    setTimeout(() => setCopied(false), 2000)
  }

  const stages = [
    {
      stage: 'RAW EVENT',
      title: `raw-${event.rawEventId.slice(0, 8)}`,
      detail: `MinIO Immutable Vault • SHA-256: ${event.rawHash.slice(0, 28)}...`,
      metadata: `s3://ulpf-raw-vault/raw/${event.tenantId}/${event.rawEventId}.dat`,
      action: onViewRaw ? 'View Raw Payload' : undefined,
    },
    {
      stage: 'EVENT ID',
      title: event.eventId,
      detail: 'Gateway Security Perimeter • Token Authentication & Anti-Spoofing Validated',
      metadata: `Port :18080 • Tenant: ${event.tenantId}`,
    },
    {
      stage: 'PARSER',
      title: event.stages.m2.parserId || 'fortigate-syslog-v1',
      detail: 'M2 Parser Engine • Grammar extraction & field normalization',
      metadata: `Port :18082 • Latency: ${event.stages.m2.latencyMs.toFixed(1)}ms`,
    },
    {
      stage: 'NORMALIZATION',
      title: 'Canonical UES v1.0.0',
      detail: 'M3 Normalizer • Canonical schema synthesis conforming to UES specification',
      metadata: `Port :18083 • Latency: ${event.stages.m3.latencyMs.toFixed(1)}ms`,
    },
    {
      stage: 'UES EVENT',
      title: 'VALIDATED CANONICAL EVENT',
      detail: 'Schema validator • RFC-8785 canonical hash computed & signed',
      metadata: `Enriched digest: ${event.enrichedDigest.slice(0, 24)}...`,
    },
    {
      stage: 'DESTINATION',
      title: 'OpenSearch SIEM & Cold Lake',
      detail: 'M5 Smart Router • Policy evaluation & multiplexed dispatch',
      metadata: 'Index: ulpf-events-v1 • Confirmed Delivery',
    },
  ]

  return (
    <div
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius)',
        padding: '14px 18px',
        maxWidth: 720,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          paddingBottom: 10,
          marginBottom: 14,
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div>
          <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
            Cryptographic Audit Trace for {event.eventId}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
            SHA-256: {event.rawHash}
          </div>
        </div>

        <button
          onClick={handleCopyHash}
          className="btn btn-secondary"
          style={{ padding: '3px 8px' }}
        >
          {copied ? <Check size={12} color="var(--green)" /> : <Copy size={12} />}
          <span>{copied ? 'Copied' : 'Copy Hash'}</span>
        </button>
      </div>

      {/* Lineage Flow Nodes */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        {stages.map((st, idx) => (
          <React.Fragment key={st.stage}>
            <div
              style={{
                background: 'var(--bg-elevated)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius)',
                padding: '10px 12px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 2 }}>
                  <span
                    style={{
                      fontSize: 10,
                      fontWeight: 700,
                      color: 'var(--accent)',
                      letterSpacing: '0.04em',
                    }}
                  >
                    {st.stage}
                  </span>
                  <span style={{ color: 'var(--border)' }}>•</span>
                  <span
                    className="font-mono"
                    style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}
                  >
                    {st.title}
                  </span>
                </div>

                <div style={{ fontSize: 11.5, color: 'var(--text-secondary)' }}>
                  {st.detail}
                </div>

                <div style={{ fontSize: 10.5, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginTop: 2 }}>
                  {st.metadata}
                </div>
              </div>

              {st.action && (
                <button
                  onClick={onViewRaw}
                  className="btn btn-secondary"
                  style={{ fontSize: 11, padding: '3px 8px' }}
                >
                  {st.action}
                </button>
              )}
            </div>

            {/* Down Connector */}
            {idx < stages.length - 1 && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  height: 20,
                  color: 'var(--text-muted)',
                  userSelect: 'none',
                }}
              >
                ↓
              </div>
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  )
}
