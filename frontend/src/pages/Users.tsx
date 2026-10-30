import { useEffect, useState } from 'react'
import { Plus } from 'lucide-react'
import api from '../api'
import { Card, Badge, Spinner, Th, Td, inputCls, btnPrimary, btnGhost, Field } from '../components'

export default function Users() {
  const [rows, setRows] = useState<any[] | null>(null)
  const [insts, setInsts] = useState<any[]>([])
  const [banks, setBanks] = useState<any[]>([])
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ email: '', full_name: '', password: '', role: 'institution', institution_id: '', bank_id: '' })
  const [error, setError] = useState('')

  const load = () => api.get('/users').then((r) => setRows(r.data))
  useEffect(() => {
    load()
    api.get('/institutions').then((r) => setInsts(r.data))
    api.get('/banks').then((r) => setBanks(r.data))
  }, [])

  async function create(e: React.FormEvent) {
    e.preventDefault(); setError('')
    try {
      await api.post('/users', {
        ...form,
        institution_id: form.institution_id ? Number(form.institution_id) : null,
        bank_id: form.bank_id ? Number(form.bank_id) : null,
      })
      setShowForm(false)
      setForm({ email: '', full_name: '', password: '', role: 'institution', institution_id: '', bank_id: '' })
      load()
    } catch (err: any) { setError(err.response?.data?.detail || 'Failed') }
  }

  async function toggle(u: any) {
    await api.put(`/users/${u.id}`, { is_active: !u.is_active })
    load()
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-navy">User &amp; Role Management</h1>
        <button className={btnPrimary} onClick={() => setShowForm(!showForm)}><Plus size={15} /> Add user</button>
      </div>

      {showForm && (
        <Card title="Create user">
          <form onSubmit={create} className="grid md:grid-cols-3 gap-4">
            <Field label="Full name *"><input required className={inputCls} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></Field>
            <Field label="Email *"><input required type="email" className={inputCls} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></Field>
            <Field label="Password *"><input required type="password" className={inputCls} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></Field>
            <Field label="Role *">
              <select className={inputCls} value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value })}>
                <option value="institution">Institution</option><option value="officer">AICTE Officer</option>
                <option value="bank">Bank Officer</option><option value="admin">Super Admin</option>
              </select>
            </Field>
            {form.role === 'institution' && (
              <Field label="Institution">
                <select required className={inputCls} value={form.institution_id} onChange={(e) => setForm({ ...form, institution_id: e.target.value })}>
                  <option value="">Select…</option>
                  {insts.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
                </select>
              </Field>
            )}
            {form.role === 'bank' && (
              <Field label="Bank">
                <select required className={inputCls} value={form.bank_id} onChange={(e) => setForm({ ...form, bank_id: e.target.value })}>
                  <option value="">Select…</option>
                  {banks.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}
                </select>
              </Field>
            )}
            {error && <div className="md:col-span-3 text-sm text-red-600">{error}</div>}
            <div className="md:col-span-3 flex gap-2">
              <button className={btnPrimary}>Create user</button>
              <button type="button" className={btnGhost} onClick={() => setShowForm(false)}>Cancel</button>
            </div>
          </form>
        </Card>
      )}

      <Card>
        {!rows ? <Spinner /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><Th>ID</Th><Th>Name</Th><Th>Email</Th><Th>Role</Th><Th>Org</Th><Th>Status</Th><Th></Th></tr></thead>
              <tbody>
                {rows.map((u) => (
                  <tr key={u.id} className="border-t border-slate-100">
                    <Td>{u.id}</Td>
                    <Td className="font-medium">{u.full_name}</Td>
                    <Td className="text-xs">{u.email}</Td>
                    <Td><Badge value={u.role === 'officer' ? 'verified' : u.role === 'bank' ? 'low' : u.role === 'admin' ? 'medium' : 'none'} /> <span className="text-xs ml-1">{u.role}</span></Td>
                    <Td className="text-xs max-w-52 truncate">{u.institution_name || u.bank_name || '—'}</Td>
                    <Td><Badge value={u.is_active ? 'active' : 'rejected'} /></Td>
                    <Td><button className={btnGhost} onClick={() => toggle(u)}>{u.is_active ? 'Disable' : 'Enable'}</button></Td>
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
