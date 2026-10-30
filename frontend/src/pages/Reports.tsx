import { useEffect, useState } from 'react'
import { FileSpreadsheet, FileText } from 'lucide-react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import api, { API_BASE } from '../api'
import { Card, Spinner, btnPrimary } from '../components'

const COLORS = ['#2563EB', '#16A34A', '#F59E0B', '#EF4444', '#8B5CF6']

export default function Reports() {
  const [charts, setCharts] = useState<any>(null)

  useEffect(() => { api.get('/dashboard/charts').then((r) => setCharts(r.data)) }, [])
  if (!charts) return <Spinner />

  const download = (path: string) => {
    const token = localStorage.getItem('fdrsetu_token')
    fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement('a')
        a.href = URL.createObjectURL(blob)
        a.download = path.split('/').pop()!
        a.click()
      })
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-navy">Reports &amp; Analytics</h1>
          <p className="text-xs text-slate-500">Operational analytics across the FDR lifecycle. All figures DEMO.</p>
        </div>
        <div className="flex gap-2">
          <button className={btnPrimary} onClick={() => download('/reports/fdrs.xlsx')}><FileSpreadsheet size={15} /> Excel export</button>
          <button className={btnPrimary} onClick={() => download('/reports/fdrs.pdf')}><FileText size={15} /> PDF export</button>
        </div>
      </div>

      <div className="grid lg:grid-cols-2 gap-5">
        <Card title="Verification status">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={charts.verification_status} dataKey="count" nameKey="name" outerRadius={85} label>
                {charts.verification_status.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Legend wrapperStyle={{ fontSize: 11 }} /><Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Release request status">
          <ResponsiveContainer width="100%" height={240}>
            <PieChart>
              <Pie data={charts.release_status} dataKey="count" nameKey="name" outerRadius={85} label>
                {charts.release_status.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Legend wrapperStyle={{ fontSize: 11 }} /><Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Monthly FDR submissions">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={charts.monthly_submissions}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="month" tick={{ fontSize: 10 }} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip /><Bar dataKey="count" fill="#2563EB" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
        <Card title="Upcoming maturity">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={charts.maturity_buckets}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="name" tick={{ fontSize: 11 }} /><YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
              <Tooltip /><Bar dataKey="count" fill="#F59E0B" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>
    </div>
  )
}
