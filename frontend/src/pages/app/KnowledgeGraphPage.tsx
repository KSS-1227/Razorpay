import { useCallback, useEffect, useMemo, useState, type MouseEvent, type ReactNode } from 'react'
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  useEdgesState,
  useNodesState,
  type Edge,
  type Node,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { AlertTriangle, Database, Network, RefreshCw, Search, Share2, X } from 'lucide-react'
import { useAuth } from '../../auth/AuthContext'
import { fetchApi } from '../../api/fetchWithNgrok'

// ─────────────────────────────────────────────────────────────────────────────
// Types matching the /api/graph/network response
// ─────────────────────────────────────────────────────────────────────────────

interface NetworkEntity {
  id: string
  label: string
  type: string
  description: string
}

interface NetworkRelationship {
  id: string
  source: string
  target: string
  weight?: number
  description?: string
}

interface NetworkPayload {
  case_id: string
  nodes: NetworkEntity[]
  edges: NetworkRelationship[]
  meta: {
    total_nodes: number
    total_edges: number
    returned_nodes: number
    returned_edges: number
  }
}

interface GraphNodeData extends Record<string, unknown> {
  label: string
  entityType: string
  description: string
}

// ─────────────────────────────────────────────────────────────────────────────
// Colour palette by entity type
// ─────────────────────────────────────────────────────────────────────────────

const TYPE_COLORS: Record<string, string> = {
  ORG: '#f59e0b',
  ORGANIZATION: '#f59e0b',
  PERSON: '#ec4899',
  POLICY: '#a855f7',
  REGULATION: '#a855f7',
  CONTROL: '#06b6d4',
  IMG: '#22c55e',
  ORI_IMG: '#22c55e',
  IMG_ENTITY: '#22c55e',
  EVENT: '#34d399',
  TECHNOLOGY: '#60a5fa',
  GEO: '#818cf8',
  CONCEPT: '#fb923c',
  RISK: '#f87171',
  REQUIREMENT: '#38bdf8',
}

const typeColor = (entityType: string) =>
  TYPE_COLORS[entityType.replace(/"/g, '').trim().toUpperCase()] ?? '#94a3b8'

// ─────────────────────────────────────────────────────────────────────────────
// ReactFlow builders
// ─────────────────────────────────────────────────────────────────────────────

function buildFlowNodes(entities: NetworkEntity[]): Node<GraphNodeData>[] {
  const count  = entities.length
  const radius = Math.max(320, count * 15)

  return entities.map((entity, index) => {
    const angle      = (index / Math.max(count, 1)) * Math.PI * 2
    const entityType = entity.type.replace(/"/g, '').trim() || 'UNKNOWN'
    const color      = typeColor(entityType)

    return {
      id: entity.id,
      position: {
        x: Math.cos(angle) * radius + radius,
        y: Math.sin(angle) * radius + radius,
      },
      data: { label: entity.label, entityType, description: entity.description },
      style: {
        background: '#18181b',
        border: `1px solid ${color}`,
        borderRadius: 12,
        boxShadow: `0 0 18px ${color}28`,
        color: '#f4f4f5',
        fontSize: 12,
        fontWeight: 600,
        maxWidth: 190,
        padding: '10px 14px',
      },
    }
  })
}

function buildFlowEdges(relationships: NetworkRelationship[]): Edge[] {
  return relationships.map((rel) => ({
    id:            rel.id,
    source:        rel.source,
    target:        rel.target,
    label:         rel.description || undefined,
    animated:      Boolean(rel.weight && rel.weight > 1),
    style:         { stroke: '#3f3f46', strokeWidth: Math.min(Number(rel.weight) || 1, 3) },
    labelStyle:    { fill: '#a1a1aa', fontSize: 10 },
    labelBgStyle:  { fill: '#09090b', fillOpacity: 0.85 },
  }))
}

// ─────────────────────────────────────────────────────────────────────────────
// Component
// ─────────────────────────────────────────────────────────────────────────────

export default function KnowledgeGraphPage() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node<GraphNodeData>>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [search,       setSearch]       = useState('')
  const [selectedType, setSelectedType] = useState('ALL')
  const [selectedNode, setSelectedNode] = useState<Node<GraphNodeData> | null>(null)
  const [loading,      setLoading]      = useState(true)
  const [error,        setError]        = useState<string | null>(null)
  const [meta,         setMeta]         = useState<NetworkPayload['meta'] | null>(null)

  const { isLoading: authLoading } = useAuth()

  // ── Resolve case_id from localStorage (set by UploadPage / CasesPage) ─────
  const caseId = localStorage.getItem('innova_active_case_id')

  const loadGraph = useCallback(async () => {
    if (!caseId) {
      setError('No active case selected. Upload a document or open a case first.')
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)

    try {
      const apiBase = ((import.meta.env.VITE_API_BASE as string) || '').replace(/\/$/, '')

      // Check case status before hitting the graph endpoint
      const caseResp = await fetchApi(`${apiBase}/api/cases/${caseId}`)
      if (caseResp.ok) {
        const caseData = await caseResp.json() as { status?: string }
        if (caseData.status === 'processing') {
          setError('Document is still being processed. Check back in a moment.')
          setLoading(false)
          return
        }
        if (caseData.status === 'failed') {
          setError('Document processing failed. Re-upload the document to rebuild the graph.')
          setLoading(false)
          return
        }
      }

      const response = await fetchApi(`${apiBase}/api/graph/network?case_id=${encodeURIComponent(caseId)}`)

      if (!response.ok) {
        const body = await response.json().catch(() => ({}))
        throw new Error(body?.detail ?? `API error ${response.status}`)
      }

      const payload = (await response.json()) as NetworkPayload
      setNodes(buildFlowNodes(payload.nodes ?? []))
      setEdges(buildFlowEdges(payload.edges ?? []))
      setMeta(payload.meta ?? null)
      setSelectedNode(null)
    } catch (err) {
      console.error('[KnowledgeGraph] loadGraph failed:', err)
      setError(err instanceof Error ? err.message : 'Unable to load graph')
    } finally {
      setLoading(false)
    }
  }, [caseId, setEdges, setNodes])

  useEffect(() => {
    if (authLoading) return   // wait for token before fetching
    void loadGraph()
  }, [loadGraph, authLoading])

  // ── Filter helpers ────────────────────────────────────────────────────────

  const entityTypes = useMemo(
    () => ['ALL', ...Array.from(new Set(nodes.map((n) => n.data.entityType))).sort()],
    [nodes],
  )

  const visibleNodeIds = useMemo(() => {
    const q = search.trim().toLowerCase()
    return new Set(
      nodes
        .filter((n) =>
          (selectedType === 'ALL' || n.data.entityType === selectedType) &&
          n.data.label.toLowerCase().includes(q),
        )
        .map((n) => n.id),
    )
  }, [nodes, search, selectedType])

  const filteredNodes = useMemo(
    () => nodes.map((n) => ({ ...n, hidden: !visibleNodeIds.has(n.id) })),
    [nodes, visibleNodeIds],
  )
  const filteredEdges = useMemo(
    () => edges.map((e) => ({
      ...e,
      hidden: !visibleNodeIds.has(e.source) || !visibleNodeIds.has(e.target),
    })),
    [edges, visibleNodeIds],
  )

  const onNodeClick = useCallback((_: MouseEvent, node: Node<GraphNodeData>) => {
    setSelectedNode(node)
  }, [])

  const selectedColor = selectedNode ? typeColor(selectedNode.data.entityType) : '#94a3b8'

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-full bg-[#09090b] px-5 py-6 text-white sm:px-8">

      {/* Header */}
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-cyan-400">
            Intelligence map
          </p>
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Knowledge Graph</h1>
          <p className="mt-2 text-sm text-zinc-400">
            Explore entities and the relationships connecting them.
            {caseId && (
              <span className="ml-2 rounded-full bg-zinc-800 px-2 py-0.5 text-xs font-mono text-zinc-400">
                case: {caseId.slice(0, 8)}…
              </span>
            )}
          </p>
        </div>
        <button
          onClick={() => void loadGraph()}
          disabled={loading}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-cyan-400/30 bg-cyan-400/10 px-4 py-2.5 text-sm font-medium text-cyan-300 transition hover:bg-cyan-400/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          Refresh graph
        </button>
      </div>

      {/* Stats */}
      <div className="mb-5 grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Stat icon={<Database size={17} />} label="Entities"      value={meta?.total_nodes ?? nodes.length}  color="text-cyan-400" />
        <Stat icon={<Share2   size={17} />} label="Relationships" value={meta?.total_edges ?? edges.length}  color="text-violet-400" />
        <Stat icon={<Network  size={17} />} label="Entity types"  value={Math.max(entityTypes.length - 1, 0)} color="text-emerald-400" />
      </div>

      {/* Filters */}
      <div className="mb-5 flex flex-col gap-3 sm:flex-row">
        <label className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" size={17} />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full rounded-xl border border-white/10 bg-zinc-950/70 py-2.5 pl-10 pr-4 text-sm text-white outline-none ring-0"
            placeholder="Filter by entity label…"
          />
        </label>
        <select
          value={selectedType}
          onChange={(e) => setSelectedType(e.target.value)}
          className="rounded-xl border border-white/10 bg-zinc-950/70 px-4 py-2.5 text-sm text-white outline-none"
        >
          {entityTypes.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>

      {/* No case selected */}
      {!caseId && !loading && (
        <div className="rounded-2xl border border-amber-400/30 bg-amber-400/10 p-5 text-sm text-amber-200 flex items-start gap-3">
          <AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-400" />
          <span>
            No active case found. Go to <strong>Upload</strong> to ingest a document or open a
            case from the <strong>Cases</strong> page.
          </span>
        </div>
      )}

      {/* Error */}
      {error && caseId && (
        <div className="rounded-2xl border border-red-400/30 bg-red-400/10 p-5 text-sm text-red-200">
          {error}. Confirm the API is running and a graph has been built for this case.
        </div>
      )}

      {/* Graph canvas */}
      {!error && (
        <div className="flex min-h-[620px] overflow-hidden rounded-2xl border border-white/10 bg-[#111116] shadow-2xl shadow-black/30">
          <div className="relative min-h-[620px] flex-1">
            {loading && (
              <div className="absolute inset-0 z-10 grid place-items-center bg-[#111116]/80 text-sm text-zinc-400">
                <RefreshCw className="mr-2 inline animate-spin" size={18} /> Loading graph…
              </div>
            )}
            {!loading && filteredNodes.length === 0 && (
              <div className="absolute inset-0 z-10 grid place-items-center text-sm text-zinc-500">
                No entities match the current filters.
              </div>
            )}
            <ReactFlow
              nodes={filteredNodes}
              edges={filteredEdges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onNodeClick={onNodeClick}
              fitView
              fitViewOptions={{ padding: 0.2 }}
              minZoom={0.1}
              className="bg-[#111116]"
              defaultEdgeOptions={{ type: 'smoothstep' }}
            >
              <Background color="#27272a" gap={22} size={1} />
              <Controls className="!border-zinc-700 !bg-zinc-900 !fill-zinc-300" />
              <MiniMap
                nodeColor={(node) => typeColor((node.data as GraphNodeData).entityType)}
                maskColor="rgba(9, 9, 11, 0.75)"
                className="!border-zinc-700 !bg-zinc-900"
              />
            </ReactFlow>
          </div>

          {/* Entity detail panel */}
          <aside className="hidden w-80 shrink-0 border-l border-white/10 bg-zinc-950/75 p-5 lg:block">
            {selectedNode ? (
              <div className="flex h-full flex-col">
                <div className="mb-6 flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.18em] text-zinc-500">
                      Entity details
                    </p>
                    <h2 className="mt-2 break-words text-xl font-semibold leading-snug">
                      {selectedNode.data.label}
                    </h2>
                  </div>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="rounded-lg p-1 text-zinc-500 transition hover:bg-white/5 hover:text-white"
                    aria-label="Close details panel"
                  >
                    <X size={18} />
                  </button>
                </div>

                <span
                  className="mb-6 w-fit rounded-full border px-2.5 py-1 text-xs font-semibold"
                  style={{
                    borderColor:     `${selectedColor}80`,
                    backgroundColor: `${selectedColor}18`,
                    color:           selectedColor,
                  }}
                >
                  {selectedNode.data.entityType}
                </span>

                <div className="border-t border-white/10 pt-5">
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-zinc-500">
                    Description
                  </p>
                  <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-zinc-300">
                    {selectedNode.data.description || 'No description available for this entity.'}
                  </p>
                </div>

                {/* Neighbouring edges count */}
                <div className="mt-auto border-t border-white/10 pt-4">
                  <p className="text-xs text-zinc-500">
                    Connected relationships:{' '}
                    <span className="font-semibold text-violet-400">
                      {edges.filter(
                        (e) => e.source === selectedNode.id || e.target === selectedNode.id,
                      ).length}
                    </span>
                  </p>
                </div>
              </div>
            ) : (
              <div className="grid h-full place-items-center text-center">
                <div>
                  <Network className="mx-auto mb-3 text-cyan-400/70" size={30} />
                  <p className="text-sm font-medium text-zinc-300">Select an entity</p>
                  <p className="mt-1 text-xs leading-5 text-zinc-500">
                    Click a node to view its type and description.
                  </p>
                </div>
              </div>
            )}
          </aside>
        </div>
      )}

      {/* Truncation notice */}
      {meta && meta.total_nodes > meta.returned_nodes && (
        <p className="mt-3 text-xs text-zinc-500 text-right">
          Showing {meta.returned_nodes} of {meta.total_nodes} nodes (graph capped at 500 for performance).
        </p>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Stat card
// ─────────────────────────────────────────────────────────────────────────────

function Stat({
  icon,
  label,
  value,
  color,
}: {
  icon: ReactNode
  label: string
  value: number
  color: string
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl border border-white/10 bg-zinc-950/70 px-4 py-3">
      <span className={color}>{icon}</span>
      <div>
        <p className="text-xs text-zinc-500">{label}</p>
        <p className="mt-0.5 text-xl font-semibold">{value}</p>
      </div>
    </div>
  )
}
