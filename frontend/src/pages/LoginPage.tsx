import { type FormEvent, useId, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Lock, Mail, ArrowRight } from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { AuthLayout } from '../components/ui/AuthLayout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { Input } from '../components/ui/Input'
import { Button } from '../components/ui/Button'
import { Alert } from '../components/ui/Alert'
import { OAuthProviders } from '../components/auth/OAuthProviders'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  // HIGH-2: Read the location the user was trying to reach before being redirected to login
  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? '/workspaces'

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  const emailId = useId()
  const passwordId = useId()

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)

    if (!email.trim() || !password) {
      setError('Please enter both email and password.')
      return
    }

    setIsSubmitting(true)
    try {
      await login(email, password)
      navigate(from, { replace: true })
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid credentials'
      if (msg.toLowerCase().includes('invalid login credentials')) {
        setError('Invalid login credentials. Make sure you have created an account first, or check that your password is correct.')
      } else if (msg.toLowerCase().includes('email not confirmed')) {
        setError('Email not confirmed. Please check your inbox for the verification link or disable "Confirm email" in Supabase settings.')
      } else {
        setError(msg)
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthLayout
      title="Welcome Back"
      subtitle="Sign in to access your multi-modal GraphRAG workspace"
    >
      <Card glass>
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>
            Enter your workspace credentials to continue
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
              id={emailId}
              label="Email address"
              type="email"
              placeholder="name@company.com"
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
                placeholder="••••••••••••"
                autoComplete="current-password"
                required
                leftIcon={<Lock className="w-4 h-4 text-slate-400" />}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
              <div className="flex items-center justify-end mt-1">
                <Link
                  to="/password-reset"
                  className="text-xs font-medium text-indigo-400 hover:text-indigo-300 transition-colors"
                >
                  Forgot password?
                </Link>
              </div>
            </div>

            <Button
              type="submit"
              variant="primary"
              fullWidth
              size="lg"
              isLoading={isSubmitting}
              rightIcon={<ArrowRight className="w-4 h-4" />}
            >
              {isSubmitting ? 'Authenticating...' : 'Sign in to Workspace'}
            </Button>
          </form>

          <OAuthProviders onError={setError} />

          <div className="text-center text-xs text-slate-400 pt-2 border-t border-white/5">
            Don't have an account?{' '}
            <Link
              to="/register"
              className="font-semibold text-indigo-400 hover:text-indigo-300 transition-colors underline underline-offset-4"
            >
              Create an account
            </Link>
          </div>
        </CardContent>
      </Card>
    </AuthLayout>
  )
}
