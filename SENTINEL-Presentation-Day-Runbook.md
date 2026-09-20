# SENTINEL — Presentation-Day Runbook
*(execute T-90 min before the submission deadline / judging window)*

## 1. Ship everything pending (5 min)
- Render dashboard → **Manual Deploy → Deploy latest commit** (auto-deploys can queue; manual is instant).
- Verify: `curl -s https://sentinel-sdoc.onrender.com | grep -o 'index-[A-Za-z0-9_-]*\.js'` matches the latest `static/app/assets` hash in the repo.

## 2. Warm + keep-warm (2 min)
- Hit `https://sentinel-sdoc.onrender.com/api/selfwarm` once — confirm `{"status":"ok","emails":520}`.
- Confirm the GitHub Actions keep-warm workflow exists and shows a green run in the last hour. If it was never added (token lacked `workflow` scope): **Add file → `.github/workflows/keep-warm.yml`** — content is in the workspace at `sentinel/.github/workflows/keep-warm.yml`. Two minutes, one commit. *(Alternative: any uptime pinger on `/api/selfwarm`.)*

## 3. Pre-seed the reviewer log (3 min — closes the "empty store" risk)
The SQLite store resets on each redeploy; seed one genuine round trip so a judge opening the site sees a live audit chain. **Seed only with score-safe actions (Confirm / Mark unresolvable) — never with "Accept as match" on a mismatch (see §7):**
1. Open the site → Inbox → open `email_013` (the LOCODE-trap mismatch).
2. In **Reviewer round trip**: reviewer = your name, note = "pre-demo verification round", click **✓ Confirm verdict as reviewed** → "approved as is", v1 recorded, verdict unchanged (MISMATCH stands).
3. Open `email_520` (the escalated one) → **Mark unresolvable** + note "pre-demo verification round".
4. Verify: `curl -s https://sentinel-sdoc.onrender.com/api/audit | head -c 400` → events present, **and** re-run the §4 submit → still `final 1.0`.
*(Or via API: `POST /api/emails/email_013/review {"action":"confirm","version":0,"note":"pre-demo verification round"}` then `POST /api/emails/email_520/review {"action":"unresolvable","version":0,"note":"pre-demo verification round"}`. If you get a 409, the response body tells you the current version — retry with it.)*

## 4. Fresh official score on the board (1 min)
```
curl -s -X POST https://sentinel-sdoc.onrender.com/api/submit \
  -H 'Content-Type: application/json' \
  -d "{\"data\": $(curl -s https://sentinel-sdoc.onrender.com/api/submission | python3 -c 'import json,sys; print(json.dumps(json.load(sys.stdin)["submission"]))')}" | python3 -c "import json,sys; s=json.load(sys.stdin); print(s.get('source'), '→ final', s['scoreboard']['final_score'])"
```
Expected: `official_scorer_bundled → final 1.0`.

## 5. Self-check links in a private window (3 min)
- Live URL loads cold (or after one warm click).
- Video link: **Unlisted/Public** or Drive "anyone with link → Viewer" (private = not accepted).
- Repo public + README renders.
- Deck link opens.
- Forms: team name / representative / email / phone filled.

## 6. The two sentences to say verbatim
- **AI role:** "على بيانات البطولة دي، محرك القواعد لوحده بيوصل للسقف — وإحنا نشرنا ده بنفسنا. الـAI بيدخل بالظبط لما اللغة تضلّل، وبيقفل الفحص اللايف. القواعد بتحسم الواضح، والـAI بيمدّ النظام لأوراق ما شافهاش قبل كده." (EN: "Rules decide the clear cases; AI is engaged precisely when language misleads.")
- **Numbers you may quote:** 520/520 · 46/46 exact defect sets · 1.0 P/R/F1 on all seven fields · batch 1.15 s · API 71–116 ms · 19/520 two-category keyword collisions · 49/520 below the 0.6 gate · review rate 3.8%.
- **Never quote:** vendor pricing, OCR benchmarks, DCSA compliance (unverified), "AI raises the accuracy" (false on this dataset and we publish that ourselves).

## 7. Score-protection protocol (CRITICAL — discovered 2026-09-20, verified live)
Reviewer actions are **not cosmetic**: they flow into `/api/submission`, and `POST /api/submit` grades the *current* state. Proven live: accepting a mismatch flag on `email_013` moved the official score **1.0 → 0.989**; correcting it back restored **1.0**. One wrong click in front of judges = the score drops live on the projector.

**Before judging starts — clean-state check (2 min):**
```
curl -s https://sentinel-sdoc.onrender.com/api/selfwarm                 # {"status":"ok","emails":520}
curl -s https://sentinel-sdoc.onrender.com/api/audit                    # only your seeded events
# + the §4 submit one-liner                                              # official_scorer_bundled → final 1.0
```
If not 1.0 → find the touched email in `/api/audit` → apply the undo recipe below → re-submit.

**During judging — what is SAFE vs FORBIDDEN:**

| Interaction | Verdict |
|---|---|
| Re-run, Self-Check, Metrics cards, filters, search, Export CSV, theme, open/close sheets | ✅ safe (read-only) |
| Generalize Lab — all samples incl. 💉, Analyze (~50 s) | ✅ safe (never touches the corpus) |
| ⚡ Re-decide with AI on `email_313` only | ✅ safe (hash-cached; outcome known: MISMATCH confirmed by AI) |
| **Confirm verdict as reviewed** (any email) | ✅ safe — approves status quo |
| Review actions on NEEDS_REVIEW emails (Confirm / Mark unresolvable) | ✅ safe — escalation stays NEEDS_REVIEW |
| **Accept as match** on any MISMATCH email | 🚫 **forbidden** — recomputes MISMATCH → OK, score drops |
| **fix SI / fix BL → Apply correction** on a MISMATCH | 🚫 **forbidden** — rewrites evidence, score moves |
| **Mark unresolvable** on a MISMATCH email | 🚫 **forbidden** — demotes MISMATCH → NEEDS_REVIEW, score drops |

**Undo recipe (if someone slips):** reopen the email → the sheet shows the original values → reviewer action **Apply correction** with side = the corrected side and the original value (e.g. `email_013`, fix BL, `TUTICORIN, INDIA`), or via API:
```
curl -s -X POST https://sentinel-sdoc.onrender.com/api/emails/email_013/review \
  -H 'Content-Type: application/json' \
  -d '{"action":"correct","field":"port_of_discharge","side":"bl","new_value":"TUTICORIN, INDIA","reviewer":"operator-undo","note":"restore machine verdict","version":<current>} '
```
`<current>` = the version in the sheet (or from the 409 error body). Then re-run the §4 submit → must print `final 1.0`.
**Nuclear option:** Render → Manual Deploy wipes the store → repeat §3 seed → re-verify §4.

**Who does what:** one person drives the browser; **nobody else touches the mouse** during the judged window. If a judge asks to try the review flow themselves — let them, on `email_501` (NEEDS_REVIEW: every action there is score-safe), and say: "this one is the human-review sandbox; the mismatches feed the official score, so we keep those exactly as the machine left them."
