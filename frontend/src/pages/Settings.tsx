import { useAuth } from '../auth'
import { roleLabel } from '../api'
import { Card, Badge } from '../components'

export default function Settings() {
  const { user } = useAuth()
  if (!user) return null
  return (
    <div className="max-w-2xl space-y-5">
      <h1 className="text-xl font-bold text-navy">Profile &amp; Settings</h1>
      <Card title="Account">
        <div className="grid grid-cols-2 gap-y-2 text-sm">
          <span className="text-slate-500">Name</span><span className="font-medium">{user.full_name}</span>
          <span className="text-slate-500">Email</span><span className="font-medium">{user.email}</span>
          <span className="text-slate-500">Role</span><span><Badge value={user.role === 'officer' ? 'verified' : 'low'} /> <span className="ml-1 text-sm">{roleLabel[user.role]}</span></span>
          {user.institution_name && <><span className="text-slate-500">Institution</span><span className="font-medium">{user.institution_name}</span></>}
          {user.bank_name && <><span className="text-slate-500">Bank</span><span className="font-medium">{user.bank_name}</span></>}
        </div>
      </Card>
      <Card title="Environment">
        <div className="text-sm space-y-2">
          <div className="flex justify-between"><span className="text-slate-500">Mode</span><Badge value="mock" /> <span className="text-xs text-slate-400 ml-1">All data synthetic; bank API simulated</span></div>
          <div className="flex justify-between"><span className="text-slate-500">OCR</span><span className="text-xs">PyMuPDF · Tesseract (if installed) · mock fallback</span></div>
          <div className="flex justify-between"><span className="text-slate-500">LLM copilot</span><span className="text-xs">Rule-based (set OPENAI_API_KEY to extend)</span></div>
          <div className="flex justify-between"><span className="text-slate-500">Storage</span><span className="text-xs">Local uploads · S3-compatible architecture</span></div>
        </div>
      </Card>
    </div>
  )
}
