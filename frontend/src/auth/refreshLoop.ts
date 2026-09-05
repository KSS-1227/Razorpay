/**
 * Token refresh loop — proactively refreshes the access token before it
 * expires, and enforces the 30-day session age limit.
 *
 * Call startRefreshLoop() once after a successful login.
 * Call stopRefreshLoop() on logout.
 *
 * Requirements: 10.4, 10.5
 */
import { supabase } from './supabaseClient'
import { clearTokens, getAccessToken, setTokens } from './tokenStore'

/** Refresh interval in milliseconds (30 seconds). */
const REFRESH_INTERVAL_MS = 30_000

/** Refresh the access token if it expires within this many seconds. */
const REFRESH_THRESHOLD_SECONDS = 60

/** Maximum session age in days before forced logout. */
const MAX_SESSION_AGE_DAYS = 30
const MAX_SESSION_AGE_SECONDS = MAX_SESSION_AGE_DAYS * 24 * 60 * 60

let _intervalId: ReturnType<typeof setInterval> | null = null

/** Redirect helper — replaces the current location with /login. */
function redirectToLogin(): void {
  clearTokens()
  // HIGH-3: Clear workspace context so next user on this device doesn't inherit it
  try { localStorage.removeItem('innova_workspace_id') } catch { /* ignore */ }
  try { localStorage.removeItem('innova_session_start') } catch { /* ignore */ }
  window.location.replace('/login')
}

/**
 * Decode the JWT payload without verifying the signature.
 * Returns null if the token is missing or malformed.
 */
function decodePayload(token: string | null): Record<string, unknown> | null {
  if (!token) return null
  try {
    return JSON.parse(atob(token.split('.')[1])) as Record<string, unknown>
  } catch {
    return null
  }
}

/**
 * One tick of the refresh loop:
 * 1. Check session age — redirect if the session is older than 30 days.
 * 2. Check expiry — refresh if within 60 seconds of expiry.
 *
 * HIGH-6 fix: The 30-day limit now uses a persistent 'innova_session_start'
 * timestamp written to localStorage on first login (not the token iat, which
 * resets to "now" on every refresh and would never trigger).
 */
async function tick(): Promise<void> {
  const token = getAccessToken()
  const payload = decodePayload(token)

  if (!payload) return // Not authenticated — nothing to do

  const now = Math.floor(Date.now() / 1000)
  const exp = payload['exp'] as number | undefined

  // Enforce 30-day session age limit using persistent session start timestamp
  try {
    const sessionStart = localStorage.getItem('innova_session_start')
    if (sessionStart) {
      const startTime = parseInt(sessionStart, 10)
      if (!isNaN(startTime) && now - startTime > MAX_SESSION_AGE_SECONDS) {
        redirectToLogin()
        return
      }
    } else {
      // First time running: record the session start
      localStorage.setItem('innova_session_start', String(now))
    }
  } catch { /* ignore localStorage errors */ }

  // Refresh if within threshold of expiry
  if (exp !== undefined && exp - now <= REFRESH_THRESHOLD_SECONDS) {
    try {
      const { data, error } = await supabase.auth.refreshSession()
      if (error || !data.session) {
        redirectToLogin()
        return
      }
      setTokens(data.session.access_token, data.session.refresh_token)
    } catch {
      redirectToLogin()
    }
  }
}

/**
 * Start the proactive token refresh loop.
 * Safe to call multiple times — existing interval is cleared first.
 *
 * Records innova_session_start so the 30-day age check has a correct baseline.
 */
export function startRefreshLoop(): void {
  stopRefreshLoop()
  // Record session start time if not already set (preserves original login time across refreshes)
  try {
    if (!localStorage.getItem('innova_session_start')) {
      localStorage.setItem('innova_session_start', String(Math.floor(Date.now() / 1000)))
    }
  } catch { /* ignore */ }
  _intervalId = setInterval(() => { void tick() }, REFRESH_INTERVAL_MS)
}

/**
 * Stop the proactive token refresh loop (call on logout).
 */
export function stopRefreshLoop(): void {
  if (_intervalId !== null) {
    clearInterval(_intervalId)
    _intervalId = null
  }
}
