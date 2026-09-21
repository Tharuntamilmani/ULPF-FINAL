import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { login, getMe } from '../api/endpoints'
import { authStore } from '../store/auth'

export function LoginPage() {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('Admin_Secure_Pass_2026!')
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data: tokenData } = await login(username, password)
      authStore.setAuth(tokenData.access_token, null as any)
      const { data: user } = await getMe()
      authStore.setAuth(tokenData.access_token, user)
      navigate('/dashboard')
    } catch {
      toast.error('Invalid credentials or M6 backend offline')
    } finally {
      setLoading(false)
    }
  }

  const handleDemoBypass = () => {
    authStore.setAuth('demo-token-sih-evaluator', {
      id: 'demo-admin-id',
      username: 'secops-analyst',
      email: 'secops@ulpf.internal',
      is_active: true,
      is_superuser: true,
      roles: [{ id: 'r1', name: 'Security Engineer', description: 'Operations Access' }],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    })
    toast.success('Logged in with Demo Access')
    navigate('/dashboard')
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-base)' }}>
      <div style={{ width: 340, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: '24px 24px' }}>
        <div style={{ textAlign: 'center', marginBottom: 20 }}>
          <h1 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', letterSpacing: '0.04em' }}>
            ULPF CONSOLE
          </h1>
          <p style={{ color: 'var(--text-secondary)', marginTop: 3, fontSize: 11.5 }}>
            Universal Log Pre-Processing Framework
          </p>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 11.5, color: 'var(--text-secondary)', fontWeight: 600 }}>Username</label>
            <input
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              style={{ width: '100%' }}
              placeholder="admin"
              autoComplete="username"
            />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: 4, fontSize: 11.5, color: 'var(--text-secondary)', fontWeight: 600 }}>Password</label>
            <input
              value={password}
              onChange={e => setPassword(e.target.value)}
              type="password"
              required
              style={{ width: '100%' }}
              placeholder="••••••••"
              autoComplete="current-password"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary"
            style={{ width: '100%', padding: '7px 12px', marginTop: 4 }}
          >
            {loading ? 'Authenticating…' : 'Sign in'}
          </button>
        </form>

        <div style={{ margin: '16px 0', borderTop: '1px solid var(--border)', position: 'relative', textAlign: 'center' }}>
          <span style={{ position: 'relative', top: -9, background: 'var(--bg-surface)', padding: '0 8px', fontSize: 10.5, color: 'var(--text-muted)' }}>
            OR
          </span>
        </div>

        <button
          type="button"
          onClick={handleDemoBypass}
          className="btn btn-secondary"
          style={{ width: '100%', padding: '6px 12px' }}
        >
          Sign in as Operator (Demo Access)
        </button>
      </div>
    </div>
  )
}
