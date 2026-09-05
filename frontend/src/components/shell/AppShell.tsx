/**
 * AppShell — master layout orchestrator for all /app/* routes.
 *
 * Composes: Sidebar + TopNav + animated Outlet.
 * Manages sidebar collapse state (persisted to localStorage) + mobile drawer.
 * Guards: redirects to /workspaces if no workspace is selected.
 */
import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Sidebar }  from './Sidebar'
import { TopNav }   from './TopNav'
import { useWorkspaceGuard } from '../../hooks/useWorkspaceGuard'
import { FullScreenLoader }  from '../ui/FullScreenLoader'

const LS_KEY = 'innova_sidebar_collapsed'

export function AppShell() {
  // ── Workspace guard ────────────────────────────────────
  const { isReady } = useWorkspaceGuard()

  // ── Sidebar state (persisted) ──────────────────────────
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try { return localStorage.getItem(LS_KEY) === 'true' } catch { return false }
  })

  // ── Mobile drawer ──────────────────────────────────────
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  function toggleCollapsed() {
    setCollapsed((prev) => {
      const next = !prev
      try { localStorage.setItem(LS_KEY, String(next)) } catch { /* ignore */ }
      return next
    })
  }

  // Close mobile drawer on route change
  useEffect(() => { setMobileOpen(false) }, [location.pathname])

  // Show loader while workspace guard is resolving
  if (!isReady) {
    return <FullScreenLoader message="Loading workspace…" />
  }

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#090a0f]">

      {/* ── Left: Sidebar ── */}
      <Sidebar
        collapsed={collapsed}
        onToggle={toggleCollapsed}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      {/* ── Right: TopNav + content pane ── */}
      <div className="flex flex-col flex-1 min-w-0 h-screen overflow-hidden">

        <TopNav onMobileMenuOpen={() => setMobileOpen(true)} />

        {/* ── Main workspace content ── */}
        <main className="flex-1 overflow-y-auto overflow-x-hidden relative">

          {/* Ambient radial glow — static, not per-page */}
          <div className="pointer-events-none fixed inset-0 z-0" aria-hidden>
            <div className="absolute top-[-20%] right-[-10%] w-[600px] h-[600px] rounded-full bg-indigo-600/[0.04] blur-[120px]" />
            <div className="absolute bottom-[-20%] left-[10%] w-[500px] h-[500px] rounded-full bg-purple-600/[0.04] blur-[100px]" />
          </div>

          {/* Animated page content — transitions on sub-route change */}
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.2, ease: 'easeOut' }}
              className="relative z-10 min-h-full"
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>

        </main>
      </div>
    </div>
  )
}
