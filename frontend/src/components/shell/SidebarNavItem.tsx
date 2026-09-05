/**
 * SidebarNavItem — a single animated navigation link in the sidebar.
 */
import { NavLink } from 'react-router-dom'
import { motion } from 'framer-motion'
import type { NavItem } from './navConfig'

interface Props {
  item: NavItem
  collapsed: boolean
}

export function SidebarNavItem({ item, collapsed }: Props) {
  const Icon = item.icon

  return (
    <NavLink
      to={item.path}
      end={item.id === 'dashboard'}
      className={({ isActive }) =>
        `group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium
         transition-all duration-150 outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60
         ${
           isActive
             ? 'bg-indigo-500/12 text-indigo-300 shadow-sm'
             : 'text-slate-400 hover:bg-white/5 hover:text-slate-100'
         }
         ${collapsed ? 'justify-center px-2' : ''}`
      }
    >
      {({ isActive }) => (
        <>
          {/* Active left-edge indicator */}
          {isActive && (
            <motion.div
              layoutId="sidebar-active-pill"
              className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-indigo-400"
              transition={{ type: 'spring', stiffness: 380, damping: 30 }}
            />
          )}

          {/* Icon */}
          <div
            className={`shrink-0 transition-all duration-150 ${
              isActive
                ? 'text-indigo-400'
                : 'text-slate-500 group-hover:text-slate-300'
            }`}
          >
            <Icon className="w-[18px] h-[18px]" strokeWidth={isActive ? 2.2 : 1.8} />
          </div>

          {/* Label */}
          {!collapsed && (
            <motion.span
              initial={false}
              animate={{ opacity: 1, x: 0 }}
              className="truncate leading-none"
            >
              {item.label}
            </motion.span>
          )}

          {/* Badge */}
          {!collapsed && item.badge !== undefined && (
            <span className="ml-auto shrink-0 min-w-[18px] h-[18px] px-1 rounded-full bg-indigo-500/20 text-indigo-300 text-[10px] font-semibold flex items-center justify-center">
              {item.badge}
            </span>
          )}

          {/* Tooltip when collapsed */}
          {collapsed && (
            <div className="pointer-events-none absolute left-full ml-2 z-50 whitespace-nowrap rounded-lg bg-slate-800 border border-white/10 text-slate-100 text-xs px-2.5 py-1.5 shadow-xl opacity-0 group-hover:opacity-100 transition-opacity duration-150">
              {item.label}
              {item.badge !== undefined && (
                <span className="ml-1.5 text-indigo-300">({item.badge})</span>
              )}
            </div>
          )}
        </>
      )}
    </NavLink>
  )
}
