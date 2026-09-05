/**
 * CompliancePage — Enterprise Compliance Intelligence Platform
 *
 * Consumes workspace-scoped compliance endpoints:
 * 1. Reconciliation (POST /api/workspace/{case_id}/reconcile)
 * 2. Tax Matching (POST /api/workspace/{case_id}/tax-match)
 * 3. Settlement Q&A (POST /api/workspace/{case_id}/settlement-qa)
 * 4. Cash Forecast (POST /api/workspace/{case_id}/forecast)
 *
 * Cross-cutting:
 * - Scoped to active case_id / workspaceId
 * - Independent loading state per section
 * - 404 empty state vs 500 error state handling
 * - No fake mock zeroes / hardcoded values
 */
import { useEffect, useMemo, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  AlertCircle,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Clock,
  FileCheck2,
  FileText,
  HelpCircle,
  Info,
  Loader2,
  Percent,
  RefreshCw,
  Scale,
  Send,
  ShieldAlert,
  Sparkles,
  TrendingUp,
  Upload,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import {
  getCashflow,
  getForecast,
  runReconciliation,
  runTaxMatch,
  sendSettlementQA,
  type CashflowResponse,
  type ForecastResponse,
  type ReconcileResponse,
  type ReconcileResultRow,
  type SettlementQAResponse,
  type TaxMatchResponse,
  type TaxMatchResultRow,
} from '../../api/complianceApi'

// ── Types ─────────────────────────────────────────────────────────────────────

type SectionTab = 'reconciliation' | 'tax-match' | 'settlement-qa' | 'forecast'

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatCurrency(val: number | null | undefined): string {
  if (val == null) return '—'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits: 0,
  }).format(val)
}

function StatusBadge({ status }: { status: 'matched' | 'exception' | 'unresolved' }) {
  if (status === 'matched') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
        <CheckCircle2 size={12} />
        Matched
      </span>
    )
  }
  if (status === 'exception') {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
        <AlertTriangle size={12} />
        Exception
      </span>
    )
  }
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
      <HelpCircle size={12} />
      Unresolved
    </span>
  )
}

// ── Section Card Shell ────────────────────────────────────────────────────────

function SectionContainer({
  title,
  description,
  icon: Icon,
  action,
  children,
}: {
  title: string
  description: string
  icon: React.ElementType
  action?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-900/70 backdrop-blur-xl p-6 shadow-xl">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-zinc-800/80">
        <div className="flex items-start gap-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 shrink-0">
            <Icon size={22} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-zinc-100 tracking-tight">{title}</h2>
            <p className="text-xs text-zinc-400 mt-0.5">{description}</p>
          </div>
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
      {children}
    </div>
  )
}

// ── Empty / No Case State ─────────────────────────────────────────────────────

function CaseEmptyState({ caseId }: { caseId: string | null }) {
  const navigate = useNavigate()
  return (
    <div className="rounded-2xl border border-dashed border-zinc-800 bg-zinc-900/40 p-12 text-center max-w-xl mx-auto my-12">
      <div className="w-14 h-14 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 flex items-center justify-center mx-auto mb-4">
        <Scale size={28} />
      </div>
      <h3 className="text-xl font-bold text-zinc-200">
        {!caseId ? 'No Active Case Selected' : 'No Graph Documents Processed Yet'}
      </h3>
      <p className="text-sm text-zinc-400 mt-2 leading-relaxed">
        {!caseId
          ? 'Select a workspace case to run compliance audit, tax matching, settlement Q&A, and cash forecasting.'
          : `Workspace "${caseId}" does not have processed knowledge graph documents yet. Upload invoices, contracts, or tax schedules to begin.`}
      </p>
      <div className="flex items-center justify-center gap-3 mt-6">
        {!caseId ? (
          <button
            onClick={() => navigate('/app/cases')}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition shadow-lg shadow-indigo-500/20 flex items-center gap-2"
          >
            Select Case
            <ArrowRight size={16} />
          </button>
        ) : (
          <button
            onClick={() => navigate('/app/upload')}
            className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-semibold transition shadow-lg shadow-indigo-500/20 flex items-center gap-2"
          >
            <Upload size={16} />
            Upload Documents
          </button>
        )}
      </div>
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────
// MAIN COMPONENT
// ─────────────────────────────────────────────────────────────────────────────

export default function CompliancePage() {
  const navigate = useNavigate()
  const { workspaceId, isLoading: authLoading } = useAuth()
  const activeCaseId = localStorage.getItem('innova_active_case_id') || workspaceId

  const [activeTab, setActiveTab] = useState<SectionTab>('reconciliation')

  // Section 1: Reconciliation State
  const [reconcileData, setReconcileData] = useState<ReconcileResponse | null>(null)
  const [loadingReconcile, setLoadingReconcile] = useState(false)
  const [reconcileError, setReconcileError] = useState<{ message: string; is404: boolean } | null>(null)
  const [reconcileFilter, setReconcileFilter] = useState<'all' | 'exceptions'>('all')

  // Section 2: Tax Matching State
  const [taxData, setTaxData] = useState<TaxMatchResponse | null>(null)
  const [loadingTax, setLoadingTax] = useState(false)
  const [taxError, setTaxError] = useState<{ message: string; is404: boolean } | null>(null)
  const [taxFilter, setTaxFilter] = useState<'all' | 'exceptions'>('all')

  // Section 3: Settlement Q&A State
  const [question, setQuestion] = useState('')
  const [loadingQA, setLoadingQA] = useState(false)
  const [qaResponse, setQAResponse] = useState<SettlementQAResponse | null>(null)
  const [qaError, setQAError] = useState<{ message: string; is404: boolean } | null>(null)
  const [evidenceOpen, setEvidenceOpen] = useState(false)

  // Section 4: Cash Forecast State
  const [forecastData, setForecastData] = useState<ForecastResponse | null>(null)
  const [loadingForecast, setLoadingForecast] = useState(false)
  const [forecastError, setForecastError] = useState<{ message: string; is404: boolean } | null>(null)
  const [cashflowSeries, setCashflowSeries] = useState<CashflowResponse | null>(null)

  // ── Actions ────────────────────────────────────────────────────────────────

  async function handleRunReconcile() {
    if (!activeCaseId) return
    setLoadingReconcile(true)
    setReconcileError(null)
    try {
      const data = await runReconciliation(activeCaseId)
      setReconcileData(data)
    } catch (err: any) {
      setReconcileError({
        message: err.message || 'Failed to run reconciliation',
        is404: err.status === 404,
      })
    } finally {
      setLoadingReconcile(false)
    }
  }

  async function handleRunTaxMatch() {
    if (!activeCaseId) return
    setLoadingTax(true)
    setTaxError(null)
    try {
      const data = await runTaxMatch(activeCaseId)
      setTaxData(data)
    } catch (err: any) {
      setTaxError({
        message: err.message || 'Failed to run tax matching',
        is404: err.status === 404,
      })
    } finally {
      setLoadingTax(false)
    }
  }

  async function handleAskSettlementQA(e?: React.FormEvent) {
    if (e) e.preventDefault()
    if (!activeCaseId || !question.trim()) return
    setLoadingQA(true)
    setQAError(null)
    try {
      const res = await sendSettlementQA(activeCaseId, question.trim())
      setQAResponse(res)
    } catch (err: any) {
      setQAError({
        message: err.message || 'Failed to execute settlement Q&A query',
        is404: err.status === 404,
      })
    } finally {
      setLoadingQA(false)
    }
  }

  async function handleFetchForecast() {
    if (!activeCaseId) return
    setLoadingForecast(true)
    setForecastError(null)
    try {
      const fc = await getForecast(activeCaseId)
      setForecastData(fc)
      // Optional daily series for sparkline
      try {
        const cf = await getCashflow(activeCaseId)
        setCashflowSeries(cf)
      } catch {
        /* silent optional */
      }
    } catch (err: any) {
      setForecastError({
        message: err.message || 'Failed to fetch cash forecast',
        is404: err.status === 404,
      })
    } finally {
      setLoadingForecast(false)
    }
  }

  // ── Auto-load on activeCaseId change ───────────────────────────────────────

  useEffect(() => {
    if (authLoading || !activeCaseId) return
    void handleRunReconcile()
    void handleRunTaxMatch()
    void handleFetchForecast()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeCaseId, authLoading])

  // ── Sorted Reconciliation Results (Problems/Exceptions first) ─────────────

  const sortedReconcileResults = useMemo(() => {
    if (!reconcileData?.results) return []
    const list = [...reconcileData.results]
    // Filter
    const filtered = reconcileFilter === 'exceptions'
      ? list.filter(r => r.status !== 'matched' || r.flags.includes('possible_structuring') || r.requires_approval)
      : list

    // Sort priority: exception / structuring -> unresolved -> matched
    return filtered.sort((a, b) => {
      const weight = (r: ReconcileResultRow) => {
        if (r.flags.includes('possible_structuring')) return 0
        if (r.status === 'exception') return 1
        if (r.status === 'unresolved') return 2
        if (r.requires_approval) return 3
        return 4
      }
      return weight(a) - weight(b)
    })
  }, [reconcileData, reconcileFilter])

  // ── Sorted Tax Match Results (Exceptions first) ───────────────────────────

  const sortedTaxResults = useMemo(() => {
    if (!taxData?.results) return []
    const list = [...taxData.results]
    const filtered = taxFilter === 'exceptions'
      ? list.filter(r => r.status !== 'matched')
      : list

    return filtered.sort((a, b) => {
      const weight = (r: TaxMatchResultRow) => {
        if (r.status === 'exception') return 0
        if (r.status === 'unresolved') return 1
        return 2
      }
      return weight(a) - weight(b)
    })
  }, [taxData, taxFilter])

  if (authLoading) {
    return (
      <div className="min-h-screen bg-[#09090B] flex items-center justify-center text-zinc-400">
        <Loader2 className="animate-spin text-indigo-500" size={36} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#09090B] text-zinc-100 p-4 sm:p-8 space-y-8">
      {/* ── Page Header ── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-zinc-800 pb-6">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-3xl font-black tracking-tight text-white">Compliance Intelligence</h1>
            {activeCaseId && (
              <span className="px-3 py-1 rounded-full text-xs font-mono font-medium bg-indigo-500/10 text-indigo-300 border border-indigo-500/20">
                Case: {activeCaseId}
              </span>
            )}
          </div>
          <p className="text-sm text-zinc-400 mt-1">
            Automated invoice reconciliation, tax-rate matching, settlement Q&amp;A, and net cashflow forecasting.
          </p>
        </div>

        {/* Section Tabs Switcher */}
        <div className="flex items-center p-1 rounded-xl bg-zinc-900 border border-zinc-800 self-start md:self-auto overflow-x-auto">
          {[
            { id: 'reconciliation', label: 'Reconciliation', icon: FileCheck2 },
            { id: 'tax-match', label: 'Tax Match', icon: Percent },
            { id: 'settlement-qa', label: 'Settlement Q&A', icon: HelpCircle },
            { id: 'forecast', label: 'Cash Forecast', icon: TrendingUp },
          ].map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as SectionTab)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition whitespace-nowrap ${
                  isActive
                    ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/60'
                }`}
              >
                <Icon size={14} />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {!activeCaseId ? (
        <CaseEmptyState caseId={null} />
      ) : (
        <div className="space-y-8">
          {/* ─────────────────────────────────────────────────────────────
              SECTION 1: Reconciliation
             ───────────────────────────────────────────────────────────── */}
          {(activeTab === 'reconciliation' || activeTab === ('all' as any)) && (
            <SectionContainer
              title="Invoice & Vendor Reconciliation"
              description="Graph-backed matching of invoice amounts against vendor contract limits & structuring checks."
              icon={FileCheck2}
              action={
                <button
                  onClick={() => void handleRunReconcile()}
                  disabled={loadingReconcile}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold transition flex items-center gap-2 shadow-lg shadow-indigo-600/20"
                >
                  {loadingReconcile ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                  Run Reconciliation
                </button>
              }
            >
              {loadingReconcile && !reconcileData ? (
                <div className="py-16 text-center text-zinc-400 space-y-3">
                  <Loader2 size={32} className="animate-spin text-indigo-500 mx-auto" />
                  <p className="text-sm">Reconciling invoice graph entities against contracts…</p>
                </div>
              ) : reconcileError ? (
                reconcileError.is404 ? (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 text-center">
                    <Info size={32} className="text-amber-400 mx-auto mb-3" />
                    <p className="text-sm font-semibold text-zinc-200">No Graph Documents for Case</p>
                    <p className="text-xs text-zinc-400 mt-1 mb-4">
                      Upload invoice and contract documents to this case workspace to perform reconciliation.
                    </p>
                    <button
                      onClick={() => navigate('/app/upload')}
                      className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-white transition"
                    >
                      Upload Documents
                    </button>
                  </div>
                ) : (
                  <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 flex items-center gap-3 text-red-400 text-sm">
                    <AlertCircle size={20} className="shrink-0" />
                    <p>{reconcileError.message}</p>
                  </div>
                )
              ) : !reconcileData ? (
                <div className="py-12 text-center text-zinc-400">
                  <FileCheck2 size={40} className="mx-auto text-zinc-600 mb-3" />
                  <p className="text-sm font-medium text-zinc-300">Reconciliation Not Executed Yet</p>
                  <p className="text-xs text-zinc-500 mt-1 mb-4">
                    Click "Run Reconciliation" to evaluate invoice contract limits and flag anomalies.
                  </p>
                  <button
                    onClick={() => void handleRunReconcile()}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
                  >
                    Run Reconciliation
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Summary KPI cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                    <div className="p-3.5 rounded-xl border border-zinc-800 bg-zinc-900/90">
                      <p className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Total Invoices</p>
                      <p className="text-xl font-bold text-zinc-100 mt-1">{reconcileData.total}</p>
                    </div>
                    <div className="p-3.5 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
                      <p className="text-[11px] font-medium text-emerald-400 uppercase tracking-wider">Matched</p>
                      <p className="text-xl font-bold text-emerald-400 mt-1">{reconcileData.matched}</p>
                    </div>
                    <div className="p-3.5 rounded-xl border border-red-500/20 bg-red-500/5">
                      <p className="text-[11px] font-medium text-red-400 uppercase tracking-wider">Exceptions</p>
                      <p className="text-xl font-bold text-red-400 mt-1">{reconcileData.exceptions}</p>
                    </div>
                    <div className="p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/5">
                      <p className="text-[11px] font-medium text-amber-400 uppercase tracking-wider">Unresolved</p>
                      <p className="text-xl font-bold text-amber-400 mt-1">{reconcileData.unresolved}</p>
                    </div>
                    <div className="p-3.5 rounded-xl border border-indigo-500/20 bg-indigo-500/5">
                      <p className="text-[11px] font-medium text-indigo-300 uppercase tracking-wider">Match Rate</p>
                      <p className="text-xl font-bold text-indigo-300 mt-1">{reconcileData.match_rate}</p>
                    </div>
                    <div className="p-3.5 rounded-xl border border-orange-500/20 bg-orange-500/5">
                      <p className="text-[11px] font-medium text-orange-400 uppercase tracking-wider">Structuring Flagged</p>
                      <p className="text-xl font-bold text-orange-400 mt-1">{reconcileData.structuring_groups}</p>
                    </div>
                  </div>

                  {/* Filter pills */}
                  <div className="flex items-center justify-between gap-4 pt-2">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setReconcileFilter('all')}
                        className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                          reconcileFilter === 'all'
                            ? 'bg-zinc-800 text-white border border-zinc-700'
                            : 'text-zinc-400 hover:text-zinc-200'
                        }`}
                      >
                        All Results ({reconcileData.results.length})
                      </button>
                      <button
                        onClick={() => setReconcileFilter('exceptions')}
                        className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                          reconcileFilter === 'exceptions'
                            ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                            : 'text-zinc-400 hover:text-zinc-200'
                        }`}
                      >
                        Issues &amp; Flagged Only ({reconcileData.exceptions + reconcileData.unresolved + reconcileData.structuring_groups})
                      </button>
                    </div>
                    <span className="text-xs text-zinc-500 hidden sm:inline">
                      Sorted: Exceptions &amp; Structuring Flags at top
                    </span>
                  </div>

                  {/* Results Table */}
                  {sortedReconcileResults.length === 0 ? (
                    <div className="p-8 text-center text-zinc-400 border border-zinc-800 rounded-xl">
                      No invoices match the selected filter.
                    </div>
                  ) : (
                    <div className="overflow-x-auto rounded-xl border border-zinc-800">
                      <table className="w-full text-left text-xs text-zinc-300">
                        <thead className="bg-zinc-950/80 text-zinc-400 font-semibold border-b border-zinc-800 uppercase tracking-wider text-[11px]">
                          <tr>
                            <th className="py-3 px-4">Invoice ID</th>
                            <th className="py-3 px-4">Vendor ID</th>
                            <th className="py-3 px-4">Status</th>
                            <th className="py-3 px-4">Invoice Amt</th>
                            <th className="py-3 px-4">Contract Amt</th>
                            <th className="py-3 px-4">Flags &amp; Approval</th>
                            <th className="py-3 px-4">Reason / Notes</th>
                            <th className="py-3 px-4">Citations</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/60 bg-zinc-900/40 font-mono text-[12px]">
                          {sortedReconcileResults.map((row, idx) => {
                            const isStructuring = row.flags.includes('possible_structuring')
                            return (
                              <tr
                                key={idx}
                                className={`transition hover:bg-zinc-800/40 ${
                                  isStructuring
                                    ? 'bg-orange-500/10 hover:bg-orange-500/15'
                                    : row.status === 'exception'
                                    ? 'bg-red-500/5 hover:bg-red-500/10'
                                    : row.status === 'unresolved'
                                    ? 'bg-amber-500/5 hover:bg-amber-500/10'
                                    : ''
                                }`}
                              >
                                <td className="py-3 px-4 font-semibold text-zinc-100">{row.invoice_id}</td>
                                <td className="py-3 px-4 text-zinc-400">{row.vendor_id || '—'}</td>
                                <td className="py-3 px-4">
                                  <StatusBadge status={row.status} />
                                </td>
                                <td className="py-3 px-4 font-medium text-zinc-200">
                                  {formatCurrency(row.invoice_amount)}
                                </td>
                                <td className="py-3 px-4 text-zinc-400">
                                  {formatCurrency(row.contract_amount)}
                                </td>
                                <td className="py-3 px-4 space-y-1">
                                  {isStructuring && (
                                    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-orange-500/20 text-orange-300 border border-orange-500/30">
                                      <ShieldAlert size={10} />
                                      possible_structuring
                                    </span>
                                  )}
                                  {row.requires_approval && (
                                    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30">
                                      Approval Required
                                    </span>
                                  )}
                                  {!isStructuring && !row.requires_approval && (
                                    <span className="text-zinc-500 text-[11px]">—</span>
                                  )}
                                </td>
                                <td className="py-3 px-4 font-sans text-xs text-zinc-300 max-w-xs truncate">
                                  {row.reason || '—'}
                                </td>
                                <td className="py-3 px-4">
                                  <div className="flex flex-wrap gap-1">
                                    {row.source_files && row.source_files.length > 0 ? (
                                      row.source_files.map((file, fIdx) => (
                                        <span
                                          key={fIdx}
                                          className="inline-block px-1.5 py-0.5 rounded text-[10px] font-sans bg-zinc-800 text-zinc-400 border border-zinc-700 truncate max-w-[120px]"
                                          title={file}
                                        >
                                          {file.split('/').pop()}
                                        </span>
                                      ))
                                    ) : (
                                      <span className="text-zinc-600 text-[11px]">—</span>
                                    )}
                                  </div>
                                </td>
                              </tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </SectionContainer>
          )}

          {/* ─────────────────────────────────────────────────────────────
              SECTION 2: Tax Matching
             ───────────────────────────────────────────────────────────── */}
          {(activeTab === 'tax-match' || activeTab === ('all' as any)) && (
            <SectionContainer
              title="Tax-Line Matching"
              description="Evaluates tax line items against ingested rate schedule HSN code expectations."
              icon={Percent}
              action={
                <button
                  onClick={() => void handleRunTaxMatch()}
                  disabled={loadingTax}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold transition flex items-center gap-2 shadow-lg shadow-indigo-600/20"
                >
                  {loadingTax ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                  Run Tax Matching
                </button>
              }
            >
              {loadingTax && !taxData ? (
                <div className="py-16 text-center text-zinc-400 space-y-3">
                  <Loader2 size={32} className="animate-spin text-indigo-500 mx-auto" />
                  <p className="text-sm">Matching TAX_LINE_ITEM nodes against rate schedules…</p>
                </div>
              ) : taxError ? (
                taxError.is404 ? (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 text-center">
                    <Info size={32} className="text-amber-400 mx-auto mb-3" />
                    <p className="text-sm font-semibold text-zinc-200">No Tax Schedule Documents</p>
                    <p className="text-xs text-zinc-400 mt-1 mb-4">
                      Upload tax invoice or HSN rate schedule documents to this case workspace.
                    </p>
                    <button
                      onClick={() => navigate('/app/upload')}
                      className="px-4 py-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-white transition"
                    >
                      Upload Documents
                    </button>
                  </div>
                ) : (
                  <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 flex items-center gap-3 text-red-400 text-sm">
                    <AlertCircle size={20} className="shrink-0" />
                    <p>{taxError.message}</p>
                  </div>
                )
              ) : !taxData ? (
                <div className="py-12 text-center text-zinc-400">
                  <Percent size={40} className="mx-auto text-zinc-600 mb-3" />
                  <p className="text-sm font-medium text-zinc-300">Tax Matching Not Executed Yet</p>
                  <p className="text-xs text-zinc-500 mt-1 mb-4">
                    Click "Run Tax Matching" to verify applied HSN tax rates.
                  </p>
                  <button
                    onClick={() => void handleRunTaxMatch()}
                    className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
                  >
                    Run Tax Matching
                  </button>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Tax Summary KPI Cards */}
                  <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
                    <div className="p-3.5 rounded-xl border border-zinc-800 bg-zinc-900/90">
                      <p className="text-[11px] font-medium text-zinc-400 uppercase tracking-wider">Total Items</p>
                      <p className="text-xl font-bold text-zinc-100 mt-1">{taxData.total}</p>
                    </div>
                    <div className="p-3.5 rounded-xl border border-emerald-500/20 bg-emerald-500/5">
                      <p className="text-[11px] font-medium text-emerald-400 uppercase tracking-wider">Matched</p>
                      <p className="text-xl font-bold text-emerald-400 mt-1">{taxData.matched}</p>
                    </div>
                    <div className="p-3.5 rounded-xl border border-red-500/20 bg-red-500/5">
                      <p className="text-[11px] font-medium text-red-400 uppercase tracking-wider">Exceptions</p>
                      <p className="text-xl font-bold text-red-400 mt-1">{taxData.exceptions}</p>
                    </div>
                    <div className="p-3.5 rounded-xl border border-amber-500/20 bg-amber-500/5">
                      <p className="text-[11px] font-medium text-amber-400 uppercase tracking-wider">Unresolved</p>
                      <p className="text-xl font-bold text-amber-400 mt-1">{taxData.unresolved}</p>
                    </div>
                    <div className="p-3.5 rounded-xl border border-indigo-500/20 bg-indigo-500/5">
                      <p className="text-[11px] font-medium text-indigo-300 uppercase tracking-wider">Match Rate</p>
                      <p className="text-xl font-bold text-indigo-300 mt-1">{taxData.match_rate}</p>
                    </div>
                  </div>

                  {/* Filter buttons */}
                  <div className="flex items-center gap-2 pt-2">
                    <button
                      onClick={() => setTaxFilter('all')}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                        taxFilter === 'all'
                          ? 'bg-zinc-800 text-white border border-zinc-700'
                          : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      All Tax Items ({taxData.results.length})
                    </button>
                    <button
                      onClick={() => setTaxFilter('exceptions')}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold transition ${
                        taxFilter === 'exceptions'
                          ? 'bg-red-500/20 text-red-300 border border-red-500/40'
                          : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                    >
                      Mismatches Only ({taxData.exceptions + taxData.unresolved})
                    </button>
                  </div>

                  {/* Tax Table */}
                  {sortedTaxResults.length === 0 ? (
                    <div className="p-8 text-center text-zinc-400 border border-zinc-800 rounded-xl">
                      No tax items match the selected filter.
                    </div>
                  ) : (
                    <div className="overflow-x-auto rounded-xl border border-zinc-800">
                      <table className="w-full text-left text-xs text-zinc-300">
                        <thead className="bg-zinc-950/80 text-zinc-400 font-semibold border-b border-zinc-800 uppercase tracking-wider text-[11px]">
                          <tr>
                            <th className="py-3 px-4">Item ID</th>
                            <th className="py-3 px-4">HSN ID</th>
                            <th className="py-3 px-4">Status</th>
                            <th className="py-3 px-4">Applied Rate</th>
                            <th className="py-3 px-4">Expected Rate</th>
                            <th className="py-3 px-4">Reason / Mismatch Details</th>
                            <th className="py-3 px-4">Source Files</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-zinc-800/60 bg-zinc-900/40 font-mono text-[12px]">
                          {sortedTaxResults.map((row, idx) => (
                            <tr
                              key={idx}
                              className={`transition hover:bg-zinc-800/40 ${
                                row.status === 'exception'
                                  ? 'bg-red-500/5 hover:bg-red-500/10'
                                  : row.status === 'unresolved'
                                  ? 'bg-amber-500/5 hover:bg-amber-500/10'
                                  : ''
                              }`}
                            >
                              <td className="py-3 px-4 font-semibold text-zinc-100">{row.item_id}</td>
                              <td className="py-3 px-4 text-zinc-400">{row.hsn_id || '—'}</td>
                              <td className="py-3 px-4">
                                <StatusBadge status={row.status} />
                              </td>
                              <td className="py-3 px-4 font-medium text-zinc-200">
                                {row.applied_rate != null ? `${row.applied_rate}%` : '—'}
                              </td>
                              <td className="py-3 px-4 text-zinc-400">
                                {row.expected_rate != null ? `${row.expected_rate}%` : '—'}
                              </td>
                              <td className="py-3 px-4 font-sans text-xs text-zinc-300 max-w-sm truncate">
                                {row.reason || '—'}
                              </td>
                              <td className="py-3 px-4">
                                <div className="flex flex-wrap gap-1">
                                  {row.source_files && row.source_files.length > 0 ? (
                                    row.source_files.map((file, fIdx) => (
                                      <span
                                        key={fIdx}
                                        className="inline-block px-1.5 py-0.5 rounded text-[10px] font-sans bg-zinc-800 text-zinc-400 border border-zinc-700 truncate max-w-[120px]"
                                        title={file}
                                      >
                                        {file.split('/').pop()}
                                      </span>
                                    ))
                                  ) : (
                                    <span className="text-zinc-600 text-[11px]">—</span>
                                  )}
                                </div>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}
            </SectionContainer>
          )}

          {/* ─────────────────────────────────────────────────────────────
              SECTION 3: Settlement Q&A
             ───────────────────────────────────────────────────────────── */}
          {(activeTab === 'settlement-qa' || activeTab === ('all' as any)) && (
            <SectionContainer
              title="Settlement & Payout Q&A"
              description="Ask natural-language questions regarding settlement IDs, fee deductions, UTR numbers, and payout dates."
              icon={HelpCircle}
            >
              <div className="space-y-6">
                {/* Chat Input Form */}
                <form onSubmit={(e) => void handleAskSettlementQA(e)} className="flex items-center gap-3">
                  <input
                    type="text"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    placeholder="Ask about settlement payouts, UTR numbers, fee deductions, or net amounts..."
                    className="flex-1 bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-zinc-100 placeholder-zinc-500 outline-none focus:border-indigo-500 transition"
                  />
                  <button
                    type="submit"
                    disabled={loadingQA || !question.trim()}
                    className="px-5 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold transition flex items-center gap-2 shadow-lg shadow-indigo-600/20 shrink-0"
                  >
                    {loadingQA ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                    Ask
                  </button>
                </form>

                {qaError && (
                  qaError.is404 ? (
                    <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-6 flex items-start gap-3 text-zinc-300">
                      <Info size={20} className="text-amber-400 shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-semibold text-zinc-200">No Settlement Documents for Case</p>
                        <p className="text-xs text-zinc-400 mt-1">
                          Upload settlement statements or payout reports to this workspace to enable Q&amp;A.
                        </p>
                        <button
                          onClick={() => navigate('/app/upload')}
                          className="mt-3 px-3 py-1.5 rounded-lg bg-zinc-800 hover:bg-zinc-700 text-xs font-medium text-white transition inline-flex items-center gap-1.5"
                        >
                          <Upload size={12} />
                          Upload Documents
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 flex items-center gap-3 text-red-400 text-sm">
                      <AlertCircle size={20} className="shrink-0" />
                      <p>{qaError.message}</p>
                    </div>
                  )
                )}

                {/* Response Bubble & Expandable Evidence */}
                {qaResponse && (
                  <div className="rounded-2xl border border-indigo-500/20 bg-zinc-950/70 p-6 space-y-4 shadow-xl">
                    <div className="flex items-center justify-between border-b border-zinc-800/80 pb-3">
                      <div className="flex items-center gap-2">
                        <Sparkles size={16} className="text-indigo-400" />
                        <span className="text-xs font-semibold text-indigo-300">Settlement Analyst Answer</span>
                      </div>
                      {qaResponse.result.processing_time_seconds != null && (
                        <span className="text-[11px] text-zinc-500 font-mono flex items-center gap-1">
                          <Clock size={12} />
                          {qaResponse.result.processing_time_seconds.toFixed(2)}s
                        </span>
                      )}
                    </div>

                    <div className="text-sm leading-relaxed text-zinc-200 whitespace-pre-wrap font-sans">
                      {qaResponse.result.answer}
                    </div>

                    {/* Expandable Citations & Evidence */}
                    {qaResponse.result.citations || qaResponse.result.evidence ? (
                      <div className="pt-2 border-t border-zinc-800">
                        <button
                          type="button"
                          onClick={() => setEvidenceOpen((v) => !v)}
                          className="flex items-center justify-between w-full text-xs font-semibold text-zinc-400 hover:text-zinc-200 transition py-1"
                        >
                          <span className="flex items-center gap-1.5">
                            <FileText size={14} className="text-indigo-400" />
                            Source Citations &amp; Evidence
                          </span>
                          {evidenceOpen ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                        </button>

                        <AnimatePresence>
                          {evidenceOpen && (
                            <motion.div
                              initial={{ opacity: 0, height: 0 }}
                              animate={{ opacity: 1, height: 'auto' }}
                              exit={{ opacity: 0, height: 0 }}
                              className="mt-3 space-y-2 overflow-hidden text-xs text-zinc-300"
                            >
                              {/* Render structured citations */}
                              {Array.isArray(qaResponse.result.citations) &&
                              qaResponse.result.citations.length > 0 ? (
                                <div className="space-y-2">
                                  {qaResponse.result.citations.map((c, cIdx) => (
                                    <div
                                      key={cIdx}
                                      className="p-3 rounded-lg border border-zinc-800 bg-zinc-900/80 font-sans"
                                    >
                                      <p className="font-semibold text-indigo-300 text-[11px]">
                                        📄 Source:{' '}
                                        {c.document_name || c.source_file || `Document #${cIdx + 1}`}
                                      </p>
                                      {c.text && (
                                        <p className="text-zinc-400 text-[11px] italic mt-1 leading-normal">
                                          "{c.text}"
                                        </p>
                                      )}
                                    </div>
                                  ))}
                                </div>
                              ) : (
                                <pre className="p-3 rounded-lg bg-zinc-900 border border-zinc-800 font-mono text-[11px] text-zinc-400 overflow-x-auto">
                                  {JSON.stringify(
                                    qaResponse.result.citations || qaResponse.result.evidence,
                                    null,
                                    2
                                  )}
                                </pre>
                              )}
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    ) : null}
                  </div>
                )}
              </div>
            </SectionContainer>
          )}

          {/* ─────────────────────────────────────────────────────────────
              SECTION 4: Cash Forecast
             ───────────────────────────────────────────────────────────── */}
          {(activeTab === 'forecast' || activeTab === ('all' as any)) && (
            <SectionContainer
              title="Net Cashflow Forecast"
              description="Quantile machine learning forecast for cashflow trajectory and confidence intervals."
              icon={TrendingUp}
              action={
                <button
                  onClick={() => void handleFetchForecast()}
                  disabled={loadingForecast}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold transition flex items-center gap-2 shadow-lg shadow-indigo-600/20"
                >
                  {loadingForecast ? <Loader2 size={14} className="animate-spin" /> : <RefreshCw size={14} />}
                  Refresh Forecast
                </button>
              }
            >
              {loadingForecast && !forecastData ? (
                <div className="py-16 text-center text-zinc-400 space-y-3">
                  <Loader2 size={32} className="animate-spin text-indigo-500 mx-auto" />
                  <p className="text-sm">Evaluating historical cashflow models…</p>
                </div>
              ) : forecastError ? (
                forecastError.is404 ? (
                  <div className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-8 text-center">
                    <Info size={32} className="text-amber-400 mx-auto mb-3" />
                    <p className="text-sm font-semibold text-zinc-200">No Cashflow Models Trained</p>
                    <p className="text-xs text-zinc-400 mt-1">
                      Forecast models have not been generated for this case yet.
                    </p>
                  </div>
                ) : (
                  <div className="rounded-xl border border-red-500/20 bg-red-500/10 p-4 flex items-center gap-3 text-red-400 text-sm">
                    <AlertCircle size={20} className="shrink-0" />
                    <p>{forecastError.message}</p>
                  </div>
                )
              ) : !forecastData ? (
                <div className="py-12 text-center text-zinc-400">
                  <TrendingUp size={40} className="mx-auto text-zinc-600 mb-3" />
                  <p className="text-sm font-medium text-zinc-300">Forecast Not Loaded</p>
                  <button
                    onClick={() => void handleFetchForecast()}
                    className="mt-4 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition"
                  >
                    Load Cash Forecast
                  </button>
                </div>
              ) : forecastData.forecast_available === false ? (
                /* THIN DATA INFORMATIONAL STATE (NOT RED ERROR) */
                <div className="rounded-xl border border-zinc-800 bg-zinc-900/60 p-6 flex items-start gap-4 text-zinc-300">
                  <div className="p-2 rounded-lg bg-zinc-800 text-amber-400 shrink-0">
                    <Info size={20} />
                  </div>
                  <div>
                    <h4 className="text-sm font-semibold text-zinc-200">Insufficient Cashflow History</h4>
                    <p className="text-xs text-zinc-400 mt-1 leading-relaxed">
                      Reason: <span className="text-amber-300 font-medium">{forecastData.reason}</span>
                    </p>
                    <p className="text-[11px] text-zinc-500 mt-2">
                      Forecasting requires at least 14 days of dated financial events (invoices, settlements) in the knowledge graph.
                    </p>
                  </div>
                </div>
              ) : (
                /* REAL FORECAST DISPLAY */
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    {/* Headline Net Cashflow */}
                    <div className="p-6 rounded-2xl border border-indigo-500/30 bg-indigo-500/5 flex flex-col justify-between">
                      <div>
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-semibold text-indigo-300 uppercase tracking-wider">
                            Forecast Net Cashflow
                          </p>
                          {forecastData.low_data_warning && (
                            <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              <AlertTriangle size={10} />
                              Low Data Caution
                            </span>
                          )}
                        </div>
                        <p className="text-3xl font-black text-white mt-3">
                          {formatCurrency(forecastData.forecast_net_cashflow)}
                        </p>
                      </div>
                      <p className="text-xs text-zinc-400 mt-4">
                        Projected horizon: <span className="text-zinc-200 font-semibold">{forecastData.horizon_days} days</span>
                      </p>
                    </div>

                    {/* Visual Range Bar */}
                    <div className="p-6 rounded-2xl border border-zinc-800 bg-zinc-900/90 md:col-span-2 flex flex-col justify-between space-y-4">
                      <div>
                        <p className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
                          80% Confidence Interval Range
                        </p>
                        <div className="grid grid-cols-2 gap-4 mt-3">
                          <div>
                            <p className="text-xs text-zinc-500">Lower Bound (p10)</p>
                            <p className="text-lg font-bold text-red-400">
                              {formatCurrency(forecastData.lower_bound)}
                            </p>
                          </div>
                          <div>
                            <p className="text-xs text-zinc-500">Upper Bound (p90)</p>
                            <p className="text-lg font-bold text-emerald-400">
                              {formatCurrency(forecastData.upper_bound)}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Range Bar Graphic */}
                      <div className="space-y-1.5 pt-2">
                        <div className="h-3 w-full rounded-full bg-zinc-800 relative overflow-hidden border border-zinc-700/50">
                          <div className="absolute inset-y-0 bg-gradient-to-r from-red-500/40 via-indigo-500/60 to-emerald-500/40 left-0 right-0" />
                          <div className="absolute top-0 bottom-0 w-1.5 bg-white shadow-lg left-1/2 -translate-x-1/2" />
                        </div>
                        <div className="flex justify-between text-[10px] text-zinc-500 font-mono">
                          <span>p10: {formatCurrency(forecastData.lower_bound)}</span>
                          <span className="text-indigo-300 font-bold">p50 Point Forecast</span>
                          <span>p90: {formatCurrency(forecastData.upper_bound)}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Model Lineage / honest framing */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl border border-zinc-800/80 bg-zinc-950/60 text-xs text-zinc-400">
                    <div className="flex items-center gap-2">
                      <Clock size={14} className="text-indigo-400 shrink-0" />
                      <span>
                        Model trained on{' '}
                        <strong className="text-zinc-200">{forecastData.model_trained_on?.n_training_rows ?? 0} days</strong> of historical workspace records.
                      </span>
                    </div>
                    {forecastData.model_trained_on?.training_date && (
                      <span className="text-zinc-500 font-mono text-[11px]">
                        Last trained: {new Date(forecastData.model_trained_on.training_date).toLocaleDateString()}
                      </span>
                    )}
                  </div>

                  {/* Cashflow Daily Series sparkline if available */}
                  {cashflowSeries?.daily_series && cashflowSeries.daily_series.length > 0 && (
                    <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-950/40">
                      <p className="text-xs font-semibold text-zinc-400 mb-3">Historical Daily Net Flow</p>
                      <div className="flex items-end gap-1 h-20 pt-2 border-b border-zinc-800 overflow-x-auto pb-1">
                        {cashflowSeries.daily_series.map((d, i) => {
                          const maxFlow = Math.max(...cashflowSeries.daily_series.map((s) => Math.abs(s.net_flow)), 1)
                          const heightPct = Math.min(100, Math.max(15, (Math.abs(d.net_flow) / maxFlow) * 100))
                          return (
                            <div
                              key={i}
                              className="flex-1 min-w-[8px] flex flex-col items-center group relative"
                            >
                              <div
                                style={{ height: `${heightPct}%` }}
                                className={`w-full rounded-t transition-all ${
                                  d.net_flow >= 0 ? 'bg-emerald-500/60 group-hover:bg-emerald-400' : 'bg-red-500/60 group-hover:bg-red-400'
                                }`}
                              />
                              <div className="opacity-0 group-hover:opacity-100 absolute bottom-full mb-1 z-20 px-2 py-1 bg-zinc-900 border border-zinc-700 text-[10px] font-mono text-zinc-200 rounded shadow-lg pointer-events-none whitespace-nowrap">
                                {d.date}: {formatCurrency(d.net_flow)}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </SectionContainer>
          )}
        </div>
      )}
    </div>
  )
}
