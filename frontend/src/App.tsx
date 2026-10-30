import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import { Layout } from './components'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Institutions from './pages/Institutions'
import FDRRegister from './pages/FDRRegister'
import FDRUpload from './pages/FDRUpload'
import FDRList from './pages/FDRList'
import Verification from './pages/Verification'
import Risk from './pages/Risk'
import BankVerification from './pages/BankVerification'
import Maturity from './pages/Maturity'
import Releases from './pages/Releases'
import Reports from './pages/Reports'
import Copilot from './pages/Copilot'
import Users from './pages/Users'
import Audit from './pages/Audit'
import Settings from './pages/Settings'
import type { ReactNode } from 'react'

function Protected({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  return user ? <>{children}</> : <Navigate to="/login" replace />
}

function Routes_() {
  const { user } = useAuth()
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <Login />} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route index element={<Dashboard />} />
        <Route path="institutions" element={<Institutions />} />
        <Route path="fdrs/register" element={<FDRRegister />} />
        <Route path="fdrs/upload" element={<FDRUpload />} />
        <Route path="fdrs" element={<FDRList />} />
        <Route path="verification" element={<Verification />} />
        <Route path="risk" element={<Risk />} />
        <Route path="bank-verification" element={<BankVerification />} />
        <Route path="maturity" element={<Maturity />} />
        <Route path="releases" element={<Releases />} />
        <Route path="reports" element={<Reports />} />
        <Route path="copilot" element={<Copilot />} />
        <Route path="users" element={<Users />} />
        <Route path="audit" element={<Audit />} />
        <Route path="settings" element={<Settings />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes_ />
      </AuthProvider>
    </BrowserRouter>
  )
}
