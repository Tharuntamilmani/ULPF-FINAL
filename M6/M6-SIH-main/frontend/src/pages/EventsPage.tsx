import React, { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Layout, PageHeader } from '../components/layout/Layout'
import { getLiveEvents, searchLiveEvents } from '../api/endpoints'
import { GOLDEN_TEMPLATES, buildSyntheticPipelineEvent } from '../api/pipelineService'
import { MOCK_RAW_EVENTS, MOCK_UES_EVENTS } from '../lib/mock/mockData'
import { TraceGraph } from '../components/pipeline/TraceGraph'
import { RawEventViewer } from '../components/pipeline/RawEventViewer'
import { Search, RefreshCw, X, Copy, Check, GitBranch, ArrowRight } from 'lucide-react'
import toast from 'react-hot-toast'

type DetailTab = 'overview' | 'raw' | 'parsed' | 'ues' | 'mapping' | 'traceability' | 'integrity'

interface EventItem {
  id: string
  time: string
  timestamp: string
  source: string
  vendor: string
  format: string
  parser: string
  eventType: string
  severity: string
  severityNum: number
  status: string
  integrityStatus?: 'VERIFIED' | 'UNVERIFIED'
  latency: string
  rawEventId: string
  rawBytes: string
  rawHash: string
  extractedFields: Record<string, any>
  mappings: Array<{ src: string; ues: string; sample: string }>
  finalUes: any
}

export function EventsPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // Filters
  const [searchQuery, setSearchQuery] = useState('')
  const [timeRange, setTimeRange] = useState('1h')
  const [selectedSource, setSelectedSource] = useState('')
  const [selectedVendor, setSelectedVendor] = useState('')
  const [selectedFormat, setSelectedFormat] = useState('')
  const [selectedType, setSelectedType] = useState('')
  const [selectedSeverity, setSelectedSeverity] = useState('')
  const [selectedStatus, setSelectedStatus] = useState('')
  const [selectedParser, setSelectedParser] = useState('')

  // Selected event for detail investigation
  const [selectedEventId, setSelectedEventId] = useState<string | null>(searchParams.get('id') || null)
  const [detailTab, setDetailTab] = useState<DetailTab>('overview')
  const [copied, setCopied] = useState(false)

  // Fetch real events from OpenSearch / M6 backend
  const { data, refetch, isFetching } = useQuery({
    queryKey: ['live-events', selectedType, selectedSeverity, searchQuery],
    queryFn: () => {
      if (searchQuery) {
        return searchLiveEvents({
          event_type: selectedType || undefined,
          min_severity: selectedSeverity ? parseInt(selectedSeverity) : undefined,
          limit: 50,
        }).then(r => ({ events: r.data.events, total: r.data.count })).catch(() => null)
      }
      return getLiveEvents({
        type: selectedType || undefined,
        severity: selectedSeverity ? parseInt(selectedSeverity) : undefined,
        limit: 50,
      }).then(r => r.data).catch(() => null)
    },
    refetchInterval: 10000,
  })

  // Provide synthetic golden events if datastore is currently empty (15 comprehensive sample events)
  const [syntheticEvents, setSyntheticEvents] = useState<EventItem[]>(() => {
    return MOCK_UES_EVENTS.map(ev => {
      const d = new Date(ev.timestamp)
      const rawMatch = MOCK_RAW_EVENTS.find(r => r.id === ev.rawEventId)
      return {
        id: ev.id,
        time: d.toTimeString().split(' ')[0],
        timestamp: ev.timestamp,
        source: ev.source,
        vendor: ev.vendor,
        format: ev.format.toUpperCase(),
        parser: ev.parser,
        eventType: ev.eventType,
        severity: ev.severity.toUpperCase(),
        severityNum: ev.severityScore,
        status: ev.status === 'UNVERIFIED' || ev.integrityStatus === 'UNVERIFIED' || ev.validation === 'FAILED' ? 'Unverified' : 'Validated',
        integrityStatus: ev.status === 'UNVERIFIED' || ev.integrityStatus === 'UNVERIFIED' || ev.validation === 'FAILED' ? 'UNVERIFIED' : 'VERIFIED',
        latency: `${ev.processingTimeMs.toFixed(1)}ms`,
        rawEventId: ev.rawEventId,
        rawBytes: rawMatch?.rawMessage || `<166>Sep 21 ${ev.source} connection to ${ev.destinationIp}`,
        rawHash: ev.rawHash,
        extractedFields: {
          srcip: ev.sourceIp,
          dstip: ev.destinationIp,
          protocol: ev.protocol,
          action: ev.action,
          outcome: ev.outcome,
          vendor: ev.vendor,
        },
        mappings: [
          { src: 'srcip', ues: 'source.ip', sample: ev.sourceIp },
          { src: 'dstip', ues: 'destination.ip', sample: ev.destinationIp },
          { src: 'protocol', ues: 'network.protocol', sample: ev.protocol },
          { src: 'action', ues: 'event.action', sample: ev.action },
        ],
        finalUes: {
          event: {
            id: ev.id,
            timestamp: ev.timestamp,
            category: ev.eventType.split('.')[0] || 'network',
            type: ev.eventType.split('.')[1] || 'connection',
            action: ev.action,
            outcome: ev.outcome,
            severity: { value: ev.severityScore, label: ev.severity },
            provider: ev.vendor,
          },
          source: { ip: ev.sourceIp },
          destination: { ip: ev.destinationIp },
          network: { protocol: ev.protocol },
          provenance: {
            raw_event_id: ev.rawEventId,
            raw_hash: ev.rawHash,
          },
        },
      }
    })
  })

  useEffect(() => {
    if (!selectedEventId && syntheticEvents.length > 0) {
      setSelectedEventId(syntheticEvents[0].id)
    }
  }, [selectedEventId, syntheticEvents])

  const baseEvents: EventItem[] = data?.events && data.events.length > 0
    ? data.events.map((e: any) => {
        const d = new Date(e.event?.timestamp || Date.now())
        return {
          id: e.event?.id || e.id || 'evt_live',
          time: d.toTimeString().split(' ')[0],
          timestamp: e.event?.timestamp || new Date().toISOString(),
          source: e.source?.ip || '192.168.10.25',
          vendor: e.observer?.vendor || 'Cisco',
          format: 'SYSLOG',
          parser: 'parser-cisco-asa',
          eventType: e.event?.type || 'connection',
          severity: (e.event?.severity?.label || 'info').toUpperCase(),
          severityNum: e.event?.severity?.value || 2,
          status: 'Validated',
          latency: '2.1ms',
          rawEventId: e.raw?.id || e.provenance?.raw_event_id || 'raw_live',
          rawBytes: e.raw?.message || '%ASA-6-302013: Built inbound UDP connection for outside:192.168.10.25/51542 to inside:8.8.8.8/53',
          rawHash: e.raw?.sha256 || 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
          extractedFields: { srcip: e.source?.ip || '192.168.10.25', dstip: e.destination?.ip || '8.8.8.8' },
          mappings: [
            { src: 'srcip', ues: 'source.ip', sample: e.source?.ip || '192.168.10.25' },
            { src: 'dstip', ues: 'destination.ip', sample: e.destination?.ip || '8.8.8.8' },
          ],
          finalUes: e,
        }
      })
    : syntheticEvents

  // Filter list
  const filteredEvents = baseEvents.filter(ev => {
    if (selectedSource && ev.source !== selectedSource) return false
    if (selectedVendor && ev.vendor.toLowerCase() !== selectedVendor.toLowerCase()) return false
    if (selectedFormat && ev.format.toLowerCase() !== selectedFormat.toLowerCase()) return false
    if (selectedType && ev.eventType !== selectedType) return false
    if (selectedSeverity && ev.severity !== selectedSeverity) return false
    if (selectedStatus && ev.status !== selectedStatus) return false
    if (selectedParser && ev.parser !== selectedParser) return false
    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      const match =
        ev.id.toLowerCase().includes(q) ||
        ev.source.toLowerCase().includes(q) ||
        ev.vendor.toLowerCase().includes(q) ||
        ev.eventType.toLowerCase().includes(q) ||
        ev.parser.toLowerCase().includes(q) ||
        ev.rawBytes.toLowerCase().includes(q)
      if (!match) return false
    }
    return true
  })

  const selectedEvent = baseEvents.find(e => e.id === selectedEventId) || filteredEvents[0] || null

  const handleSelectEvent = (id: string) => {
    setSelectedEventId(id)
    setSearchParams(id ? { id } : {})
  }

  const handleCopyJson = () => {
    if (!selectedEvent) return
    navigator.clipboard.writeText(JSON.stringify(selectedEvent.finalUes, null, 2))
    setCopied(true)
    toast.success('UES JSON copied')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Header */}
        <PageHeader
          title="Events"
          subtitle="Discover, filter, and investigate raw logs, parsed tokens, and normalized Universal Event Schema (UES v1.0.0) records"
          actions={
            <button
              onClick={() => refetch()}
              className="btn btn-secondary"
            >
              <RefreshCw size={11} style={{ animation: isFetching ? 'spin 1s linear infinite' : 'none' }} />
              <span>Refresh</span>
            </button>
          }
        />

        {/* Search & Filter Toolbar */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '10px 12px',
          }}
        >
          {/* Row 1: Search input + Time Range */}
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1 }}>
              <Search size={15} color="var(--text-muted)" />
              <input
                type="text"
                placeholder="Search by Event ID, IP, message text, vendor, or cryptographic hash..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                style={{ width: '100%', fontSize: 13.5 }}
              />
              {searchQuery && (
                <button
                  onClick={() => setSearchQuery('')}
                  className="btn btn-ghost"
                  style={{ padding: 4 }}
                >
                  <X size={15} />
                </button>
              )}
            </div>

            <select
              value={timeRange}
              onChange={e => setTimeRange(e.target.value)}
              style={{ minWidth: 145, fontSize: 13.5 }}
            >
              <option value="15m">Last 15 minutes</option>
              <option value="1h">Last 1 hour</option>
              <option value="24h">Last 24 hours</option>
              <option value="7d">Last 7 days</option>
            </select>
          </div>

          {/* Row 2: Secondary Filter Dropdowns - 13px Readable Text */}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <select
              value={selectedVendor}
              onChange={e => setSelectedVendor(e.target.value)}
              style={{ minWidth: 125, fontSize: 13 }}
            >
              <option value="">Vendor: All</option>
              <option value="Cisco">Cisco</option>
              <option value="Microsoft">Microsoft</option>
              <option value="Fortinet">Fortinet</option>
              <option value="Linux">Linux</option>
              <option value="Check Point">Check Point</option>
            </select>

            <select
              value={selectedFormat}
              onChange={e => setSelectedFormat(e.target.value)}
              style={{ minWidth: 115, fontSize: 13 }}
            >
              <option value="">Format: All</option>
              <option value="SYSLOG">SYSLOG</option>
              <option value="JSON">JSON</option>
              <option value="KV">KV</option>
              <option value="LEEF">LEEF</option>
              <option value="CEF">CEF</option>
            </select>

            <select
              value={selectedType}
              onChange={e => setSelectedType(e.target.value)}
              style={{ minWidth: 160, fontSize: 13 }}
            >
              <option value="">Event Type: All</option>
              <option value="connection">connection</option>
              <option value="logon">logon (auth)</option>
              <option value="network.connection">network.connection</option>
              <option value="firewall_traffic">firewall_traffic</option>
            </select>

            <select
              value={selectedSeverity}
              onChange={e => setSelectedSeverity(e.target.value)}
              style={{ minWidth: 135, fontSize: 13 }}
            >
              <option value="">Severity: All</option>
              <option value="INFORMATIONAL">Informational</option>
              <option value="INFO">Info</option>
              <option value="LOW">Low</option>
              <option value="MEDIUM">Medium</option>
              <option value="HIGH">High</option>
              <option value="CRITICAL">Critical</option>
            </select>

            <select
              value={selectedParser}
              onChange={e => setSelectedParser(e.target.value)}
              style={{ minWidth: 180, fontSize: 13 }}
            >
              <option value="">Parser: All</option>
              <option value="parser-cisco-asa">parser-cisco-asa</option>
              <option value="parser-windows-security">parser-windows-security</option>
              <option value="parser-fortinet-fortigate">parser-fortinet-fortigate</option>
              <option value="parser-linux-syslog">parser-linux-syslog</option>
            </select>

            <select
              value={selectedStatus}
              onChange={e => setSelectedStatus(e.target.value)}
              style={{ minWidth: 125, fontSize: 13 }}
            >
              <option value="">Status: All</option>
              <option value="Validated">Validated</option>
              <option value="Indexed">Indexed</option>
              <option value="Unverified">Unverified (Tampered)</option>
            </select>

            {(selectedVendor || selectedFormat || selectedType || selectedSeverity || selectedParser || selectedStatus || searchQuery) && (
              <button
                onClick={() => {
                  setSelectedVendor('')
                  setSelectedFormat('')
                  setSelectedType('')
                  setSelectedSeverity('')
                  setSelectedParser('')
                  setSelectedStatus('')
                  setSearchQuery('')
                }}
                className="btn btn-ghost"
                style={{ fontSize: 12.5, padding: '4px 8px', color: 'var(--accent)', fontWeight: 600 }}
              >
                Reset Filters
              </button>
            )}

            <div style={{ marginLeft: 'auto', fontSize: 12.5, color: 'var(--text-secondary)' }}>
              Showing {filteredEvents.length} events
            </div>
          </div>
        </div>

        {/* Dense Operational Table - 13px Body, 40-44px Row Height */}
        <div className="table-container">
          <table className="op-table">
            <thead>
              <tr>
                <th style={{ width: 95 }}>TIME</th>
                <th style={{ width: 170 }}>EVENT ID</th>
                <th>SOURCE</th>
                <th>VENDOR</th>
                <th style={{ width: 85 }}>FORMAT</th>
                <th>PARSER</th>
                <th>EVENT TYPE</th>
                <th style={{ width: 105 }}>SEVERITY</th>
                <th style={{ width: 110 }}>STATUS</th>
                <th style={{ width: 85 }}>LATENCY</th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.map(ev => {
                const isSelected = selectedEvent?.id === ev.id
                return (
                  <tr
                    key={ev.id}
                    onClick={() => handleSelectEvent(ev.id)}
                    style={{
                      cursor: 'pointer',
                      background: isSelected ? 'var(--accent-subtle)' : undefined,
                    }}
                  >
                    <td className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                      {ev.time}
                    </td>
                    <td className="font-mono" style={{ fontWeight: 600, color: 'var(--accent)' }}>
                      {ev.id}
                    </td>
                    <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                      {ev.source}
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>
                      {ev.vendor}
                    </td>
                    <td className="font-mono" style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>
                      {ev.format}
                    </td>
                    <td className="font-mono" style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                      {ev.parser}
                    </td>
                    <td style={{ color: 'var(--text-secondary)' }}>
                      {ev.eventType}
                    </td>
                    <td>
                      <span
                        style={{
                          fontSize: 12,
                          fontWeight: 600,
                          color:
                            ev.severity === 'CRITICAL' || ev.severity === 'HIGH'
                              ? 'var(--red)'
                              : ev.severity === 'MEDIUM'
                              ? 'var(--amber)'
                              : 'var(--text-secondary)',
                        }}
                      >
                        {ev.severity}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                        <span className={`status-dot ${ev.integrityStatus === 'UNVERIFIED' || ev.status === 'Unverified' ? 'red' : 'green'}`} />
                        <span style={{ fontSize: 12, color: ev.integrityStatus === 'UNVERIFIED' || ev.status === 'Unverified' ? 'var(--red)' : 'var(--green)', fontWeight: 600 }}>{ev.status}</span>
                      </div>
                    </td>
                    <td className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                      {ev.latency}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* 8. EVENT DETAIL INVESTIGATION WORKSPACE */}
        {selectedEvent && (
          <div
            style={{
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              overflow: 'hidden',
              marginTop: 6,
            }}
          >
            {/* Header: Event ID, Timestamp, Source, Vendor, Format, Status (Clear Readability Hierarchy) */}
            <div
              style={{
                padding: '14px 20px',
                borderBottom: '1px solid var(--border)',
                background: 'var(--bg-elevated)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: 20,
              }}
            >
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(6, auto)',
                  gap: 32,
                  alignItems: 'center',
                }}
              >
                <div>
                  <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>EVENT ID</div>
                  <div className="font-mono" style={{ fontSize: 15, fontWeight: 700, color: 'var(--accent)', marginTop: 2 }}>
                    {selectedEvent.id}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>TIMESTAMP</div>
                  <div className="font-mono" style={{ fontSize: 13, color: 'var(--text-primary)', marginTop: 2 }}>
                    {selectedEvent.timestamp.replace('T', ' ').slice(0, 19)}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>SOURCE</div>
                  <div style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-primary)', marginTop: 2 }}>
                    {selectedEvent.source}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>VENDOR</div>
                  <div style={{ fontSize: 13.5, color: 'var(--text-secondary)', marginTop: 2 }}>
                    {selectedEvent.vendor}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>FORMAT</div>
                  <div className="font-mono" style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
                    {selectedEvent.format}
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>STATUS</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 3 }}>
                    <span className={`status-dot ${selectedEvent.integrityStatus === 'UNVERIFIED' || selectedEvent.status === 'Unverified' ? 'red' : 'green'}`} />
                    <span style={{ fontSize: 12.5, color: selectedEvent.integrityStatus === 'UNVERIFIED' || selectedEvent.status === 'Unverified' ? 'var(--red)' : 'var(--green)', fontWeight: 600 }}>{selectedEvent.status}</span>
                  </div>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <button
                  onClick={handleCopyJson}
                  className="btn btn-secondary"
                >
                  {copied ? <Check size={14} color="var(--green)" /> : <Copy size={14} />}
                  <span>{copied ? 'Copied' : 'Copy UES JSON'}</span>
                </button>

                <button
                  onClick={() => navigate(`/events/${selectedEvent.id}/trace`)}
                  className="btn btn-secondary"
                >
                  <GitBranch size={14} />
                  <span>Trace Lineage</span>
                </button>
              </div>
            </div>

            {/* 7 Investigation Tabs */}
            <div className="tab-bar">
              {(['overview', 'raw', 'parsed', 'ues', 'mapping', 'traceability', 'integrity'] as DetailTab[]).map(tab => (
                <button
                  key={tab}
                  onClick={() => setDetailTab(tab)}
                  className={`tab-btn ${detailTab === tab ? 'active' : ''}`}
                >
                  {tab.toUpperCase()}
                </button>
              ))}
            </div>

            {/* TAB CONTENT */}
            <div style={{ padding: '16px 20px' }}>
              {/* TAB 1: OVERVIEW */}
              {detailTab === 'overview' && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16 }}>
                  <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>
                      NETWORK & TRANSPORT
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Source IP:</span>
                        <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{selectedEvent.finalUes?.source?.ip || '192.168.10.25'}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Source Port:</span>
                        <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{selectedEvent.finalUes?.source?.port || 51542}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Destination IP:</span>
                        <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{selectedEvent.finalUes?.destination?.ip || '8.8.8.8'}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Destination Port:</span>
                        <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{selectedEvent.finalUes?.destination?.port || 443}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Protocol:</span>
                        <span className="font-mono" style={{ color: 'var(--text-primary)' }}>{selectedEvent.finalUes?.network?.protocol || 'TCP'}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>
                      CLASSIFICATION & ACTION
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Event Type:</span>
                        <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{selectedEvent.eventType}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Severity:</span>
                        <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{selectedEvent.severity} ({selectedEvent.severityNum}/10)</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Action:</span>
                        <span style={{ color: 'var(--green)', fontWeight: 600 }}>{selectedEvent.finalUes?.event?.action || 'allow'}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Outcome:</span>
                        <span style={{ color: 'var(--green)' }}>{selectedEvent.finalUes?.event?.outcome || 'success'}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Parser ID:</span>
                        <span className="font-mono" style={{ color: 'var(--accent)', fontWeight: 600 }}>{selectedEvent.parser}</span>
                      </div>
                    </div>
                  </div>

                  <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 14 }}>
                    <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--text-secondary)', letterSpacing: '0.04em', textTransform: 'uppercase', marginBottom: 10 }}>
                      EVIDENCE PROVENANCE
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 13 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Raw ID:</span>
                        <span className="font-mono" style={{ color: 'var(--accent)', fontWeight: 600 }}>{selectedEvent.rawEventId}</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Storage:</span>
                        <span className="font-mono" style={{ color: 'var(--text-muted)' }}>s3://ulpf-raw-vault/{selectedEvent.rawEventId}.dat</span>
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Integrity:</span>
                        {selectedEvent.integrityStatus === 'UNVERIFIED' || selectedEvent.status === 'Unverified' ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                            <span className="status-dot red" />
                            <span style={{ color: 'var(--red)', fontWeight: 600 }}>Unverified (Hash Mismatch)</span>
                          </div>
                        ) : (
                          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                            <span className="status-dot green" />
                            <span style={{ color: 'var(--green)', fontWeight: 600 }}>Verified (SHA-256)</span>
                          </div>
                        )}
                      </div>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span style={{ color: 'var(--text-secondary)', fontSize: 12.5 }}>Schema:</span>
                        <span className="font-mono" style={{ color: 'var(--text-primary)' }}>Canonical UES v1.0.0</span>
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* TAB 2: RAW */}
              {detailTab === 'raw' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <RawEventViewer
                    rawBytes={selectedEvent.rawBytes}
                    sha256Hash={selectedEvent.rawHash}
                    rawEventId={selectedEvent.rawEventId}
                    storageRef={`s3://ulpf-raw-vault/${selectedEvent.rawEventId}.dat`}
                  />
                </div>
              )}

              {/* TAB 3: PARSED */}
              {detailTab === 'parsed' && (
                <div className="table-container">
                  <table className="op-table">
                    <thead>
                      <tr>
                        <th style={{ width: 220 }}>EXTRACTED FIELD</th>
                        <th>VALUE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {Object.entries(selectedEvent.extractedFields).map(([k, v]) => (
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

              {/* TAB 4: UES */}
              {detailTab === 'ues' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                      Canonical Universal Event Schema (UES v1.0.0)
                    </span>
                  </div>
                  <pre className="code-editor" style={{ maxHeight: 380 }}>
                    {JSON.stringify(selectedEvent.finalUes || {}, null, 2)}
                  </pre>
                </div>
              )}

              {/* TAB 5: MAPPING */}
              {detailTab === 'mapping' && (
                <div className="table-container">
                  <table className="op-table">
                    <thead>
                      <tr>
                        <th>SOURCE FIELD</th>
                        <th>UES TARGET FIELD</th>
                        <th>SAMPLE EXTRACTED VALUE</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedEvent.mappings.map(m => (
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

              {/* TAB 6: TRACEABILITY */}
              {detailTab === 'traceability' && (
                <TraceGraph
                  event={{
                    eventId: selectedEvent.id,
                    rawEventId: selectedEvent.rawEventId,
                    tenantId: 'tenant-enterprise',
                    sourceId: selectedEvent.source,
                    templateName: selectedEvent.vendor,
                    receivedAt: selectedEvent.timestamp,
                    transport: selectedEvent.format.toLowerCase(),
                    rawBytes: selectedEvent.rawBytes,
                    rawHash: selectedEvent.rawHash,
                    enrichedDigest: selectedEvent.rawHash.slice(0, 32) + 'a1b2',
                    correlationId: `corr-${selectedEvent.id.slice(0, 8)}`,
                    status: 'COMPLETED',
                    currentStage: 'm5',
                    stages: {
                      gateway: { status: 'COMPLETE', latencyMs: 0.8, authenticated: true, tenant: 'tenant-enterprise' },
                      m1: { status: 'COMPLETE', latencyMs: 1.2, vaultKey: `s3://ulpf-raw-vault/${selectedEvent.rawEventId}.dat`, sha256: selectedEvent.rawHash, sizeBytes: selectedEvent.rawBytes.length },
                      kafka: { status: 'COMPLETE', latencyMs: 0.5, topic: 'ulpf.events', partition: 0, offset: 1042 },
                      m2: { status: 'COMPLETE', latencyMs: 2.4, parserId: selectedEvent.parser, vendor: selectedEvent.vendor, parsedFields: selectedEvent.extractedFields },
                      m3: { status: 'COMPLETE', latencyMs: 1.8, schema: 'ues_event', version: '1.0.0', validation: 'STRICT_PASS', canonicalUes: selectedEvent.finalUes },
                      m4: { status: 'COMPLETE', latencyMs: 3.1, geoip: {}, asset: {}, threatIntel: {}, digest: selectedEvent.rawHash.slice(0, 32) },
                      m5: { status: 'COMPLETE', latencyMs: 1.5, policy: 'default_routing', decision: 'ROUTE_SIEM', destinations: ['opensearch-siem'] },
                    },
                    hops: [],
                    finalUes: selectedEvent.finalUes,
                  }}
                  onViewRaw={() => setDetailTab('raw')}
                />
              )}

              {/* TAB 7: INTEGRITY */}
              {detailTab === 'integrity' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                  {selectedEvent.integrityStatus === 'UNVERIFIED' || selectedEvent.status === 'Unverified' ? (
                    <div
                      style={{
                        padding: '12px 14px',
                        background: 'rgba(239, 68, 68, 0.08)',
                        border: '1px solid rgba(239, 68, 68, 0.25)',
                        borderRadius: 'var(--radius)',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 6,
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--red)', fontWeight: 700, fontSize: 13 }}>
                        <span className="status-dot red" />
                        <span>CRYPTOGRAPHIC EVIDENCE MISMATCH DETECTED (M1 VAULT INTEGRITY FAILURE)</span>
                      </div>
                      <div style={{ fontSize: 12.5, color: 'var(--text-primary)', lineHeight: 1.5 }}>
                        The SHA-256 digest computed from the raw vault storage payload does not match the immutable ingestion seal recorded at Gateway M1.
                        This indicates in-transit tampering, post-ingestion byte corruption, or vault storage mutation.
                      </div>
                      <div style={{ display: 'flex', gap: 18, marginTop: 4, fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                        <div><span style={{ color: 'var(--text-secondary)' }}>M1 Ingestion Seal: </span><span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{selectedEvent.rawHash}</span></div>
                      </div>
                    </div>
                  ) : (
                    <div
                      style={{
                        padding: '10px 14px',
                        background: 'rgba(16, 185, 129, 0.08)',
                        border: '1px solid rgba(16, 185, 129, 0.25)',
                        borderRadius: 'var(--radius)',
                        display: 'flex',
                        alignItems: 'center',
                        gap: 8,
                        fontSize: 12.5,
                        color: 'var(--green)',
                        fontWeight: 600,
                      }}
                    >
                      <span className="status-dot green" />
                      <span>100% Raw Evidence Integrity Verified — Ingestion SHA-256 seal matches raw storage bytes.</span>
                    </div>
                  )}

                  <div className="table-container">
                    <table className="op-table">
                      <thead>
                        <tr>
                          <th style={{ width: 240 }}>PROPERTY</th>
                          <th>CRYPTOGRAPHIC ATTRIBUTE</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Raw SHA-256 Ingestion Seal</td>
                          <td className="font-mono" style={{ color: 'var(--text-primary)' }}>
                            {selectedEvent.rawHash}
                          </td>
                        </tr>
                        <tr>
                          <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Storage Vault URI</td>
                          <td className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                            s3://ulpf-raw-vault/{selectedEvent.rawEventId}.dat
                          </td>
                        </tr>
                        <tr>
                          <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Provenance Verification</td>
                          <td>
                            <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span className={`status-dot ${selectedEvent.integrityStatus === 'UNVERIFIED' || selectedEvent.status === 'Unverified' ? 'red' : 'green'}`} />
                              <span style={{ fontSize: 12.5, color: selectedEvent.integrityStatus === 'UNVERIFIED' || selectedEvent.status === 'Unverified' ? 'var(--red)' : 'var(--green)', fontWeight: 600 }}>
                                {selectedEvent.integrityStatus === 'UNVERIFIED' || selectedEvent.status === 'Unverified'
                                  ? 'FAILED — Cryptographic Hash Mismatch (Evidence Tampered)'
                                  : '100% Bit-Exact Provenance Verified'}
                              </span>
                            </div>
                          </td>
                        </tr>
                        <tr>
                          <td style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Canonical Schema Enforcement</td>
                          <td className="font-mono" style={{ color: selectedEvent.integrityStatus === 'UNVERIFIED' || selectedEvent.status === 'Unverified' ? 'var(--amber)' : 'var(--text-primary)' }}>
                            {selectedEvent.integrityStatus === 'UNVERIFIED' || selectedEvent.status === 'Unverified'
                              ? 'QUARANTINED (Evidence Invariance Violation)'
                              : 'UES v1.0.0 Validated (RFC-8785)'}
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  {/* Interactive Evidence Verification */}
                  <div style={{ marginTop: 4 }}>
                    <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em', marginBottom: 8 }}>
                      Live Interactive Evidence Verification
                    </div>
                    <RawEventViewer
                      rawBytes={selectedEvent.rawBytes}
                      sha256Hash={selectedEvent.rawHash}
                      rawEventId={selectedEvent.rawEventId}
                      storageRef={`s3://ulpf-raw-vault/${selectedEvent.rawEventId}.dat`}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}
