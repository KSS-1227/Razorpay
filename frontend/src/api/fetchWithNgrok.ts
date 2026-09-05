/**
 * Thin wrapper around fetch() that:
 * 1. Automatically prepends VITE_API_BASE to relative /api/* paths
 * 2. Adds the `ngrok-skip-browser-warning` header so the ngrok
 *    interstitial page is bypassed in production
 * 3. Automatically attaches the Supabase Bearer token from tokenStore
 *    (callers may still pass their own Authorization header to override)
 *
 * Safe to use in all environments — headers are harmless when not behind ngrok.
 */
import { getAccessToken } from '../auth/tokenStore'

const API_BASE = ((import.meta.env.VITE_API_BASE as string) || '').replace(/\/$/, '')

export function fetchApi(url: string, init: RequestInit = {}): Promise<Response> {
  // Prepend API_BASE for relative paths (e.g. /api/workspaces)
  const fullUrl = url.startsWith('/') ? `${API_BASE}${url}` : url

  const headers = new Headers(init.headers)
  headers.set('ngrok-skip-browser-warning', 'true')

  // Attach Bearer token unless the caller already set one
  if (!headers.has('Authorization')) {
    const token = getAccessToken()
    if (token) {
      headers.set('Authorization', `Bearer ${token}`)
    }
  }

  return fetch(fullUrl, { ...init, headers })
}
