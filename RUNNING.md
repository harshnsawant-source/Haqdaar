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
exact rendered English, all four voices are correct across both verticals, the Guard's
five triggers hold, no output hedges, no placeholder leaks into English, the action
layer still refuses a verdict it cannot clear, and every failure path degrades calmly.

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
| **Stand-in** | the Stand-Up India form layout — ours, not the official PDF. Every label says `[VERIFY AT SOURCE]` |
| Real | document upload + local OCR extraction, with per-field confidence and origin |
| Fixtures | personas are checked-in JSON; a fixture-backed upload labels every borrowed value |
| **Provisional** | every scheme rule is `[VERIFY AT SOURCE]` and every card says so |

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

## Footprint (measured 2026-08-23, this machine)

The "runs on a Panchayat laptop" claim, with numbers behind it.

| | |
|---|---|
| Engine cold start (import + wire up) | **~165 ms** |
| Evaluate + render, both verticals, 7 cards | **~23 ms** |
| Engine process, resident | **~56 MB** |
| API response, warm, full vertical | **median 119 ms** (min 34, max 220) |
| PWA served bundle | **50 KB JS + 2 KB CSS gzipped**, 189 KB on disk |
| Corpus (all rules, both verticals) | **93 KB** |
| Network calls | **zero** |
| API keys | **none** |
| Generative model calls | **zero** |

Test suite: **220 passing** in under two seconds, with every key stripped from the
environment.

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
4. Open the PWA, click through **one** persona so the shell and a verdict are cached.
5. Rehearse the two set-pieces:
   - entrepreneur: NSFDC → ELIGIBLE with proof **plus** the separate approval refusal
   - welfare: Sunita → PM-JAY refusal (SECC 2011) and "eligible in 2036" for AVVC
6. Rehearse the failure: stop the engine, reload — the app must still open, still list
   personas, and say *"Showing a stored answer — you are offline."*
7. Have the backup refusal ready: ask something out of corpus ("How much tax do I owe?").
8. Know what is **simulated**: the submission and the Stand-Up India form layout. Say so
   before a judge asks.
9. Know what is **provisional**: every scheme rule. Every card says so on screen.

## If something breaks mid-demo

The failure paths are rehearsed and asserted (`engine/tests/unit/test_failure_paths.py`).
A crash does not produce a stack trace on screen; the PWA shows its calm offline copy.
The correct move is to say what happened and carry on — a system that refuses when it
cannot answer is the product working, and that is the whole pitch.
