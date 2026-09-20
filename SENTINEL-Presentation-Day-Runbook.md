# SENTINEL — Presentation-Day Runbook
*(execute T-90 min before the submission deadline / judging window)*

## 1. Ship everything pending (5 min)
- Render dashboard → **Manual Deploy → Deploy latest commit** (auto-deploys can queue; manual is instant).
- Verify: `curl -s https://sentinel-sdoc.onrender.com | grep -o 'index-[A-Za-z0-9_-]*\.js'` matches the latest `static/app/assets` hash in the repo.

## 2. Warm + keep-warm (2 min)
- Hit `https://sentinel-sdoc.onrender.com/api/selfwarm` once — confirm `{"status":"ok","emails":520}`.
- Confirm the GitHub Actions keep-warm workflow exists and shows a green run in the last hour. If it was never added (token lacked `workflow` scope): **Add file → `.github/workflows/keep-warm.yml`** — content is in the workspace at `sentinel/.github/workflows/keep-warm.yml`. Two minutes, one commit. *(Alternative: any uptime pinger on `/api/selfwarm`.)*

## 3. Pre-seed the reviewer log (3 min — closes the "empty store" risk)
The SQLite store resets on each redeploy; seed one genuine round trip so a judge opening the site sees a live audit chain:
1. Open the site → Inbox → open `email_013` (the LOCODE-trap mismatch).
2. In **Reviewer round trip**: reviewer = your name, note = "pre-demo verification round", click **Accept as match** → verdict recomputes to OK, v1 recorded.
3. Reopen the sheet → click **Apply correction** path? No — instead click **Confirm verdict as reviewed** on another email (`email_520`, the escalated one → **Mark unresolvable** + note).
4. Verify: `curl -s https://sentinel-sdoc.onrender.com/api/audit | head -c 400` → events present.
*(Or via API: `POST /api/emails/email_013/review {"action":"reject_flag","field":"port_of_discharge","note":"pre-demo verification round","version":0}` then `email_520` unresolvable.)*

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
