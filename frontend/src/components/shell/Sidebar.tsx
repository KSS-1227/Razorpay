/**
 * Sidebar — collapsible left navigation.
 *
 * Desktop: always visible, icon-only or expanded.
 * Mobile: hidden by default, revealed as overlay drawer.
 */
import { motion, AnimatePresence } from 'framer-motion'
import { ChevronLeft, LogOut, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { NAV_ITEMS, NAV_SECTIONS } from './navConfig'
import { SidebarNavItem } from './SidebarNavItem'

const SIDEBAR_W_EXPANDED = 232
const SIDEBAR_W_COLLAPSED = 64

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
  /** Mobile: whether the overlay drawer is open */
  mobileOpen: boolean
  onMobileClose: () => void
}

export function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const { logout, user, workspaceId } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    try {
      await logout()
    } catch (err) {
      // LOW-5: Don't let a network error block the user from being signed out locally
      console.error('Logout error:', err)
    }
    navigate('/login')
  }

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* ── Brand header ── */}
      <div
        className={`flex items-center gap-2.5 px-3 py-4 border-b border-white/[0.06] shrink-0 ${
          collapsed ? 'justify-center' : ''
        }`}
      >
        <div className="w-7 h-7 shrink-0 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center shadow-md shadow-indigo-500/30">
          <Sparkles className="w-3.5 h-3.5 text-white" />
        </div>
        <AnimatePresence initial={false}>
          {!collapsed && (
            <motion.div
              key="brand-text"
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden flex flex-col min-w-0"
            >
              <span className="text-[13px] font-bold tracking-tight text-white leading-tight truncate">
                InnovaHack
              </span>
              <span className="text-[10px] text-slate-500 truncate leading-tight">
                {workspaceId ?? 'No workspace'}
              </span>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Desktop collapse toggle */}
        <button
          type="button"
          onClick={onToggle}
          className={`hidden md:flex shrink-0 ml-auto w-6 h-6 rounded-lg items-center justify-center text-slate-500 hover:text-slate-300 hover:bg-white/8 transition-all duration-150 ${
            collapsed ? 'rotate-180 ml-0' : ''
          }`}
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          <ChevronLeft className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* ── Navigation ── */}
      <nav className="flex-1 overflow-y-auto overflow-x-hidden py-3 px-2 space-y-5 scrollbar-none">
        {NAV_SECTIONS.map((section) => {
          const items = NAV_ITEMS.filter((i) => i.section === section.key)
          return (
            <div key={section.key}>
              {/* Section label */}
              <AnimatePresence initial={false}>
                {!collapsed && (
                  <motion.p
                    key={`label-${section.key}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.15 }}
                    className="px-3 mb-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600 select-none"
                  >
                    {section.label}
                  </motion.p>
                )}
              </AnimatePresence>

              {/* Items */}
              <div className="flex flex-col gap-0.5">
                {items.map((item) => (
                  <SidebarNavItem
                    key={item.id}
                    item={item}
                    collapsed={collapsed}
                  />
                ))}
              </div>
            </div>
          )
        })}
      </nav>

      {/* ── User footer ── */}
      <div className="shrink-0 px-2 py-3 border-t border-white/[0.06]">
        {/* User info row */}
        {!collapsed && user && (
          <div className="flex items-center gap-2.5 px-3 py-2 mb-1 rounded-xl bg-slate-900/60 border border-white/5">
            <div className="w-7 h-7 shrink-0 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-xs font-bold text-white">
              {user.email[0].toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-[11px] font-medium text-slate-200 truncate">{user.email}</p>
              <p className="text-[10px] text-slate-500 capitalize">{user.role}</p>
            </div>
          </div>
        )}

        {/* Logout button */}
        <button
          type="button"
          onClick={() => { void handleLogout() }}
          className={`w-full group flex items-center gap-2.5 rounded-xl px-3 py-2.5 text-sm font-medium text-slate-500
            hover:bg-red-500/8 hover:text-red-400 transition-all duration-150
            ${collapsed ? 'justify-center' : ''}`}
          aria-label="Sign out"
        >
          <LogOut className="w-4 h-4 shrink-0" />
          {!collapsed && <span className="text-sm">Sign out</span>}
          {collapsed && (
            <div className="pointer-events-none absolute left-full ml-2 z-50 whitespace-nowrap rounded-lg bg-slate-800 border border-white/10 text-red-400 text-xs px-2.5 py-1.5 shadow-xl opacity-0 group-hover:opacity-100 transition-opacity duration-150">
              Sign out
            </div>
          )}
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* ─────────────── Desktop Sidebar ─────────────── */}
      <motion.aside
        animate={{ width: collapsed ? SIDEBAR_W_COLLAPSED : SIDEBAR_W_EXPANDED }}
        transition={{ type: 'spring', stiffness: 320, damping: 32 }}
        className="hidden md:flex flex-col shrink-0 h-screen sticky top-0 z-30 overflow-hidden
          bg-[#0b0d15]/95 border-r border-white/[0.06] backdrop-blur-xl"
      >
        {sidebarContent}
      </motion.aside>

      {/* ─────────────── Mobile Overlay Drawer ─────────────── */}
      <AnimatePresence>
        {mobileOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              key="mobile-backdrop"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              onClick={onMobileClose}
              className="md:hidden fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            />

            {/* Drawer */}
            <motion.aside
              key="mobile-drawer"
              initial={{ x: -SIDEBAR_W_EXPANDED }}
              animate={{ x: 0 }}
              exit={{ x: -SIDEBAR_W_EXPANDED }}
              transition={{ type: 'spring', stiffness: 320, damping: 32 }}
              style={{ width: SIDEBAR_W_EXPANDED }}
              className="md:hidden fixed left-0 top-0 bottom-0 z-50 flex flex-col
                bg-[#0b0d15] border-r border-white/[0.06]"
            >
              {sidebarContent}
            </motion.aside>
          </>
        )}
      </AnimatePresence>
    </>
  )
}
