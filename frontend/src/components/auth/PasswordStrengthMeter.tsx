import { Check, X } from 'lucide-react'

export interface Requirement {
  label: string
  pass: boolean
}

export function getPasswordRequirements(password: string): Requirement[] {
  return [
    { label: 'At least 8 characters', pass: password.length >= 8 },
    { label: 'One uppercase letter (A-Z)', pass: /[A-Z]/.test(password) },
    { label: 'One lowercase letter (a-z)', pass: /[a-z]/.test(password) },
    { label: 'One number (0-9)', pass: /\d/.test(password) },
    { label: 'One special character (!@#$...)', pass: /[^A-Za-z0-9]/.test(password) },
  ]
}

export function PasswordStrengthMeter({ password }: { password: string }) {
  if (!password) return null

  const requirements = getPasswordRequirements(password)
  const passedCount = requirements.filter((r) => r.pass).length
  const percentage = (passedCount / requirements.length) * 100

  const getStrengthColor = () => {
    if (passedCount <= 2) return 'bg-red-500 shadow-red-500/50'
    if (passedCount <= 4) return 'bg-amber-400 shadow-amber-400/50'
    return 'bg-emerald-400 shadow-emerald-400/50'
  }

  const getStrengthLabel = () => {
    if (passedCount <= 2) return 'Weak password'
    if (passedCount <= 4) return 'Good password'
    return 'Strong password'
  }

  return (
    <div className="flex flex-col gap-2.5 my-2 p-3 rounded-xl bg-slate-900/60 border border-white/5 backdrop-blur-md">
      <div className="flex items-center justify-between text-[11px] font-medium text-slate-400">
        <span>Password strength</span>
        <span className={passedCount === 5 ? 'text-emerald-400' : 'text-slate-300'}>
          {getStrengthLabel()}
        </span>
      </div>

      {/* Progress Bar */}
      <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden flex">
        <div
          className={`h-full transition-all duration-300 rounded-full ${getStrengthColor()}`}
          style={{ width: `${percentage}%` }}
        />
      </div>

      {/* Criteria Checklist */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 mt-1 text-[11px]">
        {requirements.map((req) => (
          <div
            key={req.label}
            className={`flex items-center gap-1.5 transition-colors duration-200 ${
              req.pass ? 'text-emerald-400 font-medium' : 'text-slate-500'
            }`}
          >
            {req.pass ? (
              <Check className="w-3 h-3 text-emerald-400 shrink-0" />
            ) : (
              <X className="w-3 h-3 text-slate-600 shrink-0" />
            )}
            <span className="truncate">{req.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
