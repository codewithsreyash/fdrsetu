import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, X } from 'lucide-react'
import api from '../api'
import { useAuth } from '../auth'
import { Card, Badge, Spinner, Th, Td, Empty, inputCls, inr, btnGhost } from '../components'

export default function FDRList() {
  const { user } = useAuth()
  const [params] = useSearchParams()
  const [rows, setRows] = useState<any[] | null>(null)
  const [detail, setDetail] = useState<any | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [qrUrl, setQrUrl] = useState<string | null>(null)
  const [filters, setFilters] = useState({
    search: '', status: '', verification_status: '', risk_level: '',
    expiring_days: '', expired: '', sort_by: 'created_at', sort_dir: 'desc',
  })

  const highlight = params.get('highlight')

  useEffect(() => {
    const q: any = { ...filters }
    Object.keys(q).forEach((k) => { if (!q[k]) delete q[k] })
    api.get('/fdrs', { params: q }).then((r) => setRows(r.data))
  }, [filters])

  async function openDetail(f: any) {
    const res = await api.get(`/fdrs/${f.id}`)
    setDetail(res.data)
    const h = await api.get(`/fdrs/${f.id}/history`)
    setHistory(h.data.events)
    const qr = await api.get(`/fdrs/${f.id}/qrcode`, { responseType: 'blob' })
    setQrUrl(URL.createObjectURL(qr.data))
  }

  function requestVerification(fdrId: number) {
    api.post('/verification/requests', { fdr_id: fdrId }).then(() => setDetail(null))
  }

  function requestRenewal(fdrId: number) {
    api.post('/maturity/renewals', { old_fdr_id: fdrId }).then(() => setDetail(null))
  }

  const sorted = useMemo(() => rows || [], [rows])
  const canAct = user?.role === 'institution' || user?.role === 'officer' || user?.role === 'admin'

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-navy">FDR Records</h1>
      <Card>
        <div className="flex flex-wrap items-center gap-2 mb-4">
          <div className="flex items-center gap-2">
            <Search size={16} className="text-slate-400" />
            <input className={`${inputCls} w-64`} placeholder="Search FDR no / UID / IFSC / institution…"
              value={filters.search} onChange={(e) => setFilters({ ...filters, search: e.target.value })} />
          </div>
          <select className={`${inputCls} w-36`} value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
            <option value="">Any status</option>
            {['pending', 'active', 'verified', 'expired', 'renewed', 'released'].map((s) => <option key={s}>{s}</option>)}
          </select>
          <select className={`${inputCls} w-36`} value={filters.verification_status} onChange={(e) => setFilters({ ...filters, verification_status: e.target.value })}>
            <option value="">Any verification</option>
            {['pending', 'in_review', 'verified', 'rejected'].map((s) => <option key={s}>{s}</option>)}
          </select>
          <select className={`${inputCls} w-32`} value={filters.risk_level} onChange={(e) => setFilters({ ...filters, risk_level: e.target.value })}>
            <option value="">Any risk</option>
            {['none', 'low', 'medium', 'high'].map((s) => <option key={s}>{s}</option>)}
          </select>
          <select className={`${inputCls} w-40`} value={filters.sort_by + ':' + filters.sort_dir}
            onChange={(e) => { const [s, d] = e.target.value.split(':'); setFilters({ ...filters, sort_by: s, sort_dir: d }) }}>
            <option value="created_at:desc">Newest first</option>
            <option value="maturity_date:asc">Maturity (soonest)</option>
            <option value="maturity_date:desc">Maturity (latest)</option>
            <option value="amount:desc">Amount (high→low)</option>
            <option value="amount:asc">Amount (low→high)</option>
          </select>
        </div>

        {!rows ? <Spinner /> : sorted.length === 0 ? <Empty msg="No FDRs match the filters" /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr>
                <Th>FDR UID</Th><Th>FDR No.</Th><Th>Institution</Th><Th>Bank</Th>
                <Th>Amount</Th><Th>Maturity</Th><Th>Status</Th><Th>Verification</Th><Th>Risk</Th><Th></Th>
              </tr></thead>
              <tbody>
                {sorted.map((f) => (
                  <tr key={f.id} className={`border-t border-slate-100 hover:bg-slate-50 cursor-pointer ${String(f.id) === highlight ? 'bg-sky-light' : ''}`}
                    onClick={() => openDetail(f)}>
                    <Td className="font-mono text-xs text-royal">{f.fdr_uid}</Td>
                    <Td className="font-mono text-xs">{f.fdr_number}</Td>
                    <Td className="max-w-52 truncate">{f.institution_name}</Td>
                    <Td>{f.bank_name}</Td>
                    <Td>{inr(f.amount)}</Td>
                    <Td>{f.maturity_date}</Td>
                    <Td><Badge value={f.status} /></Td>
                    <Td><Badge value={f.verification_status} /></Td>
                    <Td><Badge value={f.risk_level} />{f.open_alerts > 0 && <span className="text-xs text-red-500 ml-1">({f.open_alerts})</span>}</Td>
                    <Td className="text-royal text-xs">View</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {detail && (
        <div className="fixed inset-0 bg-black/40 z-40 flex justify-end" onClick={() => setDetail(null)}>
          <div className="w-full max-w-xl bg-white h-full overflow-y-auto p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between items-start mb-4">
              <div>
                <h2 className="text-lg font-bold text-navy">{detail.fdr_uid}</h2>
                <div className="text-xs text-slate-500">FDR No. {detail.fdr_number}</div>
              </div>
              <button onClick={() => setDetail(null)}><X size={18} /></button>
            </div>
            <div className="flex gap-4 mb-4">
              {qrUrl && <img src={qrUrl} alt="QR" className="w-28 h-28 border rounded-lg" />}
              <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm flex-1">
                <span className="text-slate-500">Institution</span><span className="font-medium">{detail.institution_name}</span>
                <span className="text-slate-500">Bank</span><span className="font-medium">{detail.bank_name}</span>
                <span className="text-slate-500">Branch</span><span className="font-medium">{detail.branch || '—'}</span>
                <span className="text-slate-500">IFSC</span><span className="font-mono">{detail.ifsc || '—'}</span>
                <span className="text-slate-500">Amount</span><span className="font-medium">{inr(detail.amount)}</span>
                <span className="text-slate-500">Interest</span><span className="font-medium">{detail.interest_rate ?? '—'}%</span>
                <span className="text-slate-500">Issue</span><span className="font-medium">{detail.issue_date}</span>
                <span className="text-slate-500">Maturity</span><span className="font-medium">{detail.maturity_date}</span>
                <span className="text-slate-500">Status</span><span><Badge value={detail.status} /></span>
                <span className="text-slate-500">Verification</span><span><Badge value={detail.verification_status} /></span>
                <span className="text-slate-500">Risk</span><span><Badge value={detail.risk_level} /></span>
              </div>
            </div>

            {detail.risk_alerts?.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-navy mb-2">Risk alerts</h3>
                {detail.risk_alerts.map((a: any) => (
                  <div key={a.id} className="text-xs border border-slate-200 rounded-lg p-2.5 mb-2 flex gap-2 items-start">
                    <Badge value={a.severity} /><span className="text-slate-600">{a.reason}</span>
                  </div>
                ))}
              </div>
            )}

            <h3 className="text-sm font-semibold text-navy mb-2">Lifecycle history</h3>
            <div className="space-y-1.5 mb-5">
              {history.map((e, i) => (
                <div key={i} className="flex gap-3 text-xs">
                  <span className="text-slate-400 w-36 shrink-0">{new Date(e.at).toLocaleString()}</span>
                  <span className="font-medium w-20 shrink-0">{e.type}</span>
                  <span className="text-slate-600">{e.detail}</span>
                </div>
              ))}
            </div>

            {canAct && (
              <div className="flex gap-2 flex-wrap">
                {detail.verification_status === 'pending' && (
                  <button className={btnGhost} onClick={() => requestVerification(detail.id)}>Request bank verification</button>
                )}
                {['expired', 'active', 'verified'].includes(detail.status) && (
                  <button className={btnGhost} onClick={() => requestRenewal(detail.id)}>Track renewal</button>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
