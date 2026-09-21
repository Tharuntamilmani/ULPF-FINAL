import React from 'react'

export interface PipelineConnectorProps {
  isAnimating: boolean
  durationMs?: number
  animKey?: string | number
}

export function PipelineConnector({
  isAnimating,
  durationMs = 380,
  animKey,
}: PipelineConnectorProps) {
  return (
    <div
      style={{
        flex: 1,
        minWidth: 16,
        maxWidth: 38,
        height: 24,
        display: 'flex',
        alignItems: 'center',
        position: 'relative',
        userSelect: 'none',
        padding: '0 2px',
        flexShrink: 0,
      }}
    >
      {/* Background Track Line */}
      <div
        style={{
          width: '100%',
          height: 1.5,
          background: isAnimating ? 'var(--accent)' : 'var(--border)',
          transition: 'background 0.15s ease',
        }}
      />

      {/* Arrowhead */}
      <div
        style={{
          position: 'absolute',
          right: 0,
          top: '50%',
          transform: 'translateY(-50%)',
          width: 0,
          height: 0,
          borderTop: '3.5px solid transparent',
          borderBottom: '3.5px solid transparent',
          borderLeft: `5px solid ${isAnimating ? 'var(--accent)' : 'var(--text-muted)'}`,
          transition: 'border-left-color 0.15s ease',
        }}
      />

      {/* Moving Event / Pulse Dot Indicator */}
      {isAnimating && (
        <div
          key={animKey || 'pulse-dot'}
          style={{
            position: 'absolute',
            top: '50%',
            transform: 'translate3d(0, -50%, 0)',
            width: 6,
            height: 6,
            borderRadius: '50%',
            background: 'var(--accent)',
            animation: `pipelinePulseTraverse ${durationMs}ms ease-in-out forwards`,
            pointerEvents: 'none',
            zIndex: 2,
          }}
        />
      )}
    </div>
  )
}
