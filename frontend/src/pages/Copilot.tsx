import { useEffect, useRef, useState } from 'react'
import { Bot, Send, User as UserIcon } from 'lucide-react'
import api from '../api'
import { Card, Badge, inputCls, btnPrimary } from '../components'

interface Msg {
  from: 'user' | 'bot'
  text: string
  rows?: any[]
  alerts?: any[]
  intent?: string
}

export default function Copilot() {
  const [msgs, setMsgs] = useState<Msg[]>([
    { from: 'bot', text: 'Namaste! I am the FDRSETU Copilot. Ask me about pending verifications, upcoming maturities, high-risk records, renewals, release requests, or an institution-wise summary. I answer from live database records.' },
  ])
  const [input, setInput] = useState('')
  const [suggested, setSuggested] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const bottom = useRef<HTMLDivElement>(null)

  useEffect(() => { api.get('/copilot/suggested').then((r) => setSuggested(r.data)) }, [])
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  async function ask(q: string) {
    if (!q.trim()) return
    setMsgs((m) => [...m, { from: 'user', text: q }])
    setInput(''); setLoading(true)
    try {
      const res = await api.post('/copilot/ask', { question: q })
      setMsgs((m) => [...m, { from: 'bot', text: res.data.answer, rows: res.data.rows, alerts: res.data.alerts, intent: res.data.intent }])
    } catch {
      setMsgs((m) => [...m, { from: 'bot', text: 'Sorry — something went wrong answering that.' }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl space-y-4">
      <div>
        <h1 className="text-xl font-bold text-navy flex items-center gap-2"><Bot size={22} className="text-royal" /> AI FDR Copilot</h1>
        <p className="text-xs text-slate-500">Rule-based assistant answering from real database records (LLM API optional — mock mode active).</p>
      </div>

      <Card>
        <div className="h-[45vh] overflow-y-auto space-y-3 pr-1">
          {msgs.map((m, i) => (
            <div key={i} className={`flex gap-2.5 ${m.from === 'user' ? 'justify-end' : ''}`}>
              {m.from === 'bot' && <div className="w-7 h-7 rounded-full bg-royal text-white flex items-center justify-center shrink-0"><Bot size={15} /></div>}
              <div className={`max-w-[80%] rounded-xl px-3.5 py-2.5 text-sm ${m.from === 'user' ? 'bg-royal text-white' : 'bg-slate-100 text-slate-800'}`}>
                <div>{m.text}</div>
                {m.rows && m.rows.length > 0 && (
                  <div className="mt-2 overflow-x-auto">
                    <table className="text-[11px] bg-white rounded-lg overflow-hidden w-full">
                      <thead><tr className="bg-navy text-white">
                        {Object.keys(m.rows[0]).slice(0, 7).map((k) => <th key={k} className="px-2 py-1 text-left font-medium">{k.replace(/_/g, ' ')}</th>)}
                      </tr></thead>
                      <tbody>
                        {m.rows.slice(0, 12).map((r, j) => (
                          <tr key={j} className="border-t border-slate-100">
                            {Object.keys(m.rows![0]).slice(0, 7).map((k) => <td key={k} className="px-2 py-1 text-slate-700">{r[k] != null ? String(r[k]) : '—'}</td>)}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {m.rows.length > 12 && <div className="text-[10px] text-slate-400 mt-1">…and {m.rows.length - 12} more</div>}
                  </div>
                )}
                {m.alerts && m.alerts.length > 0 && (
                  <div className="mt-2 space-y-1.5">
                    {m.alerts.map((a, j) => (
                      <div key={j} className="text-[11px] bg-white rounded-lg p-2 flex gap-1.5 items-start">
                        <Badge value={a.severity} /><span>{a.type.replace(/_/g, ' ')}: {a.reason}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              {m.from === 'user' && <div className="w-7 h-7 rounded-full bg-navy text-white flex items-center justify-center shrink-0"><UserIcon size={15} /></div>}
            </div>
          ))}
          {loading && <div className="text-xs text-slate-400">Copilot is thinking…</div>}
          <div ref={bottom} />
        </div>
        <div className="border-t border-slate-100 pt-3 mt-3 sticky bottom-0 bg-white">
          <div className="flex flex-wrap gap-1.5 mb-2.5">
            {suggested.map((s) => (
              <button key={s} onClick={() => ask(s)}
                className="text-[11px] bg-sky-light text-navy px-2.5 py-1 rounded-full hover:bg-royal hover:text-white transition-colors">{s}</button>
            ))}
          </div>
          <div className="flex gap-2">
            <input className={inputCls} placeholder="Ask about FDRs, verification, risk, maturity…"
              value={input} onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && ask(input)} />
            <button className={btnPrimary} onClick={() => ask(input)}><Send size={15} /></button>
          </div>
        </div>
      </Card>
    </div>
  )
}
