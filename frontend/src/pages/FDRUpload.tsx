import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { UploadCloud, FileScan, CheckCircle2, AlertTriangle } from 'lucide-react'
import api from '../api'
import { Card, Badge, btnPrimary, btnGhost } from '../components'

export default function FDRUpload() {
  const navigate = useNavigate()
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function upload() {
    if (!file) return
    setLoading(true); setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res = await api.post('/fdrs/documents/upload', fd)
      setResult(res.data)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed')
    } finally {
      setLoading(false)
    }
  }

  const ex = result?.extraction
  const fields = ex?.fields || {}
  const missing: string[] = ex?.missing_fields || []
  const labels = ex?.field_labels || {}

  return (
    <div className="max-w-3xl space-y-5">
      <div>
        <h1 className="text-xl font-bold text-navy">FDR Document Upload &amp; AI Extraction</h1>
        <p className="text-xs text-slate-500">
          Upload the FDR PDF or image — the AI pipeline extracts deposit details into editable fields for review.
          Demo file: <code className="bg-slate-100 px-1 rounded">sample_docs/sample_fdr.pdf</code>
        </p>
      </div>

      <Card>
        <label className="flex flex-col items-center justify-center border-2 border-dashed border-slate-300 rounded-xl py-10 cursor-pointer hover:border-royal hover:bg-sky-light/40 transition-colors">
          <UploadCloud size={36} className="text-royal mb-2" />
          <span className="text-sm font-medium text-navy">{file ? file.name : 'Click to choose PDF / JPG / PNG'}</span>
          <span className="text-xs text-slate-400 mt-1">Max 20 MB</span>
          <input type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden"
            onChange={(e) => { setFile(e.target.files?.[0] || null); setResult(null) }} />
        </label>
        {error && <div className="text-sm text-red-600 mt-3">{error}</div>}
        <div className="mt-4">
          <button className={btnPrimary} onClick={upload} disabled={!file || loading}>
            <FileScan size={15} /> {loading ? 'Extracting…' : 'Extract with AI'}
          </button>
        </div>
      </Card>

      {result && (
        <Card title="AI extraction result" action={<Badge value={result.extraction_status} />}>
          <div className="text-xs text-slate-500 mb-3">
            Method: <code className="bg-slate-100 px-1 rounded">{ex.method}</code>
            {ex.mock && <span className="text-amber-600 ml-2">No readable text — mock extraction mode. Fill fields manually.</span>}
          </div>
          <div className="grid md:grid-cols-2 gap-3 mb-4">
            {Object.keys(labels).map((k) => {
              const isMissing = missing.includes(k)
              const val = fields[k]
              return (
                <div key={k} className={`rounded-lg border px-3 py-2 ${isMissing ? 'border-amber-300 bg-amber-50' : 'border-green-200 bg-green-50/60'}`}>
                  <div className="text-[11px] text-slate-500 flex items-center gap-1">
                    {isMissing ? <AlertTriangle size={11} className="text-amber-500" /> : <CheckCircle2 size={11} className="text-gov-green" />}
                    {labels[k]}
                  </div>
                  <div className="text-sm font-medium text-navy mt-0.5">{val != null && val !== '' ? String(val) : '— not extracted —'}</div>
                </div>
              )
            })}
          </div>
          {ex.raw_text_excerpt && (
            <details className="mb-4">
              <summary className="text-xs text-royal cursor-pointer">Raw extracted text</summary>
              <pre className="text-[11px] bg-slate-50 rounded-lg p-3 mt-2 whitespace-pre-wrap">{ex.raw_text_excerpt}</pre>
            </details>
          )}
          <div className="flex gap-2">
            <button className={btnPrimary}
              onClick={() => navigate('/fdrs/register', {
                state: { prefill: { ...fields, missing_fields: missing }, document_id: result.document_id },
              })}>
              Review fields &amp; register FDR
            </button>
            <button className={btnGhost} onClick={() => { setResult(null); setFile(null) }}>Upload another</button>
          </div>
        </Card>
      )}
    </div>
  )
}
