import { useEffect, useState } from 'react'
import { Search, Landmark } from 'lucide-react'
import api from '../api'
import { useAuth } from '../auth'
import { Card, Badge, Spinner, Th, Td, Empty, inputCls, btnPrimary, btnGhost, Field } from '../components'

export default function BankVerification() {
  const { user } = useAuth()
  const [requests, setRequests] = useState<any[] | null>(null)
  const [searchNum, setSearchNum] = useState('')
  const [ledger, setLedger] = useState<any>(null)
  const [selected, setSelected] = useState<any | null>(null)
  const [conf, setConf] = useState({ confirm_fdr_number: false, confirm_amount: false, confirm_maturity_date: false, confirm_branch: false })
  const [remarks, setRemarks] = useState('')
  const [markVerified, setMarkVerified] = useState(true)
  const [result, setResult] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])

  const load = () => {
    api.get('/verification/requests').then((r) => setRequests(r.data))
    api.get('/verification/history').then((r) => setHistory(r.data))
  }
  useEffect(() => { load() }, [])

  async function lookup() {
    if (!searchNum) return
    const res = await api.get(`/verification/bank-lookup/${encodeURIComponent(searchNum)}`)
    setLedger(res.data)
  }

  async function submitVerification() {
    const res = await api.post('/verification/bank-verify', {
      fdr_id: selected.fdr_id ?? selected.id,
      ...conf, remarks, mark_verified: markVerified,
    })
    setResult(res.data)
    setSelected(null); setConf({ confirm_fdr_number: false, confirm_amount: false, confirm_maturity_date: false, confirm_branch: false }); setRemarks('')
    load()
  }

  const isBank = user?.role === 'bank'

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-navy">Bank Verification <span className="text-xs font-normal text-purple-600 bg-purple-100 px-2 py-0.5 rounded-full ml-2">MOCK BANK API — simulated</span></h1>
        <p className="text-xs text-slate-500">Bank-side confirmation of FDR details against the (simulated) bank ledger.</p>
      </div>

      {isBank && (
        <Card title="Search bank ledger (simulated)">
          <div className="flex gap-2 items-center">
            <Search size={16} className="text-slate-400" />
            <input className={`${inputCls} w-72`} placeholder="Enter FDR number…" value={searchNum}
              onChange={(e) => setSearchNum(e.target.value)} />
            <button className={btnPrimary} onClick={lookup}>Lookup</button>
          </div>
          {ledger && (
            <div className="mt-3 text-sm">
              {ledger.found ? (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 bg-slate-50 rounded-lg p-3">
                  {Object.entries(ledger.ledger).filter(([k]) => k !== 'source').map(([k, v]) => (
                    <div key={k}><div className="text-[11px] text-slate-500">{k.replace(/_/g, ' ')}</div><div className="font-medium">{String(v)}</div></div>
                  ))}
                </div>
              ) : <div className="text-amber-600">No record found at the bank (simulated).</div>}
            </div>
          )}
        </Card>
      )}

      <Card title="Verification requests">
        {!requests ? <Spinner /> : requests.length === 0 ? <Empty msg="No verification requests" /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><Th>FDR UID</Th><Th>FDR No.</Th><Th>Institution</Th><Th>Amount</Th><Th>Branch / IFSC</Th><Th>Maturity</Th><Th>Status</Th>{isBank && <Th></Th>}</tr></thead>
              <tbody>
                {requests.map((r) => (
                  <tr key={r.id} className="border-t border-slate-100">
                    <Td className="font-mono text-xs">{r.fdr_uid}</Td>
                    <Td className="font-mono text-xs">{r.fdr_number}</Td>
                    <Td className="max-w-56 truncate">{r.institution}</Td>
                    <Td>₹{r.amount?.toLocaleString('en-IN')}</Td>
                    <Td className="text-xs">{r.branch} <span className="font-mono">{r.ifsc}</span></Td>
                    <Td>{r.maturity_date}</Td>
                    <Td><Badge value={r.status} /></Td>
                    {isBank && <Td>{['pending', 'in_review'].includes(r.status) && <button className={btnPrimary} onClick={() => setSelected(r)}>Verify</button>}</Td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Verification history">
        {history.length === 0 ? <Empty msg="No verifications yet" /> : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead><tr><Th>FDR</Th><Th>Result</Th><Th>Confirmations</Th><Th>Remarks</Th><Th>When</Th></tr></thead>
              <tbody>
                {history.map((h) => (
                  <tr key={h.id} className="border-t border-slate-100">
                    <Td className="font-mono text-xs">{h.fdr_uid}</Td>
                    <Td><Badge value={h.result} /></Td>
                    <Td className="text-xs">
                      {Object.entries(h.confirmed).map(([k, v]) => (
                        <span key={k} className={`mr-2 ${v ? 'text-gov-green' : 'text-red-500'}`}>{k}:{v ? '✓' : '✗'}</span>
                      ))}
                    </Td>
                    <Td className="text-xs max-w-64 truncate">{h.remarks}</Td>
                    <Td className="text-xs">{new Date(h.created_at).toLocaleString()}</Td>
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
            <h2 className="font-bold text-navy mb-1 flex items-center gap-2"><Landmark size={17} /> Verify {selected.fdr_uid}</h2>
            <p className="text-xs text-slate-500 mb-4">Confirm each detail against bank records (simulated mock API).</p>
            <div className="space-y-2 mb-4 text-sm">
              <div className="flex justify-between items-center border-b pb-2"><span>FDR number: <b className="font-mono">{selected.fdr_number}</b></span>
                <input type="checkbox" checked={conf.confirm_fdr_number} onChange={(e) => setConf({ ...conf, confirm_fdr_number: e.target.checked })} /></div>
              <div className="flex justify-between items-center border-b pb-2"><span>Amount: <b>₹{selected.amount?.toLocaleString('en-IN')}</b></span>
                <input type="checkbox" checked={conf.confirm_amount} onChange={(e) => setConf({ ...conf, confirm_amount: e.target.checked })} /></div>
              <div className="flex justify-between items-center border-b pb-2"><span>Maturity: <b>{selected.maturity_date}</b></span>
                <input type="checkbox" checked={conf.confirm_maturity_date} onChange={(e) => setConf({ ...conf, confirm_maturity_date: e.target.checked })} /></div>
              <div className="flex justify-between items-center border-b pb-2"><span>Branch/IFSC: <b>{selected.branch} {selected.ifsc}</b></span>
                <input type="checkbox" checked={conf.confirm_branch} onChange={(e) => setConf({ ...conf, confirm_branch: e.target.checked })} /></div>
            </div>
            <Field label="Verification remarks">
              <textarea className={inputCls} rows={2} value={remarks} onChange={(e) => setRemarks(e.target.value)} />
            </Field>
            <div className="flex items-center gap-4 mt-4">
              <label className="text-sm flex items-center gap-2">
                <input type="radio" checked={markVerified} onChange={() => setMarkVerified(true)} /> Verified
              </label>
              <label className="text-sm flex items-center gap-2">
                <input type="radio" checked={!markVerified} onChange={() => setMarkVerified(false)} /> Rejected / mismatch
              </label>
            </div>
            <div className="flex gap-2 mt-4">
              <button className={btnPrimary} onClick={submitVerification}>Submit verification</button>
              <button className={btnGhost} onClick={() => setSelected(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {result && (
        <div className={`fixed bottom-4 right-4 z-50 rounded-xl px-4 py-3 text-sm shadow-xl ${result.result === 'verified' ? 'bg-green-600' : 'bg-amber-600'} text-white`}>
          Bank verification submitted: <b>{result.result}</b> (simulated)
        </div>
      )}
    </div>
  )
}
