import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Building2, FileCheck2, Clock3, CheckCircle2, CalendarClock, AlertTriangle,
  Undo2, ShieldAlert, RefreshCcw, Landmark,
} from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import api from '../api'
import { useAuth } from '../auth'
import { Card, KpiCard, Spinner, Badge } from '../components'

const PIE_COLORS = ['#2563EB', '#16A34A', '#F59E0B', '#EF4444', '#8B5CF6', '#64748B']

export default function Dashboard() {
  const { user } = useAuth()
  const [kpis, setKpis] = useState<any>(null)
  const [charts, setCharts] = useState<any>(null)

  useEffect(() => {
    api.get('/dashboard/kpis').then((r) => setKpis(r.data))
    api.get('/dashboard/charts').then((r) => setCharts(r.data))
    api.post('/maturity/scan').catch(() => {})
  }, [])

  if (!kpis || !charts) return <Spinner />
  const isOfficer = user?.role === 'officer' || user?.role === 'admin'

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-navy">
            {isOfficer ? 'AICTE Command Centre' : user?.role === 'bank' ? 'Bank Verification Desk' : 'Institution Dashboard'}
          </h1>
          <p className="text-xs text-slate-500">Security deposit &amp; FDR lifecycle overview · DEMO data</p>
        </div>
        <Link to="/reports" className="text-xs text-royal hover:underline">Export reports →</Link>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-3">
        {isOfficer && <KpiCard label="Institutions" value={kpis.institutions} icon={<Building2 size={18} />} />}
        <KpiCard label="Total FDRs" value={kpis.total_fdrs} icon={<FileCheck2 size={18} />} />
        <KpiCard label="Active" value={kpis.active_fdrs} icon={<CheckCircle2 size={18} />} />
        <KpiCard label="Pending verification" value={kpis.pending_verification} icon={<Clock3 size={18} />} tone="text-amber-600" />
        <KpiCard label="Verified" value={kpis.verified_fdrs} icon={<ShieldAlert size={18} />} tone="text-gov-green" />
        <KpiCard label="Maturing ≤90d" value={kpis.upcoming_maturity_90d} icon={<CalendarClock size={18} />} tone="text-amber-600" />
        <KpiCard label="Expired / overdue" value={kpis.expired_fdrs} icon={<AlertTriangle size={18} />} tone="text-red-600" />
        <KpiCard label="Renewals pending" value={kpis.renewal_pending} icon={<RefreshCcw size={18} />} />
        <KpiCard label="Release requests" value={kpis.release_pending} icon={<Undo2 size={18} />} />
        <KpiCard label="High-risk records" value={kpis.high_risk} icon={<Landmark size={18} />} tone="text-red-600" />
      </div>

      <div className="grid lg:grid-cols-2 gap-5">
        <Card title="Institution-wise FDR distribution (top 10)">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={charts.institution_distribution} layout="vertical" margin={{ left: 10, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 10 }}
                tickFormatter={(v: string) => (v.length > 22 ? v.slice(0, 21) + '…' : v)} />
              <Tooltip />
              <Bar dataKey="count" fill="#2563EB" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Bank-wise FDR distribution">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={charts.bank_distribution} dataKey="count" nameKey="name" outerRadius={90} label={({ percent }: any) => `${(percent * 100).toFixed(0)}%`}>
                {charts.bank_distribution.map((_: any, i: number) => (
                  <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                ))}
              </Pie>
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Monthly FDR submissions">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={charts.monthly_submissions}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#16A34A" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Upcoming maturity & verification status">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={charts.maturity_buckets}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#F59E0B" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <div className="flex gap-2 mt-3 flex-wrap">
            {charts.verification_status.map((v: any) => (
              <span key={v.name} className="text-xs flex items-center gap-1.5">
                <Badge value={v.name} /> {v.count}
              </span>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
