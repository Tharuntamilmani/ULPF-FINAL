import React from 'react'

export interface PipelineNodeProps {
  id: string
  label: string
  sublabel?: string
  description: string
  port?: number | string
  rate?: string
  status: 'idle' | 'active' | 'success' | 'error' | 'healthy' | 'degraded'
  latencyMs?: number | null
  isSelected?: boolean
  onClick?: () => void
  activeDataPill?: string
}

export function PipelineNode({
  id,
  label,
  description,
  status,
  isSelected,
  onClick,
}: PipelineNodeProps) {
  const isCurrentlyActive = status === 'active'

  const borderColor = isSelected
    ? 'var(--accent)'
    : isCurrentlyActive
    ? 'var(--accent)'
    : 'var(--border)'

  const bg = isSelected
    ? 'var(--accent-subtle)'
    : isCurrentlyActive
    ? 'var(--accent-subtle)'
    : 'var(--bg-surface)'

  const statusLabel = isCurrentlyActive
    ? 'Processing'
    : status === 'error'
    ? 'Failed'
    : 'Healthy'

  const statusDotClass = status === 'error'
    ? 'red'
    : 'green'

  return (
    <div
      onClick={onClick}
      style={{
        width: 126,
        height: 74,
        background: bg,
        border: `1px solid ${borderColor}`,
        borderRadius: 'var(--radius)',
        padding: '8px 10px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        cursor: 'pointer',
        transition: 'border-color 0.15s ease, background 0.15s ease',
        userSelect: 'none',
        flexShrink: 0,
      }}
    >
      <div>
        {/* Module Name */}
        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.02em', lineHeight: 1.2 }}>
          {label}
        </div>

        {/* Short Purpose */}
        <div style={{ fontSize: 10, color: 'var(--text-secondary)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {description}
        </div>
      </div>

      {/* Operational Status */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
        <span className={`status-dot ${statusDotClass}`} />
        <span
          style={{
            fontSize: 10.5,
            color: isCurrentlyActive ? 'var(--accent)' : 'var(--text-secondary)',
            fontWeight: isCurrentlyActive ? 700 : 500,
          }}
        >
          {statusLabel}
        </span>
      </div>
    </div>
  )
}
