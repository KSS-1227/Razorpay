/**
 * In-memory token store — holds a fast, synchronous copy of the current
 * access and refresh tokens for use in API request headers.
 *
 * NOTE ON ACTUAL STORAGE (MED-1):
 * Supabase's `persistSession: true` (set in supabaseClient.ts) stores the
 * full session including the refresh token in localStorage under the key
 * `sb-<project-ref>-auth-token`. This is intentional — it enables session
 * persistence across page refreshes without requiring a re-login.
 *
 * tokenStore does NOT duplicate that localStorage storage. It simply caches
 * the access token in a module-level variable so that `apiFetch()` can attach
 * an Authorization header synchronously without awaiting `getSession()`.
 * On page refresh, AuthContext restores the token from Supabase's localStorage
 * entry via `onAuthStateChange(INITIAL_SESSION)`.
 */

/** Access token (JWT) for the current session, or null if not authenticated. */
let _accessToken: string | null = null

/** Refresh token for the current session, or null if not authenticated. */
let _refreshToken: string | null = null

/**
 * Store a new token pair after a successful login or token refresh.
 *
 * @param access  - The new access token (JWT).
 * @param refresh - The new refresh token.
 */
export function setTokens(access: string, refresh: string): void {
  _accessToken = access
  _refreshToken = refresh
}

/**
 * Retrieve the current access token.
 *
 * @returns The access token string, or null if not authenticated.
 */
export function getAccessToken(): string | null {
  return _accessToken
}

/**
 * Retrieve the current refresh token.
 *
 * @returns The refresh token string, or null if not authenticated.
 */
export function getRefreshToken(): string | null {
  return _refreshToken
}

/**
 * Clear both tokens — call this on logout or when a refresh fails.
 */
export function clearTokens(): void {
  _accessToken = null
  _refreshToken = null
}
