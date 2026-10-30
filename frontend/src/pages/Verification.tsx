import { useEffect, useState } from 'react'
import api from '../api'
import { Card, Badge, Spinner, Th, Td, Empty, btnGhost, inr } from '../components'

export default function Verification() {
    const [pending, setPending] = useState<any[] | null>(null)
  const [history, setHistory] = useState<any[]>([])
  const [reqs, setReqs] = useState<any[]>([])

  const load = () => {
    api.get('/fdrs', { params: { verification_status: 'pending' } }).then((r) => setPending(r.data))
    api.get('/verification/history').then((r) => setHistory(r.data))
    api.get('/verification/requests').then((r) => setReqs(r.data))
  }
  useEffect(() => { load() }, [])

  async function request(fdr_id: number) {
    await api.post('/verification/requests', { fdr_id })
    load()
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-navy">FDR Verification</h1>
        <p className="text-xs text-slate-500">Review extracted details and route FDRs to bank verification.</p>
      </div>

      <Card title={`FDRs pending verification (${pending?.length ?? '…'})`}>
        {!pending ? <Spinner /> : pending.length === 0 ? <Empty msg="Nothing pending" /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><Th>FDR UID</Th><Th>FDR No.</Th><Th>Institution</Th><Th>Bank</Th><Th>Amount</Th><Th>Maturity</Th><Th>Risk</Th><Th></Th></tr></thead>
              <tbody>
                {pending.map((f) => (
                  <tr key={f.id} className="border-t border-slate-100">
                    <Td className="font-mono text-xs">{f.fdr_uid}</Td>
                    <Td className="font-mono text-xs">{f.fdr_number}</Td>
                    <Td className="max-w-56 truncate">{f.institution_name}</Td>
                    <Td>{f.bank_name}</Td>
                    <Td>{inr(f.amount)}</Td>
                    <Td>{f.maturity_date}</Td>
                    <Td><Badge value={f.risk_level} /></Td>
                    <Td><button className={btnGhost} onClick={() => request(f.id)}>Request bank verification</button></Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Open verification requests">
        {reqs.filter((r) => ['pending', 'in_review'].includes(r.status)).length === 0 ? <Empty msg="No open requests" /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><Th>FDR</Th><Th>Institution</Th><Th>Bank</Th><Th>Status</Th><Th>Requested</Th></tr></thead>
              <tbody>
                {reqs.filter((r) => ['pending', 'in_review'].includes(r.status)).map((r) => (
                  <tr key={r.id} className="border-t border-slate-100">
                    <Td className="font-mono text-xs">{r.fdr_uid}</Td>
                    <Td className="max-w-56 truncate">{r.institution}</Td>
                    <Td>{r.bank}</Td>
                    <Td><Badge value={r.status} /></Td>
                    <Td className="text-xs">{new Date(r.created_at).toLocaleString()}</Td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Verification history">
        {history.length === 0 ? <Empty msg="No history" /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><Th>FDR</Th><Th>Result</Th><Th>Remarks</Th><Th>Mode</Th><Th>When</Th></tr></thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id} className="border-t border-slate-100">
                    <Td className="font-mono text-xs">{h.fdr_uid}</Td>
                    <Td><Badge value={h.result} /></Td>
                    <Td className="text-xs max-w-64 truncate">{h.remarks}</Td>
                    <Td>{h.mock_api ? <Badge value="mock" /> : 'live'}</Td>
                    <Td className="text-xs">{new Date(h.created_at).toLocaleString()}</Td>
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
