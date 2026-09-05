/**
 * Profile Page — view and edit the authenticated user's profile.
 *
 * GET  /api/auth/profile/{user_id}
 * PATCH /api/auth/profile/{user_id}
 */
import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { UserCircle, Save, Loader2, CheckCircle2 } from 'lucide-react'
import { getAccessToken } from '../../auth/tokenStore'
import { useAuth } from '../../auth/AuthContext'
import { fetchApi } from '../../api/fetchWithNgrok'

// ─── Types ───────────────────────────────────────────────
interface UserProfile {
  user_id: string
  email: string
  display_name: string
  avatar_url: string | null
  preferred_language: string
  preferred_date_format: 'YYYY-MM-DD' | 'DD/MM/YYYY' | 'MM/DD/YYYY'
  email_verified: boolean
  created_at: string
}

// ─── Helpers ─────────────────────────────────────────────
function authHeaders(workspaceId?: string | null): Record<string, string> {
  const token = getAccessToken()
  const h: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) h['Authorization'] = `Bearer ${token}`
  if (workspaceId) h['X-Workspace-ID'] = workspaceId
  return h
}

const DATE_FORMATS = ['YYYY-MM-DD', 'DD/MM/YYYY', 'MM/DD/YYYY'] as const
const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'es', label: 'Spanish' },
  { value: 'ar', label: 'Arabic' },
]

// ─────────────────────────────────────────────────────────
export default function ProfilePage() {
  const { user, workspaceId } = useAuth()

  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form state
  const [displayName, setDisplayName] = useState('')
  const [language, setLanguage] = useState('en')
  const [dateFormat, setDateFormat] = useState<'YYYY-MM-DD' | 'DD/MM/YYYY' | 'MM/DD/YYYY'>('YYYY-MM-DD')

  // ── Load profile ──────────────────────────────────────
  useEffect(() => {
    if (!user?.id) return
    void (async () => {
      try {
        const resp = await fetchApi(`/api/auth/profile/${encodeURIComponent(user.id)}`, {
          headers: authHeaders(workspaceId),
        })
        if (!resp.ok) throw new Error(`Error ${resp.status}`)
        const data: UserProfile = await resp.json()
        setProfile(data)
        setDisplayName(data.display_name ?? '')
        setLanguage(data.preferred_language ?? 'en')
        setDateFormat(data.preferred_date_format ?? 'YYYY-MM-DD')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load profile')
      } finally {
        setLoading(false)
      }
    })()
  }, [user?.id, workspaceId])

  // ── Save profile ──────────────────────────────────────
  async function handleSave() {
    if (!user?.id) return
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const resp = await fetchApi(`/api/auth/profile/${encodeURIComponent(user.id)}`, {
        method: 'PATCH',
        headers: authHeaders(workspaceId),
        body: JSON.stringify({
          display_name: displayName.trim() || undefined,
          preferred_language: language,
          preferred_date_format: dateFormat,
        }),
      })
      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}))
        throw new Error(body?.detail?.message ?? body?.message ?? `Error ${resp.status}`)
      }
      const updated: UserProfile = await resp.json()
      setProfile(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile')
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-slate-400" size={32} />
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-2xl mx-auto space-y-6 text-white">

      {/* ── Header ── */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center gap-2 mb-1">
          <UserCircle className="w-5 h-5 text-violet-400" />
          <h1 className="text-2xl font-extrabold tracking-tight">Profile</h1>
        </div>
        <p className="text-sm text-slate-400">Manage your personal information and preferences.</p>
      </motion.div>

      {/* ── Avatar + email (read-only) ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}
        className="flex items-center gap-5 p-5 rounded-2xl border border-zinc-800 bg-zinc-900/60"
      >
        <div className="w-16 h-16 rounded-full bg-gradient-to-tr from-violet-500 to-indigo-500 flex items-center justify-center text-2xl font-bold text-white shrink-0">
          {(profile?.display_name ?? profile?.email ?? 'U')[0].toUpperCase()}
        </div>
        <div>
          <p className="text-base font-semibold text-white">{profile?.display_name || 'No name set'}</p>
          <p className="text-sm text-slate-400">{profile?.email}</p>
          <div className="flex items-center gap-2 mt-1.5">
            {profile?.email_verified ? (
              <span className="flex items-center gap-1 text-xs text-emerald-400">
                <CheckCircle2 size={11} /> Email verified
              </span>
            ) : (
              <span className="text-xs text-amber-400">Email not verified</span>
            )}
          </div>
        </div>
      </motion.div>

      {/* ── Edit form ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-6 space-y-5"
      >
        <h2 className="text-sm font-semibold text-slate-300">Edit Profile</h2>

        {/* Display name */}
        <div>
          <label className="block text-xs text-slate-400 mb-1.5">Display Name</label>
          <input
            value={displayName}
            onChange={e => setDisplayName(e.target.value)}
            maxLength={100}
            placeholder="Your name"
            className="w-full rounded-xl bg-zinc-950 border border-zinc-700 px-3 py-2.5 text-sm text-white outline-none focus:border-violet-500"
          />
        </div>

        {/* Language */}
        <div>
          <label className="block text-xs text-slate-400 mb-1.5">Preferred Language</label>
          <select
            value={language}
            onChange={e => setLanguage(e.target.value)}
            className="w-full rounded-xl bg-zinc-950 border border-zinc-700 px-3 py-2.5 text-sm text-white outline-none focus:border-violet-500"
          >
            {LANGUAGES.map(l => (
              <option key={l.value} value={l.value}>{l.label}</option>
            ))}
          </select>
        </div>

        {/* Date format */}
        <div>
          <label className="block text-xs text-slate-400 mb-1.5">Date Format</label>
          <div className="flex gap-3">
            {DATE_FORMATS.map(fmt => (
              <button
                key={fmt}
                type="button"
                onClick={() => setDateFormat(fmt)}
                className={`flex-1 py-2 rounded-xl text-xs font-medium border transition-all ${
                  dateFormat === fmt
                    ? 'bg-violet-500/20 border-violet-500/40 text-violet-300'
                    : 'border-zinc-700 text-slate-400 hover:border-zinc-500'
                }`}
              >
                {fmt}
              </button>
            ))}
          </div>
        </div>

        {/* Error / save feedback */}
        {error && <p className="text-xs text-red-400">{error}</p>}
        {saved && (
          <p className="text-xs text-emerald-400 flex items-center gap-1">
            <CheckCircle2 size={12} /> Profile saved successfully
          </p>
        )}

        {/* Save button */}
        <button
          type="button"
          onClick={handleSave}
          disabled={saving}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-gradient-to-r from-violet-500 to-indigo-600 text-white text-sm font-semibold disabled:opacity-50 transition-all hover:from-violet-600 hover:to-indigo-700"
        >
          {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
          Save Changes
        </button>
      </motion.div>

      {/* ── Account info (read-only) ── */}
      {profile && (
        <motion.div
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}
          className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5 space-y-3"
        >
          <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Account Info</h2>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div>
              <p className="text-slate-500">User ID</p>
              <p className="font-mono text-slate-300 mt-0.5 truncate">{profile.user_id}</p>
            </div>
            <div>
              <p className="text-slate-500">Member since</p>
              <p className="text-slate-300 mt-0.5">{new Date(profile.created_at).toLocaleDateString()}</p>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
