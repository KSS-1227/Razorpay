import type { ReactNode } from 'react'
import { motion } from 'framer-motion'
import { FloatingParticles } from './FloatingParticles'
import { ShieldCheck, Sparkles } from 'lucide-react'

export interface AuthLayoutProps {
  children: ReactNode
  title: string
  subtitle?: string
}

export function AuthLayout({ children, title, subtitle }: AuthLayoutProps) {
  return (
    <div className="min-h-screen w-full bg-[#090a0f] text-slate-100 flex flex-col justify-between items-center relative overflow-hidden px-4 py-8 sm:px-6">
      {/* Background Floating Particles & Radial Gradients */}
      <FloatingParticles />

      {/* Header / Brand Logo */}
      <header className="relative z-10 w-full max-w-md flex flex-col items-center gap-3 pt-4 sm:pt-8 text-center">
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="flex items-center gap-2.5 px-3.5 py-1.5 rounded-full bg-slate-900/80 border border-indigo-500/30 backdrop-blur-xl shadow-primary-glow"
        >
          <div className="w-6 h-6 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-white shadow-md">
            <Sparkles className="w-3.5 h-3.5" />
          </div>
          <span className="text-xs font-semibold tracking-wide bg-clip-text text-transparent bg-gradient-to-r from-indigo-200 via-white to-purple-200">
            InnovaHack Platform
          </span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse ml-0.5" />
        </motion.div>

        <div className="flex flex-col gap-1 mt-1">
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-b from-white via-slate-100 to-slate-400">
            {title}
          </h1>
          {subtitle && (
            <p className="text-xs sm:text-sm text-slate-400 max-w-xs mx-auto leading-relaxed">
              {subtitle}
            </p>
          )}
        </div>
      </header>

      {/* Main Authentication Form Container */}
      <main className="relative z-10 w-full max-w-md my-auto py-6">
        <motion.div
          initial={{ opacity: 0, y: 16, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
        >
          {children}
        </motion.div>
      </main>

      {/* Footer / System Status */}
      <footer className="relative z-10 w-full max-w-md flex flex-col sm:flex-row items-center justify-between text-[11px] text-slate-500 gap-2 pb-2 border-t border-white/5 pt-4">
        <div className="flex items-center gap-1.5">
          <ShieldCheck className="w-3.5 h-3.5 text-indigo-400" />
          <span>Ant Gravity End-to-End Encryption</span>
        </div>
        <div className="flex items-center gap-3">
          <a href="#" className="hover:text-slate-300 transition-colors">Privacy</a>
          <span>•</span>
          <a href="#" className="hover:text-slate-300 transition-colors">Terms</a>
          <span>•</span>
          <a href="#" className="hover:text-slate-300 transition-colors">Support</a>
        </div>
      </footer>
    </div>
  )
}
