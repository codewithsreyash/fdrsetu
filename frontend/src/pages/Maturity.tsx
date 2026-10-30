import { useEffect, useState } from 'react'
import { RefreshCcw } from 'lucide-react'
import api from '../api'
import { useAuth } from '../auth'
import { Card, Badge, Spinner, Th, Td, Empty, btnPrimary, btnGhost, inr } from '../components'

export default function Maturity() {
  const { user } = useAuth()
  const [tab, setTab] = useState<'upcoming' | 'expired' | 'renewals'>('upcoming')
  const [upcoming, setUpcoming] = useState<any[] | null>(null)
  const [expired, setExpired] = useState<any[] | null>(null)
  const [renewals, setRenewals] = useState<any[] | null>(null)
  const [scanning, setScanning] = useState(false)

  const load = () => {
    api.get('/maturity/upcoming?days=90').then((r) => setUpcoming(r.data))
    api.get('/maturity/expired').then((r) => setExpired(r.data))
    api.get('/maturity/renewals').then((r) => setRenewals(r.data))
  }
  useEffect(() => { load() }, [])

  async function rescan() {
    setScanning(true)
    await api.post('/maturity/scan')
    await load()
    setScanning(false)
  }

  function trackRenewal(fdrId: number) {
    api.post('/maturity/renewals', { old_fdr_id: fdrId }).then(load)
  }

  const canTrack = user?.role === 'institution' || user?.role === 'officer' || user?.role === 'admin'

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-navy">Maturity &amp; Renewal Tracking</h1>
          <p className="text-xs text-slate-500">Automatic alerts at 90 / 60 / 30 days before maturity, expired tracking and renewal links.</p>
        </div>
        <button className={btnPrimary} onClick={rescan} disabled={scanning}><RefreshCcw size={14} /> {scanning ? 'Scanning…' : 'Run maturity scan'}</button>
      </div>

      <div className="flex gap-1 border-b border-slate-200">
        {(['upcoming', 'expired', 'renewals'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm font-medium rounded-t-lg ${tab === t ? 'bg-white text-royal border border-b-0 border-slate-200' : 'text-slate-500'}`}>
            {t === 'upcoming' ? `Upcoming (${upcoming?.length ?? '…'})` : t === 'expired' ? `Expired / overdue (${expired?.length ?? '…'})` : `Renewals (${renewals?.length ?? '…'})`}
          </button>
        ))}
      </div>

      {tab === 'upcoming' && (
        <Card>
          {!upcoming ? <Spinner /> : upcoming.length === 0 ? <Empty msg="No FDRs maturing in the next 90 days" /> : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr><Th>Days left</Th><Th>FDR UID</Th><Th>Institution</Th><Th>Bank</Th><Th>Amount</Th><Th>Maturity</Th><Th>Status</Th>{canTrack && <Th></Th>}</tr></thead>
                <tbody>
                  {upcoming.map((f) => (
                    <tr key={f.id} className="border-t border-slate-100">
                      <Td><span className={`font-bold ${f.days_left <= 30 ? 'text-red-600' : f.days_left <= 60 ? 'text-amber-600' : 'text-slate-700'}`}>{f.days_left}d</span></Td>
                      <Td className="font-mono text-xs">{f.fdr_uid}</Td>
                      <Td className="max-w-56 truncate">{f.institution_name}</Td>
                      <Td>{f.bank_name}</Td>
                      <Td>{inr(f.amount)}</Td>
                      <Td>{f.maturity_date}</Td>
                      <Td><Badge value={f.status} /></Td>
                      {canTrack && <Td><button className={btnGhost} onClick={() => trackRenewal(f.id)}>Track renewal</button></Td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === 'expired' && (
        <Card>
          {!expired ? <Spinner /> : expired.length === 0 ? <Empty msg="No expired FDRs" /> : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr><Th>Overdue</Th><Th>FDR UID</Th><Th>Institution</Th><Th>Bank</Th><Th>Amount</Th><Th>Matured on</Th><Th>Status</Th>{canTrack && <Th></Th>}</tr></thead>
                <tbody>
                  {expired.map((f) => (
                    <tr key={f.id} className="border-t border-slate-100">
                      <Td><span className="font-bold text-red-600">{f.days_overdue}d</span></Td>
                      <Td className="font-mono text-xs">{f.fdr_uid}</Td>
                      <Td className="max-w-56 truncate">{f.institution_name}</Td>
                      <Td>{f.bank_name}</Td>
                      <Td>{inr(f.amount)}</Td>
                      <Td>{f.maturity_date}</Td>
                      <Td><Badge value={f.status} /></Td>
                      {canTrack && <Td>{f.status === 'expired' && <button className={btnGhost} onClick={() => trackRenewal(f.id)}>Track renewal</button>}</Td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {tab === 'renewals' && (
        <Card>
          {!renewals ? <Spinner /> : renewals.length === 0 ? <Empty msg="No renewal records" /> : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead><tr><Th>Old FDR</Th><Th>Matured</Th><Th>New / replacement FDR</Th><Th>Institution</Th><Th>Status</Th><Th>Created</Th></tr></thead>
                <tbody>
                  {renewals.map((r) => (
                    <tr key={r.id} className="border-t border-slate-100">
                      <Td className="font-mono text-xs">{r.old_fdr_uid}<br /><span className="text-slate-400">{r.old_fdr_number}</span></Td>
                      <Td>{r.old_maturity}</Td>
                      <Td className="font-mono text-xs">{r.new_fdr_uid ?? <span className="text-amber-600">awaiting submission</span>}<br /><span className="text-slate-400">{r.new_fdr_number ?? ''}</span></Td>
                      <Td className="max-w-52 truncate">{r.institution}</Td>
                      <Td><Badge value={r.status} /></Td>
                      <Td className="text-xs">{new Date(r.created_at).toLocaleDateString()}</Td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}
    </div>
  )
}
