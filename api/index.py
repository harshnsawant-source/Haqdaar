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

__all__ = ["app"]
