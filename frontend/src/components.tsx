import { useEffect, useRef, useState, type ReactNode } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import {
  LayoutDashboard, Building2, FilePlus2, FileScan, FileCheck2, ShieldAlert,
  Landmark, CalendarClock, Undo2, BarChart3, Bot, Users, ScrollText,
  Settings, LogOut, Bell, Menu, X, ShieldCheck,
} from 'lucide-react'
import api, { type User, roleLabel } from './api'
import { useAuth } from './auth'

/* ---------- primitives ---------- */

export function Card({ title, children, className = '', action }: {
  title?: string; children: ReactNode; className?: string; action?: ReactNode
}) {
  return (
    <div className={`bg-white rounded-xl border border-slate-200 shadow-sm ${className}`}>
      {title && (
        <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-semibold text-navy text-sm">{title}</h3>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </div>
  )
}

const badgeColors: Record<string, string> = {
  verified: 'bg-green-100 text-green-800', active: 'bg-green-100 text-green-800',
  approved: 'bg-green-100 text-green-800', done: 'bg-green-100 text-green-800',
  pending: 'bg-amber-100 text-amber-800', in_review: 'bg-amber-100 text-amber-800',
  under_review: 'bg-amber-100 text-amber-800', submitted: 'bg-amber-100 text-amber-800',
  rejected: 'bg-red-100 text-red-800', expired: 'bg-red-100 text-red-800',
  high: 'bg-red-100 text-red-800', failed: 'bg-red-100 text-red-800',
  medium: 'bg-orange-100 text-orange-800', low: 'bg-blue-100 text-blue-800',
  none: 'bg-slate-100 text-slate-600', released: 'bg-slate-200 text-slate-700',
  renewed: 'bg-indigo-100 text-indigo-800', mock: 'bg-purple-100 text-purple-800',
  open: 'bg-amber-100 text-amber-800', reviewed: 'bg-blue-100 text-blue-800',
  dismissed: 'bg-slate-100 text-slate-600', completed: 'bg-green-100 text-green-800',
  mismatch: 'bg-orange-100 text-orange-800',
}

export function Badge({ value }: { value: string }) {
  const cls = badgeColors[value] ?? 'bg-slate-100 text-slate-700'
  return (
    <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${cls}`}>
      {value.replace(/_/g, ' ')}
    </span>
  )
}

export function KpiCard({ label, value, icon, tone = 'text-navy' }: {
  label: string; value: ReactNode; icon?: ReactNode; tone?: string
}) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 flex items-center gap-3">
      {icon && <div className="p-2.5 rounded-lg bg-sky-light text-royal">{icon}</div>}
      <div>
        <div className="text-xs text-slate-500">{label}</div>
        <div className={`text-xl font-bold ${tone}`}>{value}</div>
      </div>
    </div>
  )
}

export function Field({ label, children, hint }: { label: string; children: ReactNode; hint?: string }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium text-slate-600 mb-1">{label}</span>
      {children}
      {hint && <span className="block text-xs text-amber-600 mt-0.5">{hint}</span>}
    </label>
  )
}

export const inputCls =
  'w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-royal/40 focus:border-royal bg-white'

export const btnPrimary =
  'inline-flex items-center gap-1.5 bg-royal hover:bg-navy text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-50'
export const btnGhost =
  'inline-flex items-center gap-1.5 border border-slate-300 hover:bg-slate-50 text-slate-700 text-sm font-medium px-3 py-2 rounded-lg transition-colors'

export function Th({ children }: { children?: ReactNode }) {
  return <th className="text-left text-xs font-semibold text-slate-500 uppercase tracking-wide px-3 py-2.5 whitespace-nowrap">{children}</th>
}
export function Td({ children, className = '' }: { children?: ReactNode; className?: string }) {
  return <td className={`px-3 py-2.5 text-sm text-slate-700 whitespace-nowrap ${className}`}>{children}</td>
}

export function Empty({ msg }: { msg: string }) {
  return <div className="py-10 text-center text-sm text-slate-400">{msg}</div>
}

export function Spinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="w-6 h-6 border-2 border-royal border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

export const inr = (n?: number | null) =>
  n == null ? '—' : `₹${n.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

/* ---------- layout ---------- */

const NAV = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard, roles: ['institution', 'officer', 'bank', 'admin'] },
  { to: '/institutions', label: 'Institutions', icon: Building2, roles: ['institution', 'officer', 'admin'] },
  { to: '/fdrs/register', label: 'FDR Registration', icon: FilePlus2, roles: ['institution', 'officer', 'admin'] },
  { to: '/fdrs/upload', label: 'Document Upload & AI', icon: FileScan, roles: ['institution', 'officer', 'admin'] },
  { to: '/fdrs', label: 'FDR Records', icon: FileCheck2, roles: ['institution', 'officer', 'bank', 'admin'] },
  { to: '/verification', label: 'Verification', icon: ShieldCheck, roles: ['institution', 'officer', 'admin'] },
  { to: '/risk', label: 'Risk & Duplicates', icon: ShieldAlert, roles: ['institution', 'officer', 'bank', 'admin'] },
  { to: '/bank-verification', label: 'Bank Verification', icon: Landmark, roles: ['bank', 'officer', 'admin'] },
  { to: '/maturity', label: 'Maturity & Renewal', icon: CalendarClock, roles: ['institution', 'officer', 'bank', 'admin'] },
  { to: '/releases', label: 'Release / Refund', icon: Undo2, roles: ['institution', 'officer', 'admin'] },
  { to: '/reports', label: 'Reports & Analytics', icon: BarChart3, roles: ['institution', 'officer', 'admin'] },
  { to: '/copilot', label: 'AI FDR Copilot', icon: Bot, roles: ['institution', 'officer', 'bank', 'admin'] },
  { to: '/users', label: 'Users & Roles', icon: Users, roles: ['admin'] },
  { to: '/audit', label: 'Audit Logs', icon: ScrollText, roles: ['officer', 'admin'] },
  { to: '/settings', label: 'Profile & Settings', icon: Settings, roles: ['institution', 'officer', 'bank', 'admin'] },
]

interface Notif { id: number; title: string; message: string; kind: string; is_read: boolean; created_at: string }

function Topbar({ user, onMenu }: { user: User; onMenu: () => void }) {
  const { logout } = useAuth()
  const [notifs, setNotifs] = useState<Notif[]>([])
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  const load = () => api.get('/notifications').then((r) => setNotifs(r.data)).catch(() => {})
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t) }, [])
  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false) }
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])

  const unread = notifs.filter((n) => !n.is_read).length

  return (
    <header className="h-14 bg-navy text-white flex items-center px-4 gap-3 sticky top-0 z-30">
      <button className="lg:hidden" onClick={onMenu}><Menu size={20} /></button>
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-royal flex items-center justify-center font-bold text-sm">FS</div>
        <div>
          <div className="font-semibold text-sm leading-tight">FDRSETU</div>
          <div className="text-[10px] text-blue-200 leading-tight">AICTE Regulation Bureau</div>
        </div>
      </div>
      <div className="flex-1" />
      <div className="relative" ref={ref}>
        <button onClick={() => setOpen(!open)} className="relative p-2 rounded-lg hover:bg-white/10">
          <Bell size={18} />
          {unread > 0 && (
            <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-[10px] w-4 h-4 rounded-full flex items-center justify-center">{unread}</span>
          )}
        </button>
        {open && (
          <div className="absolute right-0 mt-2 w-96 max-h-96 overflow-y-auto bg-white text-slate-800 rounded-xl shadow-xl border border-slate-200">
            <div className="px-4 py-2.5 border-b border-slate-100 flex justify-between items-center">
              <span className="text-sm font-semibold text-navy">Notifications</span>
              <button className="text-xs text-royal" onClick={() => { api.post('/notifications/read-all').then(load) }}>Mark all read</button>
            </div>
            {notifs.length === 0 && <div className="p-4 text-sm text-slate-400">No notifications</div>}
            {notifs.map((n) => (
              <div key={n.id} className={`px-4 py-3 border-b border-slate-50 text-sm ${n.is_read ? 'opacity-60' : ''}`}>
                <div className="font-medium text-navy">{n.title}</div>
                <div className="text-xs text-slate-500 mt-0.5">{n.message}</div>
                <div className="text-[10px] text-slate-400 mt-1">{new Date(n.created_at).toLocaleString()}</div>
              </div>
            ))}
          </div>
        )}
      </div>
      <div className="text-right hidden sm:block">
        <div className="text-sm font-medium leading-tight">{user.full_name}</div>
        <div className="text-[10px] text-blue-200">{roleLabel[user.role]}{user.institution_name ? ` · ${user.institution_name}` : ''}{user.bank_name ? ` · ${user.bank_name}` : ''}</div>
      </div>
      <button onClick={logout} title="Logout" className="p-2 rounded-lg hover:bg-white/10"><LogOut size={18} /></button>
    </header>
  )
}

export function Layout() {
  const { user } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const navigate = useNavigate()
  if (!user) { navigate('/login'); return null }
  const items = NAV.filter((n) => n.roles.includes(user.role))

  return (
    <div className="min-h-screen">
      <Topbar user={user} onMenu={() => setMobileOpen(true)} />
      <div className="flex">
        <aside className={`fixed lg:sticky top-14 z-20 h-[calc(100vh-3.5rem)] w-60 bg-white border-r border-slate-200 overflow-y-auto transition-transform lg:translate-x-0 ${mobileOpen ? 'translate-x-0' : '-translate-x-full'}`}>
          <div className="lg:hidden flex justify-end p-2"><button onClick={() => setMobileOpen(false)}><X size={18} /></button></div>
          <nav className="p-3 space-y-0.5">
            {items.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} end={to === '/'} onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive ? 'bg-sky-light text-royal' : 'text-slate-600 hover:bg-slate-50'}`}>
                <Icon size={17} /> {label}
              </NavLink>
            ))}
          </nav>
          <div className="p-4 mt-4 mx-3 rounded-lg bg-panel text-[11px] text-slate-500">
            DEMO / SYNTHETIC DATA — SIH 2026 prototype. Not an official AICTE system.
          </div>
        </aside>
        <main className="flex-1 p-4 lg:p-6 min-w-0">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
