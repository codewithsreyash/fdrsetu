import { useEffect, useState } from 'react'
import { RefreshCcw } from 'lucide-react'
import api from '../api'
import { useAuth } from '../auth'
import { Card, Badge, Spinner, Th, Td, Empty, inputCls, btnPrimary, btnGhost } from '../components'

export default function Risk() {
  const { user } = useAuth()
  const [alerts, setAlerts] = useState<any[] | null>(null)
  const [filter, setFilter] = useState({ status: 'open', severity: '' })
  const [scanning, setScanning] = useState(false)
  const canReview = user?.role === 'officer' || user?.role === 'admin'

  const load = () => api.get('/risk/alerts', { params: { status: filter.status || undefined, severity: filter.severity || undefined } })
    .then((r) => setAlerts(r.data))
  useEffect(() => { load() }, [filter])

  async function rescan() {
    setScanning(true)
    await api.post('/risk/scan')
    await load()
    setScanning(false)
  }

  async function review(id: number, status: string) {
    await api.post(`/risk/alerts/${id}/review`, { status })
    load()
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-navy">Risk &amp; Duplicate Detection</h1>
          <p className="text-xs text-slate-500">AI flags records for human review — it never declares an FDR fraudulent on its own.</p>
        </div>
        {canReview && <button className={btnPrimary} onClick={rescan} disabled={scanning}><RefreshCcw size={14} /> {scanning ? 'Scanning…' : 'Re-run checks'}</button>}
      </div>

      <Card>
        <div className="flex gap-2 mb-4">
          <select className={`${inputCls} w-40`} value={filter.status} onChange={(e) => setFilter({ ...filter, status: e.target.value })}>
            <option value="">All statuses</option><option value="open">Open</option>
            <option value="reviewed">Reviewed</option><option value="dismissed">Dismissed</option>
          </select>
          <select className={`${inputCls} w-40`} value={filter.severity} onChange={(e) => setFilter({ ...filter, severity: e.target.value })}>
            <option value="">All severities</option><option value="high">High</option>
            <option value="medium">Medium</option><option value="low">Low</option>
          </select>
        </div>
        {!alerts ? <Spinner /> : alerts.length === 0 ? <Empty msg="No alerts match" /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><Th>Severity</Th><Th>Type</Th><Th>FDR</Th><Th>Institution</Th><Th>Reason</Th><Th>Status</Th>{canReview && <Th>Action</Th>}</tr></thead>
              <tbody>
                {alerts.map((a) => (
                  <tr key={a.id} className="border-t border-slate-100 align-top">
                    <Td><Badge value={a.severity} /></Td>
                    <Td className="text-xs font-medium">{a.alert_type.replace(/_/g, ' ')}</Td>
                    <Td className="font-mono text-xs">{a.fdr_uid}<br /><span className="text-slate-400">{a.fdr_number}</span></Td>
                    <Td className="max-w-44 truncate text-xs">{a.institution}</Td>
                    <Td className="text-xs whitespace-normal min-w-80 max-w-md">{a.reason}</Td>
                    <Td><Badge value={a.status} /></Td>
                    {canReview && (
                      <Td>
                        {a.status === 'open' && (
                          <div className="flex gap-1">
                            <button className={btnGhost} onClick={() => review(a.id, 'reviewed')}>Mark reviewed</button>
                            <button className={btnGhost} onClick={() => review(a.id, 'dismissed')}>Dismiss</button>
                          </div>
                        )}
                      </Td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
