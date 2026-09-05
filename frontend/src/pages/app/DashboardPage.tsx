/**
 * DashboardPage — live data from /api/cases and /api/graph/summary
 * Replaces all mock data with real API calls.
 */
import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity, ArrowUpRight, BrainCircuit, FileText,
  FolderKanban, Layers, Loader2, Network,
  RefreshCw, Sparkles, TrendingUp, UploadCloud,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { fetchApi } from '../../api/fetchWithNgrok'

const API = ((import.meta.env.VITE_API_BASE as string) || '').replace(/\/$/, '') + '/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ApiCase {
  id: string
  title: string
  description?: string
  status: 'processing' | 'completed' | 'failed'
  created_at: string
}

interface GraphSummary {
  available?: boolean
  nodes: number
  edges: number
  entity_types?: Record<string, number>
}

interface CaseStats {
  total_queries:  number
  rag_precision:  number | null   // 0–100 or null before first query
  cache_hit_rate: number | null   // 0–100 or null before first query
  cached_entries: number
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

// ── Animation variants ────────────────────────────────────────────────────────

const container = { hidden: { opacity: 0 }, visible: { opacity: 1, transition: { staggerChildren: 0.06 } } }
const item = { hidden: { opacity: 0, y: 12 }, visible: { opacity: 1, y: 0, transition: { ease: 'easeOut' as const, duration: 0.3 } } }

// ── Main component ────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { workspaceId, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()

  const [cases, setCases]           = useState<ApiCase[]>([])
  const [graph, setGraph]           = useState<GraphSummary | null>(null)
  const [caseStats, setCaseStats]   = useState<CaseStats | null>(null)
  const [loadingCases, setLC]       = useState(true)
  const [loadingGraph, setLG]       = useState(true)
  const [loadingStats, setLS]       = useState(true)
  const [activeTab, setActiveTab]   = useState<'all' | 'completed' | 'processing'>('all')

  const caseId = localStorage.getItem('innova_active_case_id')

  async function fetchCases() {
    setLC(true)
    try {
      const r = await fetchApi(`${API}/cases`)
      const d = await r.json()
      setCases(Array.isArray(d) ? d : (d.cases ?? []))
    } catch { /* silent */ } finally { setLC(false) }
  }

  async function fetchGraph() {
    if (!caseId) { setLG(false); return }
    setLG(true)
    try {
      const r = await fetchApi(`${API}/graph/summary?case_id=${encodeURIComponent(caseId)}`)
      if (r.ok) {
        const summary = await r.json() as Omit<GraphSummary, 'available'>
        setGraph({ ...summary, available: true })
      } else {
        setGraph({ available: false, nodes: 0, edges: 0 })
      }
    } catch { /* silent */ } finally { setLG(false) }
  }

  async function fetchStats() {
    if (!caseId) { setLS(false); return }
    setLS(true)
    try {
      const r = await fetchApi(`${API}/stats?case_id=${encodeURIComponent(caseId)}`)
      if (r.ok) setCaseStats(await r.json() as CaseStats)
    } catch { /* silent */ } finally { setLS(false) }
  }

  useEffect(() => {
    if (authLoading) return   // wait for token to be populated before fetching
    void fetchCases(); void fetchGraph(); void fetchStats()
  }, [authLoading])
  const filtered = cases.filter(c => activeTab === 'all' || c.status === activeTab)

  // ── Entity type bar (from real data) ──────────────────────────────────────
  const entityTypes   = graph?.entity_types ?? {}
  const totalEntities = Object.values(entityTypes).reduce((a, b) => a + b, 0) || 1
  const TOP_COLORS    = ['bg-indigo-500', 'bg-purple-500', 'bg-cyan-400', 'bg-amber-400', 'bg-emerald-400']
  const typeEntries   = Object.entries(entityTypes).sort((a, b) => b[1] - a[1]).slice(0, 5)

  return (
    <div className="p-4 sm:p-6 lg:p-8 max-w-7xl mx-auto space-y-6">

      {/* ── Header ── */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}
        className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 p-6 rounded-2xl glass-panel relative overflow-hidden">
        <div className="absolute -top-24 -right-24 w-72 h-72 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-72 h-72 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="space-y-1.5 z-10">
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> MMKG Engine Active
            </span>
            <span className="text-xs text-slate-500">Workspace: {workspaceId ?? 'Default'}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-100 to-slate-300">
            Compliance Intelligence
          </h1>
          <p className="text-xs sm:text-sm text-slate-400">
            Multi-modal knowledge graph synthesis, spectral clustering fusion &amp; GraphRAG retrieval.
          </p>
        </div>
        <div className="flex items-center gap-2.5 z-10 shrink-0">
          <button onClick={() => navigate('/app/upload')}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800/90 hover:bg-slate-700/90 text-slate-200 border border-slate-700 text-xs font-medium transition-all active:scale-95">
            <UploadCloud className="w-4 h-4 text-indigo-400" /> Upload File
          </button>
          <button onClick={() => navigate('/app/ai-assistant')}
            className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-500 via-indigo-600 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white border border-indigo-400/30 text-xs font-semibold transition-all active:scale-95">
            <BrainCircuit className="w-4 h-4" /> New GraphRAG Query
          </button>
          <button onClick={() => { void fetchCases(); void fetchGraph(); void fetchStats() }}
            className="p-2.5 rounded-xl border border-slate-700 hover:bg-slate-800 text-slate-400 hover:text-white transition-all"
            title="Refresh">
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </motion.div>

      {/* ── Metric cards ── */}
      <motion.div variants={container} initial="hidden" animate="visible"
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

        {/* Nodes */}
        <motion.div variants={item} className="p-5 rounded-2xl glass-panel group hover:border-indigo-500/30 transition-all duration-300">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Graph Nodes</span>
            <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition-transform">
              <Network className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            {loadingGraph
              ? <Loader2 className="w-5 h-5 animate-spin text-slate-500" />
              : <span className="text-2xl font-bold text-white tracking-tight">{(graph?.nodes ?? 0).toLocaleString()}</span>}
            {!loadingGraph && graph?.nodes && (
              <span className="text-[11px] font-medium text-emerald-400 flex items-center gap-0.5">
                <TrendingUp className="w-3 h-3" /> Live
              </span>)}
          </div>
          <div className="mt-3 text-[11px] text-slate-500 border-t border-white/5 pt-2.5">
            {graph?.available ? `${Object.keys(entityTypes).length} entity types` : 'Upload a document to build graph'}
          </div>
        </motion.div>

        {/* Edges */}
        <motion.div variants={item} className="p-5 rounded-2xl glass-panel group hover:border-purple-500/30 transition-all duration-300">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Graph Edges</span>
            <div className="w-8 h-8 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-center text-purple-400 group-hover:scale-110 transition-transform">
              <Layers className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            {loadingGraph
              ? <Loader2 className="w-5 h-5 animate-spin text-slate-500" />
              : <span className="text-2xl font-bold text-white tracking-tight">{(graph?.edges ?? 0).toLocaleString()}</span>}
            {!loadingGraph && <span className="text-[11px] font-medium text-purple-400">Spectral Fused</span>}
          </div>
          <div className="mt-3 text-[11px] text-slate-500 border-t border-white/5 pt-2.5">
            {graph?.available ? 'DBSCAN + SentenceTransformer' : '—'}
          </div>
        </motion.div>

        {/* Cases */}
        <motion.div variants={item} className="p-5 rounded-2xl glass-panel group hover:border-cyan-500/30 transition-all duration-300">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Compliance Cases</span>
            <div className="w-8 h-8 rounded-xl bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400 group-hover:scale-110 transition-transform">
              <FolderKanban className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            {loadingCases
              ? <Loader2 className="w-5 h-5 animate-spin text-slate-500" />
              : <span className="text-2xl font-bold text-white tracking-tight">{cases.length}</span>}
            {!loadingCases && <span className="text-[11px] font-medium text-cyan-400">Active</span>}
          </div>
          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500 border-t border-white/5 pt-2.5">
            <span>Completed: {cases.filter(c => c.status === 'completed').length}</span>
            <span>Processing: {cases.filter(c => c.status === 'processing').length}</span>
          </div>
        </motion.div>

        {/* Precision */}
        <motion.div variants={item} className="p-5 rounded-2xl glass-panel group hover:border-emerald-500/30 transition-all duration-300">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">RAG Precision Score</span>
            <div className="w-8 h-8 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 group-hover:scale-110 transition-transform">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            {loadingStats
              ? <Loader2 className="w-5 h-5 animate-spin text-slate-500" />
              : caseStats?.rag_precision != null
                ? <span className="text-2xl font-bold text-white tracking-tight">{caseStats.rag_precision}%</span>
                : <span className="text-2xl font-bold text-slate-500">—</span>}
            {!loadingStats && (
              <span className="text-[11px] font-medium text-emerald-400">Cosine Similarity</span>
            )}
          </div>
          <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500 border-t border-white/5 pt-2.5">
            <span>MiniLM-L6 Embeddings</span>
            <span>
              Cache:{' '}
              {loadingStats || caseStats?.cache_hit_rate == null
                ? '—'
                : `${caseStats.cache_hit_rate}%`}
            </span>
          </div>
        </motion.div>
      </motion.div>

      {/* ── Middle row: Cases + KG Preview ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* Cases widget */}
        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.15 }}
          className="lg:col-span-7 glass-panel rounded-2xl p-6 flex flex-col">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
            <div>
              <div className="flex items-center gap-2">
                <FolderKanban className="w-4 h-4 text-indigo-400" />
                <h3 className="text-base font-bold text-white">Recent Compliance Cases</h3>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">Live from your workspace</p>
            </div>
            <div className="flex items-center gap-1 bg-slate-900/80 p-1 rounded-xl border border-white/5 self-start">
              {(['all', 'completed', 'processing'] as const).map(tab => (
                <button key={tab} onClick={() => setActiveTab(tab)}
                  className={`px-2.5 py-1 rounded-lg text-xs font-medium transition-all capitalize ${activeTab === tab ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-slate-200'}`}>
                  {tab}
                </button>
              ))}
            </div>
          </div>

          {loadingCases ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="w-6 h-6 animate-spin text-slate-500" />
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center py-8">
              <FolderKanban className="w-10 h-10 text-slate-700 mb-3" />
              <p className="text-sm text-slate-500">No cases yet. <Link to="/app/upload" className="text-indigo-400 hover:underline">Upload a document</Link> to get started.</p>
            </div>
          ) : (
            <div className="space-y-3 flex-1">
              <AnimatePresence mode="popLayout">
                {filtered.slice(0, 5).map(c => (
                  <motion.div key={c.id} layout initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }} transition={{ duration: 0.2 }}
                    className="p-4 rounded-xl bg-slate-900/50 hover:bg-slate-800/60 border border-white/5 hover:border-indigo-500/30 transition-all flex items-center justify-between gap-4 group">
                    <div className="space-y-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-slate-500 shrink-0">{c.id.slice(0, 8)}…</span>
                        <h4 className="text-sm font-semibold text-slate-100 group-hover:text-indigo-300 transition-colors truncate">{c.title}</h4>
                      </div>
                      <p className="text-[11px] text-slate-400">{timeAgo(c.created_at)}</p>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className={`px-2.5 py-1 rounded-full text-[10px] font-semibold border ${
                        c.status === 'completed' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : c.status === 'processing' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>{c.status}</span>
                      <button onClick={() => { localStorage.setItem('innova_active_case_id', c.id); navigate(`/app/cases/${c.id}`) }}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-white/10 transition-colors">
                        <ArrowUpRight className="w-4 h-4" />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}

          <div className="mt-5 pt-3 border-t border-white/5 flex items-center justify-between text-xs text-slate-400">
            <span>Showing {Math.min(filtered.length, 5)} of {filtered.length} cases</span>
            <Link to="/app/cases" className="text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1">
              View all <ArrowUpRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </motion.div>

        {/* KG Preview widget — real entity distribution */}
        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.2 }}
          className="lg:col-span-5 glass-panel rounded-2xl p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <h3 className="text-base font-bold text-white">Multi-Modal KG Preview</h3>
              </div>
              <Link to="/app/knowledge-graph" className="text-xs text-indigo-400 hover:text-indigo-300 font-medium flex items-center gap-1">
                Explorer <ArrowUpRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {/* Animated node visualization */}
            <div className="relative h-36 rounded-xl bg-slate-950/80 border border-white/10 overflow-hidden flex items-center justify-center">
              <div className="absolute inset-0 opacity-30 bg-[radial-gradient(#6366f1_1px,transparent_1px)] [background-size:16px_16px]" />
              {loadingGraph ? (
                <Loader2 className="w-6 h-6 animate-spin text-slate-500 relative z-10" />
              ) : graph?.available ? (
                <div className="relative z-10 flex flex-col items-center gap-2">
                  <div className="flex items-center gap-3">
                    {typeEntries.slice(0, 3).map(([type], i) => (
                      <div key={type} className={`w-10 h-10 rounded-full border flex items-center justify-center text-[9px] font-bold animate-pulse ${
                        i === 0 ? 'bg-indigo-600/30 border-indigo-400/60 text-indigo-300'
                        : i === 1 ? 'bg-purple-600/30 border-purple-400/60 text-purple-300'
                        : 'bg-cyan-600/30 border-cyan-400/60 text-cyan-300'}`}>
                        {type.slice(0, 4)}
                      </div>
                    ))}
                  </div>
                  <span className="text-[10px] text-slate-400 font-mono">
                    {graph.nodes} nodes · {graph.edges} edges · {Object.keys(entityTypes).length} types
                  </span>
                </div>
              ) : (
                <p className="relative z-10 text-xs text-slate-500 text-center px-4">
                  No graph yet — upload a document to build your knowledge graph.
                </p>
              )}
            </div>

            {/* Live entity distribution bar */}
            <div className="mt-4 space-y-2">
              <span className="text-xs font-medium text-slate-300">Entity Type Distribution</span>
              {typeEntries.length > 0 ? (
                <>
                  <div className="h-2.5 w-full bg-slate-900 rounded-full overflow-hidden flex">
                    {typeEntries.map(([type, count], i) => (
                      <div key={type} className={`h-full ${TOP_COLORS[i]}`}
                        style={{ width: `${(count / totalEntities) * 100}%` }} title={`${type}: ${count}`} />
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-slate-400 pt-1">
                    {typeEntries.map(([type, count], i) => (
                      <span key={type} className="flex items-center gap-1">
                        <span className={`w-2 h-2 rounded-full ${TOP_COLORS[i]}`} />
                        {type} ({Math.round((count / totalEntities) * 100)}%)
                      </span>
                    ))}
                  </div>
                </>
              ) : (
                <div className="h-2.5 w-full bg-slate-900 rounded-full" />
              )}
            </div>
          </div>

          <button onClick={() => navigate('/app/knowledge-graph')}
            className="mt-4 w-full py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 border border-white/10 text-xs font-semibold text-slate-200 hover:text-white flex items-center justify-center gap-2 transition-all">
            <Network className="w-4 h-4 text-purple-400" />
            Open Interactive Graph Explorer
          </button>
        </motion.div>
      </div>

      {/* ── Bottom row: Quick actions ── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">

        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.25 }}
          className="glass-panel rounded-2xl p-6 flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <UploadCloud className="w-4 h-4 text-cyan-400" />
            <h3 className="text-sm font-bold text-white">Ingest Documents</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Upload PDFs, DOCX, Excel, audio recordings, or images. The MMKG pipeline
            extracts entities and builds a unified knowledge graph automatically.
          </p>
          <button onClick={() => navigate('/app/upload')}
            className="mt-auto w-full py-2.5 rounded-xl bg-cyan-500/10 hover:bg-cyan-500/20 border border-cyan-500/20 text-cyan-300 text-xs font-semibold transition-all flex items-center justify-center gap-2">
            <UploadCloud className="w-4 h-4" /> Go to Upload
          </button>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.3 }}
          className="glass-panel rounded-2xl p-6 flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <BrainCircuit className="w-4 h-4 text-indigo-400" />
            <h3 className="text-sm font-bold text-white">GraphRAG Query</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Ask complex compliance questions. Every answer is grounded in retrieved
            graph entities with full citation traceability back to source documents.
          </p>
          <button onClick={() => navigate('/app/ai-assistant')}
            className="mt-auto w-full py-2.5 rounded-xl bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 text-indigo-300 text-xs font-semibold transition-all flex items-center justify-center gap-2">
            <BrainCircuit className="w-4 h-4" /> Ask AI Assistant
          </button>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 15 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, delay: 0.35 }}
          className="glass-panel rounded-2xl p-6 flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-purple-400" />
            <h3 className="text-sm font-bold text-white">Compliance Reports</h3>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Generate structured compliance reports from your knowledge graph.
            Reports include full evidence packages and entity distribution analysis.
          </p>
          <button onClick={() => navigate('/app/reports')}
            className="mt-auto w-full py-2.5 rounded-xl bg-purple-500/10 hover:bg-purple-500/20 border border-purple-500/20 text-purple-300 text-xs font-semibold transition-all flex items-center justify-center gap-2">
            <FileText className="w-4 h-4" /> View Reports
          </button>
        </motion.div>
      </div>

    </div>
  )
}
