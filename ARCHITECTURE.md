# ARCHITECTURE

SENTINEL — shipping document verification. One FastAPI service serves both
the API and the built React bundle: one origin, one thing to keep warm,
one thing that can break.

```
┌──────────────────────────────────────────────────────────────────┐
│ React 19 + Vite + TS (Tailwind 4) — served as static by FastAPI  │
│  inbox · pipeline · reconciliation sheet · reviewer · lab        │
└───────────────▲──────────────────────────────────────────────────┘
                │ same-origin /api/*
┌───────────────┴──────────────────────────────────────────────────┐
│ FastAPI (app.py)                                                 │
│  /api/results /api/emails/:id /api/emails/:id/recheck            │
│  /api/emails/:id/review  /api/audit  /api/submission  /api/submit│
│  /api/generalize[/stream] /api/run[/stream]  /api/scoreboard     │
├──────────────────────────────────────────────────────────────────┤
│ Pipeline (pipeline.py)          Lanes                            │
│  L1 classify   → classify.py    rules cues ⇄ LLM (ambiguous)     │
│  L2 extract    → extract.py     txt/pdf/xlsx/docx readers        │
│  L3 normalize  → normalize.py   typed values, CJK-safe labels    │
│  L4 compare    → compare.py     per-field, rule-named verdicts   │
│  L5 escalate   → escalate.py    4 canonical reasons, first match │
│  L6 verify     → sanitize.py    prompt-injection guard (6 regex) │
├──────────────────────────────────────────────────────────────────┤
│ review_store.py — SQLite, append-only                            │
│  reviews (actor, action, version, values) · audit_events (before │
│  → after). Original extractions are never mutated; corrections   │
│  re-enter normalization and the verdict is RECOMPUTED.           │
└──────────────────────────────────────────────────────────────────┘
                │
        Gemini API (flash) — content-hash disk cache, retries
```

## The AI boundary — the honest centre

| Task | Owner | Why |
|---|---|---|
| Five-way email classification | **AI** on genuinely ambiguous subjects, rules otherwise | measured cue collisions on threaded, ambiguous subjects; rules remain the fast path and the fallback |
| Semantic field-label alignment (labels outside the harvested dictionary) | **AI** | "To the Order of" → consignee has no lexical route |
| Document type / role verification | Deterministic | header-line check, decidable on the observed corpus |
| Field extraction from known labels | Deterministic | regex + alias dictionary wins on labelled key-value text; every value keeps its source line |
| Text normalisation & unit conversion | Deterministic | mechanical, reproducible; an LLM here is slower, costlier and occasionally wrong |
| SI/BL comparison | Deterministic | a probabilistic comparator gives two answers for one input |
| Discrepancy detection & reporting | Deterministic | falls out of the comparison; rule name attached to every verdict |
| Prompt-injection defence | Deterministic | pattern detection; injection text is treated as data, never obeyed |
| Live re-decision / Generalize Lab | **AI**-first with deterministic fallback | the reviewer/judge can watch the full LANE path re-run on any input |

Every stage degrades loudly, never silently: a low-confidence or
fallback-path verdict keeps its engine trace (`engine_trace`,
`classifier_engine`, `verifier`) and shows it in the UI.

## Data flow

1. **Batch run** at startup over the 520-email inbox → in-memory results +
   `submission` snapshot (`schema.build_submission`).
2. **Interactive paths** (re-check, generalize, streams) re-enter the same
   lanes live; session overlays (`human_decisions`, `ai_rechecked`) merge at
   read time so the audited bulk run stays intact.
3. **Reviewer round trip**: `POST /api/emails/:id/review` validates an
   optimistic-concurrency version, applies confirm / correct / reject_flag /
   unresolvable, recomputes the verdict (corrections re-enter normalization;
   the comparison re-runs), appends to `reviews` + `audit_events`, and the
   submission endpoint rebuilds from current state so the report and the data
   can never disagree.
4. **Scoring**: `/api/submit` posts the current submission to the official
   bundled scorer (or the organizers' hosted one when configured) and caches
   the scoreboard.

## Deployment (Render free tier)

- Single web service, Docker image, `SENTINEL_DATA=/app/data` (the
  participant dataset — verified to contain no answer key).
- Build: `npm ci && npm run build` (web → `static/app`), pip install from
  `requirements.txt`; uvicorn serves everything on one port.
- Keep-warm pings during the judging window keep the free instance hot; the
  health endpoint reports dataset count and LLM configuration.

## Production path (final round, deliberately not in the prelim)

- Managed Postgres for verdicts/fields/reviews/audit (the SQLite store is
  interface-identical: `review_store.py` is the only file that touches SQL).
- A queue + worker for batch runs (RQ/Upstash) with an inline fallback — the
  same story the UI already tells via the streaming endpoints.
- Authentication, multi-reviewer assignment, approval chains, per-reason
  escalation thresholds, dead-letter replay, chaos testing.
- DCSA eBL 3.0-flavoured export as a serializer only — it must never shape
  the internal contract.
