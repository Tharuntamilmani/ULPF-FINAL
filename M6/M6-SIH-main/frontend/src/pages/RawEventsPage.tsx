import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Layout, PageHeader } from '../components/layout/Layout'
import { MOCK_RAW_EVENTS, type MockRawEvent } from '../lib/mock/mockData'
import { Database, Search, X, ExternalLink, ShieldCheck, Hash, HardDrive } from 'lucide-react'

const FORMAT_COLORS: Record<string, { bg: string; color: string }> = {
  syslog: { bg: 'rgba(59,130,246,0.15)', color: '#60a5fa' },
  json:   { bg: 'rgba(16,185,129,0.15)', color: '#34d399' },
  kv:     { bg: 'rgba(245,158,11,0.15)', color: '#fbbf24' },
  cef:    { bg: 'rgba(139,92,246,0.15)', color: '#a78bfa' },
  leef:   { bg: 'rgba(6,182,212,0.15)',  color: '#22d3ee' },
  csv:    { bg: 'rgba(107,114,128,0.15)', color: '#9ca3af' },
}

export function RawEventsPage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [filterFormat, setFilterFormat] = useState('')
  const [filterVendor, setFilterVendor] = useState('')
  const [filterSource, setFilterSource] = useState('')
  const [selected, setSelected] = useState<MockRawEvent | null>(null)

  const events = MOCK_RAW_EVENTS

  const filtered = events.filter(e => {
    if (search && !e.id.includes(search) && !e.sha256.includes(search) && !e.rawMessage.toLowerCase().includes(search.toLowerCase())) return false
    if (filterFormat && e.format !== filterFormat) return false
    if (filterVendor && e.vendor !== filterVendor) return false
    if (filterSource && e.source !== filterSource) return false
    return true
  })

  const vendors = [...new Set(events.map(e => e.vendor))]
  const sources = [...new Set(events.map(e => e.source))]
  const hasFilters = search || filterFormat || filterVendor || filterSource

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
        title="Raw Events"
        subtitle="Preserved original events — exact byte-level store. Independent of normalization status."
        badge={
          <span style={{ padding: '2px 8px', background: 'rgba(245,158,11,0.12)', border: '1px solid rgba(245,158,11,0.4)', borderRadius: 4, fontSize: 10, fontWeight: 700, color: 'var(--yellow)' }}>
            IMMUTABLE STORE
          </span>
        }
      />

      <div style={{ display: 'flex', gap: 16 }}>
        {/* Left: list */}
        <div style={{ flex: '0 0 560px' }}>
          {/* Filters */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 14, padding: '10px 12px', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}>
            <div style={{ position: 'relative' }}>
              <Search size={12} style={{ position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="ID, hash, raw message…"
                style={{ ...selectStyle, paddingLeft: 26, width: 200 }}
              />
            </div>
            <select value={filterFormat} onChange={e => setFilterFormat(e.target.value)} style={selectStyle}>
              <option value="">All Formats</option>
              {['syslog', 'json', 'kv', 'cef', 'leef', 'csv'].map(f => <option key={f} value={f}>{f.toUpperCase()}</option>)}
            </select>
            <select value={filterVendor} onChange={e => setFilterVendor(e.target.value)} style={selectStyle}>
              <option value="">All Vendors</option>
              {vendors.map(v => <option key={v} value={v}>{v}</option>)}
            </select>
            <select value={filterSource} onChange={e => setFilterSource(e.target.value)} style={selectStyle}>
              <option value="">All Sources</option>
              {sources.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            {hasFilters && (
              <button
                onClick={() => { setSearch(''); setFilterFormat(''); setFilterVendor(''); setFilterSource('') }}
                style={{ display: 'flex', alignItems: 'center', gap: 4, padding: '6px 8px', background: 'transparent', border: '1px solid var(--border)', borderRadius: 5, color: 'var(--text-dim)', fontSize: 12, cursor: 'pointer' }}
              >
                <X size={11} /> Clear
              </button>
            )}
          </div>

          {/* List */}
          <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, overflow: 'hidden' }}>
            {filtered.map((ev, idx) => {
              const fc = FORMAT_COLORS[ev.format] ?? { bg: 'rgba(107,114,128,0.15)', color: '#9ca3af' }
              const isSelected = selected?.id === ev.id
              return (
                <div
                  key={ev.id}
                  onClick={() => setSelected(ev)}
                  style={{
                    padding: '12px 14px',
                    borderBottom: idx < filtered.length - 1 ? '1px solid var(--border)' : 'none',
                    cursor: 'pointer',
                    background: isSelected ? 'var(--bg-elevated)' : 'transparent',
                    borderLeft: isSelected ? '3px solid var(--accent)' : '3px solid transparent',
                    transition: 'background 0.1s',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
                    <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--accent)', fontWeight: 700 }}>{ev.id}</span>
                    <span style={{ padding: '2px 7px', borderRadius: 4, fontSize: 10, fontWeight: 700, background: fc.bg, color: fc.color, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                      {ev.format}
                    </span>
                  </div>
                  <div style={{ display: 'flex', gap: 12, fontSize: 11, color: 'var(--text-dim)', marginBottom: 5 }}>
                    <span>{ev.vendor}</span>
                    <span>·</span>
                    <span>{ev.source}</span>
                    <span>·</span>
                    <span>{new Date(ev.timestamp).toLocaleTimeString()}</span>
                    <span>·</span>
                    <span>{ev.rawBytes} B</span>
                  </div>
                  <div
                    style={{
                      fontFamily: 'var(--font-mono)',
                      fontSize: 10.5,
                      color: 'var(--text-muted)',
                      background: '#0d1017',
                      border: '1px solid var(--border)',
                      borderRadius: 4,
                      padding: '5px 8px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {ev.rawMessage.substring(0, 100)}{ev.rawMessage.length > 100 ? '…' : ''}
                  </div>
                  {ev.integrityStatus === 'UNVERIFIED' ? (
                    <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: 'var(--red)', fontWeight: 600 }}>
                      <span className="status-dot red" />
                      UNVERIFIED: Vault Hash Mismatch Detected • {ev.uesEventId}
                    </div>
                  ) : ev.uesEventId ? (
                    <div style={{ marginTop: 6, display: 'flex', alignItems: 'center', gap: 4, fontSize: 10, color: 'var(--green)' }}>
                      <ShieldCheck size={10} />
                      Linked UES: {ev.uesEventId} • Verified
                    </div>
                  ) : (
                    <div style={{ marginTop: 6, fontSize: 10, color: 'var(--yellow)' }}>
                      ⚠ No linked UES event (orphaned raw)
                    </div>
                  )}
                </div>
              )
            })}
            {filtered.length === 0 && (
              <div style={{ padding: 40, textAlign: 'center', color: 'var(--text-dim)' }}>No raw events match filters</div>
            )}
          </div>
        </div>

        {/* Right: detail panel */}
        <div style={{ flex: 1, minWidth: 0 }}>
          {selected ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {/* Header card */}
              <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 16 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 14 }}>
                  <div>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>RAW EVENT ID</div>
                    <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13, color: 'var(--accent)', fontWeight: 700 }}>{selected.id}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 5, padding: '4px 10px', background: 'rgba(16,185,129,0.12)', border: '1px solid var(--green)', borderRadius: 5, fontSize: 11, fontWeight: 700, color: 'var(--green)' }}>
                    <ShieldCheck size={12} />
                    ORIGINAL PRESERVED
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                  {[
                    { label: 'Source', value: selected.source },
                    { label: 'Vendor', value: selected.vendor },
                    { label: 'Format', value: selected.format.toUpperCase() },
                    { label: 'Encoding', value: selected.encoding },
                    { label: 'Raw Bytes', value: `${selected.rawBytes} B` },
                    { label: 'Timestamp', value: new Date(selected.timestamp).toLocaleString() },
                    { label: 'Storage Ref', value: selected.storageRef },
                    { label: 'UES Event', value: selected.uesEventId ?? '—' },
                  ].map(({ label, value }) => (
                    <div key={label}>
                      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginBottom: 2, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
                      <div style={{ fontSize: 12, color: 'var(--text-primary)', fontFamily: label === 'Storage Ref' || label === 'UES Event' ? 'var(--font-mono)' : 'inherit', wordBreak: 'break-all' }}>{value}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* SHA-256 */}
              <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
                  <Hash size={13} color={selected.integrityStatus === 'UNVERIFIED' ? 'var(--red)' : 'var(--purple)'} />
                  <span style={{ fontSize: 11, fontWeight: 700, color: selected.integrityStatus === 'UNVERIFIED' ? 'var(--red)' : 'var(--purple)' }}>
                    INTEGRITY HASH {selected.integrityStatus === 'UNVERIFIED' ? '(UNVERIFIED — HASH MISMATCH)' : ''}
                  </span>
                  {selected.integrityStatus === 'UNVERIFIED' && (
                    <span style={{ marginLeft: 'auto', fontSize: 10, fontWeight: 700, color: 'var(--red)', background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', padding: '2px 6px', borderRadius: 4 }}>
                      TAMPERED EVIDENCE
                    </span>
                  )}
                </div>
                <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: selected.integrityStatus === 'UNVERIFIED' ? 'var(--red)' : '#c9d1d9', background: '#0d1017', border: '1px solid var(--border)', borderRadius: 5, padding: '8px 12px', wordBreak: 'break-all' }}>
                  SHA-256: {selected.sha256}
                </div>
              </div>

              {/* Raw message */}
              <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8, padding: 14 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 10 }}>
                  <Database size={13} color="var(--yellow)" />
                  <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--yellow)' }}>EXACT RAW PAYLOAD</span>
                  <span style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--text-dim)' }}>Encoding: {selected.encoding}</span>
                </div>
                <pre
                  style={{
                    fontFamily: 'var(--font-mono)',
                    fontSize: 12,
                    color: '#c9d1d9',
                    background: '#0d1017',
                    border: '1px solid var(--border)',
                    borderRadius: 5,
                    padding: '12px 14px',
                    overflowX: 'auto',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-all',
                    margin: 0,
                    lineHeight: 1.6,
                  }}
                >
                  {selected.rawMessage}
                </pre>
              </div>

              {/* Actions */}
              {selected.uesEventId && (
                <button
                  onClick={() => navigate(`/events/${selected.uesEventId}`)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    padding: '9px 16px',
                    background: 'rgba(59,130,246,0.1)', border: '1px solid var(--accent)', borderRadius: 6,
                    color: 'var(--accent)', fontWeight: 600, fontSize: 13, cursor: 'pointer',
                  }}
                >
                  <ExternalLink size={14} />
                  View UES Event Detail
                </button>
              )}
            </div>
          ) : (
            <div
              style={{
                height: '100%',
                minHeight: 300,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 12,
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 8,
                color: 'var(--text-dim)',
              }}
            >
              <Database size={32} style={{ opacity: 0.4 }} />
              <span style={{ fontSize: 13 }}>Select a raw event to inspect its preserved payload</span>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
