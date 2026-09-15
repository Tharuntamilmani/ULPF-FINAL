import React from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard,
  Building2,
  Workflow,
  Search,
  Server,
  Code2,
  Database,
  GitMerge,
  Shield,
  Activity,
  ClipboardList,
  RotateCcw,
  Settings,
  LogOut,
  Radio,
  User,
} from 'lucide-react'
import { authStore } from '../../store/auth'
import { useAuth } from '../../hooks/useAuth'

const NAV = [
  { to: '/dashboard',     icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/pipeline',      icon: Workflow,        label: 'Event Pipeline' },
  { to: '/events',        icon: Search,          label: 'Live Explorer' },
  { to: '/tenants',       icon: Building2,       label: 'Tenants' },
  { to: '/sources',       icon: Server,          label: 'Sources' },
  { to: '/parsers',       icon: Code2,           label: 'Parsers' },
  { to: '/schemas',       icon: Database,        label: 'Schemas' },
  { to: '/mappings',      icon: GitMerge,        label: 'Mappings' },
  { to: '/policies',      icon: Shield,          label: 'Policies' },
  { to: '/services',      icon: Activity,        label: 'Services' },
  { to: '/audit',         icon: ClipboardList,   label: 'Audit' },
  { to: '/replay',        icon: RotateCcw,       label: 'Replay' },
  { to: '/configuration', icon: Settings,        label: 'Configuration' },
]

const linkStyle = (isActive: boolean): React.CSSProperties => ({
  display: 'flex', alignItems: 'center', gap: 10, padding: '7px 12px',
  borderRadius: 6, color: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
  background: isActive ? 'var(--bg-hover)' : 'transparent',
  fontWeight: isActive ? 600 : 400, fontSize: 13, transition: 'all 0.15s',
  textDecoration: 'none',
})

export function Sidebar() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const handleLogout = () => { authStore.clearAuth(); navigate('/login') }

  return (
    <aside style={{
      width: 'var(--sidebar-w)', flexShrink: 0,
      background: 'var(--bg-surface)', borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', height: '100vh', position: 'sticky', top: 0,
    }}>
      {/* Brand */}
      <div style={{ padding: '16px 16px 12px', borderBottom: '1px solid var(--border)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Radio size={18} color="var(--accent)" />
          <div>
            <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)' }}>ULPF</div>
            <div style={{ fontSize: 10, color: 'var(--text-dim)', letterSpacing: '0.05em' }}>M6 CONTROL PLANE</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1, padding: '8px 8px', overflowY: 'auto' }}>
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink key={to} to={to} style={({ isActive }) => linkStyle(isActive)}>
            <Icon size={15} />
            {label}
          </NavLink>
        ))}
      </nav>

      {/* User Info & Logout */}
      <div style={{ padding: '10px 8px', borderTop: '1px solid var(--border)' }}>
        {user && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px', marginBottom: 4 }}>
            <User size={14} color="var(--accent)" />
            <div style={{ overflow: 'hidden' }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>
                {user.username}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>
                {user.is_superuser ? 'Super Admin' : (user.roles?.[0]?.name || 'Admin')}
              </div>
            </div>
          </div>
        )}
        <button
          onClick={handleLogout}
          style={{ ...linkStyle(false), width: '100%', border: 'none', background: 'transparent', cursor: 'pointer' }}
        >
          <LogOut size={15} />
          Logout
        </button>
      </div>
    </aside>
  )
}
