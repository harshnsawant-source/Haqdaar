"""Vercel entry point for the engine.

Vercel's Python runtime serves an ASGI app exported as `app` from a file under
`api/`. The engine itself is unchanged: this only puts it on the import path and
tells it where the corpus lives, because the deployed file layout is not the repo
layout.

WHAT IS DIFFERENT WHEN DEPLOYED
-------------------------------
Live OCR. There is no tesseract binary on Vercel, and `profile/ocr.py` checks for it
before importing pytesseract, so document upload reports itself unavailable rather
than failing. Everything else runs: guided intake, free-text reading, the evaluator,
the Guard, all six triggers, rendering in three languages, and the simulated action
layer.

That degradation is honest and already has a message. It is also why the local run
stays the real demo: the pitch is that this works on a Panchayat laptop with no
network, and a hosted URL cannot demonstrate that.
"""

import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

# The engine package lives under engine/, which is not a Vercel convention.
sys.path.insert(0, str(_ROOT / "engine"))

# CORPUS_ROOT defaults to a path relative to the source file, which does not survive
# the move into the function bundle. Set it explicitly before the app is imported.
os.environ.setdefault("HAQDAAR_CORPUS", str(_ROOT / "corpus"))

from haqdaar.api.app import app  # noqa: E402

__all__ = ["app"]
