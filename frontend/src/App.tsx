/**
 * Application root — React Router v7 with Framer Motion page transitions.
 *
 * Public   : /login, /register, /password-reset, /auth/callback
 * Workspace: /workspaces
 * App shell: /app/*  (Sidebar + TopNav layout via AppShell)
 */
import { useEffect } from 'react'
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom'
import { AnimatePresence } from 'framer-motion'

import { AuthProvider }    from './auth/AuthContext'
import { supabase }        from './auth/supabaseClient'
import { useAuth }         from './auth/AuthContext'
import ProtectedRoute      from './components/ProtectedRoute'
import { FullScreenLoader } from './components/ui/FullScreenLoader'
import { AppShell }        from './components/shell/AppShell'

import LoginPage           from './pages/LoginPage'
import RegisterPage        from './pages/RegisterPage'
import PasswordResetPage   from './pages/PasswordResetPage'
import WorkspaceSelectPage from './pages/WorkspaceSelectPage'
import WorkspacePlaceholder from './pages/app/WorkspacePlaceholder'
import DashboardPage from './pages/app/DashboardPage'
import UploadPage from './pages/app/UploadPage'
import KnowledgeGraphPage from './pages/app/KnowledgeGraphPage.tsx'
import CasesPage from './pages/app/CasesPage'
import AIAssistantPage from './pages/app/AIAssistantPage'
import ReportsPage from './pages/app/ReportsPage'
import CompliancePage from './pages/app/CompliancePage'
import EvidencePage from './pages/app/EvidencePage'
import ProfilePage from './pages/app/ProfilePage'
import SettingsPage from './pages/app/SettingsPage'
import CaseDetailPage from './pages/app/CaseDetailPage'

// ─────────────────────────────────────────────────────────
// Root redirect
// ─────────────────────────────────────────────────────────

function RootRedirect() {
  const { isAuthenticated, isLoading } = useAuth()
  if (isLoading) return <FullScreenLoader message="Initialising session…" />
  return isAuthenticated
    ? <Navigate to="/workspaces" replace />
    : <Navigate to="/login" replace />
}

// ─────────────────────────────────────────────────────────
// OAuth callback
// ─────────────────────────────────────────────────────────

function OAuthCallbackPage() {
  const navigate = useNavigate()

  useEffect(() => {
    async function exchange() {
      try {
        // First check if detectSessionInUrl already resolved the session
        // (Supabase does this automatically when persistSession: true)
        const { data: { session } } = await supabase.auth.getSession()
        if (session) {
          void navigate('/workspaces', { replace: true })
          return
        }

        // PKCE flow: exchange the auth code for a session
        // Pass the full href so Supabase can extract ?code= or #access_token=
        const { error } = await supabase.auth.exchangeCodeForSession(
          window.location.href
        )
        if (error) throw error
        void navigate('/workspaces', { replace: true })
      } catch (err) {
        console.error('OAuth callback error:', err)
        void navigate('/login?error=oauth_failed', { replace: true })
      }
    }
    void exchange()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return <FullScreenLoader message="Completing sign-in…" />
}


// ─────────────────────────────────────────────────────────
// App-level router
// MED-3: AnimatePresence only keys on auth-level route changes.
// AppShell has its own inner AnimatePresence for /app/* sub-routes,
// so we must NOT re-key the outer wrapper on every sub-route change —
// that would cause the sidebar and topnav to flicker on every navigation.
// ─────────────────────────────────────────────────────────

const AUTH_ROUTES = new Set(['/login', '/register', '/password-reset', '/auth/callback', '/'])

function AnimatedRoutes() {
  const location = useLocation()
  // Only animate at the auth↔app boundary, not on every /app/* sub-route change
  const animationKey = AUTH_ROUTES.has(location.pathname) ? location.pathname : 'app-shell'

  return (
    <AnimatePresence mode="wait">
      <Routes location={location} key={animationKey}>
        {/* Root */}
        <Route path="/" element={<RootRedirect />} />

        {/* Public auth routes */}
        <Route path="/login"          element={<LoginPage />} />
        <Route path="/register"       element={<RegisterPage />} />
        <Route path="/password-reset" element={<PasswordResetPage />} />
        <Route path="/auth/callback"  element={<OAuthCallbackPage />} />

        {/* Protected routes */}
        <Route element={<ProtectedRoute />}>
          {/* Workspace picker — no shell */}
          <Route path="/workspaces" element={<WorkspaceSelectPage />} />

          {/* App shell — sidebar + topnav wrapping all /app/* */}
          <Route path="/app" element={<AppShell />}>
            {/* Default /app → dashboard */}
            <Route index element={<Navigate to="dashboard" replace />} />

            {/* Main section */}
            <Route path="dashboard"      element={<DashboardPage />} />
            <Route path="cases"          element={<CasesPage />} />
            <Route path="cases/:id"      element={<CaseDetailPage />} />
            <Route path="upload"         element={<UploadPage />} />

            {/* Intelligence section */}
            <Route path="knowledge-graph" element={<KnowledgeGraphPage />} />
            <Route path="ai-assistant"    element={<AIAssistantPage />} />
            <Route path="evidence"        element={<EvidencePage />} />
            <Route path="reports"         element={<ReportsPage />} />
            <Route path="compliance"      element={<CompliancePage />} />

            {/* Account section */}
            <Route path="settings"  element={<SettingsPage />} />
            <Route path="profile"   element={<ProfilePage />} />

            {/* Catch-all within /app */}
            <Route path="*" element={<WorkspacePlaceholder title="Not Found" description="This page doesn't exist." />} />
          </Route>
        </Route>
      </Routes>
    </AnimatePresence>
  )
}

// ─────────────────────────────────────────────────────────
// App root
// ─────────────────────────────────────────────────────────

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AnimatedRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
