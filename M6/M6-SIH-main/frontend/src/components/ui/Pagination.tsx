import React from 'react'

interface Props { page: number; pages: number; total: number; onPage: (p: number) => void }

export function Pagination({ page, pages, total, onPage }: Props) {
  if (pages <= 1) return null
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 0', color: 'var(--text-muted)', fontSize: 13 }}>
      <span>Total: {total}</span>
      <div style={{ flex: 1 }} />
      <button onClick={() => onPage(page - 1)} disabled={page <= 1} style={btnStyle}>‹ Prev</button>
      <span>Page {page} / {pages}</span>
      <button onClick={() => onPage(page + 1)} disabled={page >= pages} style={btnStyle}>Next ›</button>
    </div>
  )
}

const btnStyle: React.CSSProperties = {
  padding: '4px 12px', background: 'var(--bg-elevated)', border: '1px solid var(--border)',
  color: 'var(--text-primary)', borderRadius: 4, cursor: 'pointer',
}
