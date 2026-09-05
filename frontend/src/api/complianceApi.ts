/**
 * Compliance API Client — integrates with workspace compliance endpoints:
 * - POST /api/workspace/{case_id}/reconcile
 * - POST /api/workspace/{case_id}/tax-match
 * - POST /api/workspace/{case_id}/settlement-qa
 * - POST /api/workspace/{case_id}/forecast
 * - POST /api/workspace/{case_id}/cashflow
 */
import { fetchApi } from './fetchWithNgrok'

const API_BASE = ((import.meta.env.VITE_API_BASE as string) || '').replace(/\/$/, '') + '/api'

// ── Reconciliation Types ──────────────────────────────────────────────────────

export interface ReconcileResultRow {
  invoice_id: string
  vendor_id: string | null
  status: 'matched' | 'exception' | 'unresolved'
  reason: string | null
  invoice_amount: number | null
  contract_amount: number | null
  requires_approval: boolean
  flags: string[]
  source_files: string[]
}

export interface ReconcileResponse {
  total: number
  matched: number
  exceptions: number
  unresolved: number
  match_rate: string
  structuring_groups: number
  results: ReconcileResultRow[]
}

// ── Tax Matching Types ────────────────────────────────────────────────────────

export interface TaxMatchResultRow {
  item_id: string
  hsn_id: string | null
  status: 'matched' | 'exception' | 'unresolved'
  reason: string | null
  applied_rate: number | null
  expected_rate: number | null
  source_files: string[]
}

export interface TaxMatchResponse {
  total: number
  matched: number
  exceptions: number
  unresolved: number
  match_rate: string
  results: TaxMatchResultRow[]
}

// ── Settlement Q&A Types ──────────────────────────────────────────────────────

export interface EvidenceCitation {
  document_name?: string
  source_file?: string
  page_number?: number | string
  text?: string
  chunk_id?: string
  [key: string]: unknown
}

export interface SettlementQAResult {
  answer: string
  evidence?: unknown
  citations?: EvidenceCitation[] | Record<string, unknown>
  processing_time_seconds?: number
  graph?: {
    nodes: unknown[]
    edges: unknown[]
  }
}

export interface SettlementQAResponse {
  success: boolean
  question: string
  case_id: string
  session_id: string
  result: SettlementQAResult
}

// ── Forecast Types ────────────────────────────────────────────────────────────

export interface ForecastRealResponse {
  forecast_net_cashflow: number
  lower_bound: number
  upper_bound: number
  horizon_days: number
  model_trained_on: {
    n_training_rows: number
    training_date: string
  }
  low_data_warning?: boolean
  forecast_available?: true
}

export interface ForecastThinResponse {
  forecast_available: false
  reason: string
}

export type ForecastResponse = ForecastRealResponse | ForecastThinResponse

// ── Cashflow Types ────────────────────────────────────────────────────────────

export interface DailyCashflowSeries {
  date: string
  net_flow: number
  n_events: number
}

export interface CashflowResponse {
  workspace_id: string
  total_events: number
  daily_series: DailyCashflowSeries[]
}

// ── API Helpers ───────────────────────────────────────────────────────────────

export async function runReconciliation(caseId: string): Promise<ReconcileResponse> {
  const res = await fetchApi(`${API_BASE}/workspace/${encodeURIComponent(caseId)}/reconcile`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw { status: res.status, message: err.detail || err.message || `HTTP ${res.status}` }
  }
  return res.json()
}

export async function runTaxMatch(caseId: string): Promise<TaxMatchResponse> {
  const res = await fetchApi(`${API_BASE}/workspace/${encodeURIComponent(caseId)}/tax-match`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw { status: res.status, message: err.detail || err.message || `HTTP ${res.status}` }
  }
  return res.json()
}

export async function sendSettlementQA(
  caseId: string,
  question: string,
  topK = 10,
  sessionId?: string,
): Promise<SettlementQAResponse> {
  const res = await fetchApi(`${API_BASE}/workspace/${encodeURIComponent(caseId)}/settlement-qa`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, top_k: topK, session_id: sessionId }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw { status: res.status, message: err.detail || err.message || `HTTP ${res.status}` }
  }
  return res.json()
}

export async function getForecast(caseId: string): Promise<ForecastResponse> {
  const res = await fetchApi(`${API_BASE}/workspace/${encodeURIComponent(caseId)}/forecast`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw { status: res.status, message: err.detail || err.message || `HTTP ${res.status}` }
  }
  return res.json()
}

export async function getCashflow(caseId: string): Promise<CashflowResponse> {
  const res = await fetchApi(`${API_BASE}/workspace/${encodeURIComponent(caseId)}/cashflow`, {
    method: 'POST',
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw { status: res.status, message: err.detail || err.message || `HTTP ${res.status}` }
  }
  return res.json()
}
