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

## Tests

```bash
./.venv/Scripts/python.exe -m pytest engine/tests -q
```

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
