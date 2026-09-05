import { motion } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { FloatingParticles } from './FloatingParticles'

interface FullScreenLoaderProps {
  message?: string
}

export function FullScreenLoader({ message = 'Loading...' }: FullScreenLoaderProps) {
  return (
    <div className="min-h-screen w-full bg-[#090a0f] flex flex-col items-center justify-center relative overflow-hidden">
      <FloatingParticles />

      <div className="relative z-10 flex flex-col items-center gap-6">
        {/* Animated logo mark */}
        <motion.div
          initial={{ opacity: 0, scale: 0.7 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="relative"
        >
          {/* Outer glow ring */}
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 3, ease: 'linear', repeat: Infinity }}
            className="absolute inset-0 rounded-full border-2 border-transparent"
            style={{
              background: 'conic-gradient(from 0deg, transparent 60%, rgba(99,102,241,0.8), transparent) border-box',
              WebkitMask: 'linear-gradient(#fff 0 0) padding-box, linear-gradient(#fff 0 0)',
              WebkitMaskComposite: 'destination-out',
              maskComposite: 'exclude',
            }}
          />

          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 via-indigo-500 to-purple-500 flex items-center justify-center shadow-2xl shadow-indigo-500/40">
            <Sparkles className="w-7 h-7 text-white" />
          </div>

          {/* Pulse rings */}
          <motion.div
            animate={{ scale: [1, 1.6], opacity: [0.5, 0] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: 'easeOut' }}
            className="absolute inset-0 rounded-2xl border border-indigo-500/60"
          />
          <motion.div
            animate={{ scale: [1, 2], opacity: [0.3, 0] }}
            transition={{ duration: 1.8, repeat: Infinity, ease: 'easeOut', delay: 0.4 }}
            className="absolute inset-0 rounded-2xl border border-indigo-500/30"
          />
        </motion.div>

        {/* Dot loader */}
        <div className="flex items-center gap-1.5">
          {[0, 0.15, 0.3].map((delay, i) => (
            <motion.div
              key={i}
              animate={{ scale: [1, 1.4, 1], opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 0.9, repeat: Infinity, delay, ease: 'easeInOut' }}
              className="w-1.5 h-1.5 rounded-full bg-indigo-400"
            />
          ))}
        </div>

        <motion.p
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-sm text-slate-400 font-medium tracking-wide"
        >
          {message}
        </motion.p>
      </div>
    </div>
  )
}
