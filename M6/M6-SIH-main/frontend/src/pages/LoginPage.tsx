import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { login, getMe } from '../api/endpoints'
import { authStore } from '../store/auth'
import { Radio } from 'lucide-react'

export function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
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
      toast.error('Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--bg-base)' }}>
      <div style={{ width: 360, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 12, padding: 32 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <Radio size={32} color="var(--accent)" style={{ marginBottom: 10 }} />
          <h1 style={{ fontSize: 18, fontWeight: 700 }}>ULPF M6 Control Plane</h1>
          <p style={{ color: 'var(--text-muted)', marginTop: 4, fontSize: 13 }}>Sign in to continue</p>
        </div>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ display: 'block', marginBottom: 5, fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>Username</label>
            <input value={username} onChange={e => setUsername(e.target.value)} required
              style={inputStyle} placeholder="admin" autoComplete="username" />
          </div>
          <div>
            <label style={{ display: 'block', marginBottom: 5, fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>Password</label>
            <input value={password} onChange={e => setPassword(e.target.value)} type="password" required
              style={inputStyle} placeholder="••••••••" autoComplete="current-password" />
          </div>
          <button type="submit" disabled={loading} style={btnStyle}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%', padding: '8px 12px', background: 'var(--bg-base)',
  border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text-primary)',
  fontSize: 14, outline: 'none',
}
const btnStyle: React.CSSProperties = {
  width: '100%', padding: '10px', background: 'var(--accent)', border: 'none',
  borderRadius: 6, color: '#fff', fontWeight: 600, fontSize: 14, cursor: 'pointer', marginTop: 4,
}
