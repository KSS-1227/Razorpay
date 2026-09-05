/**
 * React auth context — provides authentication state and methods.
 *
 * Session is persisted by Supabase (localStorage) so it survives page refresh.
 * tokenStore keeps an in-memory copy of the access token for synchronous API calls.
 *
 * Fixes applied:
 *  - CRIT-2: Role now read from app_metadata first (not payload.role which is always "authenticated")
 *  - CRIT-3: startRefreshLoop / stopRefreshLoop wired up on session apply / logout
 *  - CRIT-4: Removed race-condition `initialised` ref — onAuthStateChange handles all events
 *  - CRIT-5: displayName forwarded to supabase.auth.signUp via options.data
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { supabase } from './supabaseClient'
import { clearTokens, setTokens } from './tokenStore'
import { startRefreshLoop, stopRefreshLoop } from './refreshLoop'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuthUser {
  id: string
  email: string
  role: string
}

export interface AuthContextValue {
  user: AuthUser | null
  workspaceId: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, displayName?: string) => Promise<void>
  logout: () => Promise<void>
  selectWorkspace: (id: string) => void
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

const AuthContext = createContext<AuthContextValue | null>(null)

// Workspace ID persistence key
const WS_KEY = 'innova_workspace_id'

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function AuthProvider({ children }: { readonly children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [workspaceId, setWorkspaceId] = useState<string | null>(() => {
    // Restore workspace from localStorage on mount
    try { return localStorage.getItem(WS_KEY) } catch { return null }
  })
  const [isLoading, setIsLoading] = useState(true)

  // ── Session → user state ─────────────────────────────────────────────────

  const applySession = useCallback(
    (session: {
      access_token: string
      refresh_token: string
      user: { id: string; email?: string | null }
    } | null) => {
      if (!session) {
        clearTokens()
        stopRefreshLoop()  // CRIT-3: stop refresh loop on sign-out
        setUser(null)
        return
      }

      setTokens(session.access_token, session.refresh_token)
      startRefreshLoop()  // CRIT-3: start refresh loop on sign-in

      // CRIT-2: Read custom app role from app_metadata first.
      // payload.role in a Supabase JWT is ALWAYS "authenticated" — not the custom role.
      let role = 'Viewer'
      try {
        const payload = JSON.parse(atob(session.access_token.split('.')[1]))
        role = (payload.app_metadata?.role as string | undefined)
          ?? (payload.user_metadata?.role as string | undefined)
          ?? 'Viewer'
      } catch {
        // Malformed token — keep default role
      }

      setUser({
        id: session.user.id,
        email: session.user.email ?? '',
        role,
      })
    },
    []
  )

  // ── Subscribe to Supabase auth state ─────────────────────────────────────
  //
  // CRIT-4: Removed the `initialised` ref guard which caused a race condition
  // where SIGNED_IN events fired during OAuth callback were silently dropped.
  // Supabase fires INITIAL_SESSION on subscription so no separate getSession()
  // call is needed — onAuthStateChange handles both initial state and changes.

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      (_event, session) => {
        applySession(session)
        setIsLoading(false)
      }
    )

    return () => { subscription.unsubscribe() }
  }, [applySession])

  // ── Auth methods ─────────────────────────────────────────────────────────

  const login = useCallback(async (email: string, password: string) => {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password })
    if (error) throw error
    if (data.session) applySession(data.session)
  }, [applySession])

  // CRIT-5: displayName is now forwarded to Supabase user metadata
  const register = useCallback(async (
    email: string,
    password: string,
    displayName?: string,
  ) => {
    const { error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: displayName ? { display_name: displayName } : undefined,
      },
    })
    if (error) throw error
  }, [])

  const logout = useCallback(async () => {
    stopRefreshLoop()  // CRIT-3: stop loop before sign-out
    try {
      await supabase.auth.signOut()
    } catch (err) {
      console.error('Supabase signOut error:', err)
    }
    clearTokens()
    setUser(null)
    setWorkspaceId(null)
    try { localStorage.removeItem(WS_KEY) } catch { /* ignore */ }
  }, [])

  const selectWorkspace = useCallback((id: string) => {
    setWorkspaceId(id)
    try { localStorage.setItem(WS_KEY, id) } catch { /* ignore */ }
  }, [])

  // ── Context value ────────────────────────────────────────────────────────

  const value: AuthContextValue = {
    user,
    workspaceId,
    isAuthenticated: user !== null,
    isLoading,
    login,
    register,
    logout,
    selectWorkspace,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
