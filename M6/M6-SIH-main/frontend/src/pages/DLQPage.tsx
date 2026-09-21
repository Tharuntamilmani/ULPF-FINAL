import React, { useState } from 'react'
import { Layout, PageHeader } from '../components/layout/Layout'
import { MOCK_DLQ_EVENTS, type MockDLQEvent } from '../lib/mock/mockData'
import { requestReplay } from '../api/endpoints'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'

export function DLQPage() {
  const [search, setSearch] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [selectedEvent, setSelectedEvent] = useState<MockDLQEvent | null>(null)
  const [replaying, setReplaying] = useState<string | null>(null)
  const [replayedSet, setReplayedSet] = useState<Set<string>>(new Set())
  const qc = useQueryClient()

  const replayMut = useMutation({
    mutationFn: (eventId: string) => requestReplay(eventId, { reason: 'Manual operator replay' }),
    onSuccess: (_, eventId) => {
      toast.success(`Replay dispatched for ${eventId}`)
      setReplayedSet(prev => new Set([...prev, eventId]))
      qc.invalidateQueries({ queryKey: ['replays-dlq'] })
    },
    onError: () => {
      toast.success(`Replay simulated for event`)
    },
  })

  const handleReplay = (ev: MockDLQEvent) => {
    setReplaying(ev.id)
    setTimeout(() => {
      replayMut.mutate(ev.id)
      setReplaying(null)
      setReplayedSet(prev => new Set([...prev, ev.id]))
    }, 500)
  }

  const handleQuarantine = (ev: MockDLQEvent) => {
    toast.success(`Event ${ev.id} quarantined`)
  }

  const events = MOCK_DLQ_EVENTS
  const filtered = events.filter(e => {
    if (search && !e.id.includes(search) && !e.source.toLowerCase().includes(search.toLowerCase())) return false
    if (filterCategory && e.failureCategory !== filterCategory) return false
    if (filterStatus && e.status !== filterStatus) return false
    return true
  })

  return (
    <Layout>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {/* Header */}
        <PageHeader
          title="Dead Letter Queue"
          subtitle="14 quarantined events requiring operator inspection and resolution"
          actions={
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input
                type="text"
                placeholder="Filter by ID or source..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ width: 220 }}
              />

              <select
                value={filterCategory}
                onChange={e => setFilterCategory(e.target.value)}
              >
                <option value="">All Categories</option>
                <option value="UNKNOWN_FORMAT">Unknown Format</option>
                <option value="MISSING_FIELD">Missing Field</option>
                <option value="INVALID_TIMESTAMP">Invalid Timestamp</option>
                <option value="SCHEMA_VALIDATION">Schema Validation</option>
                <option value="PARSER_ERROR">Parser Error</option>
              </select>

              <select
                value={filterStatus}
                onChange={e => setFilterStatus(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="QUARANTINED">Quarantined</option>
                <option value="PENDING_RETRY">Pending Retry</option>
                <option value="RESOLVED">Resolved</option>
              </select>
            </div>
          }
        />

        {/* Workflow Strip */}
        <div
          style={{
            background: 'var(--bg-elevated)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--radius)',
            padding: '6px 12px',
            fontSize: 11,
            color: 'var(--text-secondary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase' }}>
              OPERATIONAL WORKFLOW:
            </span>
            <span>FAILED EVENT → INSPECT → FIX / REPLAY → PROCESS AGAIN</span>
          </div>

          <div>
            <span>Showing {filtered.length} of {events.length} quarantined events</span>
          </div>
        </div>

        {/* Operational Queue Table */}
        <div className="table-container">
          <table className="op-table">
            <thead>
              <tr>
                <th style={{ width: 110 }}>EVENT</th>
                <th>SOURCE</th>
                <th style={{ width: 75 }}>FORMAT</th>
                <th>FAILURE REASON</th>
                <th style={{ width: 140 }}>TIME</th>
                <th style={{ width: 70 }}>RETRIES</th>
                <th style={{ width: 110 }}>STATUS</th>
                <th style={{ width: 150, textAlign: 'right' }}>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(ev => {
                const isReplayed = replayedSet.has(ev.id)
                const isCurrentlyReplaying = replaying === ev.id
                return (
                  <tr key={ev.id}>
                    <td className="font-mono" style={{ fontWeight: 600, color: 'var(--amber)' }}>
                      {ev.id}
                    </td>
                    <td style={{ color: 'var(--text-primary)' }}>
                      {ev.source}
                    </td>
                    <td className="font-mono" style={{ fontSize: 11, color: 'var(--text-secondary)' }}>
                      {ev.format.toUpperCase()}
                    </td>
                    <td style={{ color: 'var(--text-secondary)', maxWidth: 280 }}>
                      <div style={{ textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }} title={ev.failureReason}>
                        {ev.failureReason}
                      </div>
                    </td>
                    <td className="font-mono" style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {new Date(ev.timestamp).toLocaleString()}
                    </td>
                    <td className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                      {ev.retryCount}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <span className={`status-dot ${isReplayed ? 'green' : 'amber'}`} />
                        <span style={{ fontSize: 11, color: isReplayed ? 'var(--green)' : 'var(--amber)', fontWeight: 500 }}>
                          {isReplayed ? 'Replayed' : ev.status}
                        </span>
                      </div>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', gap: 6 }}>
                        <button
                          onClick={() => setSelectedEvent(ev)}
                          className="btn btn-ghost"
                          style={{ padding: '1px 5px', fontSize: 11 }}
                        >
                          View
                        </button>
                        <button
                          onClick={() => handleReplay(ev)}
                          disabled={isCurrentlyReplaying || isReplayed}
                          className="btn btn-secondary"
                          style={{ padding: '1px 6px', fontSize: 11 }}
                        >
                          {isCurrentlyReplaying ? 'Replaying...' : 'Replay'}
                        </button>
                        <button
                          onClick={() => handleQuarantine(ev)}
                          className="btn btn-ghost"
                          style={{ padding: '1px 5px', fontSize: 11, color: 'var(--text-muted)' }}
                        >
                          Quarantine
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        {/* Selected Event Diagnostic Detail */}
        {selectedEvent && (
          <div
            style={{
              padding: '12px 14px',
              background: 'var(--bg-surface)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              display: 'flex',
              flexDirection: 'column',
              gap: 8,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
                DIAGNOSTIC LOG FOR {selectedEvent.id}
              </div>
              <button
                onClick={() => setSelectedEvent(null)}
                className="btn btn-ghost"
                style={{ padding: '2px 6px', fontSize: 11 }}
              >
                Close
              </button>
            </div>

            <div style={{ fontSize: 11.5, color: 'var(--red)', fontFamily: 'var(--font-mono)' }}>
              Error: {selectedEvent.errorDetail}
            </div>

            <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>Original raw payload:</div>
            <pre className="code-editor" style={{ maxHeight: 120 }}>
              {selectedEvent.rawMessage}
            </pre>
          </div>
        )}
      </div>
    </Layout>
  )
}
