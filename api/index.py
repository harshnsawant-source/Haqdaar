"""Vercel entry point for the engine.

Vercel's Python runtime serves an ASGI app exported as `app` from a file under `api/`.
The engine itself is unchanged: this only puts it on the import path and tells it where
the corpus lives, because the deployed file layout is not the repo layout and
`CORPUS_ROOT` resolves relative to its own source file.

WHY THE IMPORT IS WRAPPED
-------------------------
A serverless function that fails to import returns FUNCTION_INVOCATION_FAILED and a
generic 500, which tells you nothing and cannot be debugged from outside. So a failed
boot is caught and served as a diagnostic instead: what broke, and whether the corpus,
the templates and the engine package actually made it into the bundle.

That is not a fallback in the sense of degrading gracefully. It serves NO verdicts and
never pretends to. It exists so the deployment can explain itself.

WHAT IS DIFFERENT WHEN DEPLOYED
-------------------------------
Live OCR. There is no tesseract binary on Vercel, and `profile/ocr.py` checks for it
before importing pytesseract, so document upload reports itself unavailable rather than
failing. Everything else runs: guided intake, free-text reading, the evaluator, the
Guard and all six triggers, three languages, and the simulated action layer.

That is also why the local run stays the real demo: the pitch is that this works on a
Panchayat laptop with no network, and a hosted URL cannot demonstrate that.
"""

import os
import sys
import traceback
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# The engine package lives under engine/, which is not a Vercel convention.
if str(_ROOT / "engine") not in sys.path:
    sys.path.insert(0, str(_ROOT / "engine"))

os.environ.setdefault("HAQDAAR_CORPUS", str(_ROOT / "corpus"))

try:
    from haqdaar.api.app import app
except Exception:  # noqa: BLE001 - the whole point is to report anything at all
    _TRACE = traceback.format_exc()

    def _probe() -> dict[str, object]:
        """What actually landed in the bundle. The usual cause is a missing file."""
        corpus = Path(os.environ["HAQDAAR_CORPUS"])
        templates = _ROOT / "engine" / "haqdaar" / "render" / "templates"
        return {
            "python": sys.version,
            "root": str(_ROOT),
            "root_contents": sorted(p.name for p in _ROOT.iterdir())
            if _ROOT.is_dir()
            else "root is not a directory",
            "engine_package_present": (_ROOT / "engine" / "haqdaar" / "__init__.py").is_file(),
            "corpus_dir": str(corpus),
            "corpus_present": corpus.is_dir(),
            "corpus_verticals": sorted(p.name for p in corpus.iterdir())
            if corpus.is_dir()
            else [],
            "templates_present": templates.is_dir(),
            "templates": sorted(p.name for p in templates.iterdir())
            if templates.is_dir()
            else [],
        }

    from fastapi import FastAPI
    from fastapi.responses import JSONResponse

    app = FastAPI(title="Haqdaar (failed to start)")

    @app.get("/api/health")
    @app.api_route("/{path:path}", methods=["GET", "POST"])
    def _explain(path: str = "") -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "error": "the engine failed to import, so no verdict can be served",
                "traceback": _TRACE.splitlines()[-12:],
                "bundle": _probe(),
            },
        )

__all__ = ["app"]
