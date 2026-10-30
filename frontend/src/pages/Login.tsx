import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ShieldCheck } from 'lucide-react'
import { useAuth } from '../auth'
import { inputCls, btnPrimary } from '../components'

const DEMO_CREDS = [
  { role: 'Institution', email: 'institution@fdrsetu.demo' },
  { role: 'AICTE Officer', email: 'officer@fdrsetu.demo' },
  { role: 'Bank Officer', email: 'bank@fdrsetu.demo' },
  { role: 'Super Admin', email: 'admin@fdrsetu.demo' },
]

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      await login(email.trim(), password)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-navy via-navy to-royal flex items-center justify-center p-4">
      <div className="w-full max-w-4xl grid md:grid-cols-2 rounded-2xl overflow-hidden shadow-2xl">
        <div className="bg-navy text-white p-10 hidden md:flex flex-col justify-center">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-royal flex items-center justify-center"><ShieldCheck size={26} /></div>
            <div>
              <div className="text-2xl font-bold">FDRSETU</div>
              <div className="text-xs text-blue-200">AICTE Regulation Bureau</div>
            </div>
          </div>
          <p className="text-blue-100 text-sm leading-relaxed mb-2">
            Fixed Deposit Registration, Evaluation, Security &amp; Tracking Utility
          </p>
          <p className="text-blue-300 text-xs italic">Every FDR Connected. Every Deposit Secured. Every Maturity Tracked.</p>
          <div className="mt-8 text-[11px] text-blue-300/70">
            Smart India Hackathon 2026 · Problem Statement 26265 · DEMO / SYNTHETIC DATA
          </div>
        </div>
        <div className="bg-white p-8">
          <h1 className="text-lg font-bold text-navy mb-1">Sign in</h1>
          <p className="text-xs text-slate-500 mb-5">Secure role-based access to the FDR portal</p>
          <form onSubmit={submit} className="space-y-4">
            <label className="block">
              <span className="block text-xs font-medium text-slate-600 mb-1">Email</span>
              <input className={inputCls} type="email" required value={email}
                onChange={(e) => setEmail(e.target.value)} placeholder="you@fdrsetu.demo" />
            </label>
            <label className="block">
              <span className="block text-xs font-medium text-slate-600 mb-1">Password</span>
              <input className={inputCls} type="password" required value={password}
                onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" />
            </label>
            {error && <div className="text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</div>}
            <button className={`${btnPrimary} w-full justify-center`} disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
          <div className="mt-6">
            <div className="text-xs font-semibold text-slate-500 mb-2">Demo credentials — password <code className="bg-slate-100 px-1 rounded">Demo@123</code></div>
            <div className="grid grid-cols-2 gap-2">
              {DEMO_CREDS.map((c) => (
                <button key={c.email} type="button"
                  onClick={() => { setEmail(c.email); setPassword('Demo@123') }}
                  className="text-left border border-slate-200 rounded-lg px-3 py-2 hover:border-royal hover:bg-sky-light transition-colors">
                  <div className="text-xs font-semibold text-navy">{c.role}</div>
                  <div className="text-[10px] text-slate-500 truncate">{c.email}</div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
