import { useEffect, useState } from 'react'
import api from '../api'
import { Card, Spinner, Th, Td, Empty, inputCls } from '../components'

export default function Audit() {
  const [rows, setRows] = useState<any[] | null>(null)
  const [entity, setEntity] = useState('')

  useEffect(() => {
    api.get('/audit-logs', { params: { entity: entity || undefined, limit: 300 } }).then((r) => setRows(r.data))
  }, [entity])

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-bold text-navy">Audit Logs</h1>
      <Card>
        <select className={`${inputCls} w-48 mb-4`} value={entity} onChange={(e) => setEntity(e.target.value)}>
          <option value="">All entities</option>
          {['fdr', 'institution', 'user', 'release_request', 'risk_alert', 'fdr_document'].map((e) => <option key={e}>{e}</option>)}
        </select>
        {!rows ? <Spinner /> : rows.length === 0 ? <Empty msg="No audit events" /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><Th>Time (UTC)</Th><Th>User</Th><Th>Action</Th><Th>Entity</Th><Th>Detail</Th></tr></thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.id} className="border-t border-slate-100">
                    <Td className="text-xs font-mono">{new Date(r.created_at).toLocaleString()}</Td>
                    <Td className="text-xs">{r.user_email || 'system'}</Td>
                    <Td className="text-xs font-medium">{r.action}</Td>
                    <Td className="text-xs">{r.entity ? `${r.entity}#${r.entity_id ?? ''}` : '—'}</Td>
                    <Td className="text-xs max-w-md truncate">{r.detail || '—'}</Td>
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
