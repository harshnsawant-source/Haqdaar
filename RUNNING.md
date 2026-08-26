# Running Haqdaar locally

Everything runs on the machine. No cloud calls, no API keys, no secrets.

## One-time setup

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -e "engine[dev,api]"
cd web && npm install
```

## Run the demo (two terminals)

**Terminal 1 — the engine.** Pin the date so staleness banners are reproducible:

```bash
HAQDAAR_TODAY=2026-08-22 ./.venv/Scripts/python.exe -m uvicorn haqdaar.api.app:app \
  --app-dir engine --host 127.0.0.1 --port 8000
```

**Terminal 2 — the PWA.**

```bash
cd web
npm run dev        # http://localhost:5173  — development
```

For the **installable / offline** version (what a phone would install), build and
preview instead. The service worker only registers in production builds:

```bash
cd web
npm run build
npm run preview    # http://127.0.0.1:4173
```

Both dev and preview proxy `/api` to the engine on 8000, which keeps the PWA
same-origin so the service worker is allowed to cache API responses.

## The pre-demo gate — run this, and nothing else, before walking on stage

```bash
./.venv/Scripts/python.exe -m pytest engine/tests -q
```

**One command is the whole gate.** Green means: both rehearsed refusals produce their
exact rendered English, all four voices are correct across all three verticals, the
Guard's six triggers hold, no output hedges, no placeholder leaks into English, the
action layer still refuses a verdict it cannot clear (including into a lapsed scheme),
verified schemes carry no unread marker and unverified ones carry it on every clause,
no engine module has learned what a "student" is, and every failure path degrades
calmly.

**Red means do not demo.** Not "probably fine" — a golden test going red means a
sentence a citizen would read has changed, and you need to know which one and why
before a judge does.

The suite needs no network, no API key, and no OCR engine. It is the same command on
any machine.

## Verifying the PWA

- **Installable:** open `http://127.0.0.1:4173` in Chrome → install icon in the address
  bar, or DevTools → Application → Manifest.
- **Offline is real, and worth checking rather than trusting.** Load the preview, click
  a persona so a verdict is cached, then **stop the engine in terminal 1** and reload.
  The app still opens, the persona list is still there, and any verdict you already
  viewed comes back with a banner reading *"Showing a stored answer — you are
  offline."* Ask for a persona you never opened and it says so plainly rather than
  inventing one.

The service worker warms `/api/personas` on install for exactly this reason: without
it the app opens offline to an empty screen with nothing to tap — technically a loaded
shell, practically a dead product.

## What is real and what is not

| | |
|---|---|
| Real | corpus → evaluator → Guard → deterministic render → API → UI |
| Real | offline shell + stored verdicts, install to home screen |
| Real | the A+ action layer: deterministic form fill, gap list, tracking reference |
| **Simulated** | the *submission itself*. Nothing is sent anywhere, no portal, no login. The reference is generated on this device and begins `SIM-` |
| **Stand-in** | both application form layouts (Stand-Up India, NSFDC) — ours, not the official PDFs. Every label says `[VERIFY AT SOURCE]` |
| Real | document upload + local OCR extraction, with per-field confidence and origin |
| Fixtures | personas are checked-in JSON; a fixture-backed upload labels every borrowed value |
| Real | **9 of 10 scheme rules transcribed verbatim from official government sources**, each carrying its URL and the date we read it |
| **Provisional** | SGNAY only, and on one clause: its page never says whether the 18-65 age range governs the widow categories. The card says so. See the file header |
| **Lapsed** | Stand-Up India (ended 31.03.2025) and VCF-SC (guidelines period ended 31.03.2026). The engine says so and refuses to file into either |

### Corpus, as of 2026-08-26

| Vertical | Schemes |
|---|---|
| entrepreneur | stand-up-india *(lapsed)*, nsfdc-term-loan, vcf-sc *(lapsed)* |
| welfare | pm-kisan, ignwps, sgnay *(provisional)*, pmjay, avvc |
| student | pre-matric-sc, top-class-sc |

A vertical is a corpus folder plus an intake section. No engine code knows which
verticals exist, and `test_student_vertical.py` fails if any of it learns.

### API surface

| | |
|---|---|
| `GET /api/health` | ok + the list of verticals |
| `GET /api/personas` | demo fixtures and their vertical |
| `GET /api/needs` | the front door in the citizen's words, each routed to a vertical |
| `GET /api/intake` | the question set for one vertical, in one language |
| `POST /api/intake` | answers in, cards out |
| `GET /api/evaluate` | one persona through the whole pipeline |
| `POST /api/extract` | document upload and OCR |
| `GET /api/compare` | 2-4 schemes side by side. **No best fit, ever** |
| `POST /api/act` | SIMULATED form fill. 409 on an uncleared or lapsed scheme |

## The A+ action beat

With the engine running, from an ELIGIBLE card press **Apply with this profile**. It
fills what her documents prove, lists what is still missing, and issues a reference:

```
SIMULATED. Nothing has been submitted to any government portal, and this reference is
generated on this device. It is not an application.
SIMULATED FORM LAYOUT. This is a stand-in we built, not the official application document.

I have filled what your documents can prove for Stand-Up India.
Filled 4 fields from your documents.
Your simulated reference: SIM-STANDUPIND-20260822-D1679F

You still need to supply these:  ... 10 fields ...
Bring your aadhaar — it supplies 4 of them.
```

Or from the command line:

```bash
curl -X POST "http://127.0.0.1:8000/api/act?persona_id=entrepreneur-01&scheme_id=stand-up-india"
```

It refuses (HTTP 409) for anyone the engine could not clear — try `entrepreneur-02`,
who is blocked on a caste certificate. You do not file an application for someone whose
eligibility is unproven.

## Document upload (day 6)

Local OCR, on the device. No cloud extractor, no API key, no scan of anyone's caste
certificate leaving the machine they handed it to.

**The OCR engine is an optional system dependency.** Without it the app still runs and
still tells the truth — it reports `ocr_available: false`, reads nothing, and every
field resolves UNKNOWN. To install it:

```bash
winget install --id UB-Mannheim.TesseractOCR    # Windows
# then reopen the terminal so tesseract is on PATH
```

`pytesseract` (the Python wrapper) is already a dependency; the binary is separate.

### The two modes are a visible choice, never a silent one

| Mode | What it does | When to use it |
|---|---|---|
| `LIVE` | Only what was actually read. Unreadable fields stay UNKNOWN, so the engine refuses or blocks. | Honest demonstration of the real path |
| `FIXTURE_BACKED` | Read where confident, checked-in persona elsewhere — **each borrowed field labelled on screen** | Demo determinism (guard doc §6.1) |

A fixture value is never shown as a live read, and a live read is never overwritten by
a fixture. The UI shows `Read 96%` or `Demo profile` against every field.

### Why a misread cannot produce a wrong answer

Every extracted field carries Tesseract's real confidence. Below the floor (0.75) the
field is *dropped*, not rounded up — so `CitizenProfile.get()` returns nothing, the
evaluator sees no evidence, and the predicate resolves UNKNOWN. T1/T2 then produce a
refusal or a blocked-on-document.

A bad scan can therefore cost us a *yes we could have proven*. It cannot produce a
confident wrong answer. Values outside a declared map and numbers outside a
plausibility window are dropped the same way, never coerced to the nearest option.

---

# Demo-day readiness

## Footprint (re-measured 2026-08-26, this machine)

The "runs on a Panchayat laptop" claim, with numbers behind it. Re-measure before the
demo rather than quoting these: the corpus grew from 6 schemes to 10 and from two
verticals to three since the first measurement, and every number here moved.

| | |
|---|---|
| Engine cold start (import + wire up) | **~187 ms** |
| Evaluate + render, all three verticals, 10 cards | **~42 ms** |
| Engine process, resident | **~53 MB** |
| PWA served bundle | **51 KB JS + 3 KB CSS gzipped**, 169 KB on disk |
| Corpus (all rules, three verticals) | **165 KB** |
| Network calls | **zero** |
| API keys | **none** |
| Generative model calls | **zero** |

Test suite: **351 passing, 1 skipped** in about four seconds, with every key stripped
from the environment. The skip is the live-OCR test, which needs Tesseract installed.

What this buys on stage: the whole system is a ~56 MB Python process and a 50 KB page.
It is not "cloud AI shrunk down" — there is no model to shrink. A cheap laptop at a
Common Service Centre serves the PWA over the LAN and answers in a tenth of a second
with the network unplugged.

**Honest caveat:** these are measured on a developer laptop, not on constrained
hardware. Nobody has run this on a low-end device yet. If a judge asks "show me on a
cheap machine" the honest answer is that the footprint makes it plausible and it has
not been tested there — do not claim otherwise (judge Q&A Q6).

## Live OCR needs one system install

Not installed on this machine, which is why the suite reports **1 skipped** — the
real-OCR test. Everything else runs without it, and the app honestly reports
`ocr_available: false` and reads nothing rather than guessing.

```bash
winget install --id UB-Mannheim.TesseractOCR    # then reopen the terminal
```

## Pre-flight checklist

1. `pytest engine/tests -q` → green. **Red means do not demo.**
2. Start the engine, confirm `curl http://127.0.0.1:8000/api/health` returns `ok`.
3. `npm run build && npm run preview` — use the **preview** build, not `npm run dev`:
   the service worker only registers in production, and the offline beat needs it.
4. **If you rebuilt in the last few minutes, open a FRESH TAB.** An already-open tab
   can hold the previous service worker and hang on stale assets — hard reload
   (Ctrl+Shift+R), or close the tab and reopen. Rebuilding shortly before the demo is
   exactly when this bites, so treat "I just rebuilt" as "use a new tab".
5. Open the PWA, click through **one** persona so the shell and a verdict are cached.
6. Rehearse the front door: **Tell us about your situation** → pick a domain →
   answer a few questions → tick the documents she holds. Answer WITHOUT documents
   first to show everything land on "you need this paper", then again WITH them to
   show the entitlement resolve. That contrast is the product in one gesture.
7. Rehearse the two set-pieces:
   - entrepreneur: NSFDC → ELIGIBLE with proof **plus** the separate approval refusal
   - welfare: Sunita → PM-JAY refusal (SECC 2011) and "eligible in 2036" for AVVC
8. Rehearse the failure: stop the engine, reload — the app must still open, still list
   personas, and say *"Showing a stored answer — you are offline."*
9. Have the backup refusal ready: ask something out of corpus ("How much tax do I owe?").
10. Know what is **simulated**: the submission and the Stand-Up India form layout. Say so
   before a judge asks.
11. Know what is **provisional**: every scheme rule. Every card says so on screen.

## Three quirks that will waste your time if you do not know them

**A backgrounded engine can report a failure while running perfectly.** Starting
uvicorn in the background has repeatedly reported `exit code 127` with an empty log
while the server was up and answering correctly. **Trust the port, not the status:**

```bash
netstat -ano | grep ":8000.*LISTENING"     # is something actually there?
curl -s http://127.0.0.1:8000/api/health   # is it answering?
```

**A stale engine will serve you yesterday's code.** uvicorn without `--reload` loads
the code once at startup, so a server left running from an earlier session keeps
answering with old behaviour — twice this looked like a change had not landed. If a
response is missing something you just added, check the port before debugging the code:

```bash
netstat -ano | grep ":8000.*LISTENING"          # note the PID
powershell -Command "Stop-Process -Id <PID> -Force"
```

The reliable check that a server has the code you expect is to ask it for something
only the new code can produce, rather than trusting that it restarted.

**3. `vite preview` binds to localhost, not to 127.0.0.1.** Without `--host` it listens
on IPv6 `::1` only, so `curl http://127.0.0.1:4173/` fails with a connection error while
`http://localhost:4173/` returns 200. If you are scripting a pre-flight check, use
`localhost`. It also picks the next free port silently when 4173 is taken, and prints the
real one, so read its output rather than assuming.


## If something breaks mid-demo

The failure paths are rehearsed and asserted (`engine/tests/unit/test_failure_paths.py`).
A crash does not produce a stack trace on screen; the PWA shows its calm offline copy.
The correct move is to say what happened and carry on — a system that refuses when it
cannot answer is the product working, and that is the whole pitch.

---

# Privacy and safety

This app handles caste certificates, land records and income documents, on a machine
that may be shared. These are not hypotheticals for this product — they are the
deployment story.

## NEVER PUT A REAL CITIZEN DOCUMENT IN THIS FOLDER

**This repo lives inside OneDrive, which syncs to Microsoft's cloud.** A real income
certificate or land record dropped into the working tree would be uploaded offsite
silently and would be very hard to recall.

`.gitignore` refuses image and PDF types as a safety net, but a gitignored file still
syncs to OneDrive — git has nothing to do with it. **Demo inputs only.** Better still,
move the repo outside OneDrive entirely (`C:\dev\haqdaar`).

## Shared-device hygiene

The service worker caches verdicts so the app works offline. On a shared laptop that
means the next person could otherwise reload and read the previous person's schemes,
documents and gaps.

- **"Finish and clear"** purges cached verdicts, extracted fields AND her saved intake
  answers. Use it between citizens. The app shell and persona list survive, so the
  device still works offline.
- Switching to a different person purges automatically — you do not have to remember.
- What is never purged, because it is nobody's data: the app shell, the persona list.

### Remembered answers, and why they are not an account

The app keeps her intake answers in `localStorage` so she is not retyping them next
time. There is no login and no server-side profile, deliberately:

- A signup form is one more wall between someone and an entitlement she is not
  claiming, and the people it turns away are the ones the scheme was written for.
- The data is caste, income, widowhood, landholding, BPL status. Attaching that to an
  account means running a server holding the most sensitive facts about the most
  vulnerable people in the country, as a permanent breach target. We hold none of it.

**Only the ANSWERS are stored, never a verdict.** A remembered verdict goes stale the
day a scheme lapses or a threshold moves, and would quietly become a wrong answer with
nothing to flag it. Answers do not go stale, so they get replayed through the engine
and it decides again every time. `web/src/remember.js` is the whole of it, and both
purge gestures above call its `forget()`.

## What the upload path does and does not do

| | |
|---|---|
| Per-file limit | 5 MB |
| Files per request | 4 |
| Accepted | PNG, JPEG, WEBP, TIFF, BMP — checked by **declared type and magic bytes** |
| Decoded-image bound | 50 megapixels (a 600 dpi A4 scan is ~35 MP) |
| Written to disk | **nothing** — the multipart spool threshold is raised to the per-file cap so an accepted file never reaches the filesystem |
| Retained after the response | **nothing** — asserted by `tests/unit/test_upload_security.py` |
| Sent anywhere | **nothing.** No network calls, no cloud OCR, no keys |

A refused upload reads as a refusal ("that file is not an image we can read"), never a
stack trace. An image we accept but cannot read produces UNKNOWN fields and the normal
refusing verdict — never a guessed value.

## Dependency audit (2026-08-23)

- **Python (`pip-audit`): no known vulnerabilities.**
- **npm production (`npm audit --omit=dev`): 0 vulnerabilities.** Nothing in the built
  `dist/` bundle is affected.
- **npm dev: 2 findings, both in the Vite dev server** (esbuild dev-server CORS; Vite
  path traversal, `server.fs.deny` bypass on Windows, launch-editor NTLM disclosure).
  The only fix is Vite 8, a breaking major.

  **Not upgraded before the freeze, deliberately.** All four are `npm run dev` surface
  and none ship in the built bundle. A breaking bundler upgrade days before a demo is a
  worse risk than a dev-only advisory. Mitigation: **use `npm run build && npm run
  preview` for anything demo-facing** — which is what the demo instructions already say,
  because the service worker needs a production build. Upgrade Vite after 2 September.

  Note the Windows `server.fs.deny` bypass is the one to respect: do not run
  `npm run dev` on a machine holding sensitive files while browsing untrusted sites.

## Secrets

No API keys, tokens, credentials or private keys anywhere in the working tree or in any
commit in git history. No `.env` files exist. The engine needs no keys — there is no
model to call and no service to authenticate against, so there is nothing to leak.

---

# Guided intake (the front door)

A citizen answers structured questions — never a blank box, never a model. The answers
become a profile and flow through the same evaluator, Guard and renderer as a document
upload or a checked-in fixture. `corpus/intake.yaml` holds the questions as data.

## What an answer is worth

An answer is a **self-declaration, and only that.** Every intake fact is filed under
`self_declaration`. Ticking "I have a caste certificate" is not evidence of what the
certificate says — we have not read it — so it settles nothing.

The corpus decides what a declaration settles.
`eligibility/evaluate.py` checks that a value's document appears in the clause's
`verifiable_from`, so:

- PM-KISAN's exclusions — which the real form collects on the applicant's own account —
  **are** settled by her answer.
- A caste certificate, BPL card or 7/12 extract clause is **not** settled by someone
  saying so. It stays UNKNOWN and becomes BLOCKED_ON_DOCUMENT.

Intake still asks which documents she holds, but only to point her at the upload step
for papers she already has. It never counts as evidence. Every intake result carries:

> "This is based on what you told me. I have not seen your documents, so anything that
> needs a certificate is still marked as needing one."

## The demo arc: intake, then upload

Intake alone will usually show **everything blocked**. That is the correct answer, and
it is the better arc — it is the setup, not the payoff:

1. **Tell us your situation.** → "Here are the three papers to bring."
2. **Upload them.** → the same schemes resolve, now with real proof read off real
   documents.

Same person, same answers, before and after the documents are actually read:

| | Intake only (her word) | After uploading her documents |
|---|---|---|
| PM-KISAN | BLOCKED → bring 7/12 | **ELIGIBLE**, proven from the 7/12 |
| AVVC | BLOCKED → bring Aadhaar | NOT_ELIGIBLE (rule is 70+) |
| IGNWPS / SGNAY | BLOCKED | BLOCKED — one BPL card unlocks 2 |
| PM-JAY | UNVERIFIABLE | UNVERIFIABLE (SECC 2011, forever) |

Nothing about the engine changes between the two columns. Only what she could
evidence does. **"Proven from your X" appears only where X was actually read** — a test
asserts an intake card can never claim it.

---

# Deploying to Vercel

The repo is wired for it: `vercel.json`, `requirements.txt`, and `api/index.py`, which
puts the engine on the import path and points `HAQDAAR_CORPUS` at the bundled corpus.
The PWA is built from `web/` and served as static files; `/api/*` is rewritten to one
Python serverless function running the same FastAPI app as locally.

## One thing does not work when deployed

**Live OCR.** There is no tesseract binary on Vercel. `profile/ocr.py` checks
`shutil.which("tesseract")` before importing pytesseract, so document upload reports
itself unavailable rather than failing, and the UI already has the message for it.

Everything else runs: guided intake, free-text reading, the evaluator, the Guard and all
six triggers, three languages, comparison, and the simulated action layer.

## The hosted build does not replace the local demo

The pitch is that this runs on a Panchayat laptop with no network. A URL cannot show
that, and on stage a hosted site makes hall wifi a single point of failure for the whole
demo. Deploy it so judges can try it afterwards and so the QR on the closing slide goes
somewhere. **Demo from localhost.**

## How to deploy

Import the GitHub repo at vercel.com/new. Vercel reads `vercel.json` and needs no
settings changed. Every push to `main` then redeploys.

The CLI route works too if you prefer it: `npx vercel` from the repo root, then
`npx vercel --prod`.

## `framework` must be null

`requirements.txt` lists FastAPI, and Vercel's docs say it "detects your framework
automatically when it finds a matching dependency" and then "routes every request to
it". That preset would send `/` to the Python function instead of serving the built PWA,
so the site becomes a FastAPI 404. `"framework": null` says this project is a static
site that happens to have functions under `/api`.

## Do not set `installCommand` in vercel.json

It overrides the WHOLE dependency install step, pip included, not just npm. Setting it
to skip a non-existent root `package.json` meant `requirements.txt` was never installed
and the function died with `ModuleNotFoundError: No module named 'fastapi'`. That single
line cost three failed deploys.

npm is already handled inside `buildCommand`, which runs `npm ci` in `web/`. Leave
`installCommand` absent and let Vercel install the Python dependencies itself.

## If the function fails to boot

Check the function logs for an import error first. The two things that break it are the
corpus not being bundled (`includeFiles` in `vercel.json`) and a dependency missing from
`requirements.txt`, which is pinned to what the local `.venv` runs so a deploy cannot
quietly install a different engine than the one the tests passed against.
