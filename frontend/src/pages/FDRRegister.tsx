import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import api from '../api'
import { useAuth } from '../auth'
import { Card, Field, inputCls, btnPrimary } from '../components'

export interface FDRFormState {
  fdr_number: string; bank_id: string; institution_id: string;
  branch: string; ifsc: string; amount: string; interest_rate: string;
  issue_date: string; maturity_date: string;
}

export const emptyFDR: FDRFormState = {
  fdr_number: '', bank_id: '', institution_id: '', branch: '', ifsc: '',
  amount: '', interest_rate: '', issue_date: '', maturity_date: '',
}

export default function FDRRegister() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation() as any
  const prefill = location.state?.prefill
  const docId = location.state?.document_id
  const renewedFrom = location.state?.renewed_from_id

  const [banks, setBanks] = useState<any[]>([])
  const [insts, setInsts] = useState<any[]>([])
  const [form, setForm] = useState<FDRFormState>(() => ({
    ...emptyFDR,
    ...(prefill ? {
      fdr_number: prefill.fdr_number || '',
      branch: prefill.branch || '', ifsc: prefill.ifsc || '',
      amount: prefill.amount != null ? String(prefill.amount) : '',
      interest_rate: prefill.interest_rate != null ? String(prefill.interest_rate) : '',
      issue_date: prefill.issue_date || '', maturity_date: prefill.maturity_date || '',
    } : {}),
  }))
  const [missing] = useState<string[]>(prefill?.missing_fields || [])
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get('/banks').then((r) => {
      setBanks(r.data)
      if (prefill?.bank_name) {
        const b = r.data.find((x: any) => x.name === prefill.bank_name)
        if (b) setForm((f) => ({ ...f, bank_id: String(b.id) }))
      }
    })
    if (user?.role !== 'institution') {
      api.get('/institutions').then((r) => setInsts(r.data))
    }
  }, [])

  const set = (k: keyof FDRFormState) => (e: any) =>
    setForm({ ...form, [k]: e.target.value })

  async function submit(e: React.FormEvent) {
    e.preventDefault()
    setError(''); setSaving(true)
    try {
      const res = await api.post('/fdrs', {
        fdr_number: form.fdr_number, bank_id: Number(form.bank_id),
        institution_id: form.institution_id ? Number(form.institution_id) : null,
        branch: form.branch || null, ifsc: form.ifsc || null,
        amount: Number(form.amount), interest_rate: form.interest_rate ? Number(form.interest_rate) : null,
        issue_date: form.issue_date, maturity_date: form.maturity_date,
        document_id: docId || null, renewed_from_id: renewedFrom || null,
      })
      navigate(`/fdrs?highlight=${res.data.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to register FDR')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="max-w-3xl space-y-5">
      <div>
        <h1 className="text-xl font-bold text-navy">FDR Registration</h1>
        <p className="text-xs text-slate-500">
          {prefill ? 'Review the AI-extracted fields below — correct anything before saving.' :
            renewedFrom ? `Registering renewal FDR (replaces FDR #${renewedFrom}).` :
            'Manually register a Fixed Deposit Receipt. A unique FDRSETU ID and QR code will be generated.'}
        </p>
      </div>
      <Card>
        {docId && (
          <div className="mb-4 text-xs bg-sky-light text-navy rounded-lg px-3 py-2">
            Linked uploaded document #{docId}. Missing/unreadable fields are highlighted.
          </div>
        )}
        <form onSubmit={submit} className="grid md:grid-cols-2 gap-4">
          <Field label="FDR number *" hint={missing.includes('fdr_number') ? 'Not extracted — enter manually' : undefined}>
            <input required className={`${inputCls} ${missing.includes('fdr_number') ? 'border-amber-400 bg-amber-50' : ''}`} value={form.fdr_number} onChange={set('fdr_number')} />
          </Field>
          <Field label="Bank *">
            <select required className={inputCls} value={form.bank_id} onChange={set('bank_id')}>
              <option value="">Select bank…</option>
              {banks.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </Field>
          {user?.role !== 'institution' && (
            <Field label="Institution *">
              <select required className={inputCls} value={form.institution_id} onChange={set('institution_id')}>
                <option value="">Select institution…</option>
                {insts.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
              </select>
            </Field>
          )}
          <Field label="Branch" hint={missing.includes('branch') ? 'Not extracted' : undefined}>
            <input className={`${inputCls} ${missing.includes('branch') ? 'border-amber-400 bg-amber-50' : ''}`} value={form.branch} onChange={set('branch')} />
          </Field>
          <Field label="IFSC" hint={missing.includes('ifsc') ? 'Not extracted' : undefined}>
            <input className={`${inputCls} ${missing.includes('ifsc') ? 'border-amber-400 bg-amber-50' : ''}`} value={form.ifsc} onChange={set('ifsc')} placeholder="SBIN0123456" />
          </Field>
          <Field label="Deposit amount (₹) *" hint={missing.includes('amount') ? 'Not extracted' : undefined}>
            <input required type="number" min="1" className={`${inputCls} ${missing.includes('amount') ? 'border-amber-400 bg-amber-50' : ''}`} value={form.amount} onChange={set('amount')} />
          </Field>
          <Field label="Interest rate (%)">
            <input type="number" step="0.01" className={inputCls} value={form.interest_rate} onChange={set('interest_rate')} />
          </Field>
          <Field label="Issue date *" hint={missing.includes('issue_date') ? 'Not extracted' : undefined}>
            <input required type="date" className={`${inputCls} ${missing.includes('issue_date') ? 'border-amber-400 bg-amber-50' : ''}`} value={form.issue_date} onChange={set('issue_date')} />
          </Field>
          <Field label="Maturity date *" hint={missing.includes('maturity_date') ? 'Not extracted' : undefined}>
            <input required type="date" className={`${inputCls} ${missing.includes('maturity_date') ? 'border-amber-400 bg-amber-50' : ''}`} value={form.maturity_date} onChange={set('maturity_date')} />
          </Field>
          {error && <div className="md:col-span-2 text-sm text-red-600 bg-red-50 rounded-lg px-3 py-2">{error}</div>}
          <div className="md:col-span-2">
            <button className={btnPrimary} disabled={saving}>{saving ? 'Saving…' : 'Register FDR'}</button>
          </div>
        </form>
      </Card>
    </div>
  )
}
