import { useState } from 'react'
import { Button } from '../ui/Button'
import { supabase } from '../../auth/supabaseClient'

export interface OAuthProvidersProps {
  onError: (msg: string | null) => void
}

export function OAuthProviders({ onError }: OAuthProvidersProps) {
  const [loadingProvider, setLoadingProvider] = useState<string | null>(null)

  async function handleOAuthLogin(provider: 'google' | 'github') {
    onError(null)
    setLoadingProvider(provider)
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: { redirectTo: `${window.location.origin}/auth/callback` },
      })
      if (error) throw error
    } catch (err: unknown) {
      onError(err instanceof Error ? err.message : `Failed to sign in with ${provider}`)
      setLoadingProvider(null)
    }
  }

  return (
    <div className="flex flex-col gap-3 w-full my-4">
      <div className="relative flex items-center justify-center w-full my-1">
        <div className="absolute inset-0 flex items-center">
          <div className="w-full border-t border-slate-800" />
        </div>
        <span className="relative z-10 px-3 text-[11px] font-medium uppercase tracking-wider text-slate-500 bg-[#0c0e17] rounded-full">
          Or continue with
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 w-full">
        {/* Google OAuth Button */}
        <Button
          type="button"
          variant="oauth"
          isLoading={loadingProvider === 'google'}
          onClick={() => { void handleOAuthLogin('google') }}
          leftIcon={
            <svg className="w-4 h-4" viewBox="0 0 24 24">
              <path
                fill="#EA4335"
                d="M12 5c1.6 0 3 .6 4.1 1.6l3.1-3.1C17.3 1.7 14.8 1 12 1 7.5 1 3.7 3.6 1.9 7.3l3.7 2.9C6.5 7.3 9 5 12 5z"
              />
              <path
                fill="#4285F4"
                d="M23.5 12.3c0-.8-.1-1.6-.2-2.3H12v4.6h6.5c-.3 1.5-1.1 2.8-2.4 3.7l3.7 2.9c2.2-2 3.7-5 3.7-8.9z"
              />
              <path
                fill="#FBBC05"
                d="M5.6 14.8c-.2-.7-.4-1.5-.4-2.3 0-.8.2-1.6.4-2.3L1.9 7.3C.7 9.7 0 12.3 0 15s.7 5.3 1.9 7.7l3.7-2.9c-.8-1.5-1.3-3.2-1.3-5z"
              />
              <path
                fill="#34A853"
                d="M12 23c3.2 0 6-1.1 8-3l-3.7-2.9c-1.1.7-2.5 1.2-4.3 1.2-3 0-5.5-2.3-6.4-5.2L1.9 16C3.7 19.7 7.5 23 12 23z"
              />
            </svg>
          }
        >
          Google
        </Button>

        {/* GitHub OAuth Button */}
        <Button
          type="button"
          variant="oauth"
          isLoading={loadingProvider === 'github'}
          onClick={() => { void handleOAuthLogin('github') }}
          leftIcon={
            <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
          }
        >
          GitHub
        </Button>
      </div>
    </div>
  )
}
