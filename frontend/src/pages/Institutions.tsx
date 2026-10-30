import { useEffect, useState } from 'react'
import { Plus, Search } from 'lucide-react'
import api from '../api'
import { useAuth } from '../auth'
import { Card, Field, Spinner, Th, Td, Empty, inputCls, btnPrimary, btnGhost, inr } from '../components'

export default function Institutions() {
  const { user } = useAuth()
  const [rows, setRows] = useState<any[] | null>(null)
  const [search, setSearch] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', code: '', state: '', city: '', contact_email: '', institution_type: 'Engineering College' })
  const [error, setError] = useState('')
  const canEdit = user?.role === 'officer' || user?.role === 'admin'

  const load = () => api.get('/institutions', { params: { search: search || undefined } }).then((r) => setRows(r.data))
  useEffect(() => { load() }, [search])

  async function create(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await api.post('/institutions', { ...form, code: form.code || null })
      setShowForm(false)
      setForm({ name: '', code: '', state: '', city: '', contact_email: '', institution_type: 'Engineering College' })
      load()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create institution')
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-navy">Institution Management</h1>
        {canEdit && <button className={btnPrimary} onClick={() => setShowForm(!showForm)}><Plus size={15} /> Add institution</button>}
      </div>

      {showForm && (
        <Card title="Register institution">
          <form onSubmit={create} className="grid md:grid-cols-3 gap-4">
            <Field label="Institution name *"><input required className={inputCls} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Code (auto if blank)"><input className={inputCls} value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="INST-021" /></Field>
            <Field label="Type">
              <select className={inputCls} value={form.institution_type} onChange={(e) => setForm({ ...form, institution_type: e.target.value })}>
                <option>Engineering College</option><option>Polytechnic</option><option>University</option>
              </select>
            </Field>
            <Field label="State"><input className={inputCls} value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} /></Field>
            <Field label="City"><input className={inputCls} value={form.city} onChange={(e) => setForm({ ...form, city: e.target.value })} /></Field>
            <Field label="Contact email"><input type="email" className={inputCls} value={form.contact_email} onChange={(e) => setForm({ ...form, contact_email: e.target.value })} /></Field>
            {error && <div className="md:col-span-3 text-sm text-red-600">{error}</div>}
            <div className="md:col-span-3 flex gap-2">
              <button className={btnPrimary}>Save institution</button>
              <button type="button" className={btnGhost} onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </form>
        </Card>
      )}

      <Card>
        <div className="flex items-center gap-2 mb-4">
          <Search size={16} className="text-slate-400" />
          <input className={`${inputCls} max-w-sm`} placeholder="Search name or code…" value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        {!rows ? <Spinner /> : rows.length === 0 ? <Empty msg="No institutions found" /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><Th>Code</Th><Th>Name</Th><Th>Type</Th><Th>State</Th><Th>City</Th><Th>FDRs</Th><Th>Total deposits</Th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-t border-slate-100 hover:bg-slate-50">
                    <Td className="font-mono text-xs">{r.code}</Td>
                    <Td className="font-medium text-navy whitespace-normal min-w-56">{r.name}</Td>
                    <Td>{r.institution_type}</Td>
                    <Td>{r.state}</Td>
                    <Td>{r.city}</Td>
                    <Td>{r.fdr_count}</Td>
                    <Td>{inr(r.total_amount)}</Td>
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
