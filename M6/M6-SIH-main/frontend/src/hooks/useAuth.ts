import { useEffect, useState } from 'react'
import { authStore } from '../store/auth'
import type { User } from '../types'

export function useAuth() {
  const [user, setUser] = useState<User | null>(authStore.getUser())
  const [token, setToken] = useState<string | null>(authStore.getToken())

  useEffect(() => {
    return authStore.subscribe(() => {
      setUser(authStore.getUser())
      setToken(authStore.getToken())
    })
  }, [])

  return { user, token, isAuthenticated: !!token }
}
