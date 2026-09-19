import { useState } from 'react'
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
          <p className={cn('truncate text-sm font-medium tracking-tight', defect && 'text-(--status-exception)')}>
            {si ? si.display : '—'}
            {si && si.line_no >= 0 ? <span className="ml-1 font-mono text-[10px] text-muted-foreground">L{si.line_no}</span> : null}
          </p>
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <p className="text-xs text-muted-foreground">BL</p>
          <p className={cn('truncate text-sm font-medium tracking-tight', defect && 'text-(--status-exception)')}>
            {bl ? bl.display : '—'}
            {bl && bl.line_no >= 0 ? <span className="ml-1 font-mono text-[10px] text-muted-foreground">L{bl.line_no}</span> : null}
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
  const defects = new Set((email.comparison?.defects ?? []).map((d) => d.field))
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
            <StatusCard status={email.status} />
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
                        <p className="font-sans font-medium">[{d.field}]</p>
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
