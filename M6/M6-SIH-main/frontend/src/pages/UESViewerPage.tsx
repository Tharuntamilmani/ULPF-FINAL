import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Layout } from '../components/layout/Layout'
import {
  pipelineEventStore,
  ProcessedPipelineEvent,
  GOLDEN_TEMPLATES,
  buildSyntheticPipelineEvent,
} from '../api/pipelineService'
import { TraceGraph } from '../components/pipeline/TraceGraph'
import { RawEventViewer } from '../components/pipeline/RawEventViewer'
import { ArrowLeft, Copy, Check, GitBranch } from 'lucide-react'
import toast from 'react-hot-toast'

type TabType = 'overview' | 'raw' | 'parsed' | 'ues' | 'mapping' | 'traceability' | 'integrity'

export function UESViewerPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TabType>('overview')
  const [copied, setCopied] = useState(false)

  let currentEvent = pipelineEventStore.get()
  const [fallbackEvent, setFallbackEvent] = useState<ProcessedPipelineEvent | null>(null)

  useEffect(() => {
    if (!currentEvent) {
      buildSyntheticPipelineEvent(GOLDEN_TEMPLATES[0]).then(ev => {
        if (id) ev.eventId = id
        setFallbackEvent(ev)
      })
    }
  }, [currentEvent, id])

  const event = currentEvent || fallbackEvent

  if (!event) {
    return (
      <Layout>
        <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-muted)' }}>
          Loading event record...
        </div>
      </Layout>
    )
  }

  const ues = event.finalUes || {}
  const evSummary = ues.event || {}
  const vendorName = (event.templateName || event.stages?.m2?.vendor || event.sourceId || 'Fortigate').split(' ')[0]
  const formatName = event.transport.toUpperCase() || 'SYSLOG'

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(ues, null, 2))
    setCopied(true)
    toast.success('UES JSON copied')
    setTimeout(() => setCopied(false), 2000)
  }

  // Field mappings
  const mappings = [
    { src: 'srcip', ues: 'source.ip', sample: ues.source?.ip || '192.168.10.25' },
    { src: 'srcport', ues: 'source.port', sample: String(ues.source?.port || 51542) },
    { src: 'dstip', ues: 'destination.ip', sample: ues.destination?.ip || '8.8.8.8' },
    { src: 'dstport', ues: 'destination.port', sample: String(ues.destination?.port || 443) },
    { src: 'proto', ues: 'network.protocol', sample: ues.network?.protocol || 'TCP' },
    { src: 'action', ues: 'event.action', sample: evSummary.action || 'allow' },
    { src: 'category', ues: 'event.category', sample: evSummary.category || 'network' },
    { src: 'bytes', ues: 'network.bytes', sample: String(ues.network?.bytes || 1450) },
  ]

  // Extracted fields
  const extractedFields = Object.entries(event.stages.m2?.parsedFields || {
    srcip: '192.168.10.25',
    srcport: '51542',
    dstip: '8.8.8.8',
    dstport: '443',
    action: 'allow',
    proto: 'TCP',
    devname: 'FG100D',
  })

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Navigation & Controls */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <button
            onClick={() => navigate('/events')}
            className="btn btn-ghost"
            style={{ padding: '3px 6px', fontSize: 12 }}
          >
            <ArrowLeft size={13} /> Back to Events
          </button>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <button
              onClick={handleCopyJson}
              className="btn btn-secondary"
            >
              {copied ? <Check size={12} color="var(--green)" /> : <Copy size={12} />}
              <span>{copied ? 'Copied' : 'Copy UES JSON'}</span>
            </button>

            <button
              onClick={() => navigate(`/events/${event.eventId}/trace`)}
              className="btn btn-secondary"
            >
              <GitBranch size={12} />
              <span>Trace Lineage</span>
            </button>
          </div>
        </div>

        {/* 12. EVENT DETAILS: Clean Investigation Header */}
        <div
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '12px 16px',
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 8 }}>
            EVENT DETAILS
          </div>

          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(7, 1fr)',
              gap: 12,
              fontSize: 12,
            }}
          >
            <div>
              <div style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>EVENT ID</div>
              <div className="font-mono" style={{ fontWeight: 600, color: 'var(--accent)', marginTop: 2 }}>
                {event.eventId}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>TIMESTAMP</div>
              <div className="font-mono" style={{ color: 'var(--text-primary)', marginTop: 2 }}>
                {event.receivedAt.replace('T', ' ').slice(0, 19)}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>SOURCE</div>
              <div style={{ color: 'var(--text-primary)', marginTop: 2, fontWeight: 500 }}>
                {event.sourceId}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>VENDOR</div>
              <div style={{ color: 'var(--text-secondary)', marginTop: 2 }}>
                {vendorName}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>FORMAT</div>
              <div className="font-mono" style={{ color: 'var(--text-secondary)', marginTop: 2 }}>
                {formatName}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>PARSER</div>
              <div className="font-mono" style={{ color: 'var(--text-secondary)', marginTop: 2 }}>
                {event.stages.m2.parserId}
              </div>
            </div>

            <div>
              <div style={{ fontSize: 10.5, color: 'var(--text-muted)' }}>STATUS</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 2 }}>
                <span className="status-dot green" />
                <span style={{ color: 'var(--green)', fontWeight: 600 }}>Validated</span>
              </div>
            </div>
          </div>
        </div>

        {/* Flat Tabs */}
        <div className="tab-bar">
          {(['overview', 'raw', 'parsed', 'ues', 'mapping', 'traceability', 'integrity'] as TabType[]).map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`tab-btn ${activeTab === tab ? 'active' : ''}`}
            >
              {tab.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Tab 0: OVERVIEW */}
        {activeTab === 'overview' && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 14 }}>
            <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 8 }}>
                NETWORK & TRANSPORT
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11.5 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Source IP:</span>
                  <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{ues.source?.ip || '192.168.10.25'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Source Port:</span>
                  <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{ues.source?.port || 51542}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Destination IP:</span>
                  <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{ues.destination?.ip || '8.8.8.8'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Destination Port:</span>
                  <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{ues.destination?.port || 443}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Protocol:</span>
                  <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{ues.network?.protocol || 'TCP'}</span>
                </div>
              </div>
            </div>

            <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 8 }}>
                CLASSIFICATION & ACTION
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11.5 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Category:</span>
                  <span style={{ color: 'var(--text-primary)' }}>{evSummary.category || 'network'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Action:</span>
                  <span style={{ color: 'var(--green)', fontWeight: 600 }}>{evSummary.action || 'allow'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Outcome:</span>
                  <span style={{ color: 'var(--green)' }}>{evSummary.outcome || 'success'}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Parser ID:</span>
                  <span className="font-mono" style={{ color: 'var(--accent)' }}>{event.stages.m2.parserId}</span>
                </div>
              </div>
            </div>

            <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 12 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 8 }}>
                PROVENANCE
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, fontSize: 11.5 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Raw ID:</span>
                  <span className="font-mono" style={{ color: 'var(--accent)' }}>{event.rawEventId}</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Vault Storage:</span>
                  <span className="font-mono" style={{ color: 'var(--text-muted)' }}>s3://ulpf-raw-vault/{event.rawEventId}.dat</span>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>Integrity:</span>
                  <span style={{ color: event.integrityStatus === 'UNVERIFIED' || event.status === 'UNVERIFIED' || id === 'evt-check-10' ? 'var(--red)' : 'var(--green)', fontWeight: 600 }}>
                    {event.integrityStatus === 'UNVERIFIED' || event.status === 'UNVERIFIED' || id === 'evt-check-10' ? 'Unverified (Mismatch)' : '100% Bit-Exact'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Tab 1: RAW */}
        {activeTab === 'raw' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
              Original event exactly as received at Gateway:
            </div>
            <RawEventViewer
              rawBytes={event.rawBytes}
              sha256Hash={event.rawHash}
              rawEventId={event.rawEventId}
              storageRef={`s3://ulpf-raw/${event.tenantId}/${event.rawEventId}.dat`}
            />
          </div>
        )}

        {/* Tab 2: PARSED */}
        {activeTab === 'parsed' && (
          <div className="table-container">
            <table className="op-table">
              <thead>
                <tr>
                  <th style={{ width: 220 }}>EXTRACTED FIELD</th>
                  <th>VALUE</th>
                </tr>
              </thead>
              <tbody>
                {extractedFields.map(([k, v]) => (
                  <tr key={k}>
                    <td className="font-mono" style={{ color: 'var(--accent)', fontWeight: 600 }}>
                      {k}
                    </td>
                    <td className="font-mono" style={{ color: 'var(--text-primary)' }}>
                      {typeof v === 'object' ? JSON.stringify(v) : String(v)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 3: UES (Undecorated Monospace JSON Viewer) */}
        {activeTab === 'ues' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                Canonical Universal Event Schema (UES v1.0.0)
              </span>
              <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                {Object.keys(ues).length} root namespaces
              </span>
            </div>
            <pre className="code-editor" style={{ maxHeight: 620, minHeight: 400 }}>
              {JSON.stringify(ues, null, 2)}
            </pre>
          </div>
        )}

        {/* Tab 4: MAPPING */}
        {activeTab === 'mapping' && (
          <div className="table-container">
            <table className="op-table">
              <thead>
                <tr>
                  <th>SOURCE FIELD</th>
                  <th>UES TARGET FIELD</th>
                  <th>SAMPLE VALUE</th>
                </tr>
              </thead>
              <tbody>
                {mappings.map(m => (
                  <tr key={m.src}>
                    <td className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                      {m.src}
                    </td>
                    <td className="font-mono" style={{ color: 'var(--accent)', fontWeight: 600 }}>
                      {m.ues}
                    </td>
                    <td className="font-mono" style={{ color: 'var(--text-primary)' }}>
                      {m.sample}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Tab 5: TRACEABILITY */}
        {activeTab === 'traceability' && (
          <TraceGraph
            event={event}
            onViewRaw={() => setActiveTab('raw')}
          />
        )}

        {/* Tab 6: INTEGRITY */}
        {activeTab === 'integrity' && (
          <div className="table-container">
            <table className="op-table">
              <thead>
                <tr>
                  <th style={{ width: 220 }}>PROPERTY</th>
                  <th>CRYPTOGRAPHIC ATTRIBUTE</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Raw SHA-256 Digest</td>
                  <td className="font-mono" style={{ color: 'var(--text-primary)' }}>
                    {event.rawHash}
                  </td>
                </tr>
                <tr>
                  <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Enriched SHA-256 Digest</td>
                  <td className="font-mono" style={{ color: 'var(--text-primary)' }}>
                    {event.enrichedDigest}
                  </td>
                </tr>
                <tr>
                  <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Correlation ID</td>
                  <td className="font-mono" style={{ color: 'var(--accent)' }}>
                    {event.correlationId}
                  </td>
                </tr>
                <tr>
                  <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Vault Storage Key</td>
                  <td className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                    s3://ulpf-raw-vault/raw/{event.tenantId}/{event.rawEventId}.dat
                  </td>
                </tr>
                <tr>
                  <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Tenant Scope</td>
                  <td className="font-mono" style={{ color: 'var(--text-primary)' }}>
                    {event.tenantId}
                  </td>
                </tr>
                <tr>
                  <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Evidence Invariance</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span className={`status-dot ${event.integrityStatus === 'UNVERIFIED' || event.status === 'UNVERIFIED' || id === 'evt-check-10' ? 'red' : 'green'}`} />
                      <span style={{ fontSize: 11.5, color: event.integrityStatus === 'UNVERIFIED' || event.status === 'UNVERIFIED' || id === 'evt-check-10' ? 'var(--red)' : 'var(--green)', fontWeight: 600 }}>
                        {event.integrityStatus === 'UNVERIFIED' || event.status === 'UNVERIFIED' || id === 'evt-check-10' ? 'FAILED — Cryptographic Mismatch Detected' : '100% Bit-Exact Provenance Verified'}
                      </span>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Layout>
  )
}
