import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './hooks/useAuth'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { TenantsPage } from './pages/TenantsPage'
import { EventPipelinePage } from './pages/EventPipelinePage'
import { EventsPage } from './pages/EventsPage'
import { LiveEventsPage } from './pages/LiveEventsPage'
import { RawEventsPage } from './pages/RawEventsPage'
import { UESEventsPage } from './pages/UESEventsPage'
import { UESViewerPage } from './pages/UESViewerPage'
import { TraceabilityPage } from './pages/TraceabilityPage'
import { RawEvidencePage } from './pages/RawEvidencePage'
import { ControlPlanePage } from './pages/ControlPlanePage'
import { SourcesPage } from './pages/SourcesPage'
import { ParsersPage } from './pages/ParsersPage'
import { ParserStudioPage } from './pages/ParserStudioPage'
import { SchemasPage } from './pages/SchemasPage'
import { MappingsPage } from './pages/MappingsPage'
import { PoliciesPage } from './pages/PoliciesPage'
import { ServicesPage } from './pages/ServicesPage'
import { AuditPage } from './pages/AuditPage'
import { DLQPage } from './pages/DLQPage'
import { ReplayPage } from './pages/ReplayPage'
import { HealthPage } from './pages/HealthPage'
import { SettingsPage } from './pages/SettingsPage'
import { ConfigurationPage } from './pages/ConfigurationPage'
import { ArchitecturePage } from './pages/ArchitecturePage'
import { ObservabilityPage } from './pages/ObservabilityPage'
import { DemoModePage } from './pages/DemoModePage'

import { SystemPage } from './pages/SystemPage'

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
        
        {/* OVERVIEW & PIPELINE */}
        <Route path="/dashboard"     element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/pipeline"      element={<ProtectedRoute><EventPipelinePage /></ProtectedRoute>} />
        <Route path="/live-events"   element={<ProtectedRoute><Navigate to="/events" replace /></ProtectedRoute>} />
        <Route path="/raw-events"    element={<ProtectedRoute><Navigate to="/events" replace /></ProtectedRoute>} />
        <Route path="/ues-events"    element={<ProtectedRoute><Navigate to="/events" replace /></ProtectedRoute>} />
        <Route path="/events"        element={<ProtectedRoute><EventsPage /></ProtectedRoute>} />
        
        {/* ANALYSIS & EVIDENCE */}
        <Route path="/events/:id"        element={<ProtectedRoute><UESViewerPage /></ProtectedRoute>} />
        <Route path="/events/:id/trace"  element={<ProtectedRoute><TraceabilityPage /></ProtectedRoute>} />
        <Route path="/traceability"      element={<ProtectedRoute><TraceabilityPage /></ProtectedRoute>} />
        <Route path="/raw-evidence"      element={<ProtectedRoute><RawEvidencePage /></ProtectedRoute>} />

        {/* PARSERS */}
        <Route path="/parsers"       element={<ProtectedRoute><ParsersPage /></ProtectedRoute>} />
        <Route path="/parser-studio" element={<ProtectedRoute><Navigate to="/parsers?tab=studio" replace /></ProtectedRoute>} />

        {/* CONTROL PLANE / SETTINGS */}
        <Route path="/control-plane" element={<ProtectedRoute><Navigate to="/settings" replace /></ProtectedRoute>} />
        <Route path="/tenants"       element={<ProtectedRoute><Navigate to="/settings?tab=tenants" replace /></ProtectedRoute>} />
        <Route path="/sources"       element={<ProtectedRoute><Navigate to="/settings?tab=sources" replace /></ProtectedRoute>} />
        <Route path="/schemas"       element={<ProtectedRoute><SchemasPage /></ProtectedRoute>} />
        <Route path="/mappings"      element={<ProtectedRoute><Navigate to="/settings?tab=mappings" replace /></ProtectedRoute>} />
        <Route path="/policies"      element={<ProtectedRoute><Navigate to="/settings?tab=policies" replace /></ProtectedRoute>} />
        <Route path="/configuration" element={<ProtectedRoute><ConfigurationPage /></ProtectedRoute>} />

        {/* SYSTEM & OPERATIONS */}
        <Route path="/system"        element={<ProtectedRoute><SystemPage /></ProtectedRoute>} />
        <Route path="/health"        element={<ProtectedRoute><Navigate to="/system" replace /></ProtectedRoute>} />
        <Route path="/dlq"           element={<ProtectedRoute><Navigate to="/system?tab=dlq" replace /></ProtectedRoute>} />
        <Route path="/replay"        element={<ProtectedRoute><ReplayPage /></ProtectedRoute>} />
        <Route path="/architecture"  element={<ProtectedRoute><ArchitecturePage /></ProtectedRoute>} />
        <Route path="/observability" element={<ProtectedRoute><Navigate to="/system?tab=telemetry" replace /></ProtectedRoute>} />
        <Route path="/services"      element={<ProtectedRoute><Navigate to="/system?tab=services" replace /></ProtectedRoute>} />
        <Route path="/audit"         element={<ProtectedRoute><Navigate to="/system?tab=audit" replace /></ProtectedRoute>} />

        {/* CONFIG & DEMO */}
        <Route path="/settings"      element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
        <Route path="/demo"          element={<ProtectedRoute><DemoModePage /></ProtectedRoute>} />

        <Route path="*"              element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
