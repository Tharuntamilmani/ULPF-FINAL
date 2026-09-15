import type { User } from '../types'

export interface AuthState {
  user: User | null
  token: string | null
  setAuth: (token: string, user: User) => void
  clearAuth: () => void
}

let _user: User | null = null
let _token: string | null = typeof window !== 'undefined' ? localStorage.getItem('token') : null
const _listeners: Set<() => void> = new Set()

function notify() { _listeners.forEach(l => l()) }

export const authStore = {
  getUser: () => _user,
  getToken: () => _token,
  setAuth: (token: string, user: User) => {
    _token = token
    _user = user
    if (typeof window !== 'undefined') localStorage.setItem('token', token)
    notify()
  },
  clearAuth: () => {
    _token = null
    _user = null
    if (typeof window !== 'undefined') localStorage.removeItem('token')
    notify()
  },
  subscribe: (listener: () => void) => {
    _listeners.add(listener)
    return () => { _listeners.delete(listener) }
  },
}
