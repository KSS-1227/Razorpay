/**
 * ReportsPage
 *
 * Wraps GET /api/report/{case_id}  — fetch saved report
 *      POST /api/report/           — generate new report
 *
 * Layout:
 *  Left  — generate panel (question input + case badge)
 *  Right — rendered report with KG stats + evidence breakdown
 */
import { useState } from 'react'
import {
  Activity, AlertTriangle, BookOpen, BrainCircuit,
  CheckCircle2, ChevronDown, ChevronUp, Clock,
  FileText, Layers, Link2, Loader2, Network,
  RefreshCw, Send, Share2, Sparkles,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { fetchApi } from '../../api/fetchWithNgrok'

const API = ((import.meta.env.VITE_API_BASE as string) || '').replace(/\/$/, '') + '/api'

// ── Types (mirror workspace_report.py response) ───────────────────────────────

interface KGSummary {
  nodes: number
  edges: number
  entity_distribution: Record<string, number>
}

interface EvidenceEntity  { name: string; type: string; confidence: number; description: string }
interface EvidenceRel     { source: string; target: string; description: string; weight: number }
interface EvidenceChunk   { chunk_id: string; text: string; tokens: number }

interface Evidence {
  entities?:      EvidenceEntity[]
  relationships?: EvidenceRel[]
  text_chunks?:   EvidenceChunk[]
  images?:        { entity: string; image_path: string }[]
}

interface Report {
  generated_at:    string
  case_id:         string
  query:           string
  answer:          string
  knowledge_graph: KGSummary
  evidence:        Evidence
  prototype:       { engine: string; multimodal: boolean; retrieval: string }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function Section({
  title, icon, count, color, children, open: defaultOpen = false,
}: {
  title: string; icon: React.ReactNode; count: number
  color: string; children: React.ReactNode; open?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  if (count === 0) return null
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 overflow-hidden">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between p-4 hover:bg-zinc-800/50 transition-colors">
        <div className="flex items-center gap-2.5">
          <span className={color}>{icon}</span>
          <span className="text-sm font-semibold">{title}</span>
          <span className={`text-xs font-bold px-2 py-0.5 rounded-full bg-white/5 ${color}`}>{count}</span>
        </div>
        {open ? <ChevronUp size={15} className="text-zinc-500" /> : <ChevronDown size={15} className="text-zinc-500" />}
      </button>
      {open && <div className="border-t border-zinc-800 p-3 space-y-2">{children}</div>}
    </div>
  )
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ReportsPage() {
  const navigate  = useNavigate()
  const caseId    = localStorage.getItem('innova_active_case_id')

  const [question,    setQuestion]    = useState('')
  const [generating,  setGenerating]  = useState(false)
  const [fetching,    setFetching]    = useState(false)
  const [report,      setReport]      = useState<Report | null>(null)
  const [error,       setError]       = useState<string | null>(null)

  // ── Generate new report ───────────────────────────────────────────────────
  async function generateReport() {
    if (!caseId || !question.trim()) return
    setGenerating(true); setError(null); setReport(null)
    try {
      const resp = await fetchApi(`${API}/report/`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ case_id: caseId, question: question.trim(), top_k: 10 }),
      })
      if (!resp.ok) {
        const b = await resp.json().catch(() => ({}))
        throw new Error(b?.detail ?? `Error ${resp.status}`)
      }
      const data = await resp.json()
      setReport(data.report)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally { setGenerating(false) }
  }

  // ── Fetch saved report ────────────────────────────────────────────────────
  async function fetchReport() {
    if (!caseId) return
    setFetching(true); setError(null)
    try {
      const resp = await fetchApi(`${API}/report/${encodeURIComponent(caseId)}`)
      if (!resp.ok) {
        if (resp.status === 404) throw new Error('No report found for this case. Generate one first.')
        throw new Error(`Error ${resp.status}`)
      }
      const data = await resp.json()
      setReport(data.report)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally { setFetching(false) }
  }

  const ev = report?.evidence ?? {}
  const kg = report?.knowledge_graph
  const totalEntities = Object.values(kg?.entity_distribution ?? {}).reduce((a, b) => a + b, 0) || 1
  const TOP_COLORS    = ['bg-indigo-500', 'bg-purple-500', 'bg-cyan-400', 'bg-amber-400', 'bg-emerald-400']
  const typeEntries   = Object.entries(kg?.entity_distribution ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 5)

  return (
    <div className="min-h-screen bg-[#09090b] text-white p-6 lg:p-8">

      {/* Header */}
      <div className="mb-8">
        <p className="text-xs font-semibold uppercase tracking-[0.22em] text-purple-400 mb-2">
          Compliance Output
        </p>
        <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
        <p className="text-sm text-zinc-400 mt-1">
          Generate GraphRAG-grounded compliance reports with full citation traceability.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

        {/* ── Left: Generate panel ── */}
        <div className="lg:col-span-4 space-y-4">

          {/* Case badge */}
          {caseId ? (
            <div className="rounded-xl bg-emerald-500/10 border border-emerald-500/20 px-4 py-3 text-xs text-emerald-300">
              <span className="font-semibold">Active case</span>
              <p className="font-mono mt-0.5 text-emerald-400/70 truncate">{caseId}</p>
            </div>
          ) : (
            <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 px-4 py-3 text-xs text-amber-300 flex items-start gap-2">
              <AlertTriangle size={14} className="shrink-0 mt-0.5" />
              <span>No active case. Open a case or upload documents first.</span>
            </div>
          )}

          {/* Question input */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-4">
            <div className="flex items-center gap-2 mb-1">
              <BrainCircuit size={16} className="text-indigo-400" />
              <h2 className="text-sm font-bold">Generate New Report</h2>
            </div>
            <p className="text-xs text-zinc-500 leading-relaxed">
              Enter a compliance question. GraphRAG will retrieve relevant entities
              and generate an evidence-grounded report.
            </p>
            <textarea
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); void generateReport() } }}
              placeholder="e.g. Summarize all ISO 27001 control gaps found in the uploaded documents…"
              rows={5}
              disabled={!caseId || generating}
              className="w-full resize-none rounded-xl bg-zinc-950 border border-zinc-700 px-4 py-3 text-sm outline-none focus:border-indigo-500 transition placeholder:text-zinc-600 disabled:opacity-50"
            />
            <button
              onClick={() => void generateReport()}
              disabled={!caseId || !question.trim() || generating}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 disabled:opacity-40 disabled:cursor-not-allowed py-2.5 text-sm font-semibold transition"
            >
              {generating ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
              {generating ? 'Generating…' : 'Generate Report'}
            </button>
          </div>

          {/* Load saved report */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-3">
            <div className="flex items-center gap-2">
              <BookOpen size={15} className="text-purple-400" />
              <h2 className="text-sm font-bold">Load Saved Report</h2>
            </div>
            <p className="text-xs text-zinc-500">Fetch the most recently generated report for the active case.</p>
            <button
              onClick={() => void fetchReport()}
              disabled={!caseId || fetching}
              className="w-full flex items-center justify-center gap-2 rounded-xl border border-zinc-700 hover:border-purple-500/40 disabled:opacity-40 disabled:cursor-not-allowed py-2.5 text-sm font-medium transition"
            >
              {fetching ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
              {fetching ? 'Loading…' : 'Load Saved Report'}
            </button>
          </div>

          {/* Navigate shortcuts */}
          <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4 space-y-2">
            <p className="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">Quick Links</p>
            {[
              { label: 'AI Assistant', path: '/app/ai-assistant', icon: <BrainCircuit size={13} /> },
              { label: 'Knowledge Graph', path: '/app/knowledge-graph', icon: <Network size={13} /> },
              { label: 'Evidence Explorer', path: '/app/evidence', icon: <FileText size={13} /> },
            ].map(l => (
              <button key={l.path} onClick={() => navigate(l.path)}
                className="w-full flex items-center gap-2 text-xs text-zinc-400 hover:text-white px-3 py-2 rounded-lg hover:bg-white/5 transition">
                <span className="text-indigo-400">{l.icon}</span>{l.label}
              </button>
            ))}
          </div>
        </div>

        {/* ── Right: Report content ── */}
        <div className="lg:col-span-8 space-y-5">

          {/* Error */}
          {error && (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 p-5 text-sm text-red-300 flex items-start gap-3">
              <AlertTriangle size={18} className="shrink-0 mt-0.5 text-red-400" />
              {error}
            </div>
          )}

          {/* Empty state */}
          {!report && !error && !generating && !fetching && (
            <div className="rounded-2xl border border-dashed border-zinc-700 p-16 text-center">
              <FileText size={48} className="mx-auto text-zinc-700 mb-4" />
              <h2 className="text-xl font-semibold text-zinc-300">No Report Yet</h2>
              <p className="text-zinc-500 text-sm mt-2 max-w-sm mx-auto">
                Enter a compliance question and click Generate, or load a previously saved report.
              </p>
            </div>
          )}

          {/* Generating spinner */}
          {generating && (
            <div className="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-12 text-center space-y-4">
              <Loader2 size={40} className="animate-spin text-indigo-400 mx-auto" />
              <p className="text-sm text-indigo-300 font-medium">Running GraphRAG pipeline…</p>
              <p className="text-xs text-zinc-500">Retrieving entities → grounding answer → packaging evidence</p>
            </div>
          )}

          {/* Report body */}
          {report && !generating && (
            <div className="space-y-5">

              {/* Report header card */}
              <div className="rounded-2xl border border-zinc-700 bg-zinc-900/80 p-6 space-y-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={18} className="text-emerald-400 shrink-0" />
                    <h2 className="text-lg font-bold">Compliance Report</h2>
                  </div>
                  <span className="text-[10px] font-mono text-zinc-500 shrink-0">
                    {new Date(report.generated_at).toLocaleString()}
                  </span>
                </div>

                <div className="rounded-xl bg-zinc-950/70 border border-zinc-700/50 px-4 py-2.5">
                  <p className="text-[11px] text-zinc-500 font-semibold uppercase tracking-wider mb-1">Query</p>
                  <p className="text-sm text-zinc-200 leading-relaxed">{report.query}</p>
                </div>

                <div className="flex flex-wrap gap-2 text-[11px]">
                  <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-300">
                    <Sparkles size={10} /> {report.prototype.engine}
                  </span>
                  <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-purple-300">
                    <Activity size={10} /> {report.prototype.retrieval}
                  </span>
                  {report.prototype.multimodal && (
                    <span className="flex items-center gap-1 px-2.5 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/20 text-cyan-300">
                      <Network size={10} /> Multi-Modal
                    </span>
                  )}
                </div>
              </div>

              {/* KG Stats */}
              {kg && (
                <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Network size={15} className="text-indigo-400" />
                    <h3 className="text-sm font-bold">Knowledge Graph Statistics</h3>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    {[
                      { label: 'Nodes', value: kg.nodes, color: 'text-indigo-400', icon: <Network size={14} /> },
                      { label: 'Edges', value: kg.edges, color: 'text-purple-400', icon: <Layers size={14} /> },
                      { label: 'Entity Types', value: Object.keys(kg.entity_distribution).length, color: 'text-cyan-400', icon: <Activity size={14} /> },
                    ].map(s => (
                      <div key={s.label} className="rounded-xl bg-zinc-950/60 border border-zinc-700/50 p-4 text-center">
                        <span className={`${s.color} flex justify-center mb-2`}>{s.icon}</span>
                        <p className={`text-2xl font-bold ${s.color}`}>{s.value.toLocaleString()}</p>
                        <p className="text-[11px] text-zinc-500 mt-1">{s.label}</p>
                      </div>
                    ))}
                  </div>
                  {typeEntries.length > 0 && (
                    <div className="space-y-2">
                      <p className="text-xs text-zinc-400 font-medium">Entity Distribution</p>
                      <div className="h-2 w-full bg-zinc-800 rounded-full overflow-hidden flex">
                        {typeEntries.map(([t, c], i) => (
                          <div key={t} className={`h-full ${TOP_COLORS[i]}`}
                            style={{ width: `${(c / totalEntities) * 100}%` }} title={`${t}: ${c}`} />
                        ))}
                      </div>
                      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-zinc-400">
                        {typeEntries.map(([t, c], i) => (
                          <span key={t} className="flex items-center gap-1">
                            <span className={`w-2 h-2 rounded-full ${TOP_COLORS[i]}`} />{t}: {c}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Answer */}
              <div className="rounded-2xl border border-zinc-800 bg-zinc-900/60 p-5 space-y-3">
                <div className="flex items-center gap-2">
                  <BrainCircuit size={15} className="text-indigo-400" />
                  <h3 className="text-sm font-bold">GraphRAG Answer</h3>
                </div>
                <p className="text-sm text-zinc-200 leading-7 whitespace-pre-wrap">{report.answer}</p>
              </div>

              {/* Evidence sections */}
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <FileText size={15} className="text-purple-400" />
                  <h3 className="text-sm font-bold">Citation Evidence</h3>
                  <span className="text-xs text-zinc-500">— every claim is traceable to a source</span>
                </div>

                <Section title="Supporting Entities" icon={<Network size={14} />}
                  count={ev.entities?.length ?? 0} color="text-cyan-400" open>
                  {ev.entities?.map((e, i) => (
                    <div key={i} className="rounded-lg bg-zinc-800/60 border border-zinc-700/50 p-3 space-y-1">
                      <div className="flex items-center justify-between gap-2">
                        <span className="text-xs font-semibold text-white truncate">{e.name}</span>
                        <span className="text-[10px] font-mono text-zinc-400 shrink-0">{Math.round(e.confidence * 100)}%</span>
                      </div>
                      <span className="inline-block text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">{e.type}</span>
                      {e.description && <p className="text-[11px] text-zinc-400 line-clamp-2 leading-relaxed mt-1">{e.description}</p>}
                    </div>
                  ))}
                </Section>

                <Section title="Supporting Relationships" icon={<Share2 size={14} />}
                  count={ev.relationships?.length ?? 0} color="text-violet-400">
                  {ev.relationships?.map((r, i) => (
                    <div key={i} className="rounded-lg bg-zinc-800/60 border border-zinc-700/50 p-3 space-y-1">
                      <div className="flex items-center gap-1.5 text-xs flex-wrap">
                        <span className="font-semibold text-violet-300 truncate max-w-[100px]">{r.source}</span>
                        <Link2 size={10} className="text-zinc-500 shrink-0" />
                        <span className="font-semibold text-violet-300 truncate max-w-[100px]">{r.target}</span>
                        <span className="ml-auto text-[10px] font-mono text-zinc-500">w:{Number(r.weight).toFixed(1)}</span>
                      </div>
                      {r.description && <p className="text-[11px] text-zinc-400 line-clamp-2">{r.description}</p>}
                    </div>
                  ))}
                </Section>

                <Section title="Source Document Chunks" icon={<FileText size={14} />}
                  count={ev.text_chunks?.length ?? 0} color="text-emerald-400">
                  {ev.text_chunks?.map((c, i) => (
                    <div key={i} className="rounded-lg bg-zinc-800/60 border border-zinc-700/50 p-3 space-y-1.5">
                      <div className="flex items-center justify-between text-[10px] text-zinc-500">
                        <span className="font-mono">{c.chunk_id.slice(0, 16)}…</span>
                        <span>{c.tokens} tokens</span>
                      </div>
                      <p className="text-[11px] text-zinc-300 line-clamp-4 leading-relaxed bg-zinc-900/60 p-2 rounded border border-zinc-700/40">
                        "{c.text.slice(0, 320)}{c.text.length > 320 ? '…' : ''}"
                      </p>
                    </div>
                  ))}
                </Section>

                <Section title="Supporting Images" icon={<Sparkles size={14} />}
                  count={ev.images?.length ?? 0} color="text-amber-400">
                  {ev.images?.map((img, i) => (
                    <div key={i} className="rounded-lg bg-zinc-800/60 border border-zinc-700/50 p-3">
                      <p className="text-xs font-semibold text-amber-300 truncate">{img.entity}</p>
                      <p className="text-[10px] text-zinc-500 font-mono mt-1 truncate">{img.image_path}</p>
                    </div>
                  ))}
                </Section>
              </div>

              {/* Processing metadata */}
              <div className="rounded-xl bg-zinc-900/40 border border-zinc-800 px-4 py-3 flex flex-wrap gap-4 text-[11px] text-zinc-500">
                <span className="flex items-center gap-1"><Clock size={11} /> Generated {new Date(report.generated_at).toLocaleString()}</span>
                <span className="flex items-center gap-1"><Network size={11} /> Case: {report.case_id.slice(0, 16)}…</span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
