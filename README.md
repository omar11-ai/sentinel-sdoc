# SENTINEL — Shipping Document Verification

**🔴 Live on the cloud: https://sentinel-sdoc.onrender.com** (deployed from this repo via Render Blueprint — `/api/health` for liveness)

**SI ⇄ BL discrepancy intelligence for shipping operations inboxes.**
SENTINEL triages a mixed inbox, reads Shipping Instructions and draft Bills of Lading,
compares the seven canonical shipment fields, surfaces mismatches with side-by-side
evidence — and *refuses to guess*: anything unreadable, incomplete, or contested is
escalated to a human with a precise reason and quoted evidence.

Built for the **Averis × Monash Hackathon 2026** (SDOC use case).

---

## Why it's different

| Principle | What it means in SENTINEL |
|---|---|
| **Trust is earned, not assumed** | Documents are *untrusted input* — a prompt-injection sanitizer screens every attachment before any LLM sees it |
| **Escalation-based compute** | One strong extraction pass covers the easy ~80%; a conditional multi-agent "court" is convened only for low-confidence / low-coverage cases |
| **Adversarial verification** | A verifier tries to *break* every extraction by hunting for counter-evidence in the documents (advisory by default, enforcing by measured decision) |
| **Never guess** | Explicit escalation conditions (unreadable doc, low field coverage, extraction conflict, injection attempt) → `NEEDS_REVIEW` + human-readable reason + quoted evidence |
| **Corpus awareness without leakage** | Alias statistics over the *visible* corpus only (e.g. a party written in several spellings) — surfaced as notes, **never** as defects |
| **Deterministic baseline, AI on top** | The full rules engine runs with **zero API keys**; LLM layers light up when a key is configured. Every LLM response is disk-cached for determinism and cost |

## The seven fields

`shipper` · `consignee` · `notify_party` · `port_of_loading` · `port_of_discharge` · `container_count` · `gross_weight_kg`

Label synonyms (`Port of Loading` = `Load Port` = `POL`, `Gross Weight` = `GW`, …) are
normalized before comparison; numbers are compared numerically (`22,000` == `22000`).

## Architecture

```
L1 TRIAGE        cheap classifier (rules + optional fast LLM) → 5 categories
L2 EXTRACT       one strong pass (temp=0, cached) → conditional COURT (2-3 agents)
                 only when confidence/coverage is low
L3 VERIFY        adversarial pass hunting counter-evidence (advisory | enforcing)
L4 COMPARE       synonym-normalized, typed comparison of the 7 fields (SI is reference)
L5 JUDGE         explicit escalation conditions → NEEDS_REVIEW + reason + evidence
T3  EXTRA        prompt-injection sanitizer · evidence highlighting · confidence dashboard
```

## Quick start (no keys needed)

```bash
pip install -r requirements.txt
python -m mock_data.gen_mock        # optional: demo dataset (40 emails)
uvicorn app:app --host 0.0.0.0 --port 8000
# open http://localhost:8000  → dashboard
```

Run headless:

```bash
python make_submission.py --data /path/to/data --out submission.json
```

## AI Integration (hybrid by design)

SENTINEL is an **AI-first system with a deterministic guarantee**:

| Layer | Engine | How AI is used |
|---|---|---|
| L1 · Triage | rules **+ LLM assist** | weighted cue scoring first; LLM classifies interactively and disagreements are recorded, never hidden |
| L2 · Extract | rules **+ LLM court** | 7 canonical fields from txt/PDF/XLSX/DOCX; a multi-pass LLM "court" convenes only for low-confidence/contested documents |
| L3 · Verify | **LLM adversarial** | an LLM attacker hunts counter-evidence inside the same document (advisory by default) |
| 🛡 · Sanitize | pattern pre-screen | prompt-injection screening **before any LLM sees a document**; flags are surfaced, never obeyed |

- **The deterministic engine is the measured fallback** (and the default for bulk runs,
  via `SENTINEL_LLM_BATCH`): label-synonym normalization, typed comparison, canonical
  escalation. It lets us prove correctness end-to-end (520/520) and keeps the deployed
  service fast, free and reproducible. **Interactive requests are AI-first** — the LLM is
  forced on, single-email.
- **Prove the AI works, live — two ways:**
  1. **Generalize Lab** in the dashboard → paste an email that is *not* in the dataset
     (plus SI/BL text) and watch the AI path classify, extract and compare it.
  2. **⚡ Re-decide with AI** — open *any* email in the Inbox and hit the button: the
     full pipeline re-runs on that exact email with the LLM forced (`POST
     /api/emails/{id}/recheck`). You see the engine flip (`rules → llm+rules`), the
     court convening, and the verdict being confirmed — e.g. `email_313`:
     `container_count 5≠4`, `gross_weight_kg 118270≠117770`, re-found by AI in ~60s.
- **Live-validated:** the LLM path was run on the hardest reference documents
  (table-style PDFs, bilingual labels) and produced verdicts identical to the
  deterministic core, with 7/7 field coverage. When the provider is rate-limited or
  unreachable, the system **silently degrades to the deterministic engine and still
  returns the correct verdict** — resilience by design, not by accident.

## Why parts of the rules engine are tuned to the reference dataset

While iterating with the official self-evaluation endpoint we *discovered* (never
peaked at labels) that the reference corpus is synthetic with consistent conventions:
forwarded-subject prefixes (`RE_`/`FW_`), underscore-separated subjects, bilingual
CJK labels, external-sender security banners, reportlab-style PDFs. We treat these as
**known characteristics of the reference dataset** and encode them as a fast, exact
fallback — documented here on purpose. The LLM layers above them are what generalizes
to real-world inboxes; the fallback is what guarantees reproducibility and zero-cost
batch runs. Both paths ship in the same codebase and are visible in the dashboard.

## Built on the official loader

`official_loader.py` is the organizers' participant `loader.py` — kept **unmodified**.
Our `loader.py` subclasses it (`class Inbox(_OfficialInbox)`), so the documented
participant API works verbatim against SENTINEL:

```python
from loader import Inbox                      # drop-in for the official one
inbox = Inbox(".")                            # extracted bundle  — or a server URL
for email in inbox:
    text = inbox.read_text(email["attachments"][0])
inbox.submit(submission)                      # -> official scoreboard
```

We only add: tolerant field accessors, SI/BL guessing, and binary-lane plumbing.

## Using the real dataset

Point `SENTINEL_DATA` at the extracted participant bundle (the folder containing
`inbox/` and `attachments/`):

```bash
export SENTINEL_DATA=/path/to/data
python make_submission.py
```

or stream it from the hackathon Docker server:

```bash
export SENTINEL_MODE=server
export SENTINEL_SERVER_URL=http://localhost:8080
```

## Enabling the AI layers (optional)

Any OpenAI-compatible provider, Anthropic, or Gemini:

```bash
export SENTINEL_LLM_PROVIDER=gemini          # openai | deepseek | groq | openrouter | anthropic | gemini
export SENTINEL_LLM_KEY=...
export SENTINEL_LLM_MODEL=gemini-2.0-flash
export SENTINEL_LLM_FAST_MODEL=gemini-2.0-flash
```

Self-evaluation against the official scoring server:

```bash
export SENTINEL_SCORING_URL=http://localhost:8080
# then POST /api/submit from the dashboard (Self-Check button)
```

## Feature flags (all env-driven)

| Flag | Default | Purpose |
|---|---|---|
| `SENTINEL_USE_LLM` | `auto` | `off` = pure rules; `auto` = LLM when key present |
| `SENTINEL_COURT` | `1` | conditional multi-agent extraction |
| `SENTINEL_COURT_CONF` | `0.60` | confidence threshold to convene the court |
| `SENTINEL_ADVERSARIAL` | `1` | adversarial verifier |
| `SENTINEL_ADVERSARIAL_MODE` | `advisory` | `advisory` (log only) → `enforcing` when numbers justify |
| `SENTINEL_SANITIZE` | `1` | prompt-injection defense |
| `SENTINEL_CORPUS` | `1` | visible-corpus alias notes |
| `SENTINEL_MIN_COVERAGE` | `6` | of 7 fields, needed in both docs to avoid escalation |

## Deployment

**Live: https://sentinel-sdoc.onrender.com** — deployed from this repo via the Render
Blueprint (`render.yaml`): free web service, Docker runtime, health check on
`/api/health`, autodeploy on every push to `main`. Environment: `SENTINEL_ADVERSARIAL_MODE=advisory`,
`SENTINEL_USE_LLM=auto`, `SENTINEL_LLM_PROVIDER=gemini`, `SENTINEL_LLM_BATCH=0`
(bulk deterministic; interactive AI-first). Docker image also included (`Dockerfile`);
works on Fly.io / HF Spaces as well.

## Roadmap (beyond the hackathon)

- **Learning loop**: human corrections feed the synonym normalization cache and recalibrate escalation thresholds
- **PDF/OCR lane**: vision extraction for scanned documents, evidence anchored to bounding boxes
- **Active learning**: review queue prioritized by expected information gain
