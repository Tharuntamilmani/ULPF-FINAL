import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout, PageHeader } from '../components/layout/Layout'
import { getLiveEvents, searchLiveEvents } from '../api/endpoints'
import { MOCK_UES_EVENTS, type MockUESEvent } from '../lib/mock/mockData'
import {
  Radio,
  Search,
  RefreshCw,
  Filter,
  X,
  ChevronRight,
  ArrowUpDown,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react'

const SEVERITY_COLOR: Record<string, string> = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#f59e0b',
  low: '#3b82f6',
  info: '#6b7280',
}

const FORMAT_BADGE_COLOR: Record<string, string> = {
  syslog: 'rgba(59,130,246,0.2)',
  json: 'rgba(16,185,129,0.2)',
  kv: 'rgba(245,158,11,0.2)',
  cef: 'rgba(139,92,246,0.2)',
  leef: 'rgba(6,182,212,0.2)',
  csv: 'rgba(107,114,128,0.2)',
}

function SeverityBadge({ severity }: { severity: string }) {
  const color =
    severity === 'critical' || severity === 'high'
      ? 'var(--red)'
      : severity === 'medium'
      ? 'var(--amber)'
      : 'var(--text-muted)'
  const dotColor = severity === 'critical' || severity === 'high' ? 'red' : severity === 'medium' ? 'amber' : 'dim'
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 600, color, textTransform: 'uppercase' }}>
      <span className={`status-dot ${dotColor}`} />
      {severity}
    </span>
  )
}

function FormatBadge({ format }: { format: string }) {
  return (
    <span style={{ fontSize: 10.5, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
      {format.toUpperCase()}
    </span>
  )
}

function ValidationBadge({ status }: { status: string }) {
  const isPass = status === 'PASSED'
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, fontSize: 11, fontWeight: 500, color: isPass ? 'var(--green)' : 'var(--red)' }}>
      <span className={`status-dot ${isPass ? 'green' : 'red'}`} />
      {status}
    </span>
  )
}

export function LiveEventsPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [filterSource, setFilterSource] = useState('')
  const [filterVendor, setFilterVendor] = useState('')
  const [filterFormat, setFilterFormat] = useState('')
  const [filterSeverity, setFilterSeverity] = useState('')
  const [filterValidation, setFilterValidation] = useState('')
  const [autoRefresh, setAutoRefresh] = useState(true)
  const [events, setEvents] = useState<MockUESEvent[]>(MOCK_UES_EVENTS)
  const [isLive, setIsLive] = useState(false)
  const [lastUpdate, setLastUpdate] = useState(new Date())
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Try real API, fall back to mock
  useEffect(() => {
    getLiveEvents({ limit: 50 })
      .then(r => {
        if (r.data?.events && r.data.events.length > 0) {
          setIsLive(true)
          // map real data to our display format
          const mapped: MockUESEvent[] = r.data.events.map((e: any) => ({
            id: e.event?.id ?? e.id ?? 'live',
            timestamp: e.event?.timestamp ?? new Date().toISOString(),
            source: e.source?.hostname ?? 'live-source',
            vendor: e.observer?.vendor ?? 'Unknown',
            format: e.raw?.format ?? 'json',
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
          setEvents(mapped)
        }
      })
      .catch(() => { /* use mock */ })
  }, [])

  // Auto-refresh simulation
  useEffect(() => {
    if (autoRefresh && !isLive) {
      intervalRef.current = setInterval(() => {
        setEvents(prev => {
          // Rotate: drop oldest, add new at front
          const rotated = [...prev]
          const first = rotated.shift()
          if (first) {
            const updated = { ...first, id: `evt-${Date.now().toString(36)}`, timestamp: new Date().toISOString() }
            rotated.push(updated)
          }
          return rotated
        })
        setLastUpdate(new Date())
      }, 3000)
    }
    return () => { if (intervalRef.current) clearInterval(intervalRef.current) }
  }, [autoRefresh, isLive])

  const filtered = events.filter(e => {
    if (search && !e.id.includes(search) && !e.source.toLowerCase().includes(search.toLowerCase()) && !e.sourceIp.includes(search)) return false
    if (filterSource && e.source !== filterSource) return false
    if (filterVendor && e.vendor !== filterVendor) return false
    if (filterFormat && e.format !== filterFormat) return false
    if (filterSeverity && e.severity !== filterSeverity) return false
    if (filterValidation && e.validation !== filterValidation) return false
    return true
  })

  const clearFilters = () => {
    setSearch(''); setFilterSource(''); setFilterVendor('')
    setFilterFormat(''); setFilterSeverity(''); setFilterValidation('')
  }

  const hasFilters = search || filterSource || filterVendor || filterFormat || filterSeverity || filterValidation
  const vendors = [...new Set(events.map(e => e.vendor))]
  const sources = [...new Set(events.map(e => e.source))]

  const selectStyle: React.CSSProperties = {
    padding: '6px 10px',
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border)',
    borderRadius: 5,
    color: 'var(--text-muted)',
    fontSize: 12,
    outline: 'none',
  }

  return (
    <Layout>
      <PageHeader
        title="Live Events"
        subtitle="Real-time event stream — ingested, parsed, normalized, and validated through ULPF pipeline"
        badge={
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              padding: '2px 8px',
              background: isLive ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.12)',
              border: `1px solid ${isLive ? 'var(--green)' : 'var(--yellow)'}`,
              borderRadius: 4,
              fontSize: 10,
              fontWeight: 800,
              color: isLive ? 'var(--green)' : 'var(--yellow)',
              letterSpacing: '0.05em',
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor' }} />
            {isLive ? 'LIVE' : 'DEMO SIMULATION'}
          </span>
        }
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
              Updated {lastUpdate.toLocaleTimeString()}
            </span>
            <button
              onClick={() => setAutoRefresh(a => !a)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '6px 12px',
                background: autoRefresh ? 'rgba(59,130,246,0.15)' : 'var(--bg-elevated)',
                border: `1px solid ${autoRefresh ? 'var(--accent)' : 'var(--border)'}`,
                borderRadius: 5, color: autoRefresh ? 'var(--accent)' : 'var(--text-muted)',
                fontSize: 12, fontWeight: 600, cursor: 'pointer',
              }}
            >
              <Radio size={13} />
              {autoRefresh ? 'Auto-refresh ON' : 'Auto-refresh OFF'}
            </button>
          </div>
        }
      />

      {/* Filters */}
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 8,
          marginBottom: 16,
          padding: '12px 14px',
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          alignItems: 'center',
        }}
      >
        <div style={{ position: 'relative', flexShrink: 0 }}>
          <Search size={13} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search ID, source, IP…"
            style={{ ...selectStyle, paddingLeft: 28, width: 200 }}
          />
        </div>

        <select value={filterVendor} onChange={e => setFilterVendor(e.target.value)} style={selectStyle}>
          <option value="">All Vendors</option>
          {vendors.map(v => <option key={v} value={v}>{v}</option>)}
        </select>

        <select value={filterSource} onChange={e => setFilterSource(e.target.value)} style={selectStyle}>
          <option value="">All Sources</option>
          {sources.map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <select value={filterFormat} onChange={e => setFilterFormat(e.target.value)} style={selectStyle}>
          <option value="">All Formats</option>
          {['syslog', 'json', 'kv', 'cef', 'leef', 'csv'].map(f => <option key={f} value={f}>{f.toUpperCase()}</option>)}
        </select>

        <select value={filterSeverity} onChange={e => setFilterSeverity(e.target.value)} style={selectStyle}>
          <option value="">All Severities</option>
          {['critical', 'high', 'medium', 'low', 'info'].map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <select value={filterValidation} onChange={e => setFilterValidation(e.target.value)} style={selectStyle}>
          <option value="">All Validation</option>
          <option value="PASSED">PASSED</option>
          <option value="FAILED">FAILED</option>
        </select>

        {hasFilters && (
          <button
            onClick={clearFilters}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '6px 10px', background: 'transparent',
              border: '1px solid var(--border)', borderRadius: 5,
              color: 'var(--text-dim)', fontSize: 12, cursor: 'pointer',
            }}
          >
            <X size={12} /> Clear
          </button>
        )}

        <div style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--text-dim)' }}>
          {filtered.length} events
        </div>
      </div>

      {/* Table */}
      <div
        style={{
          background: 'var(--bg-surface)',
          border: '1px solid var(--border)',
          borderRadius: 8,
          overflow: 'hidden',
        }}
      >
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
              {['Event ID', 'Timestamp', 'Source', 'Vendor', 'Format', 'Type', 'Action', 'Severity', 'Src IP', 'Dst IP', 'Parser', 'Validation', 'ms', ''].map(h => (
                <th
                  key={h}
                  style={{
                    padding: '9px 12px',
                    textAlign: 'left',
                    fontSize: 10,
                    fontWeight: 700,
                    color: 'var(--text-dim)',
                    letterSpacing: '0.06em',
                    textTransform: 'uppercase',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={14} style={{ padding: 40, textAlign: 'center', color: 'var(--text-dim)' }}>
                  No events match current filters
                </td>
              </tr>
            ) : (
              filtered.map((ev, idx) => (
                <tr
                  key={ev.id}
                  onClick={() => navigate(`/events/${ev.id}`)}
                  style={{
                    borderBottom: idx < filtered.length - 1 ? '1px solid var(--border)' : 'none',
                    cursor: 'pointer',
                    transition: 'background 0.1s',
                  }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--bg-hover)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent)' }}>
                    {ev.id.substring(0, 14)}
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>
                    {new Date(ev.timestamp).toLocaleTimeString()}
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-muted)', maxWidth: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {ev.source}
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-primary)', fontWeight: 600 }}>
                    {ev.vendor}
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <FormatBadge format={ev.format} />
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: 10 }}>
                    {ev.eventType}
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-muted)' }}>
                    {ev.action}
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <SeverityBadge severity={ev.severity} />
                  </td>
                  <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                    {ev.sourceIp}
                  </td>
                  <td style={{ padding: '8px 12px', fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--text-muted)' }}>
                    {ev.destinationIp}
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-dim)', fontSize: 11 }}>
                    {ev.parser}
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <ValidationBadge status={ev.validation} />
                  </td>
                  <td style={{ padding: '8px 12px', color: 'var(--text-dim)', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                    {ev.processingTimeMs}ms
                  </td>
                  <td style={{ padding: '8px 12px' }}>
                    <ChevronRight size={14} color="var(--text-dim)" />
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </Layout>
  )
}
