/**
 * Workspace selection page — shown after login.
 *
 * Fixes applied:
 *  - HIGH-1: Removed silent fallback to fake DEMO_WORKSPACES. Now shows real
 *            error state when the API fails, preventing fake IDs being sent to backend.
 *  - HIGH-5: Workspace creation now calls the backend API. Workspace is only
 *            added to UI state if the API call succeeds.
 *  - MED-4:  Replaced native browser prompt() with a styled inline form.
 *  - MED-5:  DEMO_WORKSPACES removed entirely — no longer defined inside component.
 */
import { type FormEvent, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Database,
  FolderOpen,
  LogOut,
  Plus,
  Sparkles,
  ChevronRight,
  Shield,
  X,
  RefreshCw,
} from 'lucide-react'
import { useAuth } from '../auth/AuthContext'
import { getAccessToken, setTokens } from '../auth/tokenStore'
import { supabase } from '../auth/supabaseClient'
import { FloatingParticles } from '../components/ui/FloatingParticles'
import { Alert } from '../components/ui/Alert'
import { fetchApi } from '../api/fetchWithNgrok'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import { Skeleton } from '../components/ui/Skeleton'
import { Input } from '../components/ui/Input'

const API_BASE = ((import.meta.env.VITE_API_BASE as string) || '').replace(/\/$/, '')

interface Workspace {
  workspace_id: string
  name: string
  owner_id: string
}

function WorkspaceSkeleton() {
  return (
    <div className="flex flex-col gap-3">
      {[1, 2, 3].map((i) => (
        <div key={i} className="flex items-center gap-4 p-4 rounded-2xl border border-white/5 bg-slate-900/40">
          <Skeleton className="w-10 h-10 rounded-xl shrink-0" />
          <div className="flex-1 flex flex-col gap-2">
            <Skeleton className="h-4 w-36" />
            <Skeleton className="h-3 w-20" />
          </div>
          <Skeleton className="w-6 h-6 rounded-lg" />
        </div>
      ))}
    </div>
  )
}

export default function WorkspaceSelectPage() {
  const { selectWorkspace, logout, user, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selecting, setSelecting] = useState<string | null>(null)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  // MED-4: Inline create form state (replaces browser prompt())
  const [showCreateForm, setShowCreateForm] = useState(false)
  const [newWorkspaceName, setNewWorkspaceName] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)
  const createInputRef = useRef<HTMLInputElement>(null)

  // ── Fetch workspaces ───────────────────────────────────────────────────

  async function fetchWorkspaces() {
    setIsLoading(true)
    setError(null)
    try {
      let token = getAccessToken()

      // If no token in memory, try to restore from Supabase session
      if (!token) {
        const { data } = await supabase.auth.getSession()
        if (data.session) {
          setTokens(data.session.access_token, data.session.refresh_token)
          token = data.session.access_token
        }
      }

      const resp = await fetchApi(`${API_BASE}/api/workspaces`, {
        headers: { Authorization: `Bearer ${token ?? ''}` },
      })

      // If 401, try to refresh the token once then retry
      if (resp.status === 401) {
        const { data, error } = await supabase.auth.refreshSession()
        if (error || !data.session) {
          // Refresh failed — session is truly expired, redirect to login
          void logout()
          return
        }
        setTokens(data.session.access_token, data.session.refresh_token)
        // Retry with fresh token
        const retryResp = await fetchApi(`${API_BASE}/api/workspaces`, {
          headers: { Authorization: `Bearer ${data.session.access_token}` },
        })
        if (!retryResp.ok) {
          setError(`Failed to load workspaces (${retryResp.status}). Please try again.`)
          return
        }
        const retryText = await retryResp.text()
        try {
          const retryData = retryText ? JSON.parse(retryText) : []
          setWorkspaces(Array.isArray(retryData) ? retryData as Workspace[] : [])
        } catch { setWorkspaces([]) }
        return
      }

      const text = await resp.text()
      if (!resp.ok) {
        setError(`Failed to load workspaces (${resp.status}). Please try again.`)
        return
      }
      let data: unknown = null
      if (text) {
        try { data = JSON.parse(text) } catch { data = null }
      }

      if (Array.isArray(data)) {
        setWorkspaces(data as Workspace[])
      } else {
        setWorkspaces([])
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Network error'
      setError(`Could not reach the server: ${msg}. Check your connection and try again.`)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    // Wait until auth context has restored the session before fetching.
    // Without this, getAccessToken() returns null and the request gets a 401.
    if (!authLoading) {
      void fetchWorkspaces()
    }
  }, [authLoading]) // eslint-disable-line react-hooks/exhaustive-deps

  // ── Select workspace ───────────────────────────────────────────────────

  async function handleSelect(workspaceId: string) {
    setSelecting(workspaceId)
    selectWorkspace(workspaceId)
    await new Promise((r) => setTimeout(r, 300)) // brief selection feedback
    void navigate('/app')
  }

  // ── Create workspace (HIGH-5: API call, not local state only) ──────────

  async function handleCreateWorkspace(e: FormEvent) {
    e.preventDefault()
    const name = newWorkspaceName.trim()
    if (!name) return

    setIsCreating(true)
    setCreateError(null)
    try {
      // Get freshest token — refresh if needed
      let token = getAccessToken()
      if (!token) {
        const { data } = await supabase.auth.getSession()
        if (data.session) {
          setTokens(data.session.access_token, data.session.refresh_token)
          token = data.session.access_token
        }
      }

      const doCreate = async (t: string) => fetchApi(`${API_BASE}/api/workspaces`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${t}` },
        body: JSON.stringify({ name }),
      })

      let resp = await doCreate(token ?? '')

      // Auto-refresh on 401 and retry once
      if (resp.status === 401) {
        const { data, error } = await supabase.auth.refreshSession()
        if (error || !data.session) { void logout(); return }
        setTokens(data.session.access_token, data.session.refresh_token)
        resp = await doCreate(data.session.access_token)
      }

      if (!resp.ok) {
        const msg = resp.status === 400
          ? 'Invalid workspace name.'
          : `Failed to create workspace (${resp.status}). Please try again.`
        setCreateError(msg)
        return
      }

      const created = await resp.json() as Workspace
      setWorkspaces((prev) => [created, ...prev])
      setShowCreateForm(false)
      setNewWorkspaceName('')
      void handleSelect(created.workspace_id)
    } catch (err: unknown) {
      setCreateError(err instanceof Error ? err.message : 'Network error. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  function openCreateForm() {
    setShowCreateForm(true)
    setCreateError(null)
    setNewWorkspaceName('')
    // Focus the input after animation
    setTimeout(() => { createInputRef.current?.focus() }, 80)
  }

  function closeCreateForm() {
    setShowCreateForm(false)
    setCreateError(null)
    setNewWorkspaceName('')
  }

  // ── Logout ─────────────────────────────────────────────────────────────

  async function handleLogout() {
    setIsLoggingOut(true)
    try {
      await logout()
    } catch (err) {
      console.error('Logout error:', err)
    }
    navigate('/login')
  }

  // ── Animation variants ─────────────────────────────────────────────────

  const containerVariants = {
    hidden: {},
    visible: { transition: { staggerChildren: 0.07, delayChildren: 0.1 } },
  }

  const itemVariants = {
    hidden: { opacity: 0, x: -16 },
    visible: { opacity: 1, x: 0, transition: { ease: 'easeOut' as const, duration: 0.35 } },
  }

  return (
    <div className="min-h-screen w-full bg-[#090a0f] text-slate-100 flex flex-col relative overflow-hidden">
      <FloatingParticles />

      {/* ── Top nav bar ── */}
      <header className="relative z-10 flex items-center justify-between px-5 sm:px-8 py-4 border-b border-white/[0.06] backdrop-blur-xl bg-slate-950/40">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center shadow-md">
            <Sparkles className="w-4 h-4 text-white" />
          </div>
          <span className="text-sm font-semibold bg-clip-text text-transparent bg-gradient-to-r from-indigo-200 to-purple-200">
            InnovaHack
          </span>
          <span className="hidden sm:inline-block text-slate-600 text-xs font-medium">/ workspaces</span>
        </div>

        <div className="flex items-center gap-3">
          {user && (
            <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900/60 border border-white/8 text-xs text-slate-400">
              <div className="w-5 h-5 rounded-full bg-gradient-to-tr from-indigo-500 to-purple-500 flex items-center justify-center text-[10px] font-bold text-white shrink-0">
                {user.email[0].toUpperCase()}
              </div>
              <span className="max-w-[140px] truncate">{user.email}</span>
            </div>
          )}
          <Button
            variant="ghost"
            size="sm"
            isLoading={isLoggingOut}
            onClick={() => { void handleLogout() }}
            leftIcon={<LogOut className="w-3.5 h-3.5" />}
            className="text-slate-400 hover:text-white hover:bg-red-500/10 hover:border-red-500/20"
          >
            Sign out
          </Button>
        </div>
      </header>

      {/* ── Main content ── */}
      <main className="relative z-10 flex flex-col items-center justify-center flex-1 px-4 py-12 sm:px-6">
        <div className="w-full max-w-lg">
          {/* Page heading */}
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="mb-8 text-center"
          >
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 text-[11px] font-medium tracking-wide uppercase mb-4">
              <Shield className="w-3 h-3" />
              <span>Authenticated</span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-b from-white to-slate-400">
              Select a Workspace
            </h1>
            <p className="text-sm text-slate-400 mt-2">
              Choose a workspace to start building knowledge graphs
            </p>
          </motion.div>

          {/* Error alert */}
          <AnimatePresence>
            {error && (
              <div className="mb-4">
                <Alert
                  variant="error"
                  message={error}
                  onClose={() => setError(null)}
                />
                <button
                  type="button"
                  onClick={() => { void fetchWorkspaces() }}
                  className="mt-2 flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors mx-auto"
                >
                  <RefreshCw className="w-3 h-3" />
                  Retry
                </button>
              </div>
            )}
          </AnimatePresence>

          {/* Workspace list */}
          <Card glass className="overflow-visible">
            <div className="p-5">
              {isLoading ? (
                <WorkspaceSkeleton />
              ) : workspaces.length === 0 && !error ? (
                /* Empty state */
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="flex flex-col items-center gap-4 py-10 text-center"
                >
                  <div className="w-14 h-14 rounded-2xl bg-slate-800/80 border border-white/5 flex items-center justify-center">
                    <FolderOpen className="w-6 h-6 text-slate-500" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-200">No workspaces yet</p>
                    <p className="text-xs text-slate-500 mt-1">Create a workspace to get started</p>
                  </div>
                </motion.div>
              ) : (
                /* Workspace cards */
                <motion.ul
                  variants={containerVariants}
                  initial="hidden"
                  animate="visible"
                  className="flex flex-col gap-2.5"
                  role="list"
                >
                  {workspaces.map((ws, idx) => {
                    const isSelected = selecting === ws.workspace_id
                    const colors = [
                      'from-indigo-500 to-purple-600',
                      'from-cyan-500 to-blue-600',
                      'from-violet-500 to-pink-600',
                    ]
                    const color = colors[idx % colors.length]

                    return (
                      <motion.li key={ws.workspace_id} variants={itemVariants}>
                        <button
                          type="button"
                          onClick={() => { void handleSelect(ws.workspace_id) }}
                          disabled={selecting !== null}
                          className={`w-full group flex items-center gap-4 p-4 rounded-xl border transition-all duration-200 text-left cursor-pointer disabled:opacity-70 disabled:cursor-wait ${
                            isSelected
                              ? 'border-indigo-500/60 bg-indigo-500/10 shadow-lg shadow-indigo-500/10'
                              : 'border-white/6 bg-slate-900/50 hover:border-indigo-500/30 hover:bg-slate-800/60'
                          }`}
                          aria-label={`Select workspace ${ws.name}`}
                        >
                          <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center shrink-0 shadow-md`}>
                            <Database className="w-5 h-5 text-white" />
                          </div>

                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-semibold text-slate-100 truncate group-hover:text-white transition-colors">
                              {ws.name}
                            </p>
                            <p className="text-xs text-slate-500 mt-0.5 truncate">
                              ID: {ws.workspace_id}
                            </p>
                          </div>

                          <div className={`transition-all duration-200 ${isSelected ? 'text-indigo-400' : 'text-slate-600 group-hover:text-indigo-400 group-hover:translate-x-0.5'}`}>
                            {isSelected ? (
                              <motion.div
                                animate={{ rotate: 360 }}
                                transition={{ duration: 0.6, ease: 'linear', repeat: Infinity }}
                                className="w-5 h-5 rounded-full border-2 border-indigo-400 border-t-transparent"
                              />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                          </div>
                        </button>
                      </motion.li>
                    )
                  })}
                </motion.ul>
              )}
            </div>

            {/* MED-4: Inline create form — replaces native browser prompt() */}
            {!isLoading && (
              <div className="px-5 pb-5 flex flex-col gap-2">
                <AnimatePresence>
                  {showCreateForm && (
                    <motion.form
                      key="create-form"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ duration: 0.22 }}
                      onSubmit={(e) => { void handleCreateWorkspace(e) }}
                      className="overflow-hidden"
                    >
                      <div className="pt-2 pb-1 flex flex-col gap-2">
                        <p className="text-xs font-semibold text-slate-300">New workspace name</p>
                        <div className="flex gap-2">
                          <Input
                            ref={createInputRef}
                            id="new-workspace-name"
                            placeholder="e.g. Legal Document Analysis"
                            value={newWorkspaceName}
                            onChange={(e) => setNewWorkspaceName(e.target.value)}
                            className="flex-1 text-sm py-2"
                            disabled={isCreating}
                            maxLength={80}
                          />
                          <Button type="submit" size="sm" isLoading={isCreating} disabled={!newWorkspaceName.trim()}>
                            Create
                          </Button>
                          <button
                            type="button"
                            onClick={closeCreateForm}
                            className="w-9 h-9 rounded-lg flex items-center justify-center text-slate-500 hover:text-slate-300 hover:bg-white/5 transition-all shrink-0"
                            aria-label="Cancel"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                        {createError && (
                          <p className="text-xs text-red-400">{createError}</p>
                        )}
                      </div>
                    </motion.form>
                  )}
                </AnimatePresence>

                {!showCreateForm && (
                  <button
                    type="button"
                    onClick={openCreateForm}
                    className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl border border-dashed border-slate-700 hover:border-indigo-500/50 text-slate-500 hover:text-indigo-300 text-xs font-medium transition-all duration-200 hover:bg-indigo-500/5 mt-2 cursor-pointer"
                  >
                    <Plus className="w-3.5 h-3.5" />
                    Create new workspace
                  </button>
                )}
              </div>
            )}
          </Card>

          {/* Footer hint */}
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className="text-center text-[11px] text-slate-600 mt-6"
          >
            Workspace data is isolated per user · Ant Gravity End-to-End Encrypted
          </motion.p>
        </div>
      </main>
    </div>
  )
}
