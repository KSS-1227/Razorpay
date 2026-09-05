import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react'

export interface AlertProps {
  variant?: 'error' | 'success' | 'info'
  title?: string
  message: string
  onClose?: () => void
  className?: string
}

export function Alert({
  variant = 'error',
  title,
  message,
  onClose,
  className = '',
}: AlertProps) {
  const variantStyles = {
    error: {
      container: 'bg-red-950/40 border-red-500/30 text-red-200 shadow-red-950/20',
      icon: <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />,
    },
    success: {
      container: 'bg-emerald-950/40 border-emerald-500/30 text-emerald-200 shadow-emerald-950/20',
      icon: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />,
    },
    info: {
      container: 'bg-indigo-950/40 border-indigo-500/30 text-indigo-200 shadow-indigo-950/20',
      icon: <Info className="w-4 h-4 text-indigo-400 shrink-0 mt-0.5" />,
    },
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -8, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: -8, scale: 0.96 }}
        transition={{ duration: 0.2 }}
        className={`p-3.5 rounded-xl border backdrop-blur-md shadow-lg flex items-start gap-3 text-xs leading-relaxed ${variantStyles[variant].container} ${className}`}
        role="alert"
      >
        {variantStyles[variant].icon}

        <div className="flex-1 text-left">
          {title && <h4 className="font-semibold text-slate-100 mb-0.5">{title}</h4>}
          <p className="opacity-90">{message}</p>
        </div>

        {onClose && (
          <button
            type="button"
            onClick={onClose}
            className="p-1 text-slate-400 hover:text-slate-200 transition-colors rounded-lg hover:bg-white/10"
            aria-label="Dismiss alert"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
      </motion.div>
    </AnimatePresence>
  )
}
