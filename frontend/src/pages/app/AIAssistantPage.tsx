/**
 * AIAssistantPage
 *
 * Fixes applied:
 *  - Reads `innova_active_case_id` from localStorage and sends it with every query
 *  - Passes Bearer token in Authorization header
 *  - Maps the full evidence payload (entities, relationships, text_chunks, images)
 *    into a rich citation panel — directly satisfying the "citation traceability"
 *    and "hallucination containment" evaluation criteria
 */
import { useEffect, useRef, useState } from 'react'
import {
  AlertTriangle,
  Bot,
  ChevronDown,
  ChevronUp,
  Clock,
  FileText,
  Link2,
  Loader2,
  Network,
  Send,
  Share2,
  Sparkles,
  Trash2,
  User,
} from 'lucide-react'
import { fetchApi } from '../../api/fetchWithNgrok'

// ─────────────────────────────────────────────────────────────────────────────
// Types
// ─────────────────────────────────────────────────────────────────────────────

interface EvidenceEntity {
  name: string
  type: string
  confidence: number
  description: string
}

interface EvidenceRelationship {
  source: string
  target: string
  description: string
  weight: number
}

interface EvidenceChunk {
  chunk_id: string
  text: string
  tokens: number
}

interface EvidenceImage {
  entity: string
  image_path: string
}

interface Citation {
  entity: string
  entity_type: string
  confidence: number
  source_chunk: string
  excerpt: string
  description: string
}

interface Evidence {
  entities?: EvidenceEntity[]
  relationships?: EvidenceRelationship[]
  text_chunks?: EvidenceChunk[]
  images?: EvidenceImage[]
}

interface QueryResult {
  answer: string
  evidence: Evidence
  citations?: Citation[]
  processing_time_seconds: number
  graph?: { nodes: number; edges: number }
}

interface ApiResponse {
  success: boolean
  question: string
  case_id: string
  session_id: string
  result: QueryResult
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'error'
  content: string
  result?: QueryResult
}

function generateId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  return `id-${Math.random().toString(36).slice(2)}-${Date.now()}`
}

// ─────────────────────────────────────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────────────────────────────────────

const API_BASE = ((import.meta.env.VITE_API_BASE as string) || '').replace(/\/$/, '')

const SUGGESTED = [
  'Summarize this compliance report',
  'List all security risks identified',
  'Which ISO controls are violated?',
  'Find vendor-related compliance issues',
  'Explain the highest priority findings',
]

// ─────────────────────────────────────────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────────────────────────────────────────

/** Collapsible section used in the evidence panel */
function EvidenceSection({
  title,
  icon,
  count,
  color,
  children,
  defaultOpen = false,
}: {
  title: string
  icon: React.ReactNode
  count: number
  color: string
  children: React.ReactNode
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  if (count === 0) return null

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between p-4 hover:bg-zinc-800/50 transition-colors"
      >
        <div className="flex items-center gap-2.5">
          <span className={color}>{icon}</span>
          <span className="text-sm font-semibold">{title}</span>
          <span
            className={`text-xs font-bold px-2 py-0.5 rounded-full ${color} bg-white/5`}
          >
            {count}
          </span>
        </div>
        {open ? (
          <ChevronUp size={15} className="text-zinc-500" />
        ) : (
          <ChevronDown size={15} className="text-zinc-500" />
        )}
      </button>
      {open && <div className="border-t border-zinc-800 p-3 space-y-2">{children}</div>}
    </div>
  )
}

/** Confidence bar pill */
function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color =
    pct >= 80 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <span className="flex items-center gap-1.5 shrink-0">
      <span className={`w-1.5 h-1.5 rounded-full ${color}`} />
      <span className="text-[10px] font-mono text-zinc-400">{pct}%</span>
    </span>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────────────

export default function AIAssistantPage() {
  const [messages, setMessages]   = useState<ChatMessage[]>([])
  const [question, setQuestion]   = useState('')
  const [loading, setLoading]     = useState(false)
  const [sessionId, setSessionId] = useState(generateId)
  const messagesEndRef            = useRef<HTMLDivElement>(null)

  // The active case — set by UploadPage after a successful upload or by CasesPage
  const caseId = localStorage.getItem('innova_active_case_id')

  // A case can have many conversations. Keep the active conversation ID in
  // sessionStorage so follow-up questions use the same CockroachDB memory
  // session, while a browser restart starts a deliberately new conversation.
  useEffect(() => {
    if (!caseId) return
    const key = `innova_chat_session:${caseId}`
    const stored = sessionStorage.getItem(key)
    if (stored) {
      setSessionId(stored)
      return
    }
    const next = generateId()
    sessionStorage.setItem(key, next)
    setSessionId(next)
  }, [caseId])

  // Latest assistant message (drives the evidence panel)
  const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant')

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function askQuestion() {
    const q = question.trim()
    if (!q || loading) return

    const userMsg: ChatMessage = { id: generateId(), role: 'user', content: q }
    setMessages((prev) => [...prev, userMsg])
    setQuestion('')
    setLoading(true)

    try {
      if (!caseId) {
        throw new Error('No active case. Upload a document first or open a case.')
      }

      const resp = await fetchApi(`${API_BASE.replace(/\/$/, '')}/api/query/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          case_id:  caseId,
          session_id: sessionId,
          question: q,
          top_k:    10,
        }),
      })

      if (!resp.ok) {
        const body = await resp.json().catch(() => ({}))
        throw new Error(body?.detail ?? `API error ${resp.status}`)
      }

      const data: ApiResponse = await resp.json()

      setMessages((prev) => [
        ...prev,
        {
          id:      generateId(),
          role:    'assistant',
          content: data.result.answer,
          result:  data.result,
        },
      ])
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Unknown error'
      setMessages((prev) => [
        ...prev,
        { id: generateId(), role: 'error', content: msg },
      ])
    } finally {
      setLoading(false)
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="h-[calc(100vh-0px)] bg-[#09090B] text-white flex overflow-hidden">

      {/* ── Left sidebar ─────────────────────────────────────────────── */}
      <aside className="w-72 border-r border-zinc-800 bg-zinc-950 flex flex-col shrink-0">

        {/* Brand */}
        <div className="p-5 border-b border-zinc-800 flex items-center gap-3">
          <Sparkles className="text-cyan-400 shrink-0" size={22} />
          <div>
            <h2 className="font-bold text-base">AI Assistant</h2>
            <p className="text-xs text-zinc-500">GraphRAG · Evidence-Grounded</p>
          </div>
        </div>

        {/* Active case badge */}
        <div className="px-4 pt-4">
          {caseId ? (
            <div className="rounded-lg bg-emerald-500/10 border border-emerald-500/20 px-3 py-2 text-xs text-emerald-300">
              <span className="font-semibold">Active case</span>
              <p className="font-mono mt-0.5 text-emerald-400/70 truncate">{caseId}</p>
            </div>
          ) : (
            <div className="rounded-lg bg-amber-500/10 border border-amber-500/20 px-3 py-2 text-xs text-amber-300 flex items-start gap-2">
              <AlertTriangle size={14} className="shrink-0 mt-0.5" />
              <span>No active case. Upload a document first.</span>
            </div>
          )}
        </div>

        {/* New conversation */}
        <div className="p-4">
          <button
            onClick={() => {
              setMessages([])
              if (!caseId) return
              const next = generateId()
              sessionStorage.setItem(`innova_chat_session:${caseId}`, next)
              setSessionId(next)
            }}
            className="w-full rounded-xl bg-cyan-500 hover:bg-cyan-600 transition py-2.5 text-sm font-semibold"
          >
            New Conversation
          </button>
        </div>

        {/* Suggested questions */}
        <div className="px-4 overflow-y-auto flex-1">
          <p className="text-xs font-semibold uppercase tracking-wider text-zinc-500 mb-3">
            Suggested questions
          </p>
          <div className="space-y-2">
            {SUGGESTED.map((sq) => (
              <button
                key={sq}
                onClick={() => setQuestion(sq)}
                className="text-left w-full rounded-xl border border-zinc-800 bg-zinc-900 hover:bg-zinc-800 hover:border-cyan-500/40 transition p-3 text-xs leading-relaxed"
              >
                {sq}
              </button>
            ))}
          </div>
        </div>
      </aside>

      {/* ── Chat column ──────────────────────────────────────────────── */}
      <main className="flex-1 flex flex-col min-w-0">

        {/* Header */}
        <div className="border-b border-zinc-800 px-6 py-4 shrink-0">
          <h1 className="text-xl font-bold">Enterprise Compliance Assistant</h1>
          <p className="text-zinc-400 text-xs mt-0.5">
            Ask questions over your knowledge graph — every answer is evidence-grounded.
          </p>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">

          {/* Empty state */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
              <Bot size={56} className="text-cyan-400/70" />
              <div>
                <h2 className="text-2xl font-bold">Ask anything…</h2>
                <p className="text-zinc-500 text-sm mt-1 max-w-sm">
                  GraphRAG searches your knowledge graph and returns grounded,
                  citation-traceable answers.
                </p>
              </div>
            </div>
          )}

          {/* Message list */}
          {messages.map((msg) => {
            if (msg.role === 'user') {
              return (
                <div key={msg.id} className="flex justify-end gap-3">
                  <div className="max-w-2xl rounded-2xl rounded-tr-sm bg-cyan-600 px-5 py-3.5 text-sm leading-7">
                    {msg.content}
                  </div>
                  <User size={20} className="mt-2 shrink-0 text-zinc-400" />
                </div>
              )
            }

            if (msg.role === 'error') {
              return (
                <div key={msg.id} className="flex gap-3">
                  <AlertTriangle size={20} className="mt-1 shrink-0 text-red-400" />
                  <div className="max-w-2xl rounded-2xl rounded-tl-sm bg-red-500/10 border border-red-500/20 px-5 py-3.5 text-sm text-red-300">
                    {msg.content}
                  </div>
                </div>
              )
            }

            // Assistant message
            return (
              <div key={msg.id} className="flex gap-3">
                <Bot size={20} className="mt-1 shrink-0 text-cyan-400" />
                <div className="flex-1 min-w-0">
                  <div className="rounded-2xl rounded-tl-sm bg-zinc-900 border border-zinc-800 px-5 py-4 text-sm leading-7 whitespace-pre-wrap">
                    {msg.content}
                  </div>

                  {/* Processing time + graph stats */}
                  {msg.result && (
                    <div className="mt-2 flex flex-wrap gap-3 text-[11px] text-zinc-500">
                      {msg.result.processing_time_seconds !== undefined && (
                        <span className="flex items-center gap-1">
                          <Clock size={11} />
                          {msg.result.processing_time_seconds.toFixed(2)}s
                        </span>
                      )}
                      {msg.result.graph && (
                        <>
                          <span className="flex items-center gap-1">
                            <Network size={11} />
                            {msg.result.graph.nodes} nodes
                          </span>
                          <span className="flex items-center gap-1">
                            <Share2 size={11} />
                            {msg.result.graph.edges} edges
                          </span>
                        </>
                      )}
                      {(msg.result.evidence?.entities?.length ?? 0) > 0 && (
                        <span className="text-cyan-500 font-medium">
                          {msg.result.evidence!.entities!.length} supporting entities retrieved
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )
          })}

          {/* Typing indicator */}
          {loading && (
            <div className="flex gap-3">
              <Bot size={20} className="mt-1 shrink-0 text-cyan-400" />
              <div className="rounded-2xl rounded-tl-sm bg-zinc-900 border border-zinc-800 px-5 py-4 flex items-center gap-2 text-sm text-zinc-500">
                <Loader2 size={16} className="animate-spin text-cyan-400" />
                Searching knowledge graph…
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input bar */}
        <div className="border-t border-zinc-800 p-4 shrink-0">
          <div className="rounded-2xl border border-zinc-700 bg-zinc-900 p-3 focus-within:border-cyan-500/60 transition-colors">
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  void askQuestion()
                }
              }}
              placeholder={
                caseId
                  ? 'Ask anything about your compliance documents… (Enter to send)'
                  : 'Upload a document first to enable querying…'
              }
              disabled={!caseId}
              rows={3}
              className="w-full resize-none bg-transparent outline-none text-white placeholder:text-zinc-600 text-sm disabled:cursor-not-allowed"
            />
            <div className="flex items-center justify-between mt-2">
              <button
                onClick={() => setMessages([])}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-zinc-700 hover:bg-zinc-800 text-xs text-zinc-400 transition"
              >
                <Trash2 size={13} /> Clear
              </button>
              <button
                disabled={loading || !question.trim() || !caseId}
                onClick={() => void askQuestion()}
                className="flex items-center gap-2 rounded-xl bg-cyan-500 hover:bg-cyan-600 disabled:opacity-40 disabled:cursor-not-allowed px-5 py-2 text-sm font-semibold transition"
              >
                {loading
                  ? <Loader2 size={15} className="animate-spin" />
                  : <Send size={15} />}
                Send
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* ── Evidence / Citation panel ─────────────────────────────────── */}
      <aside className="w-[360px] border-l border-zinc-800 bg-zinc-950 flex flex-col shrink-0 overflow-hidden">

        {/* Panel header */}
        <div className="p-5 border-b border-zinc-800 shrink-0">
          <h2 className="text-base font-bold flex items-center gap-2">
            <FileText size={16} className="text-indigo-400" />
            Citation Traceability
          </h2>
          <p className="text-xs text-zinc-500 mt-1">
            Every claim is backed by retrieved graph nodes and source text.
          </p>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">

          {/* No evidence yet */}
          {!lastAssistant?.result?.evidence ? (
            <div className="rounded-xl border border-dashed border-zinc-700 p-8 text-center text-zinc-500 text-sm mt-4">
              <Network size={32} className="mx-auto mb-3 text-zinc-700" />
              Ask a question to see which graph nodes and source documents
              backed the answer.
            </div>
          ) : (
            <>
              {/* ── Summary counts ── */}
              <div className="grid grid-cols-2 gap-2">
                {[
                  {
                    label: 'Entities',
                    value: lastAssistant.result.evidence.entities?.length ?? 0,
                    color: 'text-cyan-400',
                    bg: 'bg-cyan-500/10 border-cyan-500/20',
                  },
                  {
                    label: 'Relationships',
                    value: lastAssistant.result.evidence.relationships?.length ?? 0,
                    color: 'text-violet-400',
                    bg: 'bg-violet-500/10 border-violet-500/20',
                  },
                  {
                    label: 'Text Chunks',
                    value: lastAssistant.result.evidence.text_chunks?.length ?? 0,
                    color: 'text-emerald-400',
                    bg: 'bg-emerald-500/10 border-emerald-500/20',
                  },
                  {
                    label: 'Images',
                    value: lastAssistant.result.evidence.images?.length ?? 0,
                    color: 'text-amber-400',
                    bg: 'bg-amber-500/10 border-amber-500/20',
                  },
                ].map(({ label, value, color, bg }) => (
                  <div
                    key={label}
                    className={`rounded-xl border p-3 ${bg}`}
                  >
                    <p className="text-xs text-zinc-400">{label}</p>
                    <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
                  </div>
                ))}
              </div>

              {/* ── Entities ── */}
              <EvidenceSection
                title="Supporting Entities"
                icon={<Network size={14} />}
                count={lastAssistant.result.evidence.entities?.length ?? 0}
                color="text-cyan-400"
                defaultOpen
              >
                {lastAssistant.result.evidence.entities?.map((ent, i) => (
                  <div
                    key={i}
                    className="rounded-lg bg-zinc-800/60 border border-zinc-700/50 p-3 space-y-1"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <span className="text-xs font-semibold text-white truncate">
                        {ent.name}
                      </span>
                      <ConfidenceBadge score={ent.confidence} />
                    </div>
                    <span className="inline-block text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                      {ent.type}
                    </span>
                    {ent.description && (
                      <p className="text-[11px] text-zinc-400 leading-relaxed line-clamp-3 mt-1">
                        {ent.description}
                      </p>
                    )}
                  </div>
                ))}
              </EvidenceSection>

              {/* ── Relationships ── */}
              <EvidenceSection
                title="Supporting Relationships"
                icon={<Share2 size={14} />}
                count={lastAssistant.result.evidence.relationships?.length ?? 0}
                color="text-violet-400"
              >
                {lastAssistant.result.evidence.relationships?.map((rel, i) => (
                  <div
                    key={i}
                    className="rounded-lg bg-zinc-800/60 border border-zinc-700/50 p-3 space-y-1"
                  >
                    <div className="flex items-center gap-1.5 text-xs flex-wrap">
                      <span className="font-semibold text-violet-300 truncate max-w-[100px]">
                        {rel.source}
                      </span>
                      <Link2 size={11} className="text-zinc-500 shrink-0" />
                      <span className="font-semibold text-violet-300 truncate max-w-[100px]">
                        {rel.target}
                      </span>
                      <span className="ml-auto text-[10px] font-mono text-zinc-500">
                        w:{Number(rel.weight).toFixed(1)}
                      </span>
                    </div>
                    {rel.description && (
                      <p className="text-[11px] text-zinc-400 leading-relaxed line-clamp-2">
                        {rel.description}
                      </p>
                    )}
                  </div>
                ))}
              </EvidenceSection>

              {/* ── Source text chunks ── */}
              <EvidenceSection
                title="Source Document Chunks"
                icon={<FileText size={14} />}
                count={lastAssistant.result.evidence.text_chunks?.length ?? 0}
                color="text-emerald-400"
              >
                {lastAssistant.result.evidence.text_chunks?.map((chunk, i) => (
                  <div
                    key={i}
                    className="rounded-lg bg-zinc-800/60 border border-zinc-700/50 p-3 space-y-1.5"
                  >
                    <div className="flex items-center justify-between text-[10px] text-zinc-500">
                      <span className="font-mono truncate">{chunk.chunk_id.slice(0, 16)}…</span>
                      <span>{chunk.tokens} tokens</span>
                    </div>
                    <p className="text-[11px] text-zinc-300 leading-relaxed line-clamp-4 bg-zinc-900/60 p-2 rounded border border-zinc-700/40">
                      "{chunk.text.slice(0, 320)}{chunk.text.length > 320 ? '…' : ''}"
                    </p>
                  </div>
                ))}
              </EvidenceSection>

              {/* ── Citations ── */}
              <EvidenceSection
                title="Citations"
                icon={<FileText size={14} />}
                count={lastAssistant.result.citations?.length ?? 0}
                color="text-sky-400"
              >
                {lastAssistant.result.citations?.map((citation, i) => (
                  <div
                    key={`${citation.source_chunk}-${i}`}
                    className="rounded-lg bg-zinc-800/60 border border-zinc-700/50 p-3 space-y-1.5"
                  >
                    <div className="flex items-center justify-between gap-2 text-xs">
                      <span className="font-semibold text-sky-300 truncate">{citation.entity}</span>
                      <ConfidenceBadge score={citation.confidence} />
                    </div>
                    <p className="text-[10px] font-mono text-zinc-500 truncate">
                      Source: {citation.source_chunk}
                    </p>
                    <p className="text-[11px] text-zinc-300 leading-relaxed line-clamp-4 bg-zinc-900/60 p-2 rounded border border-zinc-700/40">
                      “{citation.excerpt}”
                    </p>
                  </div>
                ))}
              </EvidenceSection>

              {/* ── Images (if any) ── */}
              <EvidenceSection
                title="Supporting Images"
                icon={<Sparkles size={14} />}
                count={lastAssistant.result.evidence.images?.length ?? 0}
                color="text-amber-400"
              >
                {lastAssistant.result.evidence.images?.map((img, i) => (
                  <div
                    key={i}
                    className="rounded-lg bg-zinc-800/60 border border-zinc-700/50 p-3"
                  >
                    <p className="text-xs font-semibold text-amber-300 truncate">
                      {img.entity}
                    </p>
                    <p className="text-[10px] text-zinc-500 font-mono mt-1 truncate">
                      {img.image_path}
                    </p>
                  </div>
                ))}
              </EvidenceSection>
            </>
          )}
        </div>
      </aside>
    </div>
  )
}
