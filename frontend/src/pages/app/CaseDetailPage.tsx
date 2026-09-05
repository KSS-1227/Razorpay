/**
 * Case Detail Page — view a single case with actions.
 *
 * Shows case metadata, and quick links to Upload, Knowledge Graph,
 * AI Assistant, and Reports for this specific case.
 *
 * Uses:
 *   GET   /api/cases/{case_id}    — fetch case details
 *   PATCH /api/cases/{case_id}    — update title/description
 *   DELETE /api/cases/{case_id}   — delete case
 */
import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  FolderKanban,
  ArrowLeft,
  Pencil,
  Trash2,
  UploadCloud,
  Network,
  BrainCircuit,
  FileText,
  Loader2,
  CheckCircle2,
  Save,
  X,
} from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { fetchApi } from '../../api/fetchWithNgrok'

// ─── Types ───────────────────────────────────────────────
interface Case {
  id: string
  title: string
  description: string
  created_at: string
  updated_at: string
}

// ─── Helpers ─────────────────────────────────────────────
const API_BASE = ((import.meta.env.VITE_API_BASE as string) || '').replace(/\/$/, '')

function extraHeaders(workspaceId?: string | null): Record<string, string> {
  const h: Record<string, string> = { 'Content-Type': 'application/json' }
  if (workspaceId) h['X-Workspace-ID'] = workspaceId
  return h
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

// ─────────────────────────────────────────────────────────
export default function CaseDetailPage() {
  const { id: caseId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { workspaceId, isLoading: authLoading } = useAuth()

  const [caseData, setCaseData] = useState<Case | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Edit mode
  const [editing, setEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  // Delete
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // ── Load case ─────────────────────────────────────────
  useEffect(() => {
    if (!caseId || authLoading) return
    void (async () => {
      try {
        const resp = await fetchApi(`${API_BASE}/api/cases/${encodeURIComponent(caseId)}`, {
          headers: extraHeaders(workspaceId),
        })
        if (!resp.ok) throw new Error(`Case not found (${resp.status})`)
        const data: Case = await resp.json()
        setCaseData(data)
        setEditTitle(data.title)
        setEditDesc(data.description ?? '')
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load case')
      } finally {
        setLoading(false)
      }
    })()
  }, [caseId, workspaceId, authLoading])

  // ── Save edits ────────────────────────────────────────
  async function handleSave() {
    if (!caseId) return
    setSaving(true)
    try {
      const resp = await fetchApi(`${API_BASE}/api/cases/${encodeURIComponent(caseId)}`, {
        method: 'PATCH',
        headers: extraHeaders(workspaceId),
        body: JSON.stringify({
          title: editTitle.trim() || undefined,
          description: editDesc,
        }),
      })
      if (!resp.ok) throw new Error(`Error ${resp.status}`)
      const updated: Case = await resp.json()
      setCaseData(updated)
      setEditing(false)
      setSaved(true)
      setTimeout(() => setSaved(false), 2500)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  // ── Delete case ───────────────────────────────────────
  async function handleDelete() {
    if (!caseId) return
    setDeleting(true)
    try {
      const resp = await fetchApi(`${API_BASE}/api/cases/${encodeURIComponent(caseId)}`, {
        method: 'DELETE',
        headers: extraHeaders(workspaceId),
      })
      if (!resp.ok) throw new Error(`Error ${resp.status}`)
      localStorage.removeItem('innova_active_case_id')
      navigate('/app/cases')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
      setDeleting(false)
    }
  }

  // ── Navigate to action and set case_id ───────────────
  function goTo(path: string) {
    if (caseId) {
      try { localStorage.setItem('innova_active_case_id', caseId) } catch { /* ignore */ }
    }
    navigate(path)
  }

  // ─── Render ────────────────────────────────────────────
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="animate-spin text-slate-400" size={32} />
      </div>
    )
  }

  if (error || !caseData) {
    return (
      <div className="p-8 text-center space-y-4">
        <p className="text-red-400 text-sm">{error ?? 'Case not found'}</p>
        <button
          type="button"
          onClick={() => navigate('/app/cases')}
          className="text-xs text-indigo-400 hover:text-indigo-300"
        >
          ← Back to Cases
        </button>
      </div>
    )
  }

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-3xl mx-auto space-y-6 text-white">

      {/* ── Back + Header ── */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <button
          type="button"
          onClick={() => navigate('/app/cases')}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 mb-4 transition-colors"
        >
          <ArrowLeft size={13} /> Back to Cases
        </button>

        <div className="flex items-start justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shrink-0">
              <FolderKanban size={18} className="text-indigo-400" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold tracking-tight">{caseData.title}</h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Created {timeAgo(caseData.created_at)} · Updated {timeAgo(caseData.updated_at)}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {saved && (
              <span className="text-xs text-emerald-400 flex items-center gap-1">
                <CheckCircle2 size={12} /> Saved
              </span>
            )}
            <button
              type="button"
              onClick={() => { setEditing(true); setEditTitle(caseData.title); setEditDesc(caseData.description ?? '') }}
              className="p-2 rounded-lg border border-zinc-700 text-slate-400 hover:text-white hover:border-indigo-500 transition-all"
              title="Edit case"
            >
              <Pencil size={14} />
            </button>
            <button
              type="button"
              onClick={() => setDeleteConfirm(true)}
              className="p-2 rounded-lg border border-zinc-700 text-slate-400 hover:text-red-400 hover:border-red-500/40 transition-all"
              title="Delete case"
            >
              <Trash2 size={14} />
            </button>
          </div>
        </div>
      </motion.div>

      {/* ── Edit form ── */}
      {editing && (
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-5 space-y-4"
        >
          <h2 className="text-sm font-semibold text-slate-300">Edit Case</h2>
          <input
            value={editTitle}
            onChange={e => setEditTitle(e.target.value)}
            placeholder="Case title"
            maxLength={200}
            className="w-full rounded-xl bg-zinc-950 border border-zinc-700 px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-500"
          />
          <textarea
            value={editDesc}
            onChange={e => setEditDesc(e.target.value)}
            placeholder="Description (optional)"
            rows={3}
            className="w-full rounded-xl bg-zinc-950 border border-zinc-700 px-3 py-2.5 text-sm text-white outline-none focus:border-indigo-500 resize-none"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !editTitle.trim()}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-500 hover:bg-indigo-600 text-white text-sm font-semibold disabled:opacity-50 transition-all"
            >
              {saving ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
              Save
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="flex items-center gap-2 px-4 py-2 rounded-xl border border-zinc-700 text-slate-400 hover:text-white text-sm transition-all"
            >
              <X size={14} /> Cancel
            </button>
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </motion.div>
      )}

      {/* ── Description ── */}
      {!editing && caseData.description && (
        <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4">
          <p className="text-sm text-slate-300 leading-6">{caseData.description}</p>
        </div>
      )}

      {/* ── Case ID ── */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-4 flex items-center justify-between">
        <div>
          <p className="text-xs text-slate-500 mb-0.5">Case ID</p>
          <p className="font-mono text-sm text-slate-300">{caseData.id}</p>
        </div>
        <button
          type="button"
          onClick={() => {
            navigator.clipboard.writeText(caseData.id)
            try { localStorage.setItem('innova_active_case_id', caseData.id) } catch { /* ignore */ }
          }}
          className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
        >
          Copy & set active
        </button>
      </div>

      {/* ── Quick actions ── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}
        className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-4"
      >
        <h2 className="text-sm font-semibold text-slate-300">Actions for this Case</h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'Upload Docs', icon: UploadCloud, color: 'text-cyan-400', path: '/app/upload', desc: 'Add documents' },
            { label: 'View Graph', icon: Network, color: 'text-purple-400', path: '/app/knowledge-graph', desc: 'Explore entities' },
            { label: 'Ask AI', icon: BrainCircuit, color: 'text-indigo-400', path: '/app/ai-assistant', desc: 'Query this case' },
            { label: 'Reports', icon: FileText, color: 'text-rose-400', path: '/app/reports', desc: 'Generate report' },
          ].map(({ label, icon: Icon, color, path, desc }) => (
            <button
              key={label}
              type="button"
              onClick={() => goTo(path)}
              className="flex flex-col items-center gap-2 p-4 rounded-xl bg-zinc-900/50 hover:bg-zinc-800/60 border border-white/5 hover:border-white/15 transition-all cursor-pointer group text-center"
            >
              <Icon className={`w-6 h-6 ${color} group-hover:scale-110 transition-transform`} />
              <span className="text-xs font-semibold text-slate-300">{label}</span>
              <span className="text-[10px] text-slate-500">{desc}</span>
            </button>
          ))}
        </div>
        <p className="text-[11px] text-slate-600">
          Clicking any action will set this case as active so the AI Assistant and Knowledge Graph load it automatically.
        </p>
      </motion.div>

      {/* ── Delete confirmation ── */}
      {deleteConfirm && (
        <motion.div
          initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
          className="rounded-2xl border border-red-500/20 bg-red-500/5 p-5 space-y-3"
        >
          <p className="text-sm text-red-300 font-semibold">Delete this case?</p>
          <p className="text-xs text-slate-400">
            This will permanently delete the case and all associated data (uploads, graphs, reports). This cannot be undone.
          </p>
          <div className="flex gap-3">
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-red-500 hover:bg-red-600 text-white text-sm font-semibold disabled:opacity-50"
            >
              {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
              Delete
            </button>
            <button
              type="button"
              onClick={() => setDeleteConfirm(false)}
              className="px-4 py-2 rounded-xl border border-zinc-700 text-slate-400 hover:text-white text-sm transition-all"
            >
              Cancel
            </button>
          </div>
          {error && <p className="text-xs text-red-400">{error}</p>}
        </motion.div>
      )}
    </div>
  )
}
