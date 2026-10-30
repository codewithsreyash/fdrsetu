import { createContext, useContext, useState, type ReactNode } from 'react'
import api, { type User } from './api'

interface AuthCtx {
  user: User | null
  login: (email: string, password: string) => Promise<User>
  logout: () => void
}

const Ctx = createContext<AuthCtx>(null as unknown as AuthCtx)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(() => {
    const raw = localStorage.getItem('fdrsetu_user')
    try { return raw ? JSON.parse(raw) : null } catch { return null }
  })

  async function login(email: string, password: string) {
    const res = await api.post('/auth/login', { email, password })
    localStorage.setItem('fdrsetu_token', res.data.access_token)
    localStorage.setItem('fdrsetu_user', JSON.stringify(res.data.user))
    setUser(res.data.user)
    return res.data.user as User
  }

  function logout() {
    api.post('/auth/logout').catch(() => {})
    localStorage.removeItem('fdrsetu_token')
    localStorage.removeItem('fdrsetu_user')
    setUser(null)
    location.href = '/login'
  }

  return <Ctx.Provider value={{ user, login, logout }}>{children}</Ctx.Provider>
}

export const useAuth = () => useContext(Ctx)
