import { useEffect, useState } from 'react'
import { Plus, X } from 'lucide-react'
import api from '../api'
import { useAuth } from '../auth'
import { Card, Badge, Spinner, Th, Td, Empty, inputCls, btnPrimary, btnGhost, Field, inr } from '../components'

export default function Releases() {
  const { user } = useAuth()
  const [rows, setRows] = useState<any[] | null>(null)
  const [myFDRs, setMyFDRs] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ fdr_id: '', reason: '', file: null as File | null })
  const [selected, setSelected] = useState<any | null>(null)
  const [hist, setHist] = useState<any[]>([])
  const [action, setAction] = useState('under_review')
  const [remarks, setRemarks] = useState('')
  const [error, setError] = useState('')

  const isInst = user?.role === 'institution'
  const isOfficer = user?.role === 'officer' || user?.role === 'admin'

  const load = () => api.get('/releases').then((r) => setRows(r.data))
  useEffect(() => {
    load()
    if (isInst) api.get('/fdrs').then((r) => setMyFDRs(r.data.filter((f: any) => f.status !== 'released')))
  }, [])

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const fd = new FormData()
      fd.append('fdr_id', form.fdr_id)
      fd.append('reason', form.reason)
      if (form.file) fd.append('file', form.file)
      await api.post('/releases', fd)
      setShowForm(false); setForm({ fdr_id: '', reason: '', file: null })
      load()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit')
    }
  }

  async function openDetail(r: any) {
    setSelected(r)
    const h = await api.get(`/releases/${r.id}/history`)
    setHist(h.data)
  }

  async function act() {
    await api.post(`/releases/${selected.id}/action`, { action, remarks })
    setSelected(null); setRemarks('')
    load()
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-navy">Release / Refund Management</h1>
          <p className="text-xs text-slate-500">Release decisions remain with authorized AICTE officials — nothing is auto-approved.</p>
        </div>
        {isInst && <button className={btnPrimary} onClick={() => setShowForm(!showForm)}><Plus size={15} /> New release request</button>}
      </div>

      {showForm && (
        <Card title="Submit release request">
          <form onSubmit={submit} className="grid md:grid-cols-2 gap-4">
            <Field label="FDR *">
              <select required className={inputCls} value={form.fdr_id} onChange={(e) => setForm({ ...form, fdr_id: e.target.value })}>
                <option value="">Select FDR…</option>
                {myFDRs.map((f) => <option key={f.id} value={f.id}>{f.fdr_uid} — {f.fdr_number} — {inr(f.amount)}</option>)}
              </select>
            </Field>
            <Field label="Supporting document (PDF/JPG/PNG)">
              <input type="file" accept=".pdf,.jpg,.jpeg,.png" className={inputCls}
                onChange={(e) => setForm({ ...form, file: e.target.files?.[0] || null })} />
            </Field>
            <div className="md:col-span-2">
              <Field label="Reason for release">
                <textarea className={inputCls} rows={2} value={form.reason} onChange={(e) => setForm({ ...form, reason: e.target.value })} />
              </Field>
            </div>
            {error && <div className="md:col-span-2 text-sm text-red-600">{error}</div>}
            <div className="md:col-span-2 flex gap-2">
              <button className={btnPrimary}>Submit request</button>
              <button type="button" className={btnGhost} onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </form>
        </Card>
      )}

      <Card>
        {!rows ? <Spinner /> : rows.length === 0 ? <Empty msg="No release requests" /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><Th>#</Th><Th>FDR</Th><Th>Institution</Th><Th>Amount</Th><Th>Reason</Th><Th>Docs</Th><Th>Status</Th><Th>Created</Th><Th></Th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-t border-slate-100">
                    <Td>{r.id}</Td>
                    <Td className="font-mono text-xs">{r.fdr_uid}<br /><span className="text-slate-400">{r.fdr_number}</span></Td>
                    <Td className="max-w-48 truncate">{r.institution}</Td>
                    <Td>{inr(r.amount)}</Td>
                    <Td className="text-xs max-w-52 truncate">{r.reason || '—'}</Td>
                    <Td>{r.has_document ? '📎' : '—'}</Td>
                    <Td><Badge value={r.status} /></Td>
                    <Td className="text-xs">{new Date(r.created_at).toLocaleDateString()}</Td>
                    <Td><button className={btnGhost} onClick={() => openDetail(r)}>{isOfficer && ['pending', 'under_review'].includes(r.status) ? 'Review' : 'View'}</button></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {selected && (
        <div className="fixed inset-0 bg-black/40 z-40 flex items-center justify-center p-4" onClick={() => setSelected(null)}>
          <div className="bg-white rounded-xl max-w-lg w-full p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex justify-between mb-3">
              <h2 className="font-bold text-navy">Release request #{selected.id} — {selected.fdr_uid}</h2>
              <button onClick={() => setSelected(null)}><X size={18} /></button>
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm mb-4">
              <span className="text-slate-500">Institution</span><span className="font-medium">{selected.institution}</span>
              <span className="text-slate-500">Amount</span><span className="font-medium">{inr(selected.amount)}</span>
              <span className="text-slate-500">Status</span><span><Badge value={selected.status} /></span>
              <span className="text-slate-500">Reason</span><span className="font-medium">{selected.reason || '—'}</span>
            </div>
            <h3 className="text-sm font-semibold text-navy mb-1.5">Approval history</h3>
            {hist.length === 0 ? <div className="text-xs text-slate-400 mb-3">No actions yet</div> : (
              <div className="space-y-1.5 mb-4">
                {hist.map((h) => (
                  <div key={h.id} className="text-xs flex gap-2"><Badge value={h.action === 'under_review' ? 'under_review' : h.action} />
                    <span>{h.remarks}</span><span className="text-slate-400 ml-auto">{new Date(h.created_at).toLocaleString()}</span></div>
                ))}
              </div>
            )}
            {isOfficer && ['pending', 'under_review'].includes(selected.status) && (
              <>
                <div className="flex gap-3 mb-3 text-sm">
                  {['under_review', 'observation', 'approved', 'rejected'].map((a) => (
                    <label key={a} className="flex items-center gap-1.5">
                      <input type="radio" checked={action === a} onChange={() => setAction(a)} />{a.replace('_', ' ')}
                    </label>
                  ))}
                </div>
                <Field label="Remarks / observations">
                  <textarea className={inputCls} rows={2} value={remarks} onChange={(e) => setRemarks(e.target.value)} />
                </Field>
                <button className={`${btnPrimary} mt-3`} onClick={act}>Submit decision</button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
