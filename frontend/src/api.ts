import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('fdrsetu_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('fdrsetu_token')
      localStorage.removeItem('fdrsetu_user')
      if (!location.pathname.startsWith('/login')) location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default api

export interface User {
  id: number
  email: string
  full_name: string
  role: 'institution' | 'officer' | 'bank' | 'admin'
  institution_id?: number
  institution_name?: string
  bank_id?: number
  bank_name?: string
}

export const roleLabel: Record<User['role'], string> = {
  institution: 'Institution',
  officer: 'AICTE Officer',
  bank: 'Bank Officer',
  admin: 'Super Admin',
}
