import { useEffect, useState } from 'react'
import { CheckIcon, TriangleAlertIcon, XIcon, ZapIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Sheet,
  SheetClose,
  SheetContent,
  SheetDescription,
  SheetFooter,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import { useSentinel, type EmailRecord, type RecheckResult } from './context'
import { cn } from '@/lib/utils'

const FIELDS = [
  'shipper',
  'consignee',
  'notify_party',
  'port_of_loading',
  'port_of_discharge',
  'container_count',
  'gross_weight_kg',
] as const

const FIELD_LABEL: Record<string, string> = {
  shipper: 'Shipper',
  consignee: 'Consignee',
  notify_party: 'Notify party',
  port_of_loading: 'Port of loading',
  port_of_discharge: 'Port of discharge',
  container_count: 'Container count',
  gross_weight_kg: 'Gross weight (kg)',
}

type LineStatus = 'matched' | 'mismatched' | 'missing'

const lineConfig: Record<
  LineStatus,
  { label: string; className: string; Icon: typeof CheckIcon }
> = {
  matched: { label: 'Match', className: 'text-(--status-completed)', Icon: CheckIcon },
  mismatched: { label: 'Mismatch', className: 'text-(--status-exception)', Icon: XIcon },
  missing: { label: 'Missing', className: 'text-orange-500', Icon: TriangleAlertIcon },
}

function StatusCard({
  status,
}: {
  status: EmailRecord['status']
}) {
  const map: Record<string, { label: string; className: string }> = {
    OK: { label: 'Clean · OK', className: 'text-(--status-completed) bg-(--status-completed)/10' },
    MISMATCH: { label: 'Mismatch caught', className: 'text-(--status-exception) bg-(--status-exception)/10' },
    NEEDS_REVIEW: { label: 'Escalated to human', className: 'text-(--status-processing) bg-(--status-processing)/10' },
    NOT_COMPARED: { label: 'Routed — no comparison', className: 'text-muted-foreground bg-muted' },
  }
  const cfg = map[status] ?? map.NOT_COMPARED
  return (
    <span className={cn('inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-sm font-medium', cfg.className)}>
      {cfg.label}
    </span>
  )
}

function FieldRow({
  field,
  si,
  bl,
  defect,
}: {
  field: string
  si?: { display: string; line_no: number }
  bl?: { display: string; line_no: number }
  defect: boolean
}) {
  const status: LineStatus = defect ? 'mismatched' : si && bl ? 'matched' : 'missing'
  const cfg = lineConfig[status]
  const Icon = cfg.Icon
  return (
    <div className="flex flex-col gap-2 rounded-xl bg-zinc-50 px-1 pt-2 pb-1 dark:bg-muted">
      <div className="flex items-center justify-between px-2">
        <p className="text-sm font-medium tracking-tight">{FIELD_LABEL[field] ?? field}</p>
        <span className={cn('inline-flex items-center gap-1.5 rounded-xl px-2 py-1 text-xs font-medium', cfg.className)}>
          <Icon className="size-3.5" />
          {cfg.label}
        </span>
      </div>
      <div className="flex items-start gap-3 rounded-xl border bg-background p-3">
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="text-xs text-muted-foreground">SI (reference)</p>
          <p className={cn('font-mono text-sm tracking-tight', defect && 'text-(--status-exception)')}>
            {si ? si.display : '—'}
            {si && si.line_no >= 0 ? <span className="ml-1 text-[10px] text-muted-foreground">L{si.line_no}</span> : null}
          </p>
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="text-xs text-muted-foreground">BL</p>
          <p className={cn('font-mono text-sm tracking-tight', defect && 'text-(--status-exception)')}>
            {bl ? bl.display : '—'}
            {bl && bl.line_no >= 0 ? <span className="ml-1 text-[10px] text-muted-foreground">L{bl.line_no}</span> : null}
          </p>
        </div>
      </div>
    </div>
  )
}

function Note({ tone, children }: { tone: 'warn' | 'info' | 'bad'; children: React.ReactNode }) {
  const cls =
    tone === 'bad'
      ? 'text-(--status-exception)'
      : tone === 'warn'
        ? 'text-orange-600'
        : 'text-muted-foreground'
  return (
    <div className={cn('rounded-xl border bg-zinc-50 px-4 py-3 text-sm leading-relaxed dark:bg-muted', cls)}>
      {children}
    </div>
  )
}

/* ---------- reviewer round trip (blueprint §8) ---------- */

type ReviewRow = {
  id: number
  version: number
  reviewer: string
  action: string
  field: string | null
  old_value: string | null
  new_value: string | null
  reason_note: string | null
  created_at: string
}
type AuditRow = {
  id: number
  event: string
  actor: string
  before: { status?: string } | null
  after: { status?: string } | null
  created_at: string
}
type ReviewState = { version: number; history: ReviewRow[]; audit: AuditRow[] }

const ACTION_LABEL: Record<string, string> = {
  confirm: 'confirmed verdict',
  correct: 'corrected a value',
  reject_flag: 'accepted variation (flag rejected)',
  unresolvable: 'marked unresolvable',
}

function ReviewerPanel({
  email,
  onStatusChange,
}: {
  email: EmailRecord
  onStatusChange: (s: EmailRecord['status'], defects: string[]) => void
}) {
  const [rev, setRev] = useState<ReviewState | null>(null)
  const [reviewer, setReviewer] = useState('demo-reviewer')
  const [note, setNote] = useState('')
  const [corr, setCorr] = useState<Record<string, string>>({})
  const [corrSide, setCorrSide] = useState<Record<string, 'bl' | 'si'>>({})
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [okMsg, setOkMsg] = useState<string | null>(null)

  useEffect(() => {
    setRev(null)
    setErr(null)
    setOkMsg(null)
    setCorr({})
    if (!email?.email_id) return
    fetch(`/api/emails/${email.email_id}/review`)
      .then((r) => r.json())
      .then((d: ReviewState) => setRev(d))
      .catch(() => setRev(null))
  }, [email?.email_id])

  const defectList = email.comparison?.defects ?? []

  async function act(
    action: 'confirm' | 'correct' | 'reject_flag' | 'unresolvable',
    field?: string,
  ) {
    setBusy(true)
    setErr(null)
    setOkMsg(null)
    try {
      const res = await fetch(`/api/emails/${email.email_id}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          action,
          field,
          new_value: field ? (corr[field] ?? '') : note,
          side: field ? (corrSide[field] ?? 'bl') : 'bl',
          note,
          reviewer: reviewer.trim() || 'demo-reviewer',
          version: rev?.version ?? 0,
        }),
      })
      const d = await res.json()
      if (!res.ok) {
        setErr(d.error ? `${d.error}${d.version != null ? ` (current v${d.version})` : ''}` : `HTTP ${res.status}`)
        if (d.version != null && rev) setRev({ ...rev, version: d.version })
        return
      }
      setRev({ version: d.version, history: d.history, audit: d.audit })
      onStatusChange(d.status, d.defect_fields)
      setOkMsg(
        `✓ ${ACTION_LABEL[action]}${field ? ` — ${field}` : ''} · verdict recomputed (${d.status}) · v${d.version}`,
      )
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-3 rounded-xl border p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-base font-medium tracking-tight">Reviewer round trip — corrections recompute</p>
        <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs">v{rev?.version ?? 0}</span>
      </div>
      <p className="text-xs text-muted-foreground">
        The original extraction is never rewritten. A correction re-enters normalization, the comparison re-runs, and
        the verdict is recomputed — every action lands in the audit trail.
      </p>
      <div className="flex flex-wrap gap-2">
        <input
          value={reviewer}
          onChange={(e) => setReviewer(e.target.value)}
          placeholder="reviewer name"
          className="h-9 w-44 rounded-lg border bg-transparent px-3 font-mono text-xs outline-none focus:border-(--live)"
        />
        <input
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="reason note for the audit trail…"
          className="h-9 min-w-52 flex-1 rounded-lg border bg-transparent px-3 text-sm outline-none focus:border-(--live)"
        />
      </div>

      {defectList.length ? (
        <div className="flex flex-col gap-2">
          {defectList.map((d) => (
            <div key={d.field} className="flex flex-col gap-2 rounded-xl bg-zinc-50 px-3 py-2.5 dark:bg-muted">
              <p className="text-sm font-medium tracking-tight">
                {FIELD_LABEL[d.field] ?? d.field}
                <span className="ml-2 font-mono text-xs text-muted-foreground">
                  SI {String(d.si)} ≠ BL {String(d.bl)}
                </span>
              </p>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={corrSide[d.field] ?? 'bl'}
                  onChange={(e) => setCorrSide({ ...corrSide, [d.field]: e.target.value as 'bl' | 'si' })}
                  className="h-8 rounded-lg border bg-background px-2 font-mono text-xs outline-none"
                  aria-label={`document side to correct for ${d.field}`}
                >
                  <option value="bl">fix BL</option>
                  <option value="si">fix SI</option>
                </select>
                <input
                  value={corr[d.field] ?? ''}
                  onChange={(e) => setCorr({ ...corr, [d.field]: e.target.value })}
                  placeholder="corrected value (re-enters normalization)"
                  className="h-8 min-w-48 flex-1 rounded-lg border bg-background px-2.5 font-mono text-xs outline-none focus:border-(--live)"
                />
                <Button variant="outline" className="h-8 rounded-lg px-3 text-xs" disabled={busy || !(corr[d.field] ?? '').trim()} onClick={() => void act('correct', d.field)}>
                  Apply correction
                </Button>
                <Button variant="ghost" className="h-8 rounded-lg px-3 text-xs" disabled={busy} onClick={() => void act('reject_flag', d.field)}>
                  Accept as match
                </Button>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-2">
        <Button variant="outline" className="h-9" disabled={busy} onClick={() => void act('confirm')}>
          ✓ Confirm verdict as reviewed
        </Button>
        {email.status === 'NEEDS_REVIEW' || email.review_reason ? (
          <Button variant="outline" className="h-9" disabled={busy} onClick={() => void act('unresolvable')}>
            ⚖ Mark unresolvable
          </Button>
        ) : null}
      </div>

      {err ? <Note tone="bad">{err}</Note> : null}
      {okMsg ? <p className="text-sm font-medium text-(--status-completed)">{okMsg}</p> : null}

      {rev?.history?.length ? (
        <div className="flex flex-col gap-1.5 rounded-xl border bg-zinc-50 p-3 font-mono text-xs dark:bg-muted">
          <p className="font-sans text-sm font-medium">Review history</p>
          {rev.history.map((h) => (
            <p key={h.id}>
              v{h.version + 1} · {h.created_at.slice(11, 19)} · {h.reviewer} · {ACTION_LABEL[h.action] ?? h.action}
              {h.field ? ` — ${h.field}` : ''}
              {h.old_value || h.new_value ? `: ${h.old_value ?? '—'} → ${h.new_value ?? '—'}` : ''}
              {h.reason_note ? ` · “${h.reason_note}”` : ''}
            </p>
          ))}
        </div>
      ) : null}
      {rev?.audit?.length ? (
        <div className="flex flex-col gap-1.5 rounded-xl border bg-zinc-50 p-3 font-mono text-xs dark:bg-muted">
          <p className="font-sans text-sm font-medium">Audit chain</p>
          {rev.audit.map((a) => (
            <p key={a.id}>
              {a.created_at.slice(11, 19)} · {a.event} · {a.actor} · {a.before?.status ?? '—'} → {a.after?.status ?? '—'}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  )
}

export function EmailDetailsSheet({
  email,
  open,
  onOpenChange,
}: {
  email: EmailRecord | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const { recheck, llmOn } = useSentinel()
  const [ai, setAi] = useState<RecheckResult | null>(null)
  const [aiBusy, setAiBusy] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)
  const [liveStatus, setLiveStatus] = useState<EmailRecord['status'] | null>(null)
  const [liveDefects, setLiveDefects] = useState<string[] | null>(null)

  useEffect(() => {
    setLiveStatus(null)
    setLiveDefects(null)
    setAi(null)
    setAiError(null)
  }, [email?.email_id])

  async function handleRecheck() {
    if (!email) return
    setAiBusy(true)
    setAiError(null)
    setAi(null)
    try {
      setAi(await recheck(email.email_id))
    } catch (e) {
      setAiError(e instanceof Error ? e.message : String(e))
    } finally {
      setAiBusy(false)
    }
  }

  if (!email) return null
  const shownStatus = (liveStatus ?? email.status) as EmailRecord['status']
  const shownDefects = liveDefects ?? (email.defect_fields ?? [])
  const defects = new Set<string>(
    liveDefects !== null ? shownDefects : (email.comparison?.defects ?? []).map((d) => d.field),
  )
  const si = email.si?.fields ?? {}
  const bl = email.bl?.fields ?? {}
  const allFields = [
    ...FIELDS.filter((f) => f in si || f in bl),
    ...Object.keys(si).filter((f) => !(FIELDS as readonly string[]).includes(f)),
    ...Object.keys(bl).filter((f) => !(FIELDS as readonly string[]).includes(f)),
  ]

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="tallie-dashboard flex w-full flex-col gap-0 overflow-y-auto sm:max-w-xl">
        <SheetHeader className="items-start gap-3">
          <div className="flex items-center gap-3">
            <SheetTitle className="font-serif text-2xl">{email.email_id}</SheetTitle>
            <StatusCard status={shownStatus} />
          </div>
          <SheetDescription className="line-clamp-2 text-left">
            {email.subject}
          </SheetDescription>
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs">{email.category}</span>
            <span className="rounded bg-muted px-2 py-0.5 font-mono text-xs">
              conf {Math.round(email.category_confidence * 100)}% · {email.classifier_engine}
            </span>
            {email.engine_trace.map((t) => (
              <span key={t} className="rounded bg-muted px-2 py-0.5 font-mono text-xs">{t}</span>
            ))}
          </div>
        </SheetHeader>

        <div className="flex flex-col gap-6 overflow-y-auto px-4 pb-6">
          <div className="flex flex-wrap items-center gap-3 border-b pb-4">
            <Button className="h-9 gap-1.5 rounded-lg px-3.5" disabled={aiBusy} onClick={handleRecheck}>
              {aiBusy ? 'AI reading documents…' : '⚡ Re-decide with AI — live'}
              <ZapIcon className="size-4" />
            </Button>
            <span className="text-xs text-muted-foreground">
              full pipeline re-run on this exact email{llmOn ? ' · LLM forced' : ' · fallback engine'}
            </span>
          </div>

          {aiBusy ? (
            <Note tone="info">⚡ AI path running — the LLM is re-reading this email&apos;s documents live (10–60s on free quota)…</Note>
          ) : null}
          {aiError ? <Note tone="bad">AI re-decision failed: {aiError} — the batch decision above remains authoritative.</Note> : null}
          {ai ? (
            <div className="flex flex-col gap-2 rounded-xl border bg-zinc-50 p-4 font-mono text-xs leading-relaxed dark:bg-muted">
              <p className="font-sans text-sm font-medium">Live re-decision — {ai.llm_available ? `LLM ON · ${ai.llm_provider}` : 'fallback engine'} · {ai.elapsed_s ?? '?'}s</p>
              <p>
                classifier ──── batch: {ai.batch.classifier_engine} → live:{' '}
                <b className="text-(--live)">{ai.classification.engine}</b> ({Math.round((ai.classification.confidence ?? 0) * 100)}%) · {ai.classification.category}
              </p>
              {ai.si ? <p>SI extract ──── live engine: <b className="text-(--live)">{ai.si.engine}</b> · coverage {ai.si.coverage}/7 · conf {Math.round(ai.si.confidence * 100)}%</p> : null}
              {ai.bl ? <p>BL extract ──── live engine: <b className="text-(--live)">{ai.bl.engine}</b> · coverage {ai.bl.coverage}/7 · conf {Math.round(ai.bl.confidence * 100)}%</p> : null}
              {ai.injection_flags?.length ? <p>🛡 injection ─── {ai.injection_flags.join(', ')} → detected, never obeyed</p> : null}
              {ai.defects?.map((d) => (
                <p key={d.field}>defect ──────── ⚠ {d.field}: SI {String(d.si)} ≠ BL {String(d.bl)}</p>
              ))}
              {ai.review_reason ? <p>escalated ───── {ai.review_reason}{ai.details ? ' — ' + ai.details.join('; ') : ''}</p> : null}
              <p className={cn('font-sans text-sm font-medium', ai.status === ai.batch.status ? 'text-(--status-completed)' : 'text-orange-600')}>
                {ai.status === ai.batch.status
                  ? `✓ verdict confirmed — the live AI path agrees with the batch decision (${ai.status})`
                  : `verdict differs from batch: ${ai.batch.status} → ${ai.status}`}
              </p>
            </div>
          ) : null}

          {email.injection_flags.length ? (
            <Note tone="bad">
              🛡 Prompt-injection patterns detected — {email.injection_flags.join(', ')}. Treated as data, never obeyed.
            </Note>
          ) : null}
          {email.review_reason ? <Note tone="warn">⚖ ESCALATED — {email.review_reason}</Note> : null}

          <ReviewerPanel
            email={email}
            onStatusChange={(s, df) => {
              setLiveStatus(s)
              setLiveDefects(df)
            }}
          />

          {email.corpus_notes.map((n) => (
            <Note key={n} tone="info">🔎 {n} (corpus alias note — never a defect)</Note>
          ))}
          {email.verifier?.objections?.length ? (
            <Note tone="info">
              🕵 Adversarial verifier ({email.verifier.mode}):{' '}
              {email.verifier.objections.map((o) => o.evidence ?? '').join(' · ')}
            </Note>
          ) : null}

          {email.comparison ? (
            <div className="flex flex-col gap-3">
              <p className="text-base font-medium tracking-tight">Field-by-field — SI (reference) vs BL</p>
              {shownDefects.length ? (
                <p className="text-sm text-muted-foreground">
                  {shownDefects.length} of 7 fields {shownDefects.length === 1 ? 'differs' : 'differ'}:{' '}
                  <span className="font-medium text-(--status-exception)">
                    {shownDefects.map((f) => FIELD_LABEL[f] ?? f).join(', ')}
                  </span>
                </p>
              ) : null}
              {shownStatus === 'OK' && !shownDefects.length ? (
                <p className="rounded-xl border bg-(--status-completed)/10 px-3 py-2 text-sm font-medium text-(--status-completed)">
                  No mismatch detected.
                </p>
              ) : null}
              {allFields.map((f) => (
                <FieldRow
                  key={f}
                  field={f}
                  si={si[f] as { display: string; line_no: number } | undefined}
                  bl={bl[f] as { display: string; line_no: number } | undefined}
                  defect={defects.has(f)}
                />
              ))}
              {(email.comparison.defects ?? []).some((d) => d.si_line || d.bl_line) ? (
                <div className="flex flex-col gap-2 rounded-xl border bg-zinc-50 p-4 font-mono text-xs dark:bg-muted">
                  <p className="font-sans text-sm font-medium">Literal evidence — source lines</p>
                  {email.comparison.defects
                    .filter((d) => d.si_line || d.bl_line)
                    .map((d) => (
                      <div key={d.field}>
                        <p className="font-sans font-medium">
                          [{d.field}] — SI: {String(d.si)} / BL: {String(d.bl)}
                        </p>
                        <p>SI ▸ {d.si_line ?? '—'}</p>
                        <p>BL ▸ {d.bl_line ?? '—'}</p>
                      </div>
                    ))}
                </div>
              ) : null}
            </div>
          ) : email.review_reason ? (
            <div className="flex flex-col gap-2">
              <p className="text-base font-medium tracking-tight">Why escalated</p>
              <Note tone="warn">{email.review_reason}</Note>
              <p className="font-mono text-xs text-muted-foreground">
                attachments: {email.attachments.join(', ') || '—'}
              </p>
            </div>
          ) : (
            <Note tone="info">
              Routed as <b>{email.category}</b> — no document comparison required for this category.
            </Note>
          )}

          <div className="flex flex-col gap-2 pb-4">
            <p className="text-sm text-muted-foreground">Decision trace</p>
            <div className="flex flex-wrap gap-1.5">
              <span className="rounded-md border bg-zinc-50 px-2 py-1 font-mono text-xs dark:bg-muted">
                classifier: {email.classifier_engine} ({Math.round(email.category_confidence * 100)}%)
              </span>
              {email.engine_trace.map((t) => (
                <span key={t} className="rounded-md border bg-zinc-50 px-2 py-1 font-mono text-xs dark:bg-muted">{t}</span>
              ))}
              {email.verifier ? (
                <span className="rounded-md border bg-zinc-50 px-2 py-1 font-mono text-xs dark:bg-muted">
                  verifier: {email.verifier.mode} · {email.verifier.objections?.length ?? 0} objections
                </span>
              ) : null}
            </div>
          </div>
        </div>

        <SheetFooter className="mt-auto border-t">
          <SheetClose asChild>
            <Button variant="outline">Close</Button>
          </SheetClose>
        </SheetFooter>
      </SheetContent>
    </Sheet>
  )
}
