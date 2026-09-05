/**
 * Settings Page — workspace settings, member management, danger zone.
 *
 * Uses:
 *   GET    /api/workspaces                         — list workspaces
 *   POST   /api/workspaces/{id}/members            — invite member
 *   DELETE /api/workspaces/{id}/members/{uid}      — remove member
 *   PATCH  /api/workspaces/{id}/members/{uid}/role — change role
 *   DELETE /api/workspaces/{id}                    — delete workspace
 */
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Settings,
  Users,
  UserPlus,
  Trash2,
  Loader2,
  CheckCircle2,
  ShieldAlert,
} from 'lucide-react'
import { getAccessToken } from '../../auth/tokenStore'
import { useAuth } from '../../auth/AuthContext'
import { fetchApi } from '../../api/fetchWithNgrok'

// ─── Types ───────────────────────────────────────────────
type Role = 'Admin' | 'Analyst' | 'Viewer'

// ─── Helpers ─────────────────────────────────────────────
function authHeaders(workspaceId?: string | null): Record<string, string> {
  const token = getAccessToken()
  const h: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) h['Authorization'] = `Bearer ${token}`
  if (workspaceId) h['X-Workspace-ID'] = workspaceId
  return h
}

const ROLE_COLORS: Record<Role, string> = {
  Admin: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  Analyst: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
  Viewer: 'bg-slate-500/10 text-slate-400 border-slate-500/20',
}

// ─────────────────────────────────────────────────────────
export default function SettingsPage() {
  const { workspaceId, user } = useAuth()

  const [wsName, setWsName] = useState<string>('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<Role>('Viewer')
  const [inviting, setInviting] = useState(false)
  const [inviteSuccess, setInviteSuccess] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // ── Load workspace info ───────────────────────────────
  useEffect(() => {
    if (!workspaceId) return
    void (async () => {
      try {
        const resp = await fetchApi('/api/workspaces', { headers: authHeaders(workspaceId) })
        if (!resp.ok) return
        const data = await resp.json()
        const ws = (Array.isArray(data) ? data : []).find((w: any) => w.workspace_id === workspaceId)
        if (ws) setWsName(ws.name ?? '')
      } catch { /* silent */ }
    })()
  }, [workspaceId])

  // ── Load members via audit/workspace endpoint ──────────
  // Note: there's no direct "list members" endpoint, so we show what we know.
  // In a full implementation this would call GET /api/workspaces/{id}/members

  // ── Invite member ────────────────────────────────────
  async function handleInvite() {
    if (!workspaceId || !inviteEmail.trim()) return
    setInviting(true)
    setError(null)
    setInviteSuccess(false)
    try {
      const resp = await fetchApi(`/api/workspaces/${encodeURIComponent(workspaceId)}/members`, {
        method: 'POST',
        headers: authHeaders(workspaceId),
        body: JSON.stringify({ email: inviteEmail.trim(), role: inviteRole }),
      })
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}))
        throw new Error(body?.detail?.message ?? body?.message ?? `Error ${resp.status}`)
      }
      setInviteEmail('')
      setInviteSuccess(true)
      setTimeout(() => setInviteSuccess(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Invite failed')
    } finally {
      setInviting(false)
    }
  }

  // ── Delete workspace ─────────────────────────────────
  async function handleDelete() {
    if (!workspaceId) return
    setDeleting(true)
    setError(null)
    try {
      const resp = await fetchApi(`/api/workspaces/${encodeURIComponent(workspaceId)}`, {
        method: 'DELETE',
        headers: authHeaders(workspaceId),
      })
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}))
        throw new Error(body?.detail?.message ?? `Error ${resp.status}`)
      }
      // Redirect to workspace picker after deletion
      window.location.href = '/workspaces'
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
      setDeleting(false)
    }
  }

  if (!workspaceId) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        No workspace selected.
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-2xl mx-auto space-y-6 text-white">

      {/* ── Header ── */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 mb-1">
          <Settings className="w-5 h-5 text-slate-400" />
          <h1 className="text-2xl font-extrabold tracking-tight">Settings</h1>
        </div>
        <p className="text-sm text-slate-400">Manage workspace configuration and members.</p>
      </motion.div>

      {/* ── Workspace info ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
        className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-3"
      >
        <h2 className="text-sm font-semibold text-slate-300">Workspace</h2>
        <div className="grid grid-cols-2 gap-3 text-xs">
          <div>
            <p className="text-slate-500">Name</p>
            <p className="text-slate-200 mt-0.5 font-medium">{wsName || '—'}</p>
          </div>
          <div>
            <p className="text-slate-500">Workspace ID</p>
            <p className="font-mono text-slate-400 mt-0.5 truncate">{workspaceId}</p>
          </div>
          <div>
            <p className="text-slate-500">Your role</p>
            <p className="text-slate-200 mt-0.5">{user?.role ?? '—'}</p>
          </div>
        </div>
      </motion.div>

      {/* ── Invite member ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-4"
      >
        <div className="flex items-center gap-2">
          <Users size={15} className="text-cyan-400" />
          <h2 className="text-sm font-semibold text-slate-300">Invite Member</h2>
        </div>

        <div className="flex gap-2">
          <input
            value={inviteEmail}
            onChange={e => setInviteEmail(e.target.value)}
            placeholder="colleague@company.com"
            type="email"
            className="flex-1 rounded-xl bg-zinc-950 border border-zinc-700 px-3 py-2.5 text-sm text-white outline-none focus:border-cyan-500"
          />
          <select
            value={inviteRole}
            onChange={e => setInviteRole(e.target.value as Role)}
            className="rounded-xl bg-zinc-950 border border-zinc-700 px-3 py-2.5 text-sm text-white outline-none focus:border-cyan-500"
          >
            <option value="Viewer">Viewer</option>
            <option value="Analyst">Analyst</option>
            <option value="Admin">Admin</option>
          </select>
          <button
            type="button"
            onClick={handleInvite}
            disabled={inviting || !inviteEmail.trim()}
            className="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-600 text-white text-sm font-semibold disabled:opacity-50 transition-all shrink-0"
          >
            {inviting ? <Loader2 size={14} className="animate-spin" /> : <UserPlus size={14} />}
            Invite
          </button>
        </div>

        {inviteSuccess && (
          <p className="text-xs text-emerald-400 flex items-center gap-1">
            <CheckCircle2 size={12} /> Invitation sent successfully
          </p>
        )}
        {error && <p className="text-xs text-red-400">{error}</p>}

        <div className="rounded-xl border border-zinc-800 bg-zinc-950/40 p-3">
          <p className="text-xs text-slate-500 mb-2 font-semibold uppercase tracking-wide">Role permissions</p>
          <div className="space-y-1.5 text-xs text-slate-400">
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded-full border text-[10px] font-semibold ${ROLE_COLORS['Admin']}`}>Admin</span>
              Full access — manage members, delete workspace, all operations
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded-full border text-[10px] font-semibold ${ROLE_COLORS['Analyst']}`}>Analyst</span>
              Upload, query, generate reports
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-0.5 rounded-full border text-[10px] font-semibold ${ROLE_COLORS['Viewer']}`}>Viewer</span>
              Read-only access to reports and graphs
            </div>
          </div>
        </div>
      </motion.div>

      {/* ── Danger Zone ── */}
      {user?.role === 'Admin' && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="rounded-2xl border border-red-500/20 bg-red-500/5 p-5 space-y-4"
        >
          <div className="flex items-center gap-2">
            <ShieldAlert size={15} className="text-red-400" />
            <h2 className="text-sm font-semibold text-red-300">Danger Zone</h2>
          </div>

          <p className="text-xs text-slate-400">
            Deleting this workspace is permanent and irreversible. All cases, documents, and graphs will be removed.
          </p>

          {!deleteConfirm ? (
            <button
              type="button"
              onClick={() => setDeleteConfirm(true)}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-red-500/30 text-red-400 hover:bg-red-500/10 text-sm font-medium transition-all"
            >
              <Trash2 size={14} /> Delete Workspace
            </button>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-red-300 font-semibold">Are you sure? This cannot be undone.</p>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={handleDelete}
                  disabled={deleting}
                  className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-red-500 hover:bg-red-600 text-white text-sm font-semibold disabled:opacity-50 transition-all"
                >
                  {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
                  Yes, delete workspace
                </button>
                <button
                  type="button"
                  onClick={() => setDeleteConfirm(false)}
                  className="px-4 py-2.5 rounded-xl border border-zinc-700 text-slate-400 hover:text-white text-sm transition-all"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </motion.div>
      )}
    </div>
  )
}
