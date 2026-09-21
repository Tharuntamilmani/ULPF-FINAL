import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout, PageHeader } from '../components/layout/Layout'
import { getLiveEvents } from '../api/endpoints'
import { useQuery } from '@tanstack/react-query'
import { MOCK_UES_EVENTS, type MockUESEvent } from '../lib/mock/mockData'
import { FileCode2, Search, X, ChevronRight, ShieldCheck, AlertTriangle, Copy, Check } from 'lucide-react'
import toast from 'react-hot-toast'

const SEVERITY_COLOR: Record<string, string> = {
  critical: '#ef4444', high: '#f97316', medium: '#f59e0b', low: '#3b82f6', info: '#6b7280',
}

function SevBadge({ s }: { s: string }) {
  const dotColor = s === 'critical' || s === 'high' ? 'red' : s === 'medium' ? 'amber' : 'dim'
  const textColor = s === 'critical' || s === 'high' ? 'var(--red)' : s === 'medium' ? 'var(--amber)' : 'var(--text-muted)'
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 600, color: textColor, textTransform: 'uppercase' }}>
      <span className={`status-dot ${dotColor}`} />
      {s}
    </span>
  )
}

export function UESEventsPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [filterType, setFilterType] = useState('')
  const [filterSeverity, setFilterSeverity] = useState('')
  const [filterValidation, setFilterValidation] = useState('')
  const [previewId, setPreviewId] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const { data: liveData } = useQuery({
    queryKey: ['ues-events'],
    queryFn: () => getLiveEvents({ limit: 50 }).then(r => r.data).catch(() => null),
    staleTime: 10000,
  })

  const events: MockUESEvent[] =
    liveData?.events && liveData.events.length > 0
      ? liveData.events.map((e: any) => ({
          id: e.event?.id ?? 'live',
          timestamp: e.event?.timestamp ?? new Date().toISOString(),
          source: e.source?.hostname ?? 'live',
          vendor: e.observer?.vendor ?? 'Unknown',
          format: 'json',
          parser: e.parser?.id ?? 'unknown',
          parserVersion: e.parser?.version ?? '1.0',
          eventType: e.event?.type ?? 'unknown',
          action: e.event?.action ?? 'unknown',
          severity: e.event?.severity?.label ?? 'info',
          severityScore: e.event?.severity?.value ?? 0,
          outcome: e.event?.outcome ?? 'unknown',
          sourceIp: e.source?.ip ?? '0.0.0.0',
          destinationIp: e.destination?.ip ?? '0.0.0.0',
          protocol: e.network?.transport ?? 'unknown',
          validation: 'PASSED',
          processingTimeMs: 10,
          status: 'INDEXED',
          rawEventId: e.raw?.id ?? '',
          rawHash: e.raw?.sha256 ?? '',
        }))
      : MOCK_UES_EVENTS

  const filtered = events.filter(e => {
    if (search && !e.id.includes(search) && !e.sourceIp.includes(search) && !e.destinationIp.includes(search) && !e.eventType.includes(search)) return false
    if (filterType && e.eventType !== filterType) return false
    if (filterSeverity && e.severity !== filterSeverity) return false
    if (filterValidation && e.validation !== filterValidation) return false
    return true
  })

  const preview = previewId ? events.find(e => e.id === previewId) : null
  const types = [...new Set(events.map(e => e.eventType))]
  const hasFilters = search || filterType || filterSeverity || filterValidation

  const sampleUES = (ev: MockUESEvent) => ({
    event: { id: ev.id, timestamp: ev.timestamp, type: ev.eventType, action: ev.action, severity: { value: ev.severityScore, label: ev.severity }, outcome: ev.outcome },
    source: { ip: ev.sourceIp },
    destination: { ip: ev.destinationIp },
    network: { transport: ev.protocol },
    parser: { id: ev.parser, version: ev.parserVersion },
    raw: { id: ev.rawEventId, sha256: ev.rawHash },
    normalization: { schema: 'UES', version: '1.0.0', status: ev.validation },
  })

  const handleCopy = (ev: MockUESEvent) => {
    navigator.clipboard.writeText(JSON.stringify(sampleUES(ev), null, 2))
    setCopied(true)
    toast.success('UES JSON copied')
    setTimeout(() => setCopied(false), 1500)
  }

  const sel: React.CSSProperties = { padding: '6px 10px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 5, color: 'var(--text-muted)', fontSize: 12, outline: 'none' }

  return (
    <Layout>
      <PageHeader
        title="UES Events"
        subtitle="Universal Event Schema — standardized ULPF output. Every event is parsed, normalized, and validated."
        badge={
          <span style={{ padding: '2px 8px', background: 'rgba(139,92,246,0.15)', border: '1px solid var(--purple)', borderRadius: 4, fontSize: 10, fontWeight: 700, color: 'var(--purple)' }}>
            UES v1.0.0
          </span>
        }
      />

      {/* The pipeline reminder strip */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16, fontSize: 11, color: 'var(--text-dim)', padding: '8px 14px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 6 }}>
        {['RAW LOG', 'INGEST', 'PARSE', 'NORMALIZE', 'VALIDATE', '→ UES EVENT'].map((s, i, arr) => (
          <React.Fragment key={s}>
            <span style={{ color: i === arr.length - 1 ? 'var(--purple)' : 'var(--text-dim)', fontWeight: i === arr.length - 1 ? 700 : 400 }}>{s}</span>
            {i < arr.length - 1 && <span style={{ color: 'var(--text-dim)', opacity: 0.4 }}>→</span>}
          </React.Fragment>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 16 }}>
        {/* Table */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {/* Filters */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 12, padding: '10px 12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
            <div style={{ position: 'relative' }}>
              <Search size={12} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="ID, IP, type…" style={{ ...sel, paddingLeft: 26, width: 180 }} />
            </div>
            <select value={filterType} onChange={e => setFilterType(e.target.value)} style={sel}>
              <option value="">All Types</option>
              {types.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
            <select value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)} style={sel}>
              <option value="">All Severities</option>
              {['critical', 'high', 'medium', 'low', 'info'].map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            <select value={filterValidation} onChange={e => setFilterValidation(e.target.value)} style={sel}>
              <option value="">All Validation</option>
              <option value="PASSED">PASSED</option>
              <option value="FAILED">FAILED</option>
            </select>
            {hasFilters && (
              <button onClick={() => { setSearch(''); setFilterType(''); setFilterSeverity(''); setFilterValidation('') }}
                style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 8px', background: 'transparent', border: '1px solid var(--border)', borderRadius: 5, color: 'var(--text-dim)', fontSize: 12, cursor: 'pointer' }}>
                <X size={11} /> Clear
              </button>
            )}
            <span style={{ marginLeft: 'auto', fontSize: 11, color: 'var(--text-dim)', alignSelf: 'center' }}>{filtered.length} events</span>
          </div>

          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
                  {['Event ID', 'Timestamp', 'Kind / Type', 'Action', 'Outcome', 'Severity', 'Src IP', 'Dst IP', 'Protocol', 'Parser', 'Validation', ''].map(h => (
                    <th key={h} style={{ padding: '8px 10px', textAlign: 'left', fontSize: 10, fontWeight: 700, color: 'var(--text-dim)', letterSpacing: '0.05em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.length === 0 ? (
                  <tr><td colSpan={12} style={{ padding: 40, textAlign: 'center', color: 'var(--text-dim)' }}>No UES events match filters</td></tr>
                ) : filtered.map((ev, idx) => (
                  <tr
                    key={ev.id}
                    style={{
                      borderBottom: idx < filtered.length - 1 ? '1px solid var(--border)' : 'none',
                      background: previewId === ev.id ? 'var(--bg-elevated)' : 'transparent',
                      cursor: 'pointer', transition: 'background 0.1s',
                    }}
                    onMouseEnter={e => { if (previewId !== ev.id) e.currentTarget.style.background = 'var(--bg-hover)' }}
                    onMouseLeave={e => { if (previewId !== ev.id) e.currentTarget.style.background = 'transparent' }}
                    onClick={() => setPreviewId(ev.id === previewId ? null : ev.id)}
                  >
                    <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--purple)' }}>{ev.id.substring(0, 14)}</td>
                    <td style={{ padding: '7px 10px', color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>{new Date(ev.timestamp).toLocaleTimeString()}</td>
                    <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--text-muted)' }}>{ev.eventType}</td>
                    <td style={{ padding: '7px 10px', color: 'var(--text-muted)' }}>{ev.action}</td>
                    <td style={{ padding: '7px 10px', color: ev.outcome === 'success' ? 'var(--green)' : ev.outcome === 'failure' ? 'var(--red)' : 'var(--text-dim)', fontWeight: 600, fontSize: 11 }}>{ev.outcome}</td>
                    <td style={{ padding: '7px 10px' }}><SevBadge s={ev.severity} /></td>
                    <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--text-muted)' }}>{ev.sourceIp}</td>
                    <td style={{ padding: '7px 10px', fontFamily: 'var(--font-mono)', fontSize: 10.5, color: 'var(--text-muted)' }}>{ev.destinationIp}</td>
                    <td style={{ padding: '7px 10px', color: 'var(--text-dim)', fontSize: 11 }}>{ev.protocol}</td>
                    <td style={{ padding: '7px 10px', color: 'var(--text-dim)', fontSize: 10.5 }}>{ev.parser}</td>
                    <td style={{ padding: '7px 10px' }}>
                      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, color: ev.validation === 'PASSED' ? 'var(--green)' : 'var(--red)', fontWeight: 600 }}>
                        {ev.validation === 'PASSED' ? <ShieldCheck size={11} /> : <AlertTriangle size={11} />}
                        {ev.validation}
                      </span>
                    </td>
                    <td style={{ padding: '7px 10px' }}><ChevronRight size={13} color="var(--text-dim)" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* JSON Preview Panel */}
        {preview && (
          <div style={{ width: 340, flexShrink: 0 }}>
            <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--purple)', borderRadius: 8, overflow: 'hidden', position: 'sticky', top: 0 }}>
              <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <FileCode2 size={13} color="var(--purple)" />
                  <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--purple)' }}>UES JSON Preview</span>
                </div>
                <div style={{ display: 'flex', gap: 6 }}>
                  <button
                    onClick={() => handleCopy(preview)}
                    style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-dim)', fontSize: 11, cursor: 'pointer' }}
                  >
                    {copied ? <Check size={11} /> : <Copy size={11} />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                  <button
                    onClick={() => navigate(`/events/${preview.id}`)}
                    style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '4px 8px', background: 'rgba(139,92,246,0.12)', border: '1px solid var(--purple)', borderRadius: 4, color: 'var(--purple)', fontSize: 11, cursor: 'pointer', fontWeight: 600 }}
                  >
                    Full Detail
                  </button>
                </div>
              </div>
              <pre style={{ margin: 0, padding: '12px 14px', fontFamily: 'var(--font-mono)', fontSize: 11, color: '#c9d1d9', background: '#0d1017', overflowY: 'auto', maxHeight: '70vh', lineHeight: 1.6 }}>
                {JSON.stringify(sampleUES(preview), null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
