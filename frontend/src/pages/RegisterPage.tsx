import { type FormEvent, useId, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { User, Mail, Lock, CheckCircle2, ArrowRight } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { supabase } from '../auth/supabaseClient'
import { AuthLayout } from '../components/ui/AuthLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { OAuthProviders } from '../components/auth/OAuthProviders'
import { PasswordStrengthMeter, getPasswordRequirements } from '../components/auth/PasswordStrengthMeter'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()

  const [displayName, setDisplayName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const nameId = useId()
  const emailId = useId()
  const passwordId = useId()
  const confirmPasswordId = useId()

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)

    if (!displayName.trim()) {
      setError('Please enter your full name.')
      return
    }

    const reqs = getPasswordRequirements(password)
    const passedCount = reqs.filter((r) => r.pass).length
    if (passedCount < 5) {
      setError('Please satisfy all password strength requirements below.')
      return
    }

    if (password !== confirmPassword) {
      setError('Passwords do not match. Please check again.')
      return
    }

    setIsSubmitting(true)
    try {
      // Pass displayName so it is stored in Supabase user_metadata (CRIT-5)
      await register(email, password, displayName.trim())

      // LOW-6: Check if Supabase returned a session immediately (email confirmation disabled).
      // If so, the user is already logged in — send them to /workspaces.
      // If no session, email confirmation is required — show the verification message.
      const { data: { session } } = await supabase.auth.getSession()
      if (session) {
        navigate('/workspaces', { replace: true })
      } else {
        setSuccess(true)
        setTimeout(() => { navigate('/login') }, 4000)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Registration failed. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  if (success) {
    return (
      <AuthLayout
        title="Account Created"
        subtitle="Verify your email to activate your workspace"
      >
        <Card glass className="text-center">
          <CardHeader className="items-center">
            <div className="w-12 h-12 rounded-2xl bg-emerald-500/20 border border-emerald-500/40 text-emerald-400 flex items-center justify-center mb-2 shadow-lg shadow-emerald-500/10">
              <CheckCircle2 className="w-6 h-6" />
            </div>
            <CardTitle>Verification email sent!</CardTitle>
            <CardDescription className="max-w-xs mx-auto">
              We've dispatched a confirmation link to{' '}
              <span className="font-semibold text-slate-200">{email}</span>. Please click the link to activate your account.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <div className="p-3 rounded-xl bg-slate-900/60 border border-white/5 text-xs text-slate-400">
              Redirecting to sign-in page in a few seconds...
            </div>
            <Button
              variant="secondary"
              fullWidth
              onClick={() => navigate('/login')}
            >
              Return to Login Now
            </Button>
          </CardContent>
        </Card>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout
      title="Create Account"
      subtitle="Get started with multi-modal knowledge graph intelligence"
    >
      <Card glass>
        <CardHeader>
          <CardTitle>Sign up</CardTitle>
          <CardDescription>
            Build unified graph databases across your enterprise docs
          </CardDescription>
        </CardHeader>

        <CardContent>
          {error && (
            <div className="mb-4">
              <Alert
                variant="error"
                message={error}
                onClose={() => setError(null)}
              />
            </div>
          )}

          <form onSubmit={(e) => { void handleSubmit(e) }} className="flex flex-col gap-4" noValidate>
            <Input
              id={nameId}
              label="Full name"
              type="text"
              placeholder="Alex Mercer"
              autoComplete="name"
              required
              leftIcon={<User className="w-4 h-4 text-slate-400" />}
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
            />

            <Input
              id={emailId}
              label="Work email address"
              type="email"
              placeholder="alex@enterprise.com"
              autoComplete="email"
              required
              leftIcon={<Mail className="w-4 h-4 text-slate-400" />}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />

            <div className="flex flex-col gap-1">
              <Input
                id={passwordId}
                label="Password"
                type="password"
                placeholder="Create strong password"
                autoComplete="new-password"
                required
                leftIcon={<Lock className="w-4 h-4 text-slate-400" />}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <PasswordStrengthMeter password={password} />
            </div>

            <Input
              id={confirmPasswordId}
              label="Confirm password"
              type="password"
              placeholder="Re-enter password"
              autoComplete="new-password"
              required
              leftIcon={<Lock className="w-4 h-4 text-slate-400" />}
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              error={
                confirmPassword && password !== confirmPassword
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
              {isSubmitting ? 'Creating account...' : 'Create Account'}
            </Button>
          </form>

          <OAuthProviders onError={setError} />

          <div className="text-center text-xs text-slate-400 pt-2 border-t border-white/5">
            Already have an account?{' '}
            <Link
              to="/login"
              className="font-semibold text-indigo-400 hover:text-indigo-300 transition-colors underline underline-offset-4"
            >
              Sign in
            </Link>
          </div>
        </CardContent>
      </Card>
    </AuthLayout>
  )
}
