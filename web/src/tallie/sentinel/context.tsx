import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

/* ---------- API types (mirror of FastAPI payloads) ---------- */

export type FieldValue = {
  display: string
  line_no: number
  blank?: boolean
  [k: string]: unknown
}

export type DocPublic = {
  engine: string
  coverage: number
  confidence: number
  fields: Record<string, FieldValue>
  [k: string]: unknown
}

export type Defect = {
  field: string
  si: unknown
  bl: unknown
  si_line?: string
  bl_line?: string
  [k: string]: unknown
}

export type EmailRecord = {
  email_id: string
  subject: string
  attachments: string[]
  category: string
  category_confidence: number
  classifier_engine: string
  classifier_reason?: string
  classifier_disagreement?: boolean
  status: 'OK' | 'MISMATCH' | 'NEEDS_REVIEW' | 'NOT_COMPARED'
  has_defect: boolean
  defect_fields: string[]
  review_reason: string | null
  si: DocPublic | null
  bl: DocPublic | null
  comparison: { defects: Defect[]; [k: string]: unknown } | null
  injection_flags: string[]
  corpus_notes: string[]
  verifier: { mode: string; objections: { evidence?: string; [k: string]: unknown }[]; enforcing_flip?: boolean } | null
  engine_trace: string[]
  human_resolved?: boolean
}

export type Summary = {
  total: number
  ok: number
  mismatch: number
  needs_review: number
  avg_confidence: number
  categories: Record<string, number>
  [k: string]: unknown
}

export type Results = {
  generated_at: string | null
  elapsed_s: number
  summary: Summary
  emails: EmailRecord[]
  config: Record<string, unknown>
  [k: string]: unknown
  ai_session?: { llm_calls: number; llm_elapsed_s: number }
  human_decisions?: Record<string, HumanDecision>
}


export type RecheckResult = {
  mode: string
  llm_available: boolean
  llm_provider: string | null
  classification: { category: string; engine: string; confidence: number }
  batch: { category: string; status: string; classifier_engine: string; engine_trace: string[] }
  si?: DocPublic | null
  bl?: DocPublic | null
  injection_flags?: string[]
  defects?: Defect[]
  review_reason?: string
  details?: string[]
  status: string
  elapsed_s?: number
  note?: string
  route?: string
  [k: string]: unknown
}

export type GenResult = RecheckResult & { [k: string]: unknown }

export type HumanDecision = {
  decision: 'approve_as_is' | 'flag_mismatch'
  note: string
  at: string
  was: { status?: string; review_reason?: string }
}

export type Scoreboard = {
  stage1: { accuracy: number; macro_f1: number; per: Record<string, { precision: number; recall: number; f1: number }>; confusion: Record<string, Record<string, number>> }
  stage3: { defect_precision: number; defect_recall: number; defect_f1: number; [k: string]: unknown }
  reliability: { escalation_precision: number; escalation_recall: number; escalation_f1?: number; [k: string]: unknown }
  end_to_end: { rate: number; success: number; total: number; [k: string]: unknown }
  final_score: number
  journey: { v: string; score: number }[]
  journey_note: string
  n_emails: number
  [k: string]: unknown
}

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) throw new Error(`${url} → HTTP ${res.status}`)
  return (await res.json()) as T
}

/* ---------- context ---------- */

type SentinelState = {
  health: { status: string; emails: number; llm: string } | null
  llmOn: boolean
  results: Results | null
  loading: boolean
  error: string | null
  reload: () => Promise<void>
  rerun: () => Promise<void>
  selfCheck: () => Promise<string>
  recheck: (id: string) => Promise<RecheckResult>
  generalize: (payload: Record<string, string>) => Promise<GenResult>
  scoreboard: Scoreboard | null
  load: () => Promise<void>
  applyRecheck: (id: string, r: RecheckResult) => void
  decide: (id: string, decision: 'approve_as_is' | 'flag_mismatch', note?: string) => Promise<void>
}

const SentinelContext = createContext<SentinelState | null>(null)

export function SentinelProvider({ children }: { children: ReactNode }) {
  const [health, setHealth] = useState<SentinelState['health']>(null)
  const [results, setResults] = useState<Results | null>(null)
  const [scoreboard, setScoreboard] = useState<Scoreboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [h, r] = await Promise.all([
        getJson<SentinelState['health']>('/api/health'),
        getJson<Results>('/api/results'),
      ])
      setHealth(h)
      setResults(r)
      getJson<Scoreboard>('/api/scoreboard').then(setScoreboard).catch(() => {})
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const rerun = useCallback(async () => {
    await fetch('/api/run', { method: 'POST' })
    await load()
  }, [load])

  const selfCheck = useCallback(async () => {
    const sub = await getJson<{ submission: Record<string, unknown> }>('/api/submission')
    const j = await getJson<{
      scoreboard?: { final_score?: number; stage1?: { macro_f1?: number }; stage3?: { defect_f1?: number }; end_to_end?: number; reliability?: { escalation_f1?: number } }
      source?: string
      message?: string
    }>('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ data: sub.submission }),
    })
    if (j.scoreboard?.final_score !== undefined) {
      return (
        `Official scoreboard — final ${j.scoreboard.final_score}` +
        ` · macro F1 ${j.scoreboard.stage1?.macro_f1}` +
        ` · defect F1 ${j.scoreboard.stage3?.defect_f1}` +
        ` · E2E ${j.scoreboard.end_to_end}` +
        ` · escalation F1 ${j.scoreboard.reliability?.escalation_f1}`
      )
    }
    return 'Self-check sent — ' + (j.source ?? '') + (j.message ? ' · ' + j.message : '')
  }, [])

  const recheck = useCallback(
    (id: string) =>
      getJson<RecheckResult>(`/api/emails/${id}/recheck`, { method: 'POST' }),
    [],
  )

  const applyRecheck = useCallback((id: string, r: RecheckResult) => {
    setResults((rs) =>
      rs
        ? {
            ...rs,
            emails: rs.emails.map((e) =>
              e.email_id === id ? { ...e, classifier_engine: 'llm+rules' } : e,
            ),
            ai_session: r.llm_available
              ? {
                  llm_calls: (rs.ai_session?.llm_calls ?? 0) + 1,
                  llm_elapsed_s: Math.round(((rs.ai_session?.llm_elapsed_s ?? 0) + (r.elapsed_s ?? 0)) * 10) / 10,
                }
              : (rs.ai_session ?? { llm_calls: 0, llm_elapsed_s: 0 }),
          }
        : rs,
    )
  }, [])

  const decide = useCallback(
    async (id: string, decision: 'approve_as_is' | 'flag_mismatch', note?: string) => {
      const j = await getJson<{ human_decisions: Record<string, HumanDecision> }>(
        `/api/emails/${id}/decision`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ decision, note: note ?? '' }),
        },
      )
      setResults((rs) =>
        rs
          ? {
              ...rs,
              human_decisions: { ...(rs.human_decisions ?? {}), ...(j.human_decisions ?? {}) },
              emails: rs.emails.map((e) =>
                e.email_id === id
                  ? { ...e, status: decision === 'flag_mismatch' ? 'MISMATCH' : 'OK', human_resolved: true }
                  : e,
              ),
            }
          : rs,
      )
    },
    [],
  )

  const generalize = useCallback(
    (payload: Record<string, string>) =>
      getJson<GenResult>('/api/generalize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      }),
    [],
  )

  const llmOn = Boolean(health?.llm && !health.llm.startsWith('off'))

  const value = useMemo<SentinelState>(
    () => ({
      health,
      llmOn,
      results,
      scoreboard,
      loading,
      error,
      reload: load,
      rerun,
      selfCheck,
      recheck,
      generalize,
      applyRecheck,
      decide,
      load,
    }),
    [health, llmOn, results, scoreboard, loading, error, load, rerun, selfCheck, recheck, generalize, applyRecheck, decide],
  )

  return <SentinelContext.Provider value={value}>{children}</SentinelContext.Provider>
}

export function useSentinel() {
  const ctx = useContext(SentinelContext)
  if (!ctx) throw new Error('useSentinel must be used within SentinelProvider')
  return ctx
}
