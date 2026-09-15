import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { TenantsPage } from './pages/TenantsPage'
import { EventPipelinePage } from './pages/EventPipelinePage'
import { EventsPage } from './pages/EventsPage'
import { SourcesPage } from './pages/SourcesPage'
import { ParsersPage } from './pages/ParsersPage'
import { SchemasPage } from './pages/SchemasPage'
import { MappingsPage } from './pages/MappingsPage'
import { PoliciesPage } from './pages/PoliciesPage'
import { ServicesPage } from './pages/ServicesPage'
import { AuditPage } from './pages/AuditPage'
import { ReplayPage } from './pages/ReplayPage'
import { ConfigurationPage } from './pages/ConfigurationPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard"     element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/pipeline"      element={<ProtectedRoute><EventPipelinePage /></ProtectedRoute>} />
        <Route path="/events"        element={<ProtectedRoute><EventsPage /></ProtectedRoute>} />
        <Route path="/tenants"       element={<ProtectedRoute><TenantsPage /></ProtectedRoute>} />
        <Route path="/sources"       element={<ProtectedRoute><SourcesPage /></ProtectedRoute>} />
        <Route path="/parsers"       element={<ProtectedRoute><ParsersPage /></ProtectedRoute>} />
        <Route path="/schemas"       element={<ProtectedRoute><SchemasPage /></ProtectedRoute>} />
        <Route path="/mappings"      element={<ProtectedRoute><MappingsPage /></ProtectedRoute>} />
        <Route path="/policies"      element={<ProtectedRoute><PoliciesPage /></ProtectedRoute>} />
        <Route path="/services"      element={<ProtectedRoute><ServicesPage /></ProtectedRoute>} />
        <Route path="/audit"         element={<ProtectedRoute><AuditPage /></ProtectedRoute>} />
        <Route path="/replay"        element={<ProtectedRoute><ReplayPage /></ProtectedRoute>} />
        <Route path="/configuration" element={<ProtectedRoute><ConfigurationPage /></ProtectedRoute>} />
        <Route path="*"              element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
