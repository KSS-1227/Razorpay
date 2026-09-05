/**
 * TopNav — fixed top navigation bar.
 *
 * Contains: mobile menu toggle, breadcrumb, command palette trigger,
 * notification bell, workspace badge, user avatar.
 */
import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Bell,
  ChevronRight,
  Command,
  Menu,
  Search,
  X,
} from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { NAV_ITEMS } from './navConfig'

interface TopNavProps {
  onMobileMenuOpen: () => void
}

// Build breadcrumb label from current pathname
function useBreadcrumb() {
  const location = useLocation()
  const segments = location.pathname.split('/').filter(Boolean)

  return segments.map((seg, idx) => {
    const path = '/' + segments.slice(0, idx + 1).join('/')
    const navItem = NAV_ITEMS.find((n) => n.path === path)
    const label = navItem?.label ?? seg.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
    return { label, path, isLast: idx === segments.length - 1 }
  })
}

// Compact notification dot component
function NotificationBell() {
  const [open, setOpen] = useState(false)

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative w-8 h-8 rounded-lg flex items-center justify-center text-slate-400
          hover:text-slate-200 hover:bg-white/8 transition-all duration-150"
        aria-label="Notifications"
      >
        <Bell className="w-4 h-4" />
        {/* Unread dot */}
        <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 ring-1 ring-[#0b0d15]" />
      </button>

      <AnimatePresence>
        {open && (
          <>
            <div
              className="fixed inset-0 z-30"
              onClick={() => setOpen(false)}
            />
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute right-0 top-full mt-2 w-72 z-40 rounded-2xl border border-white/10
                bg-[#0f1120]/95 backdrop-blur-xl shadow-2xl shadow-black/50 overflow-hidden"
            >
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/[0.06]">
                <h3 className="text-xs font-semibold text-slate-200">Notifications</h3>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="text-slate-500 hover:text-slate-300 transition-colors"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>

              {/* Notification items */}
              <div className="divide-y divide-white/[0.04]">
                {[
                  { title: 'Knowledge graph ready', body: 'Your PDF has been processed into 342 nodes.', time: '2m ago', unread: true },
                  { title: 'New case assigned', body: 'Compliance audit — Q2 Financial Report', time: '1h ago', unread: true },
                  { title: 'Report exported', body: 'Evidence report downloaded successfully.', time: '3h ago', unread: false },
                ].map((n, i) => (
                  <div
                    key={i}
                    className={`px-4 py-3 cursor-pointer hover:bg-white/[0.03] transition-colors ${n.unread ? 'bg-indigo-500/[0.04]' : ''}`}
                  >
                    <div className="flex items-start gap-2.5">
                      {n.unread && (
                        <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400 shrink-0" />
                      )}
                      <div className={n.unread ? '' : 'ml-4'}>
                        <p className="text-[12px] font-medium text-slate-200">{n.title}</p>
                        <p className="text-[11px] text-slate-500 mt-0.5 leading-relaxed">{n.body}</p>
                        <p className="text-[10px] text-slate-600 mt-1">{n.time}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="px-4 py-2.5 border-t border-white/[0.06]">
                <button className="w-full text-center text-[11px] text-indigo-400 hover:text-indigo-300 font-medium transition-colors py-0.5">
                  View all notifications
                </button>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}

export function TopNav({ onMobileMenuOpen }: TopNavProps) {
  const { user, workspaceId } = useAuth()
  const navigate = useNavigate()
  const breadcrumbs = useBreadcrumb()

  return (
    <header className="h-14 flex items-center justify-between gap-3 px-4 sm:px-5
      border-b border-white/[0.06] bg-[#0b0d15]/80 backdrop-blur-xl sticky top-0 z-20 shrink-0">

      {/* ── Left: Mobile menu + Breadcrumb ── */}
      <div className="flex items-center gap-3 min-w-0">
        {/* Mobile hamburger */}
        <button
          type="button"
          onClick={onMobileMenuOpen}
          className="md:hidden w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-200 hover:bg-white/8 transition-all"
          aria-label="Open menu"
        >
          <Menu className="w-[18px] h-[18px]" />
        </button>

        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="flex items-center gap-1 min-w-0">
          {breadcrumbs.map((crumb, idx) => (
            <div key={crumb.path} className="flex items-center gap-1 min-w-0">
              {idx > 0 && (
                <ChevronRight className="w-3 h-3 text-slate-600 shrink-0" />
              )}
              {crumb.isLast ? (
                <span className="text-sm font-semibold text-slate-100 truncate">
                  {crumb.label}
                </span>
              ) : (
                <button
                  type="button"
                  onClick={() => navigate(crumb.path)}
                  className="text-sm text-slate-500 hover:text-slate-300 transition-colors truncate"
                >
                  {crumb.label}
                </button>
              )}
            </div>
          ))}
          {breadcrumbs.length === 0 && (
            <span className="text-sm font-semibold text-slate-200">Dashboard</span>
          )}
        </nav>
      </div>

      {/* ── Right: Actions ── */}
      <div className="flex items-center gap-1.5 shrink-0">
        {/* Command palette trigger */}
        <button
          type="button"
          className="hidden sm:flex items-center gap-2 h-8 px-2.5 rounded-lg border border-white/[0.08]
            bg-white/[0.04] hover:bg-white/[0.07] text-slate-500 hover:text-slate-300
            text-xs transition-all duration-150 group"
          aria-label="Open command palette"
        >
          <Search className="w-3.5 h-3.5" />
          <span className="hidden lg:inline text-[11px]">Search or jump to…</span>
          <kbd className="hidden lg:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-white/[0.07] text-[10px] font-mono text-slate-500">
            <Command className="w-2.5 h-2.5" />K
          </kbd>
        </button>

        {/* Workspace badge */}
        {workspaceId && (
          <div className="hidden sm:flex items-center gap-1.5 h-7 px-2.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20">
            <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
            <span className="text-[11px] font-medium text-indigo-300 max-w-[100px] truncate">
              {workspaceId}
            </span>
          </div>
        )}

        {/* Notifications */}
        <NotificationBell />

        {/* User avatar */}
        {user && (
          <button
            type="button"
            onClick={() => navigate('/app/profile')}
            className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-600
              flex items-center justify-center text-xs font-bold text-white
              ring-2 ring-transparent hover:ring-indigo-500/40 transition-all duration-150 ml-0.5"
            aria-label="User profile"
          >
            {user.email[0].toUpperCase()}
          </button>
        )}
      </div>
    </header>
  )
}
