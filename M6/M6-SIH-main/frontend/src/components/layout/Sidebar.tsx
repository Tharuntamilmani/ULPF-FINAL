import React from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import { authStore } from '../../store/auth'
import { useAuth } from '../../hooks/useAuth'
import { ChevronLeft, ChevronRight, LogOut } from 'lucide-react'

interface NavItem {
  to: string
  label: string
  matches: (pathname: string) => boolean
}

const NAV_ITEMS: NavItem[] = [
  {
    to: '/dashboard',
    label: 'Dashboard',
    matches: p => p === '/' || p.startsWith('/dashboard') || p.startsWith('/pipeline'),
  },
  {
    to: '/events',
    label: 'Events',
    matches: p =>
      p.startsWith('/events') ||
      p.startsWith('/live-events') ||
      p.startsWith('/raw-events') ||
      p.startsWith('/ues-events'),
  },
  {
    to: '/parsers',
    label: 'Parsers',
    matches: p => p.startsWith('/parsers') || p.startsWith('/parser-studio'),
  },
  {
    to: '/traceability',
    label: 'Traceability',
    matches: p => p.startsWith('/traceability') || p.startsWith('/raw-evidence'),
  },
  {
    to: '/system',
    label: 'System',
    matches: p =>
      p.startsWith('/system') ||
      p.startsWith('/health') ||
      p.startsWith('/dlq') ||
      p.startsWith('/replay') ||
      p.startsWith('/audit') ||
      p.startsWith('/observability') ||
      p.startsWith('/services') ||
      p.startsWith('/architecture'),
  },
  {
    to: '/settings',
    label: 'Settings',
    matches: p =>
      p.startsWith('/settings') ||
      p.startsWith('/control-plane') ||
      p.startsWith('/tenants') ||
      p.startsWith('/sources') ||
      p.startsWith('/mappings') ||
      p.startsWith('/policies') ||
      p.startsWith('/schemas') ||
      p.startsWith('/configuration') ||
      p.startsWith('/demo'),
  },
]

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const { user } = useAuth()

  const handleLogout = () => {
    authStore.clearAuth()
    navigate('/login')
  }

  const w = collapsed ? 54 : 224

  return (
    <aside
      style={{
        width: w,
        flexShrink: 0,
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        position: 'sticky',
        top: 0,
        transition: 'width 0.15s ease',
        overflow: 'hidden',
        userSelect: 'none',
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: collapsed ? '14px 0' : '16px 16px 14px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: collapsed ? 'center' : 'flex-start',
          minHeight: 60,
          background: 'var(--bg-surface)',
        }}
      >
        {!collapsed ? (
          <div>
            <div style={{ fontWeight: 700, fontSize: 17, color: 'var(--text-primary)', letterSpacing: '0.02em', lineHeight: 1.2 }}>
              ULPF
            </div>
            <div style={{ fontSize: 11.5, color: 'var(--text-secondary)', letterSpacing: '0.01em', marginTop: 3, whiteSpace: 'nowrap' }}>
              Universal Log Pre-Processing
            </div>
          </div>
        ) : (
          <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--accent)' }}>U</div>
        )}
      </div>

      {/* Navigation Links — 13.5px Readable Font & Comfortable Padding */}
      <nav style={{ flex: 1, padding: '14px 0', overflowY: 'auto' }}>
        {NAV_ITEMS.map(({ to, label, matches }) => {
          const isActive = matches(location.pathname)
          return (
            <NavLink
              key={to}
              to={to}
              title={collapsed ? label : undefined}
              style={{
                display: 'flex',
                alignItems: 'center',
                padding: collapsed ? '10px 0' : '9px 18px',
                justifyContent: collapsed ? 'center' : 'flex-start',
                color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                background: isActive ? 'var(--accent-subtle)' : 'transparent',
                borderLeft: !collapsed
                  ? isActive
                    ? '3px solid var(--accent)'
                    : '3px solid transparent'
                  : 'none',
                fontWeight: isActive ? 600 : 400,
                fontSize: 13.5,
                transition: 'background 0.1s ease, color 0.1s ease',
                textDecoration: 'none',
                marginBottom: 2,
              }}
            >
              {collapsed ? (
                <span style={{ fontSize: 13, fontWeight: 600 }}>{label.slice(0, 1)}</span>
              ) : (
                <span>{label}</span>
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer Controls */}
      <div style={{ padding: collapsed ? '8px 0' : '10px 14px', borderTop: '1px solid var(--border)', background: 'var(--bg-elevated)' }}>
        {!collapsed && user && (
          <div
            style={{
              fontSize: 12,
              fontWeight: 500,
              color: 'var(--text-primary)',
              padding: '2px 4px 6px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
            }}
          >
            {user.username}
          </div>
        )}
        <button
          onClick={handleLogout}
          title={collapsed ? 'Logout' : undefined}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: collapsed ? 'center' : 'flex-start',
            gap: 8,
            width: '100%',
            padding: collapsed ? '6px 0' : '6px 8px',
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            background: 'transparent',
            color: 'var(--text-secondary)',
            fontSize: 12.5,
            cursor: 'pointer',
          }}
        >
          <LogOut size={13} />
          {!collapsed && <span>Logout</span>}
        </button>

        <button
          onClick={onToggle}
          title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100%',
            padding: '6px 0',
            marginTop: 4,
            borderRadius: 'var(--radius-sm)',
            border: 'none',
            background: 'transparent',
            color: 'var(--text-muted)',
            cursor: 'pointer',
          }}
        >
          {collapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
        </button>
      </div>
    </aside>
  )
}
