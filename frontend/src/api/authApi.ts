/**
 * Typed API client for all /api/auth/* and /api/workspaces/* endpoints.
 *
 * Design:
 * - A single internal `apiFetch` helper handles auth headers, 401 retry, and
 *   error message extraction. All public functions delegate to it.
 * - Protected functions accept `workspaceId: string | null` as a parameter.
 * - Token refresh is handled via Supabase directly (no circular dep on AuthContext).
 * - On terminal auth failure (still 401 after refresh): redirects to /login.
 *
 * Requirements: 10.3, 10.10, 12.3
 */
import { supabase } from '../auth/supabaseClient'
import { clearTokens, getAccessToken, setTokens } from '../auth/tokenStore'

// ---------------------------------------------------------------------------
// Request / Response types
// ---------------------------------------------------------------------------

// Register
export interface RegisterRequest { email: string; password: string }
export interface RegisterResponse { user_id: string; email: string; message: string }

// Login
export interface LoginRequest { email: string; password: string }
export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// Refresh
export interface RefreshRequest { refresh_token: string }
export interface RefreshResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// Password reset
export interface PasswordResetRequestBody { email: string }
export interface PasswordResetConfirmBody { token: string; new_password: string }

// Profile
export interface UserProfile {
  user_id: string
  email: string
  display_name: string
  avatar_url: string | null
  preferred_language: string
  preferred_date_format: 'YYYY-MM-DD' | 'DD/MM/YYYY' | 'MM/DD/YYYY'
  email_verified: boolean
  created_at: string
}
export interface ProfileUpdateRequest {
  display_name?: string
  avatar_url?: string | null
  preferred_language?: string
  preferred_date_format?: 'YYYY-MM-DD' | 'DD/MM/YYYY' | 'MM/DD/YYYY'
}

// Workspace
export interface WorkspaceResponse {
  workspace_id: string
  name: string
  created_at: string
  member_count: number
  role: string
}
export interface WorkspaceCreateRequest { name: string }
export interface MemberInviteRequest { email: string; role: 'Admin' | 'Analyst' | 'Viewer' }
export interface MemberRoleChangeRequest { role: 'Admin' | 'Analyst' | 'Viewer' }

// Audit log
export interface AuditLogEntry {
  event_type: string
  user_id: string | null
  workspace_id: string | null
  timestamp: string
  source_ip: string
  detail: string
}
export interface AuditLogPage {
  entries: AuditLogEntry[]
  next_cursor: string | null
}

// Generic message response
interface MessageResponse { message: string }

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/**
 * Extract a human-readable message from an error response body.
 * Prefers `.message`, falls back to `.error`, then a generic HTTP status string.
 * Never exposes stack traces or raw error objects.
 */
async function extractErrorMessage(resp: Response): Promise<string> {
  try {
    const body = (await resp.json()) as { message?: string; error?: string }
    return body.message ?? body.error ?? `HTTP ${resp.status}`
  } catch {
    return `HTTP ${resp.status}`
  }
}

/**
 * Attempt one silent token refresh via Supabase.
 * Returns true if successful and tokens have been updated.
 * On failure: clears tokens and redirects to /login.
 */
async function silentRefresh(): Promise<boolean> {
  try {
    const { data, error } = await supabase.auth.refreshSession()
    if (error || !data.session) {
      clearTokens()
      try { localStorage.removeItem('innova_workspace_id') } catch { /* ignore */ }
      window.location.href = '/login'
      return false
    }
    setTokens(data.session.access_token, data.session.refresh_token)
    return true
  } catch {
    clearTokens()
    try { localStorage.removeItem('innova_workspace_id') } catch { /* ignore */ }
    window.location.href = '/login'
    return false
  }
}

/**
 * Build request headers, attaching Bearer token and workspace ID if available.
 */
function buildHeaders(
  extra: HeadersInit | undefined,
  workspaceId: string | null | undefined,
): Record<string, string> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',   // bypass ngrok interstitial page
    ...(extra as Record<string, string> | undefined),
  }
  const token = getAccessToken()
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }
  if (workspaceId) {
    headers['X-Workspace-ID'] = workspaceId
  }
  return headers
}

/**
 * Core fetch wrapper used by all public API functions.
 *
 * - Attaches `Authorization` and `X-Workspace-ID` headers automatically.
 * - On 401: attempts one silent refresh, then retries once.
 * - If still 401 after retry: redirects to /login.
 * - On any other error: throws an Error with only `message` from the response.
 * - Handles 204 No Content by returning undefined.
 */
async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
  workspaceId?: string | null,
): Promise<T> {
  const { headers: initHeaders, ...restInit } = init

  const BASE = import.meta.env.VITE_API_BASE || ''
  const url = path.startsWith('http') ? path : `${BASE.replace(/\/$/, '')}${path.startsWith('/') ? path : '/' + path}`

  let resp = await fetch(url, {
    ...restInit,
    headers: buildHeaders(initHeaders, workspaceId),
  })

  // 401 → one silent refresh + retry
  if (resp.status === 401) {
    const refreshed = await silentRefresh()
    if (!refreshed) {
      // silentRefresh already redirected; throw to stop execution
      throw new Error('Session expired')
    }
    resp = await fetch(url, {
      ...restInit,
      headers: buildHeaders(initHeaders, workspaceId),
    })
    // If still 401 after refresh, redirect and abort
    if (resp.status === 401) {
      clearTokens()
      try { localStorage.removeItem('innova_workspace_id') } catch { /* ignore */ }
      window.location.href = '/login'
      throw new Error('Session expired')
    }
  }

  if (!resp.ok) {
    const message = await extractErrorMessage(resp)
    throw new Error(message)
  }

  // 204 No Content — return undefined cast to T
  if (resp.status === 204) return undefined as unknown as T

  return resp.json() as Promise<T>
}

// ---------------------------------------------------------------------------
// Auth endpoints
// ---------------------------------------------------------------------------

/** POST /api/auth/register — no auth required */
export async function apiRegister(
  body: RegisterRequest,
): Promise<RegisterResponse> {
  return apiFetch<RegisterResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** POST /api/auth/login — no auth required */
export async function apiLogin(body: LoginRequest): Promise<LoginResponse> {
  return apiFetch<LoginResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** POST /api/auth/logout — auth required */
export async function apiLogout(
  refreshToken: string,
  workspaceId: string | null,
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(
    '/api/auth/logout',
    { method: 'POST', body: JSON.stringify({ refresh_token: refreshToken }) },
    workspaceId,
  )
}

/** POST /api/auth/logout-all — auth required */
export async function apiLogoutAll(
  workspaceId: string | null,
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(
    '/api/auth/logout-all',
    { method: 'POST', body: JSON.stringify({}) },
    workspaceId,
  )
}

/** POST /api/auth/refresh — no auth required (refresh token in body) */
export async function apiRefresh(body: RefreshRequest): Promise<RefreshResponse> {
  return apiFetch<RefreshResponse>('/api/auth/refresh', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** POST /api/auth/password-reset/request — no auth required */
export async function apiRequestPasswordReset(
  body: PasswordResetRequestBody,
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>('/api/auth/password-reset/request', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** POST /api/auth/password-reset/confirm — no auth required */
export async function apiConfirmPasswordReset(
  body: PasswordResetConfirmBody,
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>('/api/auth/password-reset/confirm', {
    method: 'POST',
    body: JSON.stringify(body),
  })
}

/** POST /api/auth/verify-email/resend — no auth required */
export async function apiResendVerification(email: string): Promise<MessageResponse> {
  return apiFetch<MessageResponse>('/api/auth/verify-email/resend', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

// ---------------------------------------------------------------------------
// Profile endpoints
// ---------------------------------------------------------------------------

/** GET /api/auth/profile/{user_id} — auth required */
export async function apiGetProfile(
  userId: string,
  workspaceId: string | null,
): Promise<UserProfile> {
  return apiFetch<UserProfile>(
    `/api/auth/profile/${encodeURIComponent(userId)}`,
    { method: 'GET' },
    workspaceId,
  )
}

/** PATCH /api/auth/profile/{user_id} — auth required */
export async function apiUpdateProfile(
  userId: string,
  update: ProfileUpdateRequest,
  workspaceId: string | null,
): Promise<UserProfile> {
  return apiFetch<UserProfile>(
    `/api/auth/profile/${encodeURIComponent(userId)}`,
    { method: 'PATCH', body: JSON.stringify(update) },
    workspaceId,
  )
}

// ---------------------------------------------------------------------------
// Workspace endpoints
// ---------------------------------------------------------------------------

/** GET /api/workspaces — auth required */
export async function apiListWorkspaces(
  workspaceId: string | null,
): Promise<WorkspaceResponse[]> {
  return apiFetch<WorkspaceResponse[]>(
    '/api/workspaces',
    { method: 'GET' },
    workspaceId,
  )
}

/** POST /api/workspaces — auth required */
export async function apiCreateWorkspace(
  body: WorkspaceCreateRequest,
  workspaceId: string | null,
): Promise<WorkspaceResponse> {
  return apiFetch<WorkspaceResponse>(
    '/api/workspaces',
    { method: 'POST', body: JSON.stringify(body) },
    workspaceId,
  )
}

/** DELETE /api/workspaces/{workspace_id} — auth required (Admin) */
export async function apiDeleteWorkspace(
  targetWorkspaceId: string,
  activeWorkspaceId: string | null,
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(
    `/api/workspaces/${encodeURIComponent(targetWorkspaceId)}`,
    { method: 'DELETE' },
    activeWorkspaceId,
  )
}

/** POST /api/workspaces/{workspace_id}/members — auth required (Admin) */
export async function apiInviteMember(
  wsId: string,
  body: MemberInviteRequest,
  activeWorkspaceId: string | null,
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(
    `/api/workspaces/${encodeURIComponent(wsId)}/members`,
    { method: 'POST', body: JSON.stringify(body) },
    activeWorkspaceId,
  )
}

/** DELETE /api/workspaces/{workspace_id}/members/{user_id} — auth required (Admin) */
export async function apiRemoveMember(
  wsId: string,
  userId: string,
  activeWorkspaceId: string | null,
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(
    `/api/workspaces/${encodeURIComponent(wsId)}/members/${encodeURIComponent(userId)}`,
    { method: 'DELETE' },
    activeWorkspaceId,
  )
}

/** PATCH /api/workspaces/{workspace_id}/members/{user_id}/role — auth required (Admin) */
export async function apiChangeMemberRole(
  wsId: string,
  userId: string,
  body: MemberRoleChangeRequest,
  activeWorkspaceId: string | null,
): Promise<MessageResponse> {
  return apiFetch<MessageResponse>(
    `/api/workspaces/${encodeURIComponent(wsId)}/members/${encodeURIComponent(userId)}/role`,
    { method: 'PATCH', body: JSON.stringify(body) },
    activeWorkspaceId,
  )
}

// ---------------------------------------------------------------------------
// Audit log endpoint
// ---------------------------------------------------------------------------

/** GET /api/workspaces/{workspace_id}/audit-log — auth required (Admin) */
export async function apiGetAuditLog(
  wsId: string,
  activeWorkspaceId: string | null,
  cursor?: string | null,
  limit?: number,
): Promise<AuditLogPage> {
  const params = new URLSearchParams()
  if (cursor) params.set('cursor', cursor)
  if (limit !== undefined) params.set('limit', String(limit))
  const qs = params.size > 0 ? `?${params.toString()}` : ''
  return apiFetch<AuditLogPage>(
    `/api/workspaces/${encodeURIComponent(wsId)}/audit-log${qs}`,
    { method: 'GET' },
    activeWorkspaceId,
  )
}
