import React from 'react'
import type { HealthStatus, ParserStatus, SourceStatus, ReplayStatus } from '../../types'

type AnyStatus = HealthStatus | ParserStatus | SourceStatus | ReplayStatus | string

const STATUS_STYLES: Record<string, string> = {
  // Health
  HEALTHY:         'background:#16a34a22;color:#22c55e;border:1px solid #22c55e44',
  DEGRADED:        'background:#ca8a0422;color:#eab308;border:1px solid #eab30844',
  UNHEALTHY:       'background:#dc262622;color:#ef4444;border:1px solid #ef444444',
  UNAVAILABLE:     'background:#71717a22;color:#a1a1aa;border:1px solid #a1a1aa44',
  UNKNOWN:         'background:#71717a22;color:#a1a1aa;border:1px solid #a1a1aa44',
  // Parser
  DRAFT:           'background:#1d4ed822;color:#60a5fa;border:1px solid #60a5fa44',
  PENDING_APPROVAL:'background:#92400e22;color:#fbbf24;border:1px solid #fbbf2444',
  APPROVED:        'background:#065f4622;color:#34d399;border:1px solid #34d39944',
  ACTIVE:          'background:#16a34a22;color:#22c55e;border:1px solid #22c55e44',
  DISABLED:        'background:#71717a22;color:#a1a1aa;border:1px solid #a1a1aa44',
  ROLLED_BACK:     'background:#7c3aed22;color:#a78bfa;border:1px solid #a78bfa44',
  // Source
  active:          'background:#16a34a22;color:#22c55e;border:1px solid #22c55e44',
  inactive:        'background:#71717a22;color:#a1a1aa;border:1px solid #a1a1aa44',
  disabled:        'background:#dc262622;color:#ef4444;border:1px solid #ef444444',
  // Replay
  REQUESTED:       'background:#1d4ed822;color:#60a5fa;border:1px solid #60a5fa44',
  QUEUED:          'background:#92400e22;color:#fbbf24;border:1px solid #fbbf2444',
  PROCESSING:      'background:#1d4ed822;color:#93c5fd;border:1px solid #93c5fd44',
  SUCCESS:         'background:#16a34a22;color:#22c55e;border:1px solid #22c55e44',
  FAILED:          'background:#dc262622;color:#ef4444;border:1px solid #ef444444',
}

export function StatusBadge({ status }: { status: AnyStatus }) {
  const style = STATUS_STYLES[status] ?? STATUS_STYLES.UNKNOWN
  return (
    <span style={{
      ...Object.fromEntries(style.split(';').filter(Boolean).map(s => {
        const [k, v] = s.split(':')
        return [k.trim().replace(/-([a-z])/g, (_, c) => c.toUpperCase()), v.trim()]
      })),
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '11px',
      fontWeight: 600,
      letterSpacing: '0.03em',
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
    }}>
      {status}
    </span>
  )
}
