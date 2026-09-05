/**
 * WorkspacePlaceholder — premium placeholder for any route not yet implemented.
 * Auto-resolves title and icon from nav config based on current pathname.
 */
import { motion, type Variants } from 'framer-motion'
import { Construction, Sparkles } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { useLocation } from 'react-router-dom'
import { NAV_ITEMS } from '../../components/shell/navConfig'

interface Props {
  title?: string
  description?: string
  icon?: LucideIcon
}

// Shared variant factory — avoids repeating ease cast everywhere
function fadeUp(delay = 0): Variants {
  return {
    hidden:   { opacity: 0, y: 16 },
    visible:  {
      opacity: 1,
      y: 0,
      transition: { delay, duration: 0.35, ease: 'easeOut' },
    },
  }
}

const containerVariants: Variants = {
  hidden:   {},
  visible:  { transition: { staggerChildren: 0.08 } },
}

// Per-nav-item gradient colours
const GRADIENTS: Record<string, string> = {
  dashboard:         'from-indigo-500 to-purple-600',
  cases:             'from-blue-500 to-cyan-600',
  upload:            'from-violet-500 to-indigo-600',
  'knowledge-graph': 'from-emerald-500 to-teal-600',
  'ai-assistant':    'from-orange-500 to-amber-600',
  evidence:          'from-rose-500 to-pink-600',
  reports:           'from-sky-500 to-blue-600',
  settings:          'from-slate-400 to-slate-600',
  profile:           'from-indigo-400 to-violet-600',
}

export default function WorkspacePlaceholder({ title, description, icon }: Props) {
  const location = useLocation()

  // Auto-detect from nav config
  const navItem = NAV_ITEMS.find((n) => n.path === location.pathname)
  const resolvedTitle = title ?? navItem?.label ?? 'Coming Soon'
  const ResolvedIcon: LucideIcon = icon ?? navItem?.icon ?? Construction
  const gradient = GRADIENTS[navItem?.id ?? ''] ?? 'from-indigo-500 to-purple-600'

  const features = ['Data ingestion', 'AI processing', 'Visual explorer']

  return (
    <div className="flex items-center justify-center min-h-full px-6 py-20">
      <motion.div
        variants={containerVariants}
        initial="hidden"
        animate="visible"
        className="flex flex-col items-center text-center max-w-sm gap-7 w-full"
      >
        {/* ── Icon halo ── */}
        <motion.div variants={fadeUp(0)} className="relative">
          {/* Glow */}
          <div className={`absolute inset-0 rounded-3xl bg-gradient-to-br ${gradient} blur-2xl opacity-25 scale-125`} />
          {/* Icon box */}
          <div className={`relative w-20 h-20 rounded-3xl bg-gradient-to-br ${gradient} flex items-center justify-center shadow-2xl`}>
            <ResolvedIcon className="w-9 h-9 text-white" strokeWidth={1.6} />
          </div>
          {/* Sparkle badge */}
          <div className="absolute -top-1.5 -right-1.5 w-6 h-6 rounded-full bg-[#0f1120] border border-white/10 flex items-center justify-center">
            <Sparkles className="w-3 h-3 text-indigo-400" />
          </div>
        </motion.div>

        {/* ── Title + description ── */}
        <motion.div variants={fadeUp(0.08)} className="flex flex-col gap-2">
          <h1 className="text-2xl font-extrabold tracking-tight text-white">
            {resolvedTitle}
          </h1>
          <p className="text-sm text-slate-400 leading-relaxed">
            {description ?? 'This module is under active development and will be available soon.'}
          </p>
        </motion.div>

        {/* ── Status badge ── */}
        <motion.div variants={fadeUp(0.16)}>
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-slate-900/70 border border-white/[0.07] text-xs font-medium text-slate-400">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            In development
          </div>
        </motion.div>

        {/* ── Feature preview dots ── */}
        <motion.div variants={fadeUp(0.24)} className="grid grid-cols-3 gap-3 w-full">
          {features.map((feat) => (
            <div
              key={feat}
              className="flex flex-col items-center gap-2 p-3.5 rounded-xl bg-slate-900/50 border border-white/[0.05]"
            >
              <div className={`w-2 h-2 rounded-full bg-gradient-to-br ${gradient}`} />
              <span className="text-[10px] text-slate-500 leading-tight">{feat}</span>
            </div>
          ))}
        </motion.div>
      </motion.div>
    </div>
  )
}
