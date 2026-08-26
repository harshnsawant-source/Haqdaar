"""Vercel entry point for the engine.

Vercel's Python runtime finds the ASGI app by STATICALLY scanning this file for a
top-level `app`. That is why the import below is a plain module-level statement and not
wrapped in a try/except: a previous version caught the import to serve a diagnostic, and
Vercel could no longer see `app` at all ("does not define a top-level app FastAPI
instance"). If the import fails now, it fails in the build log, which is readable.

The engine itself is unchanged. This only puts it on the import path and tells it where
the corpus lives, because the deployed file layout is not the repo layout and
`CORPUS_ROOT` resolves relative to its own source file.

WHAT IS DIFFERENT WHEN DEPLOYED
-------------------------------
Live OCR. There is no tesseract binary on Vercel, and `profile/ocr.py` checks for it
before importing pytesseract, so document upload reports itself unavailable rather than
failing. Everything else runs: guided intake, free-text reading, the evaluator, the
Guard and all six triggers, three languages, and the simulated action layer.

That is also why the local run stays the real demo: the pitch is that this works on a
Panchayat laptop with no network, and a hosted URL cannot demonstrate that.

WHY THIS FILE ALSO SERVES THE FRONTEND
--------------------------------------
`requirements.txt` lists FastAPI, so Vercel detects the framework and, in its words,
"runs your app as Vercel Functions and routes every request to it" — EVERY request,
including `/` and `/index.html`. `outputDirectory` never gets a look in, so the built
PWA was not served at all and the whole site answered with this app's JSON 404.

Rather than fight the detector, the app owns both. One router, so there is no second
layer that can disagree about which path goes where. The mount is here and not in
`api/app.py` because it is a deployment fact: `npm run dev` proxies to a local uvicorn
and must not start serving a stale `dist/` instead.
"""

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# The engine package lives under engine/, which is not a Vercel convention.
if str(_ROOT / "engine") not in sys.path:
    sys.path.insert(0, str(_ROOT / "engine"))

# CORPUS_ROOT defaults to a path relative to its own source file, which does not survive
# the move into the function bundle.
os.environ.setdefault("HAQDAAR_CORPUS", str(_ROOT / "corpus"))

# Top-level and unwrapped, so Vercel's scanner can find it. Keep it that way.
from haqdaar.api.app import app  # noqa: E402

_DIST = _ROOT / "web" / "dist"

if (_DIST / "index.html").is_file():
    from fastapi.staticfiles import StaticFiles  # noqa: E402

    # Appended LAST, and that ordering is the whole design. Starlette matches routes in
    # registration order, so every /api/* route above is tried before this catch-all.
    # Mounting it first would swallow the entire API.
    #
    # html=True serves index.html for "/", which is all the PWA needs: it keeps its
    # state in memory and localStorage rather than in the URL, so there are no client
    # routes to fall back for.
    app.mount("/", StaticFiles(directory=str(_DIST), html=True), name="web")
else:
    # Legible instead of mysterious. If the build step did not run, the API still works
    # and this says so, rather than returning the same bare 404 for every path and
    # sending the next person back through the routing debugging we just finished.
    from fastapi.responses import PlainTextResponse  # noqa: E402

    @app.get("/", response_class=PlainTextResponse)
    def _no_frontend() -> str:
        return (
            "The engine is running, but web/dist was not built, so there is no page to "
            "serve. Check that the build command ran. The API is live: try /api/health."
        )

__all__ = ["app"]
