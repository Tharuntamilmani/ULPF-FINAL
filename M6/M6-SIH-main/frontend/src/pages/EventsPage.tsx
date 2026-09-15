import React, { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Layout, PageHeader } from '../components/layout/Layout'
import { Card } from '../components/ui/Card'
import { getLiveEvents, searchLiveEvents, getEventRawRef } from '../api/endpoints'
import type { UESEvent } from '../types'
import { Search, Filter, Eye, RefreshCw, X, Shield, FileText, Database } from 'lucide-react'

export function EventsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState<string>('')
  const [selectedSeverity, setSelectedSeverity] = useState<string>('')
  const [selectedEvent, setSelectedEvent] = useState<UESEvent | null>(null)
  const [rawRefData, setRawRefData] = useState<any | null>(null)
  const [isLoadingRaw, setIsLoadingRaw] = useState(false)

  const { data, isLoading, refetch } = useQuery({
    queryKey: ['live-events', selectedType, selectedSeverity, searchQuery],
    queryFn: () => {
      if (searchQuery) {
        return searchLiveEvents({
          event_type: selectedType || undefined,
          min_severity: selectedSeverity ? parseInt(selectedSeverity) : undefined,
          limit: 50,
        }).then(r => ({ events: r.data.events, total: r.data.count }))
      }
      return getLiveEvents({
        type: selectedType || undefined,
        severity: selectedSeverity ? parseInt(selectedSeverity) : undefined,
        limit: 50,
      }).then(r => r.data)
    },
    refetchInterval: 8000,
  })

  const handleSelectEvent = async (ev: UESEvent) => {
    setSelectedEvent(ev)
    setRawRefData(null)
    const eventId = ev.event?.id || (ev as any).id
    if (eventId) {
      setIsLoadingRaw(true)
      try {
        const res = await getEventRawRef(eventId)
        setRawRefData(res.data)
      } catch {
        setRawRefData({ error: 'Raw reference not retrievable or mock storage' })
      } finally {
        setIsLoadingRaw(false)
      }
    }
  }

  const events = data?.events ?? []

  return (
    <Layout>
      <PageHeader
        title="Live Event Explorer"
        subtitle="Inspect, search, and audit canonical UES events processed by the pipeline"
        actions={
          <button
            onClick={() => refetch()}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              padding: '8px 12px',
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              borderRadius: 6,
              color: 'var(--text-primary)',
              cursor: 'pointer',
              fontSize: 13,
            }}
          >
            <RefreshCw size={14} /> Refresh
          </button>
        }
      />

      {/* Filter Bar */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          marginBottom: 16,
          background: 'var(--bg-surface)',
          padding: 12,
          borderRadius: 8,
          border: '1px solid var(--border)',
          alignItems: 'center',
          flexWrap: 'wrap',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: 200 }}>
          <Search size={16} color="var(--text-dim)" />
          <input
            type="text"
            placeholder="Search events by keyword, IP, action..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{
              width: '100%',
              background: 'transparent',
              border: 'none',
              color: 'var(--text-primary)',
              outline: 'none',
              fontSize: 13,
            }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Filter size={15} color="var(--text-dim)" />
          <select
            value={selectedType}
            onChange={e => setSelectedType(e.target.value)}
            style={{
              padding: '6px 10px',
              borderRadius: 6,
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              color: 'var(--text-primary)',
              fontSize: 12,
            }}
          >
            <option value="">All Event Types</option>
            <option value="network.flow">network.flow</option>
            <option value="authentication">authentication</option>
            <option value="system.process">system.process</option>
            <option value="cisco.firewall">cisco.firewall</option>
          </select>

          <select
            value={selectedSeverity}
            onChange={e => setSelectedSeverity(e.target.value)}
            style={{
              padding: '6px 10px',
              borderRadius: 6,
              background: 'var(--bg-elevated)',
              border: '1px solid var(--border)',
              color: 'var(--text-primary)',
              fontSize: 12,
            }}
          >
            <option value="">All Severities</option>
            <option value="1">1 - Informational</option>
            <option value="2">2 - Low</option>
            <option value="3">3 - Medium</option>
            <option value="4">4 - High</option>
            <option value="5">5 - Critical</option>
          </select>
        </div>
      </div>

      {/* Main Content: Table + Detail View */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedEvent ? '1fr 1fr' : '1fr', gap: 16 }}>
        <Card title={`Canonical UES Events (${events.length} returned)`}>
          {isLoading ? (
            <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-muted)' }}>
              Loading live events from M5 Smart Router...
            </div>
          ) : events.length === 0 ? (
            <div style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>
              No matching events found. Go to the "Event Pipeline" page to inject a live syslog event.
            </div>
          ) : (
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)', textAlign: 'left', color: 'var(--text-muted)' }}>
                    <th style={{ padding: '8px 10px' }}>Timestamp</th>
                    <th style={{ padding: '8px 10px' }}>Tenant</th>
                    <th style={{ padding: '8px 10px' }}>Type</th>
                    <th style={{ padding: '8px 10px' }}>Source → Dest</th>
                    <th style={{ padding: '8px 10px', textAlign: 'right' }}>Inspect</th>
                  </tr>
                </thead>
                <tbody>
                  {events.map((ev, i) => {
                    const isSelected = selectedEvent === ev
                    return (
                      <tr
                        key={i}
                        onClick={() => handleSelectEvent(ev)}
                        style={{
                          borderBottom: '1px solid var(--border)',
                          cursor: 'pointer',
                          background: isSelected ? 'var(--bg-hover)' : 'transparent',
                        }}
                      >
                        <td style={{ padding: '10px', color: 'var(--text-dim)', fontSize: 12 }}>
                          {ev.event?.timestamp ? new Date(ev.event.timestamp).toLocaleTimeString() : 'Recent'}
                        </td>
                        <td style={{ padding: '10px', fontWeight: 600 }}>
                          <code>{ev.tenant?.id || 'tenant-cisco'}</code>
                        </td>
                        <td style={{ padding: '10px', color: 'var(--accent)' }}>
                          {ev.event?.type || 'network.flow'}
                        </td>
                        <td style={{ padding: '10px', fontFamily: 'monospace', fontSize: 12 }}>
                          {ev.source?.ip || '192.168.1.50'} → {ev.destination?.ip || '10.0.0.5'}
                        </td>
                        <td style={{ padding: '10px', textAlign: 'right' }}>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              handleSelectEvent(ev)
                            }}
                            style={{
                              padding: '4px 8px',
                              border: '1px solid var(--border)',
                              background: 'var(--bg-elevated)',
                              borderRadius: 4,
                              color: 'var(--text-primary)',
                              cursor: 'pointer',
                            }}
                          >
                            <Eye size={13} />
                          </button>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Selected Event Details Pane */}
        {selectedEvent && (
          <Card
            title="Event Detail Inspector"
            actions={
              <button
                onClick={() => setSelectedEvent(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer' }}
              >
                <X size={16} />
              </button>
            }
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {/* Event Metadata */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, padding: 10, background: 'var(--bg-elevated)', borderRadius: 6, fontSize: 12 }}>
                <div>
                  <span style={{ color: 'var(--text-dim)', display: 'block' }}>Event ID:</span>
                  <code style={{ fontSize: 11 }}>{selectedEvent.event?.id || 'event-id'}</code>
                </div>
                <div>
                  <span style={{ color: 'var(--text-dim)', display: 'block' }}>Tenant:</span>
                  <code style={{ fontSize: 11 }}>{selectedEvent.tenant?.id || 'default_tenant'}</code>
                </div>
                <div>
                  <span style={{ color: 'var(--text-dim)', display: 'block' }}>Action:</span>
                  <span>{selectedEvent.event?.action || 'flow_permit'}</span>
                </div>
                <div>
                  <span style={{ color: 'var(--text-dim)', display: 'block' }}>Severity:</span>
                  <span>Level {selectedEvent.event?.severity?.value ?? 1}</span>
                </div>
              </div>

              {/* Raw Vault Reference */}
              <div style={{ padding: 10, background: 'var(--bg-elevated)', borderRadius: 6, fontSize: 12 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontWeight: 600, marginBottom: 4, color: 'var(--text-primary)' }}>
                  <Database size={14} color="var(--accent)" />
                  MinIO Raw Vault Storage Reference
                </div>
                {isLoadingRaw ? (
                  <span style={{ color: 'var(--text-dim)' }}>Querying raw storage reference...</span>
                ) : rawRefData ? (
                  <div style={{ fontFamily: 'monospace', fontSize: 11, color: 'var(--text-muted)' }}>
                    <div>Raw ID: {rawRefData.raw_event_id}</div>
                    <div>Storage URI: {rawRefData.storage_ref}</div>
                  </div>
                ) : (
                  <span style={{ color: 'var(--text-dim)' }}>Reference available via /v1/events/id/raw</span>
                )}
              </div>

              {/* Canonical UES v1.0.0 JSON */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, fontWeight: 600, marginBottom: 6, color: 'var(--text-primary)' }}>
                  <FileText size={14} color="var(--green)" />
                  Canonical UES v1.0.0 Structure
                </div>
                <pre
                  style={{
                    padding: 12,
                    borderRadius: 6,
                    background: 'var(--bg-base)',
                    border: '1px solid var(--border)',
                    fontSize: 11,
                    fontFamily: 'monospace',
                    overflowX: 'auto',
                    maxHeight: 340,
                    color: 'var(--text-primary)',
                  }}
                >
                  {JSON.stringify(selectedEvent, null, 2)}
                </pre>
              </div>
            </div>
          </Card>
        )}
      </div>
    </Layout>
  )
}
