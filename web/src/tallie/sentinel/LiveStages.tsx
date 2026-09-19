import { useEffect, useMemo, useState } from 'react'
import { AnimatePresence, motion } from 'motion/react'

export type LiveEvent = {
  t: 'stage' | 'note' | 'result' | 'error' | 'progress'
  key?: string
  state?: 'start' | 'done' | 'skip'
  label?: string
  at?: number // seconds since run start (set by the consumer, performance clock)
  emails?: number
  elapsed_s?: number
  message?: string
  done?: number
  total?: number
  email_id?: string
  result?: Record<string, unknown>
}

const META: Record<string, { title: string; icon: string }> = {
  triage: { title: 'Triage', icon: '✉' },
  sanitize: { title: 'Sanitize', icon: '🛡' },
  si: { title: 'Extract SI', icon: '📄' },
  bl: { title: 'Extract BL', icon: '📄' },
  judge: { title: 'Judge', icon: '⚖' },
  compare: { title: 'Compare', icon: '⇄' },
  verdict: { title: 'Verdict', icon: '✓' },
}

type RowState = 'active' | 'done' | 'skip'

export function LiveStages({ events }: { events: LiveEvent[] }) {
  const [, setTick] = useState(0)
  const anyActive = events.some((e) => e.t === 'stage' && e.state === 'start')
  useEffect(() => {
    if (!anyActive) return
    const id = setInterval(() => setTick((x) => x + 1), 100)
    return () => clearInterval(id)
  }, [anyActive])

  const rows = useMemo(() => {
    const out: {
      key: string
      state: RowState
      label: string
      startAt?: number
      endAt?: number
    }[] = []
    for (const e of events) {
      if (e.t !== 'stage' || !e.key) continue
      let row = out.find((r) => r.key === e.key)
      if (!row) {
        row = { key: e.key, state: 'active', label: '' }
        out.push(row)
      }
      if (e.state === 'start') {
        row.state = 'active'
        row.startAt = e.at
      } else if (e.state === 'done') {
        row.state = 'done'
        row.endAt = e.at
        row.label = e.label ?? ''
      } else if (e.state === 'skip') {
        row.state = 'skip'
        row.endAt = e.at
        row.label = e.label ?? ''
      }
    }
    return out
  }, [events])

  const startAt = rows.find((r) => r.state === 'active')?.startAt

  return (
    <div className="relative flex flex-col gap-2 rounded-xl border bg-zinc-50/40 p-5 dark:bg-card/40">
      {rows.map((r, i) => {
        const meta = META[r.key] ?? { title: r.key, icon: '•' }
        const isVerdict = r.key === 'verdict'
        const stageElapsed =
          r.state === 'done' && r.startAt !== undefined && r.endAt !== undefined
            ? (r.endAt - r.startAt).toFixed(1) + 's'
            : undefined
        const activeElapsed =
          r.state === 'active' && startAt !== undefined
            ? Math.max(0, performance.now() / 1000 - startAt).toFixed(1) + 's'
            : undefined
        return (
          <div key={r.key} className="relative flex items-start gap-3">
            {i < rows.length - 1 ? (
              <span className="absolute left-[15px] top-9 h-[calc(100%-6px)] w-0.5 rounded bg-border" />
            ) : null}
            <motion.span
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 400, damping: 24 }}
              className={
                'relative z-10 grid size-8 shrink-0 place-items-center rounded-full border text-sm ' +
                (r.state === 'active'
                  ? 'border-(--live) bg-background text-(--live)'
                  : r.state === 'done'
                    ? 'border-transparent bg-(--live)/15 text-(--live)'
                    : 'border-border bg-background text-muted-foreground')
              }
            >
              {r.state === 'active' ? (
                <>
                  <motion.span
                    animate={{ boxShadow: ['0 0 0 0px rgba(0,177,83,0.35)', '0 0 0 9px rgba(0,177,83,0)'] }}
                    transition={{ repeat: Infinity, duration: 1.5, ease: 'easeOut' }}
                    className="absolute inset-0 rounded-full"
                  />
                  <motion.span
                    animate={{ rotate: 360 }}
                    transition={{ repeat: Infinity, duration: 1.1, ease: 'linear' }}
                    className="font-bold"
                  >
                    ◌
                  </motion.span>
                </>
              ) : r.state === 'done' ? (
                <b>{isVerdict ? meta.icon : '✓'}</b>
              ) : (
                '—'
              )}
            </motion.span>
            <div className="flex min-w-0 flex-1 flex-col gap-0.5 pt-0.5">
              <div className="flex items-baseline justify-between gap-3">
                <p
                  className={
                    'text-sm font-medium tracking-tight ' +
                    (r.state === 'skip' ? 'text-muted-foreground/60 line-through' : '')
                  }
                >
                  {meta.title}
                </p>
                {stageElapsed || activeElapsed ? (
                  <span className="font-mono text-xs text-muted-foreground">{activeElapsed ?? stageElapsed}</span>
                ) : null}
              </div>
              <AnimatePresence mode="wait">
                {r.label ? (
                  <motion.p
                    key={r.key + r.label}
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25 }}
                    className={
                      'font-mono text-xs leading-relaxed ' +
                      (isVerdict && r.state === 'done'
                        ? 'font-bold text-foreground'
                        : 'text-muted-foreground')
                    }
                  >
                    {r.label}
                  </motion.p>
                ) : null}
              </AnimatePresence>
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function RunProgress({
  done,
  total,
  emailId,
  startedAt,
  finished,
}: {
  done: number
  total: number
  emailId: string
  startedAt: number
  finished: string | null
}) {
  const [, setTick] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setTick((x) => x + 1), 100)
    return () => clearInterval(id)
  }, [])
  const elapsed = Math.max(0.1, performance.now() / 1000 - startedAt)
  const rate = done / elapsed
  const remaining = finished || rate > 0 ? Math.max(0, total - done) / Math.max(rate, 0.001) : 0
  const pct = Math.min(100, (done / Math.max(total, 1)) * 100)
  return (
    <div className="flex flex-col gap-2.5">
      <div className="flex items-baseline justify-between gap-3 font-mono text-xs">
        <span className="font-bold text-(--live)">{done} / {total} emails</span>
        <span className="text-muted-foreground">
          {rate.toFixed(0)} emails/s · ETA {remaining.toFixed(0)}s · {emailId}
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full rounded-full bg-(--live)"
          animate={{ width: pct + '%' }}
          transition={{ ease: 'easeOut', duration: 0.2 }}
        />
      </div>
    </div>
  )
}
