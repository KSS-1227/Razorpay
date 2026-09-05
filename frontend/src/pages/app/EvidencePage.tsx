/**
 * EvidencePage
 *
 * Visual entity-relationship explorer for the active case.
 * Wires to:
 *   GET /api/graph/summary?case_id=   — KG stats header
 *   GET /api/graph/entities?case_id=  — entity cards grid
 *   GET /api/graph/relationships?case_id= — relationship table
 *
 * Layout:
 *   Top  — KG summary stats bar
 *   Left — entity cards (searchable, filterable by type)
 *   Right — relationship list + selected entity deep-dive
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowRight, BookOpen,
  FileSearch2, Filter, Layers, Link2, Loader2,
  Network, RefreshCw, Search, Share2, X,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { fetchApi } from '../../api/fetchWithNgrok'

const API = ((import.meta.env.VITE_API_BASE as string) || '').replace(/\/$/, '') + '/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface Entity {
  name:        string
  type:        string
  description: string
}

interface Relationship {
  source:      string
  target:      string
  description: string
  weight:      number
}

interface GraphSummary {
  nodes:        number
  edges:        number
  entity_types: Record<string, number>
}

// ── Colour palette ────────────────────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
  ORG:          'border-amber-500/60 bg-amber-500/10 text-amber-300',
  ORGANIZATION: 'border-amber-500/60 bg-amber-500/10 text-amber-300',
  PERSON:       'border-pink-500/60  bg-pink-500/10  text-pink-300',
  POLICY:       'border-purple-500/60 bg-purple-500/10 text-purple-300',
  REGULATION:   'border-purple-500/60 bg-purple-500/10 text-purple-300',
  CONTROL:      'border-cyan-500/60  bg-cyan-500/10  text-cyan-300',
  RISK:         'border-red-500/60   bg-red-500/10   text-red-300',
  EVENT:        'border-emerald-500/60 bg-emerald-500/10 text-emerald-300',
  TECHNOLOGY:   'border-blue-500/60  bg-blue-500/10  text-blue-300',
  CONCEPT:      'border-orange-500/60 bg-orange-500/10 text-orange-300',
  IMG:          'border-green-500/60 bg-green-500/10 text-green-300',
  ORI_IMG:      'border-green-500/60 bg-green-500/10 text-green-300',
}

function typeStyle(t: string) {
  return TYPE_COLORS[t.replace(/"/g, '').toUpperCase()] ?? 'border-zinc-600 bg-zinc-800/60 text-zinc-300'
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function clean(s: string) { return s.replace(/"/g, '').trim() }

// ── Main component ────────────────────────────────────────────────────────────

export default function EvidencePage() {
  const navigate = useNavigate()
  const { isLoading: authLoading } = useAuth()
  const caseId   = localStorage.getItem('innova_active_case_id')

  const [summary,   setSummary]   = useState<GraphSummary | null>(null)
  const [entities,  setEntities]  = useState<Entity[]>([])
  const [rels,      setRels]      = useState<Relationship[]>([])
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState<string | null>(null)

  const [search,    setSearch]    = useState('')
  const [typeFilter,setTypeFilter]= useState('ALL')
  const [selected,  setSelected]  = useState<Entity | null>(null)

  // ── Fetch all three endpoints in parallel ─────────────────────────────────
  const load = useCallback(async () => {
    if (!caseId) { setLoading(false); return }
    setLoading(true); setError(null)
    try {
      const qs = `?case_id=${encodeURIComponent(caseId)}`
      const [rSum, rEnt, rRel] = await Promise.all([
        fetchApi(`${API}/graph/summary${qs}`),
        fetchApi(`${API}/graph/entities${qs}&limit=300`),
        fetchApi(`${API}/graph/relationships${qs}&limit=500`),
      ])
      if (!rSum.ok) throw new Error(`Graph summary: ${rSum.status}`)
      if (!rEnt.ok) throw new Error(`Entities: ${rEnt.status}`)
      if (!rRel.ok) throw new Error(`Relationships: ${rRel.status}`)

      const [sum, ent, rel] = await Promise.all([rSum.json(), rEnt.json(), rRel.json()])
      setSummary(sum)
      setEntities(Array.isArray(ent) ? ent : [])
      setRels(Array.isArray(rel) ? rel : [])
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load evidence')
    } finally { setLoading(false) }
  }, [caseId])

  useEffect(() => {
    if (authLoading) return   // wait for token before fetching
    void load()
  }, [load, authLoading])

  // ── Derived ───────────────────────────────────────────────────────────────
  const allTypes = useMemo(
    () => ['ALL', ...Array.from(new Set(entities.map(e => clean(e.type)))).sort()],
    [entities],
  )

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase()
    return entities.filter(e =>
      (typeFilter === 'ALL' || clean(e.type) === typeFilter) &&
      (clean(e.name).toLowerCase().includes(q) || clean(e.description).toLowerCase().includes(q))
    )
  }, [entities, search, typeFilter])

  // Relationships for selected entity
  const selectedRels = useMemo(() => {
    if (!selected) return []
    const n = clean(selected.name)
    return rels.filter(r => clean(r.source) === n || clean(r.target) === n)
  }, [selected, rels])

  // Entity type distribution from summary
  const typeEntries  = Object.entries(summary?.entity_types ?? {}).sort((a, b) => b[1] - a[1])
  const totalEnt     = typeEntries.reduce((a, [, v]) => a + v, 0) || 1
  const TOP_COLORS   = ['bg-indigo-500','bg-purple-500','bg-cyan-400','bg-amber-400','bg-emerald-400']

  // ── No case ───────────────────────────────────────────────────────────────
  if (!caseId) return (
    <div className="min-h-screen bg-[#09090b] text-white flex flex-col items-center justify-center gap-4 p-8">
      <AlertTriangle size={48} className="text-amber-400" />
      <h2 className="text-2xl font-bold">No Active Case</h2>
      <p className="text-zinc-400 text-sm text-center max-w-sm">
        Open a case from the Cases page or upload a document first,
        then come back to explore its evidence.
      </p>
      <button onClick={() => navigate('/app/cases')}
        className="mt-2 px-6 py-2.5 rounded-xl bg-cyan-500 hover:bg-cyan-600 text-sm font-semibold transition">
        Go to Cases
      </button>
    </div>
  )

  return (
    <div className="min-h-screen bg-[#09090b] text-white flex flex-col">

      {/* ── Header ── */}
      <div className="px-6 pt-6 pb-4 border-b border-zinc-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.22em] text-purple-400 mb-1">
            Citation Traceability
          </p>
          <h1 className="text-2xl font-bold tracking-tight">Evidence Explorer</h1>
          <p className="text-xs text-zinc-400 mt-0.5">
            Browse every entity and relationship extracted from your documents.
            {caseId && <span className="ml-2 font-mono text-zinc-500">{caseId.slice(0, 8)}…</span>}
          </p>
        </div>
        <button onClick={() => void load()} disabled={loading}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl border border-zinc-700 hover:border-cyan-500/40 text-sm text-zinc-300 hover:text-white transition disabled:opacity-50">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
        </button>
      </div>

      {/* ── KG stats bar ── */}
      {summary && (
        <div className="px-6 py-3 border-b border-zinc-800 flex flex-wrap gap-6 text-xs text-zinc-400">
          <span className="flex items-center gap-1.5">
            <Network size={13} className="text-indigo-400" />
            <span className="font-bold text-white">{summary.nodes.toLocaleString()}</span> entities
          </span>
          <span className="flex items-center gap-1.5">
            <Share2 size={13} className="text-violet-400" />
            <span className="font-bold text-white">{summary.edges.toLocaleString()}</span> relationships
          </span>
          <span className="flex items-center gap-1.5">
            <Activity size={13} className="text-cyan-400" />
            <span className="font-bold text-white">{Object.keys(summary.entity_types).length}</span> entity types
          </span>
          {/* Distribution mini-bar */}
          <div className="flex items-center gap-2 flex-1 min-w-[160px]">
            <div className="h-2 flex-1 bg-zinc-800 rounded-full overflow-hidden flex">
              {typeEntries.slice(0, 5).map(([t, c], i) => (
                <div key={t} className={`h-full ${TOP_COLORS[i]}`}
                  style={{ width: `${(c / totalEnt) * 100}%` }} title={`${t}: ${c}`} />
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Error ── */}
      {error && (
        <div className="m-6 rounded-2xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300 flex items-start gap-3">
          <AlertTriangle size={16} className="shrink-0 mt-0.5 text-red-400" /> {error}
        </div>
      )}

      {/* ── Loading ── */}
      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <Loader2 size={36} className="animate-spin text-zinc-600" />
        </div>
      )}

      {/* ── Main grid ── */}
      {!loading && !error && (
        <div className="flex-1 flex overflow-hidden">

          {/* ── Left: Entities ── */}
          <div className="flex flex-col w-full lg:w-[55%] xl:w-[60%] border-r border-zinc-800 overflow-hidden">

            {/* Search + filter bar */}
            <div className="p-4 border-b border-zinc-800 flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                <input value={search} onChange={e => setSearch(e.target.value)}
                  placeholder="Search entities by name or description…"
                  className="w-full pl-9 pr-4 py-2 rounded-xl bg-zinc-900 border border-zinc-700 text-sm outline-none focus:border-indigo-500 transition placeholder:text-zinc-600" />
              </div>
              <div className="relative">
                <Filter size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" />
                <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}
                  className="pl-8 pr-4 py-2 rounded-xl bg-zinc-900 border border-zinc-700 text-sm outline-none text-white appearance-none cursor-pointer">
                  {allTypes.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
            </div>

            {/* Count */}
            <div className="px-4 py-2 text-xs text-zinc-500 border-b border-zinc-800">
              Showing <span className="font-semibold text-zinc-300">{filtered.length}</span> of {entities.length} entities
            </div>

            {/* Entity cards grid */}
            <div className="flex-1 overflow-y-auto p-4">
              {filtered.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-full text-center py-16 gap-3">
                  <FileSearch2 size={40} className="text-zinc-700" />
                  <p className="text-sm text-zinc-500">No entities match your filters.</p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                  {filtered.map((e, i) => {
                    const style   = typeStyle(e.type)
                    const name    = clean(e.name)
                    const type    = clean(e.type)
                    const desc    = clean(e.description)
                    const isActive = selected?.name === e.name
                    return (
                      <button key={i} onClick={() => setSelected(isActive ? null : e)}
                        className={`text-left rounded-xl border p-3.5 transition-all space-y-2 ${
                          isActive
                            ? 'border-indigo-500/60 bg-indigo-500/10 shadow-lg shadow-indigo-500/10'
                            : 'border-zinc-700/60 bg-zinc-900/60 hover:border-zinc-500/60 hover:bg-zinc-800/60'
                        }`}>
                        <div className="flex items-start justify-between gap-2">
                          <span className="text-sm font-semibold text-white leading-snug line-clamp-2">{name}</span>
                          {isActive && <X size={13} className="text-indigo-400 shrink-0 mt-0.5" />}
                        </div>
                        <span className={`inline-block text-[10px] font-mono px-2 py-0.5 rounded border ${style}`}>
                          {type || 'UNKNOWN'}
                        </span>
                        {desc && (
                          <p className="text-[11px] text-zinc-400 leading-relaxed line-clamp-2">{desc}</p>
                        )}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          </div>

          {/* ── Right: Detail + Relationships ── */}
          <div className="hidden lg:flex flex-col w-[45%] xl:w-[40%] overflow-hidden">

            {selected ? (
              <>
                {/* Entity detail */}
                <div className="p-5 border-b border-zinc-800 space-y-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-500 mb-1">Selected Entity</p>
                      <h2 className="text-lg font-bold leading-snug">{clean(selected.name)}</h2>
                    </div>
                    <button onClick={() => setSelected(null)}
                      className="p-1.5 rounded-lg text-zinc-500 hover:text-white hover:bg-white/5 transition">
                      <X size={16} />
                    </button>
                  </div>

                  <span className={`inline-block text-xs font-mono px-2.5 py-1 rounded border ${typeStyle(selected.type)}`}>
                    {clean(selected.type) || 'UNKNOWN'}
                  </span>

                  {clean(selected.description) ? (
                    <div className="bg-zinc-900/60 rounded-xl border border-zinc-700/50 p-3">
                      <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider mb-2">Description</p>
                      <p className="text-sm text-zinc-300 leading-6">{clean(selected.description)}</p>
                    </div>
                  ) : (
                    <p className="text-xs text-zinc-600 italic">No description available.</p>
                  )}

                  <div className="flex items-center gap-2 text-xs text-zinc-500">
                    <Share2 size={12} className="text-violet-400" />
                    <span><span className="font-semibold text-violet-300">{selectedRels.length}</span> connected relationships</span>
                  </div>
                </div>

                {/* Relationships for selected entity */}
                <div className="flex-1 overflow-y-auto p-4 space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3 flex items-center gap-2">
                    <Layers size={12} className="text-violet-400" /> Relationships
                  </p>
                  {selectedRels.length === 0 ? (
                    <p className="text-xs text-zinc-600 italic">No relationships found for this entity.</p>
                  ) : (
                    selectedRels.map((r, i) => {
                      const src   = clean(r.source)
                      const tgt   = clean(r.target)
                      const desc  = clean(r.description)
                      const isSource = src === clean(selected.name)
                      return (
                        <div key={i} className="rounded-xl bg-zinc-900/60 border border-zinc-700/50 p-3 space-y-1.5">
                          <div className="flex items-center gap-1.5 text-xs flex-wrap">
                            <span className={`font-semibold truncate max-w-[100px] ${isSource ? 'text-indigo-300' : 'text-zinc-300'}`}>
                              {src}
                            </span>
                            <ArrowRight size={11} className="text-zinc-500 shrink-0" />
                            <span className={`font-semibold truncate max-w-[100px] ${!isSource ? 'text-indigo-300' : 'text-zinc-300'}`}>
                              {tgt}
                            </span>
                            <span className="ml-auto text-[10px] font-mono text-zinc-500 shrink-0">
                              w:{Number(r.weight).toFixed(1)}
                            </span>
                          </div>
                          {desc && (
                            <p className="text-[11px] text-zinc-400 line-clamp-2 leading-relaxed">{desc}</p>
                          )}
                        </div>
                      )
                    })
                  )}
                </div>
              </>
            ) : (

              /* All relationships table when nothing selected */
              <div className="flex flex-col h-full overflow-hidden">
                <div className="p-5 border-b border-zinc-800">
                  <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-1 flex items-center gap-2">
                    <Link2 size={12} className="text-violet-400" /> All Relationships
                    <span className="font-bold text-violet-300">{rels.length}</span>
                  </p>
                  <p className="text-xs text-zinc-600">Click an entity card to see its connections.</p>
                </div>
                <div className="flex-1 overflow-y-auto p-4 space-y-2">
                  {rels.slice(0, 200).map((r, i) => (
                    <div key={i} className="rounded-xl bg-zinc-900/40 border border-zinc-800 p-3 space-y-1">
                      <div className="flex items-center gap-1.5 text-xs flex-wrap">
                        <span className="font-semibold text-zinc-300 truncate max-w-[110px]">{clean(r.source)}</span>
                        <ArrowRight size={10} className="text-zinc-600 shrink-0" />
                        <span className="font-semibold text-zinc-300 truncate max-w-[110px]">{clean(r.target)}</span>
                        <span className="ml-auto text-[10px] font-mono text-zinc-600 shrink-0">
                          w:{Number(r.weight).toFixed(1)}
                        </span>
                      </div>
                      {clean(r.description) && (
                        <p className="text-[11px] text-zinc-500 line-clamp-1">{clean(r.description)}</p>
                      )}
                    </div>
                  ))}
                  {rels.length > 200 && (
                    <p className="text-xs text-zinc-600 text-center pt-2">
                      Showing 200 of {rels.length} relationships. Use the Knowledge Graph page for full exploration.
                    </p>
                  )}
                </div>

                {/* Bottom shortcut */}
                <div className="p-4 border-t border-zinc-800">
                  <button onClick={() => navigate('/app/knowledge-graph')}
                    className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-xs font-semibold text-zinc-300 hover:text-white transition">
                    <Network size={14} className="text-purple-400" />
                    Open Interactive Graph Explorer
                  </button>
                  <button onClick={() => navigate('/app/reports')}
                    className="mt-2 w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-xs font-semibold text-zinc-300 hover:text-white transition">
                    <BookOpen size={14} className="text-indigo-400" />
                    Generate Compliance Report
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
