import { type FormEvent, useEffect, useId, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { Mail, Lock, ArrowLeft, CheckCircle2, ArrowRight, KeyRound, X } from 'lucide-react'
import { supabase } from '../auth/supabaseClient'
import { AuthLayout } from '../components/ui/AuthLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { PasswordStrengthMeter, getPasswordRequirements } from '../components/auth/PasswordStrengthMeter'

/** View 1: Request Password Reset Link */
function RequestView() {
  const [email, setEmail] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const emailId = useId()

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)

    if (!email.trim()) {
      setError('Please enter your account email address.')
      return
    }

    setIsSubmitting(true)
    try {
      const { error: supaErr } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/password-reset?token=true`,
      })
      if (supaErr) throw supaErr
      setSubmitted(true)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to send reset link.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (submitted) {
    return (
      <Card glass className="text-center">
        <CardHeader className="items-center">
          <div className="w-12 h-12 rounded-2xl bg-indigo-500/20 border border-indigo-500/40 text-indigo-400 flex items-center justify-center mb-2 shadow-lg shadow-indigo-500/10">
            <Mail className="w-6 h-6" />
          </div>
          <CardTitle>Check your inbox</CardTitle>
          <CardDescription className="max-w-xs mx-auto">
            If an account with <span className="font-semibold text-slate-200">{email}</span> exists, we've sent password reset instructions.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 text-xs text-slate-400">
            Check your spam or junk folder if you don't see the email within 2 minutes.
          </div>
          <Button
            variant="secondary"
            fullWidth
            onClick={() => setSubmitted(false)}
          >
            Try another email address
          </Button>
          <div className="text-center pt-2">
            <Link
              to="/login"
              className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              Back to sign in
            </Link>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card glass>
      <CardHeader>
        <div className="w-10 h-10 rounded-xl bg-indigo-500/15 border border-indigo-500/30 text-indigo-400 flex items-center justify-center mb-1">
          <KeyRound className="w-5 h-5" />
        </div>
        <CardTitle>Reset your password</CardTitle>
        <CardDescription>
          Enter your registered email address and we'll send you a password recovery link
        </CardDescription>
      </CardHeader>

      <CardContent>
        {error && (
          <div className="mb-4">
            <Alert variant="error" message={error} onClose={() => setError(null)} />
          </div>
        )}

        <form onSubmit={(e) => { void handleSubmit(e) }} className="flex flex-col gap-4" noValidate>
          <Input
            id={emailId}
            label="Account email"
            type="email"
            placeholder="name@company.com"
            autoComplete="email"
            required
            leftIcon={<Mail className="w-4 h-4 text-slate-400" />}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />

          <Button
            type="submit"
            variant="primary"
            fullWidth
            size="lg"
            isLoading={isSubmitting}
            rightIcon={<ArrowRight className="w-4 h-4" />}
          >
            {isSubmitting ? 'Sending link...' : 'Send Reset Link'}
          </Button>
        </form>

        <div className="text-center text-xs text-slate-400 pt-4 mt-4 border-t border-white/5">
          Remembered your password?{' '}
          <Link
            to="/login"
            className="font-semibold text-indigo-400 hover:text-indigo-300 transition-colors underline underline-offset-4"
          >
            Back to login
          </Link>
        </div>
      </CardContent>
    </Card>
  )
}

/** View 2: Set New Password Confirmation */
function ConfirmView() {
  const navigate = useNavigate()
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  // MED-6: Guard — verify a real recovery session exists before showing the form
  const [sessionChecked, setSessionChecked] = useState(false)
  const [sessionValid, setSessionValid] = useState(false)

  const newPasswordId = useId()
  const confirmPasswordId = useId()

  // Verify the Supabase recovery session on mount.
  // Supabase's detectSessionInUrl:true processes the hash token automatically,
  // but we must wait for that to complete before calling updateUser().
  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSessionValid(!!data.session?.user)
      setSessionChecked(true)
    })
  }, [])

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)

    const reqs = getPasswordRequirements(newPassword)
    const passedCount = reqs.filter((r) => r.pass).length
    if (passedCount < 5) {
      setError('Please satisfy all password strength requirements below.')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }

    setIsSubmitting(true)
    try {
      const { error: supaErr } = await supabase.auth.updateUser({ password: newPassword })
      if (supaErr) throw supaErr
      setSuccess(true)
      setTimeout(() => { navigate('/login') }, 3000)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update password.')
    } finally {
      setIsSubmitting(false)
    }
  }

  // Still waiting for session check
  if (!sessionChecked) {
    return (
      <Card glass className="text-center">
        <CardContent className="py-12">
          <div className="flex flex-col items-center gap-3">
            <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
            <p className="text-sm text-slate-400">Verifying reset link…</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  // No valid recovery session — link is invalid or expired
  if (!sessionValid) {
    return (
      <Card glass className="text-center">
        <CardHeader className="items-center">
          <div className="w-12 h-12 rounded-2xl bg-red-500/20 border border-red-500/40 text-red-400 flex items-center justify-center mb-2">
            <X className="w-6 h-6" />
          </div>
          <CardTitle>Link Invalid or Expired</CardTitle>
          <CardDescription>
            This password reset link has already been used or has expired. Please request a new one.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <Button variant="primary" fullWidth onClick={() => navigate('/password-reset')}>
            Request new link
          </Button>
          <Link to="/login" className="text-xs text-slate-500 hover:text-slate-300 transition-colors text-center">
            Back to login
          </Link>
        </CardContent>
      </Card>
    )
  }

  if (success) {
    return (
      <Card glass className="text-center">
        <CardHeader className="items-center">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 flex items-center justify-center mb-2 shadow-lg shadow-emerald-500/10">
            <CheckCircle2 className="w-6 h-6" />
          </div>
          <CardTitle>Password updated!</CardTitle>
          <CardDescription>
            Your account password has been reset successfully.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 text-xs text-slate-400">
            Redirecting to sign-in page...
          </div>
          <Button
            variant="primary"
            fullWidth
            onClick={() => navigate('/login')}
          >
            Sign In Now
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card glass>
      <CardHeader>
        <CardTitle>Create new password</CardTitle>
        <CardDescription>
          Enter a new secure password for your workspace account
        </CardDescription>
      </CardHeader>

      <CardContent>
        {error && (
          <div className="mb-4">
            <Alert variant="error" message={error} onClose={() => setError(null)} />
          </div>
        )}

        <form onSubmit={(e) => { void handleSubmit(e) }} className="flex flex-col gap-4" noValidate>
          <div className="flex flex-col gap-1">
            <Input
              id={newPasswordId}
              label="New password"
              type="password"
              placeholder="••••••••••••"
              autoComplete="new-password"
              required
              leftIcon={<Lock className="w-4 h-4 text-slate-400" />}
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
            <PasswordStrengthMeter password={newPassword} />
          </div>

          <Input
            id={confirmPasswordId}
            label="Confirm new password"
            type="password"
            placeholder="Re-enter new password"
            autoComplete="new-password"
            required
            leftIcon={<Lock className="w-4 h-4 text-slate-400" />}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            error={
              confirmPassword && newPassword !== confirmPassword
                ? 'Passwords do not match'
                : undefined
            }
          />

          <Button
            type="submit"
            variant="primary"
            fullWidth
            size="lg"
            isLoading={isSubmitting}
            rightIcon={<ArrowRight className="w-4 h-4" />}
          >
            {isSubmitting ? 'Updating...' : 'Set New Password'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

export default function PasswordResetPage() {
  const [searchParams] = useSearchParams()
  const isConfirm = searchParams.get('token') === 'true' || searchParams.has('type')

  return (
    <AuthLayout
      title={isConfirm ? 'New Password' : 'Account Recovery'}
      subtitle="Secure password management powered by Supabase Auth"
    >
      {isConfirm ? <ConfirmView /> : <RequestView />}
    </AuthLayout>
  )
}
