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
| **Simulated** | the "Apply with this profile" button — labelled SIMULATED, disabled, lands day 5 |
| Fixtures | personas are checked-in JSON; document upload/OCR lands day 6 |
| **Provisional** | every scheme rule is `[VERIFY AT SOURCE]` and every card says so |
